# RetroRevive Implementation Plan: HAMURABI Modernization

This build plan outlines the step-by-step milestones to implement **HAMURABI (1978)** as a robust, clean Python 3 application.

**Guidelines:**
- Python 3 standard library only (no external packages, no pip).
- Implementation will start only after Product Owner review and approval of `RULES.md`, `INTERFACE.md`, and `BUILD_PLAN.md`.
- Test-driven approach using standard `unittest`.

---

## Milestones & Acceptance Criteria

### Milestone 1: Test Harness & Project Structure
- **Objective:** Establish the project layout and verify test runner.
- **Tasks:**
  - Create project files: `game_logic.py`, `main.py`, `test_game.py`.
  - Verify execution with `python -m unittest test_game.py`.
- **Acceptance Criteria:**
  - Test runner executes cleanly without errors or warnings.
  - Zero external dependencies required.

---

### Milestone 2: State Data Models & Validation Engine
- **Objective:** Implement data structures and input validation rules in `game_logic.py`.
- **Tasks:**
  - Implement `GameState`, `TurnDecisions`, and `ValidationResult`.
  - Implement `init_game()` returning initial state for Year 1.
  - Implement validation functions:
    - `validate_buy_land`
    - `validate_sell_land` (verifying `< A` rule)
    - `validate_feed_people`
    - `validate_plant_seed` (verifying `< 10*P` and `acres // 2` checks)
- **Acceptance Criteria:**
  - Unit tests verify all valid purchases, sales, feeds, and plantings.
  - Unit tests verify rejection of unaffordable or out-of-bounds orders.
  - Unit tests verify negative inputs flag fatal steward dismissal (`is_fatal=True`).

---

### Milestone 3: Annual Simulation Step & Random Events
- **Objective:** Implement the annual turn transition in `game_logic.py`.
- **Tasks:**
  - Implement `RandomProvider`, `DefaultRNG`, and `MockRNG`.
  - Implement harvest yield calculation ($Y \in [1, 5]$).
  - Implement rat infestation parity logic (even roll eats grain; odd roll eats 0).
  - Implement immigration calculation based on land, stores, population, and roll.
  - Implement starvation calculation:
    - Exact/underfeeding: $D = P - C$; impeachment if $D > 0.45 P$; updates $P$, $P_1$, $D_1$.
    - Overfeeding: skips starvation updates.
  - Implement plague calculation ($Q \le 0$ triggers 50% population loss next year).
- **Acceptance Criteria:**
  - Deterministic unit tests with `MockRNG` verify every calculation against known historical outputs.
  - Impeachment triggers reliably when starvation exceeds 45%.
  - Rats, harvest yields, and plagues trigger at verified mathematical probabilities.

---

### Milestone 4: Final Term Evaluation System
- **Objective:** Implement the 10-year term completion rating in `game_logic.py`.
- **Tasks:**
  - Implement `evaluate_term(state, rng)`.
  - Implement evaluation tiers:
    - Tier 1: National Fink / Impeachment ($P_1 > 33$ or $L < 7$).
    - Tier 2: Nero & Ivan IV / Hated Ruler ($P_1 > 10$ or $L < 9$).
    - Tier 3: Mediocre / Assassination Risk ($P_1 > 3$ or $L < 10$).
    - Tier 4: Fantastic Performance / Charlemagne ($P_1 \le 3$ and $L \ge 10$).
- **Acceptance Criteria:**
  - Unit tests for each evaluation tier verify that the exact boundary conditions and historical text outputs match the 1978 source.

---

### Milestone 5: Command-Line Interface & Safe Input Controller
- **Objective:** Implement user interface and game loop in `main.py`.
- **Tasks:**
  - Implement `prompt_int()` with `try/except ValueError` catching non-numeric input.
  - Format historical turn report and narrative announcements matching original terminal display.
  - Connect user choices to `step_year()`.
  - Handle termination states (steward fired, impeached, completed).
- **Acceptance Criteria:**
  - Entering invalid text (e.g. "two hundred", symbols, empty enter) re-prompts safely with `?REDO FROM START` without crashing or corrupting game state.
  - Entering negative numbers cleanly fires the steward and exits.
  - Full game can be played interactively from Year 1 to Year 10.

---

### Milestone 6: Verification & Final Acceptance
- **Objective:** Full verification of rules, automated test coverage, and documentation.
- **Tasks:**
  - Run full test suite: `python -m unittest discover -v`.
  - Execute end-to-end multi-year game play-throughs.
  - Document product decisions and historical fidelity in `README.md`.
- **Acceptance Criteria:**
  - 100% of automated tests pass without errors.
  - Zero dependencies beyond standard Python 3.10+.
  - Clean code compliant with PEP 8.
