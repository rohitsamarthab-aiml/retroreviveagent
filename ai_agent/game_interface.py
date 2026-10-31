"""
game_interface.py - Abstract Game Engine Interface

Defines the interface that your RetroRevive game engine must implement
for the AI Royal Governor to control it.

Classes:
    - KingdomState: Dataclass representing kingdom state
    - GameAction: Dataclass representing an action result
    - GameEngine: Abstract base class for game engine integration
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from enum import Enum


class WeatherCondition(Enum):
    """Game weather conditions."""
    NORMAL = "normal"
    DROUGHT = "drought"
    FLOOD = "flood"
    HARSH_WINTER = "harsh_winter"


class DelegationStatus(Enum):
    """Status of AI delegation."""
    INACTIVE = "inactive"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    REVOKED = "revoked"
    ERROR = "error"


@dataclass
class KingdomState:
    """Snapshot of the current kingdom state."""
    year: int
    population: int
    grain_stores: int  # in bushels
    land_acres: int
    land_planted_acres: int
    farmers: int
    treasury: int  # in gold/currency
    harvest_expected: int  # Expected harvest next turn
    weather_condition: str  # 'normal', 'drought', 'flood', etc.
    plague_active: bool
    disaster_risk: float  # 0.0 to 1.0
    grain_price_per_bushel: float
    population_growth_rate: float
    births_this_year: int = 0
    deaths_this_year: int = 0
    starvation_deaths: int = 0
    tax_collected: int = 0


@dataclass
class GameAction:
    """Represents a single action taken by the AI agent."""
    action_name: str
    parameters: Dict[str, Any]
    success: bool
    result_message: str
    state_before: Optional[KingdomState] = None
    state_after: Optional[KingdomState] = None
    grain_delta: int = 0
    land_delta: int = 0
    population_delta: int = 0
    treasury_delta: int = 0
    timestamp: str = ""


class GameEngine(ABC):
    """
    Abstract base class for game engine integration.
    
    Your RetroRevive game must implement this interface
    to integrate with the AI Royal Governor.
    """

    @abstractmethod
    def get_current_state(self) -> KingdomState:
        """Returns the current complete kingdom state."""
        pass

    @abstractmethod
    def advance_turn(self) -> bool:
        """
        Advances the game by one turn/year.
        Returns success status.
        """
        pass

    @abstractmethod
    def allocate_grain(self, amount_bushels: int, purpose: str) -> GameAction:
        """
        Allocate grain for consumption, storage, seed, or sale.
        
        Args:
            amount_bushels: Amount of grain in bushels
            purpose: 'consumption', 'storage', 'seed', or 'sell'
        
        Returns:
            GameAction with success status and result
        """
        pass

    @abstractmethod
    def manage_land(self, acres_to_buy: int = 0, acres_to_sell: int = 0) -> GameAction:
        """
        Buy or sell land.
        
        Args:
            acres_to_buy: Number of acres to purchase
            acres_to_sell: Number of acres to sell
        
        Returns:
            GameAction with success status and result
        """
        pass

    @abstractmethod
    def manage_farming(self, acres_to_plant: int) -> GameAction:
        """
        Plant grain on specified acres.
        
        Args:
            acres_to_plant: Number of acres to plant with grain
        
        Returns:
            GameAction with success status and result
        """
        pass

    @abstractmethod
    def manage_irrigation(self, acres_to_irrigate: int) -> GameAction:
        """
        Invest in irrigation systems.
        
        Args:
            acres_to_irrigate: Acres to improve with irrigation
        
        Returns:
            GameAction with success status and result
        """
        pass

    @abstractmethod
    def manage_treasury(self, amount: int, operation: str) -> GameAction:
        """
        Manage treasury: deposit or withdraw currency.
        
        Args:
            amount: Amount of currency
            operation: 'deposit' or 'withdraw'
        
        Returns:
            GameAction with success status and result
        """
        pass

    @abstractmethod
    def inspect_disaster_conditions(self) -> Dict[str, Any]:
        """
        Check current disaster risk and environmental conditions.
        
        Returns:
            Dict with weather, plague status, risk levels, etc.
        """
        pass

    @abstractmethod
    def save_game_state(self, filename: str) -> bool:
        """Save current game state to file."""
        pass

    @abstractmethod
    def load_game_state(self, filename: str) -> bool:
        """Load game state from file."""
        pass

    @abstractmethod
    def is_game_over(self) -> bool:
        """Returns True if the game has ended."""
        pass

    @abstractmethod
    def get_game_over_reason(self) -> str:
        """Returns the reason the game ended."""
        pass
