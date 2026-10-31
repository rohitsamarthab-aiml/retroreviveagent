"""
auth_manager.py - Local Authentication, User Profiles & Multi-Slot Saves for RetroRevive.

Features:
- Secure local authentication using salted SHA-256 password hashing
- Registration, validation, and login
- One-click Guest Ruler access for instant zero-friction play
- Player profiles with reign statistics and historical achievements
- Multi-slot save game management (Slot 1, Slot 2, Slot 3) per player
- 100% offline standard-library implementation (json, hashlib, os, time)
"""

from dataclasses import asdict, dataclass, field
from datetime import datetime
import hashlib
import json
import os
import secrets
from typing import Any, Dict, List, Optional, Tuple


ACCOUNTS_FILE = "accounts.json"
SAVES_DIR = "saves"


def _hash_password(password: str, salt_hex: Optional[str] = None) -> Tuple[str, str]:
    """Generates a secure PBKDF2-HMAC-SHA256 password hash with salt."""
    if salt_hex is None:
        salt = secrets.token_bytes(16)
        salt_hex = salt.hex()
    else:
        salt = bytes.fromhex(salt_hex)
    
    key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100000)
    return key.hex(), salt_hex


def _verify_password(password: str, salt_hex: str, hash_hex: str) -> bool:
    """Verifies candidate password against stored salt and hash."""
    calc_hash, _ = _hash_password(password, salt_hex)
    return secrets.compare_digest(calc_hash, hash_hex)


@dataclass
class UserProfile:
    """Player profile storing reign records and achievements."""
    username: str
    display_name: str
    salt_hex: str
    hash_hex: str
    created_at: str
    last_login: str
    games_played: int = 0
    victories: int = 0
    best_score_tier: int = 0
    best_score_title: str = "Unrecorded"
    achievements: List[str] = field(default_factory=list)
    is_guest: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UserProfile":
        return cls(
            username=data.get("username", "ruler"),
            display_name=data.get("display_name", "Hammurabi"),
            salt_hex=data.get("salt_hex", ""),
            hash_hex=data.get("hash_hex", ""),
            created_at=data.get("created_at", datetime.now().isoformat()),
            last_login=data.get("last_login", datetime.now().isoformat()),
            games_played=data.get("games_played", 0),
            victories=data.get("victories", 0),
            best_score_tier=data.get("best_score_tier", 0),
            best_score_title=data.get("best_score_title", "Unrecorded"),
            achievements=data.get("achievements", []),
            is_guest=data.get("is_guest", False),
        )


PlayerProfile = UserProfile


class AuthManager:
    """Manages player accounts, sessions, and multiple save slots."""

    def __init__(self, accounts_path: str = ACCOUNTS_FILE, saves_dir: str = SAVES_DIR) -> None:
        self.accounts_path = accounts_path
        self.saves_dir = saves_dir
        self.users: Dict[str, UserProfile] = {}
        self.current_user: Optional[UserProfile] = None
        os.makedirs(self.saves_dir, exist_ok=True)
        self._load_accounts()

        # Default to a friendly guest session initially
        self.login_as_guest()

    def _load_accounts(self) -> None:
        if os.path.exists(self.accounts_path):
            try:
                with open(self.accounts_path, "r", encoding="utf-8") as f:
                    raw = json.load(f)
                    for u_name, u_data in raw.get("users", {}).items():
                        self.users[u_name] = UserProfile.from_dict(u_data)
            except Exception:
                self.users = {}

    def _save_accounts(self) -> None:
        try:
            out = {
                "version": 1,
                "users": {
                    u_name: prof.to_dict()
                    for u_name, prof in self.users.items()
                    if not prof.is_guest
                }
            }
            with open(self.accounts_path, "w", encoding="utf-8") as f:
                json.dump(out, f, indent=2)
        except Exception:
            pass

    def get_current_username(self) -> str:
        """Returns current ruler display name or guest identifier."""
        if self.current_user:
            if self.current_user.is_guest:
                return "Guest"
            return self.current_user.display_name or self.current_user.username
        return "Guest"

    def get_current_profile(self) -> Optional[UserProfile]:
        """Returns the active UserProfile dataclass instance."""
        return self.current_user

    def register(self, username: str, password: str, confirm: Optional[str] = None, display_name: Optional[str] = None) -> Tuple[bool, str]:
        """Registers a new user account with validation."""
        username = username.strip()
        if len(username) < 3:
            return False, "Username must be at least 3 characters."
        if not username.replace("_", "").isalnum():
            return False, "Username must contain only letters, numbers, and underscores."
        if username.lower() in self.users:
            return False, "Username already exists. Please choose another."
        if len(password) < 4:
            return False, "Password must be at least 4 characters."
        if confirm is not None and password != confirm:
            return False, "Passwords do not match."

        hash_hex, salt_hex = _hash_password(password)
        disp = display_name.strip() if (display_name and display_name.strip()) else username.capitalize()
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M")

        profile = UserProfile(
            username=username.lower(),
            display_name=disp,
            salt_hex=salt_hex,
            hash_hex=hash_hex,
            created_at=now_str,
            last_login=now_str,
            games_played=0,
            victories=0,
            achievements=["BABYLON_CITIZEN"],
            is_guest=False,
        )
        self.users[username.lower()] = profile
        self.current_user = profile
        self._save_accounts()
        return True, f"Welcome to the Kingdom, {disp}!"

    def login(self, username: str, password: str) -> Tuple[bool, str]:
        """Authenticates an existing user."""
        u_key = username.strip().lower()
        if u_key not in self.users:
            return False, "User not found. Please register or play as Guest."

        prof = self.users[u_key]
        if not _verify_password(password, prof.salt_hex, prof.hash_hex):
            return False, "Incorrect password. Please try again."

        prof.last_login = datetime.now().strftime("%Y-%m-%d %H:%M")
        self.current_user = prof
        self._save_accounts()
        return True, f"Welcome back, Sovereign {prof.display_name}!"

    def login_as_guest(self) -> None:
        """Enters an immediate guest session for judges or quick play."""
        self.current_user = UserProfile(
            username="guest",
            display_name="King Hammurabi (Guest)",
            salt_hex="",
            hash_hex="",
            created_at=datetime.now().strftime("%Y-%m-%d %H:%M"),
            last_login=datetime.now().strftime("%Y-%m-%d %H:%M"),
            is_guest=True,
            achievements=["ROYAL_GUEST"],
        )

    def logout(self) -> None:
        """Logs out and resets to guest ruler."""
        self.login_as_guest()

    def record_game_outcome(self, tier: int, title: str, year: int) -> None:
        """Updates career statistics and unlocks historical achievements."""
        if not self.current_user:
            return
        self.current_user.games_played += 1
        if tier >= 3:
            self.current_user.victories += 1
        if tier > self.current_user.best_score_tier:
            self.current_user.best_score_tier = tier
            self.current_user.best_score_title = title

        # Achievements
        achieves = set(self.current_user.achievements)
        achieves.add("RULED_BABYLON")
        if year >= 10:
            achieves.add("TEN_YEAR_REIGN")
        if tier == 4:
            achieves.add("CHARLEMAGNE_TIER")
        self.current_user.achievements = sorted(list(achieves))

        if not self.current_user.is_guest:
            self._save_accounts()

    # -------------------------------------------------------------------------
    # Multiple Save Slots (Slot 1, Slot 2, Slot 3)
    # -------------------------------------------------------------------------

    def _get_slot_path(self, slot_id: int) -> str:
        u_name = self.current_user.username if self.current_user else "guest"
        return os.path.join(self.saves_dir, f"{u_name}_slot_{slot_id}.json")

    def list_save_slots(self) -> List[Dict[str, Any]]:
        """Returns metadata for all 3 save slots for active user."""
        slots = []
        for i in range(1, 4):
            path = self._get_slot_path(i)
            if os.path.exists(path):
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        st = data.get("state", {})
                        slots.append({
                            "slot_id": i,
                            "exists": True,
                            "saved_at": data.get("saved_at", "Unknown"),
                            "mode": data.get("mode", "CLASSIC"),
                            "year": st.get("year", 1),
                            "population": st.get("population", 100),
                            "bushels": st.get("bushels", 2800),
                            "acres": st.get("acres", 1000),
                        })
                except Exception:
                    slots.append({"slot_id": i, "exists": False})
            else:
                slots.append({"slot_id": i, "exists": False})
        return slots

    def save_slot(self, slot_id: int, game_data: Dict[str, Any]) -> bool:
        """Saves game state into specified slot."""
        path = self._get_slot_path(slot_id)
        try:
            payload = {
                "slot_id": slot_id,
                "saved_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "username": self.current_user.username if self.current_user else "guest",
                **game_data,
            }
            with open(path, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2)
            return True
        except Exception:
            return False

    def load_slot(self, slot_id: int) -> Optional[Dict[str, Any]]:
        """Loads game state payload from specified slot."""
        path = self._get_slot_path(slot_id)
        if not os.path.exists(path):
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None

    def delete_slot(self, slot_id: int) -> bool:
        """Deletes a save slot."""
        path = self._get_slot_path(slot_id)
        if os.path.exists(path):
            try:
                os.remove(path)
                return True
            except Exception:
                return False
        return True
