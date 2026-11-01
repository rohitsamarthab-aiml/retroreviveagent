"""
agent_tools.py - Refined tools for AI Governor.
"""
from __future__ import annotations
import math
from typing import Any, Dict, List, Optional
from game_logic import *
from modern_game_logic import *

ToolResult = Dict[str, Any]

def _state_to_dict(state: GameState) -> Dict[str, Any]:
    return {"year": state.year, "population": state.population, "grain": state.bushels, "acres": state.acres, "soldiers": state.soldiers, "strength": state.military_strength, "gold": state.treasury_gold}

def inspect_kingdom_state(enhanced: EnhancedGameState) -> ToolResult:
    return {"success": True, "state": _state_to_dict(enhanced.classic_state)}

def calculate_grain_requirements(enhanced: EnhancedGameState) -> ToolResult:
    s = enhanced.classic_state
    return {"success": True, "requirements": {"feed": s.population * 20, "seed": (min(s.acres, s.population * 10)) // 2}}

def validate_action(enhanced: EnhancedGameState, **kwargs) -> ToolResult:
    s = enhanced.classic_state
    v = all([validate_buy_land(s, kwargs.get("buy_acres", 0)).is_valid, validate_feed_people(s, kwargs.get("feed_bushels", 0)).is_valid, validate_plant_seed(s, kwargs.get("plant_acres", 0), kwargs.get("feed_bushels", 0)).is_valid])
    return {"success": True, "all_valid": v, "can_execute": v}

def advance_kingdom_turn(enhanced: EnhancedGameState, **kwargs) -> tuple[EnhancedGameState, ToolResult]:
    d = TurnDecisions(buy_acres=kwargs.get("buy_acres",0), sell_acres=kwargs.get("sell_acres",0), feed_bushels=kwargs.get("feed_bushels",0), plant_acres=kwargs.get("plant_acres",0), recruit_soldiers=kwargs.get("recruit_soldiers",0), train_soldiers_cost=kwargs.get("train_soldiers_cost",0), buy_fortifications=kwargs.get("buy_fortifications",0))
    n = step_enhanced_year(enhanced, d)
    return n, {"success": True, "after": _state_to_dict(n.classic_state)}

def inspect_rival_kingdoms(enhanced: EnhancedGameState) -> ToolResult:
    data = []
    for r in enhanced.rivals:
        rel = next((d for d in enhanced.diplomacy if d.rival_id == r.id), None)
        data.append({"name": r.name, "status": rel.status if rel else "UNKNOWN", "power": "CONFIRMED" if rel and rel.intelligence_level > 50 else "ESTIMATED", "strength": r.military_strength})
    return {"success": True, "kingdoms": data}

def evaluate_war_readiness(enhanced: EnhancedGameState, target_id: str) -> ToolResult:
    r = next((k for k in enhanced.rivals if k.id == target_id), None)
    if not r: return {"success": False}
    s = enhanced.classic_state
    req_soldiers = int(r.soldiers * 1.2)
    req_grain = req_soldiers * 20
    return {"success": True, "analysis": {"power_ratio": round(s.military_strength/max(1,r.military_strength), 2), "req_soldiers": req_soldiers, "req_grain": req_grain, "readiness": "READY" if s.soldiers >= req_soldiers else "NOT READY"}}

def manage_diplomacy(enhanced, target_id, proposal):
    return {"success": True, "accepted": True}

def inspect_disaster_conditions(enhanced):
    return {"success": True, "famine": "SAFE"}

def get_advisor_recommendation(enhanced):
    return {"success": True, "advice": "Maintain stability."}

def get_chronicle_summary(enhanced):
    return {"success": True, "history": []}
