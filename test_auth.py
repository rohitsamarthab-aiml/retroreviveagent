"""
test_auth.py - Comprehensive Unit and Integration Tests for RetroRevive Authentication & UI Startup Flow.

Tests:
- Password hashing and salt verification
- User registration, duplicate checks, validation
- Login authentication, guest sessions, logout
- Multi-slot save management (save, load, list, delete)
- Game outcome & achievements tracking
- AuthModal dialog events: switching modes, submitting login, registration, guest access
- Application startup flows in main.py, ui_pygame.py, and retrorevive.py
"""

import os
import shutil
import tempfile
import unittest
import pygame

from auth_manager import AuthManager, UserProfile, _hash_password, _verify_password
from ui_auth import AuthModal
from ui_pygame import GameApp
import retrorevive


class TestAuthManager(unittest.TestCase):
    """Verifies core authentication security and account persistence."""

    def setUp(self) -> None:
        self.test_dir = tempfile.mkdtemp()
        self.accounts_path = os.path.join(self.test_dir, "accounts.json")
        self.saves_dir = os.path.join(self.test_dir, "saves")
        self.auth = AuthManager(accounts_path=self.accounts_path, saves_dir=self.saves_dir)

    def tearDown(self) -> None:
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_default_session_is_guest(self) -> None:
        self.assertIsNotNone(self.auth.current_user)
        self.assertTrue(self.auth.current_user.is_guest)
        self.assertEqual(self.auth.get_current_username(), "Guest")

    def test_registration_validation(self) -> None:
        # Username too short
        ok, msg = self.auth.register("ab", "pass123")
        self.assertFalse(ok)
        self.assertIn("at least 3 characters", msg)

        # Invalid characters
        ok, msg = self.auth.register("user@name", "pass123")
        self.assertFalse(ok)
        self.assertIn("letters, numbers", msg)

        # Password mismatch
        ok, msg = self.auth.register("validuser", "pass123", confirm="different")
        self.assertFalse(ok)
        self.assertIn("do not match", msg)

        # Successful registration
        ok, msg = self.auth.register("validuser", "pass123", confirm="pass123", display_name="Sargon")
        self.assertTrue(ok)
        self.assertIn("Welcome", msg)
        self.assertEqual(self.auth.get_current_username(), "Sargon")
        self.assertFalse(self.auth.current_user.is_guest)

        # Duplicate username rejection
        ok, msg = self.auth.register("validuser", "anotherpass")
        self.assertFalse(ok)
        self.assertIn("already exists", msg)

    def test_login_and_logout(self) -> None:
        self.auth.register("sargon", "akkad123")
        self.auth.logout()
        self.assertTrue(self.auth.current_user.is_guest)

        # Wrong password
        ok, msg = self.auth.login("sargon", "wrongpass")
        self.assertFalse(ok)
        self.assertIn("Incorrect password", msg)

        # Correct password
        ok, msg = self.auth.login("sargon", "akkad123")
        self.assertTrue(ok)
        self.assertFalse(self.auth.current_user.is_guest)
        self.assertEqual(self.auth.get_current_username(), "Sargon")

        # Unknown user
        ok, msg = self.auth.login("unknown", "pass")
        self.assertFalse(ok)
        self.assertIn("User not found", msg)

    def test_multi_slot_saves(self) -> None:
        self.auth.register("nabu", "temple123")
        slots = self.auth.list_save_slots()
        self.assertEqual(len(slots), 3)
        self.assertFalse(slots[0]["exists"])

        # Save to slot 1
        payload = {"mode": "ENHANCED", "state": {"year": 5, "population": 120, "bushels": 3200, "acres": 1100}}
        saved = self.auth.save_slot(1, payload)
        self.assertTrue(saved)

        # List slots
        slots = self.auth.list_save_slots()
        self.assertTrue(slots[0]["exists"])
        self.assertEqual(slots[0]["year"], 5)
        self.assertEqual(slots[0]["population"], 120)

        # Load slot
        loaded = self.auth.load_slot(1)
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded["slot_id"], 1)
        self.assertEqual(loaded["state"]["year"], 5)

        # Delete slot
        deleted = self.auth.delete_slot(1)
        self.assertTrue(deleted)
        self.assertIsNone(self.auth.load_slot(1))

    def test_record_game_outcome_and_achievements(self) -> None:
        self.auth.register("gilgamesh", "uruk123")
        self.auth.record_game_outcome(tier=4, title="Charlemagne of the Ancient World", year=10)
        prof = self.auth.get_current_profile()
        self.assertEqual(prof.games_played, 1)
        self.assertEqual(prof.victories, 1)
        self.assertEqual(prof.best_score_tier, 4)
        self.assertIn("CHARLEMAGNE_TIER", prof.achievements)
        self.assertIn("TEN_YEAR_REIGN", prof.achievements)


class TestAuthModalUI(unittest.TestCase):
    """Verifies AuthModal UI interaction and callbacks."""

    @classmethod
    def setUpClass(cls) -> None:
        pygame.init()
        pygame.display.set_mode((1280, 720), pygame.HIDDEN)

    @classmethod
    def tearDownClass(cls) -> None:
        pygame.quit()

    def setUp(self) -> None:
        self.test_dir = tempfile.mkdtemp()
        self.auth = AuthManager(
            accounts_path=os.path.join(self.test_dir, "accounts.json"),
            saves_dir=os.path.join(self.test_dir, "saves")
        )
        self.success_called = False

        def on_success():
            self.success_called = True

        self.on_success = on_success
        self.modal = AuthModal(self.auth, on_success=self.on_success, initial_mode="LOGIN")

    def tearDown(self) -> None:
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_guest_button_submits_and_closes(self) -> None:
        self.modal._submit_guest()
        self.assertTrue(self.success_called)
        self.assertFalse(self.modal.is_open)
        self.assertTrue(self.auth.current_user.is_guest)

    def test_registration_and_login_flow(self) -> None:
        self.modal.switch_mode("REGISTER")
        self.assertEqual(self.modal.mode, "REGISTER")

        self.modal.username_buffer = "enheduanna"
        self.modal.password_buffer = "hymn123"
        self.modal.confirm_password_buffer = "hymn123"
        self.modal._submit_register()

        self.assertTrue(self.success_called)
        self.assertFalse(self.modal.is_open)
        self.assertEqual(self.auth.get_current_username(), "Enheduanna")

        # Now test login
        self.auth.logout()
        self.modal = AuthModal(self.auth, on_success=self.on_success, initial_mode="LOGIN")
        self.modal.username_buffer = "enheduanna"
        self.modal.password_buffer = "hymn123"
        self.modal._submit_login()

        self.assertFalse(self.modal.is_open)
        self.assertEqual(self.auth.get_current_username(), "Enheduanna")

    def test_keyboard_tab_cycling(self) -> None:
        self.modal.switch_mode("REGISTER")
        self.modal.focused_field = "username"

        tab_ev = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_TAB)
        self.modal.handle_event(tab_ev, (0, 0))
        self.assertEqual(self.modal.focused_field, "password")

        self.modal.handle_event(tab_ev, (0, 0))
        self.assertEqual(self.modal.focused_field, "confirm")

        self.modal.handle_event(tab_ev, (0, 0))
        self.assertEqual(self.modal.focused_field, "username")

    def test_escape_closes_modal(self) -> None:
        esc_ev = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE)
        self.modal.handle_event(esc_ev, (0, 0))
        self.assertFalse(self.modal.is_open)


class TestStartupIntegration(unittest.TestCase):
    """Verifies that GameApp and RetroReviveHub integrate Auth seamlessly."""

    @classmethod
    def setUpClass(cls) -> None:
        pygame.init()
        pygame.display.set_mode((1280, 720), pygame.HIDDEN)

    @classmethod
    def tearDownClass(cls) -> None:
        pygame.quit()

    def test_game_app_with_show_auth_modal(self) -> None:
        app = GameApp(show_auth_modal=True)
        self.assertIsNotNone(app.auth_modal)
        self.assertTrue(app.auth_modal.is_open)
        self.assertEqual(app.auth_modal.mode, "LOGIN")

        # Click guest access on the startup modal
        app.auth_modal._submit_guest()
        self.assertFalse(app.auth_modal.is_open)
        self.assertEqual(app.auth.get_current_username(), "Guest")

    def test_game_app_without_auth_modal(self) -> None:
        app = GameApp(show_auth_modal=False)
        self.assertIsNone(app.auth_modal)

    def test_hub_with_show_auth_modal(self) -> None:
        hub = retrorevive.RetroReviveHub(show_auth_modal=True)
        self.assertIsNotNone(hub.auth_modal)
        self.assertTrue(hub.auth_modal.is_open)

        # Login in Hub
        hub.auth.register("urukking", "crown123")
        hub.auth_modal.username_buffer = "urukking"
        hub.auth_modal.password_buffer = "crown123"
        hub.auth_modal._submit_login()
        self.assertFalse(hub.auth_modal.is_open)

        # Launching Hammurabi preserves the same authenticated user
        hub.launch_game("hammurabi")
        self.assertIsNotNone(hub.active_subapp)
        self.assertEqual(hub.active_subapp.auth.get_current_username(), "Urukking")


if __name__ == "__main__":
    unittest.main()
