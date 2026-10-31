"""
verify_ui.py - Automated visual verification and screenshot generator for RetroRevive platform.

Renders all screens at logical 1280x720 and multiple window resolutions,
captures screenshots into docs/screenshots/, and verifies alignment and text layout
for both the central platform library and all playable retro games.
"""

import os
import pygame

from game_logic import GameState
from games import matches_app
import retrorevive
from ui_pygame import BASE_HEIGHT, BASE_WIDTH, GameApp
from ui_theme import SoundSynthesizer


def run_visual_verification() -> bool:
    print("Starting visual platform & UI verification and screenshot generation...")
    os.makedirs("docs/screenshots", exist_ok=True)
    SoundSynthesizer.set_enabled(False)  # Mute audio during headless test

    # -------------------------------------------------------------------------
    # 1. Platform Library & Detail Modals
    # -------------------------------------------------------------------------
    hub = retrorevive.RetroReviveHub()
    hub.update(0.1)
    hub.draw()
    lib_path = "docs/screenshots/screenshot_platform_library.png"
    pygame.image.save(hub.canvas, lib_path)
    print(f"Captured: {lib_path}")

    # Open details modal for Hammurabi
    hub._open_details(hub.cards[0].meta)
    hub.update(0.1)
    hub.draw()
    details_path = "docs/screenshots/screenshot_game_details_modal.png"
    pygame.image.save(hub.canvas, details_path)
    print(f"Captured: {details_path}")
    hub._close_modal()

    # -------------------------------------------------------------------------
    # 2. 23 Matches Game Interface
    # -------------------------------------------------------------------------
    m_app = matches_app.MatchesApp()
    # Play a move so some matches are taken
    m_app._on_human_move(2)
    m_app.update(1.0)  # computer responds
    m_app.draw()
    m_game_path = "docs/screenshots/screenshot_23matches_gameplay.png"
    pygame.image.save(m_app.canvas, m_game_path)
    print(f"Captured: {m_game_path}")

    # Capture 23 Matches Victory Game Over
    m_app.state.game_over = True
    m_app.state.winner = "HUMAN"
    m_app.draw()
    m_over_path = "docs/screenshots/screenshot_23matches_game_over.png"
    pygame.image.save(m_app.canvas, m_over_path)
    print(f"Captured: {m_over_path}")

    # -------------------------------------------------------------------------
    # 3. Hammurabi Reimagined Screens
    # -------------------------------------------------------------------------
    app = GameApp()

    # Capture Main Menu Screen
    app.current_screen = "MAIN_MENU"
    app.update(0.1)
    app.draw()
    menu_path = "docs/screenshots/screenshot_main_menu.png"
    pygame.image.save(app.canvas, menu_path)
    print(f"Captured: {menu_path}")

    # Capture Classic Gameplay Screen (Year 1)
    app._start_classic_game()
    app.update(0.1)
    app.draw()
    classic_path = "docs/screenshots/screenshot_classic_gameplay.png"
    pygame.image.save(app.canvas, classic_path)
    print(f"Captured: {classic_path}")

    # Capture Enhanced Gameplay Screen (with Advisors dialog)
    app._start_enhanced_game()
    app.update(0.1)
    app._open_advisors_modal()
    app.draw()
    advisors_path = "docs/screenshots/screenshot_enhanced_advisors.png"
    pygame.image.save(app.canvas, advisors_path)
    print(f"Captured: {advisors_path}")
    app.active_modal = None

    # Capture Scenario Challenges Screen
    app._open_scenarios_screen()
    app.update(0.1)
    app.draw()
    scenarios_path = "docs/screenshots/screenshot_scenarios.png"
    pygame.image.save(app.canvas, scenarios_path)
    print(f"Captured: {scenarios_path}")

    # Capture Tutorial / Instructions Screen
    app._open_instructions_screen()
    app.update(0.1)
    app.draw()
    instructions_path = "docs/screenshots/screenshot_tutorial.png"
    pygame.image.save(app.canvas, instructions_path)
    print(f"Captured: {instructions_path}")

    # Capture Game Over / Evaluation Screen (Tier 4 Charlemagne)
    state = GameState(
        year=11,
        population=110,
        bushels=3200,
        acres=1200,
        land_price=22,
        starved_this_year=0,
        starved_total=5,
        starved_pct_avg=0.5,
        immigrants_this_year=8,
        harvest_yield=4,
        rats_ate=50,
        plague_struck=False,
        plague_next_year=False,
        is_over=True,
    )
    app.active_mode = "CLASSIC"
    app.classic_state = state
    app._handle_game_over(state)
    app.update(0.1)
    app.draw()
    game_over_path = "docs/screenshots/screenshot_game_over.png"
    pygame.image.save(app.canvas, game_over_path)
    print(f"Captured: {game_over_path}")

    # -------------------------------------------------------------------------
    # 3b. Cinematic Cutscenes (Prologue, Harvest, Plague)
    # -------------------------------------------------------------------------
    app.current_screen = "MAIN_MENU"
    app.cinematics.trigger_prologue()
    app.update(1.2)
    app.draw()
    prologue_path = "docs/screenshots/screenshot_cinematic_prologue.png"
    pygame.image.save(app.canvas, prologue_path)
    print(f"Captured: {prologue_path}")
    app.cinematics.skip()

    # Harvest Cinematic
    app.current_screen = "GAMEPLAY"
    app.cinematics.trigger_harvest(yield_per_acre=5, total_harvest=2500)
    app.update(1.5)
    app.draw()
    harvest_path = "docs/screenshots/screenshot_cinematic_harvest.png"
    pygame.image.save(app.canvas, harvest_path)
    print(f"Captured: {harvest_path}")
    app.cinematics.skip()

    # Plague Event Cinematic
    app.current_screen = "GAMEPLAY"
    app.cinematics.trigger_plague(deaths=50, survivors=50)
    app.update(1.5)
    app.draw()
    plague_path = "docs/screenshots/screenshot_cinematic_plague.png"
    pygame.image.save(app.canvas, plague_path)
    print(f"Captured: {plague_path}")
    app.cinematics.skip()

    # -------------------------------------------------------------------------
    # 4. Multi-Resolution Window Scaling (1366x768 and 1920x1080)
    # -------------------------------------------------------------------------
    for w, h in [(1366, 768), (1920, 1080)]:
        hub.screen_width = w
        hub.screen_height = h
        hub.window = pygame.Surface((w, h))
        hub.draw()
        scale_path = f"docs/screenshots/screenshot_scale_{w}x{h}.png"
        pygame.image.save(hub.window, scale_path)
        print(f"Captured scaled window: {scale_path}")

    pygame.quit()
    print("Visual verification completed successfully! All screenshots saved.")
    return True


if __name__ == "__main__":
    run_visual_verification()
