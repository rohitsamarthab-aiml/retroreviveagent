"""
royal_governor.py - AI Royal Governor with Gemini LLM support.
"""
from __future__ import annotations
import json
import os
import time
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from game_logic import GameState, TurnDecisions
from modern_game_logic import EnhancedGameState, RivalKingdom, DiplomaticRelation
from agent_tools import *

try:
    import google.generativeai as genai
    HAS_LLM = True
except ImportError:
    HAS_LLM = False

class AgentStatus(str, Enum):
    IDLE, PLANNING, EXECUTING, VERIFYING, DELEGATED, PAUSED, COMPLETED, FAILED = "IDLE", "PLANNING", "EXECUTING", "VERIFYING", "DELEGATED", "PAUSED", "COMPLETED", "FAILED"

@dataclass
class ActionRecord:
    turn_number: int; game_year: int; goal: str; observation: Dict[str, Any]; disaster_check: Dict[str, Any]; reasoning: str; planned_actions: Dict[str, int]; validation_result: Dict[str, Any]; tool_calls: List[str]; execution_result: Dict[str, Any]; before_resources: Dict[str, int]; after_resources: Dict[str, int]; resource_deltas: Dict[str, int]; verification: str; verification_ok: bool; backend_used: str = "RULE_BASED"; timestamp: float = field(default_factory=time.time)

@dataclass
class DelegationSession:
    goal: str; turns_delegated: int; turns_completed: int = 0; turns_remaining: int = 0; is_active: bool = True; session_start_year: int = 1; action_history: List[ActionRecord] = field(default_factory=list)
    def __post_init__(self): self.turns_remaining = self.turns_delegated

class GeminiGovernor:
    def __init__(self, api_key: str):
        genai.configure(api_key=api_key); self.model = genai.GenerativeModel('gemini-1.5-flash')
    def generate_plan(self, prompt: str) -> Dict[str, Any]:
        try:
            res = self.model.generate_content(prompt, generation_config=genai.types.GenerationConfig(temperature=0.2, response_mime_type="application/json"))
            return json.loads(res.text)
        except Exception as e: return {"error": str(e)}

class RoyalGovernor:
    def __init__(self, enhanced_state: EnhancedGameState):
        self.current_enhanced_state = enhanced_state; self.status = AgentStatus.IDLE; self.backend_name = "RULE_BASED"
        self.api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        self.llm_engine = GeminiGovernor(self.api_key) if HAS_LLM and self.api_key else None
        if self.llm_engine: self.backend_name = "GEMINI_LLM"
    def delegate(self, goal: str, turns: int) -> DelegationSession:
        session = DelegationSession(goal=goal, turns_delegated=turns, session_start_year=self.current_enhanced_state.classic_state.year)
        self.current_session = session; self.status = AgentStatus.DELEGATED
        while session.is_active and session.turns_remaining > 0:
            self.execute_autonomous_turn()
            if self.status == AgentStatus.PAUSED: break
        return session
    def execute_autonomous_turn(self) -> ActionRecord:
        session = self.current_session; state = self.current_enhanced_state.classic_state
        obs, disaster, advisor, grain_req, rivals, history = inspect_kingdom_state(self.current_enhanced_state), inspect_disaster_conditions(self.current_enhanced_state), get_advisor_recommendation(self.current_enhanced_state), calculate_grain_requirements(self.current_enhanced_state), inspect_rival_kingdoms(self.current_enhanced_state), get_chronicle_summary(self.current_enhanced_state)
        if self.llm_engine:
            prompt = f"Goal: {session.goal}\nContext: {json.dumps({'obs': obs, 'rivals': rivals})}\nOutput JSON with 'reasoning' and 'actions' (buy_acres, sell_acres, feed_bushels, plant_acres, recruit_soldiers)."
            plan = self.llm_engine.generate_plan(prompt)
            actions = plan.get("actions", {"feed_bushels": state.population * 20, "plant_acres": state.acres})
            reasoning = plan.get("reasoning", "LLM strategy.")
        else:
            actions, reasoning = {"feed_bushels": state.population * 20, "plant_acres": min(state.acres, state.population * 10)}, "Rule-based strategy."
        before = {"pop": state.population, "grain": state.bushels}
        new_state, res = advance_kingdom_turn(self.current_enhanced_state, **actions)
        self.current_enhanced_state = new_state
        after = {"pop": new_state.classic_state.population, "grain": new_state.classic_state.bushels}
        rec = ActionRecord(session.turns_completed+1, state.year, session.goal, obs, disaster, reasoning, actions, {}, [], res, before, after, {}, "OK", True, self.backend_name)
        session.action_history.append(rec); session.turns_completed += 1; session.turns_remaining -= 1
        return rec
    def revoke(self):
        if hasattr(self, 'current_session'): self.current_session.is_active = False
        self.status = AgentStatus.PAUSED
