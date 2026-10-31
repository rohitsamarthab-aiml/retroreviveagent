"""
test_game.py - Comprehensive automated tests for Hammurabi modernization.

Uses only the Python standard library unittest. Verifies initial state,
input validations, resource constraints, random events, formulas, historical quirks,
and end-to-end multi-year scenarios with MockRNG.
"""

from io import StringIO
import math
import unittest
from unittest.mock import patch

from game_logic import (
    DefaultRNG,
    EvaluationResult,
    GameState,
    MockRNG,
    TurnDecisions,
    calculate_land_price,
    evaluate_term,
    init_game,
    step_year,
    validate_buy_land,
    validate_feed_people,
    validate_plant_seed,
    validate_sell_land,
)
from main import safe_prompt_int


class TestInitialState(unittest.TestCase):
    """Verifies lines 95-110 and lines 215-260 initial setup."""

    def test_initial_state_values(self) -> None:
        mock_rng = MockRNG([0.5])  # INT(10 * 0.5) = 5 -> land price 22
        state = init_game(rng=mock_rng)

        self.assertEqual(state.year, 1)
        self.assertEqual(state.population, 100)  # 95 starting + 5 immigrants
        self.assertEqual(state.bushels, 2800)
        self.assertEqual(state.acres, 1000)
        self.assertEqual(state.land_price, 22)
        self.assertEqual(state.starved_this_year, 0)
        self.assertEqual(state.starved_total, 0)
        self.assertEqual(state.starved_pct_avg, 0.0)
        self.assertEqual(state.immigrants_this_year, 5)
        self.assertEqual(state.harvest_yield, 3)
        self.assertEqual(state.rats_ate, 200)
        self.assertFalse(state.plague_struck)
        self.assertFalse(state.plague_next_year)
        self.assertFalse(state.is_over)
        self.assertIsNone(state.game_over_reason)

    def test_land_price_bounds(self) -> None:
        # Minimum roll: 0.0 -> INT(10 * 0.0) + 17 = 17
        rng_min = MockRNG([0.0])
        self.assertEqual(calculate_land_price(rng_min), 17)

        # Maximum roll: 0.9999 -> INT(10 * 0.9999) + 17 = 9 + 17 = 26
        rng_max = MockRNG([0.9999])
        self.assertEqual(calculate_land_price(rng_max), 26)


class TestInputValidations(unittest.TestCase):
    """Verifies player order boundary checks and historical quirks."""

    def setUp(self) -> None:
        self.mock_rng = MockRNG([0.5])
        self.state = init_game(rng=self.mock_rng)  # land price 22, bushels 2800, acres 1000, pop 100

    def test_validate_buy_land(self) -> None:
        # Valid purchase: 100 acres at 22 bu/acre = 2200 <= 2800
        res = validate_buy_land(self.state, 100)
        self.assertTrue(res.is_valid)
        self.assertFalse(res.is_fatal)

        # Exact affordability: 2800 // 22 = 127 acres * 22 = 2794 <= 2800
        res = validate_buy_land(self.state, 127)
        self.assertTrue(res.is_valid)

        # Over-budget: 128 acres * 22 = 2816 > 2800
        res = validate_buy_land(self.state, 128)
        self.assertFalse(res.is_valid)
        self.assertFalse(res.is_fatal)
        self.assertIn("THINK AGAIN", res.message)

        # Negative input: fires steward immediately
        res = validate_buy_land(self.state, -1)
        self.assertFalse(res.is_valid)
        self.assertTrue(res.is_fatal)
        self.assertIn("GET YOURSELF ANOTHER STEWARD", res.message)

    def test_validate_sell_land_strict_vs_relaxed(self) -> None:
        # Valid sell: 500 acres
        res = validate_sell_land(self.state, 500, strict_historical=True)
        self.assertTrue(res.is_valid)

        # Selling 999 acres of 1000: valid in both modes
        res = validate_sell_land(self.state, 999, strict_historical=True)
        self.assertTrue(res.is_valid)

        # Selling all 1000 acres:
        # Strict historical (line 342: IF Q < A): rejected
        res_strict = validate_sell_land(self.state, 1000, strict_historical=True)
        self.assertFalse(res_strict.is_valid)
        self.assertIn("THINK AGAIN.  YOU OWN ONLY 1000 ACRES", res_strict.message)

        # Relaxed mode: allowed
        res_relaxed = validate_sell_land(self.state, 1000, strict_historical=False)
        self.assertTrue(res_relaxed.is_valid)

        # Selling more than owned: 1001 acres rejected in both
        res_over = validate_sell_land(self.state, 1001, strict_historical=False)
        self.assertFalse(res_over.is_valid)

        # Negative input: fatal steward dismissal
        res_neg = validate_sell_land(self.state, -5, strict_historical=True)
        self.assertTrue(res_neg.is_fatal)

    def test_validate_feed_people(self) -> None:
        # Valid feeding: 2000 bushels (20 per person for 100 people)
        res = validate_feed_people(self.state, 2000)
        self.assertTrue(res.is_valid)

        # Exact grain in store: 2800
        res = validate_feed_people(self.state, 2800)
        self.assertTrue(res.is_valid)

        # Exceeding grain in store: 2801
        res = validate_feed_people(self.state, 2801)
        self.assertFalse(res.is_valid)
        self.assertIn("THINK AGAIN.  YOU HAVE ONLY", res.message)

        # Negative input: fatal steward dismissal
        res = validate_feed_people(self.state, -20)
        self.assertTrue(res.is_fatal)

    def test_validate_plant_seed_strict_vs_relaxed(self) -> None:
        # Pop = 100, Land = 1000, Grain available = 1000
        # Valid: 500 acres (requires 250 grain, 50 laborers)
        res = validate_plant_seed(
            self.state, 500, available_grain=1000, strict_historical=True
        )
        self.assertTrue(res.is_valid)

        # Exceeding owned land: 1001 acres
        res = validate_plant_seed(
            self.state, 1001, available_grain=1000, strict_historical=True
        )
        self.assertFalse(res.is_valid)
        self.assertIn("YOU OWN ONLY 1000 ACRES", res.message)

        # Exceeding seed grain: 800 acres needs 400 bushels, but only 300 available
        res = validate_plant_seed(
            self.state, 800, available_grain=300, strict_historical=True
        )
        self.assertFalse(res.is_valid)
        self.assertIn("YOU HAVE ONLY\n300 BUSHELS OF GRAIN", res.message)

        # Labor capacity: 100 people * 10 acres/person = 1000 acres
        # Strict historical (line 455: IF D < 10 * P): 1000 is rejected! Max is 999.
        res_strict_999 = validate_plant_seed(
            self.state, 999, available_grain=1000, strict_historical=True
        )
        self.assertTrue(res_strict_999.is_valid)

        res_strict_1000 = validate_plant_seed(
            self.state, 1000, available_grain=1000, strict_historical=True
        )
        self.assertFalse(res_strict_1000.is_valid)
        self.assertIn("BUT YOU HAVE ONLY 100 PEOPLE TO TEND THE FIELDS!", res_strict_1000.message)

        # Relaxed mode: 1000 is allowed
        res_relaxed_1000 = validate_plant_seed(
            self.state, 1000, available_grain=1000, strict_historical=False
        )
        self.assertTrue(res_relaxed_1000.is_valid)

        # Negative input: fatal steward dismissal
        res_neg = validate_plant_seed(
            self.state, -10, available_grain=1000, strict_historical=True
        )
        self.assertTrue(res_neg.is_fatal)


class TestHarvestAndRatsCalculations(unittest.TestCase):
    """Verifies harvest yields, rat parity behavior, and timing."""

    def test_harvest_yield_range(self) -> None:
        # Minimum yield: RND = 0.0 -> INT(0.0 * 5) + 1 = 1
        # Maximum yield: RND = 0.99 -> INT(0.99 * 5) + 1 = 5
        for r_val, expected_yield in [(0.0, 1), (0.21, 2), (0.41, 3), (0.61, 4), (0.99, 5)]:
            # 5 rolls per turn:
            # 1: Harvest yield roll
            # 2: Rat roll (0.1 -> odd 1 -> no rats)
            # 3: Immigrants roll (0.1 -> roll 1)
            # 4: Plague roll (0.5 -> no plague)
            # 5: Next year land price (0.0 -> 17)
            mock_rng = MockRNG([r_val, 0.1, 0.1, 0.5, 0.0])
            state = init_game(rng=MockRNG([0.0]))  # price 17
            decisions = TurnDecisions(plant_acres=100, feed_bushels=2000)
            next_state = step_year(state, decisions, rng=mock_rng)
            self.assertEqual(next_state.harvest_yield, expected_yield)

    def test_rat_infestation_parity_and_timing(self) -> None:
        # Odd rat roll (e.g., C = 1 or 3 or 5): NO rats
        # r = 0.1 -> C = INT(0.1 * 5) + 1 = 1 (Odd)
        mock_rng_odd = MockRNG([0.5, 0.1, 0.1, 0.5, 0.0])
        state = init_game(rng=MockRNG([0.0]))
        decisions = TurnDecisions(feed_bushels=2000, plant_acres=200)
        next_state = step_year(state, decisions, rng=mock_rng_odd)
        self.assertEqual(next_state.rats_ate, 0)

        # Even rat roll: C = 2 (r = 0.25 -> INT(0.25 * 5) + 1 = 2)
        # Stored grain before rat calculation:
        # Initial: 2800 - 2000 (feed) - 100 (seed for 200 acres) = 700 bushels.
        # Rats eat INT(700 / 2) = 350 bushels!
        # Harvest: 200 acres * yield 3 (r=0.5 -> yield 3) = 600 bushels.
        # Final store: 700 - 350 + 600 = 950 bushels.
        mock_rng_even = MockRNG([0.5, 0.25, 0.1, 0.5, 0.0])
        state = init_game(rng=MockRNG([0.0]))
        next_state = step_year(state, decisions, rng=mock_rng_even)
        self.assertEqual(next_state.rats_ate, 350)
        self.assertEqual(next_state.bushels, 950)


class TestImmigrationAndPlague(unittest.TestCase):
    """Verifies immigration formula and 20% plague trigger."""

    def test_immigration_formula(self) -> None:
        # Formula: I = INT(C * (20 * A + S) / P / 100 + 1)
        # A = 1000, Initial S = 2800, Feed = 2000 -> S becomes 800
        # If C = 5 (r = 0.99): (5 * (20000 + 800)) / (100 * 100) + 1 = 104000 / 10000 + 1 = 10.4 + 1 = 11.4 -> 11
        c_val = 0.99  # Roll 4 gives C = 5
        mock_rng = MockRNG([0.5, 0.1, c_val, 0.5, 0.0])
        state = init_game(rng=MockRNG([0.0]))
        decisions = TurnDecisions(feed_bushels=2000, plant_acres=0)
        next_state = step_year(state, decisions, rng=mock_rng)
        self.assertEqual(next_state.immigrants_this_year, 11)

    def test_plague_halving(self) -> None:
        # Plague triggers when plague_r < 0.20
        # Year 1 step rolls plague_r = 0.05 -> Q = INT(10 * (0.1 - 0.3)) = -2 <= 0 (plague next year)
        mock_rng_yr1 = MockRNG([0.5, 0.1, 0.1, 0.05, 0.0])
        state = init_game(rng=MockRNG([0.0]))
        decisions = TurnDecisions(feed_bushels=2000, plant_acres=0)
        state_yr2 = step_year(state, decisions, rng=mock_rng_yr1)
        self.assertTrue(state_yr2.plague_next_year)

        # In Year 2 transition, plague strikes: P is halved!
        # Surviving pop = 100. Immigrants roll 0.1 -> C = 1 -> immigrants = 3.
        # Pop before plague = 100 + 3 = 103.
        # Halved by plague: 103 // 2 = 51.
        mock_rng_yr2 = MockRNG([0.5, 0.1, 0.1, 0.8, 0.0])  # no plague in yr 3
        state_yr3 = step_year(state_yr2, decisions, rng=mock_rng_yr2)
        self.assertTrue(state_yr3.plague_struck)
        self.assertEqual(state_yr3.population, 51)


class TestStarvationAndImpeachment(unittest.TestCase):
    """Verifies feeding math, starvation % running average, and 45% impeachment."""

    def test_underfeeding_and_running_average(self) -> None:
        # Pop 100, feed 1800 bushels -> 90 people fed, 10 starve.
        # D = 10. D <= 0.45 * 100 (10 <= 45), so not impeached.
        # Year 1 starvation: P1 = ((1 - 1)*0 + 10 * 100 / 100) / 1 = 10.0%
        mock_rng = MockRNG([0.5, 0.1, 0.1, 0.5, 0.0])
        state = init_game(rng=MockRNG([0.0]))
        decisions = TurnDecisions(feed_bushels=1800, plant_acres=0)
        next_state = step_year(state, decisions, rng=mock_rng)

        self.assertEqual(next_state.starved_this_year, 10)
        self.assertEqual(next_state.starved_total, 10)
        self.assertAlmostEqual(next_state.starved_pct_avg, 10.0)
        self.assertFalse(next_state.is_over)

    def test_overfeeding_quirk(self) -> None:
        # Pop 100, feed 2200 bushels -> 110 people fed (P < C)
        # Line 550 skips starvation updates: D=0, P1 unchanged
        mock_rng = MockRNG([0.5, 0.1, 0.1, 0.5, 0.0])
        state = init_game(rng=MockRNG([0.0]))
        decisions = TurnDecisions(feed_bushels=2200, plant_acres=0)
        next_state = step_year(state, decisions, rng=mock_rng)

        self.assertEqual(next_state.starved_this_year, 0)
        self.assertEqual(next_state.starved_total, 0)
        self.assertEqual(next_state.starved_pct_avg, 0.0)

    def test_impeachment_trigger_over_45_percent(self) -> None:
        # Pop 100, feed 1000 bushels -> 50 fed, 50 starve (50 > 45) -> IMPEACHED!
        mock_rng = MockRNG([0.5, 0.1, 0.1, 0.5])
        state = init_game(rng=MockRNG([0.0]))
        decisions = TurnDecisions(feed_bushels=1000, plant_acres=0)
        next_state = step_year(state, decisions, rng=mock_rng)

        self.assertTrue(next_state.is_over)
        self.assertEqual(next_state.game_over_reason, "IMPEACHED")
        self.assertEqual(next_state.starved_this_year, 50)


class TestFinalEvaluationTiers(unittest.TestCase):
    """Verifies performance review logic and historical outcome texts."""

    def test_tier_1_fink(self) -> None:
        # P1 > 33 or L < 7
        state = GameState(
            year=11,
            population=100,
            bushels=1000,
            acres=600,  # L = 600 / 100 = 6.0 < 7
            land_price=20,
            starved_this_year=0,
            starved_total=50,
            starved_pct_avg=35.0,  # P1 > 33
            immigrants_this_year=5,
            harvest_yield=3,
            rats_ate=0,
            plague_struck=False,
            plague_next_year=False,
            is_over=True,
            game_over_reason="COMPLETED",
        )
        res = evaluate_term(state)
        self.assertEqual(res.tier, 1)
        self.assertIn("NATIONAL FINK", res.message)

    def test_tier_2_nero(self) -> None:
        # P1 > 10 or L < 9 (and not Tier 1)
        state = GameState(
            year=11,
            population=100,
            bushels=1000,
            acres=800,  # L = 8.0 (< 9)
            land_price=20,
            starved_this_year=0,
            starved_total=20,
            starved_pct_avg=15.0,  # P1 = 15.0 (<= 33, > 10)
            immigrants_this_year=5,
            harvest_yield=3,
            rats_ate=0,
            plague_struck=False,
            plague_next_year=False,
            is_over=True,
            game_over_reason="COMPLETED",
        )
        res = evaluate_term(state)
        self.assertEqual(res.tier, 2)
        self.assertIn("NERO AND IVAN IV", res.message)

    def test_tier_3_mediocre_assassination(self) -> None:
        # P1 > 3 or L < 10 (and not Tier 1 or 2)
        state = GameState(
            year=11,
            population=100,
            bushels=1000,
            acres=950,  # L = 9.5 (< 10)
            land_price=20,
            starved_this_year=0,
            starved_total=5,
            starved_pct_avg=5.0,  # P1 = 5.0 (<= 10, > 3)
            immigrants_this_year=5,
            harvest_yield=3,
            rats_ate=0,
            plague_struck=False,
            plague_next_year=False,
            is_over=True,
            game_over_reason="COMPLETED",
        )
        # Roll for assassinated: 0.5 * 100 * 0.8 = 40
        mock_rng = MockRNG([0.5])
        res = evaluate_term(state, rng=mock_rng)
        self.assertEqual(res.tier, 3)
        self.assertIn("ASSASSINATED", res.message)
        self.assertIn("40 PEOPLE", res.message)

    def test_tier_4_fantastic_charlemagne(self) -> None:
        # P1 <= 3 and L >= 10
        state = GameState(
            year=11,
            population=100,
            bushels=3000,
            acres=1200,  # L = 12.0 (>= 10)
            land_price=20,
            starved_this_year=0,
            starved_total=0,
            starved_pct_avg=1.0,  # P1 <= 3
            immigrants_this_year=5,
            harvest_yield=3,
            rats_ate=0,
            plague_struck=False,
            plague_next_year=False,
            is_over=True,
            game_over_reason="COMPLETED",
        )
        res = evaluate_term(state)
        self.assertEqual(res.tier, 4)
        self.assertIn("CHARLEMANGE, DISRAELI, AND", res.message)


class TestMultiYearSimulation(unittest.TestCase):
    """End-to-end 10-year simulation under deterministic MockRNG."""

    def test_full_ten_year_game(self) -> None:
        # We supply deterministic numbers for 10 years
        # Year 1 init takes 1 roll (land price)
        # Years 1-9 take 5 rolls each:
        # [harvest_yield, rat_roll, imm_roll, plague_roll, next_land_price]
        # Year 10 takes 4 rolls:
        # [harvest_yield, rat_roll, imm_roll, plague_roll]
        # Total rolls = 1 + 9 * 5 + 4 = 50 rolls.
        rolls = [0.5]  # yr 1 price: 22
        for _ in range(9):
            rolls.extend([0.6, 0.1, 0.2, 0.5, 0.5])  # yield 4, no rats, 5 immigrants, no plague, next price 22
        rolls.extend([0.6, 0.1, 0.2, 0.5])  # yr 10

        rng = MockRNG(rolls)
        state = init_game(rng=rng)

        for year in range(1, 11):
            self.assertEqual(state.year, year)
            self.assertFalse(state.is_over)
            # Feed population fully, plant safe acreage
            food = state.population * 20
            planted = min(state.acres, state.population * 9)
            decisions = TurnDecisions(
                buy_acres=0,
                sell_acres=0,
                feed_bushels=food,
                plant_acres=planted,
            )
            state = step_year(state, decisions, rng=rng)

        self.assertEqual(state.year, 11)
        self.assertTrue(state.is_over)
        self.assertEqual(state.game_over_reason, "COMPLETED")
        self.assertEqual(state.starved_total, 0)
        self.assertEqual(state.starved_pct_avg, 0.0)


class TestSafeInputHandling(unittest.TestCase):
    """Verifies that safe_prompt_int gracefully reprompts on malformed inputs."""

    def test_safe_prompt_valid_int(self) -> None:
        with patch("builtins.input", return_value="  42  "):
            self.assertEqual(safe_prompt_int("PROMPT: "), 42)

    def test_safe_prompt_invalid_string_recovery(self) -> None:
        # User enters 'abc', then '', then '15'
        inputs = ["abc", "", "15"]
        with patch("builtins.input", side_effect=inputs):
            with patch("sys.stdout", new_callable=StringIO) as mock_out:
                val = safe_prompt_int("PROMPT: ")
                self.assertEqual(val, 15)
                output = mock_out.getvalue()
                self.assertIn("?REDO FROM START", output)

    def test_safe_prompt_eof_handling(self) -> None:
        with patch("builtins.input", side_effect=EOFError):
            with patch("sys.stdout", new_callable=StringIO):
                self.assertIsNone(safe_prompt_int("PROMPT: "))


class TestPresentationLayer(unittest.TestCase):
    """Verifies optional cosmetic visual presentation, ASCII scenes, and animations."""

    def test_colorize_plain_text_fallback(self) -> None:
        from presentation import Colors, VisualConfig, colorize

        config_no_color = VisualConfig(enabled=False, use_color=False)
        self.assertEqual(colorize("Hello", Colors.RED, config_no_color), "Hello")

    def test_colorize_when_enabled(self) -> None:
        from presentation import Colors, VisualConfig, colorize

        config_color = VisualConfig(enabled=True, use_color=True)
        res = colorize("Hello", Colors.RED, config_color)
        self.assertTrue(res.startswith(Colors.RED))
        self.assertTrue(res.endswith(Colors.RESET))
        self.assertIn("Hello", res)

    def test_visual_config_detect_flags(self) -> None:
        from presentation import VisualConfig

        cfg_forced = VisualConfig.detect(force_animate=True, force_color="always")
        self.assertTrue(cfg_forced.enabled)
        self.assertTrue(cfg_forced.use_color)

        cfg_disabled = VisualConfig.detect(force_animate=False, force_color="never")
        self.assertFalse(cfg_disabled.enabled)
        self.assertFalse(cfg_disabled.use_color)

    def test_render_city_scene_elements(self) -> None:
        from presentation import VisualConfig, render_city_scene

        state = init_game(rng=MockRNG([0.0]))
        config = VisualConfig(enabled=True, use_color=False)
        scene = render_city_scene(state, config)

        self.assertIn("ANCIENT SUMERIA", scene)
        self.assertIn("TEMPLE", scene)
        self.assertIn("SILOS", scene)
        self.assertIn("CITIZENS", scene)
        self.assertIn("FARMLAND", scene)

    def test_event_animations_output(self) -> None:
        from presentation import (
            VisualConfig,
            animate_harvest,
            animate_plague,
            animate_rats,
            print_evaluation_banner,
        )

        config_instant = VisualConfig(enabled=True, use_color=False, frame_delay=0.0)

        # Harvest animation output
        with patch("sys.stdout", new_callable=StringIO) as out:
            animate_harvest(500, 4, 2000, config_instant)
            val = out.getvalue()
            self.assertIn("Reapers gathering", val)
            self.assertIn("Bountiful harvest: +2000 bushels", val)

        # Rats animation output
        with patch("sys.stdout", new_callable=StringIO) as out:
            animate_rats(350, config_instant)
            val = out.getvalue()
            self.assertIn("Rats devoured 350 bushels", val)

        # Plague animation output
        with patch("sys.stdout", new_callable=StringIO) as out:
            animate_plague(config_instant)
            val = out.getvalue()
            self.assertIn("A HORRIBLE PLAGUE STRUCK!", val)

        # Evaluation banners
        for tier in [1, 2, 3, 4]:
            with patch("sys.stdout", new_callable=StringIO) as out:
                print_evaluation_banner(tier, config_instant)
                val = out.getvalue()
                self.assertTrue(len(val) > 0)


if __name__ == "__main__":
    unittest.main()
