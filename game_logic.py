"""
game_logic.py - Core simulation engine for Hammurabi (1978 Creative Computing Edition).

This module contains pure game logic and state transitions without any terminal
I/O (no input(), print(), or sys.exit()). All random events are injectably
controlled via a RandomProvider interface for deterministic testing.
"""

from dataclasses import dataclass
import math
import random
from typing import Callable, Optional

# Type alias for a random float generator returning in [0.0, 1.0)
RandomProvider = Callable[[], float]


class DefaultRNG:
    """Production random number generator using Python standard random."""

    def __init__(self, seed: Optional[int] = None) -> None:
        self._rng = random.Random(seed)

    def __call__(self) -> float:
        return self._rng.random()


class MockRNG:
    """Deterministic mock random number generator for repeatable automated tests."""

    def __init__(self, sequence: list[float]) -> None:
        self._sequence = list(sequence)
        self._index = 0

    def __call__(self) -> float:
        if self._index >= len(self._sequence):
            raise IndexError(
                f"MockRNG exhausted: test consumed more than {len(self._sequence)} values."
            )
        val = self._sequence[self._index]
        self._index += 1
        return val


@dataclass(frozen=True)
class GameState:
    \"\"\"Immutable snapshot of the Hammurabi simulation state.\"\"\"

    year: int  # Z: 1 to 10 during play; 11 triggers term end
    population: int  # P: Current living citizens
    bushels: int  # S: Grain in store / silos
    acres: int  # A: Total acres owned
    land_price: int  # Y (during trade): Cost per acre this year (17-26)
    starved_this_year: int  # D: Number of citizens starved in current year
    starved_total: int  # D1: Cumulative deaths from starvation
    starved_pct_avg: float  # P1: Average annual percentage of starved citizens
    immigrants_this_year: int  # I: Newcomers who arrived this year
    harvest_yield: int  # Y: Bushels harvested per acre (1-5)
    rats_ate: int  # E: Bushels eaten by rats
    plague_struck: bool  # Whether a plague halved the population this year
    plague_next_year: bool  # Whether a plague was rolled to strike next year
    is_over: bool  # True if the game reached any ending
    game_over_reason: Optional[str] = None  # "STEWARD_FIRED", "IMPEACHED", "COMPLETED"
    
    # --- Multi-Kingdom & Military Expansion ---
    soldiers: int = 0
    military_strength: int = 0  # Combat rating
    treasury_gold: int = 0      # Currency for diplomacy and military
    defense_level: int = 0      # Fortification bonus
    territory_influence: float = 1.0  # Regional power scale


@dataclass(frozen=True)
class TurnDecisions:
    \"\"\"Player decisions submitted for a single year.\"\"\"

    buy_acres: int = 0
    sell_acres: int = 0
    feed_bushels: int = 0
    plant_acres: int = 0
    
    # --- Expansion Decisions ---
    recruit_soldiers: int = 0
    train_soldiers_cost: int = 0
    buy_fortifications: int = 0


@dataclass(frozen=True)
class ValidationResult:
    \"\"\"Result of checking a player order against game constraints.\"\"\"

    is_valid: bool
    is_fatal: bool = False
    message: Optional[str] = None


@dataclass(frozen=True)
class EvaluationResult:
    \"\"\"Final performance review after 10 years of governing.\"\"\"

    tier: int  # 1: Fink, 2: Nero/Ivan, 3: Mediocre, 4: Fantastic
    acres_per_person: float  # L = A / P
    avg_starved_pct: float  # P1
    total_starved: int  # D1
    message: str


def calculate_land_price(rng: RandomProvider) -> int:
    \"\"\"
    Calculates land price for the year: INT(10 * RND(1)) + 17 (lines 310-312).
    Returns an integer from 17 to 26 inclusive.
    \"\"\"
    c = math.floor(10.0 * rng())
    return c + 17


def init_game(
    rng: Optional[RandomProvider] = None,
    strict_historical: bool = True,
) -> GameState:
    \"\"\"
    Initializes the game to Year 1 pre-decision state.
    Matches lines 95-110 and lines 215-260 of the 1978 BASIC listing:
      - Z = 1, P = 100 (95 + 5), S = 2800, A = 1000, Y = 3, E = 200, I = 5, D = 0.
      - Generates Year 1 land price using rng.
    \"\"\"
    provider = rng if rng is not None else DefaultRNG()
    price = calculate_land_price(provider)

    return GameState(
        year=1,
        population=100,  # 95 starting + 5 immigrants
        bushels=2800,
        acres=1000,
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


def validate_buy_land(state: GameState, acres: int) -> ValidationResult:
    \"\"\"
    Validates land purchase (lines 321-324).
    - acres < 0: steward fired immediately (fatal).
    - acres * land_price > bushels: cannot afford.
    \"\"\"
    if acres < 0:
        return ValidationResult(
            is_valid=False,
            is_fatal=True,
            message=\"HAMURABI:  I CANNOT DO WHAT YOU WISH.\\nGET YOURSELF ANOTHER STEWARD!!!!!\",
        )
    cost = acres * state.land_price
    if cost > state.bushels:
        return ValidationResult(
            is_valid=False,
            is_fatal=False,
            message=f\"HAMURABI:  THINK AGAIN.  YOU HAVE ONLY\\n{state.bushels} BUSHELS OF GRAIN.  NOW THEN,\",
        )
    return ValidationResult(is_valid=True)


def validate_sell_land(
    state: GameState,
    acres: int,
    strict_historical: bool = True,
) -> ValidationResult:
    \"\"\"
    Validates land sale (lines 341-344).
    - acres < 0: steward fired immediately (fatal).
    - strict_historical=True (line 342: IF Q < A): acres >= state.acres rejected.
    - strict_historical=False: acres > state.acres rejected (permits selling all).
    \"\"\"
    if acres < 0:
        return ValidationResult(
            is_valid=False,
            is_fatal=True,
            message=\"HAMURABI:  I CANNOT DO WHAT YOU WISH.\\nGET YOURSELF ANOTHER STEWARD!!!!!\",
        )
    if strict_historical:
        if acres >= state.acres:
            return ValidationResult(
                is_valid=False,
                is_fatal=False,
                message=f\"HAMURABI:  THINK AGAIN.  YOU OWN ONLY {state.acres} ACRES.  NOW THEN,\",
            )
    else:
        if acres > state.acres:
            return ValidationResult(
                is_valid=False,
                is_fatal=False,
                message=f\"HAMURABI:  THINK AGAIN.  YOU OWN ONLY {state.acres} ACRES.  NOW THEN,\",
            )
    return ValidationResult(is_valid=True)


def validate_feed_people(state: GameState, bushels: int) -> ValidationResult:
    \"\"\"
    Validates grain allocation to citizens (lines 411-412).
    - bushels < 0: fatal.
    - bushels > silos: cannot afford.
    \"\"\"
    if bushels < 0:
        return ValidationResult(
            is_valid=False,
            is_fatal=True,
            message=\"HAMURABI:  I CANNOT DO WHAT YOU WISH.\\nGET YOURSELF ANOTHER STEWARD!!!!!\",
        )
    if bushels > state.bushels:
        return ValidationResult(
            is_valid=False,
            is_fatal=False,
            message=f\"HAMURABI:  THINK AGAIN.  YOU HAVE ONLY\\n{state.bushels} BUSHELS OF GRAIN.  NOW THEN,\",
        )
    return ValidationResult(is_valid=True)


def validate_plant_seed(state: GameState, acres: int) -> ValidationResult:
    \"\"\"
    Validates seed planting (lines 441-447).
    - acres < 0: fatal.
    - acres > land owned: no space.
    - acres > labor limit (10 acres/person): not enough workers.
    - seed > silos (1 bushel / 2 acres): cannot afford.
    \"\"\"
    if acres < 0:
        return ValidationResult(
            is_valid=False,
            is_fatal=True,
            message=\"HAMURABI:  I CANNOT DO WHAT YOU WISH.\\nGET YOURSELF ANOTHER STEWARD!!!!!\",
        )
    if acres > state.acres:
        return ValidationResult(
            is_valid=False,
            is_fatal=False,
            message=f\"HAMURABI:  THINK AGAIN.  YOU OWN ONLY {state.acres} ACRES.  NOW THEN,\",
        )
    if acres // 2 > state.bushels:
        return ValidationResult(
            is_valid=False,
            is_fatal=False,
            message=f\"HAMURABI:  THINK AGAIN.  YOU HAVE ONLY\\n{state.bushels} BUSHELS OF GRAIN.  NOW THEN,\",
        )
    if acres > 10 * state.population:
        return ValidationResult(
            is_valid=False,
            is_fatal=False,
            message=f\"BUT YOU HAVE ONLY {state.population} PEOPLE TO TEND THE FIELDS!  NOW THEN,\",
        )
    return ValidationResult(is_valid=True)


def step_year(
    state: GameState,
    decisions: TurnDecisions,
    rng: Optional[RandomProvider] = None,
) -> GameState:
    \"\"\"
    Executes one turn of the simulation (lines 215-560).
    Calculates harvest, immigration, plague, and rat destruction.
    Returns the new immutable state for the start of the next year.
    \"\"\"
    provider = rng if rng is not None else DefaultRNG()

    # 1. Update resources from trade/feeding/planting
    # Note: validation ensures these are safe
    new_acres = state.acres + decisions.buy_acres - decisions.sell_acres
    new_bushels = state.bushels - (decisions.buy_acres * state.land_price) + \\
                  (decisions.sell_acres * state.land_price) - decisions.feed_bushels - \\
                  (decisions.plant_acres // 2)

    # 2. Harvest results (lines 510-515)
    harvest_yield = math.floor(5.0 * provider()) + 1
    harvested = decisions.plant_acres * harvest_yield

    # 3. Rat destruction (lines 521-525)
    rats_ate = 0
    c = math.floor(5.0 * provider()) + 1
    if math.floor(c / 2.0) == (c / 2.0):
        rats_ate = math.floor(new_bushels / c)
    new_bushels = new_bushels + harvested - rats_ate

    # 4. Immigration (lines 531-533)
    c = math.floor(5.0 * provider()) + 1
    immigrants = math.floor(c * (20 * new_acres + new_bushels) / state.population / 100.0) + 1

    # 5. Population and Starvation (lines 541-550)
    # Each person needs 20 bushels to survive.
    fed_people = decisions.feed_bushels // 20
    starved = max(0, state.population - fed_people)

    # Impeachment check: > 45% starved in one year
    if starved > 0.45 * state.population:
        return state.__class__(
            year=state.year,
            population=state.population - starved,
            bushels=new_bushels,
            acres=new_acres,
            land_price=state.land_price,
            starved_this_year=starved,
            starved_total=state.starved_total + starved,
            starved_pct_avg=state.starved_pct_avg,
            immigrants_this_year=0,
            harvest_yield=harvest_yield,
            rats_ate=rats_ate,
            plague_struck=False,
            plague_next_year=False,
            is_over=True,
            game_over_reason=\"IMPEACHED\",
            soldiers=state.soldiers,
            military_strength=state.military_strength,
            treasury_gold=state.treasury_gold,
            defense_level=state.defense_level,
            territory_influence=state.territory_influence
        )

    # 6. Plague check (lines 215-218)
    plague_struck = False
    new_pop = state.population - starved + immigrants
    if provider() < 0.15:  # 15% chance of plague halving population
        plague_struck = True
        new_pop = math.floor(new_pop / 2.0)

    # 7. Progress Year
    new_year = state.year + 1
    new_price = calculate_land_price(provider)
    
    # Update average starvation pct
    total_starved = state.starved_total + starved
    # Simple moving average over years
    new_avg_starved = ((state.starved_pct_avg * (state.year - 1)) + (starved / state.population * 100)) / state.year

    # --- Military & Economy updates ---
    new_soldiers = state.soldiers + decisions.recruit_soldiers
    # Military cost: 10 bushels per soldier per year (maintenance)
    soldier_cost = new_soldiers * 10
    if new_bushels >= soldier_cost:
        new_bushels -= soldier_cost
    else:
        # Desertion if not fed
        desertion = (soldier_cost - new_bushels) // 10
        new_soldiers = max(0, new_soldiers - desertion)
        new_bushels = 0
    
    # Treasury gains from trade and taxes (simplified)
    tax_revenue = math.floor(new_pop * 2.5) # 2.5 gold per person
    new_treasury = state.treasury_gold + tax_revenue - decisions.train_soldiers_cost - (decisions.buy_fortifications * 50)
    
    new_defense = state.defense_level + decisions.buy_fortifications
    new_strength = new_soldiers * (1 + new_defense * 0.1)

    is_over = new_year > 10

    return GameState(
        year=new_year,
        population=new_pop,
        bushels=new_bushels,
        acres=new_acres,
        land_price=new_price,
        starved_this_year=starved,
        starved_total=total_starved,
        starved_pct_avg=new_avg_starved,
        immigrants_this_year=immigrants,
        harvest_yield=harvest_yield,
        rats_ate=rats_ate,
        plague_struck=plague_struck,
        plague_next_year=False,
        is_over=is_over,
        game_over_reason=\"COMPLETED\" if is_over else None,
        soldiers=new_soldiers,
        military_strength=int(new_strength),
        treasury_gold=new_treasury,
        defense_level=new_defense,
        territory_influence=state.territory_influence
    )


def evaluate_term(state: GameState) -> EvaluationResult:
    \"\"\"
    Final performance evaluation (lines 720-860).
    \"\"\"
    L = state.acres / max(1, state.population)
    P1 = state.starved_pct_avg
    D1 = state.starved_total

    if P1 > 33 or L < 7:
        tier = 1
        msg = \"IN YOUR 10-YEAR TERM OF OFFICE, {0} PERCENT OF THE\\nPOPULATION STARVED PER YEAR ON AVERAGE. A TOTAL OF {1}\\nPEOPLE DIED!! YOU HAVE BEEN DECLARED A 'FINK'!!\".format(int(P1), D1)
    elif P1 > 10 or L < 9:
        tier = 2
        msg = \"YOUR PERFORMANCE COULD HAVE BEEN WORSE, BUT A\\nCONGRESSIONAL INVESTIGATION OF YOUR MISMANAGEMENT\\nIS IN ORDER. {0} PEOPLE DIED IN ALL.\".format(D1)
    elif P1 > 3 or L < 10:
        tier = 3
        msg = \"YOUR HEAVY-HANDED GOVERNING IS TYPICAL OF THE\\nMEDIOCRE. {0} PEOPLE DIED IN ALL.\".format(D1)
    else:
        tier = 4
        msg = \"A FANTASTIC PERFORMANCE!!! CHARLEMAGNE, DISRAELI, AND\\nJEFFERSON COMBINED COULD NOT HAVE DONE BETTER!\"

    return EvaluationResult(
        tier=tier,
        acres_per_person=L,
        avg_starved_pct=P1,
        total_starved=D1,
        message=msg
    )
