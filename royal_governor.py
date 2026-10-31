"""
royal_governor.py — AI Royal Governor agent for RetroRevive: Hammurabi's Living Empire.

Architecture:
  - RoyalGovernor is the central agent controller
  - It uses a real LLM (Google Gemini via google-generativeai) when an API key
    is configured in the environment variable GEMINI_API_KEY or GOOGLE_API_KEY
  - When no API key is available, it falls back to a deterministic rule-based
    planner that is HONEST about what it is (not labeled as LLM-powered)
  - ALL planning and tool calls go through real agent_tools.py functions
  - Game state is NEVER faked — every resource value comes from game_logic.py

Decision cycle per turn (ReAct-style Observe → Think → Plan → Act → Verify):
  1. OBSERVE  — call inspect_kingdom_state() + inspect_disaster_conditions()
  2. THINK    — LLM / rule-planner reasons about goal + threats
  3. PLAN     — generates concrete TurnDecisions with justification
  4. VALIDATE — call validate_action() before executing
  5. ACT      — call advance_kingdom_turn() (only function that mutates state)
  6. OBSERVE  — read updated state
  7. VERIFY   — compare before/after, check goal progress
  8. LOG      — append ActionRecord to history
"""

from __future__ import annotations

import json
import math
import os
import time
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Dict, List, Optional

from game_logic import GameState, TurnDecisions, DefaultRNG
from modern_game_logic import EnhancedGameState, init_enhanced_game
from agent_tools import (
    inspect_kingdom_state,
    calculate_grain_requirements,
    validate_action,
    allocate_grain,
    manage_land,
    manage_farming,
    advance_kingdom_turn,
    inspect_disaster_conditions,
    get_advisor_recommendation,
    get_chronicle_summary,
    ToolResult,
)


# ---------------------------------------------------------------------------
# Data model for one agent action record
# ---------------------------------------------------------------------------

class AgentStatus(str, Enum):
    IDLE       = "IDLE"
    PLANNING   = "PLANNING"
    EXECUTING  = "EXECUTING"
    VERIFYING  = "VERIFYING"
    DELEGATED  = "DELEGATED"
    PAUSED     = "PAUSED"
    COMPLETED  = "COMPLETED"
    FAILED     = "FAILED"


@dataclass
class ActionRecord:
    """Complete record of one agent turn cycle."""
    turn_number:      int
    game_year:        int
    goal:             str
    observation:      Dict[str, Any]
    disaster_check:   Dict[str, Any]
    reasoning:        str
    planned_actions:  Dict[str, int]
    validation_result:Dict[str, Any]
    tool_calls:       List[str]
    execution_result: Dict[str, Any]
    before_resources: Dict[str, int]
    after_resources:  Dict[str, int]
    resource_deltas:  Dict[str, int]
    verification:     str
    verification_ok:  bool
    replanned:        bool = False
    replan_reason:    str  = ""
    backend_used:     str  = "RULE_BASED"   # "GEMINI_LLM" | "RULE_BASED"
    timestamp:        float = field(default_factory=time.time)


@dataclass
class DelegationSession:
    """Tracks a player's delegation of kingdom management to the Governor."""
    goal:              str
    turns_delegated:   int
    turns_completed:   int = 0
    turns_remaining:   int = 0
    is_active:         bool = True
    revoked_by_player: bool = False
    session_start_year: int = 1
    action_history:    List[ActionRecord] = field(default_factory=list)

    def __post_init__(self):
        self.turns_remaining = self.turns_delegated


# ---------------------------------------------------------------------------
# Rule-based planner (honest fallback when no LLM key configured)
# ---------------------------------------------------------------------------

class RuleBasedPlanner:
    """
    Deterministic kingdom-management planner.
    Implements classic agricultural economics for the Hammurabi simulation.
    HONEST label: 'Rule-Based Planner' — not an LLM.
    """

    def plan(
        self,
        state: GameState,
        goal: str,
        observation: ToolResult,
        disaster: ToolResult,
        advisor: ToolResult,
        grain_req: ToolResult,
    ) -> tuple[Dict[str, int], str]:
        """
        Returns (decisions_dict, reasoning_text).
        decisions_dict keys: buy_acres, sell_acres, feed_bushels, plant_acres
        """
        pop   = state.population
        bush  = state.bushels
        acres = state.acres
        price = state.land_price

        reasoning_lines = []
        reasoning_lines.append(f"OBSERVE: Year {state.year}, Pop={pop}, Grain={bush}, Acres={acres}, Price={price}")

        # Step 1: Determine feeding target
        full_feed   = pop * 20
        famine_level = disaster["famine"]["level"]

        if famine_level == "ACTIVE_FAMINE":
            # Must sell land to survive
            deficit      = full_feed - bush
            sell_n       = min(math.ceil(deficit / max(1, price)), acres - 1)
            grain_after_sale = bush + sell_n * price
            feed_bushels = min(full_feed, grain_after_sale)
            buy_acres    = 0
            sell_acres   = sell_n
            reasoning_lines.append(f"THREAT: Active famine. Selling {sell_n} acres to cover grain deficit of {deficit} bu.")
        elif famine_level in ("CRITICAL", "WARNING"):
            sell_acres   = 0
            buy_acres    = 0
            feed_bushels = min(full_feed, bush)
            reasoning_lines.append(f"THREAT: {famine_level} grain shortage. Feeding max possible {feed_bushels} bu.")
        else:
            # Safe — consider land investment
            sell_acres = 0
            feed_bushels = full_feed

            # Buy land if cheap and have surplus
            surplus = bush - feed_bushels
            labor_surplus = max(0, (pop * 10 - 1) - acres)
            if price <= 19 and surplus > 200 and labor_surplus > 0 and "expand" in goal.lower():
                affordable = surplus // price
                buy_acres  = min(affordable // 2, labor_surplus, 30)
                reasoning_lines.append(f"OPPORTUNITY: Land cheap at {price}. Buying {buy_acres} acres.")
            else:
                buy_acres = 0
                reasoning_lines.append(f"STABLE: Feeding all {pop} citizens with {feed_bushels} bu.")

        # Step 2: Planting
        grain_for_planting = max(0, bush - (feed_bushels + buy_acres * price - sell_acres * price))
        labor_limit   = pop * 10 - 1
        land_to_plant = acres + buy_acres - sell_acres
        max_by_seed   = grain_for_planting * 2
        plant_acres   = max(0, min(land_to_plant, labor_limit, max_by_seed))
        reasoning_lines.append(f"FARMING: Planting {plant_acres} acres (labor_limit={labor_limit}, seed_budget={grain_for_planting*2}).")

        # Step 3: Goal alignment check
        if "famine" in goal.lower() or "grain" in goal.lower():
            # Prioritise grain reserves — plant more, buy less
            reasoning_lines.append("GOAL: Prioritising grain reserves as instructed.")
        if "expand" in goal.lower() or "land" in goal.lower():
            reasoning_lines.append("GOAL: Expansion goal detected — favouring land purchase when viable.")

        decisions = {
            "buy_acres":    max(0, buy_acres),
            "sell_acres":   max(0, sell_acres),
            "feed_bushels": max(0, feed_bushels),
            "plant_acres":  max(0, plant_acres),
        }

        return decisions, "\n".join(reasoning_lines)


# ---------------------------------------------------------------------------
# LLM Planner (uses Google Gemini when GEMINI_API_KEY is set)
# ---------------------------------------------------------------------------

class GeminiLLMPlanner:
    """
    Plans decisions using Google Gemini with function-calling (tool-use).
    Falls back to RuleBasedPlanner if the API call fails.
    """

    TOOL_DECLARATIONS = [
        {
            "name": "propose_turn_decisions",
            "description": (
                "Propose specific numeric decisions for this Hammurabi game turn. "
                "Provide exact values for buy_acres, sell_acres, feed_bushels, and plant_acres. "
                "Ensure buy_acres and sell_acres are not both >0."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "buy_acres":    {"type": "integer", "description": "Acres to buy (0 if not buying)"},
                    "sell_acres":   {"type": "integer", "description": "Acres to sell (0 if not selling)"},
                    "feed_bushels": {"type": "integer", "description": "Bushels to allocate for food"},
                    "plant_acres":  {"type": "integer", "description": "Acres to plant with seed grain"},
                    "reasoning":    {"type": "string",  "description": "Explain why you chose these values"},
                },
                "required": ["buy_acres", "sell_acres", "feed_bushels", "plant_acres", "reasoning"],
            },
        }
    ]

    def __init__(self, api_key: str) -> None:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        self._model = genai.GenerativeModel(
            model_name="gemini-1.5-flash",
            tools=self.TOOL_DECLARATIONS,
        )
        self._fallback = RuleBasedPlanner()

    def plan(
        self,
        state: GameState,
        goal: str,
        observation: ToolResult,
        disaster: ToolResult,
        advisor: ToolResult,
        grain_req: ToolResult,
    ) -> tuple[Dict[str, int], str]:
        """
        Ask Gemini to plan the turn. Falls back to rule-based planner on error.
        Returns (decisions_dict, reasoning_text).
        """
        prompt = self._build_prompt(state, goal, observation, disaster, advisor, grain_req)

        try:
            response = self._model.generate_content(prompt)

            # Extract function call from response
            for part in response.candidates[0].content.parts:
                if hasattr(part, "function_call") and part.function_call:
                    fc = part.function_call
                    args = dict(fc.args)
                    decisions = {
                        "buy_acres":    int(args.get("buy_acres", 0)),
                        "sell_acres":   int(args.get("sell_acres", 0)),
                        "feed_bushels": int(args.get("feed_bushels", 0)),
                        "plant_acres":  int(args.get("plant_acres", 0)),
                    }
                    reasoning = f"[GEMINI LLM] {args.get('reasoning', 'No reasoning provided.')}"
                    return decisions, reasoning

            # No function call — fallback
            return self._fallback.plan(state, goal, observation, disaster, advisor, grain_req)

        except Exception as e:
            # API failed — honest fallback
            fallback_decisions, fallback_reasoning = self._fallback.plan(
                state, goal, observation, disaster, advisor, grain_req
            )
            return fallback_decisions, f"[GEMINI API ERROR: {e}] Falling back to rule-based planner.\n{fallback_reasoning}"

    def _build_prompt(self, state, goal, observation, disaster, advisor, grain_req) -> str:
        return f"""You are the Royal Governor of ancient Babylon, managing King Hammurabi's kingdom.

PLAYER GOAL: {goal}

CURRENT KINGDOM STATE (from real game engine):
- Year: {state.year} / 10
- Population: {state.population} citizens
- Grain in silos: {state.bushels} bushels
- Land owned: {state.acres} acres
- Land price this year: {state.land_price} bushels/acre
- Harvest yield last year: {state.harvest_yield} bushels/acre

DISASTER ANALYSIS:
- Famine level: {disaster['famine']['level']} — {disaster['famine']['detail']}
- Plague next year: {disaster['plague']['risk_next_year']}
- Land health: {disaster['land_health']}
- Impeachment risk: {disaster['impeachment_risk']}

GRAIN REQUIREMENTS:
- Full feed cost: {grain_req['requirements']['full_feed_bushels']} bushels (20 per person)
- Can fully feed: {grain_req['can_fully_feed']}
- Seed for max planting: {grain_req['requirements']['seed_for_max_planting']} bushels

ROYAL ADVISOR RECOMMENDATIONS:
- Vizier: {advisor['advisor_recommendations']['vizier_summary']}
- Recommended feed: {advisor['advisor_recommendations']['recommended_feed_bushels']} bushels
- Recommended plant: {advisor['advisor_recommendations']['recommended_plant_acres']} acres
- Recommended buy: {advisor['advisor_recommendations']['recommended_buy_acres']} acres
- Recommended sell: {advisor['advisor_recommendations']['recommended_sell_acres']} acres

GAME RULES:
1. Each citizen needs 20 bushels/year. Starving >45% of population = impeachment (game over).
2. Planting requires: 1 bushel seed per 2 acres, AND max 10 acres per citizen (labor).
3. Buying land costs: acres × land_price bushels.
4. Cannot buy AND sell land in the same turn.
5. All values must be >= 0 and within available resources.

Using the propose_turn_decisions tool, provide your decision for this turn.
Justify your choices based on the player's goal and current threats.
"""


# ---------------------------------------------------------------------------
# Royal Governor — Main Agent Controller
# ---------------------------------------------------------------------------

class RoyalGovernor:
    """
    AI Royal Governor that autonomously manages kingdom turns on the player's behalf.

    Usage:
        governor = RoyalGovernor(enhanced_state)
        session  = governor.delegate("Prevent famine for 3 years", turns=3)
        # Governor runs autonomously; player can call governor.revoke() at any time

    After each turn, governor.current_session.action_history holds the full log.
    governor.current_enhanced_state holds the live (updated) game state.
    """

    def __init__(
        self,
        enhanced_state: EnhancedGameState,
        api_key: Optional[str] = None,
    ) -> None:
        self.current_enhanced_state = enhanced_state
        self._session: Optional[DelegationSession] = None
        self._status  = AgentStatus.IDLE
        self._callbacks: Dict[str, Any] = {}

        # Resolve API key
        resolved_key = (
            api_key
            or os.environ.get("GEMINI_API_KEY")
            or os.environ.get("GOOGLE_API_KEY")
        )

        # Initialize planner
        if resolved_key:
            try:
                self._planner = GeminiLLMPlanner(resolved_key)
                self._backend = "GEMINI_LLM"
            except Exception:
                self._planner = RuleBasedPlanner()
                self._backend = "RULE_BASED"
        else:
            self._planner = RuleBasedPlanner()
            self._backend = "RULE_BASED"

    # -----------------------------------------------------------------
    # Public interface
    # -----------------------------------------------------------------

    @property
    def status(self) -> AgentStatus:
        return self._status

    @property
    def current_session(self) -> Optional[DelegationSession]:
        return self._session

    @property
    def backend_name(self) -> str:
        return self._backend

    def delegate(self, goal: str, turns: int) -> DelegationSession:
        """
        Player assigns a goal and delegation limit.
        Immediately begins executing turns autonomously.
        Returns the completed DelegationSession.
        """
        if self.current_enhanced_state.classic_state.is_over:
            raise RuntimeError("Game is already over — cannot delegate.")

        if turns < 1 or turns > 10:
            raise ValueError("Delegation must be 1–10 turns.")

        self._session = DelegationSession(
            goal=goal,
            turns_delegated=turns,
            session_start_year=self.current_enhanced_state.classic_state.year,
        )
        self._status = AgentStatus.DELEGATED

        # Execute turns
        for _ in range(turns):
            if not self._session.is_active:
                break
            if self.current_enhanced_state.classic_state.is_over:
                break

            record = self._execute_one_turn(self._session.goal, self._session.turns_completed + 1)
            self._session.action_history.append(record)
            self._session.turns_completed += 1
            self._session.turns_remaining  = max(0, turns - self._session.turns_completed)

            # Notify callback if registered
            if "on_turn_complete" in self._callbacks:
                self._callbacks["on_turn_complete"](record, self.current_enhanced_state)

        self._session.is_active = False
        if self._session.revoked_by_player:
            self._status = AgentStatus.PAUSED
        elif (
            self.current_enhanced_state.classic_state.is_over
            and self.current_enhanced_state.classic_state.game_over_reason == "IMPEACHED"
        ):
            self._status = AgentStatus.FAILED
        else:
            self._status = AgentStatus.COMPLETED
        return self._session

    def revoke(self) -> None:
        """Player revokes control from the Governor immediately."""
        if self._session:
            self._session.is_active         = False
            self._session.revoked_by_player = True
        self._status = AgentStatus.PAUSED

    def on_turn_complete(self, callback) -> None:
        """Register a callback to be called after each agent turn (for UI updates)."""
        self._callbacks["on_turn_complete"] = callback

    def get_session_summary(self) -> Dict[str, Any]:
        """Return a JSON-serialisable summary of the current session."""
        if not self._session:
            return {"status": "NO_SESSION"}

        state = self.current_enhanced_state.classic_state
        return {
            "goal":               self._session.goal,
            "status":             self._status.value,
            "backend":            self._backend,
            "turns_delegated":    self._session.turns_delegated,
            "turns_completed":    self._session.turns_completed,
            "turns_remaining":    self._session.turns_remaining,
            "revoked_by_player":  self._session.revoked_by_player,
            "session_start_year": self._session.session_start_year,
            "current_year":       state.year,
            "current_resources": {
                "population": state.population,
                "bushels":    state.bushels,
                "acres":      state.acres,
            },
            "total_starved_session": sum(
                r.execution_result.get("events", {}).get("starved_this_year", 0)
                for r in self._session.action_history
            ),
            "action_count": len(self._session.action_history),
        }

    # -----------------------------------------------------------------
    # Internal: single turn cycle
    # -----------------------------------------------------------------

    def _execute_one_turn(self, goal: str, turn_num: int) -> ActionRecord:
        """Execute full Observe→Think→Plan→Validate→Act→Verify cycle for one turn."""
        state = self.current_enhanced_state.classic_state

        # ── OBSERVE ──────────────────────────────────────────────────
        self._status = AgentStatus.PLANNING
        observation  = inspect_kingdom_state(self.current_enhanced_state)
        disaster     = inspect_disaster_conditions(self.current_enhanced_state)
        grain_req    = calculate_grain_requirements(self.current_enhanced_state)
        advisor      = get_advisor_recommendation(self.current_enhanced_state)

        before_resources = {
            "population": state.population,
            "bushels":    state.bushels,
            "acres":      state.acres,
        }

        # ── THINK + PLAN ──────────────────────────────────────────────
        decisions, reasoning = self._planner.plan(
            state, goal, observation, disaster, advisor, grain_req
        )

        # ── VALIDATE ─────────────────────────────────────────────────
        validation = validate_action(
            self.current_enhanced_state,
            buy_acres=decisions["buy_acres"],
            sell_acres=decisions["sell_acres"],
            feed_bushels=decisions["feed_bushels"],
            plant_acres=decisions["plant_acres"],
        )

        replanned = False
        replan_reason = ""

        if not validation["can_execute"]:
            # Replan: fall back to safest valid decision
            replanned    = True
            replan_reason = f"Original plan invalid: {validation['validation']}. Replanning with safe defaults."
            decisions, reasoning = self._safe_replan(state, decisions, reasoning)
            validation = validate_action(
                self.current_enhanced_state,
                **decisions,
            )

        # ── ACT ───────────────────────────────────────────────────────
        self._status = AgentStatus.EXECUTING
        tool_calls   = ["inspect_kingdom_state", "inspect_disaster_conditions",
                        "calculate_grain_requirements", "get_advisor_recommendation",
                        "validate_action", "advance_kingdom_turn"]

        new_enhanced, exec_result = advance_kingdom_turn(
            self.current_enhanced_state,
            buy_acres=decisions["buy_acres"],
            sell_acres=decisions["sell_acres"],
            feed_bushels=decisions["feed_bushels"],
            plant_acres=decisions["plant_acres"],
        )

        # ── VERIFY ───────────────────────────────────────────────────
        self._status = AgentStatus.VERIFYING
        if exec_result["success"]:
            self.current_enhanced_state = new_enhanced
            after_state = new_enhanced.classic_state

            after_resources = {
                "population": after_state.population,
                "bushels":    after_state.bushels,
                "acres":      after_state.acres,
            }
            deltas = {
                k: after_resources[k] - before_resources[k]
                for k in before_resources
            }

            # Verification logic
            starved = exec_result["events"]["starved_this_year"]
            if starved > 0.45 * state.population:
                verification = f"FAIL: Impeachment triggered — {starved} citizens starved (>{0.45*state.population:.0f} limit)."
                ok = False
            elif starved > 0:
                verification = f"PARTIAL: {starved} citizens starved but kingdom survived. Adjusting plan next turn."
                ok = False
            else:
                verification = f"SUCCESS: All citizens fed. Grain now {after_state.bushels} bu, Pop {after_state.population}."
                ok = True

            # Goal-specific verification
            if "famine" in goal.lower() and starved == 0:
                verification += " Famine prevention goal: ACHIEVED this turn."
            if "grain" in goal.lower():
                if after_state.bushels > state.bushels:
                    verification += f" Grain increased by {after_state.bushels - state.bushels} bu."
                else:
                    verification += f" Grain decreased by {state.bushels - after_state.bushels} bu."
        else:
            after_resources = before_resources.copy()
            deltas = {k: 0 for k in before_resources}
            verification = f"FAIL: Turn execution failed — {exec_result.get('error', 'unknown error')}."
            ok = False

        return ActionRecord(
            turn_number=turn_num,
            game_year=state.year,
            goal=goal,
            observation=observation,
            disaster_check=disaster,
            reasoning=reasoning,
            planned_actions=decisions,
            validation_result=validation,
            tool_calls=tool_calls,
            execution_result=exec_result,
            before_resources=before_resources,
            after_resources=after_resources,
            resource_deltas=deltas,
            verification=verification,
            verification_ok=ok,
            replanned=replanned,
            replan_reason=replan_reason,
            backend_used=self._backend,
        )

    def _safe_replan(
        self,
        state: GameState,
        original: Dict[str, int],
        reasoning: str,
    ) -> tuple[Dict[str, int], str]:
        """Emergency safe fallback: feed as much as possible, plant conservatively."""
        feed = min(state.population * 20, state.bushels)
        remaining = state.bushels - feed
        plant = min(state.acres, state.population * 10 - 1, remaining * 2)
        plant = max(0, plant)
        safe = {"buy_acres": 0, "sell_acres": 0, "feed_bushels": feed, "plant_acres": plant}
        new_reasoning = (
            reasoning
            + f"\n[REPLAN] Emergency safe defaults: feed={feed}, plant={plant}, no land trade."
        )
        return safe, new_reasoning

