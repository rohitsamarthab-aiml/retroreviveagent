"""
test_governor_gui_scenarios.py - Automated verification for all 10 Royal Governor GUI scenarios.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

import pytest
import pygame
from ui_pygame import GameApp
from retrorevive import RetroReviveHub
from modern_game_logic import init_enhanced_game
from game_logic import init_game
from royal_governor import AgentStatus


def test_scenario_1_launch_graphical_game():
    """Scenario 1: Launch normal graphical game."""
    app = GameApp()
    assert app is not None
    assert app.current_screen == "MAIN_MENU"
    assert app.window is not None
    assert app.canvas is not None
    print("✓ Scenario 1: Launched normal graphical game (GameApp) successfully.")


def test_scenario_2_and_3_open_governor_no_terminal():
    """Scenario 2 & 3: Open Royal Governor dashboard & confirm no terminal game starts."""
    app = GameApp()
    # Click Royal Governor button on main menu
    app.btn_menu_governor.callback()
    assert app.current_screen == "ROYAL_GOVERNOR"
    assert app.governor_dashboard is not None
    assert app.governor_dashboard.governor is not None

    # Verify frame update and draw without exception (no terminal prompt / input loop)
    app.governor_dashboard.update(0.016)
    app.governor_dashboard.draw(app.canvas)
    print("✓ Scenario 2 & 3: Royal Governor GUI opened in same window; zero terminal prompts invoked.")


def test_scenario_4_switch_between_game_and_governor():
    """Scenario 4: Switch between game and Royal Governor."""
    app = GameApp()
    # 1. From MAIN_MENU to Royal Governor and back
    app._open_governor_screen()
    assert app.current_screen == "ROYAL_GOVERNOR"
    app.governor_dashboard.btn_return.callback()
    assert app.current_screen == "MAIN_MENU"

    # 2. From GAMEPLAY to Royal Governor and back
    app._start_enhanced_game()
    assert app.current_screen == "GAMEPLAY"
    initial_year = app.classic_state.year

    app._open_governor_screen()
    assert app.current_screen == "ROYAL_GOVERNOR"
    app.governor_dashboard.btn_return.callback()
    assert app.current_screen == "GAMEPLAY"
    assert app.classic_state.year == initial_year
    print("✓ Scenario 4: Clean bidirectional switching between main menu/gameplay and Royal Governor.")


def test_scenario_5_6_7_delegate_mission_read_state_change_resources():
    """Scenario 5, 6 & 7: Delegate mission, verify state read, verify resource changes."""
    app = GameApp()
    app._start_enhanced_game()
    initial_bushels = app.enhanced_state.classic_state.bushels
    initial_pop = app.enhanced_state.classic_state.population

    # Open Royal Governor
    app._open_governor_screen()
    dashboard = app.governor_dashboard

    # Select mandate
    dashboard._select_goal(0)  # Famine Defense
    assert "famine" in dashboard.selected_goal.lower()

    # Delegate 1 turn
    dashboard.btn_step_turn.callback()

    # Verify agent read actual kingdom state (Scenario 6)
    assert dashboard.last_record is not None
    rec = dashboard.last_record
    assert rec.before_resources["bushels"] == initial_bushels
    assert rec.before_resources["population"] == initial_pop

    # Verify tool calls changed actual game resources (Scenario 7)
    assert len(rec.tool_calls) > 0
    assert rec.after_resources["bushels"] != initial_bushels or rec.after_resources["acres"] != rec.before_resources["acres"]
    assert "bushels" in rec.resource_deltas
    assert rec.verification_ok is True

    # Check updated live state in dashboard
    assert dashboard.governor.current_enhanced_state.classic_state.year == 2
    print(f"✓ Scenario 5, 6, 7: Mission delegated, state read verified, tool calls executed: {rec.tool_calls}")


def test_scenario_8_revoke_delegation_regain_control():
    """Scenario 8: Revoke delegation and confirm that player regains control."""
    app = GameApp()
    app._start_enhanced_game()
    app._open_governor_screen()
    dashboard = app.governor_dashboard

    # Delegate 3 turns
    dashboard.turns_to_delegate = 3
    # Click revoke
    dashboard.btn_revoke.callback()
    assert dashboard.governor.is_delegating is False
    assert dashboard.governor.status == AgentStatus.PAUSED
    assert "REVOKED" in dashboard.status_message

    # Return to game and verify player can make manual input decisions
    dashboard.btn_return.callback()
    assert app.current_screen == "GAMEPLAY"
    assert app.input_feed is not None
    assert app.input_plant is not None
    print("✓ Scenario 8: Delegation successfully revoked; player retained immediate manual command.")


def test_scenario_9_return_to_main_menu():
    """Scenario 9: Return to the main menu."""
    app = GameApp()
    # From Main Menu -> Governor -> Return
    app._open_governor_screen()
    assert app.current_screen == "ROYAL_GOVERNOR"
    app.governor_dashboard.btn_return.callback()
    assert app.current_screen == "MAIN_MENU"

    # From Gameplay -> Pause -> Main Menu
    app._start_classic_game()
    assert app.current_screen == "GAMEPLAY"
    app._return_to_main_menu()
    assert app.current_screen == "MAIN_MENU"
    print("✓ Scenario 9: Return to main menu verified cleanly.")


def test_scenario_10_original_game_modes_work():
    """Scenario 10: Confirm that original game modes still work."""
    # 1. Classic 1978 mode
    app = GameApp()
    app._start_classic_game()
    assert app.active_mode == "CLASSIC"
    assert app.classic_state is not None
    assert app.classic_state.year == 1
    # Execute a manual turn
    app.input_buy.value = 0
    app.input_sell.value = 0
    app.input_feed.value = 2000
    app.input_plant.value = 500
    app._on_execute_turn()
    assert app.classic_state.year == 2

    # 2. Enhanced mode
    app2 = GameApp()
    app2._start_enhanced_game()
    assert app2.active_mode == "ENHANCED"
    assert app2.enhanced_state is not None
    assert len(app2.enhanced_state.rivals) == 3

    # 3. Scenario challenges
    app3 = GameApp()
    app3._start_scenario("drought")
    assert app3.enhanced_state.mode == "SCENARIO"

    # 4. RetroRevive Hub
    hub = RetroReviveHub()
    assert hub is not None
    assert len(hub.cards) >= 2
    # Quick launch Hammurabi into governor via key 3
    evt3 = pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_3})
    hub.handle_event(evt3)
    assert hub.active_subapp is not None
    assert hub.active_subapp.current_screen == "ROYAL_GOVERNOR"
    print("✓ Scenario 10: All original game modes (Classic, Enhanced, Scenarios, Hub) verified operational.")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
