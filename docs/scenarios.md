# RetroRevive — Repeatable Gameplay Scenarios

This document details **six documented, repeatable test scenarios** for RetroRevive's modernization of **HAMURABI (1978)**. Each scenario specifies the initial state, exact player inputs, expected simulation transitions, and source-backed outcomes.

---

## Scenario 1: The Prudent Ruler (The "Charlemagne" Victory)

- **Objective:** Complete the full 10-year term with zero starvation and maintain at least 10 acres per citizen, achieving Tier 4 performance.
- **Rule Justification:** Lines 860–905 of the 1978 BASIC source. $P_1 \le 3\%$ average starvation and $L = A / P \ge 10$ acres/person triggers the highest historical rating.
- **Run Command:**
  ```bash
  python test_game.py TestMultiYearSimulation.test_full_ten_year_game
  ```
- **Inputs & Strategy (Annual):**
  - **Buy / Sell:** 0 acres (maintain starting 1,000 acres).
  - **Feed:** Exactly $20 \times P$ bushels (e.g. 2,000 bushels in Year 1).
  - **Plant:** $9 \times P$ acres (safe below both the seed store and the historical $10 \times P$ labor limit).
- **Expected Outcome:**
  - Starvation: 0 deaths every year.
  - Cumulative Starvation ($D_1$): 0.
  - Average Starvation ($P_1$): 0.0%.
  - Final Land per Person ($L$): $\ge 10.0$ acres/person.
  - Final Message:
    ```
    A FANTASTIC PERFORMANCE!!!  CHARLEMANGE, DISRAELI, AND
    JEFFERSON COMBINED COULD NOT HAVE DONE BETTER!
    ```

---

## Scenario 2: Catastrophic Famine & Immediate Impeachment

- **Objective:** Verify that starving more than 45% of the population in a single year causes immediate mid-term termination.
- **Rule Justification:** Lines 552 and 560–567 of the 1978 BASIC source: `IF D > .45 * P THEN 560`.
- **Run Command:**
  ```bash
  python -c "import subprocess; p = subprocess.run(['python', 'main.py', '--no-sound'], input='0\n0\n1000\n0\n', text=True, capture_output=True); print(p.stdout)"
  ```
- **Inputs (Year 1):**
  - Buy Acres: `0`
  - Sell Acres: `0`
  - Feed Bushels: `1000` (Feeds $\lfloor 1000 / 20 \rfloor = 50$ citizens out of 100).
  - Plant Acres: `0`
- **Simulation Mechanics:**
  - Starved ($D$): $100 - 50 = 50$ citizens.
  - Impeachment Threshold: $0.45 \times 100 = 45$ citizens.
  - Since $50 > 45$, the impeachment branch triggers immediately.
- **Expected Outcome:**
  ```
  YOU STARVED 50 PEOPLE IN ONE YEAR!!!
  DUE TO THIS EXTREME MISMANAGEMENT YOU HAVE NOT ONLY
  BEEN IMPEACHED AND THROWN OUT OF OFFICE BUT YOU HAVE
  ALSO BEEN DECLARED NATIONAL FINK!!!!

  SO LONG FOR NOW.
  ```

---

## Scenario 3: Insolent Steward Dismissal (Negative Input)

- **Objective:** Verify that entering any negative integer at any prompt immediately terminates the game with the steward dismissal message.
- **Rule Justification:** Lines 321, 341, 412, and 442 of the 1978 BASIC source: `IF Q < 0 THEN 850` (or `IF D < 0 THEN 850`).
- **Run Command:**
  ```bash
  python -c "import subprocess; p = subprocess.run(['python', 'main.py', '--no-sound'], input='-1\n', text=True, capture_output=True); print(p.stdout)"
  ```
- **Inputs (Year 1):**
  - Buy Acres: `-1`
- **Expected Outcome:**
  ```
  HAMURABI:  I CANNOT DO WHAT YOU WISH.
  GET YOURSELF ANOTHER STEWARD!!!!!

  SO LONG FOR NOW.
  ```

---

## Scenario 4: Safe Handling of Malformed & Non-Numeric Input

- **Objective:** Verify that entering text, empty lines, words, or symbols does not crash the program, but instead safely re-prompts with the classic `?REDO FROM START` message without altering game state.
- **Rule Justification:** Vintage Microsoft BASIC runtime handling of numeric `INPUT` statements; required by buildathon specification.
- **Run Command:**
  ```bash
  python -c "import subprocess; p = subprocess.run(['python', 'main.py', '--no-sound'], input='all of it\n\nfifty\n0\n0\n2000\n-1\n', text=True, capture_output=True); print(p.stdout)"
  ```
- **Inputs:**
  - `all of it` $\rightarrow$ triggers `?REDO FROM START`
  - ` ` (empty enter) $\rightarrow$ triggers `?REDO FROM START`
  - `fifty` $\rightarrow$ triggers `?REDO FROM START`
  - `0` $\rightarrow$ valid integer accepted
- **Expected Outcome:**
  ```
  HOW MANY ACRES DO YOU WISH TO BUY? ?REDO FROM START
  HOW MANY ACRES DO YOU WISH TO BUY? ?REDO FROM START
  HOW MANY ACRES DO YOU WISH TO BUY? ?REDO FROM START
  HOW MANY ACRES DO YOU WISH TO BUY? HOW MANY ACRES DO YOU WISH TO SELL?
  ```

---

## Scenario 5: Historical Boundary Constraint Rejections

- **Objective:** Verify the two famous historical off-by-one boundary quirks in the 1978 BASIC source, and demonstrate `--relaxed` flag behavior.
- **Rule Justification:**
  - Selling Land (Line 342): `IF Q < A THEN 350` (Strictly $< A$; cannot sell 100% of land).
  - Planting Crops (Line 455): `IF D < 10 * P THEN 510` (Strictly $< 10 \times P$; 100 people cannot plant 1,000 acres, only 999).
- **Test 5A: Strict Historical Mode (Default):**
  - Sell Acres: `1000` (owns 1000) $\rightarrow$ Rejected: `HAMURABI:  THINK AGAIN.  YOU OWN ONLY 1000 ACRES.  NOW THEN,`
  - Plant Acres: `1000` (has 100 people) $\rightarrow$ Rejected: `BUT YOU HAVE ONLY 100 PEOPLE TO TEND THE FIELDS!  NOW THEN,`
- **Test 5B: Modernized/Relaxed Mode (`--relaxed`):**
  - Sell Acres: `1000` $\rightarrow$ Accepted ($\le A$).
  - Plant Acres: `1000` $\rightarrow$ Accepted ($\le 10 \times P$).
- **Run Automated Test:**
  ```bash
  python -m unittest test_game.TestInputValidations.test_validate_sell_land_strict_vs_relaxed
  python -m unittest test_game.TestInputValidations.test_validate_plant_seed_strict_vs_relaxed
  ```

---

## Scenario 6: Rat Infestation & Grain Store Timing

- **Objective:** Verify that rats eat stored grain *before* the new harvest is credited, and test rat parity (even rolls cause damage, odd rolls cause zero damage).
- **Rule Justification:** Lines 521–530 of the 1978 BASIC source.
- **Test Mechanics:**
  - Stored grain after feeding and seeding: $S_{\text{start}} = 2800 - 2000 - 100 = 700$ bushels.
  - Even Rat Roll ($C = 2$): Rats eat $E = \lfloor 700 / 2 \rfloor = 350$ bushels.
  - Harvest: 200 acres $\times 3$ bu/acre = 600 bushels.
  - Final Store ($S$): $700 - 350 + 600 = 950$ bushels.
- **Run Automated Test:**
  ```bash
  python -m unittest test_game.TestHarvestAndRatsCalculations.test_rat_infestation_parity_and_timing
  ```
- **Expected Outcome:** Verified exact match to line 530 arithmetic.
