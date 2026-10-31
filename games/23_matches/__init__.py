"""
games/23_matches/__init__.py
"""
# Relative import works even when the folder name starts with a digit
from .engine import (
    MatchesGameState,
    init_game,
    validate_move,
    make_move,
    get_computer_move,
    play_cli,
)

__all__ = [
    "MatchesGameState",
    "init_game",
    "validate_move",
    "make_move",
    "get_computer_move",
    "play_cli",
]
