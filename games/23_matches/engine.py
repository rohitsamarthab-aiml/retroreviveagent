"""
games/23_matches/engine.py - Pure Python engine for 23 Matches (1978 Edition).

Preserves the historical rules and AI calculations from Bob Albrecht's original game
published in 101 BASIC Computer Games (1973) and BASIC Computer Games (1978, Ahl).
Uses only the Python standard library.
"""

from dataclasses import dataclass, field
import sys
from typing import Any, List, Optional, Tuple


@dataclass
class TurnRecord:
    """Records a single turn in the match game."""
    turn_index: int
    player: str  # "HUMAN" or "COMPUTER"
    matches_taken: int
    matches_remaining: int


@dataclass
class MatchesGameState:
    """State model for 23 Matches."""
    matches_remaining: int = 23
    current_player: str = "HUMAN"  # "HUMAN" or "COMPUTER"
    game_over: bool = False
    winner: Optional[str] = None  # "HUMAN" or "COMPUTER"
    loser: Optional[str] = None   # "HUMAN" or "COMPUTER"
    last_move: Optional[int] = None
    last_mover: Optional[str] = None
    history: List[TurnRecord] = field(default_factory=list)
    ai_mode: str = "CLASSIC_1978"  # "CLASSIC_1978" or "OPTIMAL"


def init_game(
    initial_matches: int = 23,
    first_player: str = "HUMAN",
    ai_mode: str = "CLASSIC_1978",
) -> MatchesGameState:
    """
    Initializes a new game of 23 Matches.
    Default starts with 23 matches on the table, Human moving first.
    """
    if initial_matches < 1:
        raise ValueError("Initial match count must be at least 1.")
    if first_player not in ("HUMAN", "COMPUTER"):
        raise ValueError("first_player must be 'HUMAN' or 'COMPUTER'.")
    if ai_mode not in ("CLASSIC_1978", "OPTIMAL"):
        raise ValueError("ai_mode must be 'CLASSIC_1978' or 'OPTIMAL'.")

    return MatchesGameState(
        matches_remaining=initial_matches,
        current_player=first_player,
        game_over=False,
        winner=None,
        loser=None,
        last_move=None,
        last_mover=None,
        history=[],
        ai_mode=ai_mode,
    )


def validate_move(state: MatchesGameState, take: Any) -> Tuple[bool, Optional[str]]:
    """
    Validates a player's proposed move.
    Returns (True, None) if legal, or (False, error_reason) if illegal.
    Does NOT modify the game state.
    """
    if state.game_over:
        return False, "The game is already over."

    if not isinstance(take, int) or isinstance(take, bool):
        return False, "You must enter an integer number of matches (1, 2, or 3)."

    if take < 1:
        return False, "Illegal move. You must take at least 1 match."

    if take > 3:
        return False, "Illegal move. You can take at most 3 matches per turn."

    if take > state.matches_remaining:
        return False, f"Illegal move. Only {state.matches_remaining} matches remain on the table."

    return True, None


def make_move(state: MatchesGameState, take: int) -> MatchesGameState:
    """
    Executes a move for the current player.
    Returns a new or updated MatchesGameState.
    Raises ValueError if move is invalid.
    """
    is_valid, err = validate_move(state, take)
    if not is_valid:
        raise ValueError(err)

    new_remaining = state.matches_remaining - take
    mover = state.current_player
    turn_idx = len(state.history) + 1

    record = TurnRecord(
        turn_index=turn_idx,
        player=mover,
        matches_taken=take,
        matches_remaining=new_remaining,
    )
    new_history = list(state.history) + [record]

    # Misère Nim: Player who takes the last match loses
    if new_remaining <= 0:
        loser = mover
        winner = "COMPUTER" if mover == "HUMAN" else "HUMAN"
        return MatchesGameState(
            matches_remaining=0,
            current_player=mover,
            game_over=True,
            winner=winner,
            loser=loser,
            last_move=take,
            last_mover=mover,
            history=new_history,
            ai_mode=state.ai_mode,
        )

    next_player = "COMPUTER" if mover == "HUMAN" else "HUMAN"
    return MatchesGameState(
        matches_remaining=new_remaining,
        current_player=next_player,
        game_over=False,
        winner=None,
        loser=None,
        last_move=take,
        last_mover=mover,
        history=new_history,
        ai_mode=state.ai_mode,
    )


def get_computer_move(state: MatchesGameState) -> int:
    """
    Computes the computer's move based on the selected AI strategy.
    
    1. CLASSIC_1978 (Bob Albrecht):
       If human just moved with take Z, computer plays Z1 = 4 - Z.
       If remaining matches < 4 - Z, computer takes as many as allowed to leave 1,
       or takes 1 if forced.
       
    2. OPTIMAL (Modular Misère Nim):
       Target state is to leave the opponent with N = 1 (mod 4).
       Target remainder r = (N - 1) % 4.
       If r in (1, 2, 3), take r matches!
       If r == 0, opponent is in winning position; computer plays 1 match stalling.
    """
    if state.game_over:
        raise ValueError("Cannot calculate computer move when game is over.")
    if state.matches_remaining <= 0:
        raise ValueError("No matches remaining.")

    N = state.matches_remaining

    # If only 1 match remains, computer is forced to take it and lose
    if N == 1:
        return 1

    if state.ai_mode == "CLASSIC_1978":
        # Check human's last move
        if state.last_mover == "HUMAN" and state.last_move is not None:
            z1 = 4 - state.last_move
            # If z1 matches remain and is legal (1 <= z1 <= 3 and z1 <= N):
            if 1 <= z1 <= 3 and z1 <= N:
                # If z1 leaves 0 matches, that would be taking the last match!
                # If we can avoid taking the last match, leave 1!
                if N - z1 == 0 and N > 1:
                    # Choose a move that leaves 1 match if possible
                    return min(3, max(1, N - 1))
                return z1

        # Fallback if no prior human move or z1 invalid
        r = (N - 1) % 4
        if 1 <= r <= 3 and r <= N:
            return r
        return min(3, max(1, N - 1))

    else:  # OPTIMAL
        # Optimal misère Nim target: leave N' where (N' - 1) % 4 == 0 (i.e. 1, 5, 9, 13, 17, 21)
        r = (N - 1) % 4
        if 1 <= r <= 3 and r <= N:
            return r
        # If in a losing position (r == 0), take 1 match
        return 1


def play_cli(ai_mode: str = "CLASSIC_1978") -> None:
    """
    Interactive terminal command-line runner for 23 Matches.
    Uses pure standard library.
    """
    print("=" * 60)
    print("           23 MATCHES (1978 CREATIVE COMPUTING)")
    print("          Original by Bob Albrecht & David H. Ahl")
    print("=" * 60)
    print("THIS IS A GAME CALLED '23 MATCHES'.")
    print("WHEN IT IS YOUR TURN, YOU MAY TAKE 1, 2, OR 3 MATCHES.")
    print("THE OBJECT OF THE GAME IS TO FORCE YOUR OPPONENT TO")
    print("TAKE THE VERY LAST MATCH!\n")

    state = init_game(initial_matches=23, first_player="HUMAN", ai_mode=ai_mode)

    while not state.game_over:
        print(f"\nTHERE ARE NOW {state.matches_remaining} MATCHES REMAINING.")
        # Render ASCII matchsticks
        match_art = "| " * state.matches_remaining
        print(f"Pile: {match_art}")

        if state.current_player == "HUMAN":
            while True:
                try:
                    raw = input("YOUR MOVE (1, 2, OR 3)? ").strip()
                    if not raw:
                        continue
                    val = int(raw)
                    ok, err = validate_move(state, val)
                    if not ok:
                        print(f"? {err}")
                        continue
                    state = make_move(state, val)
                    break
                except ValueError:
                    print("? ILLEGAL MOVE. PLEASE ENTER 1, 2, OR 3.")
                except (EOFError, KeyboardInterrupt):
                    print("\nSO LONG FOR NOW.")
                    return
        else:
            comp_take = get_computer_move(state)
            print(f"MY TURN! I REMOVE {comp_take} MATCH{'ES' if comp_take > 1 else ''}.")
            state = make_move(state, comp_take)

    print("\n" + "=" * 60)
    if state.winner == "HUMAN":
        print("THE COMPUTER TOOK THE LAST MATCH! YOU WIN!")
    else:
        print("YOU TOOK THE LAST MATCH! THE COMPUTER WINS!")
    print("=" * 60)
