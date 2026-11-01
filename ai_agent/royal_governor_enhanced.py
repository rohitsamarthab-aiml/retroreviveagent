"""
royal_governor_enhanced.py - Enhanced AI Royal Governor Agent

Implements autonomous kingdom management with observe→reason→plan→execute→verify cycle.
This is the core AI agent for delegated kingdom management.
"""

import logging
import json
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import asdict, dataclass, field
from enum import Enum

from .game_interface import GameEngine, KingdomState, GameAction, DelegationStatus


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(name)s] - %(levelname)s - %(message)s'
)
logger = logging.getLogger('RoyalGovernor')


@dataclass
class DelegationGoal:
    """Represents a delegation goal."""
    goal_text: str
    max_turns: int
    priorities: List[str] = field(default_factory=lambda: ['prevent_famine', 'maintain_reserves'])
    created_at: str = ""
    status: DelegationStatus = DelegationStatus.INACTIVE
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()


class RoyalGovernor:
    """
    Autonomous AI agent for kingdom management.
    
    Implements observe→identify threats→reason→plan→validate→execute→verify→replan cycle.
    
    All actions operate on real game state through the GameEngine interface.
    No simulations or separate copies of game state are maintained.
    """

    def __init__(self, game_engine: GameEngine, config: Optional[Dict] = None):
        """
        Initialize the Royal Governor.
        
        Args:
            game_engine: Reference to the actual game engine
            config: Optional configuration dict with thresholds
        """
        self.game = game_engine
        self.config = config or {}
        
        # Delegation tracking
        self.delegation_goal: Optional[DelegationGoal] = None
        self.turns_delegated = 0
        self.max_delegation_turns = 0
        self.status = DelegationStatus.INACTIVE
        
        # Action history and reasoning
        self.action_history: List[GameAction] = []
        self.reasoning_log: List[Dict[str, Any]] = []
        self.state_snapshots: List[KingdomState] = []
        self.turn_summaries: List[str] = []
        
        # Thresholds (tunable)
        self.min_grain_reserves = self.config.get('min_grain_reserves', 2000)
        self.min_farmers_percentage = self.config.get('min_farmers_percentage', 0.20)
        self.max_land_investment = self.config.get('max_land_investment', 0.3)
        self.famine_threshold = self.config.get('famine_threshold', 1000)
        self.critical_population_threshold = self.config.get('critical_population', 100)
        
        logger.info("✓ Royal Governor initialized with game engine")

    def set_delegation_goal(self, goal: str, max_turns: int, priorities: List[str] = None):
        """
        Set a delegation goal and activate the agent.
        
        Args:
            goal: Description of goal
            max_turns: Maximum number of turns to delegate
            priorities: List of priorities in order
        """
        self.delegation_goal = DelegationGoal(
            goal_text=goal,
            max_turns=max_turns,
            priorities=priorities or ['prevent_famine', 'maintain_reserves'],
            status=DelegationStatus.ACTIVE
        )
        self.max_delegation_turns = max_turns
        self.turns_delegated = 0
        self.status = DelegationStatus.ACTIVE
        self.action_history.clear()
        self.reasoning_log.clear()
        self.state_snapshots.clear()
        self.turn_summaries.clear()
        
        logger.info(f"🎯 Delegation goal set: '{goal}' ({max_turns} turns max)")
        logger.info(f"   Priorities: {', '.join(priorities or ['prevent_famine', 'maintain_reserves'])}")

    def revoke_delegation(self):
        """Stop AI control immediately."""
        if self.delegation_goal:
            self.delegation_goal.status = DelegationStatus.REVOKED
        self.status = DelegationStatus.REVOKED
        logger.warning("⛔ Delegation revoked by player")

    def pause_delegation(self):
        """Pause AI control (can resume later)."""
        if self.delegation_goal:
            self.delegation_goal.status = DelegationStatus.PAUSED
        self.status = DelegationStatus.PAUSED
        logger.info("⏸  Delegation paused")

    def resume_delegation(self):
        """Resume paused delegation."""
        if self.delegation_goal:
            self.delegation_goal.status = DelegationStatus.ACTIVE
        self.status = DelegationStatus.ACTIVE
        logger.info("▶️  Delegation resumed")

    def execute_autonomous_turn(self) -> Tuple[bool, str]:
        """
        Execute one complete autonomous turn.
        
        Implements: observe → threats → reason → plan → validate → execute → verify
        
        Returns:
            (success: bool, summary: str)
        """
        if self.status != DelegationStatus.ACTIVE:
            return False, f"Delegation is {self.status.value}, cannot execute"
        
        if self.turns_delegated >= self.max_delegation_turns:
            self.status = DelegationStatus.COMPLETED
            return False, f"Delegation limit reached ({self.max_delegation_turns} turns)"
        
        try:
            logger.info(f"\n{'='*60}")
            logger.info(f"AUTONOMOUS TURN {self.turns_delegated + 1}")
            logger.info(f"{'='*60}")
            
            # STEP 1: OBSERVE
            state_before = self._observe_kingdom()
            self.state_snapshots.append(state_before)
            
            # STEP 2: IDENTIFY THREATS
            threats = self._identify_threats(state_before)
            
            # STEP 3: REASON
            reasoning = self._reason_about_situation(state_before, threats)
            self.reasoning_log.append(reasoning)
            
            # STEP 4: PLAN
            plan = self._generate_plan(state_before, threats, reasoning)
            
            # STEP 5-7: EXECUTE & VERIFY
            actions_taken = self._execute_plan(plan, state_before)
            self.action_history.extend(actions_taken)
            
            # STEP 8: VERIFY
            verification = self._verify_execution(state_before, actions_taken)
            
            # Check game over before advancing
            if self.game.is_game_over():
                self.status = DelegationStatus.ERROR
                reason = self.game.get_game_over_reason()
                logger.error(f"Game over: {reason}")
                return False, f"Game ended: {reason}"
            
            # STEP 9: ADVANCE TURN
            turn_advanced = self.game.advance_turn()
            if not turn_advanced:
                logger.warning("⚠️  Failed to advance turn")
                return False, "Failed to advance game turn"
            
            self.turns_delegated += 1
            
            # Build and log summary
            summary = self._build_turn_summary(state_before, actions_taken, verification)
            self.turn_summaries.append(summary)
            logger.info(f"✓ Turn completed: {summary}")
            
            return True, summary
            
        except Exception as e:
            logger.error(f"❌ Error during autonomous turn: {e}", exc_info=True)
            self.status = DelegationStatus.ERROR
            return False, f"Error: {str(e)}"

    def _observe_kingdom(self) -> KingdomState:
        """STEP 1: Observe current kingdom state."""
        state = self.game.get_current_state()
        logger.debug(f"Observation: Year={state.year}, Pop={state.population}, "
                    f"Grain={state.grain_stores}, Land={state.land_acres}, "
                    f"Treasury={state.treasury}")
        return state

    def _identify_threats(self, state: KingdomState) -> Dict[str, Any]:
        """STEP 2: Identify threats and resource shortages."""
        threats = {
            'famine_risk': False,
            'plague_risk': False,
            'treasury_crisis': False,
            'overpopulation': False,
            'critical_population': False,
            'grain_shortage': False,
            'insufficient_farmers': False,
            'disaster_imminent': False,
        }
        
        # Check grain levels
        if state.grain_stores < self.famine_threshold:
            threats['famine_risk'] = True
            logger.warning(f"⚠️  THREAT: Famine risk - grain at {state.grain_stores} (threshold: {self.famine_threshold})")
        
        if state.grain_stores < self.min_grain_reserves:
            threats['grain_shortage'] = True
        
        # Check population vs farmers
        if state.population > 0:
            farmer_ratio = state.farmers / state.population
            if farmer_ratio < self.min_farmers_percentage:
                threats['insufficient_farmers'] = True
                logger.warning(f"⚠️  THREAT: Insufficient farmers - {farmer_ratio:.1%} (min: {self.min_farmers_percentage:.1%})")
        
        # Check plague
        if state.plague_active:
            threats['plague_risk'] = True
            logger.warning("⚠️  THREAT: Plague is active")
        
        # Check treasury
        if state.treasury < 1000:
            threats['treasury_crisis'] = True
            logger.warning(f"⚠️  THREAT: Treasury crisis - only {state.treasury} gold")
        
        # Check critical population
        if state.population <= self.critical_population_threshold:
            threats['critical_population'] = True
            logger.error(f"❌ CRITICAL: Population near extinction - {state.population}")
        
        # Check population strain
        if state.population > 0:
            available_grain_per_capita = state.grain_stores / state.population
            if available_grain_per_capita < 20:
                threats['overpopulation'] = True
                logger.warning(f"⚠️  THREAT: Overpopulation - {available_grain_per_capita:.1f} bushels/person (need 20)")
        
        # Check disaster risk
        disasters = self.game.inspect_disaster_conditions()
        if disasters.get('disaster_risk', 0) > 0.5:
            threats['disaster_imminent'] = True
            logger.warning(f"⚠️  THREAT: Disaster risk high - {disasters.get('disaster_risk', 0):.1%}")
        
        return threats

    def _reason_about_situation(self, state: KingdomState, threats: Dict[str, Any]) -> Dict[str, Any]:
        """STEP 3: Reason about the situation."""
        reasoning = {
            'timestamp': datetime.now().isoformat(),
            'year': state.year,
            'state_summary': {
                'population': state.population,
                'grain': state.grain_stores,
                'land': state.land_acres,
                'farmers': state.farmers,
                'treasury': state.treasury,
                'weather': state.weather_condition,
                'plague': state.plague_active,
            },
            'active_threats': [k for k, v in threats.items() if v],
            'goal': self.delegation_goal.goal_text if self.delegation_goal else None,
            'priorities': self.delegation_goal.priorities if self.delegation_goal else [],
            'analysis': "",
        }
        
        # Build analysis
        active_threats = reasoning['active_threats']
        if active_threats:
            reasoning['analysis'] = f"⚠️  Active threats: {', '.join(active_threats)}"
        else:
            reasoning['analysis'] = "✓ Kingdom is stable; opportunity for growth"
        
        logger.info(f"Analysis: {reasoning['analysis']}")
        return reasoning

    def _generate_plan(self, state: KingdomState, threats: Dict[str, Any], 
                       reasoning: Dict[str, Any]) -> List[Dict[str, Any]]:
        """STEP 4: Generate action plan respecting game rules."""
        plan = []
        
        # PRIORITY 1: Prevent starvation/famine
        if threats['famine_risk'] and state.grain_stores < self.famine_threshold:
            reserve_target = self.min_grain_reserves
            if state.grain_stores < reserve_target:
                plan.append({
                    'action': 'allocate_grain',
                    'params': {'amount_bushels': min(1000, state.grain_stores // 2),
                              'purpose': 'storage'},
                    'reason': 'CRITICAL: Store grain to prevent famine',
                    'priority': 1
                })
        
        # PRIORITY 2: Generate income if in crisis
        if threats['treasury_crisis'] and state.grain_stores > self.min_grain_reserves + 2000:
            excess = state.grain_stores - (self.min_grain_reserves + 2000)
            plan.append({
                'action': 'allocate_grain',
                'params': {'amount_bushels': min(excess, 1000), 'purpose': 'sell'},
                'reason': 'Sell excess grain to restore treasury',
                'priority': 2
            })
        
        # PRIORITY 3: Increase farming if grain is safe
        if not threats['famine_risk'] and not threats['insufficient_farmers']:
            available_land = state.land_acres - state.land_planted_acres
            if available_land > 50 and state.farmers > 100:
                acres_to_plant = min(available_land * 0.7, available_land)
                plan.append({
                    'action': 'manage_farming',
                    'params': {'acres_to_plant': int(acres_to_plant)},
                    'reason': 'Plant available land to increase harvest',
                    'priority': 3
                })
        
        # PRIORITY 4: Invest in land if treasury is strong
        if state.treasury > 5000 and not threats['famine_risk'] and not threats['treasury_crisis']:
            land_budget = int(state.treasury * self.max_land_investment)
            acres_can_buy = land_budget // 100
            if acres_can_buy > 0:
                plan.append({
                    'action': 'manage_land',
                    'params': {'acres_to_buy': min(acres_can_buy, 500)},
                    'reason': 'Expand land holdings for long-term growth',
                    'priority': 4
                })
        
        # PRIORITY 5: Irrigation investment
        if not threats['famine_risk'] and not threats['disaster_imminent']:
            if state.treasury > 2000 and state.land_planted_acres > 100:
                plan.append({
                    'action': 'manage_irrigation',
                    'params': {'acres_to_irrigate': min(state.land_planted_acres // 2, 200)},
                    'reason': 'Invest in irrigation to improve harvest resilience',
                    'priority': 5
                })
        
        # Sort by priority
        plan.sort(key=lambda x: x.get('priority', 99))
        
        logger.info(f"Plan generated: {len(plan)} actions")
        for i, action in enumerate(plan, 1):
            logger.info(f"  {i}. {action['action']:20s} - {action['reason']}")
        
        return plan

    def _execute_plan(self, plan: List[Dict[str, Any]], initial_state: KingdomState) -> List[GameAction]:
        """STEP 5-6: Execute the plan through real game tools."""
        actions_taken = []
        
        for plan_item in plan:
            action_name = plan_item['action']
            params = plan_item['params']
            reason = plan_item['reason']
            
            logger.info(f"\nExecuting: {action_name}")
            logger.info(f"  Reason: {reason}")
            logger.info(f"  Params: {params}")
            
            try:
                # Call real game engine
                if action_name == 'allocate_grain':
                    action = self.game.allocate_grain(
                        amount_bushels=params['amount_bushels'],
                        purpose=params['purpose']
                    )
                elif action_name == 'manage_farming':
                    action = self.game.manage_farming(
                        acres_to_plant=params['acres_to_plant']
                    )
                elif action_name == 'manage_land':
                    action = self.game.manage_land(
                        acres_to_buy=params.get('acres_to_buy', 0),
                        acres_to_sell=params.get('acres_to_sell', 0)
                    )
                elif action_name == 'manage_irrigation':
                    action = self.game.manage_irrigation(
                        acres_to_irrigate=params.get('acres_to_irrigate', 0)
                    )
                elif action_name == 'manage_treasury':
                    action = self.game.manage_treasury(
                        amount=params['amount'],
                        operation=params['operation']
                    )
                else:
                    logger.error(f"Unknown action: {action_name}")
                    continue
                
                if action.success:
                    logger.info(f"  ✓ SUCCESS: {action.result_message}")
                else:
                    logger.warning(f"  ✗ FAILED: {action.result_message}")
                
                actions_taken.append(action)
                
            except Exception as e:
                logger.error(f"  ❌ Exception: {e}")
        
        return actions_taken

    def _verify_execution(self, state_before: KingdomState, 
                         actions: List[GameAction]) -> Dict[str, Any]:
        """STEP 8: Verify outcomes against actual state."""
        state_after = self.game.get_current_state()
        
        verification = {
            'timestamp': datetime.now().isoformat(),
            'deltas': {
                'population': state_after.population - state_before.population,
                'grain': state_after.grain_stores - state_before.grain_stores,
                'land': state_after.land_acres - state_before.land_acres,
                'treasury': state_after.treasury - state_before.treasury,
                'farmers': state_after.farmers - state_before.farmers,
            },
            'actions_executed': len(actions),
            'actions_successful': sum(1 for a in actions if a.success),
            'all_successful': all(a.success for a in actions),
        }
        
        success_rate = (verification['actions_successful'] / max(verification['actions_executed'], 1)) * 100
        logger.info(f"\nVerification: {verification['actions_successful']}/{verification['actions_executed']} actions successful ({success_rate:.0f}%)")
        logger.info(f"Resource deltas - Grain: {verification['deltas']['grain']:+d}, "
                   f"Land: {verification['deltas']['land']:+d}, "
                   f"Treasury: {verification['deltas']['treasury']:+d}")
        
        return verification

    def _build_turn_summary(self, state: KingdomState, actions: List[GameAction], 
                           verification: Dict[str, Any]) -> str:
        """Build human-readable turn summary."""
        lines = [
            f"Year {state.year} | Turn {self.turns_delegated}/{self.max_delegation_turns}",
            f"Population: {state.population} | Grain: {state.grain_stores} | Land: {state.land_acres} | Treasury: {state.treasury}",
            f"Actions: {verification['actions_successful']}/{verification['actions_executed']}",
        ]
        
        if verification['deltas']['grain'] != 0:
            lines.append(f"Grain: {verification['deltas']['grain']:+d}")
        if verification['deltas']['treasury'] != 0:
            lines.append(f"Treasury: {verification['deltas']['treasury']:+d}")
        
        return " | ".join(lines)

    def get_action_history(self) -> List[Dict[str, Any]]:
        """Get action history for UI."""
        return [asdict(a) for a in self.action_history]

    def get_reasoning_log(self) -> List[Dict[str, Any]]:
        """Get reasoning log for UI."""
        return self.reasoning_log

    def get_turn_summaries(self) -> List[str]:
        """Get turn-by-turn summaries."""
        return self.turn_summaries

    def get_status_report(self) -> Dict[str, Any]:
        """Get current delegation status and statistics."""
        return {
            'status': self.status.value,
            'delegation_goal': self.delegation_goal.goal_text if self.delegation_goal else None,
            'priorities': self.delegation_goal.priorities if self.delegation_goal else [],
            'turns_completed': self.turns_delegated,
            'turns_remaining': max(0, self.max_delegation_turns - self.turns_delegated),
            'total_actions': len(self.action_history),
            'successful_actions': sum(1 for a in self.action_history if a.success),
            'success_rate': f"{(sum(1 for a in self.action_history if a.success) / max(len(self.action_history), 1) * 100):.1f}%",
        }

    def export_session(self) -> Dict[str, Any]:
        """Export complete session data for saving."""
        return {
            'goal': self.delegation_goal.goal_text if self.delegation_goal else None,
            'status': self.status.value,
            'turns_delegated': self.turns_delegated,
            'turn_summaries': self.turn_summaries,
            'action_count': len(self.action_history),
            'reasoning_log': self.reasoning_log,
        }
