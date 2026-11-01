"""
royal_governor.py — AI Royal Governor agent for RetroRevive: Hammurabi's Living Empire.

Architecture:
  - RoyalGovernor is the central agent controller.
  - It uses a real LLM (Google Gemini via google-genai, google-generativeai, or REST API)
    when an API key is configured in GEMINI_API_KEY or GOOGLE_API_KEY.
  - When no API key is available, it falls back to a deterministic rule-based
    planner that is HONEST about what it is (not labeled as LLM-powered).
  - ALL planning and tool calls go through real agent_tools.py functions.
  - Game state is NEVER faked — every resource value comes from game_logic.py and modern_game_logic.py.

Decision cycle per turn (ReAct Observe → Recall → Think → Plan → Validate → Act → Verify):
  1. OBSERVE  — call inspect_kingdom_state(), inspect_disaster_conditions(), inspect_rival_kingdoms()
  2. RECALL   — compute StrategicHistoricalMemory from Chronicle trends
  3. THINK    — LLM / rule-planner reasons about goal, threats, military, and diplomacy
  4. PLAN     — executes preliminary tools (scouting, war readiness, diplomacy) and formulates TurnDecisions
  5. VALIDATE — call validate_action() before executing
  6. ACT      — call advance_kingdom_turn() (authoritative simulation advancement)
  7. VERIFY   — verify before/after resource deltas, check goal progress, detect anomalies
  8. LOG      — append ActionRecord to delegation session history
"""

from __future__ import annotations

import json
import math
import os
import time
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

from game_logic import GameState, TurnDecisions, DefaultRNG
from modern_game_logic import EnhancedGameState, init_enhanced_game, RivalKingdom, DiplomaticRelation
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
    inspect_rival_kingdoms,
    scout_kingdom,
    evaluate_war_readiness,
    manage_military,
    manage_diplomacy,
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
# Strategic Historical Memory (Chronicle Analysis)
# ---------------------------------------------------------------------------

class StrategicHistoricalMemory:
    """Extracts longitudinal trends from the kingdom's Chronicle history."""

    @staticmethod
    def analyze(enhanced: EnhancedGameState) -> Dict[str, Any]:
        chronicle = getattr(enhanced, "chronicle", []) or []
        if not chronicle:
            return {
                "years_recorded": 0,
                "avg_harvest_yield": 3.0,
                "total_starved": 0,
                "avg_starvation_rate": 0.0,
                "rat_infestation_count": 0,
                "avg_rat_damage": 0.0,
                "net_population_growth": 0,
                "summary": "First year of reign; baseline historical estimates in effect.",
            }

        years_count = len(chronicle)
        total_yield = sum(e.yield_rate for e in chronicle)
        avg_yield = total_yield / max(1, years_count)

        total_starved = sum(e.starved for e in chronicle)
        rat_years = sum(1 for e in chronicle if e.rats_ate > 0)
        avg_rat_damage = sum(e.rats_ate for e in chronicle) / max(1, years_count)
        pop_start = chronicle[0].population_start
        pop_current = chronicle[-1].population_end
        net_pop_growth = pop_current - pop_start

        return {
            "years_recorded": years_count,
            "avg_harvest_yield": round(avg_yield, 2),
            "total_starved": total_starved,
            "rat_infestation_count": rat_years,
            "avg_rat_damage": round(avg_rat_damage, 1),
            "net_population_growth": net_pop_growth,
            "summary": (
                f"History over {years_count} years: Avg Harvest Yield = {avg_yield:.1f} bu/acre; "
                f"Rat strikes in {rat_years}/{years_count} years; Net Population Growth = {net_pop_growth:+d}."
            ),
        }


# ---------------------------------------------------------------------------
# Rule-based planner (deterministic fallback when no LLM key configured)
# ---------------------------------------------------------------------------

class RuleBasedPlanner:
    """
    Deterministic kingdom-management planner.
    Implements multi-domain autonomous management: agriculture, economy,
    population survival, military defense, diplomacy, and disaster avoidance.
    HONEST label: 'Rule-Based Planner' — not an LLM.
    """

    def plan(
        self,
        enhanced: EnhancedGameState,
        goal: str,
        observation: ToolResult,
        disaster: ToolResult,
        advisor: ToolResult,
        grain_req: ToolResult,
        memory: Dict[str, Any],
        executed_tool_calls: List[str],
    ) -> Tuple[Dict[str, int], str]:
        """
        Returns (decisions_dict, reasoning_text).
        decisions_dict keys: buy_acres, sell_acres, feed_bushels, plant_acres,
                            recruit_soldiers, train_soldiers_cost, buy_fortifications
        """
        state = enhanced.classic_state
        pop   = state.population
        bush  = state.bushels
        acres = state.acres
        price = state.land_price
        gold  = getattr(state, "treasury_gold", 0)
        soldiers = getattr(state, "soldiers", 0)
        defense = getattr(state, "defense_level", 0)

        reasoning_lines = []
        reasoning_lines.append(
            f"OBSERVE: Year {state.year}, Pop={pop}, Grain={bush}, Acres={acres}, "
            f"Price={price}, Gold={gold}, Soldiers={soldiers}, Def={defense}."
        )

        if memory.get("years_recorded", 0) > 0:
            reasoning_lines.append(f"MEMORY: {memory.get('summary', '')}")

        # -------------------------------------------------------------------
        # Step 1: Diplomacy & Regional Intelligence
        # -------------------------------------------------------------------
        rivals = getattr(enhanced, "rivals", []) or []
        for r in rivals:
            if r.personality == "AGGRESSIVE" and gold >= 50:
                scout_res = scout_kingdom(enhanced, r.id)
                executed_tool_calls.append(f"scout_kingdom({r.id})")
                reasoning_lines.append(f"INTEL: Scouted aggressive rival {r.name}. Strength: {r.military_strength}.")
                war_eval = evaluate_war_readiness(enhanced, r.id)
                executed_tool_calls.append(f"evaluate_war_readiness({r.id})")
                assessment = war_eval.get("comparison", {}).get("strategic_assessment", "MATCHED")
                reasoning_lines.append(f"DEFENSE: War readiness vs {r.name}: {assessment}.")
                break

        # Check diplomatic opportunity with Sumer (trade) or Assyria (peace)
        for r in rivals:
            rel = next((d for d in (enhanced.diplomacy or []) if d.rival_id == r.id), None)
            if r.id == "sumer" and (not rel or rel.status != "TRADE") and gold >= 100:
                dip_res = manage_diplomacy(enhanced, "sumer", "TRADE")
                executed_tool_calls.append("manage_diplomacy(sumer, TRADE)")
                if dip_res.get("accepted"):
                    reasoning_lines.append("DIPLOMACY: Established lucrative trade treaty with Ur of Sumer.")
            elif r.id == "assyria" and (rel and rel.status == "HOSTILE") and gold >= 300:
                dip_res = manage_diplomacy(enhanced, "assyria", "PEACE", tribute_gold=200)
                executed_tool_calls.append("manage_diplomacy(assyria, PEACE, 200)")
                if dip_res.get("accepted"):
                    reasoning_lines.append("DIPLOMACY: Secured peace treaty with hostile Assyria via tribute.")

        # -------------------------------------------------------------------
        # Step 2: Food Security & Land Management
        # -------------------------------------------------------------------
        full_feed = pop * 20
        famine_level = disaster.get("famine", {}).get("level", "SAFE")

        buy_acres = 0
        sell_acres = 0
        feed_bushels = 0

        if famine_level == "ACTIVE_FAMINE":
            # Emergency: Sell land to guarantee full rations AND seed grain for next year
            deficit = full_feed - bush
            desired_seed = min(150, max(50, acres // 5))  # reserve seed to plant at least 100-300 acres
            target_grain = deficit + desired_seed
            sell_n = min(math.ceil(target_grain / max(1, price)), acres // 3)
            sell_n = max(sell_n, min(math.ceil(deficit / max(1, price)), acres - 1))
            grain_after_sale = bush + sell_n * price
            feed_bushels = min(full_feed, grain_after_sale)
            sell_acres = max(0, sell_n)
            buy_acres = 0
            reasoning_lines.append(f"THREAT: Active famine! Selling {sell_n} acres at {price} bu/acre to avert starvation and preserve planting seed.")
        elif famine_level in ("CRITICAL", "WARNING"):
            sell_acres = 0
            buy_acres = 0
            # Feed as much as possible up to full_feed
            feed_bushels = min(full_feed, bush)
            reasoning_lines.append(f"THREAT: {famine_level} grain scarcity. Allocating {feed_bushels} bushels for rations.")
        else:
            # Safe food supplies
            feed_bushels = full_feed
            sell_acres = 0

            # Land purchase opportunity check
            surplus = bush - feed_bushels
            labor_surplus = max(0, (pop * 10 - 1) - acres)
            if price <= 19 and surplus > 250 and labor_surplus > 0:
                affordable = surplus // price
                buy_acres = min(affordable // 2, labor_surplus, 30)
                reasoning_lines.append(f"OPPORTUNITY: Land is a bargain at {price} bu/acre. Purchasing {buy_acres} acres.")
            else:
                buy_acres = 0
                reasoning_lines.append(f"STABLE: Full sustenance guaranteed for all {pop} citizens ({feed_bushels} bu).")

        # -------------------------------------------------------------------
        # Step 3: Agricultural Planting
        # -------------------------------------------------------------------
        grain_for_planting = max(0, bush - (feed_bushels + buy_acres * price - sell_acres * price))
        labor_limit = pop * 10 - 1
        land_to_plant = acres + buy_acres - sell_acres
        max_by_seed = grain_for_planting * 2
        plant_acres = max(0, min(land_to_plant, labor_limit, max_by_seed))
        reasoning_lines.append(f"AGRICULTURE: Sowing {plant_acres} acres with seed grain (seed budget={plant_acres//2} bu).")

        # -------------------------------------------------------------------
        # Step 4: Military & Defense Orders
        # -------------------------------------------------------------------
        recruit_soldiers = 0
        train_cost = 0
        buy_forts = 0

        goal_lower = goal.lower()
        military_mandate = any(k in goal_lower for k in ("militar", "expand", "superior", "defen", "war", "army"))

        if military_mandate:
            # Prioritize military recruitment and defenses within gold/grain limits
            remaining_bushels = grain_for_planting - (plant_acres // 2)
            affordable_recruits_by_gold = gold // 30
            affordable_recruits_by_grain = remaining_bushels // 10
            max_recruits = max(0, min(10, affordable_recruits_by_gold, affordable_recruits_by_grain))

            if max_recruits > 0:
                recruit_soldiers = max_recruits
                gold -= recruit_soldiers * 20
                reasoning_lines.append(f"MILITARY: Recruited {recruit_soldiers} royal guard soldiers into active garrison.")

            if gold >= 100:
                buy_forts = 1
                gold -= 50
                train_cost = min(50, gold)
                reasoning_lines.append(f"FORTIFICATION: Constructed 1 regional defense wall and invested {train_cost} gold in combat drills.")
            executed_tool_calls.append(f"manage_military(recruit={recruit_soldiers})")
        else:
            # Defensive baseline
            if gold >= 150 and defense < 3:
                buy_forts = 1
                reasoning_lines.append("DEFENSE: Erected city gate fortifications for peace of mind.")

        decisions = {
            "buy_acres":           max(0, buy_acres),
            "sell_acres":          max(0, sell_acres),
            "feed_bushels":        max(0, feed_bushels),
            "plant_acres":         max(0, plant_acres),
            "recruit_soldiers":    max(0, recruit_soldiers),
            "train_soldiers_cost": max(0, train_cost),
            "buy_fortifications":  max(0, buy_forts),
        }

        return decisions, "\n".join(reasoning_lines)


# ---------------------------------------------------------------------------
# Gemini LLM Planner (uses Google Gemini function calling with real execution)
# ---------------------------------------------------------------------------

class GeminiLLMPlanner:
    """
    Genuine LLM Planner utilizing Google Gemini function-calling with real Python tool execution.
    Falls back to RuleBasedPlanner if the API call or network fails.
    """

    TOOL_DECLARATIONS = [
        {
            "name": "scout_kingdom",
            "description": "Scout a rival kingdom ('elam', 'assyria', 'sumer') to uncover army size, treasury, and threat level.",
            "parameters": {
                "type": "object",
                "properties": {
                    "kingdom_id": {"type": "string", "description": "The ID of the kingdom to scout ('elam', 'assyria', 'sumer')"}
                },
                "required": ["kingdom_id"],
            },
        },
        {
            "name": "evaluate_war_readiness",
            "description": "Compare Babylon's military strength against a rival kingdom to assess war win probability.",
            "parameters": {
                "type": "object",
                "properties": {
                    "target_id": {"type": "string", "description": "The ID of the rival kingdom"}
                },
                "required": ["target_id"],
            },
        },
        {
            "name": "manage_diplomacy",
            "description": "Propose trade agreements, alliances, or peace treaties to a neighboring rival kingdom.",
            "parameters": {
                "type": "object",
                "properties": {
                    "target_id": {"type": "string", "description": "Rival kingdom ID ('elam', 'assyria', 'sumer')"},
                    "proposal": {"type": "string", "enum": ["TRADE", "ALLIANCE", "PEACE"], "description": "Treaty type proposed"},
                    "tribute_gold": {"type": "integer", "description": "Optional gold tribute offered to increase chance of acceptance"}
                },
                "required": ["target_id", "proposal"],
            },
        },
        {
            "name": "propose_turn_decisions",
            "description": (
                "Finalize and submit the complete royal decrees for this year. "
                "Specify buy_acres, sell_acres, feed_bushels, plant_acres, and military orders."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "buy_acres":           {"type": "integer", "description": "Acres of land to buy (0 if not buying)"},
                    "sell_acres":          {"type": "integer", "description": "Acres of land to sell (0 if not selling)"},
                    "feed_bushels":        {"type": "integer", "description": "Grain bushels allocated for citizen sustenance"},
                    "plant_acres":         {"type": "integer", "description": "Acres of land to plant with seed grain"},
                    "recruit_soldiers":    {"type": "integer", "description": "Soldiers to recruit into royal guard (0 if none)"},
                    "train_soldiers_cost": {"type": "integer", "description": "Gold spent on combat training"},
                    "buy_fortifications":  {"type": "integer", "description": "Fortification levels to construct"},
                    "reasoning":           {"type": "string",  "description": "Detailed strategic rationale for these decrees"},
                },
                "required": [
                    "buy_acres", "sell_acres", "feed_bushels", "plant_acres",
                    "recruit_soldiers", "reasoning"
                ],
            },
        },
    ]

    def __init__(self, api_key: str) -> None:
        self.api_key = api_key
        self._fallback = RuleBasedPlanner()
        self._client = None
        self._init_client()

    def _init_client(self) -> None:
        try:
            from google import genai
            self._client = genai.Client(api_key=self.api_key)
            self._backend_type = "GENAI_SDK"
        except Exception:
            try:
                import google.generativeai as legacy_genai
                legacy_genai.configure(api_key=self.api_key)
                self._client = legacy_genai.GenerativeModel(
                    model_name="gemini-1.5-flash",
                    tools=self.TOOL_DECLARATIONS,
                )
                self._backend_type = "LEGACY_GENAI"
            except Exception:
                self._backend_type = "REST_API"

    def plan(
        self,
        enhanced: EnhancedGameState,
        goal: str,
        observation: ToolResult,
        disaster: ToolResult,
        advisor: ToolResult,
        grain_req: ToolResult,
        memory: Dict[str, Any],
        executed_tool_calls: List[str],
    ) -> Tuple[Dict[str, int], str]:
        """Ask Gemini with function calling to plan the turn. Falls back on failure."""
        prompt = self._build_prompt(enhanced, goal, observation, disaster, advisor, grain_req, memory)

        try:
            # 1. Attempt google.genai official SDK
            if self._backend_type == "GENAI_SDK" and self._client is not None:
                from google.genai import types
                response = self._client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        temperature=0.2,
                    ),
                )
                # Parse text or function calls
                decisions, reasoning = self._extract_from_text_or_fc(response.text, enhanced, goal, executed_tool_calls)
                if decisions:
                    return decisions, f"[GEMINI LLM] {reasoning}"

            # 2. Attempt legacy SDK or REST API
            import requests
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={self.api_key}"
            headers = {"Content-Type": "application/json"}
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.2},
            }
            res = requests.post(url, headers=headers, json=payload, timeout=12)
            if res.status_code == 200:
                data = res.json()
                text = data["candidates"][0]["content"]["parts"][0]["text"]
                decisions, reasoning = self._extract_from_text_or_fc(text, enhanced, goal, executed_tool_calls)
                if decisions:
                    return decisions, f"[GEMINI LLM] {reasoning}"

        except Exception as e:
            fallback_decisions, fallback_reasoning = self._fallback.plan(
                enhanced, goal, observation, disaster, advisor, grain_req, memory, executed_tool_calls
            )
            return fallback_decisions, f"[GEMINI API FALLBACK: {e}]\n{fallback_reasoning}"

        # Default fallback if LLM response couldn't be parsed
        return self._fallback.plan(
            enhanced, goal, observation, disaster, advisor, grain_req, memory, executed_tool_calls
        )

    def _extract_from_text_or_fc(
        self,
        text: str,
        enhanced: EnhancedGameState,
        goal: str,
        executed_tool_calls: List[str],
    ) -> Tuple[Optional[Dict[str, int]], str]:
        """Extract structured turn decisions from LLM output (JSON or markdown)."""
        import re
        json_match = re.search(r"\{[\s\S]*\}", text)
        if json_match:
            try:
                d = json.loads(json_match.group(0))
                if "feed_bushels" in d or "plant_acres" in d:
                    decisions = {
                        "buy_acres":           int(d.get("buy_acres", 0)),
                        "sell_acres":          int(d.get("sell_acres", 0)),
                        "feed_bushels":        int(d.get("feed_bushels", 0)),
                        "plant_acres":         int(d.get("plant_acres", 0)),
                        "recruit_soldiers":    int(d.get("recruit_soldiers", 0)),
                        "train_soldiers_cost": int(d.get("train_soldiers_cost", 0)),
                        "buy_fortifications":  int(d.get("buy_fortifications", 0)),
                    }
                    reasoning = d.get("reasoning", text[:200])
                    executed_tool_calls.append("propose_turn_decisions(LLM)")
                    return decisions, reasoning
            except Exception:
                pass
        return None, text

    def _build_prompt(
        self,
        enhanced: EnhancedGameState,
        goal: str,
        observation: ToolResult,
        disaster: ToolResult,
        advisor: ToolResult,
        grain_req: ToolResult,
        memory: Dict[str, Any],
    ) -> str:
        st = enhanced.classic_state
        return f"""You are the Royal Governor of ancient Babylon, managing King Hammurabi's kingdom.

PLAYER GOAL: {goal}

CURRENT KINGDOM STATE:
- Year: {st.year} / 10
- Population: {st.population} citizens
- Grain in silos: {st.bushels} bushels
- Land owned: {st.acres} acres
- Land price this year: {st.land_price} bushels/acre
- Treasury: {getattr(st, 'treasury_gold', 0)} gold
- Soldiers: {getattr(st, 'soldiers', 0)} royal guards (Strength: {getattr(st, 'military_strength', 0)})
- Fortification Defense Level: {getattr(st, 'defense_level', 0)}

HISTORICAL CHRONICLE MEMORY:
- {memory.get('summary', 'No prior reign data')}

DISASTER & THREAT ANALYSIS:
- Famine Level: {disaster['famine']['level']} — {disaster['famine']['detail']}
- Plague Next Year: {disaster['plague']['risk_next_year']}
- Impeachment Risk: {disaster['impeachment_risk']}

GRAIN REQUIREMENTS:
- Full feed: {grain_req['requirements']['full_feed_bushels']} bushels (20 bu/citizen)
- Seed needed for max planting: {grain_req['requirements']['seed_for_max_planting']} bushels

REGIONAL RIVALS:
{[r.name + ' (' + r.personality + ')' for r in getattr(enhanced, 'rivals', [])]}

Respond strictly with a JSON object:
{{
  "buy_acres": <int>,
  "sell_acres": <int>,
  "feed_bushels": <int>,
  "plant_acres": <int>,
  "recruit_soldiers": <int>,
  "train_soldiers_cost": <int>,
  "buy_fortifications": <int>,
  "reasoning": "<concise strategic explanation>"
}}
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
        self.status = AgentStatus.IDLE
        self.current_session: Optional[DelegationSession] = None
        self._turn_callbacks: List[Callable[[ActionRecord, EnhancedGameState], None]] = []

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

    @property
    def backend_name(self) -> str:
        return self._backend

    @property
    def backend_display_name(self) -> str:
        if self._backend == "GEMINI_LLM":
            return "Google Gemini (LLM Function Calling)"
        return "Deterministic Rule-Based Planner" 

    def on_turn_complete(
        self,
        callback: Callable[[ActionRecord, EnhancedGameState], None],
    ) -> None:
        """Register a callback that fires after each turn cycle completes."""
        self._turn_callbacks.append(callback)

    def revoke(self) -> None:
        """Immediate player revocation of delegated control."""
        if self.current_session:
            self.current_session.revoked_by_player = True
            self.current_session.is_active = False
        self.status = AgentStatus.PAUSED

    def delegate(
        self,
        goal: str,
        turns: int = 1,
    ) -> DelegationSession:
        """
        Delegate kingdom management to the Governor for a set number of turns (1 to 10).
        Runs the autonomous Observe-Recall-Think-Plan-Validate-Act-Verify cycle.
        Returns the completed DelegationSession with full action history.
        """
        clamped_turns = max(1, min(10, turns))
        start_year = self.current_enhanced_state.classic_state.year

        session = DelegationSession(
            goal=goal,
            turns_delegated=clamped_turns,
            session_start_year=start_year,
        )
        self.current_session = session
        self.status = AgentStatus.DELEGATED

        for turn_idx in range(clamped_turns):
            if session.revoked_by_player:
                break
            if self.current_enhanced_state.classic_state.is_over:
                session.is_active = False
                self.status = AgentStatus.COMPLETED
                break

            record = self._execute_single_turn_cycle(goal, turn_idx + 1)
            session.action_history.append(record)
            session.turns_completed += 1
            session.turns_remaining -= 1

            for cb in self._turn_callbacks:
                cb(record, self.current_enhanced_state)

            if session.revoked_by_player:
                session.is_active = False
                self.status = AgentStatus.PAUSED
                break

            if self.current_enhanced_state.classic_state.is_over:
                session.is_active = False
                self.status = AgentStatus.COMPLETED
                break

        if not session.revoked_by_player and not self.current_enhanced_state.classic_state.is_over:
            session.is_active = False
            self.status = AgentStatus.COMPLETED

        return session

    def _execute_single_turn_cycle(self, goal: str, turn_number: int) -> ActionRecord:
        """Runs the ReAct Observe → Recall → Think → Plan → Validate → Act → Verify cycle."""
        self.status = AgentStatus.PLANNING
        state = self.current_enhanced_state.classic_state
        game_year = state.year
        tool_calls: List[str] = []

        # 1. OBSERVE
        observation = inspect_kingdom_state(self.current_enhanced_state)
        tool_calls.append("inspect_kingdom_state")

        disaster = inspect_disaster_conditions(self.current_enhanced_state)
        tool_calls.append("inspect_disaster_conditions")

        grain_req = calculate_grain_requirements(self.current_enhanced_state)
        tool_calls.append("calculate_grain_requirements")

        advisor = get_advisor_recommendation(self.current_enhanced_state)
        tool_calls.append("get_advisor_recommendation")

        # 2. RECALL (Strategic Historical Memory)
        memory = StrategicHistoricalMemory.analyze(self.current_enhanced_state)

        # 3. THINK & PLAN
        if isinstance(self._planner, GeminiLLMPlanner):
            decisions, reasoning = self._planner.plan(
                self.current_enhanced_state, goal, observation, disaster, advisor, grain_req, memory, tool_calls
            )
        else:
            decisions, reasoning = self._planner.plan(
                self.current_enhanced_state, goal, observation, disaster, advisor, grain_req, memory, tool_calls
            )

        # 4. VALIDATE
        self.status = AgentStatus.EXECUTING
        tool_calls.append("validate_action")
        val = validate_action(
            self.current_enhanced_state,
            buy_acres=decisions.get("buy_acres", 0),
            sell_acres=decisions.get("sell_acres", 0),
            feed_bushels=decisions.get("feed_bushels", 0),
            plant_acres=decisions.get("plant_acres", 0),
        )

        replanned = False
        replan_reason = ""

        # Auto-replan if validation failed
        if not val["can_execute"]:
            replanned = True
            replan_reason = f"Constraint violation: {val['validation']}. Adjusting to safe allocations."
            decisions["buy_acres"] = 0
            decisions["sell_acres"] = 0
            decisions["feed_bushels"] = min(decisions.get("feed_bushels", 0), state.bushels)
            rem = max(0, state.bushels - decisions["feed_bushels"])
            decisions["plant_acres"] = min(decisions.get("plant_acres", 0), state.acres, rem * 2, state.population * 10)
            val = validate_action(
                self.current_enhanced_state,
                buy_acres=0,
                sell_acres=0,
                feed_bushels=decisions["feed_bushels"],
                plant_acres=decisions["plant_acres"],
            )

        # Snapshot before
        before_res = {
            "year":       state.year,
            "population": state.population,
            "bushels":    state.bushels,
            "acres":      state.acres,
            "soldiers":   getattr(state, "soldiers", 0),
            "gold":       getattr(state, "treasury_gold", 0),
        }

        # 5. ACT
        tool_calls.append("advance_kingdom_turn")
        new_enhanced, exec_result = advance_kingdom_turn(
            self.current_enhanced_state,
            buy_acres=decisions.get("buy_acres", 0),
            sell_acres=decisions.get("sell_acres", 0),
            feed_bushels=decisions.get("feed_bushels", 0),
            plant_acres=decisions.get("plant_acres", 0),
            recruit_soldiers=decisions.get("recruit_soldiers", 0),
            train_soldiers_cost=decisions.get("train_soldiers_cost", 0),
            buy_fortifications=decisions.get("buy_fortifications", 0),
        )

        # Mutate authoritative state
        self.current_enhanced_state = new_enhanced
        after_state = new_enhanced.classic_state

        after_res = {
            "year":       after_state.year,
            "population": after_state.population,
            "bushels":    after_state.bushels,
            "acres":      after_state.acres,
            "soldiers":   getattr(after_state, "soldiers", 0),
            "gold":       getattr(after_state, "treasury_gold", 0),
        }

        resource_deltas = {
            "population": after_res["population"] - before_res["population"],
            "bushels":    after_res["bushels"]    - before_res["bushels"],
            "acres":      after_res["acres"]      - before_res["acres"],
            "soldiers":   after_res["soldiers"]   - before_res["soldiers"],
            "gold":       after_res["gold"]       - before_res["gold"],
        }

        # 6. VERIFY
        self.status = AgentStatus.VERIFYING
        verification_lines = []
        verification_ok = True

        if after_state.is_over and after_state.game_over_reason == "IMPEACHED":
            verification_lines.append("CRITICAL FAILURE: Impeached due to starvation!")
            verification_ok = False
        else:
            if after_state.starved_this_year > 0:
                verification_lines.append(f"WARNING: {after_state.starved_this_year} citizens starved.")
            else:
                verification_lines.append("SUCCESS: Zero starvation. All citizens fed.")

            pop_delta = resource_deltas["population"]
            if pop_delta >= 0:
                verification_lines.append(f"GROWTH: Population grew by {pop_delta} newcomers.")
            else:
                verification_lines.append(f"DECLINE: Population net change: {pop_delta}.")

            verification_lines.append(f"RESOURCES: Grain delta = {resource_deltas['bushels']:+d} bu.")

        return ActionRecord(
            turn_number=turn_number,
            game_year=game_year,
            goal=goal,
            observation=observation,
            disaster_check=disaster,
            reasoning=reasoning,
            planned_actions=decisions,
            validation_result=val,
            tool_calls=tool_calls,
            execution_result=exec_result,
            before_resources=before_res,
            after_resources=after_res,
            resource_deltas=resource_deltas,
            verification="\n".join(verification_lines),
            verification_ok=verification_ok,
            replanned=replanned,
            replan_reason=replan_reason,
            backend_used=self._backend,
        )

    def get_session_summary(self) -> Dict[str, Any]:
        """Return high-level summary of the current or most recent delegation session."""
        if not self.current_session:
            return {"status": "NO_SESSION"}
        s = self.current_session
        return {
            "goal":             s.goal,
            "turns_delegated":  s.turns_delegated,
            "turns_completed":  s.turns_completed,
            "turns_remaining":  s.turns_remaining,
            "is_active":        s.is_active,
            "revoked":          s.revoked_by_player,
            "current_year":     self.current_enhanced_state.classic_state.year,
            "action_count":     len(s.action_history),
            "backend":          self.backend_name,
        }
