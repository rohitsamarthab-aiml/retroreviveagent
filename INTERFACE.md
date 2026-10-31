# Hammurabi Architecture & Interface Design

This document details the modular software design for modernizing historical **HAMURABI (1978)** into Python 3. It adheres strictly to the **Python standard library** and ensures complete separation between business rules, terminal input/output, and automated testing.

---

## 1. Architectural Overview & Component Responsibilities

```
┌──────────────────────────────────────────────────────────┐
│                         main.py                          │
│   (CLI Controller, User I/O, Safe Input Handling)        │
└───────────────┬──────────────────────────▲───────────────┘
                │                          │
        Decisions & Commands        State & Event Reports
                │                          │
                ▼                          │
┌──────────────────────────────────────────┴───────────────┐
│                      game_logic.py                       │
│    (Pure Game Engine, State Machine, Validations)        │
│                                                          │
│        Uses: RandomProvider (Default: random.random)     │
└──────────────────────────────────────────────────────────┘
                ▲                          ▲
                │                          │
┌───────────────┴──────────┐     ┌─────────┴───────────────┐
│       test_game.py       │     │     presentation.py     │
│ (Automated unittest suite│     │ (Cosmetic Visual Layer: │
│ with MockRNG sequences)  │     │ ASCII City, Farmland,   │
│                          │     │ Animations & Colors)    │
└──────────────────────────┘     └─────────────────────────┘
```

### Module Responsibilities:
1. **`game_logic.py` (Core Simulation Engine):**
   - Implements the exact verified mathematical formulas from the 1978 Creative Computing BASIC source.
   - Contains **zero** `print()`, **zero** `input()`, and **zero** `sys.exit()` calls.
   - Operates as a pure state transition engine: takes an existing state and turn decisions, and returns a new state and result summary.
   - Encapsulates all resource validations and termination triggers.
2. **`presentation.py` (Cosmetic Visual & Animation Layer):**
   - Renders 100% portable 7-bit ASCII city landscapes, temples, and farmland.
   - Provides fast retro harvest and rat animations, year transition banners, and resource meters.
   - Detects terminal capabilities (TTY, `NO_COLOR`, `TERM`) with automatic plain-text fallback.
   - Contains zero game calculations or random rolls.
3. **`main.py` (Terminal Controller & Game Loop):**
   - Drives the interactive game loop.
   - Coordinates `game_logic.py` state simulation and `presentation.py` cosmetic visual rendering.
   - **Safely parses all user inputs:** Handles malformed text, non-numeric values, empty lines, and whitespace without crashing or silently altering state.
   - Translates game termination states into appropriate exit codes and messages.
4. **`test_game.py` (Automated Test Suite):**
   - Built with standard library `unittest`.
   - Tests every mathematical rule, boundary condition, random event branch, termination scenario, and presentation component.
   - Injects deterministic pseudo-random sequences to guarantee 100% reproducible tests without flakiness.

---

## 2. Core Data Structures (`game_logic.py`)

Using Python's standard `dataclasses.dataclass` provides clean, typed, readable state tracking:

```python
from dataclasses import dataclass
from typing import Optional, Literal

@dataclass(frozen=True)
class GameState:
    """Immutable snapshot of the simulation state."""
    year: int                         # Z: Current year (1 to 10; 11 triggers game over)
    population: int                   # P: Number of living citizens
    bushels: int                      # S: Grain in store
    acres: int                        # A: Acres of land owned
    land_price: int                   # Y (during trading): Price per acre this turn (17-26)
    starved_this_year: int            # D: Deaths by starvation in current year
    starved_total: int                # D1: Cumulative deaths from starvation
    starved_pct_avg: float            # P1: Average annual percentage of starved citizens
    immigrants_this_year: int         # I: Newcomers arriving this year
    harvest_yield: int                # Y: Bushels harvested per acre (1-5)
    rats_ate: int                     # E: Grain eaten by rats this turn
    plague_struck: bool               # Whether plague halved population this year
    plague_next_year: bool            # Whether plague will strike next year (Q <= 0)
    is_over: bool                     # Whether the game has reached a terminal condition
    game_over_reason: Optional[str]   # "STEWARD_FIRED", "IMPEACHED", "COMPLETED"
```

```python
@dataclass(frozen=True)
class TurnDecisions:
    """Player choices submitted for one year."""
    buy_acres: int = 0
    sell_acres: int = 0
    feed_bushels: int = 0
    plant_acres: int = 0
```

```python
@dataclass(frozen=True)
class ValidationResult:
    """Outcome of validating a player input against game rules."""
    is_valid: bool
    is_fatal: bool                    # True if negative input (steward fired)
    message: Optional[str] = None     # Exact historical rebuke text
```

---

## 3. Controlling Random Events Reproducibly

### 3.1 The 5 Random Rolls per Turn
In the canonical 1978 listing, each regular year executes random rolls in this exact sequence:
1. **Roll 1 (Land Price):** `C = INT(10 * RND(1))` $\rightarrow$ Land price is `C + 17` (Range: 17 to 26).
2. **Roll 2 (Harvest Yield):** `C = INT(RND(1) * 5) + 1` $\rightarrow$ Crop yield per acre (Range: 1 to 5).
3. **Roll 3 (Rat Infestation):** `C = INT(RND(1) * 5) + 1` $\rightarrow$ If $C$ is odd (1, 3, 5), no rats; if even (2, 4), rats eat $S // C$.
4. **Roll 4 (Immigration):** `C = INT(RND(1) * 5) + 1` $\rightarrow$ Immigrants formula: $I = \lfloor C(20A + S) / (100P) \rfloor + 1$.
5. **Roll 5 (Plague Chance):** $Q = \lfloor 10(2 \cdot \text{RND}(1) - 0.3) \rfloor \rightarrow$ If $Q \le 0$, plague strikes next year.

*(Note: Tier 3 final evaluation makes an optional 6th roll: `INT(P * 0.8 * RND(1))` for assassinated citizens).*

### 3.2 RandomProvider Interface
To make random behavior 100% reproducible in automated tests without depending on global random seeds:

```python
class RandomProvider:
    """Callable interface returning a pseudo-random float in [0.0, 1.0)."""
    def __call__(self) -> float:
        raise NotImplementedError

class DefaultRNG(RandomProvider):
    """Production RNG using Python standard library random module."""
    def __init__(self, seed: Optional[int] = None):
        import random
        self._rng = random.Random(seed)

    def __call__(self) -> float:
        return self._rng.random()

class MockRNG(RandomProvider):
    """Test RNG returning a predetermined sequence of numbers."""
    def __init__(self, sequence: list[float]):
        self._sequence = list(sequence)
        self._index = 0

    def __call__(self) -> float:
        if self._index >= len(self._sequence):
            raise IndexError("MockRNG exhausted: test provided fewer random numbers than consumed.")
        val = self._sequence[self._index]
        self._index += 1
        return val
```

This ensures unit tests can craft explicit deterministic test cases:
- Want to guarantee a plague? Provide a roll where $r = 0.05 \rightarrow Q = -2 \le 0$.
- Want to guarantee severe rat damage? Provide $r = 0.25 \rightarrow C = 2 \rightarrow$ rats eat 50% of grain.
- Want to verify 10 consecutive years of record harvests? Provide $r = 0.99 \rightarrow Y = 5$.

---

## 4. Public Engine Functions (`game_logic.py`)

### 4.1 State Initialization
```python
def init_game(rng: Optional[RandomProvider] = None) -> GameState:
    """
    Initializes the game to Year 1 pre-decision state.
    Matches lines 95-110 and lines 215-260 of the 1978 BASIC code:
      - Z = 1, P = 100 (95 + 5), S = 2800, A = 1000, Y = 3, E = 200, I = 5, D = 0.
      - Calculates Year 1 land price using rng.
    """
```

### 4.2 Resource & Action Validations
Each function takes the current state and player input, returning a `ValidationResult`:

```python
def validate_buy_land(state: GameState, acres: int) -> ValidationResult:
    """
    Validates land purchase (lines 321-322).
    - If acres < 0: is_fatal=True (Steward fired).
    - If acres * state.land_price > state.bushels: is_valid=False (Cannot afford).
    - Else: is_valid=True.
    """

def validate_sell_land(state: GameState, acres: int) -> ValidationResult:
    """
    Validates land sale (lines 341-342).
    - If acres < 0: is_fatal=True (Steward fired).
    - If acres >= state.acres: is_valid=False (Historical quirk: strictly < A).
    - Else: is_valid=True.
    """

def validate_feed_people(state: GameState, bushels: int) -> ValidationResult:
    """
    Validates grain allocated for food (lines 411-420).
    - If bushels < 0: is_fatal=True (Steward fired).
    - If bushels > state.bushels: is_valid=False (Not enough in silos).
    - Else: is_valid=True.
    """

def validate_plant_seed(state: GameState, acres: int, grain_in_store: int) -> ValidationResult:
    """
    Validates land planted with seed (lines 441-455).
    - If acres < 0: is_fatal=True (Steward fired).
    - If acres > state.acres: is_valid=False (Not enough land).
    - If (acres // 2) > grain_in_store: is_valid=False (Not enough seed grain).
    - If acres >= 10 * state.population: is_valid=False (Historical quirk: strictly < 10*P).
    - Else: is_valid=True.
    """
```

### 4.3 Simulation Step
```python
def step_year(state: GameState, decisions: TurnDecisions, rng: Optional[RandomProvider] = None) -> GameState:
    """
    Executes a complete annual cycle:
    1. Deducts grain fed.
    2. Deducts seed grain (acres // 2).
    3. Rolls harvest yield and calculates harvest.
    4. Rolls rat infestation and updates grain silos.
    5. Rolls new immigrants.
    6. Calculates starvation, impeachment check (>45%), updates P1 and D1.
    7. Rolls next year's plague chance.
    8. Advances year, applies immigrants, applies plague if rolled previously.
    9. Rolls next year's land price.
    """
```

### 4.4 Final Performance Evaluation
```python
@dataclass(frozen=True)
class EvaluationResult:
    tier: int                         # 1 (Fink), 2 (Tyrant), 3 (Mediocre), 4 (Fantastic)
    acres_per_person: float           # L = A / P
    avg_starved_pct: float            # P1
    total_starved: int                # D1
    message: str                      # Historical outcome prose

def evaluate_term(state: GameState, rng: Optional[RandomProvider] = None) -> EvaluationResult:
    """
    Evaluates player performance at Z=11 (lines 860-975).
    """
```

---

## 5. Command-Line Interface Design (`main.py`)

### 5.1 Safe Input Parsing
To guarantee that malformed or non-numeric input never crashes the application, `main.py` utilizes a robust input-helper function:

```python
def prompt_int(prompt_text: str) -> Optional[int]:
    """
    Prompts the user on stdout and reads stdin.
    - Strips whitespace.
    - If input cannot be converted to int, prints historical "?REDO FROM START"
      and re-prompts without crashing or modifying game state.
    - Gracefully handles EOF (Ctrl+D / Ctrl+Z) by returning None.
    """
```

### 5.2 Flow of `main.py`
1. Print introductory title and historical banner:
   ```
                                   HAMURABI
                  CREATIVE COMPUTING  MORRISTOWN, NEW JERSEY

   TRY YOUR HAND AT GOVERNING ANCIENT SUMERIA
   FOR A TEN-YEAR TERM OF OFFICE.
   ```
2. Initialize `GameState` with `init_game()`.
3. Loop while `not state.is_over`:
   - Print annual status report (population, land, yield, rats, stores).
   - If `state.year == 11`, call `evaluate_term()`, display evaluation, print beeps, and break.
   - Collect land purchase decision. If `0`, collect land sale decision.
   - Collect food decision.
   - Collect planting decision.
   - Call `step_year(state, decisions)`.
   - If player was impeached or steward was fired, print termination message and break.
4. Exit with status code `0`.

---

## 6. Automated Test Suite Design (`test_game.py`)

The test suite will contain comprehensive unit tests divided into logical test cases:

```python
class TestInitialState(unittest.TestCase):
    """Verifies year 1 setup, initial variables, and pre-decision report figures."""

class TestInputValidations(unittest.TestCase):
    """Verifies land, grain, and labor limits, including historical < quirks."""

class TestNegativeInputTermination(unittest.TestCase):
    """Verifies that entering negative numbers immediately fires the steward."""

class TestHarvestAndRats(unittest.TestCase):
    """Verifies yield math [1..5], rat parity check (odd/even), and timing."""

class TestImmigrationAndPlague(unittest.TestCase):
    """Verifies immigration formula and plague trigger (Q <= 0)."""

class TestStarvationAndImpeachment(unittest.TestCase):
    """Verifies underfeeding, 45% annual impeachment, and overfeeding quirk."""

class TestFinalEvaluationTiers(unittest.TestCase):
    """Verifies Tier 1 (Fink), Tier 2 (Nero), Tier 3 (Assassination), Tier 4 (Fantastic)."""

class TestFullGameDeterminism(unittest.TestCase):
    """Simulates multi-year scenarios end-to-end with MockRNG."""
```

---

## 7. Graphical Desktop Architecture (Pygame)

To elevate RetroRevive into a modern desktop gaming experience without compromising historical engine integrity, a modular Pygame graphical layer was integrated:

```
┌────────────────────────────────────────────────────────────────────────┐
│                              ui_pygame.py                              │
│  (Desktop Game App, Canvas Letterbox Scaler, Screen Routing, Modals)  │
└───────┬──────────────────────────┬──────────────────────────┬──────────┘
        │                          │                          │
        ▼                          ▼                          ▼
┌──────────────────┐      ┌──────────────────┐      ┌────────────────────┐
│   ui_theme.py    │      │   ui_world.py    │      │modern_game_logic.py│
│ (Palette, Fonts, │      │ (Living Sumeria, │      │ (Scenarios, Royal  │
│  PCM Synth, UI   │      │  Ziggurat, River,│      │  Advisors, Logs,   │
│  Widgets, Toast) │      │  Silos, Particles)│     │  JSON Save/Resume) │
└──────────────────┘      └──────────────────┘      └─────────┬──────────┘
                                                              │
                                                              ▼
                                                    ┌────────────────────┐
                                                    │   game_logic.py    │
                                                    │ (Authoritative 1978│
                                                    │  Simulation Engine)│
                                                    └────────────────────┘
```

### Module Responsibilities:
1. **`ui_pygame.py`:** Main desktop application loop running at 60 FPS.
   - Logical 1280x720 canvas rendering scaled proportionally to any window resolution (e.g., 1366x768, 1920x1080) with letterboxing.
   - Routes between screens: `MAIN_MENU`, `GAMEPLAY`, `SCENARIOS`, `INSTRUCTIONS` (5-step tutorial), and `GAME_OVER`.
2. **`ui_theme.py`:** Design system and procedural sound generator:
   - Palette: Sandstone gold, lapis lazuli blue, desert tan, crimson, fertile green.
   - `SoundSynthesizer`: Real-time 16-bit PCM waveform generation for retro sounds (button clicks, coins, harvest chimes, warnings, bells). Zero external audio files required.
   - Reusable widgets: `UIButton`, `UINumberInput` (direct typing + quick step buttons `[-100, -10, +10, +100, MAX, CLR]`), `UIModal` (with automatic line word-wrapping), and `UIToast` notifications.
3. **`ui_world.py`:** Living animated procedural Sumerian environment:
   - Dynamic sky with drifting clouds and pulsing celestial sun.
   - Distant Zagros mountain silhouette.
   - Step Ziggurat of Ur with burning temple braziers.
   - Flowing Euphrates river with sinusoidal wave crests.
   - Dynamic farmland plots and mudbrick granary silos with grain fill meters.
   - Animated citizen villagers walking along the riverbank.
   - Particle systems for wheat chaff, scampering rats, and celebratory fireworks.
4. **`modern_game_logic.py`:** Enhanced Mode engine extending `game_logic.py`:
   - 4 Scenarios: *The Great Drought*, *The Population Boom*, *The Granary Defense*, *Empire of Babylon*.
   - Contextual Royal Advisors: Vizier (macro stability), Granary Master (food & rationing), and Surveyor (land & planting capacity).
   - Chronicle event log tracking year-by-year history.
   - Safe JSON persistence (`save_game_state`, `load_game_state`).
5. **`test_modern.py`:** Automated test suite verifying scenario victory logic, advisor recommendations, chronicle logging, and JSON persistence round-trips.
