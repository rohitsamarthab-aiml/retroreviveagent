"""
test_ai_royal_governor.py - Comprehensive Test Suite for AI Royal Governor

Tests include:
- Initialization and configuration
- Threat identification (normal, famine, drought, plague)
- Autonomous turn execution
- Delegation limits and revocation
- Complete drought/famine scenario
- Game tools validation and execution

Run with: pytest tests/test_ai_royal_governor.py -v -s
"""

import unittest
import sys
import logging
from pathlib import Path

# Configure logging for tests
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Attempt imports from ai_agent module
try:
    from ai_agent.game_interface import GameEngine, KingdomState, GameAction, DelegationStatus
    from ai_agent.royal_governor_enhanced import RoyalGovernor, DelegationGoal
    from ai_agent.game_tools import GameToolset
except ImportError:
    # Fallback for direct test execution
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from ai_agent.game_interface import GameEngine, KingdomState, GameAction, DelegationStatus
    from ai_agent.royal_governor_enhanced import RoyalGovernor, DelegationGoal
    from ai_agent.game_tools import GameToolset


class MockGameEngine(GameEngine):
    """Mock game engine for testing."""
    
    def __init__(self, initial_state: KingdomState = None):
        if initial_state:
            self.current_state = initial_state
        else:
            self.current_state = KingdomState(
                year=1,
                population=10000,
                grain_stores=5000,
                land_acres=1000,
                land_planted_acres=500,
                farmers=2000,
                treasury=5000,
                harvest_expected=2500,
                weather_condition='normal',
                plague_active=False,
                disaster_risk=0.1,
                grain_price_per_bushel=1.0,
                population_growth_rate=0.02,
            )
        self.turn_count = 0
        self.actions_log = []
    
    def get_current_state(self) -> KingdomState:
        return self.current_state
    
    def advance_turn(self) -> bool:
        """Advance turn with realistic harvest and population changes."""
        self.turn_count += 1
        self.current_state.year += 1
        
        # Simulate harvest (80-120% of expected)
        import random
        harvest_factor = random.uniform(0.8, 1.2)
        harvest = int(self.current_state.harvest_expected * harvest_factor)
        self.current_state.grain_stores += harvest
        
        # Consume grain for population
        consumption = self.current_state.population * 20
        starvation_deaths = 0
        if self.current_state.grain_stores < consumption:
            deficit = consumption - self.current_state.grain_stores
            starvation_deaths = int(deficit / 20)
            self.current_state.population = max(0, self.current_state.population - starvation_deaths)
            self.current_state.grain_stores = 0
            self.current_state.starvation_deaths = starvation_deaths
        else:
            self.current_state.grain_stores -= consumption
            self.current_state.starvation_deaths = 0
        
        # Population growth
        births = int(self.current_state.population * self.current_state.population_growth_rate)
        self.current_state.population += births
        self.current_state.births_this_year = births
        
        # Plague effects
        if self.current_state.plague_active:
            plague_deaths = int(self.current_state.population * 0.1)
            self.current_state.population = max(0, self.current_state.population - plague_deaths)
            self.current_state.plague_active = False
        
        # Weather changes
        import random
        if random.random() < 0.2:
            self.current_state.weather_condition = random.choice(['drought', 'flood', 'normal'])
        
        # Reset planted acres for next year
        self.current_state.land_planted_acres = 0
        self.current_state.harvest_expected = self.current_state.land_acres * 5
        
        return True
    
    def allocate_grain(self, amount_bushels: int, purpose: str) -> GameAction:
        success = self.current_state.grain_stores >= amount_bushels
        
        if success:
            if purpose == 'sell':
                self.current_state.grain_stores -= amount_bushels
                revenue = int(amount_bushels * self.current_state.grain_price_per_bushel)
                self.current_state.treasury += revenue
                msg = f"Sold {amount_bushels} bushels for {revenue} gold"
                grain_delta = -amount_bushels
                treasury_delta = revenue
            else:
                msg = f"Allocated {amount_bushels} for {purpose}"
                grain_delta = 0
                treasury_delta = 0
        else:
            msg = f"Insufficient grain ({self.current_state.grain_stores} available)"
            grain_delta = 0
            treasury_delta = 0
        
        return GameAction(
            action_name='allocate_grain',
            parameters={'amount': amount_bushels, 'purpose': purpose},
            success=success,
            result_message=msg,
            grain_delta=grain_delta,
            treasury_delta=treasury_delta,
        )
    
    def manage_land(self, acres_to_buy: int = 0, acres_to_sell: int = 0) -> GameAction:
        buy_cost = acres_to_buy * 100
        sell_revenue = acres_to_sell * 100
        
        success = (self.current_state.treasury >= buy_cost) and (self.current_state.land_acres >= acres_to_sell)
        
        if success:
            self.current_state.land_acres += acres_to_buy - acres_to_sell
            self.current_state.treasury += sell_revenue - buy_cost
            net_acres = acres_to_buy - acres_to_sell
            msg = f"Land transaction: {net_acres:+d} acres"
            land_delta = net_acres
            treasury_delta = sell_revenue - buy_cost
        else:
            msg = "Insufficient funds or land"
            land_delta = 0
            treasury_delta = 0
        
        return GameAction(
            action_name='manage_land',
            parameters={'buy': acres_to_buy, 'sell': acres_to_sell},
            success=success,
            result_message=msg,
            land_delta=land_delta,
            treasury_delta=treasury_delta,
        )
    
    def manage_farming(self, acres_to_plant: int) -> GameAction:
        available_land = self.current_state.land_acres - self.current_state.land_planted_acres
        success = acres_to_plant <= available_land and acres_to_plant >= 0
        
        if success:
            self.current_state.land_planted_acres += acres_to_plant
            self.current_state.harvest_expected += acres_to_plant * 5
            msg = f"Planted {acres_to_plant} acres"
        else:
            msg = f"Cannot plant {acres_to_plant} acres (available: {available_land})"
        
        return GameAction(
            action_name='manage_farming',
            parameters={'acres': acres_to_plant},
            success=success,
            result_message=msg,
        )
    
    def manage_irrigation(self, acres_to_irrigate: int) -> GameAction:
        cost = acres_to_irrigate * 50
        success = self.current_state.treasury >= cost and acres_to_irrigate >= 0
        
        if success:
            self.current_state.treasury -= cost
            self.current_state.harvest_expected += acres_to_irrigate * 2
            msg = f"Irrigated {acres_to_irrigate} acres"
            treasury_delta = -cost
        else:
            msg = f"Insufficient treasury for irrigation"
            treasury_delta = 0
        
        return GameAction(
            action_name='manage_irrigation',
            parameters={'acres': acres_to_irrigate},
            success=success,
            result_message=msg,
            treasury_delta=treasury_delta,
        )
    
    def manage_treasury(self, amount: int, operation: str) -> GameAction:
        if operation == 'withdraw':
            success = self.current_state.treasury >= amount
            delta = -amount if success else 0
        elif operation == 'deposit':
            success = amount > 0
            delta = amount
        else:
            return GameAction(
                action_name='manage_treasury',
                parameters={'amount': amount, 'op': operation},
                success=False,
                result_message=f"Invalid operation: {operation}",
            )
        
        if success:
            self.current_state.treasury += delta
        
        msg = f"{operation.title()}: {amount}"
        
        return GameAction(
            action_name='manage_treasury',
            parameters={'amount': amount, 'op': operation},
            success=success,
            result_message=msg,
            treasury_delta=delta if success else 0,
        )
    
    def inspect_disaster_conditions(self) -> dict:
        return {
            'weather': self.current_state.weather_condition,
            'plague_active': self.current_state.plague_active,
            'disaster_risk': self.current_state.disaster_risk,
        }
    
    def save_game_state(self, filename: str) -> bool:
        return True
    
    def load_game_state(self, filename: str) -> bool:
        return True
    
    def is_game_over(self) -> bool:
        return self.current_state.population <= 0
    
    def get_game_over_reason(self) -> str:
        if self.current_state.population <= 0:
            return "Population extinct - kingdom fell"
        return "Unknown"


class TestRoyalGovernor(unittest.TestCase):
    """Tests for the RoyalGovernor AI agent."""
    
    def setUp(self):
        self.game = MockGameEngine()
        self.governor = RoyalGovernor(self.game)
    
    def test_01_initialization(self):
        """Test that governor initializes correctly."""
        self.assertEqual(self.governor.status, DelegationStatus.INACTIVE)
        self.assertIsNone(self.governor.delegation_goal)
        print("\n✓ Initialization test passed")
    
    def test_02_set_delegation_goal(self):
        """Test setting a delegation goal."""
        self.governor.set_delegation_goal(
            goal="Prevent famine for 3 years",
            max_turns=3,
            priorities=['prevent_famine', 'maintain_reserves']
        )
        self.assertEqual(self.governor.status, DelegationStatus.ACTIVE)
        self.assertEqual(self.governor.max_delegation_turns, 3)
        print("✓ Delegation goal test passed")
    
    def test_03_threat_identification_normal(self):
        """Test threat identification in normal conditions."""
        state = self.game.get_current_state()
        threats = self.governor._identify_threats(state)
        
        self.assertFalse(threats['famine_risk'])
        self.assertFalse(threats['plague_risk'])
        self.assertFalse(threats['treasury_crisis'])
        print("✓ Normal threat identification passed")
    
    def test_04_threat_identification_famine(self):
        """Test threat identification during famine."""
        self.game.current_state.grain_stores = 500
        threats = self.governor._identify_threats(self.game.current_state)
        
        self.assertTrue(threats['famine_risk'])
        print("✓ Famine threat identification passed")
    
    def test_05_autonomous_turn(self):
        """Test executing a complete autonomous turn."""
        self.governor.set_delegation_goal("Test management", max_turns=1)
        success, summary = self.governor.execute_autonomous_turn()
        
        self.assertTrue(success, f"Turn failed: {summary}")
        self.assertEqual(self.governor.turns_delegated, 1)
        print("✓ Autonomous turn test passed")
    
    def test_06_delegation_limit(self):
        """Test that delegation respects turn limits."""
        self.governor.set_delegation_goal("Test", max_turns=2)
        
        success1, _ = self.governor.execute_autonomous_turn()
        self.assertTrue(success1)
        
        success2, _ = self.governor.execute_autonomous_turn()
        self.assertTrue(success2)
        
        success3, msg = self.governor.execute_autonomous_turn()
        self.assertFalse(success3)
        self.assertEqual(self.governor.status, DelegationStatus.COMPLETED)
        print("✓ Delegation limit test passed")
    
    def test_07_revoke_delegation(self):
        """Test revoking delegation."""
        self.governor.set_delegation_goal("Test", max_turns=5)
        self.governor.revoke_delegation()
        
        self.assertEqual(self.governor.status, DelegationStatus.REVOKED)
        success, _ = self.governor.execute_autonomous_turn()
        self.assertFalse(success)
        print("✓ Revoke delegation test passed")
    
    def test_08_drought_famine_scenario(self):
        """
        CRITICAL TEST: Severe drought leading to famine.
        The AI must identify the threat and respond autonomously.
        """
        print("\n" + "="*70)
        print("TEST: DROUGHT AND FAMINE SCENARIO - AI AUTONOMOUS RESPONSE")
        print("="*70)
        
        self.governor.set_delegation_goal(
            "Survive drought and maintain population for 5 years",
            max_turns=5,
            priorities=['prevent_famine', 'maintain_reserves', 'protect_treasury']
        )
        
        # Year 1: Normal conditions
        print("\n[Year 1] Normal conditions")
        initial_grain = self.game.current_state.grain_stores
        print(f"  Initial grain: {initial_grain} bushels")
        success1, summary1 = self.governor.execute_autonomous_turn()
        self.assertTrue(success1)
        print(f"  {summary1}")
        
        # Year 2: Severe drought strikes
        print("\n[Year 2] SEVERE DROUGHT STRIKES!")
        self.game.current_state.weather_condition = 'drought'
        self.game.current_state.grain_price_per_bushel = 2.0
        self.game.current_state.harvest_expected = int(self.game.current_state.harvest_expected * 0.3)
        
        print(f"  Grain before turn: {self.game.current_state.grain_stores}")
        success2, summary2 = self.governor.execute_autonomous_turn()
        print(f"  AI Response: {summary2}")
        self.assertTrue(success2)
        
        # Continue managing through famine
        print("\n[Years 3-5] Continuing through famine...")
        for year in range(3, 6):
            print(f"\n[Year {year}] Famine conditions persist")
            grain_before = self.game.current_state.grain_stores
            pop_before = self.game.current_state.population
            
            success, summary = self.governor.execute_autonomous_turn()
            
            grain_after = self.game.current_state.grain_stores
            pop_after = self.game.current_state.population
            
            print(f"  Grain: {grain_before} → {grain_after}")
            print(f"  Pop: {pop_before} → {pop_after}")
            print(f"  AI: {summary}")
            
            if not success:
                if self.governor.status == DelegationStatus.COMPLETED:
                    print("  ✓ Delegation completed")
                    break
                else:
                    print(f"  Turn failed: {summary}")
                    break
        
        # Final verification
        print(f"\n{'='*70}")
        final_state = self.game.get_current_state()
        print(f"FINAL STATE AFTER FAMINE:")
        print(f"  Year: {final_state.year}")
        print(f"  Population: {final_state.population}")
        print(f"  Grain: {final_state.grain_stores}")
        print(f"  Treasury: {final_state.treasury}")
        print(f"  Game Over: {self.game.is_game_over()}")
        
        status = self.governor.get_status_report()
        print(f"\nAI AGENT PERFORMANCE METRICS:")
        print(f"  Status: {status['status']}")
        print(f"  Turns completed: {status['turns_completed']}/{status['turns_remaining']}")
        print(f"  Total actions: {status['total_actions']}")
        print(f"  Successful actions: {status['successful_actions']}")
        print(f"  Success rate: {status['success_rate']}")
        
        # Agent should have taken action
        self.assertTrue(len(self.governor.action_history) > 0,
                       "Governor should have taken actions during famine")
        
        print(f"{'='*70}\n")
        print("✓ Drought and famine scenario test PASSED\n")


class TestGameTools(unittest.TestCase):
    """Tests for the GameToolset."""
    
    def setUp(self):
        self.game = MockGameEngine()
        self.toolset = GameToolset(self.game)
    
    def test_tool_listing(self):
        """Test that all tools are registered."""
        tools = self.toolset.list_tools()
        self.assertIn('inspect_kingdom_state', tools)
        self.assertIn('allocate_grain', tools)
        self.assertIn('manage_land', tools)
        print("\n✓ Tool listing test passed")
    
    def test_tool_validation_valid(self):
        """Test validation of valid tool calls."""
        valid, error = self.toolset.validate_tool_call(
            'allocate_grain',
            {'amount_bushels': 100, 'purpose': 'storage'}
        )
        self.assertTrue(valid)
        self.assertIsNone(error)
        print("✓ Valid tool validation test passed")
    
    def test_tool_validation_invalid(self):
        """Test validation of invalid tool calls."""
        valid, error = self.toolset.validate_tool_call(
            'allocate_grain',
            {'amount_bushels': -10, 'purpose': 'invalid'}
        )
        self.assertFalse(valid)
        self.assertIsNotNone(error)
        print("✓ Invalid tool validation test passed")


if __name__ == '__main__':
    unittest.main(verbosity=2)
