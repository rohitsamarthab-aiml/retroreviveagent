"""
modern_game_logic.py - Enhanced Mode logic for RetroRevive: Hammurabi Reimagined.
- Multi-Kingdom simulation and Diplomacy
"""

from dataclasses import asdict, dataclass, field
import json
import math
import os
import random
from typing import Any, Dict, List, Optional, Tuple

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
    scenario_id: str
    title: str
    subtitle: str
    description: str
    target_year: int
    starting_population: int = 100
    starting_bushels: int = 2800
    starting_acres: int = 1000
    min_final_bushels: int = 0
    min_final_acres: int = 0
    min_final_population: int = 0
    max_avg_starvation_pct: float = 33.0
    zero_starvation_required: bool = False


SCENARIOS: Dict[str, ScenarioDefinition] = {
    "drought": ScenarioDefinition(
        scenario_id="drought", title="The Great Drought", subtitle="5-Year Survival Challenge",
        description="Depleted grain silos survival.", target_year=5, starting_bushels=1800, min_final_bushels=2500, max_avg_starvation_pct=5.0,
    ),
    "boom": ScenarioDefinition(
        scenario_id="boom", title="The Population Boom", subtitle="7-Year Expansion Challenge",
        description="Grow population and land.", target_year=7, min_final_acres=1300, min_final_population=120, max_avg_starvation_pct=3.0,
    ),
    "granary": ScenarioDefinition(
        scenario_id="granary", title="The Granary Defense", subtitle="6-Year Stockpile Challenge",
        description="Protect against rats.", target_year=6, min_final_bushels=3500, max_avg_starvation_pct=4.0,
    ),
    "empire": ScenarioDefinition(
        scenario_id="empire", title="Empire of Babylon", subtitle="10-Year Master Challenge",
        description="Establish ancient empire.", target_year=10, min_final_acres=1400, min_final_population=130, max_avg_starvation_pct=3.0,
    ),
}


@dataclass
class AdvisorAdvice:
    vizier: str
    granary_master: str
    surveyor: str
    recommended_feed: int
    recommended_plant: int
    land_price_rating: str
    recommended_buy: int = 0
    recommended_sell: int = 0


@dataclass
class ChronicleEntry:
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
class RivalKingdom:
    id: str
    name: str
    leader: str
    population: int
    bushels: int
    acres: int
    soldiers: int
    military_strength: int
    treasury: int
    territory: float
    land_health: float = 1.0
    personality: str = "BALANCED" # "AGGRESSIVE", "DEFENSIVE", "BALANCED", "EXPANSIONIST"
    
    def simulate_turn(self, rng: RandomProvider) -> None:
        needed_food = self.population * 20
        if self.bushels >= needed_food:
            self.bushels -= needed_food
        else:
            starved = (needed_food - self.bushels) // 20
            self.population = max(10, self.population - starved)
            self.bushels = 0
        harvest = self.acres * (int(5 * rng()) + 1)
        self.bushels += harvest
        self.population += int(self.population * 0.05 * rng())
        if self.personality == "AGGRESSIVE":
            recruit = int(self.population * 0.1)
            self.soldiers += recruit
            self.treasury -= recruit * 2
        elif self.personality == "EXPANSIONIST":
            buy = int(self.acres * 0.05)
            self.acres += buy
            self.bushels -= buy * 20
        self.soldiers = max(5, self.soldiers)
        self.treasury += int(self.population * 2)


@dataclass
class DiplomaticRelation:
    rival_id: str
    status: str = "NEUTRAL" # "ALLY", "NEUTRAL", "HOSTILE", "WAR"
    opinion: int = 50
    trade_agreement: bool = False
    intelligence_level: int = 0


@dataclass
class EnhancedGameState:
    classic_state: GameState
    mode: str = "ENHANCED"
    scenario_id: Optional[str] = None
    chronicle: List[ChronicleEntry] = field(default_factory=list)
    scenario_status: str = "IN_PROGRESS"
    status_message: Optional[str] = None
    rivals: List[RivalKingdom] = field(default_factory=list)
    diplomacy: List[DiplomaticRelation] = field(default_factory=list)
    global_events: List[str] = field(default_factory=list)


def init_enhanced_game(
    mode: str = "ENHANCED", scenario_id: Optional[str] = None,
    rng: Optional[RandomProvider] = None, strict_historical: bool = True,
) -> EnhancedGameState:
    provider = rng if rng is not None else DefaultRNG()
    if mode == "SCENARIO" and scenario_id in SCENARIOS:
        scen = SCENARIOS[scenario_id]
        base_state = GameState(
            year=1, population=scen.starting_population, bushels=scen.starting_bushels,
            acres=scen.starting_acres, land_price=calculate_land_price(provider),
            starved_this_year=0, starved_total=0, starved_pct_avg=0.0,
            immigrants_this_year=5, harvest_yield=3, rats_ate=200,
            plague_struck=False, plague_next_year=False, is_over=False,
            soldiers=20, military_strength=100, treasury_gold=500, defense_level=1,
        )
        egs = EnhancedGameState(classic_state=base_state, mode="SCENARIO", scenario_id=scenario_id)
    else:
        base_state = init_game(provider, strict_historical)
        egs = EnhancedGameState(classic_state=base_state, mode="ENHANCED")

    egs.rivals = [
        RivalKingdom("elam", "Elam", "King Shutruk", 120, 2500, 1100, 30, 150, 400, 1.2, personality="AGGRESSIVE"),
        RivalKingdom("assyria", "Assyria", "Tiglath-Pileser", 150, 3500, 1500, 50, 250, 600, 1.5, personality="EXPANSIONIST"),
        RivalKingdom("sumer", "Ur of Sumer", "Ur-Nammu", 90, 2200, 900, 15, 80, 800, 0.9, personality="DEFENSIVE"),
    ]
    egs.diplomacy = [
        DiplomaticRelation("elam", status="NEUTRAL", opinion=40),
        DiplomaticRelation("assyria", status="HOSTILE", opinion=20),
        DiplomaticRelation("sumer", status="NEUTRAL", opinion=65),
    ]
    return egs


def step_enhanced_year(
    enhanced: EnhancedGameState, decisions: TurnDecisions, rng: Optional[RandomProvider] = None,
) -> EnhancedGameState:
    provider = rng if rng is not None else DefaultRNG()
    before = enhanced.classic_state
    new_classic = step_year(before, decisions, provider)
    for rival in enhanced.rivals:
        rival.simulate_turn(provider)
    enhanced.global_events = []
    if provider() < 0.2: enhanced.global_events.append("Locust swarm reduced harvests.")
    
    entry = ChronicleEntry(
        year=before.year, population_start=before.population, population_end=new_classic.population,
        starved=new_classic.starved_this_year, immigrants=new_classic.immigrants_this_year,
        plague=new_classic.plague_struck, acres=new_classic.acres, bushels=new_classic.bushels,
        land_price=before.land_price, bought_acres=decisions.buy_acres, sold_acres=decisions.sell_acres,
        fed_bushels=decisions.feed_bushels, planted_acres=decisions.plant_acres,
        yield_rate=new_classic.harvest_yield, harvested_total=decisions.plant_acres * new_classic.harvest_yield,
        rats_ate=new_classic.rats_ate,
    )
    
    status, msg = enhanced.scenario_status, enhanced.status_message
    if enhanced.mode == "SCENARIO" and enhanced.scenario_id in SCENARIOS:
        scen = SCENARIOS[enhanced.scenario_id]
        if new_classic.game_over_reason == "IMPEACHED":
            status, msg = "DEFEAT", "SCENARIO FAILED: Impeached."
        elif new_classic.year > scen.target_year:
            victory = all([
                new_classic.bushels >= scen.min_final_bushels,
                new_classic.acres >= scen.min_final_acres,
                new_classic.population >= scen.min_final_population,
                new_classic.starved_pct_avg <= scen.max_avg_starvation_pct
            ])
            status, msg = ("VICTORY", f"SCENARIO COMPLETE: {scen.title}") if victory else ("DEFEAT", "SCENARIO FAILED: Goals missed.")
    
    return EnhancedGameState(
        classic_state=new_classic, mode=enhanced.mode, scenario_id=enhanced.scenario_id,
        chronicle=enhanced.chronicle + [entry], scenario_status=status, status_message=msg,
        rivals=enhanced.rivals, diplomacy=enhanced.diplomacy, global_events=enhanced.global_events,
    )


def get_advisor_advice(state: GameState) -> AdvisorAdvice:
    pop, bush = state.population, state.bushels
    vizier = "Stable."
    if bush < pop * 20: vizier = "Famine risk."
    elif bush > pop * 50: vizier = "Surplus."
    
    price = state.land_price
    rating = "FAIR"
    if price < 19: rating = "CHEAP"
    elif price > 24: rating = "EXPENSIVE"
    
    harvestable = min(state.acres, pop * 10)
    return AdvisorAdvice(
        vizier=vizier, granary_master=f"Plant {harvestable}.", surveyor="Fair.",
        recommended_feed=pop * 20, recommended_plant=harvestable, land_price_rating=rating,
    )
