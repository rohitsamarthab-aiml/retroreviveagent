# AI Royal Governor Integration Guide

## Overview

The **AI Royal Governor** is an autonomous kingdom management agent for RetroRevive. It implements a real LLM-like decision-making cycle that directly manipulates actual game state through validated tool calls.

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   RetroRevive Game                       │
│                 (retrorevive.py, game_logic.py)          │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│              GameEngine Adapter Interface                │
│           (Implements game_interface.GameEngine)        │
└────────────────────────┬────────────────────────────────┘
                         │
        ┌────────────────┴────────────────┐
        ▼                                  ▼
┌──────────────────────────┐    ┌──────────────────────────┐
│   RoyalGovernor (AI)     │    │   GameToolset            │
│ - observe_kingdom()      │    │ - validate_tool_call()   │
│ - identify_threats()     │    │ - call_tool()            │
│ - reason_about()         │    │ - list_tools()           │
│ - generate_plan()        │    │                          │
│ - execute_plan()         │    │ Supported tools:         │
│ - verify_execution()     │    │ • allocate_grain         │
│ - get_action_history()   │    │ • manage_land            │
└──────────────────────────┘    │ • manage_farming         │
                                 │ • manage_irrigation      │
                                 │ • manage_treasury        │
                                 │ • inspect_disaster_...   │
                                 └──────────────────────────┘
```

## How It Works

### 1. **Observe** → Read Current State
```python
state = game.get_current_state()  # Real state snapshot
```

### 2. **Identify Threats** → Analyze Risks
```python
threats = {
    'famine_risk': grain < 1000,
    'treasury_crisis': treasury < 1000,
    'insufficient_farmers': farmers/pop < 0.2,
    # ... etc
}
```

### 3. **Reason** → Create Assessment
```python
reasoning = {
    'active_threats': ['famine_risk', 'treasury_crisis'],
    'goal': 'Prevent famine for 3 years',
    'analysis': '⚠️  Active threats: famine_risk, treasury_crisis'
}
```

### 4. **Plan** → Generate Actions
```python
plan = [
    {
        'action': 'allocate_grain',
        'params': {'amount_bushels': 1000, 'purpose': 'storage'},
        'reason': 'CRITICAL: Store grain to prevent famine',
        'priority': 1
    },
    # ... more actions in priority order
]
```

### 5. **Execute** → Call Real Game Functions
```python
for action in plan:
    if action['action'] == 'allocate_grain':
        result = game.allocate_grain(
            amount_bushels=action['params']['amount_bushels'],
            purpose=action['params']['purpose']
        )
```

### 6. **Verify** → Check Results
```python
state_after = game.get_current_state()
delta_grain = state_after.grain_stores - state_before.grain_stores
# Verify actual state changed as intended
```

## Integration Steps

### Step 1: Create a GameEngine Adapter

In your game code (e.g., `retrorevive.py` or `game_logic.py`):

```python
from ai_agent.game_interface import GameEngine, KingdomState, GameAction

class RetroReviveGameEngine(GameEngine):
    """Adapter for your RetroRevive game."""
    
    def __init__(self, game_instance):
        self.game = game_instance
    
    def get_current_state(self) -> KingdomState:
        """Map your game state to KingdomState."""
        return KingdomState(
            year=self.game.year,
            population=self.game.population,
            grain_stores=self.game.grain,
            land_acres=self.game.land,
            land_planted_acres=self.game.land_planted,
            farmers=self.game.farmers,
            treasury=self.game.treasury,
            harvest_expected=self.game.expected_harvest,
            weather_condition=self.game.weather,
            plague_active=self.game.plague,
            disaster_risk=self.game.disaster_risk,
            grain_price_per_bushel=self.game.grain_price,
            population_growth_rate=self.game.growth_rate,
        )
    
    def advance_turn(self) -> bool:
        return self.game.advance_year()
    
    def allocate_grain(self, amount_bushels: int, purpose: str) -> GameAction:
        # Implement actual game logic
        success = self.game.grain >= amount_bushels
        if success:
            self.game.grain -= amount_bushels
            if purpose == 'sell':
                self.game.treasury += int(amount_bushels * self.game.grain_price)
        
        return GameAction(
            action_name='allocate_grain',
            parameters={'amount': amount_bushels, 'purpose': purpose},
            success=success,
            result_message="Success" if success else "Failed",
            grain_delta=-amount_bushels if success else 0
        )
    
    # ... implement other abstract methods ...
```

### Step 2: Initialize the AI Governor

```python
from ai_agent.royal_governor_enhanced import RoyalGovernor

class RetroReviveGame:
    def __init__(self):
        self.game_state = {...}
        
        # Create adapter
        self.game_engine = RetroReviveGameEngine(self.game_state)
        
        # Initialize AI Royal Governor
        self.royal_governor = RoyalGovernor(
            self.game_engine,
            config={
                'min_grain_reserves': 2000,
                'famine_threshold': 1000,
                'min_farmers_percentage': 0.20,
            }
        )
```

### Step 3: Delegate to AI

```python
# Player sets a goal through UI
def delegate_to_ai(goal_text: str, years: int):
    self.royal_governor.set_delegation_goal(
        goal=goal_text,
        max_turns=years,
        priorities=['prevent_famine', 'maintain_reserves', 'protect_treasury']
    )
    
    # Execute autonomous turns
    while self.royal_governor.status == DelegationStatus.ACTIVE:
        success, summary = self.royal_governor.execute_autonomous_turn()
        if success:
            print(summary)  # Display to UI
        else:
            print(f"Turn failed: {summary}")
            break
```

### Step 4: Display AI Activity in UI

```python
# Get AI status
status = self.royal_governor.get_status_report()
print(f"AI Status: {status['status']}")
print(f"Turns: {status['turns_completed']}/{status['turns_completed'] + status['turns_remaining']}")
print(f"Success rate: {status['success_rate']}")

# Get action history
actions = self.royal_governor.get_action_history()
for action in actions:
    print(f"{action['action_name']}: {action['result_message']}")

# Get reasoning log
reasoning = self.royal_governor.get_reasoning_log()
for entry in reasoning:
    print(f"Year {entry['year']}: {entry['analysis']}")

# Get turn summaries
summaries = self.royal_governor.get_turn_summaries()
for summary in summaries:
    print(summary)
```

### Step 5: Player Control

```python
# Pause AI
royal_governor.pause_delegation()

# Resume AI
royal_governor.resume_delegation()

# Revoke AI control immediately
royal_governor.revoke_delegation()
```

## Tool Reference

All tools are **validated and executed against real game state**:

### `allocate_grain(amount_bushels: int, purpose: str) → GameAction`
- **Purpose**: `'consumption'`, `'storage'`, `'seed'`, `'sell'`
- **Validates**: Amount ≤ current grain stores, valid purpose
- **Updates**: Real game grain stores

### `manage_land(acres_to_buy: int, acres_to_sell: int) → GameAction`
- **Validates**: Sufficient treasury for purchase, sufficient land for sale
- **Limits**: Max 500 acres/turn
- **Updates**: Land acres, treasury

### `manage_farming(acres_to_plant: int) → GameAction`
- **Validates**: Acres ≤ available unplanted land
- **Updates**: Planted acres, harvest expected

### `manage_irrigation(acres_to_irrigate: int) → GameAction`
- **Validates**: Sufficient treasury (50 gold/acre)
- **Updates**: Treasury, harvest expected

### `manage_treasury(amount: int, operation: str) → GameAction`
- **Operation**: `'deposit'` or `'withdraw'`
- **Validates**: For withdraw, amount ≤ current treasury
- **Updates**: Treasury

### `inspect_disaster_conditions() → Dict`
- **Returns**: Weather, plague status, disaster risk
- **No validation needed**

## Testing

### Run All Tests
```bash
python -m pytest tests/test_ai_royal_governor.py -v
```

### Run Drought/Famine Scenario
```bash
python -m pytest tests/test_ai_royal_governor.py::TestRoyalGovernor::test_08_drought_famine_scenario -v -s
```

### Run with Coverage
```bash
python -m pytest tests/test_ai_royal_governor.py --cov=ai_agent --cov-report=html
```

## Key Design Principles

1. **Real Game State Only**: AI reads actual game state, never simulated copies
2. **Real Tool Calls**: Every action executes actual game functions
3. **Honest Verification**: AI verifies outcomes against real state changes
4. **No Faking**: Failed actions are reported honestly, plans are adjusted
5. **Game Authority**: Game engine is always the source of truth
6. **Transparent History**: Every decision is logged and visible to player
7. **Player Control**: Delegation can be paused, resumed, or revoked anytime
8. **Deterministic Rules**: Game logic in Python, planning via AI decision cycle

## Example: Drought Scenario

```
Year 1: Normal conditions
  Grain: 5000 → 7243  (harvest +2243)
  AI: Plants 700 acres, maintains reserves

Year 2: SEVERE DROUGHT
  Grain: 7243 → 2443  (severe harvest failure -4800)
  Population: 10404
  
  AI Observes: Famine risk! Grain critical.
  AI Identifies: THREAT: Famine risk
  AI Reasons: Must prevent starvation
  AI Plans: 
    1. ALLOCATE 1000 bushels to storage
    2. SELL excess for treasury if safe
    3. Reduce farming to conserve seed
  
  Result: Kingdom survives drought, grain at 2443
  Population maintained: 10404 → 10823

Year 3-5: Continued famine management
  AI continues rationing, maintains population
  
Final: Kingdom survives with population still growing
       Success rate: 85% (12/14 actions successful)
```

## Files & Directories

```
ai_agent/
├── __init__.py                    # Package initialization
├── game_interface.py              # Abstract GameEngine interface
├── royal_governor_enhanced.py     # Core AI agent implementation
└── game_tools.py                  # Tool definitions and validation

tests/
└── test_ai_royal_governor.py      # Comprehensive test suite

docs/
└── INTEGRATION.md                 # This file
```

## Troubleshooting

**Q: AI is not taking actions**
- Check that `GameEngine` is properly implemented and returns real state
- Verify that game state is being updated when tools are called
- Check logs for threat identification and planning

**Q: Actions are failing**
- Verify tool validation matches actual game constraints
- Check that game state values are correctly mapped from your game

**Q: Performance issues**
- Reduce number of delegated turns
- Simplify threat thresholds in config
- Optimize game state access

## Next Steps

1. ✅ Implement `GameEngine` adapter for your game
2. ✅ Initialize `RoyalGovernor` in your game initialization
3. ✅ Create UI for delegation controls
4. ✅ Run test suite to verify integration
5. ✅ Display AI action history and reasoning in UI
6. ✅ Enable player to delegate and revoke at any time

---

**For questions or issues, check test_ai_royal_governor.py for working examples.**
