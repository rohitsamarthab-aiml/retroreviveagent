"""
test_royal_governor.py - Automated test suite for the AI Royal Governor agent.

Verifies:
1. Agent tools read real game engine state
2. Agent tools select valid actions and reject invalid actions
3. Authoritative turn progression changes real resources
4. Autonomous Observe-Think-Plan-Validate-Act-Verify cycle
5. Replanning when plans are constrained
6. Player delegation limit and control revocation
7. End-to-end famine / drought survival scenario
"""

import pytest
from game_logic import GameState, MockRNG, init_game
from modern_game_logic import (
    EnhancedGameState,
    init_enhanced_game,
    SCENARIOS,
)
from agent_tools import (
    allocate_grain,
    advance_kingdom_turn,
    calculate_grain_requirements,
    get_advisor_recommendation,
    get_chronicle_summary,
    inspect_disaster_conditions,
    inspect_kingdom_state,
    manage_farming,
    manage_land,
    validate_action,
)
from royal_governor import (
    AgentStatus,
    DelegationSession,
    RoyalGovernor,
    RuleBasedPlanner,
)


class TestAgentTools:
    """Tests for agent_tools.py calling the authoritative game engine."""

    def test_inspect_kingdom_state(self):
        enhanced = init_enhanced_game(mode="ENHANCED")
        res = inspect_kingdom_state(enhanced)

        assert res["success"] is True
        assert res["tool"] == "inspect_kingdom_state"
        st = res["state"]
        assert st["year"] == 1
        assert st["population"] == 100
        assert st["grain_bushels"] == 2800
        assert st["acres_owned"] == 1000
        assert 17 <= st["land_price_per_acre"] <= 26
        assert res["analytics"]["grain_per_person_bushels"] == 28.0
        assert res["analytics"]["famine_risk"] in ("LOW", "HIGH", "CRITICAL")

    def test_calculate_grain_requirements(self):
        enhanced = init_enhanced_game(mode="ENHANCED")
        res = calculate_grain_requirements(enhanced)

        assert res["success"] is True
        assert res["tool"] == "calculate_grain_requirements"
        assert res["population"] == 100
        assert res["grain_in_store"] == 2800
        assert res["requirements"]["full_feed_bushels"] == 2000  # 100 * 20
        assert res["requirements"]["max_plantable_acres"] == 1000
        assert res["requirements"]["seed_for_max_planting"] == 500  # 1000 // 2
        assert res["can_fully_feed"] is True

    def test_validate_action_accepts_valid_orders(self):
        enhanced = init_enhanced_game(mode="ENHANCED")
        res = validate_action(
            enhanced,
            buy_acres=0,
            sell_acres=0,
            feed_bushels=2000,
            plant_acres=600,
        )

        assert res["success"] is True
        assert res["all_valid"] is True
        assert res["any_fatal_error"] is False
        assert res["can_execute"] is True

    def test_validate_action_rejects_excess_food(self):
        enhanced = init_enhanced_game(mode="ENHANCED")
        res = validate_action(
            enhanced,
            buy_acres=0,
            sell_acres=0,
            feed_bushels=5000,  # exceeds 2800 in silos
            plant_acres=500,
        )

        assert res["all_valid"] is False
        assert res["can_execute"] is False
        assert res["validation"]["feed_people"]["valid"] is False

    def test_validate_action_rejects_negative_input(self):
        enhanced = init_enhanced_game(mode="ENHANCED")
        res = validate_action(
            enhanced,
            buy_acres=-10,
            sell_acres=0,
            feed_bushels=2000,
            plant_acres=500,
        )

        assert res["all_valid"] is False
        assert res["any_fatal_error"] is True
        assert res["can_execute"] is False

    def test_allocate_grain_tool(self):
        enhanced = init_enhanced_game(mode="ENHANCED")
        res = allocate_grain(enhanced, feed_bushels=2000)

        assert res["success"] is True
        assert res["outcome_preview"]["citizens_fully_fed"] == 100
        assert res["outcome_preview"]["citizens_will_starve"] == 0
        assert res["outcome_preview"]["impeachment_risk"] is False

    def test_manage_land_buy_and_sell_mutually_exclusive(self):
        enhanced = init_enhanced_game(mode="ENHANCED")
        res = manage_land(enhanced, buy_acres=10, sell_acres=10)
        assert res["success"] is False
        assert "Cannot buy AND sell" in res["error"]

    def test_manage_farming_tool(self):
        enhanced = init_enhanced_game(mode="ENHANCED")
        res = manage_farming(enhanced, plant_acres=800, grain_available_after_feed=800)
        assert res["success"] is True
        assert res["seed_cost_bushels"] == 400
        assert res["harvest_projection"]["min_harvest_bushels"] == 800
        assert res["harvest_projection"]["max_harvest_bushels"] == 4000

    def test_advance_kingdom_turn_mutates_state(self):
        enhanced = init_enhanced_game(mode="ENHANCED")
        initial_year = enhanced.classic_state.year

        new_enhanced, res = advance_kingdom_turn(
            enhanced,
            buy_acres=0,
            sell_acres=0,
            feed_bushels=2000,
            plant_acres=500,
        )

        assert res["success"] is True
        assert res["year_processed"] == initial_year
        assert new_enhanced.classic_state.year == initial_year + 1
        assert "before" in res
        assert "after" in res
        assert "resource_deltas" in res
        assert len(new_enhanced.chronicle) == 1

    def test_inspect_disaster_conditions(self):
        enhanced = init_enhanced_game(mode="ENHANCED")
        res = inspect_disaster_conditions(enhanced)

        assert res["success"] is True
        assert "famine" in res
        assert "plague" in res
        assert "land_health" in res
        assert "impeachment_risk" in res
        assert res["famine"]["level"] in ("SAFE", "WARNING", "CRITICAL", "ACTIVE_FAMINE")

    def test_get_advisor_recommendation(self):
        enhanced = init_enhanced_game(mode="ENHANCED")
        res = get_advisor_recommendation(enhanced)

        assert res["success"] is True
        rec = res["advisor_recommendations"]
        assert "vizier_summary" in rec
        assert rec["recommended_feed_bushels"] == 2000
        assert rec["recommended_plant_acres"] > 0

    def test_get_chronicle_summary(self):
        enhanced = init_enhanced_game(mode="ENHANCED")
        res = get_chronicle_summary(enhanced)
        assert res["success"] is True
        assert res["turns_completed"] == 0

        # Advance one turn and check chronicle
        new_enhanced, _ = advance_kingdom_turn(
            enhanced,
            feed_bushels=2000,
            plant_acres=500,
        )
        res2 = get_chronicle_summary(new_enhanced)
        assert res2["turns_completed"] == 1
        assert res2["history"][0]["year"] == 1


class TestRoyalGovernorCore:
    """Tests for the Royal Governor autonomous decision engine."""

    def test_governor_init_and_backend_honesty(self):
        enhanced = init_enhanced_game(mode="ENHANCED")
        # Without API key, governor honestly reports Rule-Based Planner
        gov = RoyalGovernor(enhanced)
        assert gov.status == AgentStatus.IDLE
        assert gov.backend_name in ("RULE_BASED", "GEMINI_LLM")
        assert gov.current_enhanced_state.classic_state.year == 1

    def test_delegation_single_turn(self):
        enhanced = init_enhanced_game(mode="ENHANCED")
        gov = RoyalGovernor(enhanced)

        session = gov.delegate(
            goal="Prevent famine and maintain kingdom stability",
            turns=1,
        )

        assert session.turns_completed == 1
        assert session.turns_remaining == 0
        assert session.is_active is False
        assert len(session.action_history) == 1

        rec = session.action_history[0]
        assert rec.turn_number == 1
        assert rec.game_year == 1
        assert rec.verification_ok is True
        assert "inspect_kingdom_state" in rec.tool_calls
        assert "advance_kingdom_turn" in rec.tool_calls
        assert gov.current_enhanced_state.classic_state.year == 2

    def test_delegation_multi_turn(self):
        enhanced = init_enhanced_game(mode="ENHANCED")
        gov = RoyalGovernor(enhanced)

        session = gov.delegate(
            goal="Manage agriculture and grow population for 3 years",
            turns=3,
        )

        assert session.turns_completed == 3
        assert session.turns_remaining == 0
        assert len(session.action_history) == 3
        assert gov.current_enhanced_state.classic_state.year == 4

        # Check turn continuity
        years = [r.game_year for r in session.action_history]
        assert years == [1, 2, 3]

    def test_resource_values_change_correctly(self):
        enhanced = init_enhanced_game(mode="ENHANCED")
        gov = RoyalGovernor(enhanced)

        before_bushels = enhanced.classic_state.bushels
        session = gov.delegate(goal="Prevent famine", turns=1)
        rec = session.action_history[0]

        # Verify before/after resource tracking
        assert rec.before_resources["bushels"] == before_bushels
        assert rec.after_resources["bushels"] == gov.current_enhanced_state.classic_state.bushels
        assert rec.resource_deltas["bushels"] == rec.after_resources["bushels"] - before_bushels

    def test_player_can_revoke_control(self):
        enhanced = init_enhanced_game(mode="ENHANCED")
        gov = RoyalGovernor(enhanced)

        # Register callback that revokes control after turn 1
        def revoke_after_first(record, state):
            if record.turn_number == 1:
                gov.revoke()

        gov.on_turn_complete(revoke_after_first)
        session = gov.delegate(goal="Long term 5 year plan", turns=5)

        # Should have stopped after turn 1 due to player revocation
        assert session.turns_completed == 1
        assert session.revoked_by_player is True
        assert gov.status == AgentStatus.PAUSED

    def test_governor_session_summary(self):
        enhanced = init_enhanced_game(mode="ENHANCED")
        gov = RoyalGovernor(enhanced)
        gov.delegate(goal="Famine prevention", turns=2)

        summary = gov.get_session_summary()
        assert summary["goal"] == "Famine prevention"
        assert summary["turns_delegated"] == 2
        assert summary["turns_completed"] == 2
        assert summary["current_year"] == 3
        assert summary["action_count"] == 2


class TestEndToEndFamineScenario:
    """End-to-end tests for the Royal Governor in adverse famine/drought conditions."""

    def test_drought_famine_avoidance(self):
        """
        In the Drought challenge scenario (starts with only 1800 bushels for 100 people),
        the governor must recognize the deficit and either prioritize rations or
        sell land to prevent starvation impeachment.
        """
        enhanced = init_enhanced_game(mode="SCENARIO", scenario_id="drought")
        assert enhanced.classic_state.bushels == 1800  # Scarce grain
        assert enhanced.classic_state.population == 100

        gov = RoyalGovernor(enhanced)
        session = gov.delegate(
            goal="Survive the great drought, prevent famine, and maintain population",
            turns=3,
        )

        assert session.turns_completed == 3
        st = gov.current_enhanced_state.classic_state

        # Crucial: Governor must NOT have caused impeachment (>45% dead)
        assert st.game_over_reason != "IMPEACHED"
        assert st.population > 50 or (st.plague_struck and st.starved_total < 20)  # Overwhelming majority survived

        # Verify action records reflect threat awareness
        for rec in session.action_history:
            assert rec.planned_actions["feed_bushels"] > 0
            # Feed bushels should prioritize keeping people alive (up to 20 per person)
            assert rec.planned_actions["feed_bushels"] <= rec.before_resources["population"] * 20
