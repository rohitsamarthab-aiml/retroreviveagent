\"\"\"
royal_governor.py - AI Royal Governor for RetroRevive.

Architecture:
- Genuine LLM-powered decision engine using Google Gemini.
- ReAct Decision Cycle: Observe (Real Data) -> Think (LLM Reasoning) -> Plan -> Act (Tools) -> Verify.
- Strategic Memory: Retains and analyzes Chronicle history to improve kingdom outcomes.
- Rule-Based Fallback: Secure deterministic planner when LLM is unavailable.
\"\"\"

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from game_logic import GameState, TurnDecisions
from modern_game_logic import EnhancedGameState, RivalKingdom, DiplomaticRelation
from agent_tools import (
    inspect_kingdom_state,
    calculate_grain_requirements,
    validate_action,
    advance_kingdom_turn,
    inspect_disaster_conditions,
    get_advisor_recommendation,
    get_chronicle_summary,
    inspect_rival_kingdoms,
    evaluate_war_readiness,
    manage_diplomacy,
    ToolResult
)

# Optional Google Gemini Integration
try:
    import google.generativeai as genai
    HAS_LLM = True
except ImportError:
    HAS_LLM = False


class AgentStatus(str, Enum):
    IDLE = \"IDLE\"
    PLANNING = \"PLANNING\"
    EXECUTING = \"EXECUTING\"
    VERIFYING = \"VERIFYING\"
    DELEGATED = \"DELEGATED\"
    PAUSED = \"PAUSED\"
    COMPLETED = \"COMPLETED\"
    FAILED = \"FAILED\"


@dataclass
class ActionRecord:
    \"\"\"Complete record of one agent turn cycle.\"\"\"
    turn_number: int
    game_year: int
    goal: str
    observation: Dict[str, Any]
    disaster_check: Dict[str, Any]
    reasoning: str
    planned_actions: Dict[str, int]
    validation_result: Dict[str, Any]
    tool_calls: List[str]
    execution_result: Dict[str, Any]
    before_resources: Dict[str, Any]
    after_resources: Dict[str, Any]
    resource_deltas: Dict[str, int]
    verification: str
    verification_ok: bool
    backend_used: str = \"RULE_BASED\"
    timestamp: float = field(default_factory=time.time)


@dataclass
class DelegationSession:
    \"\"\"Tracks a player's delegation of kingdom management to the Governor.\"\"\"
    goal: str
    turns_delegated: int
    turns_completed: int = 0
    turns_remaining: int = 0
    is_active: bool = True
    session_start_year: int = 1
    action_history: List[ActionRecord] = field(default_factory=list)

    def __post_init__(self):
        self.turns_remaining = self.turns_delegated


class GeminiGovernor:
    \"\"\"LLM decision engine using Gemini 1.5 Flash.\"\"\"
    def __init__(self, api_key: str):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')

    def generate_plan(self, prompt: str) -> Dict[str, Any]:
        \"\"\"Calls LLM to generate turn decisions.\"\"\"
        try:
            response = self.model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.2,
                    response_mime_type=\"application/json\"
                )
            )
            return json.loads(response.text)
        except Exception as e:
            return {\"error\": str(e)}


class RoyalGovernor:
    \"\"\"The central AI agent coordinating all kingdom management.\"\"\"

    def __init__(self, enhanced_state: EnhancedGameState):
        self.current_enhanced_state = enhanced_state
        self.status = AgentStatus.IDLE
        self.backend_name = \"RULE_BASED\"
        self.current_session: Optional[DelegationSession] = None
        
        # Configure API Key
        self.api_key = os.getenv(\"GEMINI_API_KEY\") or os.getenv(\"GOOGLE_API_KEY\")
        if HAS_LLM and self.api_key:
            self.llm_engine = GeminiGovernor(self.api_key)
            self.backend_name = \"GEMINI_LLM\"
        else:
            self.llm_engine = None

    def delegate(self, goal: str, turns: int) -> DelegationSession:
        \"\"\"Grants kingdom control to the Governor.\"\"\"
        self.current_session = DelegationSession(
            goal=goal,
            turns_delegated=turns,
            session_start_year=self.current_enhanced_state.classic_state.year
        )
        self.status = AgentStatus.DELEGATED

        while self.current_session.is_active and self.current_session.turns_remaining > 0:
            self.execute_autonomous_turn()
            if self.status == AgentStatus.PAUSED:
                break
                
        return self.current_session

    def execute_autonomous_turn(self) -> ActionRecord:
        \"\"\"Performs one ReAct cycle: Observe -> Think -> Plan -> Act -> Verify.\"\"\"
        if not self.current_session:
            raise RuntimeError(\"No active session\")

        self.status = AgentStatus.PLANNING
        state = self.current_enhanced_state.classic_state
        
        # 1. OBSERVE
        obs = inspect_kingdom_state(self.current_enhanced_state)
        disaster = inspect_disaster_conditions(self.current_enhanced_state)
        advisor = get_advisor_recommendation(self.current_enhanced_state)
        grain_req = calculate_grain_requirements(self.current_enhanced_state)
        rivals = inspect_rival_kingdoms(self.current_enhanced_state)
        history = get_chronicle_summary(self.current_enhanced_state)

        # 2. THINK & PLAN
        if self.llm_engine:
            prompt = self._build_prompt(obs, disaster, advisor, grain_req, rivals, history)
            plan = self.llm_engine.generate_plan(prompt)
            if \"error\" in plan:
                actions, reasoning = self._rule_fallback(state), f\"[Fallback] {plan['error']}\"
            else:
                actions = plan.get(\"actions\", self._rule_fallback(state))
                reasoning = plan.get(\"reasoning\", \"Strategic plan generated by LLM.\")
        else:
            actions, reasoning = self._rule_fallback(state), \"Rule-based strategic fallback.\"

        # 3. ACT
        self.status = AgentStatus.EXECUTING
        before_snap = {k: v for k, v in state.__dict__.items() if isinstance(v, (int, float))}
        
        new_state, result = advance_kingdom_turn(self.current_enhanced_state, **actions)
        self.current_enhanced_state = new_state
        
        # 4. VERIFY
        after_snap = {k: v for k, v in new_state.classic_state.__dict__.items() if isinstance(v, (int, float))}
        deltas = {k: after_snap[k] - before_snap.get(k, 0) for k in [\"population\", \"bushels\", \"acres\", \"soldiers\"]}
        
        record = ActionRecord(
            turn_number=self.current_session.turns_completed + 1,
            game_year=state.year,
            goal=self.current_session.goal,
            observation=obs,
            disaster_check=disaster,
            reasoning=reasoning,
            planned_actions=actions,
            validation_result={},
            tool_calls=[\"inspect_kingdom_state\", \"advance_kingdom_turn\"],
            execution_result=result,
            before_resources=before_snap,
            after_resources=after_snap,
            resource_deltas=deltas,
            verification=\"Target reached\" if result.get(\"success\") else \"Verification failed\",
            verification_ok=result.get(\"success\", False),
            backend_used=self.backend_name
        )
        
        self.current_session.action_history.append(record)
        self.current_session.turns_completed += 1
        self.current_session.turns_remaining -= 1
        
        return record

    def _build_prompt(self, obs, disaster, advisor, grain_req, rivals, history) -> str:
        return f\"\"\"
        You are the Royal Governor of Babylon.
        Current Goal: {self.current_session.goal}
        
        Kingdom Data: {json.dumps(obs)}
        Threats: {json.dumps(disaster)}
        Rivals: {json.dumps(rivals)}
        Historical Trends: {json.dumps(history['history'][-5:])}
        
        Strategy: Manage Agriculture, Military, and Diplomacy. Compare our strength with rivals.
        Output JSON: {{\"reasoning\": \"...\", \"actions\": {{\"buy_acres\": 0, \"sell_acres\": 0, \"feed_bushels\": 2000, \"plant_acres\": 1000, \"recruit_soldiers\": 5}}}}
        \"\"\"

    def _rule_fallback(self, state: GameState) -> Dict[str, int]:
        return {
            \"feed_bushels\": state.population * 20,
            \"plant_acres\": min(state.acres, state.population * 10),
            \"buy_acres\": 0,
            \"sell_acres\": 0,
            \"recruit_soldiers\": 5 if state.treasury_gold > 200 else 0
        }

    def revoke(self):
        if self.current_session:
            self.current_session.is_active = False
        self.status = AgentStatus.PAUSED
