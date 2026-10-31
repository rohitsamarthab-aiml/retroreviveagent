"""
modern_game_logic.py - Enhanced Mode logic for RetroRevive: Hammurabi Reimagined.

This module provides genuinely useful gameplay enhancements for modern players
while keeping historical rules separate:
- Interactive Scenarios with explicit goals and victory conditions
- Contextual Royal Advisors (Vizier, Granary Master, Surveyor)
- Comprehensive Chronicle & Event Log (year-by-year decisions and stats)
- Safe Save & Resume game persistence via standard-library JSON
"""

from dataclasses import asdict, dataclass, field
import json
import math
import os
from typing import Any, Dict, List, Optional

from game_logic import (
    DefaultRNG,
    GameState,
    RandomProvider,
    TurnDecisions,
    calculate_land_price,
    evaluate_term,
    init_game,
    step_year,
    validate_buy_land,
    validate_feed_people,
    validate_plant_seed,
    validate_sell_land,
)


@dataclass
class ScenarioDefinition:
    """Defines a challenge scenario with specific starting conditions and objectives."""

    scenario_id: str
    title: str
    subtitle: str
    description: str
    target_year: int
    starting_population: int = 100
    starting_bushels: int = 2800
    starting_acres: int = 1000
    # Victory check criteria
    min_final_bushels: int = 0
    min_final_acres: int = 0
    min_final_population: int = 0
    max_avg_starvation_pct: float = 33.0
    zero_starvation_required: bool = False


SCENARIOS: Dict[str, ScenarioDefinition] = {
    "drought": ScenarioDefinition(
        scenario_id="drought",
        title="The Great Drought",
        subtitle="5-Year Survival Challenge",
        description=(
            "Severe dry winds parch Sumeria. Starting with depleted grain silos, "
            "you must manage rations carefully, avoid famine, and stockpile at "
            "least 2,500 bushels by Year 5."
        ),
        target_year=5,
        starting_population=100,
        starting_bushels=1800,  # Starts with scarce grain
        starting_acres=1000,
        min_final_bushels=2500,
        max_avg_starvation_pct=5.0,
    ),
    "boom": ScenarioDefinition(
        scenario_id="boom",
        title="The Population Boom",
        subtitle="7-Year Expansion Challenge",
        description=(
            "Word of Sumeria's wealth spreads, bringing large waves of migrants. "
            "You must expand your farmland to at least 1,300 acres to provide "
            "enough work and food for the growing city."
        ),
        target_year=7,
        starting_population=100,
        starting_bushels=3000,
        starting_acres=1000,
        min_final_acres=1300,
        min_final_population=120,
        max_avg_starvation_pct=3.0,
    ),
    "granary": ScenarioDefinition(
        scenario_id="granary",
        title="The Granary Defense",
        subtitle="6-Year Stockpile Challenge",
        description=(
            "Aggressive desert rodents threaten Sumeria's food reserves. Protect "
            "your silos, cultivate harvests diligently, and finish Year 6 with "
            "at least 3,500 bushels stored in reserve."
        ),
        target_year=6,
        starting_population=100,
        starting_bushels=2800,
        starting_acres=1000,
        min_final_bushels=3500,
        max_avg_starvation_pct=4.0,
    ),
    "empire": ScenarioDefinition(
        scenario_id="empire",
        title="Empire of Babylon",
        subtitle="10-Year Master Challenge",
        description=(
            "Govern for a full 10-year term and establish an ancient empire: "
            "surpass 140 population, expand beyond 1,400 acres, and secure a "
            "legendary Charlemagne-tier final performance evaluation."
        ),
        target_year=10,
        starting_population=100,
        starting_bushels=2800,
        starting_acres=1000,
        min_final_acres=1400,
        min_final_population=130,
        max_avg_starvation_pct=3.0,
        zero_starvation_required=False,
    ),
}


@dataclass
class AdvisorAdvice:
    """Actionable counsel provided by the Royal Council."""

    vizier: str
    granary_master: str
    surveyor: str
    recommended_feed: int
    recommended_plant: int
    land_price_rating: str  # "CHEAP", "FAIR", "EXPENSIVE"
    recommended_buy: int = 0
    recommended_sell: int = 0


@dataclass
class ChronicleEntry:
    """Historical record of decisions and consequences for one year."""

    year: int
    population_start: int
    population_end: int
    starved: int
    immigrants: int
    plague: bool
    acres: int
    bushels: int
    land_price: int
    bought_acres: int
    sold_acres: int
    fed_bushels: int
    planted_acres: int
    yield_rate: int
    harvested_total: int
    rats_ate: int


@dataclass
class EnhancedGameState:
    """State wrapper for Enhanced Mode and Scenarios."""

    classic_state: GameState
    mode: str = "ENHANCED"  # "ENHANCED" or "SCENARIO"
    scenario_id: Optional[str] = None
    chronicle: List[ChronicleEntry] = field(default_factory=list)
    scenario_status: str = "IN_PROGRESS"  # "IN_PROGRESS", "VICTORY", "DEFEAT"
    status_message: Optional[str] = None


def init_enhanced_game(
    mode: str = "ENHANCED",
    scenario_id: Optional[str] = None,
    rng: Optional[RandomProvider] = None,
    strict_historical: bool = True,
) -> EnhancedGameState:
    """Initializes a new Enhanced Mode or Scenario session."""
    provider = rng if rng is not None else DefaultRNG()

    if mode == "SCENARIO" and scenario_id in SCENARIOS:
        scen = SCENARIOS[scenario_id]
        price = calculate_land_price(provider)
        base_state = GameState(
            year=1,
            population=scen.starting_population,
            bushels=scen.starting_bushels,
            acres=scen.starting_acres,
            land_price=price,
            starved_this_year=0,
            starved_total=0,
            starved_pct_avg=0.0,
            immigrants_this_year=5,
            harvest_yield=3,
            rats_ate=200,
            plague_struck=False,
            plague_next_year=False,
            is_over=False,
            game_over_reason=None,
        )
        return EnhancedGameState(
            classic_state=base_state,
            mode="SCENARIO",
            scenario_id=scenario_id,
            chronicle=[],
            scenario_status="IN_PROGRESS",
            status_message=f"Scenario Started: {scen.title} (Target: Year {scen.target_year})",
        )

    # Standard Enhanced Mode (uses 10-year term with advisors and chronicle)
    base_state = init_game(rng=provider, strict_historical=strict_historical)
    return EnhancedGameState(
        classic_state=base_state,
        mode="ENHANCED",
        scenario_id=None,
        chronicle=[],
        scenario_status="IN_PROGRESS",
        status_message="Welcome, Sire. The Royal Council stands ready to assist your reign.",
    )


def get_advisor_advice(state: GameState) -> AdvisorAdvice:
    """
    Computes contextual advice based on the current kingdom state.
    Provides transparent arithmetic without modifying any game state.
    """
    pop = state.population
    bushels = state.bushels
    acres = state.acres
    price = state.land_price

    # Granary calculations
    exact_feed = pop * 20
    # Planting labor capacity
    labor_limit = pop * 10
    max_plant_by_land = acres

    # Evaluate land market price (17-26)
    if price <= 18:
        price_rating = "VERY CHEAP"
        surveyor_trade = f"Land trades at a bargain {price} bu/acre! Buy if silos permit."
    elif price <= 20:
        price_rating = "CHEAP"
        surveyor_trade = f"Land is reasonably priced at {price} bu/acre."
    elif price <= 23:
        price_rating = "FAIR"
        surveyor_trade = f"Land trades at an average price of {price} bu/acre."
    else:
        price_rating = "EXPENSIVE"
        surveyor_trade = f"Land trades at a high price of {price} bu/acre! Consider selling surplus land."

    rec_sell = 0
    rec_buy = 0

    # Recommended food & emergency trade
    if bushels >= exact_feed:
        rec_feed = exact_feed
        surplus_grain = bushels - exact_feed
        granary_msg = (
            f"Allocate {exact_feed} bushels (20 per person) to completely prevent starvation. "
            f"You will retain {surplus_grain} bushels for seed and reserve."
        )
        if price <= 18 and surplus_grain > (acres // 2) + price:
            grain_for_investment = surplus_grain - (acres // 2)
            max_buy = grain_for_investment // price
            labor_surplus = max(0, (labor_limit - 1) - acres)
            rec_buy = min(max_buy, labor_surplus if labor_surplus > 0 else 20)
            if rec_buy > 0:
                surveyor_trade = f"Bargain land opportunity at {price} bu/acre! Silos permit purchasing {rec_buy} acres."
    else:
        deficit = exact_feed - bushels
        # Recommend emergency land sale to cover food shortage
        rec_sell = min(math.ceil(deficit / max(1, price)), max(0, acres - 1))
        raised_grain = rec_sell * price
        effective_grain = bushels + raised_grain
        rec_feed = min(exact_feed, effective_grain)
        remaining_deficit = max(0, exact_feed - effective_grain)

        if remaining_deficit == 0:
            granary_msg = (
                f"CRITICAL SHORTAGE: We need {exact_feed} bushels, but have only {bushels}! "
                f"Emergency Decree: Sell {rec_sell} acres at {price} bu/acre to raise {raised_grain} bushels and feed all {pop} citizens!"
            )
        else:
            granary_msg = (
                f"CATASTROPHIC FAMINE: We need {exact_feed} bushels, but have only {bushels}! "
                f"Famine threatens {deficit // 20} citizens unless we sell land immediately!"
            )

    # Recommended planting
    grain_after_feed = max(0, (bushels + rec_sell * price - rec_buy * price) - rec_feed)
    max_plant_by_seed = grain_after_feed * 2
    available_land = acres - rec_sell + rec_buy
    rec_plant = min(available_land, labor_limit - 1, max_plant_by_seed)
    if rec_plant < 0:
        rec_plant = 0

    seed_needed = rec_plant // 2
    surveyor_msg = (
        f"{surveyor_trade} With {pop} citizens, we can cultivate up to {labor_limit - 1} acres. "
        f"Planting {rec_plant} acres requires {seed_needed} bushels of seed."
    )

    # Vizier overall guidance
    if bushels < exact_feed:
        vizier_msg = (
            f"Sire, our highest priority is emergency grain! Sell {rec_sell} acres at {price} bu/acre to prevent famine."
            if rec_sell > 0
            else "Sire, famine threatens our realm! Allocate all reserves to food."
        )
    elif state.year == 10:
        vizier_msg = "Final year of your term! Maximize land per capita and maintain zero starvation."
    elif rec_plant < acres * 0.7:
        vizier_msg = "Our grain or workforce limits how much land we can seed. Keep a balanced treasury."
    else:
        vizier_msg = "The realm is stable and prosperous. Maintain steady rations and fertile planting."

    return AdvisorAdvice(
        vizier=vizier_msg,
        granary_master=granary_msg,
        surveyor=surveyor_msg,
        recommended_feed=rec_feed,
        recommended_plant=rec_plant,
        land_price_rating=price_rating,
        recommended_buy=rec_buy,
        recommended_sell=rec_sell,
    )


def step_enhanced_year(
    enhanced: EnhancedGameState,
    decisions: TurnDecisions,
    rng: Optional[RandomProvider] = None,
    strict_historical: bool = True,
) -> EnhancedGameState:
    """
    Executes an annual turn, records chronicle metrics, and evaluates scenario goals.
    Uses authoritative game_logic.step_year() for exact historical calculations.
    """
    old_state = enhanced.classic_state

    # Execute simulation using authoritative engine
    new_state = step_year(
        old_state,
        decisions,
        rng=rng,
        strict_historical=strict_historical,
    )

    # Compute chronicle entry
    entry = ChronicleEntry(
        year=old_state.year,
        population_start=old_state.population,
        population_end=new_state.population,
        starved=new_state.starved_this_year,
        immigrants=new_state.immigrants_this_year,
        plague=new_state.plague_struck,
        acres=new_state.acres,
        bushels=new_state.bushels,
        land_price=old_state.land_price,
        bought_acres=decisions.buy_acres,
        sold_acres=decisions.sell_acres,
        fed_bushels=decisions.feed_bushels,
        planted_acres=decisions.plant_acres,
        yield_rate=new_state.harvest_yield,
        harvested_total=decisions.plant_acres * new_state.harvest_yield,
        rats_ate=new_state.rats_ate,
    )
    updated_chronicle = list(enhanced.chronicle) + [entry]

    # Check for in-term impeachment
    if new_state.is_over and new_state.game_over_reason == "IMPEACHED":
        return EnhancedGameState(
            classic_state=new_state,
            mode=enhanced.mode,
            scenario_id=enhanced.scenario_id,
            chronicle=updated_chronicle,
            scenario_status="DEFEAT",
            status_message="DEFEAT: You were impeached for catastrophic famine!",
        )

    # Scenario-specific evaluation
    if enhanced.mode == "SCENARIO" and enhanced.scenario_id in SCENARIOS:
        scen = SCENARIOS[enhanced.scenario_id]

        # Target year reached
        if old_state.year >= scen.target_year or new_state.is_over:
            won = True
            reasons = []

            if new_state.bushels < scen.min_final_bushels:
                won = False
                reasons.append(
                    f"Bushels ({new_state.bushels}) below target ({scen.min_final_bushels})"
                )
            if new_state.acres < scen.min_final_acres:
                won = False
                reasons.append(
                    f"Acres ({new_state.acres}) below target ({scen.min_final_acres})"
                )
            if new_state.population < scen.min_final_population:
                won = False
                reasons.append(
                    f"Population ({new_state.population}) below target ({scen.min_final_population})"
                )
            if new_state.starved_pct_avg > scen.max_avg_starvation_pct:
                won = False
                reasons.append(
                    f"Starvation ({new_state.starved_pct_avg:.1f}%) exceeded limit ({scen.max_avg_starvation_pct}%)"
                )

            # Mark state as ended
            marked_state = GameState(
                year=new_state.year,
                population=new_state.population,
                bushels=new_state.bushels,
                acres=new_state.acres,
                land_price=new_state.land_price,
                starved_this_year=new_state.starved_this_year,
                starved_total=new_state.starved_total,
                starved_pct_avg=new_state.starved_pct_avg,
                immigrants_this_year=new_state.immigrants_this_year,
                harvest_yield=new_state.harvest_yield,
                rats_ate=new_state.rats_ate,
                plague_struck=new_state.plague_struck,
                plague_next_year=new_state.plague_next_year,
                is_over=True,
                game_over_reason="SCENARIO_WON" if won else "SCENARIO_LOST",
            )

            status = "VICTORY" if won else "DEFEAT"
            msg = (
                f"SCENARIO VICTORY: You achieved all objectives for '{scen.title}'!"
                if won
                else f"SCENARIO DEFEAT: Objectives not met: {', '.join(reasons)}"
            )

            return EnhancedGameState(
                classic_state=marked_state,
                mode=enhanced.mode,
                scenario_id=enhanced.scenario_id,
                chronicle=updated_chronicle,
                scenario_status=status,
                status_message=msg,
            )

    return EnhancedGameState(
        classic_state=new_state,
        mode=enhanced.mode,
        scenario_id=enhanced.scenario_id,
        chronicle=updated_chronicle,
        scenario_status=enhanced.scenario_status,
        status_message=f"Year {new_state.year} commenced.",
    )


# ---------------------------------------------------------------------------
# Save & Resume Persistence
# ---------------------------------------------------------------------------

DEFAULT_SAVE_FILE = "retrorevive_save.json"


def save_game_state(
    enhanced: EnhancedGameState,
    filepath: str = DEFAULT_SAVE_FILE,
) -> bool:
    """Safely saves current game state to JSON using only standard library."""
    try:
        data = {
            "classic_state": asdict(enhanced.classic_state),
            "mode": enhanced.mode,
            "scenario_id": enhanced.scenario_id,
            "chronicle": [asdict(e) for e in enhanced.chronicle],
            "scenario_status": enhanced.scenario_status,
            "status_message": enhanced.status_message,
        }
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        return True
    except Exception as e:
        return False


def load_game_state(
    filepath: str = DEFAULT_SAVE_FILE,
) -> Optional[EnhancedGameState]:
    """Safely loads and validates game state from JSON."""
    if not os.path.exists(filepath):
        return None
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        c_dict = data["classic_state"]
        c_state = GameState(
            year=int(c_dict["year"]),
            population=int(c_dict["population"]),
            bushels=int(c_dict["bushels"]),
            acres=int(c_dict["acres"]),
            land_price=int(c_dict["land_price"]),
            starved_this_year=int(c_dict["starved_this_year"]),
            starved_total=int(c_dict["starved_total"]),
            starved_pct_avg=float(c_dict["starved_pct_avg"]),
            immigrants_this_year=int(c_dict["immigrants_this_year"]),
            harvest_yield=int(c_dict["harvest_yield"]),
            rats_ate=int(c_dict["rats_ate"]),
            plague_struck=bool(c_dict["plague_struck"]),
            plague_next_year=bool(c_dict["plague_next_year"]),
            is_over=bool(c_dict["is_over"]),
            game_over_reason=c_dict.get("game_over_reason"),
        )

        chronicle_entries = [
            ChronicleEntry(**item) for item in data.get("chronicle", [])
        ]

        return EnhancedGameState(
            classic_state=c_state,
            mode=data.get("mode", "ENHANCED"),
            scenario_id=data.get("scenario_id"),
            chronicle=chronicle_entries,
            scenario_status=data.get("scenario_status", "IN_PROGRESS"),
            status_message=data.get("status_message"),
        )
    except Exception:
        return None


def delete_save_game(filepath: str = DEFAULT_SAVE_FILE) -> bool:
    """Removes the save file if present."""
    if os.path.exists(filepath):
        try:
            os.remove(filepath)
            return True
        except Exception:
            return False
    return False
