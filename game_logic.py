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
    """Immutable snapshot of the Hammurabi simulation state."""

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


@dataclass(frozen=True)
class TurnDecisions:
    """Player decisions submitted for a single year."""

    buy_acres: int = 0
    sell_acres: int = 0
    feed_bushels: int = 0
    plant_acres: int = 0


@dataclass(frozen=True)
class ValidationResult:
    """Result of checking a player order against game constraints."""

    is_valid: bool
    is_fatal: bool = False
    message: Optional[str] = None


@dataclass(frozen=True)
class EvaluationResult:
    """Final performance review after 10 years of governing."""

    tier: int  # 1: Fink, 2: Nero/Ivan, 3: Mediocre, 4: Fantastic
    acres_per_person: float  # L = A / P
    avg_starved_pct: float  # P1
    total_starved: int  # D1
    message: str


def calculate_land_price(rng: RandomProvider) -> int:
    """
    Calculates land price for the year: INT(10 * RND(1)) + 17 (lines 310-312).
    Returns an integer from 17 to 26 inclusive.
    """
    c = math.floor(10.0 * rng())
    return c + 17


def init_game(
    rng: Optional[RandomProvider] = None,
    strict_historical: bool = True,
) -> GameState:
    """
    Initializes the game to Year 1 pre-decision state.
    Matches lines 95-110 and lines 215-260 of the 1978 BASIC listing:
      - Z = 1, P = 100 (95 + 5), S = 2800, A = 1000, Y = 3, E = 200, I = 5, D = 0.
      - Generates Year 1 land price using rng.
    """
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
    )


def validate_buy_land(state: GameState, acres: int) -> ValidationResult:
    """
    Validates land purchase (lines 321-324).
    - acres < 0: steward fired immediately (fatal).
    - acres * land_price > bushels: cannot afford.
    """
    if acres < 0:
        return ValidationResult(
            is_valid=False,
            is_fatal=True,
            message="HAMURABI:  I CANNOT DO WHAT YOU WISH.\nGET YOURSELF ANOTHER STEWARD!!!!!",
        )
    cost = acres * state.land_price
    if cost > state.bushels:
        return ValidationResult(
            is_valid=False,
            is_fatal=False,
            message=f"HAMURABI:  THINK AGAIN.  YOU HAVE ONLY\n{state.bushels} BUSHELS OF GRAIN.  NOW THEN,",
        )
    return ValidationResult(is_valid=True)


def validate_sell_land(
    state: GameState,
    acres: int,
    strict_historical: bool = True,
) -> ValidationResult:
    """
    Validates land sale (lines 341-344).
    - acres < 0: steward fired immediately (fatal).
    - strict_historical=True (line 342: IF Q < A): acres >= state.acres rejected.
    - strict_historical=False: acres > state.acres rejected (permits selling all).
    """
    if acres < 0:
        return ValidationResult(
            is_valid=False,
            is_fatal=True,
            message="HAMURABI:  I CANNOT DO WHAT YOU WISH.\nGET YOURSELF ANOTHER STEWARD!!!!!",
        )
    if strict_historical:
        if acres >= state.acres:
            return ValidationResult(
                is_valid=False,
                is_fatal=False,
                message=f"HAMURABI:  THINK AGAIN.  YOU OWN ONLY {state.acres} ACRES.  NOW THEN,",
            )
    else:
        if acres > state.acres:
            return ValidationResult(
                is_valid=False,
                is_fatal=False,
                message=f"HAMURABI:  THINK AGAIN.  YOU OWN ONLY {state.acres} ACRES.  NOW THEN,",
            )
    return ValidationResult(is_valid=True)


def validate_feed_people(state: GameState, bushels: int) -> ValidationResult:
    """
    Validates grain allocated for food (lines 411-422).
    - bushels < 0: steward fired immediately (fatal).
    - bushels > state.bushels: cannot feed more grain than currently in store.
    """
    if bushels < 0:
        return ValidationResult(
            is_valid=False,
            is_fatal=True,
            message="HAMURABI:  I CANNOT DO WHAT YOU WISH.\nGET YOURSELF ANOTHER STEWARD!!!!!",
        )
    if bushels > state.bushels:
        return ValidationResult(
            is_valid=False,
            is_fatal=False,
            message=f"HAMURABI:  THINK AGAIN.  YOU HAVE ONLY\n{state.bushels} BUSHELS OF GRAIN.  NOW THEN,",
        )
    return ValidationResult(is_valid=True)


def validate_plant_seed(
    state: GameState,
    acres: int,
    available_grain: int,
    strict_historical: bool = True,
) -> ValidationResult:
    """
    Validates acreage planted with seed (lines 441-470).
    - acres < 0: steward fired immediately (fatal).
    - acres > state.acres: cannot plant more than owned.
    - acres // 2 > available_grain: need 1 bushel for every 2 acres.
    - strict_historical=True (line 455: IF D < 10 * P): acres >= 10 * population rejected.
    - strict_historical=False: acres > 10 * population rejected.
    """
    if acres < 0:
        return ValidationResult(
            is_valid=False,
            is_fatal=True,
            message="HAMURABI:  I CANNOT DO WHAT YOU WISH.\nGET YOURSELF ANOTHER STEWARD!!!!!",
        )
    if acres > state.acres:
        return ValidationResult(
            is_valid=False,
            is_fatal=False,
            message=f"HAMURABI:  THINK AGAIN.  YOU OWN ONLY {state.acres} ACRES.  NOW THEN,",
        )
    seed_required = acres // 2
    if seed_required > available_grain:
        return ValidationResult(
            is_valid=False,
            is_fatal=False,
            message=f"HAMURABI:  THINK AGAIN.  YOU HAVE ONLY\n{available_grain} BUSHELS OF GRAIN.  NOW THEN,",
        )
    labor_limit = 10 * state.population
    if strict_historical:
        if acres >= labor_limit:
            return ValidationResult(
                is_valid=False,
                is_fatal=False,
                message=f"BUT YOU HAVE ONLY {state.population} PEOPLE TO TEND THE FIELDS!  NOW THEN,",
            )
    else:
        if acres > labor_limit:
            return ValidationResult(
                is_valid=False,
                is_fatal=False,
                message=f"BUT YOU HAVE ONLY {state.population} PEOPLE TO TEND THE FIELDS!  NOW THEN,",
            )
    return ValidationResult(is_valid=True)


def step_year(
    state: GameState,
    decisions: TurnDecisions,
    rng: Optional[RandomProvider] = None,
    strict_historical: bool = True,
) -> GameState:
    """
    Advances the simulation by one year applying player decisions and random events.
    Matches lines 330-780 of the 1978 BASIC code:
      1. Land transactions (buy or sell).
      2. Deduct food grain.
      3. Deduct seed grain (INT(D/2)).
      4. Harvest roll: Y in [1..5], H = D * Y.
      5. Rat roll: C in [1..5]; if even, E = INT(S / C); S = S - E + H.
      6. Immigrants roll: C in [1..5]; I = INT(C * (20*A + S) / P / 100 + 1).
      7. Starvation & 45% impeachment check.
      8. Plague roll for next year: Q = INT(10 * (2 * RND(1) - 0.3)).
      9. Advance year: Z = Z + 1, apply immigrants, apply plague if triggered.
    """
    provider = rng if rng is not None else DefaultRNG()

    # Apply land transactions
    current_acres = state.acres
    current_bushels = state.bushels

    if decisions.buy_acres > 0:
        current_acres += decisions.buy_acres
        current_bushels -= decisions.buy_acres * state.land_price
    elif decisions.sell_acres > 0:
        current_acres -= decisions.sell_acres
        current_bushels += decisions.sell_acres * state.land_price

    # Deduct food
    current_bushels -= decisions.feed_bushels

    # Deduct seed grain: INT(D/2) (line 510)
    seed_used = decisions.plant_acres // 2
    current_bushels -= seed_used

    # Roll 2: Harvest yield Y = INT(RND(1) * 5) + 1 (lines 511, 800)
    harvest_yield = math.floor(provider() * 5.0) + 1
    harvest_total = decisions.plant_acres * harvest_yield

    # Roll 3: Rats infestation (lines 521-530)
    rat_roll = math.floor(provider() * 5.0) + 1
    # Line 522: IF INT(C/2) <> C/2 THEN 530 (odd rolls skip rats)
    if rat_roll % 2 == 0:
        # Line 525: E = INT(S / C)
        rats_ate = current_bushels // rat_roll
    else:
        rats_ate = 0

    # Line 530: S = S - E + H (rats eat before harvest is added)
    current_bushels = current_bushels - rats_ate + harvest_total

    # Roll 4: Immigration (lines 531-533)
    imm_roll = math.floor(provider() * 5.0) + 1
    # Line 533: I = INT(C * (20 * A + S) / P / 100 + 1)
    immigrants = math.floor(
        (imm_roll * (20 * current_acres + current_bushels))
        / (state.population * 100.0)
        + 1.0
    )

    # Starvation calculation (lines 539-555)
    # Line 540: C = INT(Q / 20) (each citizen needs 20 bushels)
    full_tummies = decisions.feed_bushels // 20

    # Roll 5: Plague chance for next year (line 542)
    # Line 542: Q = INT(10 * (2 * RND(1) - 0.3))
    plague_r = provider()
    q_plague = math.floor(10.0 * (2.0 * plague_r - 0.3))
    # Line 227 checks: IF Q > 0 THEN 230 (so Q <= 0 triggers plague)
    plague_next_year = q_plague <= 0

    # Check feeding outcome:
    # Line 550: IF P < C THEN 210 (Overfeeding: skip starvation updates completely)
    if state.population < full_tummies:
        starved = 0
        new_starved_total = state.starved_total
        new_starved_pct_avg = state.starved_pct_avg
        surviving_population = state.population
    else:
        # Line 552: D = P - C
        starved = state.population - full_tummies

        # Line 552: IF D > 0.45 * P THEN 560 (Impeachment)
        if starved > 0.45 * state.population:
            return GameState(
                year=state.year,
                population=state.population - starved,
                bushels=current_bushels,
                acres=current_acres,
                land_price=state.land_price,
                starved_this_year=starved,
                starved_total=state.starved_total + starved,
                starved_pct_avg=state.starved_pct_avg,
                immigrants_this_year=immigrants,
                harvest_yield=harvest_yield,
                rats_ate=rats_ate,
                plague_struck=False,
                plague_next_year=plague_next_year,
                is_over=True,
                game_over_reason="IMPEACHED",
            )

        # Line 553: P1 = ((Z - 1) * P1 + D * 100 / P) / Z
        current_year_pct = (starved * 100.0) / state.population
        new_starved_pct_avg = (
            (state.year - 1) * state.starved_pct_avg + current_year_pct
        ) / state.year
        surviving_population = full_tummies
        new_starved_total = state.starved_total + starved

    # Advance to next year (lines 215-229)
    next_year = state.year + 1
    # Line 218: P = P + I
    next_population = surviving_population + immigrants

    # Line 227-229: Plague check from previous roll
    plague_struck_this_turn = state.plague_next_year
    if plague_struck_this_turn:
        # Line 228: P = INT(P / 2)
        next_population = next_population // 2

    # Line 270: IF Z = 11 THEN 860
    if next_year == 11:
        return GameState(
            year=11,
            population=next_population,
            bushels=current_bushels,
            acres=current_acres,
            land_price=state.land_price,
            starved_this_year=starved,
            starved_total=new_starved_total,
            starved_pct_avg=new_starved_pct_avg,
            immigrants_this_year=immigrants,
            harvest_yield=harvest_yield,
            rats_ate=rats_ate,
            plague_struck=plague_struck_this_turn,
            plague_next_year=plague_next_year,
            is_over=True,
            game_over_reason="COMPLETED",
        )

    # Roll 1 of next year: Land price (lines 310-312)
    next_land_price = calculate_land_price(provider)

    return GameState(
        year=next_year,
        population=next_population,
        bushels=current_bushels,
        acres=current_acres,
        land_price=next_land_price,
        starved_this_year=starved,
        starved_total=new_starved_total,
        starved_pct_avg=new_starved_pct_avg,
        immigrants_this_year=immigrants,
        harvest_yield=harvest_yield,
        rats_ate=rats_ate,
        plague_struck=plague_struck_this_turn,
        plague_next_year=plague_next_year,
        is_over=False,
        game_over_reason=None,
    )


def evaluate_term(
    state: GameState,
    rng: Optional[RandomProvider] = None,
) -> EvaluationResult:
    """
    Evaluates player performance at the end of the 10-year term (lines 860-975).
    Evaluated sequentially:
      - Tier 1: Fink (P1 > 33 or L < 7)
      - Tier 2: Nero & Ivan IV (P1 > 10 or L < 9)
      - Tier 3: Mediocre / Assassination (P1 > 3 or L < 10)
      - Tier 4: Fantastic / Charlemagne (P1 <= 3 and L >= 10)
    """
    provider = rng if rng is not None else DefaultRNG()

    # Line 865: L = A / P
    acres_per_person = state.acres / state.population if state.population > 0 else 0.0

    p1 = state.starved_pct_avg
    l_val = acres_per_person

    # Tier 1 (lines 880-885)
    if p1 > 33.0 or l_val < 7.0:
        msg = (
            "DUE TO THIS EXTREME MISMANAGEMENT YOU HAVE NOT ONLY\n"
            "BEEN IMPEACHED AND THROWN OUT OF OFFICE BUT YOU HAVE\n"
            "ALSO BEEN DECLARED NATIONAL FINK!!!!"
        )
        return EvaluationResult(1, acres_per_person, p1, state.starved_total, msg)

    # Tier 2 (lines 890-892)
    if p1 > 10.0 or l_val < 9.0:
        msg = (
            "YOUR HEAVY-HANDED PERFORMANCE SMACKS OF NERO AND IVAN IV.\n"
            "THE PEOPLE (REMAINING) FIND YOU AN UNPLEASANT RULER, AND,\n"
            "FRANKLY, HATE YOUR GUTS!!"
        )
        return EvaluationResult(2, acres_per_person, p1, state.starved_total, msg)

    # Tier 3 (lines 895-896)
    if p1 > 3.0 or l_val < 10.0:
        # Line 965: INT(P * .8 * RND(1))
        assassinated = math.floor(state.population * 0.8 * provider())
        msg = (
            "YOUR PERFORMANCE COULD HAVE BEEN SOMEWHAT BETTER, BUT\n"
            f"REALLY WASN'T TOO BAD AT ALL. {assassinated} PEOPLE\n"
            "WOULD DEARLY LIKE TO SEE YOU ASSASSINATED BUT WE ALL HAVE OUR\n"
            "TRIVIAL PROBLEMS."
        )
        return EvaluationResult(3, acres_per_person, p1, state.starved_total, msg)

    # Tier 4 (lines 900-905)
    msg = (
        "A FANTASTIC PERFORMANCE!!!  CHARLEMANGE, DISRAELI, AND\n"
        "JEFFERSON COMBINED COULD NOT HAVE DONE BETTER!"
    )
    return EvaluationResult(4, acres_per_person, p1, state.starved_total, msg)
