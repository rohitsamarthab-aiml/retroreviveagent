"""
games/23_matches/test_engine.py - Automated tests for 23 Matches rule engine and AI.
"""

import unittest
from .engine import (
    MatchesGameState,
    init_game,
    validate_move,
    make_move,
    get_computer_move,
)


class TestMatchesInitialState(unittest.TestCase):
    """Verifies default and custom initial state generation."""

    def test_default_initial_state(self) -> None:
        state = init_game()
        self.assertEqual(state.matches_remaining, 23)
        self.assertEqual(state.current_player, "HUMAN")
        self.assertFalse(state.game_over)
        self.assertIsNone(state.winner)
        self.assertIsNone(state.loser)
        self.assertEqual(len(state.history), 0)
        self.assertEqual(state.ai_mode, "CLASSIC_1978")

    def test_custom_initial_state(self) -> None:
        state = init_game(initial_matches=21, first_player="COMPUTER", ai_mode="OPTIMAL")
        self.assertEqual(state.matches_remaining, 21)
        self.assertEqual(state.current_player, "COMPUTER")
        self.assertEqual(state.ai_mode, "OPTIMAL")

    def test_invalid_initialization_parameters(self) -> None:
        with self.assertRaises(ValueError):
            init_game(initial_matches=0)
        with self.assertRaises(ValueError):
            init_game(first_player="ALIEN")
        with self.assertRaises(ValueError):
            init_game(ai_mode="IMPOSSIBLE")


class TestMatchesMoveValidation(unittest.TestCase):
    """Verifies move bounds, integer validation, and state-preservation on rejection."""

    def setUp(self) -> None:
        self.state = init_game(initial_matches=23)

    def test_valid_moves(self) -> None:
        for val in (1, 2, 3):
            ok, err = validate_move(self.state, val)
            self.assertTrue(ok)
            self.assertIsNone(err)

    def test_reject_out_of_bounds_numbers(self) -> None:
        for val in (-5, -1, 0, 4, 10):
            ok, err = validate_move(self.state, val)
            self.assertFalse(ok)
            self.assertIsNotNone(err)

    def test_reject_non_integers(self) -> None:
        for val in ("two", "3.0", 2.5, None, True, False, []):
            ok, err = validate_move(self.state, val)
            self.assertFalse(ok)
            self.assertIn("integer", err.lower())

    def test_reject_exceeding_remaining_matches(self) -> None:
        state_2 = MatchesGameState(matches_remaining=2, current_player="HUMAN")
        ok, err = validate_move(state_2, 3)
        self.assertFalse(ok)
        self.assertIn("only 2 matches remain", err.lower())

        state_1 = MatchesGameState(matches_remaining=1, current_player="HUMAN")
        ok_2, _ = validate_move(state_1, 2)
        ok_3, _ = validate_move(state_1, 3)
        self.assertFalse(ok_2)
        self.assertFalse(ok_3)

    def test_reject_move_when_game_over(self) -> None:
        state_over = MatchesGameState(matches_remaining=0, game_over=True)
        ok, err = validate_move(state_over, 1)
        self.assertFalse(ok)
        self.assertIn("already over", err.lower())


class TestMatchesGameProgressionAndMisere(unittest.TestCase):
    """Verifies turn advancement and Misère Nim end conditions."""

    def test_legal_move_decrements_matches(self) -> None:
        state = init_game(initial_matches=23)
        next_st = make_move(state, 3)
        self.assertEqual(next_st.matches_remaining, 20)
        self.assertEqual(next_st.current_player, "COMPUTER")
        self.assertEqual(next_st.last_move, 3)
        self.assertEqual(next_st.last_mover, "HUMAN")
        self.assertEqual(len(next_st.history), 1)
        self.assertEqual(next_st.history[0].matches_taken, 3)
        self.assertEqual(next_st.history[0].matches_remaining, 20)

    def test_human_takes_last_match_loses(self) -> None:
        state = MatchesGameState(matches_remaining=1, current_player="HUMAN")
        end_st = make_move(state, 1)
        self.assertTrue(end_st.game_over)
        self.assertEqual(end_st.matches_remaining, 0)
        self.assertEqual(end_st.loser, "HUMAN")
        self.assertEqual(end_st.winner, "COMPUTER")

    def test_computer_takes_last_match_loses(self) -> None:
        state = MatchesGameState(matches_remaining=1, current_player="COMPUTER")
        end_st = make_move(state, 1)
        self.assertTrue(end_st.game_over)
        self.assertEqual(end_st.matches_remaining, 0)
        self.assertEqual(end_st.loser, "COMPUTER")
        self.assertEqual(end_st.winner, "HUMAN")


class TestMatchesComputerAI(unittest.TestCase):
    """Verifies Classic 1978 and Optimal AI decision making."""

    def test_classic_1978_mirrors_to_four(self) -> None:
        # If human took 1, computer takes 3
        st1 = MatchesGameState(matches_remaining=22, current_player="COMPUTER", last_mover="HUMAN", last_move=1, ai_mode="CLASSIC_1978")
        self.assertEqual(get_computer_move(st1), 3)

        # If human took 2, computer takes 2
        st2 = MatchesGameState(matches_remaining=21, current_player="COMPUTER", last_mover="HUMAN", last_move=2, ai_mode="CLASSIC_1978")
        self.assertEqual(get_computer_move(st2), 2)

        # If human took 3, computer takes 1
        st3 = MatchesGameState(matches_remaining=20, current_player="COMPUTER", last_mover="HUMAN", last_move=3, ai_mode="CLASSIC_1978")
        self.assertEqual(get_computer_move(st3), 1)

    def test_optimal_ai_targets_multiples_of_four_plus_one(self) -> None:
        # From 23 matches, (23 - 1) % 4 == 2 -> computer takes 2 to reach 21
        st = MatchesGameState(matches_remaining=23, current_player="COMPUTER", ai_mode="OPTIMAL")
        self.assertEqual(get_computer_move(st), 2)

        # From 22 matches, (22 - 1) % 4 == 1 -> computer takes 1 to reach 21
        st_22 = MatchesGameState(matches_remaining=22, current_player="COMPUTER", ai_mode="OPTIMAL")
        self.assertEqual(get_computer_move(st_22), 1)

        # From 20 matches, (20 - 1) % 4 == 3 -> computer takes 3 to reach 17
        st_20 = MatchesGameState(matches_remaining=20, current_player="COMPUTER", ai_mode="OPTIMAL")
        self.assertEqual(get_computer_move(st_20), 3)

    def test_endgame_critical_decisions(self) -> None:
        # With 4 matches, taking 3 leaves 1 match for opponent -> win!
        st_4 = MatchesGameState(matches_remaining=4, current_player="COMPUTER", ai_mode="OPTIMAL")
        self.assertEqual(get_computer_move(st_4), 3)

        # With 3 matches, taking 2 leaves 1 match for opponent -> win!
        st_3 = MatchesGameState(matches_remaining=3, current_player="COMPUTER", ai_mode="OPTIMAL")
        self.assertEqual(get_computer_move(st_3), 2)

        # With 2 matches, taking 1 leaves 1 match for opponent -> win!
        st_2 = MatchesGameState(matches_remaining=2, current_player="COMPUTER", ai_mode="OPTIMAL")
        self.assertEqual(get_computer_move(st_2), 1)

        # With 1 match, forced to take 1 and lose
        st_1 = MatchesGameState(matches_remaining=1, current_player="COMPUTER", ai_mode="OPTIMAL")
        self.assertEqual(get_computer_move(st_1), 1)


class TestRepeatableGameScenarios(unittest.TestCase):
    """Runs complete end-to-end games demonstrating deterministic repeatable scenarios."""

    def test_human_perfect_play_wins_against_classic_ai(self) -> None:
        """
        In 1978 Bob Albrecht rules (23 matches, human first, computer does 4 - Z):
        Turn 1: Human takes 2 -> 21 remaining.
        Computer takes 4 - 2 = 2 -> 19 remaining.
        Turn 2: Human takes 2 -> 17 remaining.
        Computer takes 4 - 2 = 2 -> 15 remaining.
        Turn 3: Human takes 2 -> 13 remaining.
        Computer takes 4 - 2 = 2 -> 11 remaining.
        Turn 4: Human takes 2 -> 9 remaining.
        Computer takes 4 - 2 = 2 -> 7 remaining.
        Turn 5: Human takes 2 -> 5 remaining.
        Computer takes 4 - 2 = 2 -> 3 remaining.
        Turn 6: Human takes 2 -> 1 remaining!
        Computer is forced to take the last match and LOSES!
        """
        st = init_game(initial_matches=23, ai_mode="CLASSIC_1978")
        while not st.game_over:
            if st.current_player == "HUMAN":
                # Always take 2
                take = min(2, st.matches_remaining)
                st = make_move(st, take)
            else:
                comp_move = get_computer_move(st)
                st = make_move(st, comp_move)

        self.assertTrue(st.game_over)
        self.assertEqual(st.winner, "HUMAN")
        self.assertEqual(st.loser, "COMPUTER")

    def test_state_isolation_on_restart(self) -> None:
        st1 = init_game(initial_matches=23)
        st1 = make_move(st1, 3)
        self.assertEqual(st1.matches_remaining, 20)

        # Fresh game must be completely independent
        st2 = init_game(initial_matches=23)
        self.assertEqual(st2.matches_remaining, 23)
        self.assertEqual(len(st2.history), 0)
        self.assertEqual(st1.matches_remaining, 20)


if __name__ == "__main__":
    unittest.main()
