# RetroRevive — Ancient Babylonian Kingdom Strategy

> **A premium, historically-grounded strategy game built on the legendary 1978 BASIC HAMURABI engine.**  
> Govern Babylon. Feed your people. Build your empire.

---

## 🎮 Quick Start — Double-Click to Play

**Windows:** Double-click `RUN_RETROREVIVE.bat`

First time? Run `setup.bat` to install dependencies automatically.

---

## 🏛️ About the Game

RetroRevive is a modernized tribute to **HAMURABI (1978)**. You govern ancient Babylon for a 10-year term as King Hammurabi.

### 🤖 Upgraded AI Royal Governor (NEW)
The game now features a **genuine LLM-powered autonomous AI agent**. You can delegate your kingdom's management to the Royal Governor, who handles:
- **Agriculture & Economy**: Rations grain, buys land, and manages harvests.
- **Military & Intelligence**: Recruits soldiers, builds fortifications, and scouts rival kingdoms.
- **Diplomacy & Trade**: Negotiates alliances, trade agreements, and peace treaties with rivals.
- **ReAct Reasoning**: The agent observes the kingdom, identifies threats (famine, war), reasons through a plan, and executes actions.

*To enable the full LLM experience, set your `GEMINI_API_KEY` or `GOOGLE_API_KEY` in your environment.*

### 🌍 Living Multi-Kingdom World (NEW)
Babylon is no longer alone. Interact with three active rival kingdoms:
- **Assyria**: A powerful expansionist neighbor.
- **Elam**: An aggressive military rival.
- **Ur of Sumer**: A traditional trading partner.

Each kingdom has its own population, treasury, and military, making independent decisions that affect the regional economy and stability.

---

## 🎨 Visual Features
- **Kingdom Intelligence Dashboard**: Compare your strength with rivals in real-time.
- **Diplomacy Center**: Manage envoys and view relationship status (Ally, Hostile, War).
- **Living Babylonian World**: Animated Euphrates, Ziggurat, Ishtar Gates, and markets.
- **Day/Sky Cycle**: Sky changes with year progression.

---

## ⌨️ Keyboard Shortcuts

### Main Menu
| Key | Action |
|-----|--------|
| `1–7` | Quick-select menu option |
| `Enter` | Confirm selection |
| `G` | **Open AI Royal Governor Dashboard** |

### Gameplay
| Key | Action |
|-----|--------|
| `Tab` | Cycle input fields |
| `A` | Royal Advisors (Enhanced Mode) |
| `I` | **Kingdom Intelligence & Diplomacy** |
| `S` | Quick save |
| `P / Esc` | Pause menu |

---

## 📦 Installation

### Automatic (Recommended)
```batch
double-click setup.bat
```

### Manual
```batch
pip install -r requirements.txt
python main.py
```

### LLM Setup (Optional)
```batch
set GEMINI_API_KEY=your_key_here
python main.py
```

---

## 🧪 Running Tests

```batch
pytest test_game.py test_modern.py test_royal_governor.py test_multi_kingdom_agent.py -v
```

**125+ tests, all passing.**

---

## 🏆 Historical Background

**HAMURABI** was created by David H. Ahl in 1978. RetroRevive expands this classic with modern AI and multi-agent simulation while preserving the authoritative 1978 logic at its core.

---

*RetroRevive — Built for the Buildathon 2026 Hackathon*  
*Python 3.14.0 | pygame-ce 2.5.8*
