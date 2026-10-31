"""
games/__init__.py - Games package for RetroRevive platform.

Provides clean module access even for directories with leading digits.
"""

import importlib

# Dynamic module imports to bypass Python syntax limitation on leading digits (23_matches)
matches_engine = importlib.import_module("games.23_matches.engine")
matches_app = importlib.import_module("games.23_matches.app")

__all__ = ["matches_engine", "matches_app"]
