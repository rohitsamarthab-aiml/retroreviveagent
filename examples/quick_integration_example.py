"""
Quick Integration Example

This is a minimal example of integrating the AI Royal Governor
with your RetroRevive game.

Copy this pattern into your actual game code and customize
as needed.
"""

from ai_agent import GameEngine, RoyalGovernor, KingdomState, GameAction


class MyRetroReviveEngine(GameEngine):
    """
    Example GameEngine adapter for your RetroRevive game.
    Replace with actual game references.
    """
    
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
            harvest_expected=self.game.harvest_expected,
            weather_condition=self.game.weather,
            plague_active=self.game.plague,
            disaster_risk=self.game.disaster_risk,
            grain_price_per_bushel=self.game.grain_price,
            population_growth_rate=self.game.pop_growth,
        )
    
    def advance_turn(self) -> bool:
        """Progress the game by one turn."""
        return self.game.advance_year()
    
    def allocate_grain(self, amount_bushels: int, purpose: str) -> GameAction:
        """Allocate grain for various purposes."""
        success = self.game.grain >= amount_bushels
        
        if success:
            self.game.grain -= amount_bushels
            if purpose == 'sell':
                revenue = int(amount_bushels * self.game.grain_price)
                self.game.treasury += revenue
        
        return GameAction(
            action_name='allocate_grain',
            parameters={'amount': amount_bushels, 'purpose': purpose},
            success=success,
            result_message=f"Allocated {amount_bushels} for {purpose}",
            grain_delta=-amount_bushels if success else 0,
        )
    
    def manage_land(self, acres_to_buy: int = 0, acres_to_sell: int = 0) -> GameAction:
        """Buy or sell land."""
        cost = acres_to_buy * 100
        revenue = acres_to_sell * 100
        success = (self.game.treasury >= cost) and (self.game.land >= acres_to_sell)
        
        if success:
            self.game.land += acres_to_buy - acres_to_sell
            self.game.treasury -= cost
            self.game.treasury += revenue
        
        return GameAction(
            action_name='manage_land',
            parameters={'buy': acres_to_buy, 'sell': acres_to_sell},
            success=success,
            result_message=f"Land transaction: {acres_to_buy - acres_to_sell:+d} acres",
            land_delta=acres_to_buy - acres_to_sell if success else 0,
            treasury_delta=(revenue - cost) if success else 0,
        )
    
    def manage_farming(self, acres_to_plant: int) -> GameAction:
        """Plant grain on land."""
        available = self.game.land - self.game.land_planted
        success = acres_to_plant <= available and acres_to_plant >= 0
        
        if success:
            self.game.land_planted += acres_to_plant
            self.game.harvest_expected += acres_to_plant * 5
        
        return GameAction(
            action_name='manage_farming',
            parameters={'acres': acres_to_plant},
            success=success,
            result_message=f"Planted {acres_to_plant} acres",
        )
    
    def manage_irrigation(self, acres_to_irrigate: int) -> GameAction:
        """Invest in irrigation."""
        cost = acres_to_irrigate * 50
        success = self.game.treasury >= cost and acres_to_irrigate >= 0
        
        if success:
            self.game.treasury -= cost
            self.game.harvest_expected += acres_to_irrigate * 2
        
        return GameAction(
            action_name='manage_irrigation',
            parameters={'acres': acres_to_irrigate},
            success=success,
            result_message=f"Irrigated {acres_to_irrigate} acres",
            treasury_delta=-cost if success else 0,
        )
    
    def manage_treasury(self, amount: int, operation: str) -> GameAction:
        """Manage treasury."""
        if operation == 'withdraw':
            success = self.game.treasury >= amount
            delta = -amount if success else 0
        elif operation == 'deposit':
            success = amount > 0
            delta = amount
        else:
            return GameAction(
                action_name='manage_treasury',
                parameters={'amount': amount, 'op': operation},
                success=False,
                result_message="Invalid operation",
            )
        
        if success:
            self.game.treasury += delta
        
        return GameAction(
            action_name='manage_treasury',
            parameters={'amount': amount, 'op': operation},
            success=success,
            result_message=f"{operation.title()}: {amount}",
            treasury_delta=delta if success else 0,
        )
    
    def inspect_disaster_conditions(self) -> dict:
        """Check disaster risks."""
        return {
            'weather': self.game.weather,
            'plague_active': self.game.plague,
            'disaster_risk': self.game.disaster_risk,
        }
    
    def save_game_state(self, filename: str) -> bool:
        """Save game state."""
        return self.game.save(filename)
    
    def load_game_state(self, filename: str) -> bool:
        """Load game state."""
        return self.game.load(filename)
    
    def is_game_over(self) -> bool:
        """Check if game has ended."""
        return self.game.population <= 0 or self.game.grain < 0
    
    def get_game_over_reason(self) -> str:
        """Get reason for game over."""
        if self.game.population <= 0:
            return "Population extinct"
        return "Out of grain - starvation"


# ============================================================================
# USAGE EXAMPLE
# ============================================================================

def example_usage(game):
    """Example of using the AI Royal Governor."""
    
    # 1. Create engine adapter
    engine = MyRetroReviveEngine(game)
    
    # 2. Initialize AI governor
    governor = RoyalGovernor(engine)
    
    # 3. Set delegation goal
    governor.set_delegation_goal(
        goal="Manage kingdom for 5 years, prevent famine",
        max_turns=5,
        priorities=['prevent_famine', 'maintain_reserves', 'protect_treasury']
    )
    
    # 4. Execute autonomous turns
    print("\n" + "="*60)
    print("DELEGATING TO AI ROYAL GOVERNOR")
    print("="*60)
    
    while governor.status.value == 'active':
        success, summary = governor.execute_autonomous_turn()
        
        if success:
            print(f"\n✓ {summary}")
        else:
            print(f"\n✗ Turn failed: {summary}")
            break
    
    # 5. Display results
    print("\n" + "="*60)
    print("DELEGATION COMPLETE")
    print("="*60)
    
    status = governor.get_status_report()
    print(f"Status: {status['status']}")
    print(f"Turns: {status['turns_completed']}/{status['turns_remaining']}")
    print(f"Actions: {status['successful_actions']}/{status['total_actions']} successful")
    print(f"Success rate: {status['success_rate']}")
    
    # 6. Display action history
    print(f"\nAction History ({len(governor.get_action_history())} total):")
    for action in governor.get_action_history()[-5:]:  # Show last 5
        print(f"  - {action['action_name']}: {action['result_message']}")
    
    # 7. Display reasoning
    print(f"\nLatest Reasoning:")
    if governor.get_reasoning_log():
        latest = governor.get_reasoning_log()[-1]
        print(f"  Year {latest['year']}: {latest['analysis']}")
        print(f"  Threats: {', '.join(latest['active_threats']) or 'None'}")


# ============================================================================
# PLAYER CONTROL EXAMPLE
# ============================================================================

def example_player_control(governor):
    """Example of player controlling the AI."""
    
    # Pause AI
    print("\nPlayer pauses delegation...")
    governor.pause_delegation()
    print(f"Status: {governor.status.value}")
    
    # Resume AI
    print("\nPlayer resumes delegation...")
    governor.resume_delegation()
    print(f"Status: {governor.status.value}")
    
    # Execute more turns
    for _ in range(2):
        success, summary = governor.execute_autonomous_turn()
        if success:
            print(f"✓ {summary}")
    
    # Revoke AI control
    print("\nPlayer revokes delegation...")
    governor.revoke_delegation()
    print(f"Status: {governor.status.value}")
    
    # AI will not execute anymore
    success, msg = governor.execute_autonomous_turn()
    print(f"✗ Cannot execute: {msg}")


if __name__ == '__main__':
    # This would integrate with your actual game
    print("See integration guide in docs/INTEGRATION.md")
    print("See working tests in tests/test_ai_royal_governor.py")
