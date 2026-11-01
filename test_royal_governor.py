import pytest
from game_logic import GameState
from modern_game_logic import EnhancedGameState, init_enhanced_game
from agent_tools import *
from royal_governor import RoyalGovernor

class TestRoyalGovernorMultiKingdom:
    def test_multi_kingdom_init(self):
        e = init_enhanced_game()
        assert len(e.rivals) == 3
        assert len(e.diplomacy) == 3
    def test_scout_tool(self):
        e = init_enhanced_game()
        e.classic_state = e.classic_state.__class__(**{**e.classic_state.__dict__, "treasury_gold": 500})
        res = scout_kingdom(e, "elam")
        assert res["success"] is True
    def test_autonomous_cycle(self):
        e = init_enhanced_game()
        gov = RoyalGovernor(e)
        session = gov.delegate("Build military", 1)
        assert session.turns_completed == 1
