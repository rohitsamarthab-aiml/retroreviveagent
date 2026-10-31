# RetroRevive Compatibility & Historical Verification Report

This document records the historical evidence, mathematical verification, line-by-line code correspondence, and scope boundaries for RetroRevive's Python 3 modernization of **HAMURABI (1978)**.

---

## 1. Primary Source Attribution & Provenance

- **Game Title:** `HAMURABI`
- **Author:** David H. Ahl (adapting Doug Dyment's 1968 DEC PDP-8 FOCAL program *The Sumer Game*)
- **Definitive Publication:** *BASIC Computer Games: Microcomputer Edition*, Workman Publishing / Creative Computing, Morristown, New Jersey, 1978, pp. 78–79.
- **Corroborating References:**
  1. *AtariArchives Digital Library:* [https://www.atariarchives.org/basicgames/showpage.php?page=78](https://www.atariarchives.org/basicgames/showpage.php?page=78)
  2. *The Hamurabi Collection:* [https://github.com/tajmone/hamurabi-collection](https://github.com/tajmone/hamurabi-collection) (Tristano Ajmone's authorized reproduction of the 1978 Microsoft BASIC source)
  3. *Vintage BASIC Archive:* `http://www.vintage-basic.net/bcg/hammurabi.bas`
  4. *Basic Computer Games GitHub Repository:* [https://github.com/coding-horror/basic-computer-games](https://github.com/coding-horror/basic-computer-games)

---

## 2. Rule Verification Matrix

| Game Feature | Historical Line(s) | Original BASIC Code / Formula | Modern Implementation (`game_logic.py`) | Status |
|---|---|---|---|---|
| **Turn 1 Init** | 95–110, 215–218 | `P=95, S=2800, H=3000, Y=3, A=1000, I=5; P=P+I` | `init_game()` sets $P=100$, $S=2800$, $A=1000$, $Y=3$, $E=200$, $I=5$ | **VERIFIED** |
| **Land Price** | 310–312 | `C=INT(10*RND(1)): Y=C+17` | `calculate_land_price()` $\rightarrow 17 \le Y \le 26$ | **VERIFIED** |
| **Buy Land** | 320–334 | `INPUT Q: IF Q<0 THEN 850: IF Y*Q<=S THEN A=A+Q: S=S-Y*Q: GOTO 400` | `validate_buy_land()` validates affordability, deducts grain, skips sell | **VERIFIED** |
| **Sell Land** | 340–350 | `INPUT Q: IF Q<0 THEN 850: IF Q<A THEN A=A-Q: S=S+Y*Q` | `validate_sell_land()` enforces strictly $< A$ (or $\le A$ in relaxed) | **VERIFIED** |
| **Feed People** | 410–430 | `INPUT Q: IF Q<0 THEN 850: IF Q<=S THEN S=S-Q` | `validate_feed_people()` checks store, deducts grain | **VERIFIED** |
| **Plant Seed** | 440–470, 510 | `INPUT D: IF D<=A; IF INT(D/2)<=S; IF D<10*P; S=S-INT(D/2)` | `validate_plant_seed()` checks land, seed ($D//2$), labor ($< 10P$) | **VERIFIED** |
| **Crop Harvest** | 511–515, 800 | `GOSUB 800: Y=C: H=D*Y` where `C=INT(RND(1)*5)+1` | Yield $Y \in [1, 5]$; Harvest $H = D \times Y$ | **VERIFIED** |
| **Rat Infestation** | 521–530 | `GOSUB 800: IF INT(C/2)<>C/2 THEN 530; E=INT(S/C); S=S-E+H` | Even roll: rats eat $S // C$; store updated as $S - E + H$ | **VERIFIED** |
| **Immigration** | 531–533 | `GOSUB 800: I=INT(C*(20*A+S)/P/100+1)` | $I = \lfloor C(20A + S) / (100P) \rfloor + 1$ | **VERIFIED** |
| **Starvation Count** | 540, 552 | `C=INT(Q/20): D=P-C` | Full tummies $C = \lfloor Q / 20 \rfloor$; Deaths $D = P - C$ | **VERIFIED** |
| **Impeachment** | 552, 560–567 | `IF D>.45*P THEN 560: GOTO 990` | If $D > 0.45 P$: prints National Fink message and exits | **VERIFIED** |
| **Starvation Avg** | 553 | `P1=((Z-1)*P1+D*100/P)/Z` | Running average: $P_1 = ((Z-1)P_1 + 100D/P) / Z$ | **VERIFIED** |
| **Plague Roll** | 541–542, 227–228 | `Q=INT(10*(2*RND(1)-.3)); IF Q<=0 THEN P=INT(P/2)` | $Q \le 0$ triggers plague next year; pop halved | **VERIFIED** |
| **Term End** | 270, 860 | `IF Z=11 THEN 860` | Year 11 check triggers `evaluate_term()` after Year 10 report | **VERIFIED** |
| **Final Rating Tiers**| 880–905 | Fink ($P_1>33$ or $L<7$), Nero ($P_1>10$ or $L<9$), Mediocre ($P_1>3$ or $L<10$), Charlemagne | Evaluated sequentially in exact order | **VERIFIED** |
| **Negative Input** | 321, 341, 412, 442| `IF Q<0 THEN 850: GOTO 990` | Triggers steward fired and exits immediately | **VERIFIED** |
| **Non-Numeric Input**| BASIC Runtime | Interpreter caught `ValueError` with `?REDO FROM START` | `safe_prompt_int()` catches `ValueError`, prints `?REDO FROM START` | **INFERRED / ENHANCED** |

---

## 3. Discrepancies and Historical Quirks

### 3.1 Labor Capacity Strict Less-Than (`D < 10 * P`)
- **Historical Code (Line 455):** `455 IF D<10*P THEN 510`
- **Impact:** 100 people cannot tend 1,000 acres, only 999.
- **Handling:** RetroRevive enforces this strict historical behavior by default. Users may pass `--relaxed` to allow $D \le 10P$.

### 3.2 Land Sale Strict Less-Than (`Q < A`)
- **Historical Code (Line 342):** `342 IF Q<A THEN 350`
- **Impact:** A ruler cannot sell 100% of their land; at least 1 acre must be kept.
- **Handling:** Preserved by default. The `--relaxed` flag enables selling up to $A$.

### 3.3 Overfeeding Starvation Statistic Bypass
- **Historical Code (Line 550):** `550 IF P<C THEN 210`
- **Impact:** Overfeeding citizens skips line 553, leaving $P_1$ unchanged instead of averaging in 0% for that turn.
- **Handling:** Verified and preserved verbatim in `game_logic.py`.

### 3.4 Actual 20% Plague Chance vs 15% Comment
- **Historical Code (Lines 541–542):** `REM *** HORROS, A 15% CHANCE OF PLAGUE` followed by `Q = INT(10 * (2 * RND(1) - 0.3))`.
- **Mathematical Reality:** For any $r < 0.20$, $10(2r - 0.3) < 1.0$, which yields $Q \le 0$ when floored. Thus, the real probability is 20%.
- **Handling:** Verified mathematical implementation preserved.

---

## 4. Known Scope Boundaries

- **Single Game Scope:** Modernizes only the 1978 Microsoft BASIC edition of *Hammurabi*. Other historical variants (1968 FOCAL, 1973 DEC `HMRABI`) are documented but not combined.
- **Console Only:** Adheres strictly to a clean command-line application using standard Python library. Web interfaces, databases, multiplayer, and external third-party dependencies are intentionally out of scope for this buildathon project.

---

## 5. Cosmetic Presentation Layer (`presentation.py`)

- **Strict Separation:** Visual effects, ASCII scenes, and animations are strictly cosmetic presentation routines. They consume read-only `GameState` attributes and never alter game rules, formulas, or random event outcomes.
- **Portability & Encodings:** All ASCII assets use standard 7-bit characters (`+`, `-`, `|`, `*`, `#`, `=`), ensuring 100% crash-free execution on Windows `cp1252`, `cp437`, and POSIX `utf-8`.
- **Automatic Fallback:** When stdout is redirected to a pipe, running inside automated test runners, or when `NO_COLOR` / `TERM=dumb` is set, `presentation.py` automatically falls back to clean plain-text output with zero delay, ensuring tests remain instantaneous and deterministic.
