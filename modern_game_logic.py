"""
modern_game_logic.py - Enhanced Mode logic for RetroRevive: Hammurabi Reimagined.

This module provides genuinely useful gameplay enhancements for modern players
while keeping historical rules separate:
- Interactive Scenarios with explicit goals and victory conditions
- Contextual Royal Advisors (Vizier, Granary Master, Surveyor)
- Comprehensive Chronicle & Event Log (year-by-year decisions and stats)
- Safe Save & Resume game persistence via standard-library JSON
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
    \"\"\"Defines a challenge scenario with specific starting conditions and objectives.\"\"\"

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
    \"drought\": ScenarioDefinition(
        scenario_id=\"drought\",
        title=\"The Great Drought\",
        subtitle=\"5-Year Survival Challenge\",
        description=(
            \"Severe dry winds parch Sumeria. Starting with depleted grain silos, \"
            \"you must manage rations carefully, avoid famine, and stockpile at \"
            \"least 2,500 bushels by Year 5.\"
        ),
        target_year=5,
        starting_population=100,
        starting_bushels=1800,  # Starts with scarce grain
        starting_acres=1000,
        min_final_bushels=2500,
        max_avg_starvation_pct=5.0,
    ),
    \"boom\": ScenarioDefinition(
        scenario_id=\"boom\",
        title=\"The Population Boom\",
        subtitle=\"7-Year Expansion Challenge\",
        description=(
            \"Word of Sumeria's wealth spreads, bringing large waves of migrants. \"
            \"You must expand your farmland to at least 1,300 acres to provide \"
            \"enough work and food for the growing city.\"
        ),
        target_year=7,
        starting_population=100,
        starting_bushels=3000,
        starting_acres=1000,
        min_final_acres=1300,
        min_final_population=120,
        max_avg_starvation_pct=3.0,
    ),
    \"granary\": ScenarioDefinition(
        scenario_id=\"granary\",
        title=\"The Granary Defense\",
        subtitle=\"6-Year Stockpile Challenge\",
        description=(
            \"Aggressive desert rodents threaten Sumeria's food reserves. Protect \"
            \"your silos, cultivate harvests diligently, and finish Year 6 with \"
            \"at least 3,500 bushels stored in reserve.\"
        ),
        target_year=6,
        starting_population=100,
        starting_bushels=2800,
        starting_acres=1000,
        min_final_bushels=3500,
        max_avg_starvation_pct=4.0,
    ),
    \"empire\": ScenarioDefinition(
        scenario_id=\"empire\",
        title=\"Empire of Babylon\",
        subtitle=\"10-Year Master Challenge\",
        description=(
            \"Govern for a full 10-year term and establish an ancient empire: \"
            \"surpass 140 population, expand beyond 1,400 acres, and secure a \"
            \"legendary Charlemagne-tier final performance evaluation.\"
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
    \"\"\"Actionable counsel provided by the Royal Council.\"\"\"

    vizier: str
    granary_master: str
    surveyor: str
    recommended_feed: int
    recommended_plant: int
    land_price_rating: str  # \"CHEAP\", \"FAIR\", \"EXPENSIVE\"
    recommended_buy: int = 0
    recommended_sell: int = 0


@dataclass
class ChronicleEntry:
    \"\"\"Historical record of decisions and consequences for one year.\"\"\"

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
    \"\"\"Simulated kingdom with its own AI and economy.\"\"\"
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
    personality: str = \"BALANCED\" # \"AGGRESSIVE\", \"DEFENSIVE\", \"BALANCED\", \"EXPANSIONIST\"
    
    def simulate_turn(self, rng: RandomProvider) -> None:
        \"\"\"Independent decision making for rival kingdom.\"\"\"
        # Simple AI logic based on personality
        needed_food = self.population * 20
        
        # 1. Feeding
        if self.bushels >= needed_food:
            self.bushels -= needed_food
        else:
            starved = (needed_food - self.bushels) // 20
            self.population = max(10, self.population - starved)
            self.bushels = 0
            
        # 2. Farming (simplified)
        harvest = self.acres * (int(5 * rng()) + 1)
        self.bushels += harvest
        
        # 3. Growth
        self.population += int(self.population * 0.05 * rng())
        
        # 4. Military development
        if self.personality == \"AGGRESSIVE\":
            recruit = int(self.population * 0.1)
            self.soldiers += recruit
            self.treasury -= recruit * 2
        elif self.personality == \"EXPANSIONIST\":
            buy = int(self.acres * 0.05)
            self.acres += buy
            self.bushels -= buy * 20
        
        # Maintain minimums
        self.soldiers = max(5, self.soldiers)
        self.treasury += int(self.population * 2) # Basic tax


@dataclass
class DiplomaticRelation:
    \"\"\"Status of relationship between player and a rival kingdom.\"\"\"
    rival_id: str
    status: str = \"NEUTRAL\" # \"ALLY\", \"NEUTRAL\", \"HOSTILE\", \"WAR\"
    opinion: int = 50       # 0 to 100
    trade_agreement: bool = False
    intelligence_level: int = 0 # 0 (None) to 100 (Full)


@dataclass
class EnhancedGameState:
    \"\"\"State wrapper for Enhanced Mode and Scenarios.\"\"\"

    classic_state: GameState
    mode: str = \"ENHANCED\"  # \"ENHANCED\" or \"SCENARIO\"
    scenario_id: Optional[str] = None
    chronicle: List[ChronicleEntry] = field(default_factory=list)
    scenario_status: str = \"IN_PROGRESS\"  # \"IN_PROGRESS\", \"VICTORY\", \"DEFEAT\"
    status_message: Optional[str] = None
    
    # --- Multi-Kingdom Extension ---
    rivals: List[RivalKingdom] = field(default_factory=list)
    diplomacy: List[DiplomaticRelation] = field(default_factory=list)
    global_events: List[str] = field(default_factory=list)


def init_enhanced_game(
    mode: str = \"ENHANCED\",
    scenario_id: Optional[str] = None,
    rng: Optional[RandomProvider] = None,
    strict_historical: bool = True,
) -> EnhancedGameState:
    \"\"\"Initializes a new Enhanced Mode or Scenario session.\"\"\"
    provider = rng if rng is not None else DefaultRNG()

    if mode == \"SCENARIO\" and scenario_id in SCENARIOS:
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
            soldiers=20,
            military_strength=100,
            treasury_gold=500,
            defense_level=1,
            territory_influence=1.0,
        )
        egs = EnhancedGameState(
            classic_state=base_state,
            mode=\"SCENARIO\",
            scenario_id=scenario_id,
        )
    else:
        base_state = init_game(provider, strict_historical)
        egs = EnhancedGameState(classic_state=base_state, mode=\"ENHANCED\")

    # Initialize Rival Kingdoms
    egs.rivals = [
        RivalKingdom(\"elam\", \"Elam\", \"King Shutruk\", 120, 2500, 1100, 30, 150, 400, 1.2, personality=\"AGGRESSIVE\"),
        RivalKingdom(\"assyria\", \"Assyria\", \"Tiglath-Pileser\", 150, 3500, 1500, 50, 250, 600, 1.5, personality=\"EXPANSIONIST\"),
        RivalKingdom(\"sumer\", \"Ur of Sumer\", \"Ur-Nammu\", 90, 2200, 900, 15, 80, 800, 0.9, personality=\"DEFENSIVE\"),
    ]
    egs.diplomacy = [
        DiplomaticRelation(\"elam\", status=\"NEUTRAL\", opinion=40),
        DiplomaticRelation(\"assyria\", status=\"HOSTILE\", opinion=20),
        DiplomaticRelation(\"sumer\", status=\"NEUTRAL\", opinion=65),
    ]

    return egs


def step_enhanced_year(
    enhanced: EnhancedGameState,
    decisions: TurnDecisions,
    rng: Optional[RandomProvider] = None,
) -> EnhancedGameState:
    \"\"\"Advances the entire living world by one year.\"\"\"
    provider = rng if rng is not None else DefaultRNG()
    
    # 1. Record 'before' snapshot
    before = enhanced.classic_state

    # 2. Step the player's kingdom (authoritative)
    new_classic = step_year(before, decisions, provider)
    
    # 3. Step Rival Kingdoms
    for rival in enhanced.rivals:
        rival.simulate_turn(provider)
        
    # 4. Generate global events
    enhanced.global_events = []
    if provider() < 0.2:
        enhanced.global_events.append(\"A regional locust swarm has reduced all harvests.\")
    if provider() < 0.1:
        enhanced.global_events.append(\"Trade routes to the East are blocked by storms.\")

    # 5. Create chronicle entry
    entry = ChronicleEntry(
        year=before.year,
        population_start=before.population,
        population_end=new_classic.population,
        starved=new_classic.starved_this_year,
        immigrants=new_classic.immigrants_this_year,
        plague=new_classic.plague_struck,
        acres=new_classic.acres,
        bushels=new_classic.bushels,
        land_price=before.land_price,
        bought_acres=decisions.buy_acres,
        sold_acres=decisions.sell_acres,
        fed_bushels=decisions.feed_bushels,
        planted_acres=decisions.plant_acres,
        yield_rate=new_classic.harvest_yield,
        harvested_total=decisions.plant_acres * new_classic.harvest_yield,
        rats_ate=new_classic.rats_ate,
    )
    
    # 6. Check Scenario Victory/Defeat
    status = enhanced.scenario_status
    msg = enhanced.status_message
    
    if enhanced.mode == \"SCENARIO\" and enhanced.scenario_id in SCENARIOS:
        scen = SCENARIOS[enhanced.scenario_id]
        
        # Check Defeat
        if new_classic.game_over_reason == \"IMPEACHED\":
            status = \"DEFEAT\"
            msg = \"SCENARIO FAILED: You were impeached due to high starvation.\"
        elif new_classic.year > scen.target_year:
            # Reached time limit, evaluate objectives
            victory = True
            if new_classic.bushels < scen.min_final_bushels: victory = False
            if new_classic.acres < scen.min_final_acres: victory = False
            if new_classic.population < scen.min_final_population: victory = False
            if new_classic.starved_pct_avg > scen.max_avg_starvation_pct: victory = False
            
            if victory:
                status = \"VICTORY\"
                msg = f\"SCENARIO COMPLETE: You have successfully mastered {scen.title}!\"
            else:
                status = \"DEFEAT\"
                msg = \"SCENARIO FAILED: You reached the time limit but missed the objectives.\"
    
    # Reconstruct state
    new_enhanced = EnhancedGameState(
        classic_state=new_classic,
        mode=enhanced.mode,
        scenario_id=enhanced.scenario_id,
        chronicle=enhanced.chronicle + [entry],
        scenario_status=status,
        status_message=msg,
        rivals=enhanced.rivals,
        diplomacy=enhanced.diplomacy,
        global_events=enhanced.global_events,
    )
    
    return new_enhanced


def get_advisor_advice(state: GameState) -> AdvisorAdvice:
    \"\"\"Calculates recommendations for the current year.\"\"\"
    price = state.land_price
    pop = state.population
    bush = state.bushels
    
    # Vizier
    if bush < pop * 20:
        vizier = \"Sire, we have not enough grain to feed everyone. Sell land or expect deaths.\"
    elif bush > pop * 50:
        vizier = \"Our silos overflow! It is a time for great expansion or investment.\"
    else:
        vizier = \"The kingdom is stable. Maintain a steady hand, my King.\"
        
    # Surveyor
    if price < 19:
        surveyor = \"Land is exceptionally cheap. Buy as much as possible!\"
        rating = \"CHEAP\"
    elif price > 24:
        surveyor = \"Acres are overpriced. Consider selling if you need grain.\"
        rating = \"EXPENSIVE\"
    else:
        surveyor = \"Land prices are fair for Sumeria.\"
        rating = \"FAIR\"
        
    # Granary Master
    harvestable = min(state.acres, pop * 10)
    seed_req = harvestable // 2
    granary = f\"We can plant {harvestable} acres. You will need {seed_req} bushels for seed.\"
    
    return AdvisorAdvice(
        vizier=vizier,
        granary_master=granary,
        surveyor=surveyor,
        recommended_feed=pop * 20,
        recommended_plant=harvestable,
        land_price_rating=rating,
        recommended_buy=0,
        recommended_sell=0,
    )


def save_game(enhanced: EnhancedGameState, slot: int = 1) -> bool:
    \"\"\"Persists game state to a local JSON file.\"\"\"
    try:
        data = {
            \"mode\": enhanced.mode,
            \"scenario_id\": enhanced.scenario_id,
            \"classic\": asdict(enhanced.classic_state),
            \"chronicle\": [asdict(e) for e in enhanced.chronicle],
            \"rivals\": [asdict(r) for r in enhanced.rivals],
            \"diplomacy\": [asdict(d) for d in enhanced.diplomacy],
        }
        filename = f\"retrorevive_save_slot_{slot}.json\"
        with open(filename, \"w\") as f:
            json.dump(data, f)
        return True
    except Exception:
        return False


def load_game(slot: int = 1) -> Optional[EnhancedGameState]:
    \"\"\"Loads game state from a local JSON file.\"\"\"
    filename = f\"retrorevive_save_slot_{slot}.json\"
    if not os.path.exists(filename):
        return None
        
    try:
        with open(filename, \"r\") as f:
            data = json.load(f)
            
        # Reconstruct GameState
        c = data[\"classic\"]
        # Handle older saves missing military keys
        base = GameState(
            year=c[\"year\"], population=c[\"population\"], bushels=c[\"bushels\"],
            acres=c[\"acres\"], land_price=c[\"land_price\"],
            starved_this_year=c[\"starved_this_year\"], starved_total=c[\"starved_total\"],
            starved_pct_avg=c[\"starved_pct_avg\"], immigrants_this_year=c[\"immigrants_this_year\"],
            harvest_yield=c[\"harvest_yield\"], rats_ate=c[\"rats_ate\"],
            plague_struck=c[\"plague_struck\"], plague_next_year=c[\"plague_next_year\"],
            is_over=c[\"is_over\"], game_over_reason=c.get(\"game_over_reason\"),
            soldiers=c.get(\"soldiers\", 20),
            military_strength=c.get(\"military_strength\", 100),
            treasury_gold=c.get(\"treasury_gold\", 500),
            defense_level=c.get(\"defense_level\", 1),
            territory_influence=c.get(\"territory_influence\", 1.0)
        )
        
        egs = EnhancedGameState(
            classic_state=base,
            mode=data.get(\"mode\", \"ENHANCED\"),
            scenario_id=data.get(\"scenario_id\"),
            chronicle=[ChronicleEntry(**e) for e in data.get(\"chronicle\", [])]
        )
        
        if \"rivals\" in data:
            egs.rivals = [RivalKingdom(**r) for r in data[\"rivals\"]]
        if \"diplomacy\" in data:
            egs.diplomacy = [DiplomaticRelation(**d) for d in data[\"diplomacy\"]]
            
        return egs
    except Exception:
        return None
