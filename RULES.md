# Hammurabi: Canonical Rules Specification (1978 Creative Computing Edition)

## 1. Source Edition & Provenance

### 1.1 Selected Historical Edition
- **Canonical Game Title:** `HAMURABI` (historically spelled with a single 'm')
- **Author & Editor:** David H. Ahl (adapted from Doug Dyment's 1968 FOCAL program *The Sumer Game*)
- **Publication:** *BASIC Computer Games: Microcomputer Edition*, Workman Publishing / Creative Computing, Morristown, New Jersey, 1978, pages 78–79.
- **Verified Primary Source Listings:**
  1. *AtariArchives Digital Library:* [BASIC Computer Games: Hammurabi](https://www.atariarchives.org/basicgames/showpage.php?page=78)
  2. *The Hamurabi Collection (Tristano Ajmone):* [1978/hamurabi.bas](https://github.com/tajmone/hamurabi-collection/blob/master/1978/hamurabi.bas) (reproduced with author David H. Ahl's permission)
  3. *Vintage BASIC Archive:* `http://www.vintage-basic.net/bcg/hammurabi.bas`
  4. *Basic Computer Games GitHub Repository:* [43_Hammurabi/hammurabi.bas](https://github.com/coding-horror/basic-computer-games/blob/main/43_Hammurabi/hammurabi.bas)

### 1.2 Comparison with Other Historical Editions (Why They Are Not Mixed)
- **1968 DEC FOCAL (*The Sumer Game* by Doug Dyment):** Written for DEC PDP-8 in FOCAL-68. Did not include David Ahl's 10-year performance evaluation at the end of the game, used different initial resource quantities, and used FOCAL-specific syntax.
- **1973 DEC Edition (*101 BASIC Computer Games* by David H. Ahl):** Titled `HMRABI` due to the 6-character filename limit on DEC PDP systems. Targeted DEC EduSystem-25 BASIC with DEC-specific random functions and syntax.
- **1978 Microcomputer Edition (*BASIC Computer Games*):** Titled `HAMURABI`. Standardized for Microsoft BASIC, which became the universal standard across Apple II, Commodore PET, TRS-80, and Altair microcomputers. This is the definitive edition played and referenced worldwide.
- **Modern / Derivative Variants:** Later community ports frequently changed rules arbitrarily (e.g., modifying population caps, fixing arithmetic quirks without documentation, or blending mechanics with *Kingdom* or *Santa Paravia*). To maintain historical fidelity, **only the verified 1978 Creative Computing Microsoft BASIC listing is used as the single source of truth**.

### 1.3 Material Restrictions & Copyright Notice
- **Gameplay Mechanics & Mathematics:** Under US Copyright Law (17 U.S.C. § 102(b)), game rules, ideas, algorithms, and mathematical simulations are not copyrightable.
- **Original Prose & Presentation:** The original book layout, introductory commentary, and exact phrasing by David H. Ahl / Creative Computing are historical literary works. RetroRevive respects historical authorship by acknowledging Doug Dyment and David H. Ahl, faithfully modernizing the mechanics in original clean Python 3, and avoiding verbatim commercial exploitation.

---

## 2. Initial State & Turn 1 Setup

### 2.1 Raw Variable Initialization (Lines 95–110)
When the BASIC program boots, the following initial variables are assigned:

| Variable | BASIC Name | Initial Value | Line Reference | Status | Description |
|---|---|---|---|---|---|
| Cumulative Starved | `D1` | `0` | Line 95 | **[VERIFIED]** | Total number of citizens who have starved across all years |
| Cumulative Average Starvation % | `P1` | `0` | Line 95 | **[VERIFIED]** | Running average percentage of population starved per year |
| Year Counter | `Z` | `0` | Line 100 | **[VERIFIED]** | Incremented to `1` at the start of the first report |
| Population | `P` | `95` | Line 100 | **[VERIFIED]** | Initial population base before Year 1 immigration |
| Bushels in Store | `S` | `2800` | Line 100 | **[VERIFIED]** | Grain in silos at start |
| Harvest Total | `H` | `3000` | Line 100 | **[VERIFIED]** | Harvest amount displayed in Year 1 initial report |
| Rats Eaten | `E` | `H - S = 200` | Line 100 | **[VERIFIED]** | Grain eaten by rats displayed in Year 1 initial report |
| Harvest Yield | `Y` | `3` | Line 110 | **[VERIFIED]** | Yield per acre displayed in Year 1 initial report |
| City Land | `A` | `H / Y = 1000` | Line 110 | **[VERIFIED]** | Total acres of land owned at start |
| Immigrants | `I` | `5` | Line 110 | **[VERIFIED]** | Immigrants arriving in Year 1 initial report |
| Plague Flag | `Q` | `1` | Line 110 | **[VERIFIED]** | Initialized to 1 (> 0 means no plague struck in Year 1) |
| Current Year Starved | `D` | `0` | Line 210 | **[VERIFIED]** | Starved deaths in current year report |

### 2.2 Turn 1 Pre-Decision Report (Lines 215–260)
Before the player is prompted for any input in Year 1:
1. `Z` is incremented: `Z = Z + 1` -> `Z = 1`. **[VERIFIED line 215]**
2. Immigration is added: `P = P + I = 95 + 5 = 100`. **[VERIFIED line 218]**
3. Plague check: `IF Q > 0 THEN 230`. Since `Q = 1`, plague is skipped. **[VERIFIED line 227]**
4. The Year 1 report displays:
   - Year: `1`
   - Starved: `0`
   - Immigrants: `5`
   - Population: `100`
   - Land owned: `1000` acres
   - Harvested: `3` bushels per acre
   - Rats ate: `200` bushels
   - In store: `2800` bushels **[VERIFIED lines 217–260]**

---

## 3. Yearly Lifecycle Sequence

Each year from 1 to 10 follows this exact sequential execution order:

```
[Start Year Z]
       │
       ▼
1. Report Phase:
   - Advance Year: Z = Z + 1
   - Add Immigrants: P = P + I
   - Check Plague: If Q <= 0, P = INT(P / 2) and announce plague
   - Display Status Report (Population, Acres, Yield, Rats, Store)
       │
       ▼
2. Year 11 Check:
   - If Z == 11, jump immediately to Final Evaluation (Game Over)
       │
       ▼
3. Land Trading Phase:
   - Generate Land Price: Y = INT(10 * RND(1)) + 17 (17 to 26 bu/acre)
   - Prompt: Buy Land
     ├─ If Q < 0 ──> Immediate Termination (Steward Fired)
     ├─ If Buy > 0 and Affordable ──> Buy Land, Skip Sell Phase
     ├─ If Buy > 0 and Unaffordable ──> Reprompt Buy
     └─ If Buy == 0 ──> Proceed to Sell Land Prompt
          ├─ If Q < 0 ──> Immediate Termination (Steward Fired)
          ├─ If Sell < A ──> Sell Land
          └─ If Sell >= A ──> Reprompt Sell
       │
       ▼
4. Feeding Phase:
   - Prompt: Feed Bushels
     ├─ If Q < 0 ──> Immediate Termination (Steward Fired)
     ├─ If Q > S ──> Reprompt Feed
     └─ If Q <= S ──> Deduct Grain (S = S - Q)
       │
       ▼
5. Planting Phase:
   - Prompt: Plant Acres
     ├─ If D == 0 ──> Skip Planting Deductions
     ├─ If D < 0 ──> Immediate Termination (Steward Fired)
     ├─ If D > A ──> Reprompt (Not enough land)
     ├─ If INT(D / 2) > S ──> Reprompt (Not enough seed grain)
     ├─ If D >= 10 * P ──> Reprompt (Not enough people; strictly < 10*P in BASIC)
     └─ If Valid ──> Deduct Seed Grain (S = S - INT(D / 2))
       │
       ▼
6. Simulation & Event Phase:
   - Crop Harvest: Yield Y in [1..5], Harvest H = D * Y
   - Rat Infestation: Roll [1..5]; if even, rats eat S // Roll; Store S = S - E + H
   - New Immigrants: Calculate I based on land, grain, population, and roll [1..5]
   - Starvation & Plague Roll:
     ├─ Full Tummies C = INT(Q / 20)
     ├─ Roll Next Year Plague: Q = INT(10 * (2 * RND(1) - 0.3))
     ├─ If P < C (Overfeeding) ──> Skip starvation; D = 0; P, P1, D1 unchanged
     └─ If P >= C (Underfeeding / Exact):
          ├─ D = P - C
          ├─ If D > 0.45 * P ──> Immediate Termination (Impeached / National Fink)
          └─ If D <= 0.45 * P ──> Update P1, P = C, D1 = D1 + D
       │
       ▼
[Loop to Next Year Report]
```

---

## 4. Mechanics, Calculations & Validations

### 4.1 Land Price Generation
- **Formula:** `C = INT(10 * RND(1))`, `Y = C + 17` **[VERIFIED lines 310–312]**
- **Outcome Range:** Random integer from `17` to `26` inclusive (bushels per acre).
- **RNG Calls:** Consumes 1 random float `RND(1)`.

### 4.2 Buying Land
- **Prompt:** `HOW MANY ACRES DO YOU WISH TO BUY` **[VERIFIED line 320]**
- **Input Rules:**
  - If `Q < 0`: Immediate termination via steward firing routine (Line 850). **[VERIFIED line 321]**
  - If `Y * Q <= S`: Valid purchase.
    - `A = A + Q`
    - `S = S - Y * Q`
    - Program branches directly to Feeding Phase (`GOTO 400`), completely skipping Land Selling for the year. **[VERIFIED lines 322, 331, 334]**
  - If `Y * Q > S`: Insufficient grain.
    - Displays: `HAMURABI:  THINK AGAIN.  YOU HAVE ONLY [S] BUSHELS OF GRAIN.  NOW THEN,`
    - Re-prompts for purchase. **[VERIFIED lines 323–324, 710–712]**
  - If `Q == 0`: No land purchased; advances to Land Selling prompt. **[VERIFIED line 330]**

### 4.3 Selling Land
- Reached **only** if the player entered `0` for buying land. **[VERIFIED line 330]**
- **Prompt:** `HOW MANY ACRES DO YOU WISH TO SELL` **[VERIFIED line 340]**
- **Input Rules:**
  - If `Q < 0`: Immediate termination via steward firing routine (Line 850). **[VERIFIED line 341]**
  - If `Q < A`: Valid sale.
    - `A = A - Q`
    - `S = S + Y * Q`
    - Proceeds to Feeding Phase. **[VERIFIED lines 342, 350]**
  - If `Q >= A`: Land sale rejected.
    - Displays: `HAMURABI:  THINK AGAIN.  YOU OWN ONLY [A] ACRES.  NOW THEN,`
    - Re-prompts for sale. **[VERIFIED lines 342–344, 720–730]**
- **Historical Quirk Note:** In line 342 (`IF Q < A THEN 350`), selling all acres (`Q == A`) is rejected. A player owning 1000 acres can sell at most 999 acres. **[VERIFIED line 342]**

### 4.4 Feeding People
- **Prompt:** `HOW MANY BUSHELS DO YOU WISH TO FEED YOUR PEOPLE` **[VERIFIED line 410]**
- **Input Rules:**
  - If `Q < 0`: Immediate termination via steward firing routine (Line 850). **[VERIFIED line 412]**
  - If `Q <= S`: Valid feeding.
    - `S = S - Q`
    - Grain is deducted immediately from store. **[VERIFIED lines 420, 430]**
  - If `Q > S`: Insufficient grain.
    - Displays: `HAMURABI:  THINK AGAIN.  YOU HAVE ONLY [S] BUSHELS OF GRAIN.  NOW THEN,`
    - Re-prompts for feed amount. **[VERIFIED lines 420–422, 710–712]**

### 4.5 Planting Seed
- **Prompt:** `HOW MANY ACRES DO YOU WISH TO PLANT WITH SEED` **[VERIFIED line 440]**
- **Input Rules & Multi-Constraint Validation:**
  - If `D == 0`: Allowed. Bypasses seed deduction and proceeds to harvest with `D = 0`. **[VERIFIED line 441]**
  - If `D < 0`: Immediate termination via steward firing routine (Line 850). **[VERIFIED line 442]**
  - **Constraint 1 (Land):** `IF D <= A THEN 450`
    - If `D > A`: Displays `HAMURABI:  THINK AGAIN.  YOU OWN ONLY [A] ACRES.  NOW THEN,` and re-prompts. **[VERIFIED lines 445–447, 720–730]**
  - **Constraint 2 (Seed Grain):** `IF INT(D / 2) <= S THEN 455`
    - Seed rate: 1 bushel per 2 acres (i.e., `INT(D / 2)` bushels required).
    - If `INT(D / 2) > S`: Displays `HAMURABI:  THINK AGAIN.  YOU HAVE ONLY [S] BUSHELS OF GRAIN.  NOW THEN,` and re-prompts. **[VERIFIED lines 450–453, 710–712]**
  - **Constraint 3 (Labor Capacity):** `IF D < 10 * P THEN 510`
    - Labor capacity rule: 1 person tends up to 10 acres.
    - If `D >= 10 * P`: Displays `BUT YOU HAVE ONLY [P] PEOPLE TO TEND THE FIELDS!  NOW THEN,` and re-prompts. **[VERIFIED lines 455–470]**
    - **Historical Quirk Note:** The check in the original BASIC is strictly less than (`D < 10 * P`). If a player has 100 people, `10 * 100 = 1000`. Entering `1000` is rejected! The maximum plantable acreage in original code is `10 * P - 1` (999 acres). **[VERIFIED line 455]**
  - If all checks pass:
    - Deduct seed grain: `S = S - INT(D / 2)` **[VERIFIED line 510]**

### 4.6 Harvest Calculation
- Subroutine 800 is called: `C = INT(RND(1) * 5) + 1` **[VERIFIED lines 511, 800]**
  - Yield per acre: `Y = C` (random integer in range `[1, 5]`). **[VERIFIED line 515]**
- Total bushels harvested: `H = D * Y` **[VERIFIED line 515]**
- Pre-set rat loss: `E = 0` **[VERIFIED line 515]**

### 4.7 Rat Infestation
- Subroutine 800 is called again: `C = INT(RND(1) * 5) + 1` (random integer in `[1, 5]`). **[VERIFIED lines 521, 800]**
- Parity Check: `IF INT(C / 2) <> C / 2 THEN 530` **[VERIFIED line 522]**
  - If `C` is odd (`1, 3, 5`): Rats do not strike (`E = 0`). Probability = 3/5 (60%).
  - If `C` is even (`2, 4`): Rats run wild! Probability = 2/5 (40%).
    - Bushels eaten: `E = INT(S / C)` **[VERIFIED line 525]**
    - When `C = 2`, rats eat half the stored grain (`INT(S / 2)`).
    - When `C = 4`, rats eat one quarter of the stored grain (`INT(S / 4)`).
- Store Update: `S = S - E + H` **[VERIFIED line 530]**
  - **Critical Timing:** Rats eat from store `S` **before** the new harvest `H` is added!

### 4.8 Immigration Calculation
- Subroutine 800 is called again: `C = INT(RND(1) * 5) + 1` (random integer in `[1, 5]`). **[VERIFIED lines 531, 800]**
- Formula: `I = INT(C * (20 * A + S) / P / 100 + 1)` **[VERIFIED line 533]**
  - Evaluated left-to-right as: `INT( (C * (20 * A + S)) / (P * 100) + 1 )`
  - Uses current acres `A`, post-harvest store `S`, and current population `P`.
  - Guaranteed to be at least `1` immigrant.

### 4.9 Starvation & Impeachment
- Bushels fed per person required: `20` bushels.
- People fed count: `C = INT(Q / 20)` (where `Q` is grain fed). **[VERIFIED line 540]**
- Next year's plague roll: `Q = INT(10 * (2 * RND(1) - 0.3))` **[VERIFIED line 542]**
- **Branch A: Overfeeding (`P < C`)**
  - `IF P < C THEN 210` **[VERIFIED line 550]**
  - The game jumps immediately to line 210 for next year!
  - `D = 0` (0 people starved). **[VERIFIED line 210]**
  - **Quirk:** `P1` (average starvation %) is **not** updated. `D1` is **not** incremented. `P` remains unchanged. **[VERIFIED lines 550–215]**
- **Branch B: Underfeeding or Exact (`P >= C`)**
  - Deaths this year: `D = P - C` **[VERIFIED line 552]**
  - **Impeachment Check:** `IF D > 0.45 * P THEN 560` **[VERIFIED line 552]**
    - If more than 45% of the population starved in a single year, the game terminates immediately with impeachment:
      ```
      YOU STARVED [D] PEOPLE IN ONE YEAR!!!
      DUE TO THIS EXTREME MISMANAGEMENT YOU HAVE NOT ONLY
      BEEN IMPEACHED AND THROWN OUT OF OFFICE BUT YOU HAVE
      ALSO BEEN DECLARED NATIONAL FINK!!!!
      ```
      Followed by 10 terminal beeps, `SO LONG FOR NOW.`, and exit. **[VERIFIED lines 560–567, 990–999]**
  - If `D <= 0.45 * P`:
    - Update average annual starvation percentage:
      `P1 = ((Z - 1) * P1 + D * 100 / P) / Z` **[VERIFIED line 553]**
    - Update surviving population: `P = C` **[VERIFIED line 555]**
    - Accumulate total deaths: `D1 = D1 + D` **[VERIFIED line 555]**
    - Jump to line 215 (start next year report). **[VERIFIED line 555]**

### 4.10 Plague Mechanic
- In year `Z`, line 542 rolled `Q = INT(10 * (2 * RND(1) - 0.3))`.
- At start of year `Z + 1` report: `IF Q > 0 THEN 230` **[VERIFIED line 227]**
- If `Q <= 0`:
  - `P = INT(P / 2)` **[VERIFIED line 228]**
  - Displays: `A HORRIBLE PLAGUE STRUCK!  HALF THE PEOPLE DIED.` **[VERIFIED line 229]**
- **Probability Breakdown:**
  - Let $r = \text{RND}(1) \in [0, 1)$.
  - $2r - 0.3 < 0.1 \iff 2r < 0.4 \iff r < 0.20$.
  - When $r < 0.20$, $10(2r - 0.3) < 1.0$, so $\text{INT}(10(2r - 0.3)) \le 0$.
  - Thus, despite the author's comment `REM *** HORROS, A 15% CHANCE OF PLAGUE`, the exact math triggers a plague with a **20% probability**. **[VERIFIED math & line 541–542]**

---

## 5. Termination Conditions & Final Evaluation

### 5.1 Termination Scenarios
The game terminates in exactly three ways:
1. **Steward Dismissal (Immediate):** If the player enters any negative number at any decision prompt (`Q < 0` or `D < 0`).
   ```
   HAMURABI:  I CANNOT DO WHAT YOU WISH.
   GET YOURSELF ANOTHER STEWARD!!!!!
   ```
   Followed by 10 beeps, `SO LONG FOR NOW.`, and program exit. **[VERIFIED lines 850–857, 990–999]**
2. **In-Term Impeachment (Immediate):** If in any single year, more than 45% of the population starves (`D > 0.45 * P`).
   Followed by the National Fink message, 10 beeps, `SO LONG FOR NOW.`, and program exit. **[VERIFIED lines 560–567, 990–999]**
3. **End of 10-Year Term (`Z == 11`):** When year 10 completes and loops to line 215, `Z` becomes 11.
   Line 270 checks `IF Z = 11 THEN 860`. The year 10 report is printed, but no inputs are asked; execution branches directly to the Final Evaluation routine. **[VERIFIED lines 270, 860]**

### 5.2 Final Evaluation Routine (Lines 860–975)
At the end of 10 years:
1. Calculate final land per capita: `L = A / P` **[VERIFIED line 865]**
2. Print summary report:
   ```
   IN YOUR 10-YEAR TERM OF OFFICE, [P1] PERCENT OF THE
   POPULATION STARVED PER YEAR ON THE AVERAGE, I.E. A TOTAL OF
   [D1] PEOPLE DIED!!
   YOU STARTED WITH 10 ACRES PER PERSON AND ENDED WITH
   [L] ACRES PER PERSON.
   ```
   **[VERIFIED lines 860–875]**
3. Performance Tiers (Evaluated sequentially):

| Tier | Evaluation Condition | Resulting Outcome & Historical Text | Status |
|---|---|---|---|
| **Tier 1: Impeachment** | `P1 > 33` OR `L < 7` | Line 565: `DUE TO THIS EXTREME MISMANAGEMENT YOU HAVE NOT ONLY BEEN IMPEACHED AND THROWN OUT OF OFFICE BUT YOU HAVE ALSO BEEN DECLARED NATIONAL FINK!!!!` | **[VERIFIED lines 880–885, 565–567]** |
| **Tier 2: Tyrant / Hated** | `P1 > 10` OR `L < 9` | Lines 940–950: `YOUR HEAVY-HANDED PERFORMANCE SMACKS OF NERO AND IVAN IV. THE PEOPLE (REMAINING) FIND YOU AN UNPLEASANT RULER, AND, FRANKLY, HATE YOUR GUTS!!` | **[VERIFIED lines 890–892, 940–950]** |
| **Tier 3: Mediocre** | `P1 > 3` OR `L < 10` | Lines 960–975: `YOUR PERFORMANCE COULD HAVE BEEN SOMEWHAT BETTER, BUT REALLY WASN'T TOO BAD AT ALL. [INT(P * 0.8 * RND(1))] PEOPLE WOULD DEARLY LIKE TO SEE YOU ASSASSINATED BUT WE ALL HAVE OUR TRIVIAL PROBLEMS.` | **[VERIFIED lines 895–896, 960–975]** |
| **Tier 4: Fantastic** | `P1 <= 3` AND `L >= 10` | Lines 900–905: `A FANTASTIC PERFORMANCE!!!  CHARLEMANGE, DISRAELI, AND JEFFERSON COMBINED COULD NOT HAVE DONE BETTER!` | **[VERIFIED lines 900–905]** |

4. Exit routine:
   - Prints 10 ASCII bell characters: `FOR N=1 TO 10: PRINT CHR$(7);: NEXT N` **[VERIFIED line 990]**
   - Displays: `SO LONG FOR NOW.` **[VERIFIED line 995]**
   - Terminates (`END`) **[VERIFIED line 999]**

---

## 6. Invalid-Input & Malformed Data Handling

### 6.1 Negative Numerical Input
- In all 4 numeric prompts (buy, sell, feed, plant), entering any negative number is treated as an intentional resign/steward rejection action by Hammurabi (`IF Q < 0 THEN 850`).
- Status: **[VERIFIED lines 321, 341, 412, 442]**

### 6.2 Exceeding Resource Constraints
- Entering an integer greater than available grain, land, or labor triggers specific in-character rebuke messages ("THINK AGAIN", "BUT YOU HAVE ONLY P PEOPLE...") and re-prompts the player for that specific decision. Valid previous decisions in the same turn are retained.
- Status: **[VERIFIED lines 322–324, 342–344, 420–422, 445–470]**

### 6.3 Non-Numeric & Malformed Input
- In vintage Microsoft BASIC, entering letters (e.g. `abc`), symbols, or empty carriage returns at a numeric `INPUT` statement caused the BASIC interpreter runtime to print `?REDO FROM START` and re-prompt the user without crashing the game or modifying variables.
- Status: **[INFERRED from Microsoft BASIC interpreter specification]**
- **Modern Python Requirement:** In Python 3, calling `int(input())` on non-numeric input raises a `ValueError`. To prevent crashes, Python code must catch `ValueError` and re-prompt the user safely with `?REDO FROM START` without changing state.
- Status: **[PROPOSED IMPROVEMENT / COMPATIBILITY ENHANCEMENT]**

---

## 7. Historical Quirks & Strict Mode Implementation

To respect both the exact 1978 BASIC listing and modern expectations, the engine defaults to **verified historical behavior** while supporting an optional relaxed/modern mode:

1. **Labor Planting Boundary:**
   - *Historical Default (`strict_historical=True`):* strictly `D < 10 * P` (100 people plant up to 999 acres).
   - *Relaxed Mode (`strict_historical=False`):* allows `D <= 10 * P` (100 people plant up to 1000 acres).
2. **Selling All Land:**
   - *Historical Default (`strict_historical=True`):* strictly `Q < A` (cannot sell 100% of acres).
   - *Relaxed Mode (`strict_historical=False`):* allows `Q <= A` (can sell up to all acres).
3. **Overfeeding Starvation Statistics Quirk:**
   - Preserves exact historical behavior where overfeeding ($P < C$) jumps past lines 552–555, leaving $P_1$ unchanged for that turn.
4. **Plague Probability Math:**
   - Preserves the exact 1978 formula $Q = \lfloor 10(2r - 0.3) \rfloor$, resulting in the actual 20% rate.
5. **Game Over Audio Beeps:**
   - Output routine emits standard `\a` bell characters if supported, ensuring terminal compatibility.
