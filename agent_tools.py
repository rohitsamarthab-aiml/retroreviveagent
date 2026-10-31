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
"""

from __future__ import annotations

import math
from dataclasses import asdict
from typing import Any, Dict, Optional

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
    """Convert GameState dataclass to plain dict with human-readable keys."""
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
    }


# ---------------------------------------------------------------------------
# TOOL 1: inspect_kingdom_state
# ---------------------------------------------------------------------------
def inspect_kingdom_state(enhanced: EnhancedGameState) -> ToolResult:
    """
    Read the complete current kingdom state from the real game engine.
    Returns all resources, population, grain, land, and threat indicators.
    """
    state = enhanced.classic_state
    state_dict = _state_to_dict(state)

    # Derived analytics
    grain_per_person = state.bushels / max(1, state.population)
    years_of_food    = state.bushels / max(1, state.population * 20)
    acres_per_person = state.acres / max(1, state.population)
    labor_capacity   = state.population * 10   # max acres that can be farmed
    seed_for_all     = state.acres // 2         # bushels needed to plant all land

    return {
        "tool": "inspect_kingdom_state",
        "success": True,
        "state": state_dict,
        "analytics": {
            "grain_per_person_bushels": round(grain_per_person, 1),
            "food_security_years": round(years_of_food, 2),
            "acres_per_person": round(acres_per_person, 2),
            "max_plantable_acres_by_labor": labor_capacity,
            "bushels_to_plant_all_land": seed_for_all,
            "famine_risk": "CRITICAL" if state.bushels < state.population * 20
                           else "HIGH" if state.bushels < state.population * 30
                           else "LOW",
            "starvation_risk_tier": (
                "IMPEACHMENT_RISK" if state.bushels < state.population * 10
                else "HIGH" if state.bushels < state.population * 18
                else "SAFE"
            ),
        },
        "chronicle_turns_completed": len(enhanced.chronicle),
        "mode": enhanced.mode,
    }


# ---------------------------------------------------------------------------
# TOOL 2: calculate_grain_requirements
# ---------------------------------------------------------------------------
def calculate_grain_requirements(enhanced: EnhancedGameState) -> ToolResult:
    """
    Compute exact grain allocations needed based on game rules.
    Returns recommended feed, seed, reserve amounts for this turn.
    """
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
        "tool": "calculate_grain_requirements",
        "success": True,
        "population": pop,
        "grain_in_store": bush,
        "requirements": {
            "full_feed_bushels": full_feed,
            "minimum_viable_feed_bushels": min_viable_feed,
            "seed_for_max_planting": seed_needed,
            "max_plantable_acres": plant_target,
        },
        "budget_breakdown": {
            "after_full_feed_remaining": grain_after_feed,
            "allocated_to_seed": grain_for_seed,
            "grain_reserve_after_seed": grain_reserve,
        },
        "can_fully_feed": bush >= full_feed,
        "can_plant_max": grain_after_feed >= seed_needed,
        "warning": (
            f"CRITICAL: Only {bush} bushels available, need {full_feed} to feed {pop} people!"
            if bush < full_feed else None
        ),
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
) -> ToolResult:
    """
    Validate a proposed set of decisions against real game rules.
    Returns validation status for each action and whether combined decisions are viable.
    """
    state = enhanced.classic_state

    # Run each validator
    buy_result  = validate_buy_land(state, buy_acres)
    sell_result = validate_sell_land(state, sell_acres)

    # Compute grain after land transactions for feed/plant validation
    grain_after_trade = state.bushels
    if buy_acres > 0:
        grain_after_trade -= buy_acres * state.land_price
    elif sell_acres > 0:
        grain_after_trade += sell_acres * state.land_price

    feed_result = validate_feed_people(
        GameState(**{**asdict(state), "bushels": grain_after_trade}),
        feed_bushels
    )

    grain_after_feed = grain_after_trade - feed_bushels
    plant_result = validate_plant_seed(
        GameState(**{**asdict(state), "bushels": grain_after_feed}),
        plant_acres,
        grain_after_feed,
    )

    all_valid = all([
        buy_result.is_valid,
        sell_result.is_valid,
        feed_result.is_valid,
        plant_result.is_valid,
    ])
    any_fatal = any([
        buy_result.is_fatal,
        sell_result.is_fatal,
        feed_result.is_fatal,
        plant_result.is_fatal,
    ])

    return {
        "tool": "validate_action",
        "success": True,
        "proposed_decisions": {
            "buy_acres": buy_acres,
            "sell_acres": sell_acres,
            "feed_bushels": feed_bushels,
            "plant_acres": plant_acres,
        },
        "validation": {
            "buy_land":   {"valid": buy_result.is_valid,  "fatal": buy_result.is_fatal,  "message": buy_result.message},
            "sell_land":  {"valid": sell_result.is_valid, "fatal": sell_result.is_fatal, "message": sell_result.message},
            "feed_people":{"valid": feed_result.is_valid, "fatal": feed_result.is_fatal, "message": feed_result.message},
            "plant_seed": {"valid": plant_result.is_valid,"fatal": plant_result.is_fatal,"message": plant_result.message},
        },
        "all_valid": all_valid,
        "any_fatal_error": any_fatal,
        "can_execute": all_valid and not any_fatal,
    }


# ---------------------------------------------------------------------------
# TOOL 4: allocate_grain
# ---------------------------------------------------------------------------
def allocate_grain(
    enhanced: EnhancedGameState,
    feed_bushels: int,
) -> ToolResult:
    """
    Validate and confirm the grain feeding allocation for this turn.
    Does NOT advance the turn — just confirms the decision is valid.
    """
    state  = enhanced.classic_state
    result = validate_feed_people(state, feed_bushels)

    citizens_fed   = feed_bushels // 20
    will_starve    = max(0, state.population - citizens_fed)
    starve_pct     = (will_starve / max(1, state.population)) * 100

    return {
        "tool": "allocate_grain",
        "success": result.is_valid,
        "feed_bushels": feed_bushels,
        "validation": {
            "valid": result.is_valid,
            "fatal": result.is_fatal,
            "message": result.message,
        },
        "outcome_preview": {
            "citizens_fully_fed": citizens_fed,
            "citizens_will_starve": will_starve,
            "starvation_pct": round(starve_pct, 1),
            "grain_remaining_after_feed": state.bushels - feed_bushels if result.is_valid else None,
            "impeachment_risk": will_starve > 0.45 * state.population,
        },
    }


# ---------------------------------------------------------------------------
# TOOL 5: manage_land
# ---------------------------------------------------------------------------
def manage_land(
    enhanced: EnhancedGameState,
    buy_acres: int = 0,
    sell_acres: int = 0,
) -> ToolResult:
    """
    Validate a land buy or sell decision against current grain and ownership.
    Returns cost/revenue and validation. Does NOT advance the turn.
    """
    state = enhanced.classic_state

    if buy_acres > 0 and sell_acres > 0:
        return {
            "tool": "manage_land",
            "success": False,
            "error": "Cannot buy AND sell land in the same turn. Choose one.",
        }

    if buy_acres > 0:
        result = validate_buy_land(state, buy_acres)
        cost   = buy_acres * state.land_price
        return {
            "tool": "manage_land",
            "success": result.is_valid,
            "action": "BUY",
            "acres": buy_acres,
            "cost_bushels": cost,
            "price_per_acre": state.land_price,
            "grain_after_purchase": state.bushels - cost if result.is_valid else None,
            "new_acres_total": state.acres + buy_acres if result.is_valid else None,
            "validation": {"valid": result.is_valid, "fatal": result.is_fatal, "message": result.message},
        }
    elif sell_acres > 0:
        result  = validate_sell_land(state, sell_acres)
        revenue = sell_acres * state.land_price
        return {
            "tool": "manage_land",
            "success": result.is_valid,
            "action": "SELL",
            "acres": sell_acres,
            "revenue_bushels": revenue,
            "price_per_acre": state.land_price,
            "grain_after_sale": state.bushels + revenue if result.is_valid else None,
            "new_acres_total": state.acres - sell_acres if result.is_valid else None,
            "validation": {"valid": result.is_valid, "fatal": result.is_fatal, "message": result.message},
        }
    else:
        return {
            "tool": "manage_land",
            "success": True,
            "action": "HOLD",
            "acres": 0,
            "note": "No land transaction this turn.",
        }


# ---------------------------------------------------------------------------
# TOOL 6: manage_farming
# ---------------------------------------------------------------------------
def manage_farming(
    enhanced: EnhancedGameState,
    plant_acres: int,
    grain_available_after_feed: int,
) -> ToolResult:
    """
    Validate a planting decision given grain remaining after feeding.
    Returns seed cost, expected harvest range, and validation.
    """
    state  = enhanced.classic_state
    result = validate_plant_seed(state, plant_acres, grain_available_after_feed)

    seed_cost          = plant_acres // 2
    min_harvest        = plant_acres * 1   # yield can be 1–5
    max_harvest        = plant_acres * 5
    expected_harvest   = plant_acres * 3   # average yield

    return {
        "tool": "manage_farming",
        "success": result.is_valid,
        "plant_acres": plant_acres,
        "seed_cost_bushels": seed_cost,
        "labor_capacity": state.population * 10,
        "validation": {
            "valid": result.is_valid,
            "fatal": result.is_fatal,
            "message": result.message,
        },
        "harvest_projection": {
            "min_harvest_bushels": min_harvest,
            "expected_harvest_bushels": expected_harvest,
            "max_harvest_bushels": max_harvest,
            "note": "Actual yield determined by random weather (1-5 bu/acre)",
        } if result.is_valid else None,
    }


# ---------------------------------------------------------------------------
# TOOL 7: advance_kingdom_turn
# ---------------------------------------------------------------------------
def advance_kingdom_turn(
    enhanced: EnhancedGameState,
    buy_acres: int = 0,
    sell_acres: int = 0,
    feed_bushels: int = 0,
    plant_acres: int = 0,
    rng=None,
) -> tuple[EnhancedGameState, ToolResult]:
    """
    Execute ONE real game turn with the provided decisions.
    Validates ALL decisions first. If any fail, returns error without advancing.
    Returns (new_enhanced_state, result_dict).

    This is the ONLY function that actually changes the game state.
    """
    # Full validation pass before executing
    validation = validate_action(
        enhanced,
        buy_acres=buy_acres,
        sell_acres=sell_acres,
        feed_bushels=feed_bushels,
        plant_acres=plant_acres,
    )

    if not validation["can_execute"]:
        return enhanced, {
            "tool": "advance_kingdom_turn",
            "success": False,
            "error": "Decisions failed validation. Turn NOT advanced.",
            "validation_errors": validation["validation"],
            "decisions_attempted": {
                "buy_acres": buy_acres,
                "sell_acres": sell_acres,
                "feed_bushels": feed_bushels,
                "plant_acres": plant_acres,
            },
        }

    # Snapshot before
    before_state = enhanced.classic_state

    # Execute through the REAL game engine
    decisions = TurnDecisions(
        buy_acres=buy_acres,
        sell_acres=sell_acres,
        feed_bushels=feed_bushels,
        plant_acres=plant_acres,
    )
    new_enhanced = step_enhanced_year(enhanced, decisions, rng=rng)
    after_state  = new_enhanced.classic_state

    # Compute deltas (what actually changed)
    result = {
        "tool": "advance_kingdom_turn",
        "success": True,
        "year_processed": before_state.year,
        "decisions_executed": {
            "buy_acres":     buy_acres,
            "sell_acres":    sell_acres,
            "feed_bushels":  feed_bushels,
            "plant_acres":   plant_acres,
        },
        "before": {
            "year":       before_state.year,
            "population": before_state.population,
            "bushels":    before_state.bushels,
            "acres":      before_state.acres,
        },
        "after": {
            "year":       after_state.year,
            "population": after_state.population,
            "bushels":    after_state.bushels,
            "acres":      after_state.acres,
        },
        "events": {
            "harvest_yield":   after_state.harvest_yield,
            "total_harvested": plant_acres * after_state.harvest_yield,
            "grain_eaten_by_rats": after_state.rats_ate,
            "immigrants_arrived":  after_state.immigrants_this_year,
            "starved_this_year":   after_state.starved_this_year,
            "plague_struck":       after_state.plague_struck,
        },
        "resource_deltas": {
            "population_change": after_state.population - before_state.population,
            "bushel_change":     after_state.bushels    - before_state.bushels,
            "acre_change":       after_state.acres      - before_state.acres,
        },
        "game_over": after_state.is_over,
        "game_over_reason": after_state.game_over_reason,
        "chronicle_entry_added": True,
    }

    return new_enhanced, result


# ---------------------------------------------------------------------------
# TOOL 8: inspect_disaster_conditions
# ---------------------------------------------------------------------------
def inspect_disaster_conditions(enhanced: EnhancedGameState) -> ToolResult:
    """
    Analyse current game state for famine, plague, and economic collapse risks.
    Returns threat assessment with recommended mitigation actions.
    """
    state = enhanced.classic_state
    pop   = state.population
    bush  = state.bushels
    acres = state.acres

    # Famine risk
    needed = pop * 20
    deficit = needed - bush
    famine_turns_of_food = bush / max(1, needed)

    if bush < needed:
        famine_level  = "ACTIVE_FAMINE"
        famine_detail = f"Grain deficit of {deficit} bushels. {deficit // 20} citizens will starve this turn unless land is sold immediately."
    elif bush < needed * 1.2:
        famine_level  = "CRITICAL"
        famine_detail = f"Only {bush} bushels for {pop} people. One bad harvest could trigger famine."
    elif bush < needed * 1.5:
        famine_level  = "WARNING"
        famine_detail = f"Grain reserves tight. Recommend building buffer above {int(needed * 1.5)} bushels."
    else:
        famine_level  = "SAFE"
        famine_detail = f"Adequate reserves: {bush} bushels for {pop} people ({famine_turns_of_food:.1f} turns of food)."

    # Impeachment risk (>45% starvation triggers game over)
    if bush < pop * 9:   # feeding 0 → 45%+ starve
        impeachment_risk = "IMMINENT"
    elif bush < needed * 0.55:
        impeachment_risk = "HIGH"
    else:
        impeachment_risk = "NONE"

    # Plague risk
    plague_risk = "PENDING" if state.plague_next_year else "NONE"

    # Economic collapse (acres per person < 7 → Tier-1 end)
    acres_per_person = acres / max(1, pop)
    if acres_per_person < 7:
        land_health = "CRITICAL — TIER_1_RISK (below 7 acres/person)"
    elif acres_per_person < 9:
        land_health = "POOR — TIER_2_RISK"
    elif acres_per_person < 10:
        land_health = "FAIR — TIER_3_RISK"
    else:
        land_health = "GOOD — TIER_4_ELIGIBLE"

    # Mitigation recommendations
    mitigations = []
    if famine_level == "ACTIVE_FAMINE":
        acres_to_sell = math.ceil(deficit / max(1, state.land_price))
        mitigations.append(f"URGENT: Sell {acres_to_sell} acres at {state.land_price} bu/acre to cover grain deficit")
    if plague_risk == "PENDING":
        mitigations.append("PREPARE: Plague will strike next year — stockpile extra grain for reduced population")
    if acres_per_person < 9:
        mitigations.append(f"LAND ALERT: Buy more acres when grain permits (currently {acres_per_person:.1f} ac/person)")

    return {
        "tool": "inspect_disaster_conditions",
        "success": True,
        "famine": {
            "level": famine_level,
            "detail": famine_detail,
            "grain_needed_to_feed_all": needed,
            "grain_available": bush,
            "turns_of_food_remaining": round(famine_turns_of_food, 2),
        },
        "plague": {
            "struck_this_year": state.plague_struck,
            "risk_next_year": plague_risk,
        },
        "land_health": land_health,
        "impeachment_risk": impeachment_risk,
        "recommended_mitigations": mitigations,
    }


# ---------------------------------------------------------------------------
# TOOL 9: get_advisor_recommendation
# ---------------------------------------------------------------------------
def get_advisor_recommendation(enhanced: EnhancedGameState) -> ToolResult:
    """
    Run the existing Royal Advisor engine and return structured recommendations.
    Uses the real advisor logic from modern_game_logic.py.
    """
    advice = get_advisor_advice(enhanced.classic_state)
    return {
        "tool": "get_advisor_recommendation",
        "success": True,
        "advisor_recommendations": {
            "vizier_summary": advice.vizier,
            "granary_master": advice.granary_master,
            "surveyor": advice.surveyor,
            "recommended_feed_bushels": advice.recommended_feed,
            "recommended_plant_acres": advice.recommended_plant,
            "recommended_buy_acres": advice.recommended_buy,
            "recommended_sell_acres": advice.recommended_sell,
            "land_price_rating": advice.land_price_rating,
        },
    }


# ---------------------------------------------------------------------------
# TOOL 10: get_chronicle_summary
# ---------------------------------------------------------------------------
def get_chronicle_summary(enhanced: EnhancedGameState) -> ToolResult:
    """
    Return the turn-by-turn history of all decisions and their outcomes.
    """
    entries = []
    for e in enhanced.chronicle:
        entries.append({
            "year":            e.year,
            "population_start": e.population_start,
            "population_end":   e.population_end,
            "starved":          e.starved,
            "immigrants":       e.immigrants,
            "plague":           e.plague,
            "grain_end":        e.bushels,
            "acres":            e.acres,
            "bought_acres":     e.bought_acres,
            "sold_acres":       e.sold_acres,
            "fed_bushels":      e.fed_bushels,
            "planted_acres":    e.planted_acres,
            "yield_rate":       e.yield_rate,
            "total_harvested":  e.harvested_total,
            "rats_ate":         e.rats_ate,
        })

    return {
        "tool": "get_chronicle_summary",
        "success": True,
        "turns_completed": len(entries),
        "history": entries,
    }

