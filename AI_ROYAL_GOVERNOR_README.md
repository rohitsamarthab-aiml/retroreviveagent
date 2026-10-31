# 🤖 AI Royal Governor - Autonomous Kingdom Management Agent

A **production-ready AI agent** for the RetroRevive Hammurabi game that autonomously manages kingdom resources through real game state observation, planning, and execution.

## ✨ Features

- **Autonomous Decision Cycle**: Observe → Identify Threats → Reason → Plan → Execute → Verify
- **Real Game Integration**: All AI actions directly manipulate actual game state (no simulations)
- **Tool-Based Execution**: Validated tool calls to real game functions
- **Threat Intelligence**: Identifies famine, plague, treasury crisis, overpopulation risks
- **Goal-Based Planning**: Respects priorities and generates action sequences
- **Verified Execution**: Confirms outcomes against real state changes
- **Player Control**: Delegation can be paused, resumed, or revoked instantly
- **Transparent History**: Complete action history, reasoning logs, and turn summaries
- **Comprehensive Testing**: Includes drought/famine survival scenarios

## 🚀 Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Create a GameEngine Adapter
```python
from ai_agent import GameEngine, KingdomState

class MyGameEngine(GameEngine):
    def __init__(self, game):
        self.game = game
    
    def get_current_state(self) -> KingdomState:
        return KingdomState(
            year=self.game.year,
            population=self.game.population,
            grain_stores=self.game.grain,
            # ... map all state fields
        )
    
    # Implement abstract methods...
```

### 3. Initialize and Delegate
```python
from ai_agent import RoyalGovernor

engine = MyGameEngine(game)
governor = RoyalGovernor(engine)

# Set a goal and let AI manage
governor.set_delegation_goal(
    goal="Prevent famine for 5 years",
    max_turns=5,
    priorities=['prevent_famine', 'maintain_reserves']
)

# Execute autonomous turns
while governor.status.value == 'active':
    success, summary = governor.execute_autonomous_turn()
    print(summary)
```

### 4. Monitor AI Activity
```python
# Get status
status = governor.get_status_report()
print(f"Turns: {status['turns_completed']}/{status['turns_remaining']}")
print(f"Success rate: {status['success_rate']}")

# Get action history
actions = governor.get_action_history()
reasoning = governor.get_reasoning_log()
summaries = governor.get_turn_summaries()
```

## 📊 How It Works

```
┌─────────────────────────────────────────┐
│         Observe Kingdom State            │
│  (population, grain, land, treasury...)  │
└──────────────┬──────────────────────────┘
               ▼
┌─────────────────────────────────────────┐
│       Identify Active Threats            │
│  (famine, plague, treasury crisis...)    │
└──────────────┬──────────────────────────┘
               ▼
┌─────────────────────────────────────────┐
│     Reason About the Situation           │
│  (analyze risks, assess goal progress)   │
└──────────────┬──────────────────────────┘
               ▼
┌─────────────────────────────────────────┐
│       Generate Action Plan               │
│  (prioritize actions respecting rules)   │
└──────────────┬──────────────────────────┘
               ▼
┌─────────────────────────────────────────┐
│    Execute Actions (Real Game Tools)     │
│  (allocate_grain, manage_land, etc.)     │
└──────────────┬──────────────────────────┘
               ▼
┌─────────────────────────────────────────┐
│     Verify Outcomes & State Changes      │
│  (confirm actual game state updated)     │
└──────────────┬──────────────────────────┘
               ▼
┌─────────────────────────────────────────┐
│        Advance Game Turn                 │
│  (populations grow, harvests happen...)  │
└─────────────────────────────────────────┘
```

## 🛠️ AI Tools

The agent can call these real game functions:

| Tool | Purpose | Validates |
|------|---------|-----------|
| `allocate_grain()` | Store/sell/consume grain | Amount ≤ stores |
| `manage_land()` | Buy/sell land | Budget, acreage limits |
| `manage_farming()` | Plant crops | Available land |
| `manage_irrigation()` | Improve harvests | Treasury ≥ cost |
| `manage_treasury()` | Deposit/withdraw gold | Amount ≤ available |
| `inspect_disaster_conditions()` | Check risks | Weather, plague, risk % |
| `advance_kingdom_turn()` | Progress game | Game rules |
| `inspect_kingdom_state()` | Read current state | Always available |

## 🧪 Testing

### Run All Tests
```bash
python -m pytest tests/test_ai_royal_governor.py -v
```

### Run Drought/Famine Test
```bash
python -m pytest tests/test_ai_royal_governor.py::TestRoyalGovernor::test_08_drought_famine_scenario -v -s
```

### Example Test Output
```
[Year 1] Normal conditions
  Initial grain: 5000 bushels
  AI: Year 1 | Turn 1/5 | Population: 10200 | Grain: 7243 | Land: 1000 | Treasury: 5000

[Year 2] SEVERE DROUGHT STRIKES!
  Grain before: 7243
  AI identifies famine risk
  AI executes: allocate_grain (priority 1)
  Year 2 | Turn 2/5 | Population: 10404 | Grain: 2443 | Land: 1000 | Treasury: 5000

[Years 3-5] Continuing through famine...
  AI maintains rationing policy
  Population grows despite famine: 10404 → 11039
  Kingdom survives!

FINAL RESULTS:
  Year: 5
  Population: 11039 ✓ (not extinct)
  Grain: 100 (critically low but survived)
  AI Actions: 12/14 successful (85.7% success rate)
  Status: COMPLETED ✓
```

## 📁 Project Structure

```
retroreviveagent/
├── ai_agent/
│   ├── __init__.py                    # Package exports
│   ├── game_interface.py              # GameEngine abstract interface
│   ├── royal_governor_enhanced.py     # Core AI agent implementation
│   └── game_tools.py                  # Tool validation and calling
├── tests/
│   └── test_ai_royal_governor.py      # Comprehensive test suite
├── docs/
│   └── INTEGRATION.md                 # Integration guide
├── requirements.txt                   # Python dependencies
└── README.md                          # This file
```

## 📖 Documentation

- **[INTEGRATION.md](docs/INTEGRATION.md)** - Step-by-step integration guide with code examples
- **[test_ai_royal_governor.py](tests/test_ai_royal_governor.py)** - Working examples and scenarios
- **Source docstrings** - Full API documentation in code

## 🎯 Design Principles

1. **Real Game State Only**
   - AI reads and modifies actual game state
   - No separate simulations or copies
   - GameEngine is the single source of truth

2. **Honest Execution**
   - Failed actions are reported, not hidden
   - Plans are adjusted based on actual results
   - No hardcoded success responses

3. **Validated Tool Calls**
   - Every tool call is validated before execution
   - Game rules are always respected
   - Constraints are enforced (e.g., can't spend more than treasury)

4. **Transparent Decision Making**
   - All observations logged
   - All reasoning steps recorded
   - Complete action history maintained
   - Player can see why AI made each decision

5. **Player Control**
   - Delegation can be paused at any time
   - Delegation can be resumed from pause
   - Delegation can be revoked instantly
   - Player can always take control

6. **Deterministic & Testable**
   - All AI decisions are deterministic given state
   - No randomness in reasoning
   - Fully testable with mock game engine
   - Reproducible scenarios

## 🔧 Configuration

Create custom thresholds when initializing:

```python
governor = RoyalGovernor(
    engine,
    config={
        'min_grain_reserves': 3000,      # Minimum bushels to keep
        'famine_threshold': 500,         # When to panic
        'min_farmers_percentage': 0.25,  # Min % of population
        'max_land_investment': 0.2,      # Max % of treasury
        'critical_population': 50,       # Game over threshold
    }
)
```

## 🔗 Integration Checklist

- [ ] Implement `GameEngine` adapter
- [ ] Test adapter returns real game state
- [ ] Test adapter executes real game actions
- [ ] Initialize `RoyalGovernor` in game
- [ ] Add delegation UI controls
- [ ] Display AI action history
- [ ] Display AI reasoning logs
- [ ] Display real-time status
- [ ] Implement pause/resume/revoke controls
- [ ] Run test suite
- [ ] Test with real game scenarios

## ⚡ Performance Notes

- Single autonomous turn: ~10-50ms (depends on threat analysis complexity)
- 5-turn delegation: ~100-300ms
- No external API calls (purely local)
- Memory overhead: ~1MB per session
- Scales with game state complexity, not number of previous turns

## 🐛 Troubleshooting

**AI not taking actions?**
- Verify `GameEngine` adapter is returning real state
- Check that game state is being updated when tools execute
- Review logs for threat identification

**Actions always failing?**
- Verify tool validation matches actual game constraints
- Check game state field mappings
- Ensure sufficient resources before testing

**Integration errors?**
- See [INTEGRATION.md](docs/INTEGRATION.md)
- Check test_ai_royal_governor.py for working examples
- Review docstrings in source code

## 📝 License

Same as RetroRevive

## 🤝 Contributing

1. Maintain real game state interaction (no simulations)
2. Always validate tool calls before execution
3. Add tests for new threat types
4. Update action history and reasoning logs
5. Ensure player control is always available

## 📞 Support

See documentation in `docs/` directory or example code in `tests/test_ai_royal_governor.py`

---

**Ready to let the AI manage your kingdom!** 👑
