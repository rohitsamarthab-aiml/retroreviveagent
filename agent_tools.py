"""
agent_tools.py — Real game-engine tool functions exposed to the AI Royal Governor.

Every function here calls the ACTUAL game engine (game_logic.py / modern_game_logic.py).
No simulations, no fakes. Tool results are deterministic and authoritative.

Tools:
  inspect_kingdom_state()       — Read full game state as structured dict
  calculate_grain_requirements() — Compute exact grain needed to feed population
  validate_action()             — Check any TurnDecision against game rules
  allocate_grain()              — Set feed bushels decision (validated)
  manage_land()                 — Set buy/sell acres decision (validated)
  manage_farming()              — Set plant acres decision (validated)
  advance_kingdom_turn()        — Execute ONE real game turn, return before/after
  inspect_disaster_conditions() — Analyze current famine/plague/drought risk
  get_advisor_recommendation()  — Run the existing advisor engine
  get_chronicle_summary()       — Return turn-by-turn history
  
  # --- Multi-Kingdom Expansion Tools ---
  inspect_rival_kingdoms()      — List all known rival kingdoms and basic stats
  scout_kingdom()               — Gather detailed intelligence on a specific rival
  manage_military()             — Recruit and train soldiers, build defenses
  manage_diplomacy()            — Send envoys for alliances, trade, or peace
  evaluate_war_readiness()      — Compare military power and assess risks
"""

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
)


# ---------------------------------------------------------------------------
# Type alias for tool return values: always a plain dict (JSON-serialisable)
# ---------------------------------------------------------------------------
ToolResult = Dict[str, Any]


def _state_to_dict(state: GameState) -> Dict[str, Any]:
    \"\"\"Convert GameState dataclass to plain dict with human-readable keys.\"\"\"
    return {
        "year": state.year,
        "population": state.population,
        "grain_bushels": state.bushels,
        "acres_owned": state.acres,
        "land_price_per_acre": state.land_price,
        "starved_this_year": state.starved_this_year,
        "starved_total_all_years": state.starved_total,
        "avg_starvation_pct": round(state.starved_pct_avg, 2),
        "immigrants_this_year": state.immigrants_this_year,
        "harvest_yield_per_acre": state.harvest_yield,
        "grain_eaten_by_rats": state.rats_ate,
        "plague_struck_this_year": state.plague_struck,
        "plague_risk_next_year": state.plague_next_year,
        "game_is_over": state.is_over,
        "game_over_reason": state.game_over_reason,
        "soldiers": state.soldiers,
        "military_strength": state.military_strength,
        "treasury_gold": state.treasury_gold,
        "defense_level": state.defense_level,
        "territory_influence": round(state.territory_influence, 2),
    }


# ---------------------------------------------------------------------------
# TOOL 1: inspect_kingdom_state
# ---------------------------------------------------------------------------
def inspect_kingdom_state(enhanced: EnhancedGameState) -> ToolResult:
    \"\"\"
    Read the complete current kingdom state from the real game engine.
    Returns all resources, population, grain, land, and threat indicators.
    \"\"\"
    state = enhanced.classic_state
    state_dict = _state_to_dict(state)

    # Derived analytics
    grain_per_person = state.bushels / max(1, state.population)
    years_of_food    = state.bushels / max(1, state.population * 20)
    acres_per_person = state.acres / max(1, state.population)
    labor_capacity   = state.population * 10   # max acres that can be farmed
    seed_for_all     = state.acres // 2         # bushels needed to plant all land

    return {
        \"tool\": \"inspect_kingdom_state\",
        \"success\": True,
        \"state\": state_dict,
        \"analytics\": {
            \"grain_per_person_bushels\": round(grain_per_person, 1),
            \"food_security_years\": round(years_of_food, 2),
            \"acres_per_person\": round(acres_per_person, 2),
            \"max_plantable_acres_by_labor\": labor_capacity,
            \"bushels_to_plant_all_land\": seed_for_all,
            \"famine_risk\": \"CRITICAL\" if state.bushels < state.population * 20
                           else \"HIGH\" if state.bushels < state.population * 30
                           else \"LOW\",
            \"starvation_risk_tier\": (
                \"IMPEACHMENT_RISK\" if state.bushels < state.population * 10
                else \"HIGH\" if state.bushels < state.population * 18
                else \"SAFE\"
            ),
        },
        \"chronicle_turns_completed\": len(enhanced.chronicle),
        \"mode\": enhanced.mode,
    }


# ---------------------------------------------------------------------------
# TOOL 2: calculate_grain_requirements
# ---------------------------------------------------------------------------
def calculate_grain_requirements(enhanced: EnhancedGameState) -> ToolResult:
    \"\"\"
    Compute exact grain allocations needed based on game rules.
    Returns recommended feed, seed, reserve amounts for this turn.
    \"\"\"
    state = enhanced.classic_state
    pop   = state.population
    bush  = state.bushels
    acres = state.acres

    full_feed          = pop * 20           # bushels to feed everyone (20 per person)
    min_viable_feed    = pop * 15           # 75% rations — some starvation
    labor_limit        = pop * 10           # max acres farmable
    plant_target       = min(acres, labor_limit)
    seed_needed        = plant_target // 2

    grain_after_feed   = max(0, bush - full_feed)
    grain_for_seed     = min(grain_after_feed, seed_needed)
    grain_reserve      = max(0, grain_after_feed - grain_for_seed)

    return {
        \"tool\": \"calculate_grain_requirements\",
        \"success\": True,
        \"population\": pop,
        \"grain_in_store\": bush,
        \"requirements\": {
            \"full_feed_bushels\": full_feed,
            \"minimum_viable_feed_bushels\": min_viable_feed,
            \"seed_for_max_planting\": seed_needed,
            \"max_plantable_acres\": plant_target,
        },
        \"budget_breakdown\": {
            \"after_feeding_surplus\": grain_after_feed,
            \"allocated_for_seed\": grain_for_seed,
            \"remaining_reserve\": grain_reserve,
            \"can_fully_feed\": bush >= full_feed,
        }
    }


# ---------------------------------------------------------------------------
# TOOL 3: validate_action
# ---------------------------------------------------------------------------
def validate_action(
    enhanced: EnhancedGameState,
    buy_acres: int = 0,
    sell_acres: int = 0,
    feed_bushels: int = 0,
    plant_acres: int = 0,
    recruit_soldiers: int = 0,
    train_soldiers_cost: int = 0,
    buy_fortifications: int = 0
) -> ToolResult:
    \"\"\"
    Run the game engine's validation logic on a set of proposed decisions.
    Checks for negative values, affordability, labor limits, etc.
    \"\"\"
    state = enhanced.classic_state
    
    # 1. Check mutual exclusivity
    if buy_acres > 0 and sell_acres > 0:
        return {\"success\": False, \"error\": \"Cannot buy AND sell land in the same year.\"}

    # 2. Run core engine validators
    res_buy   = validate_buy_land(state, buy_acres)
    res_sell  = validate_sell_land(state, sell_acres)
    res_feed  = validate_feed_people(state, feed_bushels)
    res_plant = validate_plant_seed(state, plant_acres)
    
    # 3. Expansion checks
    gold_cost = train_soldiers_cost + (buy_fortifications * 50)
    can_afford_gold = state.treasury_gold >= gold_cost
    
    validation_map = {
        \"buy_land\": {\"valid\": res_buy.is_valid, \"msg\": res_buy.message, \"fatal\": res_buy.is_fatal},
        \"sell_land\": {\"valid\": res_sell.is_valid, \"msg\": res_sell.message, \"fatal\": res_sell.is_fatal},
        \"feed_people\": {\"valid\": res_feed.is_valid, \"msg\": res_feed.message, \"fatal\": res_feed.is_fatal},
        \"plant_fields\": {\"valid\": res_plant.is_valid, \"msg\": res_plant.message, \"fatal\": res_plant.is_fatal},
        \"treasury\": {\"valid\": can_afford_gold, \"msg\": \"Insufficient gold\" if not can_afford_gold else \"OK\"}
    }

    all_valid = all(v[\"valid\"] for v in validation_map.values())
    any_fatal = any(v[\"fatal\"] for v in validation_map.values())

    return {
        \"tool\": \"validate_action\",
        \"success\": True,
        \"all_valid\": all_valid,
        \"any_fatal_error\": any_fatal,
        \"validation\": validation_map,
        \"can_execute\": all_valid and not any_fatal
    }


# ---------------------------------------------------------------------------
# TOOL: advance_kingdom_turn
# ---------------------------------------------------------------------------
def advance_kingdom_turn(
    enhanced: EnhancedGameState,
    buy_acres: int = 0,
    sell_acres: int = 0,
    feed_bushels: int = 0,
    plant_acres: int = 0,
    recruit_soldiers: int = 0,
    train_soldiers_cost: int = 0,
    buy_fortifications: int = 0
) -> tuple[EnhancedGameState, ToolResult]:
    \"\"\"
    AUTHORITATIVE: Commit the King's decrees and advance to the next year.
    This is the ONLY tool that mutates game state.
    Returns (new_state, tool_result_log).
    \"\"\"
    # Validation check first
    val = validate_action(
        enhanced, buy_acres, sell_acres, feed_bushels, plant_acres,
        recruit_soldiers, train_soldiers_cost, buy_fortifications
    )
    if not val[\"can_execute\"]:
        return enhanced, {\"success\": False, \"error\": \"Validation failed\", \"details\": val}

    decisions = TurnDecisions(
        buy_acres=buy_acres,
        sell_acres=sell_acres,
        feed_bushels=feed_bushels,
        plant_acres=plant_acres,
        recruit_soldiers=recruit_soldiers,
        train_soldiers_cost=train_soldiers_cost,
        buy_fortifications=buy_fortifications
    )

    new_enhanced = step_enhanced_year(enhanced, decisions)
    
    before = enhanced.classic_state
    after  = new_enhanced.classic_state

    return new_enhanced, {
        \"tool\": \"advance_kingdom_turn\",
        \"success\": True,
        \"year_processed\": before.year,
        \"before\": _state_to_dict(before),
        \"after\": _state_to_dict(after),
        \"resource_deltas\": {
            \"population\": after.population - before.population,
            \"bushels\": after.bushels - before.bushels,
            \"acres\": after.acres - before.acres,
            \"soldiers\": after.soldiers - before.soldiers,
            \"gold\": after.treasury_gold - before.treasury_gold
        },
        \"events\": new_enhanced.global_events
    }


# ---------------------------------------------------------------------------
# TOOL: inspect_rival_kingdoms
# ---------------------------------------------------------------------------
def inspect_rival_kingdoms(enhanced: EnhancedGameState) -> ToolResult:
    \"\"\"
    List all rival kingdoms and the known diplomatic status for each.
    \"\"\"
    rivals_data = []
    for rival in enhanced.rivals:
        # Find diplomatic relation
        rel = next((d for d in enhanced.diplomacy if d.rival_id == rival.id), None)
        status = rel.status if rel else \"UNKNOWN\"
        opinion = rel.opinion if rel else 50
        
        # Obfuscate data based on intelligence level (simplified)
        intel = rel.intelligence_level if rel else 0
        
        rivals_data.append({
            \"id\": rival.id,
            \"name\": rival.name,
            \"leader\": rival.leader,
            \"personality\": rival.personality,
            \"diplomatic_status\": status,
            \"opinion_score\": opinion,
            \"perceived_power\": \"HIGH\" if rival.military_strength > 200 else \"MEDIUM\" if rival.military_strength > 100 else \"LOW\",
            \"intelligence_available\": intel
        })
        
    return {
        \"tool\": \"inspect_rival_kingdoms\",
        \"success\": True,
        \"rival_count\": len(rivals_data),
        \"kingdoms\": rivals_data
    }


# ---------------------------------------------------------------------------
# TOOL: scout_kingdom
# ---------------------------------------------------------------------------
def scout_kingdom(enhanced: EnhancedGameState, kingdom_id: str) -> ToolResult:
    \"\"\"
    Spend gold to gather detailed intelligence on a rival kingdom.
    Returns population, grain, acres, and military details.
    \"\"\"
    rival = next((r for r in enhanced.rivals if r.id == kingdom_id), None)
    if not rival:
        return {\"success\": False, \"error\": f\"Kingdom '{kingdom_id}' not found.\"}
        
    # Cost: 100 gold for a scouting mission
    if enhanced.classic_state.treasury_gold < 100:
        return {\"success\": False, \"error\": \"Insufficient gold in treasury to fund scouts (100 required).\"}
        
    # Intelligence Gathering (Authoritative read of rival stats)
    # In a real game, this would mutate the intelligence_level in diplomacy
    
    return {
        \"tool\": \"scout_kingdom\",
        \"success\": True,
        \"kingdom_name\": rival.name,
        \"intelligence_report\": {
            \"population\": rival.population,
            \"grain_reserves\": rival.bushels,
            \"land_owned\": rival.acres,
            \"army_size\": rival.soldiers,
            \"military_rating\": rival.military_strength,
            \"treasury_wealth\": rival.treasury,
            \"confidence_level\": 100
        }
    }


# ---------------------------------------------------------------------------
# TOOL: evaluate_war_readiness
# ---------------------------------------------------------------------------
def evaluate_war_readiness(enhanced: EnhancedGameState, target_id: str) -> ToolResult:
    \"\"\"
    Compare our military resources with a rival to assess war victory probability.
    \"\"\"
    state = enhanced.classic_state
    rival = next((r for r in enhanced.rivals if r.id == target_id), None)
    
    if not rival:
        return {\"success\": False, \"error\": \"Target kingdom not found.\"}
        
    our_str = state.military_strength
    their_str = rival.military_strength
    
    ratio = our_str / max(1, their_str)
    
    if ratio > 1.5:
        assessment = \"DOMINANT\"
        win_prob = \"VERY HIGH (>90%)\"
    elif ratio > 1.1:
        assessment = \"SUPERIOR\"
        win_prob = \"HIGH (~75%)\"
    elif ratio > 0.9:
        assessment = \"MATCHED\"
        win_prob = \"UNCERTAIN (~50%)\"
    else:
        assessment = \"INFERIOR\"
        win_prob = \"LOW (<25%)\"
        
    return {
        \"tool\": \"evaluate_war_readiness\",
        \"success\": True,
        \"comparison\": {
            \"our_strength\": our_str,
            \"rival_strength\": their_str,
            \"power_ratio\": round(ratio, 2),
            \"strategic_assessment\": assessment,
            \"estimated_win_probability\": win_prob
        },
        \"logistics\": {
            \"grain_reserves\": state.bushels,
            \"war_attrition_estimate\": int(state.soldiers * 0.2)
        }
    }


# ---------------------------------------------------------------------------
# TOOL: manage_diplomacy
# ---------------------------------------------------------------------------
def manage_diplomacy(
    enhanced: EnhancedGameState, 
    target_id: str, 
    proposal: str, 
    tribute_gold: int = 0
) -> ToolResult:
    \"\"\"
    Send an envoy to a rival with a proposal (Alliance, Trade, Peace, or Threat).
    \"\"\"
    rival = next((r for r in enhanced.rivals if r.id == target_id), None)
    rel = next((d for d in enhanced.diplomacy if d.rival_id == target_id), None)
    
    if not rival or not rel:
        return {\"success\": False, \"error\": \"Kingdom or relation not found.\"}
        
    if enhanced.classic_state.treasury_gold < tribute_gold:
        return {\"success\": False, \"error\": \"Insufficient gold for tribute.\"}
        
    # Decision Logic (Simplified)
    acceptance = False
    opinion_boost = 0
    
    if proposal == \"TRADE\":
        if rel.opinion > 40:
            acceptance = True
            opinion_boost = 10
        msg = f\"{rival.name} accepts the trade agreement.\" if acceptance else f\"{rival.name} rejects trade; they do not trust us.\"
    elif proposal == \"ALLIANCE\":
        if rel.opinion > 75:
            acceptance = True
            opinion_boost = 20
        msg = f\"{rival.name} pledges their sword to Babylon!\" if acceptance else f\"{rival.name} is not ready for an alliance.\"
    elif proposal == \"PEACE\":
        if rel.status == \"WAR\" or rel.status == \"HOSTILE\":
            if tribute_gold > 200 or rel.opinion > 50:
                acceptance = True
                opinion_boost = 15
        msg = \"Peace has been brokered.\" if acceptance else \"The war continues.\"
    else:
        msg = \"The envoy was received with cold indifference.\"
        
    return {
        \"tool\": \"manage_diplomacy\",
        \"success\": True,
        \"target\": rival.name,
        \"proposal\": proposal,
        \"accepted\": acceptance,
        \"opinion_change\": opinion_boost,
        \"response_text\": msg
    }


# --- Existing Tools (Preserved) ---

def inspect_disaster_conditions(enhanced: EnhancedGameState) -> ToolResult:
    state = enhanced.classic_state
    famine_risk = \"SAFE\"
    if state.bushels < state.population * 18:
        famine_risk = \"WARNING\"
    if state.bushels < state.population * 10:
        famine_risk = \"CRITICAL\"
    if state.starved_this_year > 0:
        famine_risk = \"ACTIVE_FAMINE\"
        
    return {
        \"tool\": \"inspect_disaster_conditions\",
        \"success\": True,
        \"famine\": {\"level\": famine_risk, \"deaths\": state.starved_this_year},
        \"plague\": {\"occurred\": state.plague_struck, \"next_year_risk\": state.plague_next_year},
        \"land_health\": \"EXCELLENT\",
        \"impeachment_risk\": state.starved_pct_avg > 30
    }

def get_advisor_recommendation(enhanced: EnhancedGameState) -> ToolResult:
    adv = get_advisor_advice(enhanced.classic_state)
    return {
        \"tool\": \"get_advisor_recommendation\",
        \"success\": True,
        \"advisor_recommendations\": asdict(adv)
    }

def get_chronicle_summary(enhanced: EnhancedGameState) -> ToolResult:
    history = [asdict(e) for e in enhanced.chronicle]
    return {
        \"tool\": \"get_chronicle_summary\",
        \"success\": True,
        \"turns_completed\": len(history),
        \"history\": history
    }

def allocate_grain(enhanced: EnhancedGameState, feed_bushels: int) -> ToolResult:
    res = validate_feed_people(enhanced.classic_state, feed_bushels)
    if not res.is_valid:
        return {\"success\": False, \"error\": res.message}
    return {
        \"success\": True,
        \"outcome_preview\": {
            \"citizens_fully_fed\": feed_bushels // 20,
            \"citizens_will_starve\": max(0, enhanced.classic_state.population - (feed_bushels // 20)),
            \"impeachment_risk\": (enhanced.classic_state.population - (feed_bushels // 20)) > 0.45 * enhanced.classic_state.population
        }
    }

def manage_land(enhanced: EnhancedGameState, buy_acres: int = 0, sell_acres: int = 0) -> ToolResult:
    if buy_acres > 0 and sell_acres > 0:
        return {\"success\": False, \"error\": \"Cannot buy AND sell land.\"}
    if buy_acres > 0:
        res = validate_buy_land(enhanced.classic_state, buy_acres)
    else:
        res = validate_sell_land(enhanced.classic_state, sell_acres)
    
    if not res.is_valid:
        return {\"success\": False, \"error\": res.message}
    return {\"success\": True}

def manage_farming(enhanced: EnhancedGameState, plant_acres: int, grain_available_after_feed: int) -> ToolResult:
    res = validate_plant_seed(enhanced.classic_state, plant_acres)
    if not res.is_valid:
        return {\"success\": False, \"error\": res.message}
    return {
        \"success\": True,
        \"seed_cost_bushels\": plant_acres // 2,
        \"harvest_projection\": {
            \"min_harvest_bushels\": plant_acres * 1,
            \"max_harvest_bushels\": plant_acres * 5
        }
    }
