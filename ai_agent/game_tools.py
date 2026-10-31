"""
game_tools.py - Tool Definitions and Tool-Calling Framework

Manages available tools that the AI can call and validates all tool calls.
Each tool wraps a real game engine function and includes validation.
"""

from typing import Dict, Any, Callable, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger('GameTools')


@dataclass
class ToolDefinition:
    """Definition of an available tool."""
    name: str
    description: str
    parameters: Dict[str, str]
    required_params: list
    validation_fn: Optional[Callable] = None


class GameToolset:
    """
    Manages tools that the AI agent can call.
    Each tool wraps a real game engine function with validation.
    """
    
    def __init__(self, game_engine):
        self.game = game_engine
        self.tools = self._define_tools()
        self.call_history: list = []
    
    def _define_tools(self) -> Dict[str, ToolDefinition]:
        """Define all available tools with validation."""
        return {
            'inspect_kingdom_state': ToolDefinition(
                name='inspect_kingdom_state',
                description='Read the current complete kingdom state',
                parameters={},
                required_params=[],
                validation_fn=lambda p: True
            ),
            'allocate_grain': ToolDefinition(
                name='allocate_grain',
                description='Allocate grain for consumption, storage, seed, or sale',
                parameters={
                    'amount_bushels': 'int (> 0)',
                    'purpose': 'str (consumption|storage|seed|sell)'
                },
                required_params=['amount_bushels', 'purpose'],
                validation_fn=self._validate_allocate_grain
            ),
            'manage_land': ToolDefinition(
                name='manage_land',
                description='Buy or sell land (max 500 acres/turn)',
                parameters={
                    'acres_to_buy': 'int (≥ 0)',
                    'acres_to_sell': 'int (≥ 0)'
                },
                required_params=[],
                validation_fn=self._validate_manage_land
            ),
            'manage_farming': ToolDefinition(
                name='manage_farming',
                description='Plant grain on available land',
                parameters={'acres_to_plant': 'int (≥ 0)'},
                required_params=['acres_to_plant'],
                validation_fn=self._validate_manage_farming
            ),
            'manage_irrigation': ToolDefinition(
                name='manage_irrigation',
                description='Invest in irrigation systems for improved harvests',
                parameters={'acres_to_irrigate': 'int (≥ 0)'},
                required_params=['acres_to_irrigate'],
                validation_fn=self._validate_manage_irrigation
            ),
            'manage_treasury': ToolDefinition(
                name='manage_treasury',
                description='Manage treasury deposits and withdrawals',
                parameters={
                    'amount': 'int (> 0)',
                    'operation': 'str (deposit|withdraw)'
                },
                required_params=['amount', 'operation'],
                validation_fn=self._validate_manage_treasury
            ),
            'advance_kingdom_turn': ToolDefinition(
                name='advance_kingdom_turn',
                description='Advance game by one turn/year',
                parameters={},
                required_params=[],
                validation_fn=lambda p: True
            ),
            'inspect_disaster_conditions': ToolDefinition(
                name='inspect_disaster_conditions',
                description='Check current disaster risks and environmental conditions',
                parameters={},
                required_params=[],
                validation_fn=lambda p: True
            ),
        }
    
    def get_tool(self, tool_name: str) -> Optional[ToolDefinition]:
        """Get a tool definition by name."""
        return self.tools.get(tool_name)
    
    def list_tools(self) -> list:
        """List all available tool names."""
        return list(self.tools.keys())
    
    def describe_tool(self, tool_name: str) -> str:
        """Get human-readable tool description."""
        tool = self.get_tool(tool_name)
        if not tool:
            return f"Unknown tool: {tool_name}"
        
        params_str = ", ".join([f"{k}: {v}" for k, v in tool.parameters.items()]) if tool.parameters else "none"
        return f"{tool.name}({params_str}) - {tool.description}"
    
    def validate_tool_call(self, tool_name: str, parameters: Dict[str, Any]) -> tuple:
        """
        Validate a tool call before execution.
        
        Returns:
            (is_valid: bool, error_message: str or None)
        """
        if tool_name not in self.tools:
            return False, f"Unknown tool: {tool_name}"
        
        tool = self.tools[tool_name]
        
        # Check required params
        for required in tool.required_params:
            if required not in parameters:
                return False, f"Missing required parameter: {required}"
        
        # Run custom validation
        if tool.validation_fn:
            try:
                if not tool.validation_fn(parameters):
                    return False, f"Validation failed for {tool_name}"
            except Exception as e:
                return False, f"Validation error: {str(e)}"
        
        return True, None
    
    def call_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Call a tool and return the result.
        
        Returns:
            Result dict with success status and data
        """
        # Validate
        is_valid, error = self.validate_tool_call(tool_name, parameters)
        if not is_valid:
            logger.error(f"Tool validation failed: {error}")
            return {'success': False, 'error': error, 'tool': tool_name}
        
        logger.debug(f"Calling tool: {tool_name} with params: {parameters}")
        
        try:
            if tool_name == 'inspect_kingdom_state':
                state = self.game.get_current_state()
                return {'success': True, 'state': state, 'tool': tool_name}
            
            elif tool_name == 'allocate_grain':
                action = self.game.allocate_grain(
                    parameters['amount_bushels'],
                    parameters['purpose']
                )
                return {'success': action.success, 'action': action, 'tool': tool_name}
            
            elif tool_name == 'manage_land':
                action = self.game.manage_land(
                    parameters.get('acres_to_buy', 0),
                    parameters.get('acres_to_sell', 0)
                )
                return {'success': action.success, 'action': action, 'tool': tool_name}
            
            elif tool_name == 'manage_farming':
                action = self.game.manage_farming(parameters['acres_to_plant'])
                return {'success': action.success, 'action': action, 'tool': tool_name}
            
            elif tool_name == 'manage_irrigation':
                action = self.game.manage_irrigation(parameters['acres_to_irrigate'])
                return {'success': action.success, 'action': action, 'tool': tool_name}
            
            elif tool_name == 'manage_treasury':
                action = self.game.manage_treasury(
                    parameters['amount'],
                    parameters['operation']
                )
                return {'success': action.success, 'action': action, 'tool': tool_name}
            
            elif tool_name == 'advance_kingdom_turn':
                success = self.game.advance_turn()
                return {'success': success, 'tool': tool_name}
            
            elif tool_name == 'inspect_disaster_conditions':
                conditions = self.game.inspect_disaster_conditions()
                return {'success': True, 'conditions': conditions, 'tool': tool_name}
        
        except Exception as e:
            logger.error(f"Error calling tool {tool_name}: {e}")
            return {'success': False, 'error': str(e), 'tool': tool_name}
    
    # Validation functions
    def _validate_allocate_grain(self, params: Dict) -> bool:
        if params.get('amount_bushels', 0) <= 0:
            return False
        if params.get('purpose') not in ['consumption', 'storage', 'seed', 'sell']:
            return False
        return True
    
    def _validate_manage_land(self, params: Dict) -> bool:
        if params.get('acres_to_buy', 0) < 0:
            return False
        if params.get('acres_to_sell', 0) < 0:
            return False
        if params.get('acres_to_buy', 0) > 500:
            return False
        return True
    
    def _validate_manage_farming(self, params: Dict) -> bool:
        return params.get('acres_to_plant', 0) >= 0
    
    def _validate_manage_irrigation(self, params: Dict) -> bool:
        return params.get('acres_to_irrigate', 0) >= 0
    
    def _validate_manage_treasury(self, params: Dict) -> bool:
        if params.get('amount', 0) <= 0:
            return False
        if params.get('operation') not in ['deposit', 'withdraw']:
            return False
        return True
