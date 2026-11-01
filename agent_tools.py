\"\"\"
agent_tools.py - Comprehensive tool suite for the LLM Royal Governor.

Exposes authoritative game-engine functions to the AI agent for:
- Kingdom inspection and analytics
- Rival kingdom intelligence and scouting
- Military readiness and war assessment
- Diplomatic relations and proposals
- Strategic planning and turn advancement
\"\"\"

from __future__ import annotations

import math
from dataclasses import asdict
from typing import Any, Dict, List, Optional

from game_logic import (
    GameState,
    TurnDecisions,
    ValidationResult,
    validate_buy_land,
    validate_feed_people,
    validate_plant_seed,
    validate_sell_land,
    step_year,
    DefaultRNG,
)
from modern_game_logic import (
    EnhancedGameState,
    AdvisorAdvice,
    get_advisor_advice,
    step_enhanced_year,
    RivalKingdom,
    DiplomaticRelation,
)

# ---------------------------------------------------------------------------
# Type alias for tool return values: always a plain dict (JSON-serialisable)
# ---------------------------------------------------------------------------
ToolResult = Dict[str, Any]


def _state_to_dict(state: GameState) -> Dict[str, Any]:
    \"\"\"Convert GameState dataclass to plain dict with human-readable keys.\"\"\"
    return {
        \"year\": state.year,
        \"population\": state.population,
        \"grain_bushels\": state.bushels,
        \"acres_owned\": state.acres,
        \"land_price_per_acre\": state.land_price,
        \"starved_this_year\": state.starved_this_year,
        \"starved_total_all_years\": state.starved_total,
        \"avg_starvation_pct\": round(state.starved_pct_avg, 2),
        \"immigrants_this_year\": state.immigrants_this_year,
        \"harvest_yield_per_acre\": state.harvest_yield,
        \"grain_eaten_by_rats\": state.rats_ate,
        \"plague_struck_this_year\": state.plague_struck,
        \"plague_risk_next_year\": state.plague_next_year,
        \"game_is_over\": state.is_over,
        \"game_over_reason\": state.game_over_reason,
        \"soldiers\": state.soldiers,
        \"military_strength\": state.military_strength,
        \"treasury_gold\": state.treasury_gold,
        \"defense_level\": state.defense_level,
        \"territory_influence\": round(state.territory_influence, 2),
    }


# ---------------------------------------------------------------------------
# KINGDOM MANAGEMENT TOOLS
# ---------------------------------------------------------------------------

def inspect_kingdom_state(enhanced: EnhancedGameState) -> ToolResult:
    \"\"\"Read the complete current kingdom state and derived analytics.\"\"\"
    state = enhanced.classic_state
    state_dict = _state_to_dict(state)

    # Derived analytics
    grain_per_person = state.bushels / max(1, state.population)
    acres_per_person = state.acres / max(1, state.population)
    labor_capacity   = state.population * 10
    seed_for_all     = state.acres // 2

    return {
        \"tool\": \"inspect_kingdom_state\",
        \"success\": True,
        \"state\": state_dict,
        \"analytics\": {
            \"grain_per_person\": round(grain_per_person, 1),
            \"acres_per_person\": round(acres_per_person, 2),
            \"max_plantable_acres\": labor_capacity,
            \"bushels_to_plant_all\": seed_for_all,
            \"famine_risk\": \"CRITICAL\" if state.bushels < state.population * 20 else \"HIGH\" if state.bushels < state.population * 30 else \"LOW\",
        },
        \"mode\": enhanced.mode,
    }


def calculate_grain_requirements(enhanced: EnhancedGameState) -> ToolResult:
    \"\"\"Compute exact grain allocations needed based on population and land.\"\"\"
    state = enhanced.classic_state
    full_feed = state.population * 20
    labor_limit = state.population * 10
    plant_target = min(state.acres, labor_limit)
    seed_needed = plant_target // 2

    return {
        \"tool\": \"calculate_grain_requirements\",
        \"success\": True,
        \"requirements\": {
            \"full_feed_bushels\": full_feed,
            \"seed_for_max_planting\": seed_needed,
            \"max_plantable_acres\": plant_target,
        },
        \"can_fully_feed\": state.bushels >= full_feed
    }


def validate_action(enhanced: EnhancedGameState, **kwargs) -> ToolResult:
    \"\"\"Run game engine validation on proposed decisions.\"\"\"
    state = enhanced.classic_state
    
    # Run core engine validators
    res_buy   = validate_buy_land(state, kwargs.get(\"buy_acres\", 0))
    res_sell  = validate_sell_land(state, kwargs.get(\"sell_acres\", 0))
    res_feed  = validate_feed_people(state, kwargs.get(\"feed_bushels\", 0))
    res_plant = validate_plant_seed(state, kwargs.get(\"plant_acres\", 0))
    
    validation_map = {
        \"buy_land\": {\"valid\": res_buy.is_valid, \"msg\": res_buy.message},
        \"sell_land\": {\"valid\": res_sell.is_valid, \"msg\": res_sell.message},
        \"feed_people\": {\"valid\": res_feed.is_valid, \"msg\": res_feed.message},
        \"plant_fields\": {\"valid\": res_plant.is_valid, \"msg\": res_plant.message}
    }

    all_valid = all(v[\"valid\"] for v in validation_map.values())
    return {
        \"tool\": \"validate_action\",
        \"success\": True,
        \"all_valid\": all_valid,
        \"validation\": validation_map,
        \"can_execute\": all_valid
    }


def advance_kingdom_turn(enhanced: EnhancedGameState, **kwargs) -> tuple[EnhancedGameState, ToolResult]:
    \"\"\"AUTHORITATIVE: Commit decrees and advance the world by one year.\"\"\"
    decisions = TurnDecisions(
        buy_acres=kwargs.get(\"buy_acres\", 0),
        sell_acres=kwargs.get(\"sell_acres\", 0),
        feed_bushels=kwargs.get(\"feed_bushels\", 0),
        plant_acres=kwargs.get(\"plant_acres\", 0),
        recruit_soldiers=kwargs.get(\"recruit_soldiers\", 0),
        train_soldiers_cost=kwargs.get(\"train_soldiers_cost\", 0),
        buy_fortifications=kwargs.get(\"buy_fortifications\", 0)
    )

    new_enhanced = step_enhanced_year(enhanced, decisions)
    
    return new_enhanced, {
        \"tool\": \"advance_kingdom_turn\",
        \"success\": True,
        \"after\": _state_to_dict(new_enhanced.classic_state),
        \"global_events\": new_enhanced.global_events
    }


# ---------------------------------------------------------------------------
# INTELLIGENCE & DIPLOMACY TOOLS
# ---------------------------------------------------------------------------

def inspect_rival_kingdoms(enhanced: EnhancedGameState) -> ToolResult:
    \"\"\"List all rival kingdoms and known diplomatic status.\"\"\"
    rivals_data = []
    for rival in enhanced.rivals:
        rel = next((d for d in enhanced.diplomacy if d.rival_id == rival.id), None)
        rivals_data.append({
            \"id\": rival.id,
            \"name\": rival.name,
            \"personality\": rival.personality,
            \"status\": rel.status if rel else \"UNKNOWN\",
            \"opinion\": rel.opinion if rel else 50,
            \"strength_estimate\": rival.military_strength,
            \"intel_confidence\": rel.intelligence_level if rel else 0
        })
        
    return {
        \"tool\": \"inspect_rival_kingdoms\",
        \"success\": True,
        \"kingdoms\": rivals_data
    }


def scout_kingdom(enhanced: EnhancedGameState, kingdom_id: str) -> ToolResult:
    \"\"\"Gather detailed intelligence on a specific rival (costs gold).\"\"\"
    rival = next((r for r in enhanced.rivals if r.id == kingdom_id), None)
    if not rival: return {\"success\": False, \"error\": \"Kingdom not found.\"}
    
    # Authoritative read of rival stats
    return {
        \"tool\": \"scout_kingdom\",
        \"success\": True,
        \"report\": {
            \"population\": rival.population,
            \"grain\": rival.bushels,
            \"army\": rival.soldiers,
            \"confidence\": 100
        }
    }


def evaluate_war_readiness(enhanced: EnhancedGameState, target_id: str) -> ToolResult:
    \"\"\"Compare military power and assess war victory probability.\"\"\"
    rival = next((r for r in enhanced.rivals if r.id == target_id), None)
    if not rival: return {\"success\": False, \"error\": \"Target not found.\"}
    
    our_str = enhanced.classic_state.military_strength
    their_str = rival.military_strength
    ratio = our_str / max(1, their_str)
    
    assessment = \"DOMINANT\" if ratio > 1.5 else \"SUPERIOR\" if ratio > 1.1 else \"MATCHED\" if ratio > 0.9 else \"INFERIOR\"
    
    return {
        \"tool\": \"evaluate_war_readiness\",
        \"success\": True,
        \"power_ratio\": round(ratio, 2),
        \"assessment\": assessment,
        \"req_soldiers\": int(rival.soldiers * 1.2)
    }


def manage_diplomacy(enhanced: EnhancedGameState, target_id: str, proposal: str) -> ToolResult:
    \"\"\"Send an envoy to a rival with a proposal (Alliance, Trade, Peace).\"\"\"
    rival = next((r for r in enhanced.rivals if r.id == target_id), None)
    if not rival: return {\"success\": False}
    
    # Simplified acceptance logic based on personality
    accepted = True if rival.personality != \"AGGRESSIVE\" else False
    
    return {
        \"tool\": \"manage_diplomacy\",
        \"success\": True,
        \"target\": rival.name,
        \"proposal\": proposal,
        \"accepted\": accepted,
        \"response\": f\"{rival.leader} has accepted the terms.\" if accepted else \"The proposal was rejected.\"
    }


# ---------------------------------------------------------------------------
# ANALYTICS & HISTORY TOOLS
# ---------------------------------------------------------------------------

def inspect_disaster_conditions(enhanced: EnhancedGameState) -> ToolResult:
    \"\"\"Analyze current famine and plague risks.\"\"\"
    s = enhanced.classic_state
    level = \"SAFE\"
    if s.bushels < s.population * 10: level = \"CRITICAL\"
    elif s.bushels < s.population * 18: level = \"WARNING\"
        
    return {
        \"tool\": \"inspect_disaster_conditions\",
        \"success\": True,
        \"famine\": {\"level\": level, \"starved\": s.starved_this_year},
        \"plague\": {\"occurred\": s.plague_struck}
    }


def get_advisor_recommendation(enhanced: EnhancedGameState) -> ToolResult:
    \"\"\"Run the advisor engine for recommendations.\"\"\"
    adv = get_advisor_advice(enhanced.classic_state)
    return {
        \"tool\": \"get_advisor_recommendation\",
        \"success\": True,
        \"advice\": asdict(adv)
    }


def get_chronicle_summary(enhanced: EnhancedGameState) -> ToolResult:
    \"\"\"Return turn-by-turn history of the current reign.\"\"\"
    history = [asdict(e) for e in enhanced.chronicle]
    return {
        \"tool\": \"get_chronicle_summary\",
        \"success\": True,
        \"history\": history
    }
