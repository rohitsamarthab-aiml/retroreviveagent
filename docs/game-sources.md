# RetroRevive — Historical Game Sources & Licensing Provenance

**Event:** Confluence Buildathon 2026  
**Track:** Resurrections  
**Documentation:** Provenance, Historical Attribution, and Legal Distinctions

---

## 1. Overview of Legal & Historical Preservation Standards

RetroRevive modernizes classic text games from early computing history into clean, maintainable Python applications with polished desktop graphics.

To respect historical attribution and software licensing:
1. **Rule Engine Integrity:** RetroRevive implements the mathematical rules and algorithms of classic games based on authoritative public documentation and literature.
2. **No Unauthorized Code Redistribution:** RetroRevive does **not** copy complete proprietary historical source listings or binary ROMs into the repository. All Python code is original work created for RetroRevive.
3. **Attribution of Creators:** Full credit is given to the pioneering programmers, educators, and authors who created and popularized these games in the 1960s and 1970s.

---

## 2. Implemented Games

### 2.1. Hammurabi (The Sumer Game)

| Attribute | Verified Historical Record |
| :--- | :--- |
| **Original Creator** | Doug Dyment (1968) |
| **Original Platform** | DEC PDP-8 in the FOCAL-69 language (The Sumer Game) |
| **Adaptation & Microcomputer Port** | David H. Ahl (1973, 1978) |
| **First Book Publication** | *101 BASIC Computer Games* (Digital Equipment Corporation, Maynard, MA, 1973) |
| **Microcomputer Publication** | *BASIC Computer Games: Microcomputer Edition*, ed. David H. Ahl, Creative Computing Press, Morristown, NJ, 1978, pp. 78–79 |
| **Target Verified Edition** | **1978 Microsoft BASIC microcomputer edition** |
| **Public Archive Reference** | AtariArchives.org, Digital Preservation Project |

#### Historical Fidelity in RetroRevive
- **Classic 1978 Mode:** Faithfully mirrors the calculations and valid-input behavior of lines 215–560 of the 1978 BASIC listing.
  - Feeding: 20 bushels per person to survive ($C = \text{INT}(P \times 20)$).
  - Planting: 1 acre requires 1 bushel of seed ($S = \text{INT}(A)$); 1 citizen can tend up to 10 acres ($L = \text{INT}(P \times 10)$).
  - Land Price: Randomized annually between 17 and 26 bushels per acre ($Y = \text{INT}(RND(1) \times 10) + 17$).
  - Rat Infestation: Only occurs on odd-parity random years ($\text{INT}(E/2) \times 2 \ne E$); eats $\text{INT}(S / \text{yield})$.
  - Impeachment: Starving more than 45% of the population in any single year triggers immediate dismissal and public expulsion.
  - Evaluation Tiers: 4 historical ratings based on 10-year average starvation percentage and final acres per person (Nero, Fink, Mediocre assassination, Charlemagne).
- **Safe Input Handling:** Rejects non-integers, floats, negative numbers, and out-of-range orders without corrupting game state, echoing the authentic `?REDO FROM START` behavior.
- **Enhanced Mode (RetroRevive Original):** Royal Advisors, Scenario Challenges, and Chronicle Log are built as non-breaking, optional modern additions on top of the verified engine.

---

### 2.2. 23 Matches (The Game of Nim)

| Attribute | Verified Historical Record |
| :--- | :--- |
| **Original Creator** | Bob Albrecht (1973) |
| **Original Organization** | People's Computer Company (Menlo Park, CA) |
| **Book Publication** | *101 BASIC Computer Games* (1973, ed. David H. Ahl) |
| **Microcomputer Publication** | *BASIC Computer Games: Microcomputer Edition* (Creative Computing Press, 1978, pp. 177–178, Game #93) |
| **Target Verified Edition** | **1978 Microsoft / Creative Computing BASIC edition** |
| **Program File Name in Archives** | `23matches.bas` / `23match.bas` |

#### Historical Game Mechanics
- **The Setup:** A pile starts with exactly 23 matches on the table.
- **Turn Order:** Two players (human and computer) take turns. The human player moves first in the historical standard game.
- **Legal Moves:** A player may remove 1, 2, or 3 matches from the table.
- **Move Constraint:** A player cannot remove more matches than remain on the table (e.g. if 2 matches remain, taking 3 is illegal).
- **The Objective (Misère Nim):** Whichever player takes the **very last match** loses the game!
- **Historical 1978 AI (Bob Albrecht Formula):**
  - Line 205 in the original BASIC listing: `Z1 = 4 - Z`.
  - The computer takes $4 - Z$, where $Z$ is the number of matches the human player took.
  - By taking $4 - Z$, the pair of moves removes $Z + (4 - Z) = 4$ matches per round.
  - Bob Albrecht designed this specific starting number (23) for educational discovery:
    - If the human knows the mathematical secret and takes 2 on the first move ($23 - 2 = 21$), the human reaches a winning position ($21 \equiv 1 \pmod 4$)!
- **Master Mind AI (Optimal Modular Nim):**
  - Targets leaving the opponent with $(N' - 1) \equiv 0 \pmod 4$ (i.e. 21, 17, 13, 9, 5, or 1 match).
  - Evaluates remainder $r = (N - 1) \bmod 4$. If $r \in \{1, 2, 3\}$, the AI takes $r$ matches, locking the human into an unwinnable position.

---

## 3. Planned Catalog Expansion (Coming Soon Titles)

The following games are indexed in `game_registry.py` and planned for future milestone resurrection:

### 3.1. Lunar Lander
- **Original Creator:** Jim Storer (Lexington High School, 1969).
- **Publication:** *101 BASIC Computer Games* (DEC, 1973); *BASIC Computer Games* (1978, pp. 106–108).
- **Mechanics:** Physics-based numerical simulation of Apollo 11 lunar module descent. Burn fuel rates against lunar gravity ($1.62 \text{ m/s}^2$). Soft landing achieved below 5 ft/sec.

### 3.2. Super Star Trek
- **Original Creator:** Mike Mayfield (1971, SDS Sigma 7); adapted by David H. Ahl & Bob Leedom (1974).
- **Publication:** *Creative Computing* (1974); *BASIC Computer Games* (1978, pp. 157–163).
- **Mechanics:** 8x8 quadrant galaxy command simulation. Energy management across phasers, photon torpedoes, long-range sensors, and dockings at starbases before stardates elapse.

### 3.3. The Oregon Trail
- **Original Creators:** Don Rawitsch, Bill Heinemann, and Paul Dillenberger (1971).
- **Original Organization:** MECC (Minnesota Educational Computing Consortium).
- **Publication:** *Creative Computing* (May/June 1978).
- **Mechanics:** 2,040-mile pioneer journey from Missouri to Oregon. Supply management (oxen, bullets, clothing, food) and risk mitigation across river fords and outbreaks of illness.

---

## 4. Software License & Copyright Notice

- **RetroRevive Implementation:** Copyright © 2026 RetroRevive Contributors. Released under the open-source MIT License.
- **Historical Algorithms & Rules:** Game rules, mathematical principles, and formulas are documented historical concepts published in early public computing literature for educational and non-commercial preservation.
- **Audio Synthesizer:** Pure procedural math tone generator (`ui_theme.py`) generating custom sine/square waves in memory with no third-party audio files or copyrighted samples.
