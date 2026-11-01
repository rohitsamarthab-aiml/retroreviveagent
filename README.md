# RetroRevive — Ancient Babylonian Kingdom Strategy

> **A premium, historically-grounded strategy game built on the legendary 1978 BASIC HAMURABI engine.**  
> Govern Babylon. Feed your people. Build your empire.

---

## 🎮 Quick Start — Double-Click to Play

**Windows:** Double-click `RUN_RETROREVIVE.bat`

First time? Run `setup.bat` to install dependencies automatically.

---

## 🏛️ About the Game

RetroRevive is a modernized tribute to **HAMURABI (1978)** by David H. Ahl (Creative Computing). You govern ancient Sumeria/Babylon for a 10-year term as King Hammurabi — the great lawgiver of the ancient world.

### Game Modes
| Mode | Description |
|------|-------------|
| **Classic 1978** | 100% faithful to the original BASIC rules — buy land, feed people, plant crops |
| **Enhanced Realm** | Royal Advisors, Chronicle Log, and cinematic events |
| **Scenario Challenges** | The Great Drought, Population Boom, Granary Defense |
| **AI Royal Governor** | Autonomous LLM-powered agent with real tool calling, multi-kingdom diplomacy, and military commands |
| **Babylon 3D & Cinematics** | Cinematic Studio, procedural world camera, and Babylon empire immersion |
| **23 Matches (Nim)** | The 1978 Bob Albrecht Nim game, fully playable |

### Core Gameplay Loop (Every Year)
1. **Land Trading** — Buy or sell acres at market price (17–26 bushels/acre)
2. **Ration Grain** — Feed citizens (20 bushels each to survive)
3. **Sow Crops** — Plant acres (1 bushel of seed per 2 acres; 10 acres per worker)
4. **Harvest & Events** — Random yield 1–5 bu/acre; rat infestations; plague; immigration
5. **Review Results** — Royal Annual Report with event banners

### How to Win
Rule for 10 years keeping:
- Average starvation rate **< 3%** and land **≥ 10 acres/person** → **Fantastic (Charlemagne Tier)**
- Avoid impeachment (> 45% population starved in one year)

---


---

## 👑 AI Royal Governor — Autonomous Regional Agent

RetroRevive features a genuinely autonomous **AI Royal Governor** built for **Agentathon**. The Governor acts as the King's autonomous prime minister, making real decisions that directly mutate authoritative game engine state.

### 🧠 Core Agent Architecture
1. **Observe** — Inspects real kingdom state, disaster threats (famine, plague, rodent risk), and food security metrics.
2. **Recall** — Evaluates **Strategic Historical Memory** by analyzing multi-year trends from the Chronicle log.
3. **Think & Plan** — Uses **Google Gemini LLM Function Calling** (via `GEMINI_API_KEY` or `GOOGLE_API_KEY`) with real Python tool execution, with an honest deterministic **Rule-Based Planner** fallback.
4. **Act** — Executes decrees through the authoritative engine (`game_logic.py` and `modern_game_logic.py`).
5. **Verify** — Verifies before-and-after resource deltas, food security buffers, and ensures goal progress.

### 🌍 Multi-Kingdom Regional Simulation
- **Assyria** (Tiglath-Pileser) — Expansionist & militaristic powerhouse.
- **Elam** (King Shutruk) — Aggressive eastern kingdom requiring active deterrence.
- **Ur of Sumer** (Ur-Nammu) — Defensive trading partner rich in cultural heritage.
- Rivals execute independent annual turns (harvests, consumption, army recruitment, opinion adjustments).

### 🛠️ 15 Authoritative Agent Tools
- `inspect_kingdom_state` & `calculate_grain_requirements`
- `allocate_grain`, `manage_land`, & `manage_farming`
- `inspect_disaster_conditions` & `get_advisor_recommendation`
- `get_chronicle_summary` & `advance_kingdom_turn`
- `inspect_rival_kingdoms` & `scout_kingdom`
- `evaluate_war_readiness` & `manage_military`
- `manage_diplomacy` (Trade agreements, alliances, peace treaties)

## 🎨 Visual Features
- **Living Babylonian World** — Animated Euphrates River, Ziggurat of Etemenanki, Royal Palace, Ishtar Gates, farms, and markets
- **Procedural Characters** — King Hammurabi, citizens, farmers, palace guards, merchants, river boats, bird flocks
- **Cinematic Sequences** — Harvest golden sunbeams, plague twilight, drought storms, immigration caravans
- **Day/Sky Cycle** — Sky changes with year progression (dawn → dusk over 10 years)
- **Particles** — Harvest chaff, smoke plumes, rat swarms, victory fireworks
- **Professional UI** — Navy-blue sapphire glass, Mesopotamian gold, lapis lazuli accents

---

## 🔐 Accounts & Saves
- **Guest Mode** — Play instantly without registration
- **Register** — Create a named Sovereign profile with reign statistics and achievements
- **Multi-Slot Saves** — 3 save slots per player (Slot 1, 2, 3)
- **Achievements** — Charlemagne Tier, Ten-Year Reign, and more
- All data stored locally in `accounts.json` and `saves/` — no internet required

---

## ⌨️ Keyboard Shortcuts

### Main Menu
| Key | Action |
|-----|--------|
| `1–7` | Quick-select menu option |
| `↑ / ↓` | Navigate menu |
| `Enter` | Confirm selection |
| `P` | Watch Royal Prologue cinematic |

### Gameplay
| Key | Action |
|-----|--------|
| `Tab` | Cycle input fields |
| `Enter` | Confirm / Execute Decree |
| `R` | Reset inputs |
| `S` | Quick save |
| `A` | Royal Advisors (Enhanced Mode) |
| `C` | Chronicle Log (Enhanced Mode) |
| `G` | Scenario Goals (Scenario Mode) |
| `P / Esc` | Pause menu |

---

## 🖥️ System Requirements

| Component | Requirement |
|-----------|-------------|
| OS | Windows 10/11 (64-bit) |
| Python | 3.14.0 (bundled venv) |
| pygame-ce | 2.5.8 (auto-installed) |
| RAM | 512 MB |
| Display | 1280 × 720 or larger (resizable, letterboxed) |

---

## 📦 Installation

### Option A — Automatic (Recommended)
```batch
double-click  setup.bat
```
Then play:
```batch
double-click  RUN_RETROREVIVE.bat
```

### Option B — Manual
```batch
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

### Option C — Terminal / CLI (no pygame)
```batch
.venv\Scripts\python main.py --cli
```

---

## 🧪 Running Tests

```batch
.venv\Scripts\activate
pytest test_game.py test_modern.py test_auth.py test_ui.py test_platform.py "games\23_matches\test_engine.py" -v
```

**184 tests, all passing on Python 3.14.0.**

---

## 📁 Project Structure

```
RetroRevive/
├── main.py                   # Universal entry point (GUI + CLI)
├── game_logic.py             # Core Hammurabi simulation engine (pure Python)
├── modern_game_logic.py      # Enhanced mode, scenarios, advisors, saves
├── presentation.py           # CLI ASCII animations and terminal renderer
├── retrorevive.py            # Game Library Hub (main launcher screen)
├── auth_manager.py           # Local authentication & multi-slot saves
├── game_registry.py          # Game catalog metadata
│
├── ui_pygame.py              # Main pygame game application (2100+ lines)
├── ui_theme.py               # Design system: colors, fonts, sounds, widgets
├── ui_world.py               # Living Babylonian world renderer
├── ui_characters.py          # Procedural character animation
├── ui_cinematics.py          # Cinematic sequence director
├── ui_districts.py           # Kingdom districts & interactive map pins
├── ui_auth.py                # Login/register/profile modal
│
├── games/
│   └── 23_matches/           # 23 Matches (Nim) game
│       ├── engine.py
│       ├── app.py
│       └── test_engine.py
│
├── assets/
│   ├── babylon_world_bg.jpg  # World background
│   ├── hammurabi_portrait.jpg
│   └── vizier_portrait.jpg
│
├── test_game.py              # 25 Hammurabi engine tests
├── test_modern.py            # 11 Enhanced mode & scenario tests
├── test_auth.py              # 13 Authentication & UI tests
├── test_ui.py                # 37 Pygame UI regression tests
├── test_platform.py          # 16 Platform hub & registry tests
│
├── requirements.txt          # Python dependencies
├── setup.bat                 # One-click dependency installer
├── RUN_RETROREVIVE.bat       # One-click game launcher
├── pytest.ini                # Test configuration
└── conftest.py               # Pytest root config (headless SDL)
```

---

## 🏆 Historical Background

**HAMURABI** was created by David H. Ahl and first published in 1973 in *101 BASIC Computer Games*, then republished in the 1978 edition from Creative Computing Press (Morristown, NJ). It is one of the earliest text-based strategy simulation games, inspired by the Sumerian civilization under the rule of King Hammurabi (~1792–1750 BCE), author of the Code of Hammurabi — one of the earliest written legal codes in human history.

---

## 📜 License

- **Game Engine** — Open source (original public domain BASIC, modernized in Python)
- **pygame-ce** — LGPL 2.1
- **Assets** (portraits, background) — Included for personal/educational use

---

*RetroRevive — Built for the Buildathon 2026 Hackathon*  
*Python 3.14.0 | pygame-ce 2.5.8 | 184 tests passing*
