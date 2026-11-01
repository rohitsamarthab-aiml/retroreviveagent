"""
agent_tools.py - Expanded tools for AI Governor.
"""
from __future__ import annotations
import math
from dataclasses import asdict
from typing import Any, Dict, List, Optional
from game_logic import (
    GameState, TurnDecisions, ValidationResult, validate_buy_land,
    validate_feed_people, validate_plant_seed, validate_sell_land,
    step_year, DefaultRNG
)
from modern_game_logic import (
    EnhancedGameState, AdvisorAdvice, get_advisor_advice, step_enhanced_year
)

ToolResult = Dict[str, Any]

def _state_to_dict(state: GameState) -> Dict[str, Any]:
    return {
        "year": state.year, "population": state.population, "grain_bushels": state.bushels,
        "acres_owned": state.acres, "land_price_per_acre": state.land_price,
        "starved_this_year": state.starved_this_year, "starved_total_all_years": state.starved_total,
        "avg_starvation_pct": round(state.starved_pct_avg, 2), "immigrants_this_year": state.immigrants_this_year,
        "harvest_yield_per_acre": state.harvest_yield, "grain_eaten_by_rats": state.rats_ate,
        "plague_struck_this_year": state.plague_struck, "plague_risk_next_year": state.plague_next_year,
        "game_is_over": state.is_over, "game_over_reason": state.game_over_reason,
        "soldiers": state.soldiers, "military_strength": state.military_strength,
        "treasury_gold": state.treasury_gold, "defense_level": state.defense_level,
    }

def inspect_kingdom_state(enhanced: EnhancedGameState) -> ToolResult:
    state = enhanced.classic_state
    return {"tool": "inspect_kingdom_state", "success": True, "state": _state_to_dict(state)}

def calculate_grain_requirements(enhanced: EnhancedGameState) -> ToolResult:
    state = enhanced.classic_state
    return {
        "tool": "calculate_grain_requirements", "success": True,
        "requirements": {"full_feed_bushels": state.population * 20, "seed_needed": (min(state.acres, state.population * 10)) // 2}
    }

def validate_action(enhanced: EnhancedGameState, **kwargs) -> ToolResult:
    state = enhanced.classic_state
    res_buy = validate_buy_land(state, kwargs.get("buy_acres", 0))
    res_sell = validate_sell_land(state, kwargs.get("sell_acres", 0))
    res_feed = validate_feed_people(state, kwargs.get("feed_bushels", 0))
    res_plant = validate_plant_seed(state, kwargs.get("plant_acres", 0))
    all_valid = all([res_buy.is_valid, res_sell.is_valid, res_feed.is_valid, res_plant.is_valid])
    return {"tool": "validate_action", "success": True, "all_valid": all_valid, "can_execute": all_valid}

def advance_kingdom_turn(enhanced: EnhancedGameState, **kwargs) -> tuple[EnhancedGameState, ToolResult]:
    decisions = TurnDecisions(
        buy_acres=kwargs.get("buy_acres", 0), sell_acres=kwargs.get("sell_acres", 0),
        feed_bushels=kwargs.get("feed_bushels", 0), plant_acres=kwargs.get("plant_acres", 0),
        recruit_soldiers=kwargs.get("recruit_soldiers", 0), train_soldiers_cost=kwargs.get("train_soldiers_cost", 0),
        buy_fortifications=kwargs.get("buy_fortifications", 0)
    )
    new_enhanced = step_enhanced_year(enhanced, decisions)
    return new_enhanced, {"tool": "advance_kingdom_turn", "success": True, "after": _state_to_dict(new_enhanced.classic_state)}

def inspect_rival_kingdoms(enhanced: EnhancedGameState) -> ToolResult:
    rivals_data = []
    for rival in enhanced.rivals:
        rel = next((d for d in enhanced.diplomacy if d.rival_id == rival.id), None)
        rivals_data.append({"id": rival.id, "name": rival.name, "status": rel.status if rel else "UNKNOWN", "power": rival.military_strength})
    return {"tool": "inspect_rival_kingdoms", "success": True, "kingdoms": rivals_data}

def evaluate_war_readiness(enhanced: EnhancedGameState, target_id: str) -> ToolResult:
    rival = next((r for r in enhanced.rivals if r.id == target_id), None)
    if not rival: return {"success": False}
    ratio = enhanced.classic_state.military_strength / max(1, rival.military_strength)
    return {"tool": "evaluate_war_readiness", "success": True, "power_ratio": round(ratio, 2)}

def manage_diplomacy(enhanced: EnhancedGameState, target_id: str, proposal: str) -> ToolResult:
    rival = next((r for r in enhanced.rivals if r.id == target_id), None)
    if not rival: return {"success": False}
    return {"tool": "manage_diplomacy", "success": True, "target": rival.name, "accepted": True}

def inspect_disaster_conditions(enhanced: EnhancedGameState) -> ToolResult:
    state = enhanced.classic_state
    return {"tool": "inspect_disaster_conditions", "success": True, "famine": {"level": "SAFE" if state.bushels >= state.population * 20 else "WARNING"}}

def get_advisor_recommendation(enhanced: EnhancedGameState) -> ToolResult:
    return {"tool": "get_advisor_recommendation", "success": True, "advisor_recommendations": asdict(get_advisor_advice(enhanced.classic_state))}

def get_chronicle_summary(enhanced: EnhancedGameState) -> ToolResult:
    return {"tool": "get_chronicle_summary", "success": True, "history": [asdict(e) for e in enhanced.chronicle]}
