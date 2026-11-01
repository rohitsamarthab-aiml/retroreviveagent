"""
AI Royal Governor Package

A production-ready autonomous kingdom management agent for Hammurabi-style games.
Implements real decision-making cycles that directly manipulate actual game state.

Core Components:
- GameEngine: Abstract interface for game integration
- RoyalGovernor: Autonomous AI agent with observe→reason→plan→execute→verify cycle
- GameToolset: Tool definitions and validation for AI tool calls

Example Usage:
    >>> from ai_agent import RoyalGovernor, GameEngine
    >>> engine = YourGameEngine(game_instance)
    >>> governor = RoyalGovernor(engine)
    >>> governor.set_delegation_goal("Manage kingdom for 5 years", max_turns=5)
    >>> success, summary = governor.execute_autonomous_turn()
"""

__version__ = "1.0.0"
__author__ = "RetroRevive Team"
__all__ = [
    'GameEngine',
    'KingdomState',
    'GameAction',
    'DelegationStatus',
    'RoyalGovernor',
    'DelegationGoal',
    'GameToolset',
    'ToolDefinition',
]

from ai_agent.game_interface import (
    GameEngine,
    KingdomState,
    GameAction,
    DelegationStatus,
    WeatherCondition,
)
from ai_agent.royal_governor_enhanced import RoyalGovernor, DelegationGoal
from ai_agent.game_tools import GameToolset, ToolDefinition
