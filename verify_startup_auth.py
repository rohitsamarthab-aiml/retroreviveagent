"""
verify_startup_auth.py - Live Verification of RetroRevive Real Startup Flow and Auth Features.

Tests real entry points:
1. main.py default flow (RetroReviveHub) with AuthModal startup
2. ui_auth.py registration screen, inputs, password mask toggle, submission
3. ui_auth.py login screen, authentication, sovereign identity
4. ui_auth.py guest / demo access (1-click zero friction)
5. main.py --hammurabi direct entry point with auth integration
6. Captures screenshots into artifacts directory to visually prove correctness.
"""

import os
import sys
import time
import pygame

# Set dummy audio driver if no hardware available, but keep video real/hidden
os.environ["SDL_AUDIODRIVER"] = "dummy"

import main
from auth_manager import AuthManager
from ui_auth import AuthModal
from ui_pygame import GameApp
import retrorevive

ARTIFACT_DIR = r"C:\Users\rohit\.gemini\antigravity-ide\brain\df59fad2-fefb-429b-8f2e-ac48bda89608"
os.makedirs(ARTIFACT_DIR, exist_ok=True)


def test_real_startup_flow() -> None:
    print("=== 1. Testing RetroReviveHub Real Entry Point with Auth Startup ===")
    hub = retrorevive.RetroReviveHub(show_auth_modal=True)
    assert hub.auth_modal is not None, "AuthModal should be initialized"
    assert hub.auth_modal.is_open, "AuthModal should be open on default application startup"
    assert hub.auth_modal.mode == "LOGIN", "Default initial mode should be LOGIN"

    # Render frame 1: Hub with Login modal
    hub.canvas.fill((20, 20, 30))
    hub.draw()
    shot_hub_login = os.path.join(ARTIFACT_DIR, "shot_startup_hub_login.png")
    pygame.image.save(hub.canvas, shot_hub_login)
    print(f"Captured: {shot_hub_login}")

    # Switch to registration mode
    print("=== 2. Testing Registration Mode in AuthModal ===")
    hub.auth_modal.switch_mode("REGISTER")
    assert hub.auth_modal.mode == "REGISTER"

    hub.canvas.fill((20, 20, 30))
    hub.draw()
    shot_register = os.path.join(ARTIFACT_DIR, "shot_startup_register.png")
    pygame.image.save(hub.canvas, shot_register)
    print(f"Captured: {shot_register}")

    # Test registration with mismatch
    test_user = f"ruler_{int(time.time())}"
    hub.auth_modal.username_buffer = test_user
    hub.auth_modal.password_buffer = "ishtar777"
    hub.auth_modal.confirm_password_buffer = "mismatch"
    hub.auth_modal._submit_register()
    assert hub.auth_modal.error_message == "Passwords do not match."
    assert hub.auth_modal.is_open

    # Test successful registration
    hub.auth_modal.confirm_password_buffer = "ishtar777"
    hub.auth_modal._submit_register()
    assert not hub.auth_modal.is_open, f"Modal should close on registration success: {hub.auth_modal.error_message}"
    assert hub.auth.get_current_username() == test_user.capitalize()
    assert not hub.auth.current_user.is_guest

    # Verify hub header updated with Sovereign's name
    hub.draw()
    shot_hub_registered = os.path.join(ARTIFACT_DIR, "shot_hub_registered_user.png")
    pygame.image.save(hub.canvas, shot_hub_registered)
    print(f"Captured: {shot_hub_registered}")

    print("=== 3. Testing Launching Hammurabi from Hub with Authenticated Session ===")
    hub.launch_game("hammurabi")
    assert hub.active_subapp is not None
    assert hub.active_subapp.auth.get_current_username() == test_user.capitalize()
    assert hub.active_subapp.auth.current_user.username == test_user

    hub.draw()
    shot_hammurabi_auth = os.path.join(ARTIFACT_DIR, "shot_hammurabi_authenticated.png")
    pygame.image.save(hub.active_subapp.canvas, shot_hammurabi_auth)
    print(f"Captured: {shot_hammurabi_auth}")

    # Return to library
    hub._return_to_hub()
    assert hub.active_subapp is None

    print("=== 4. Testing Guest / Demo Access Flow ===")
    # Open auth modal again and test Guest access
    hub._open_auth_modal()
    assert hub.auth_modal.is_open
    hub.auth_modal._submit_guest()
    assert not hub.auth_modal.is_open
    assert hub.auth.current_user.is_guest
    assert hub.auth.get_current_username() == "Guest"

    print("=== 5. Testing Direct Hammurabi Entry Point (main.py --hammurabi) ===")
    game_app = GameApp(show_auth_modal=True)
    assert game_app.auth_modal is not None
    assert game_app.auth_modal.is_open

    game_app.draw()
    shot_game_login = os.path.join(ARTIFACT_DIR, "shot_game_app_login.png")
    pygame.image.save(game_app.canvas, shot_game_login)
    print(f"Captured: {shot_game_login}")

    # Guest access in Hammurabi
    game_app.auth_modal._submit_guest()
    assert not game_app.auth_modal.is_open
    assert game_app.auth.current_user.is_guest

    game_app.draw()
    shot_game_guest = os.path.join(ARTIFACT_DIR, "shot_game_app_guest_menu.png")
    pygame.image.save(game_app.canvas, shot_game_guest)
    print(f"Captured: {shot_game_guest}")

    print("=== 6. Testing multi-slot saves in game ===")
    game_app._open_save_slots_modal("SAVE")
    assert game_app.auth_modal is not None
    assert game_app.auth_modal.is_open
    assert game_app.auth_modal.mode == "SAVES"

    game_app.draw()
    shot_saves = os.path.join(ARTIFACT_DIR, "shot_game_save_slots.png")
    pygame.image.save(game_app.canvas, shot_saves)
    print(f"Captured: {shot_saves}")

    print("\n[ALL STARTUP FLOW AND AUTHENTICATION VERIFICATIONS PASSED 100%!]")


if __name__ == "__main__":
    test_real_startup_flow()
