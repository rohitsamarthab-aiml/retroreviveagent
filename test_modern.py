"""
test_modern.py - Automated tests for Enhanced Mode, Scenarios, Advisors, and Persistence.
"""

import os
import tempfile
import unittest

from game_logic import MockRNG, TurnDecisions
from modern_game_logic import (
    SCENARIOS,
    EnhancedGameState,
    delete_save_game,
    get_advisor_advice,
    init_enhanced_game,
    load_game_state,
    save_game_state,
    step_enhanced_year,
)


class TestEnhancedScenariosAndAdvisors(unittest.TestCase):
    """Verifies scenario definitions, objectives, and advisor guidance."""

    def test_scenario_initializations(self) -> None:
        for scen_id, defn in SCENARIOS.items():
            state = init_enhanced_game(mode="SCENARIO", scenario_id=scen_id, rng=MockRNG([0.0]))
            self.assertEqual(state.mode, "SCENARIO")
            self.assertEqual(state.scenario_id, scen_id)
            self.assertEqual(state.classic_state.population, defn.starting_population)
            self.assertEqual(state.classic_state.bushels, defn.starting_bushels)
            self.assertEqual(state.classic_state.acres, defn.starting_acres)
            self.assertEqual(state.scenario_status, "IN_PROGRESS")

    def test_advisor_advice_calculations(self) -> None:
        state = init_enhanced_game(rng=MockRNG([0.0]))  # price 17 (very cheap)
        advice = get_advisor_advice(state.classic_state)

        # 100 population requires 2000 bushels
        self.assertEqual(advice.recommended_feed, 2000)
        # Pop 100 can cultivate up to 999 acres (labor limit 10*P - 1)
        self.assertEqual(advice.recommended_plant, 999)
        self.assertIn("VERY CHEAP", advice.land_price_rating)
        self.assertIn("2000 bushels", advice.granary_master)
        self.assertIn("stable and prosperous", advice.vizier)

    def test_chronicle_tracking_across_years(self) -> None:
        rng = MockRNG([0.5, 0.1, 0.1, 0.5, 0.0])
        state = init_enhanced_game(rng=MockRNG([0.0]))
        decisions = TurnDecisions(feed_bushels=2000, plant_acres=400)

        next_state = step_enhanced_year(state, decisions, rng=rng)
        self.assertEqual(len(next_state.chronicle), 1)
        entry = next_state.chronicle[0]
        self.assertEqual(entry.year, 1)
        self.assertEqual(entry.fed_bushels, 2000)
        self.assertEqual(entry.planted_acres, 400)
        self.assertEqual(entry.starved, 0)

    def test_scenario_victory_condition(self) -> None:
        # Drought target year is 5.
        # We start with land price 20, sell 50 acres to fund rations and plant 500 acres.
        state = init_enhanced_game(mode="SCENARIO", scenario_id="drought", rng=MockRNG([0.3]))
        self.assertEqual(state.scenario_id, "drought")

        # Year 1: sell 50 acres at 20 bu/acre, feed 2000, plant 500
        rng = MockRNG([0.8, 0.1, 0.1, 0.8, 0.0])  # yield 5, no rats
        decisions = TurnDecisions(sell_acres=50, feed_bushels=2000, plant_acres=500)
        state = step_enhanced_year(state, decisions, rng=rng)

        # Years 2 to 4
        for yr in range(2, 5):
            rng = MockRNG([0.8, 0.1, 0.1, 0.8, 0.0])
            decisions = TurnDecisions(feed_bushels=state.classic_state.population * 20, plant_acres=500)
            state = step_enhanced_year(state, decisions, rng=rng)

        # 5th year: reaches target year 5
        rng = MockRNG([0.8, 0.1, 0.1, 0.8, 0.0])
        decisions = TurnDecisions(feed_bushels=state.classic_state.population * 20, plant_acres=500)
        final_state = step_enhanced_year(state, decisions, rng=rng)

        self.assertTrue(final_state.classic_state.is_over)
        self.assertEqual(final_state.scenario_status, "VICTORY")
        self.assertIn("VICTORY", final_state.status_message)


    def test_advisor_emergency_land_sale_during_famine(self) -> None:
        # Drought scenario: 100 pop requires 2000 bushels, but kingdom only starts with 1800 bushels
        state = init_enhanced_game(mode="SCENARIO", scenario_id="drought", rng=MockRNG([0.3]))
        st = state.classic_state
        self.assertEqual(st.bushels, 1800)
        self.assertEqual(st.population, 100)
        self.assertEqual(st.land_price, 20)  # 17 + int(0.3 * 10) = 20

        advice = get_advisor_advice(st)
        self.assertIn("emergency grain", advice.vizier.lower())
        self.assertIn("Sell 10 acres", advice.granary_master)
        self.assertIn("raise 200 bushels", advice.granary_master)
        # 200 deficit / 20 bu/acre = 10 acres emergency sale recommended
        self.assertEqual(advice.recommended_sell, 10)
        self.assertEqual(advice.recommended_buy, 0)

    def test_advisor_land_bargain_purchase(self) -> None:
        # Kingdom with surplus grain and cheap land (price 17)
        state = init_enhanced_game(rng=MockRNG([0.0]))  # price 17
        import dataclasses
        st = dataclasses.replace(state.classic_state, bushels=5000)
        advice = get_advisor_advice(st)
        self.assertEqual(advice.recommended_sell, 0)
        self.assertGreater(advice.recommended_buy, 0)
        self.assertIn("Bargain land opportunity", advice.surveyor)


class TestSaveAndResume(unittest.TestCase):
    """Verifies clean JSON serialization and state restoration."""

    def setUp(self) -> None:
        self.temp_file = tempfile.mktemp(suffix=".json")

    def tearDown(self) -> None:
        if os.path.exists(self.temp_file):
            os.remove(self.temp_file)

    def test_save_and_load_roundtrip(self) -> None:
        state = init_enhanced_game(mode="ENHANCED", rng=MockRNG([0.5]))
        decisions = TurnDecisions(feed_bushels=2000, plant_acres=300)
        advanced_state = step_enhanced_year(state, decisions, rng=MockRNG([0.6, 0.1, 0.2, 0.5, 0.5]))

        # Save state
        saved = save_game_state(advanced_state, filepath=self.temp_file)
        self.assertTrue(saved)
        self.assertTrue(os.path.exists(self.temp_file))

        # Load state
        loaded = load_game_state(filepath=self.temp_file)
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.mode, advanced_state.mode)
        self.assertEqual(loaded.classic_state.year, advanced_state.classic_state.year)
        self.assertEqual(loaded.classic_state.population, advanced_state.classic_state.population)
        self.assertEqual(loaded.classic_state.bushels, advanced_state.classic_state.bushels)
        self.assertEqual(loaded.classic_state.acres, advanced_state.classic_state.acres)
        self.assertEqual(len(loaded.chronicle), 1)

    def test_load_nonexistent_file(self) -> None:
        res = load_game_state("non_existent_file_xyz123.json")
        self.assertIsNone(res)

    def test_load_corrupt_file(self) -> None:
        with open(self.temp_file, "w") as f:
            f.write("{corrupt json content...")
        res = load_game_state(self.temp_file)
        self.assertIsNone(res)

    def test_delete_save_game(self) -> None:
        with open(self.temp_file, "w") as f:
            f.write("{}")
        self.assertTrue(os.path.exists(self.temp_file))
        deleted = delete_save_game(self.temp_file)
        self.assertTrue(deleted)
        self.assertFalse(os.path.exists(self.temp_file))


if __name__ == "__main__":
    unittest.main()

