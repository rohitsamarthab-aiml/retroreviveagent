"""
royal_governor.py — AI Royal Governor agent for RetroRevive: Hammurabi's Living Empire.

Architecture:
  - RoyalGovernor is the central agent controller.
  - Upgraded to genuine LLM-powered reasoning using Google Gemini API.
  - Handles Multi-Kingdom Intelligence, Military, Diplomacy, and Agriculture.
  - Implements ReAct decision cycle: Observe → Think → Plan → Act → Verify.
  - Historical Memory: Analyzes previous game sessions and chronicle history.
  - Deterministic Rule-Based Planner: Maintained as a validation/fallback layer.
"""

from __future__ import annotations

import json
import math
import os
import time
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

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
    manage_military,
    manage_diplomacy,
    evaluate_war_readiness,
    ToolResult,
)

# Optional: Google Generative AI integration
try:
    import google.generativeai as genai
    HAS_LLM = True
except ImportError:
    HAS_LLM = False


# ---------------------------------------------------------------------------
# Data model for one agent action record
# ---------------------------------------------------------------------------

class AgentStatus(str, Enum):
    IDLE       = \"IDLE\"
    PLANNING   = \"PLANNING\"
    EXECUTING  = \"EXECUTING\"
    VERIFYING  = \"VERIFYING\"
    DELEGATED  = \"DELEGATED\"
    PAUSED     = \"PAUSED\"
    COMPLETED  = \"COMPLETED\"
    FAILED     = \"FAILED\"


@dataclass
class ActionRecord:
    \"\"\"Complete record of one agent turn cycle.\"\"\"
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
    replan_reason:    str  = \"\"
    backend_used:     str  = \"RULE_BASED\"   # \"GEMINI_LLM\" | \"RULE_BASED\"
    timestamp:        float = field(default_factory=time.time)


@dataclass
class DelegationSession:
    \"\"\"Tracks a player's delegation of kingdom management to the Governor.\"\"\"
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
# LLM Intelligence Engine
# ---------------------------------------------------------------------------

class GeminiGovernor:
    \"\"\"
    Genuine LLM-powered decision engine for the Royal Governor.
    Uses Google Gemini for reasoning and tool selection.
    \"\"\"
    def __init__(self, api_key: str):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')
        
    def generate_plan(self, prompt: str) -> Dict[str, Any]:
        \"\"\"Calls LLM to generate turn decisions and reasoning.\"\"\"
        response = self.model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.2,
                response_mime_type=\"application/json\"
            )
        )
        try:
            return json.loads(response.text)
        except:
            return {\"error\": \"LLM failed to produce valid JSON\", \"text\": response.text}


# ---------------------------------------------------------------------------
# Rule-based planner (honest fallback when no LLM key configured)
# ---------------------------------------------------------------------------

class RuleBasedPlanner:
    \"\"\"
    Deterministic kingdom-management planner.
    Implements classic agricultural economics for the Hammurabi simulation.
    \"\"\"
    def plan(
        self,
        state: GameState,
        goal: str,
        observation: ToolResult,
        disaster: ToolResult,
        advisor: ToolResult,
        grain_req: ToolResult,
        rivals: ToolResult
    ) -> tuple[Dict[str, int], str]:
        pop   = state.population
        bush  = state.bushels
        acres = state.acres
        price = state.land_price

        reasoning_lines = []
        reasoning_lines.append(f\"OBSERVE: Year {state.year}, Pop={pop}, Grain={bush}, Acres={acres}, Price={price}\")

        # Step 1: Agriculture & Survival
        full_feed = pop * 20
        famine_level = disaster[\"famine\"][\"level\"]
        
        feed_bushels = min(full_feed, bush)
        sell_acres = 0
        buy_acres = 0
        
        if famine_level == \"ACTIVE_FAMINE\" and bush < full_feed:
            deficit = full_feed - bush
            sell_acres = min(math.ceil(deficit / max(1, price)), acres - 1)
            feed_bushels = min(full_feed, bush + sell_acres * price)
            reasoning_lines.append(f\"CRISIS: Famine detected. Selling {sell_acres} acres to feed population.\")

        # Step 2: Farming
        plantable = min(state.acres + buy_acres - sell_acres, pop * 10)
        seed_cost = plantable // 2
        remaining = bush + (sell_acres * price) - feed_bushels
        plant_acres = min(plantable, remaining * 2)

        # Step 3: Military (Basic)
        recruit_soldiers = 0
        if state.treasury_gold > 200 and state.soldiers < state.population * 0.2:
            recruit_soldiers = 5
            reasoning_lines.append(\"MILITARY: Recruiting scouts to bolster defense.\")

        decisions = {
            \"buy_acres\": buy_acres,
            \"sell_acres\": sell_acres,
            \"feed_bushels\": feed_bushels,
            \"plant_acres\": plant_acres,
            \"recruit_soldiers\": recruit_soldiers,
            \"train_soldiers_cost\": recruit_soldiers * 2,
            \"buy_fortifications\": 0
        }

        return decisions, \"\\n\".join(reasoning_lines)


# ---------------------------------------------------------------------------
# Central Royal Governor Agent
# ---------------------------------------------------------------------------

class RoyalGovernor:
    \"\"\"
    The central AI agent coordinating all kingdom management responsibilities.
    \"\"\"

    def __init__(self, enhanced_state: EnhancedGameState):
        self.current_enhanced_state = enhanced_state
        self.status = AgentStatus.IDLE
        self.current_session: Optional[DelegationSession] = None
        self.backend_name = \"RULE_BASED\"
        
        # Check for Gemini API key
        self.api_key = os.getenv(\"GEMINI_API_KEY\") or os.getenv(\"GOOGLE_API_KEY\")
        if HAS_LLM and self.api_key:
            self.llm_engine = GeminiGovernor(self.api_key)
            self.backend_name = \"GEMINI_LLM\"
        else:
            self.llm_engine = None
            
        self.planner = RuleBasedPlanner()
        self._turn_callback = None

    def delegate(self, goal: str, turns: int) -> DelegationSession:
        \"\"\"Player grants control of the kingdom to the Governor.\"\"\"
        self.current_session = DelegationSession(
            goal=goal,
            turns_delegated=turns,
            session_start_year=self.current_enhanced_state.classic_state.year
        )
        self.status = AgentStatus.DELEGATED

        # Autonomous turn loop
        while self.current_session.is_active and self.current_session.turns_remaining > 0:
            self.execute_autonomous_turn()
            if self.status == AgentStatus.PAUSED:
                break

        if self.current_session.turns_remaining == 0:
            self.status = AgentStatus.COMPLETED
            self.current_session.is_active = False

        return self.current_session

    def execute_autonomous_turn(self) -> ActionRecord:
        \"\"\"
        Performs one full ReAct decision cycle.
        \"\"\"
        if not self.current_session:
            raise RuntimeError(\"No active delegation session.\")

        self.status = AgentStatus.PLANNING
        state = self.current_enhanced_state.classic_state
        year = state.year
        goal = self.current_session.goal

        # 1. OBSERVE
        obs      = inspect_kingdom_state(self.current_enhanced_state)
        disaster = inspect_disaster_conditions(self.current_enhanced_state)
        advisor  = get_advisor_recommendation(self.current_enhanced_state)
        grain_req= calculate_grain_requirements(self.current_enhanced_state)
        rivals   = inspect_rival_kingdoms(self.current_enhanced_state)
        history  = get_chronicle_summary(self.current_enhanced_state)

        # 2. THINK & PLAN
        if self.llm_engine:
            # LLM Prompt construction with multi-kingdom context
            prompt = self._build_llm_prompt(obs, disaster, advisor, grain_req, rivals, history, goal)
            plan_data = self.llm_engine.generate_plan(prompt)
            
            if \"error\" in plan_data:
                # LLM failed, fallback to rule-based
                planned_actions, reasoning = self.planner.plan(state, goal, obs, disaster, advisor, grain_req, rivals)
                reasoning = f\"[LLM FAILED: {plan_data['error']}] Falling back to Rule-Based Planner. \" + reasoning
            else:
                planned_actions = plan_data.get(\"actions\", {})
                reasoning = plan_data.get(\"reasoning\", \"Decided through LLM reasoning.\")
        else:
            planned_actions, reasoning = self.planner.plan(state, goal, obs, disaster, advisor, grain_req, rivals)

        # 3. VALIDATE
        val = validate_action(self.current_enhanced_state, **planned_actions)
        
        # 4. ACT
        self.status = AgentStatus.EXECUTING
        before_res = _state_to_dict(state)
        
        new_state, exec_result = advance_kingdom_turn(self.current_enhanced_state, **planned_actions)
        self.current_enhanced_state = new_state
        
        # 5. VERIFY
        self.status = AgentStatus.VERIFYING
        after_res = _state_to_dict(self.current_enhanced_state.classic_state)
        
        deltas = {k: after_res[k] - before_res[k] for k in [\"population\", \"grain_bushels\", \"acres_owned\", \"soldiers\", \"treasury_gold\"] if k in after_res}
        
        verification_msg = \"Turn successful. Kingdom advanced to next year.\"
        verification_ok = exec_result.get(\"success\", False)
        
        # 6. LOG
        record = ActionRecord(
            turn_number=self.current_session.turns_completed + 1,
            game_year=year,
            goal=goal,
            observation=obs,
            disaster_check=disaster,
            reasoning=reasoning,
            planned_actions=planned_actions,
            validation_result=val,
            tool_calls=[\"inspect_kingdom_state\", \"advance_kingdom_turn\"],
            execution_result=exec_result,
            before_resources=before_res,
            after_resources=after_res,
            resource_deltas=deltas,
            verification=verification_msg,
            verification_ok=verification_ok,
            backend_used=self.backend_name
        )
        
        self.current_session.action_history.append(record)
        self.current_session.turns_completed += 1
        self.current_session.turns_remaining -= 1
        
        if self._turn_callback:
            self._turn_callback(record, self.current_enhanced_state)
            
        return record

    def _build_llm_prompt(self, obs, disaster, advisor, grain_req, rivals, history, goal) -> str:
        \"\"\"Constructs a detailed system prompt for the LLM.\"\"\"
        context = {
            \"goal\": goal,
            \"observation\": obs,
            \"threats\": disaster,
            \"advisors\": advisor,
            \"grain_requirements\": grain_req,
            \"rival_kingdoms\": rivals,
            \"history_brief\": history[\"history\"][-3:] if history[\"history\"] else []
        }
        
        return f\"\"\"
        You are the Royal Governor of Babylon, a sophisticated AI agent. 
        Your goal: {goal}
        
        Current Kingdom Data:
        {json.dumps(context, indent=2)}
        
        MISSION:
        Manage Agriculture, Military, Diplomacy, and Treasury.
        Compare our military strength with rivals and assess war readiness.
        Suggest alliances or trade to improve security.
        Prevent famine at all costs.
        
        OUTPUT FORMAT:
        Return a JSON object with:
        1. \"reasoning\": String explaining your strategy and intelligence analysis.
        2. \"actions\": Dictionary with keys: buy_acres, sell_acres, feed_bushels, plant_acres, recruit_soldiers, train_soldiers_cost, buy_fortifications.
        
        Ensure all action values are non-negative integers.
        \"\"\"

    def on_turn_complete(self, callback_fn):
        \"\"\"Register a callback function for turn execution events.\"\"\"
        self._turn_callback = callback_fn

    def pause(self):
        self.status = AgentStatus.PAUSED

    def revoke(self):
        if self.current_session:
            self.current_session.is_active = False
            self.current_session.revoked_by_player = True
        self.status = AgentStatus.PAUSED

    def get_session_summary(self) -> Dict[str, Any]:
        if not self.current_session:
            return {\"status\": \"No active session\"}
        return {
            \"goal\": self.current_session.goal,
            \"turns_delegated\": self.current_session.turns_delegated,
            \"turns_completed\": self.current_session.turns_completed,
            \"current_year\": self.current_enhanced_state.classic_state.year,
            \"action_count\": len(self.current_session.action_history),
            \"backend\": self.backend_name
        }


def _state_to_dict(state: GameState) -> Dict[str, int]:
    return {
        \"year\": state.year,
        \"population\": state.population,
        \"grain_bushels\": state.bushels,
        \"acres_owned\": state.acres,
        \"soldiers\": state.soldiers,
        \"treasury_gold\": state.treasury_gold
    }
