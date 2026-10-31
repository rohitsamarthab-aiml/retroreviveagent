"""
ui_pygame.py - Graphical desktop application for RetroRevive: Hammurabi Reimagined.

Features:
- Full 1280x720 responsive desktop interface with aspect-ratio letterboxing
- CLASSIC MODE: 100% faithful to 1978 Microsoft BASIC Hammurabi rules
- ENHANCED MODE: Interactive Tutorial, Royal Advisors, Chronicle, and Scenarios
- Animated ancient Sumerian kingdom landscape, flowing river, and particles
- Complete interactive controls: Number entry, steppers, Min/Max buttons, Modals
- Save & Resume game persistence via standard-library JSON
"""

import math
import os
import sys
from typing import Callable, Dict, List, Optional, Tuple
import pygame

from game_logic import (
    DefaultRNG,
    GameState,
    RandomProvider,
    TurnDecisions,
    evaluate_term,
    init_game,
    step_year,
    validate_buy_land,
    validate_feed_people,
    validate_plant_seed,
    validate_sell_land,
)
from modern_game_logic import (
    SCENARIOS,
    AdvisorAdvice,
    EnhancedGameState,
    delete_save_game,
    get_advisor_advice,
    init_enhanced_game,
    load_game_state,
    save_game_state,
    step_enhanced_year,
)
from auth_manager import AuthManager
from ui_auth import AuthModal
from ui_characters import RoyalAdvisorPortrait, RoyalHammurabi
from ui_cinematics import CinematicDirector
from ui_districts import DistrictManager
from ui_theme import (
    DecreePreviewData,
    FontManager,
    Palette,
    SoundSynthesizer,
    UIButton,
    UIDecreePreview,
    UIModal,
    UINumberInput,
    UIToast,
)
from ui_world import WorldRenderer
from ui_military import MilitaryDashboard
from ui_agriculture import AgriculturalDashboard
from ui_video_creator import VideoCreatorPanel
from ui_day_night import DayNightRenderer


BASE_WIDTH = 1280
BASE_HEIGHT = 720


class GameApp:
    """Main Pygame application controller managing state, screens, and window scaling."""

    def __init__(
        self,
        start_fullscreen: bool = False,
        on_exit_to_library: Optional[Callable[[], None]] = None,
        shared_window: Optional[pygame.Surface] = None,
        auth: Optional[AuthManager] = None,
        show_auth_modal: bool = False,
    ) -> None:
        pygame.init()
        SoundSynthesizer.init()

        self.on_exit_to_library = on_exit_to_library
        self.screen_width = BASE_WIDTH
        self.screen_height = BASE_HEIGHT

        if shared_window is not None:
            self.window = shared_window
        else:
            flags = pygame.RESIZABLE
            if start_fullscreen:
                flags |= pygame.FULLSCREEN
            self.window = pygame.display.set_mode((self.screen_width, self.screen_height), flags)

        pygame.display.set_caption("RetroRevive: Hammurabi — The Living Empire")

        self.canvas = pygame.Surface((BASE_WIDTH, BASE_HEIGHT))
        self.clock = pygame.time.Clock()
        self.is_running = True

        # Global Settings
        self.animations_enabled = True
        self.sound_enabled = True
        self.animation_speed = 1.0

        # World Scene Renderer & Characters
        self.world = WorldRenderer()
        self.day_night = DayNightRenderer()
        self.hammurabi = RoyalHammurabi(scale=1.0)
        self.advisor_portrait = RoyalAdvisorPortrait()
        self.cinematics = CinematicDirector()

        # Ministry Screens & Cinematic Studio
        self.military_dashboard = MilitaryDashboard(screen_w=BASE_WIDTH, screen_h=BASE_HEIGHT, on_return=self._return_to_main_menu)
        self.agriculture_dashboard = AgriculturalDashboard(on_return=self._return_to_main_menu)
        self.video_creator = VideoCreatorPanel(on_return=self._return_to_main_menu)

        # Authentication & Profile Manager
        self.auth = auth or AuthManager()
        self.auth_modal: Optional[AuthModal] = None
        if show_auth_modal:
            self._open_profile_modal()

        # Kingdom Districts & Camera Manager
        self.districts = DistrictManager()
        self.is_command_deck_collapsed = False

        # Navigation State
        self.current_screen = "MAIN_MENU"  # MAIN_MENU, CLASSIC, ENHANCED, SCENARIOS, INSTRUCTIONS, GAME_OVER
        self.active_modal: Optional[UIModal] = None
        self.active_toast: Optional[UIToast] = None

        # Game Instances
        self.classic_state: Optional[GameState] = None
        self.enhanced_state: Optional[EnhancedGameState] = None
        self.active_mode = "CLASSIC"  # "CLASSIC" or "ENHANCED"
        self.game_over_result: Optional[dict] = None
        self.last_turn_summary: Optional[dict] = None
        self.selected_menu_idx: int = 0

        self._is_updating_inputs = False

        # Turn Control Inputs
        self._init_turn_inputs()

        # Build Screen UI Buttons
        self._init_menu_buttons()
        self._init_scenario_buttons()
        self._init_instruction_buttons()
        self._init_game_over_buttons()

        # Tutorial step
        self.tutorial_step = 0

    def _init_scenario_buttons(self) -> None:
        """Creates persistent buttons for scenario challenges screen."""
        self.btn_scenarios_back = UIButton((50, 30, 120, 38), "← BACK", self._return_to_main_menu)
        self.scenario_play_buttons: Dict[str, UIButton] = {}
        card_w, card_h = 270, 520
        start_x = 55
        card_y = 110
        for i, key in enumerate(SCENARIOS.keys()):
            cx = start_x + i * (card_w + 25)
            self.scenario_play_buttons[key] = UIButton(
                (cx + 25, card_y + card_h - 60, 220, 44),
                "PLAY SCENARIO",
                lambda k=key: self._start_scenario(k),
                primary=True
            )

    def _init_instruction_buttons(self) -> None:
        """Creates persistent buttons for tutorial instructions screen."""
        panel_w, panel_h = 920, 580
        px, py = (BASE_WIDTH - panel_w) // 2, 70
        self.btn_instructions_back = UIButton((px + 30, py + 20, 100, 36), "← MENU", self._return_to_main_menu)
        self.btn_tutorial_prev = UIButton((px + 280, py + panel_h - 65, 140, 42), "← PREV", self._prev_tutorial_step)
        self.btn_tutorial_next = UIButton((px + 500, py + panel_h - 65, 140, 42), "NEXT →", self._next_tutorial_step, primary=True)

    def _init_game_over_buttons(self) -> None:
        """Creates persistent buttons for game over screen."""
        panel_w, panel_h = 760, 520
        px, py = (BASE_WIDTH - panel_w) // 2, 70
        self.btn_game_over_replay = UIButton((px + 140, py + panel_h - 70, 220, 48), "PLAY AGAIN", self._start_classic_game, primary=True)
        self.btn_game_over_menu = UIButton((px + 400, py + panel_h - 70, 220, 48), "MAIN MENU", self._return_to_main_menu, color_scheme="lapis")

    def _init_turn_inputs(self) -> None:
        """Initializes numeric input widgets for land, feeding, and planting with live preview."""
        input_w = 345
        input_h = 108
        col1_x = 28
        col2_x = 390
        row1_y = 462
        row2_y = 578

        # Buy Land (Col 1, Row 1)
        self.input_buy = UINumberInput((col1_x, row1_y, input_w, input_h), label="BUY LAND", unit_label="ACRES", on_change=self._on_input_changed)
        # Sell Land (Col 1, Row 2)
        self.input_sell = UINumberInput((col1_x, row2_y, input_w, input_h), label="SELL LAND", unit_label="ACRES", on_change=self._on_input_changed)
        # Feed Citizens (Col 2, Row 1)
        self.input_feed = UINumberInput((col2_x, row1_y, input_w, input_h), label="FEED CITIZENS", unit_label="BUSHELS", on_change=self._on_input_changed)
        # Plant Crops (Col 2, Row 2)
        self.input_plant = UINumberInput((col2_x, row2_y, input_w, input_h), label="PLANT SEED", unit_label="ACRES", on_change=self._on_input_changed)

        # Royal Scribe's Decree Preview Ledger (Col 3: x = 752, width = 290, height = 224)
        self.preview_widget = UIDecreePreview((752, 462, 290, 224))

        # Action Buttons (Col 4: x = 1058, width = 196)
        self.btn_execute_turn = UIButton((1058, 560, 196, 68), "ENACT DECREE", self._on_execute_turn, font_size=19, primary=True)
        self.btn_advisors = UIButton((1058, 462, 196, 44), "ROYAL ADVISORS", self._open_advisors_modal, font_size=15, color_scheme="lapis")
        self.btn_chronicle = UIButton((1058, 511, 196, 44), "CHRONICLE LOG", self._open_chronicle_modal, font_size=15)
        self.btn_reset_turn = UIButton((1058, 638, 196, 38), "RESET INPUTS", self._reset_turn_inputs_for_new_turn, font_size=14, color_scheme="sand")

        # In-Game Header Buttons (Top-Right)
        uname = self.auth.get_current_username()
        self.btn_profile = UIButton((710, 14, 135, 36), f"RULER: {uname[:10]}", self._open_profile_modal, font_size=13, color_scheme="gold")
        self.btn_save = UIButton((855, 14, 90, 36), "SAVES", lambda: self._open_save_slots_modal("SAVE"), font_size=14, color_scheme="lapis")
        self.btn_toggle_view = UIButton((955, 14, 115, 36), "PANORAMA", self._toggle_command_deck, font_size=13)
        self.btn_pause = UIButton((1080, 14, 85, 36), "MENU", self._open_pause_modal, font_size=14)
        self.btn_goals = UIButton((610, 14, 90, 36), "GOALS", self._open_scenario_goals_modal, font_size=13, color_scheme="gold")

        # Floating quick controls in panorama mode
        self.btn_quick_enact = UIButton((1060, 664, 190, 42), "ENACT DECREE", self._on_execute_turn, font_size=16, primary=True)
        self.btn_expand_deck = UIButton((890, 664, 160, 42), "▲ EXPAND DECK", self._toggle_command_deck, font_size=13, color_scheme="lapis")

    def _init_menu_buttons(self) -> None:
        """Creates main menu buttons with robust spacing and save file detection."""
        bx = (BASE_WIDTH - 380) // 2
        has_save = os.path.exists("retrorevive_save.json")

        quit_label = "RETURN TO LIBRARY" if self.on_exit_to_library else "QUIT GAME"
        if has_save:
            start_y = 216
            spacing = 49
            btn_h = 40
            self.menu_buttons = [
                UIButton((bx, start_y, 380, btn_h), "PLAY CLASSIC MODE (1978)", self._start_classic_game, primary=True),
                UIButton((bx, start_y + spacing, 380, btn_h), "PLAY ENHANCED MODE", self._start_enhanced_game, color_scheme="lapis"),
                UIButton((bx, start_y + spacing * 2, 380, btn_h), "RESUME SAVED GAME", self._resume_game_action, color_scheme="gold"),
                UIButton((bx, start_y + spacing * 3, 380, btn_h), "SCENARIO CHALLENGES", self._open_scenarios_screen, color_scheme="sand"),
                UIButton((bx, start_y + spacing * 4, 380, btn_h), "HOW TO PLAY & TUTORIAL", self._open_instructions_screen, color_scheme="sand"),
                UIButton((bx, start_y + spacing * 5, 380, btn_h), "SETTINGS & AUDIO", self._open_settings_modal, color_scheme="sand"),
                UIButton((bx, start_y + spacing * 6, 380, btn_h), quit_label, self.quit, color_scheme="crimson"),
            ]
        else:
            start_y = 230
            spacing = 54
            btn_h = 44
            self.menu_buttons = [
                UIButton((bx, start_y, 380, btn_h), "PLAY CLASSIC MODE (1978)", self._start_classic_game, primary=True),
                UIButton((bx, start_y + spacing, 380, btn_h), "PLAY ENHANCED MODE", self._start_enhanced_game, color_scheme="lapis"),
                UIButton((bx, start_y + spacing * 2, 380, btn_h), "SCENARIO CHALLENGES", self._open_scenarios_screen, color_scheme="sand"),
                UIButton((bx, start_y + spacing * 3, 380, btn_h), "HOW TO PLAY & TUTORIAL", self._open_instructions_screen, color_scheme="sand"),
                UIButton((bx, start_y + spacing * 4, 380, btn_h), "SETTINGS & AUDIO", self._open_settings_modal, color_scheme="sand"),
                UIButton((bx, start_y + spacing * 5, 380, btn_h), quit_label, self.quit, color_scheme="crimson"),
            ]

        self.btn_watch_prologue = UIButton((960, 435, 270, 40), "WATCH ROYAL PROLOGUE", self.cinematics.trigger_prologue, primary=True)
        self.btn_military = UIButton((960, 485, 270, 40), "⚔️ MILITARY COMMAND", self._open_military_screen, color_scheme="crimson")
        self.btn_agriculture = UIButton((960, 535, 270, 40), "🌾 AGRICULTURAL MINISTRY", self._open_agriculture_screen, color_scheme="gold")
        self.btn_studio = UIButton((960, 585, 270, 40), "🎬 CINEMATIC STUDIO", self._open_video_creator_screen, color_scheme="lapis")
        # Top header auth buttons for main menu
        self.btn_menu_profile = UIButton((960, 20, 280, 40), f"SOVEREIGN: {self.auth.get_current_username()[:16]}", self._open_profile_modal, font_size=13, color_scheme="gold")
        self.btn_menu_saves = UIButton((660, 20, 280, 40), "MULTI-SLOT SAVES", lambda: self._open_save_slots_modal("LOAD"), font_size=13, color_scheme="lapis")

    def _open_military_screen(self) -> None:
        self.active_modal = None
        self.active_toast = None
        self.current_screen = "MILITARY"
        SoundSynthesizer.play("click")

    def _open_agriculture_screen(self) -> None:
        self.active_modal = None
        self.active_toast = None
        self.current_screen = "AGRICULTURE"
        SoundSynthesizer.play("harvest")

    def _open_video_creator_screen(self) -> None:
        self.active_modal = None
        self.active_toast = None
        self.current_screen = "VIDEO_CREATOR"
        SoundSynthesizer.play("bell")

    def _on_input_changed(self, _: int) -> None:
        """Updates UI limits dynamically when inputs change without infinite recursion."""
        if self._is_updating_inputs:
            return
        self._is_updating_inputs = True
        try:
            st = self._get_current_game_state()
            if not st:
                return

            buy = self.input_buy.value
            sell = self.input_sell.value

            # In classic mode, buying and selling land in the same year is mutually exclusive
            if self.active_mode == "CLASSIC":
                if buy > 0:
                    self.input_sell.is_enabled = False
                    self.input_sell.label = "SELL LAND (Buying Land)"
                    if sell != 0:
                        self.input_sell.set_value(0)
                        sell = 0
                    self.input_buy.is_enabled = True
                    self.input_buy.label = "BUY LAND"
                    available_grain = max(0, st.bushels - buy * st.land_price)
                elif sell > 0:
                    self.input_buy.is_enabled = False
                    self.input_buy.label = "BUY LAND (Selling Land)"
                    if buy != 0:
                        self.input_buy.set_value(0)
                        buy = 0
                    self.input_sell.is_enabled = True
                    self.input_sell.label = "SELL LAND (Acres)"
                    self.input_sell.max_value = max(0, st.acres - 1)
                    available_grain = max(0, st.bushels + sell * st.land_price)
                else:
                    self.input_buy.is_enabled = True
                    self.input_buy.label = "BUY LAND"
                    self.input_sell.is_enabled = True
                    self.input_sell.label = "SELL LAND (Acres)"
                    self.input_sell.max_value = max(0, st.acres - 1)
                    available_grain = st.bushels
            else:
                self.input_buy.is_enabled = True
                self.input_buy.label = "BUY LAND"
                self.input_sell.is_enabled = True
                self.input_sell.label = "SELL LAND (Acres)"
                self.input_sell.max_value = max(0, st.acres)
                available_grain = max(0, st.bushels - buy * st.land_price + sell * st.land_price)

            self.input_buy.max_value = max(0, st.bushels // max(1, st.land_price))
            self.input_feed.max_value = available_grain

            grain_after_feed = max(0, available_grain - self.input_feed.value)
            max_plant_by_seed = grain_after_feed * 2
            max_plant_by_labor = st.population * 10 - 1
            max_plant_by_land = st.acres + buy - sell
            self.input_plant.max_value = max(0, min(max_plant_by_land, max_plant_by_labor, max_plant_by_seed))
        finally:
            self._is_updating_inputs = False

    def _get_current_game_state(self) -> Optional[GameState]:
        if self.active_mode == "ENHANCED" and self.enhanced_state:
            return self.enhanced_state.classic_state
        return self.classic_state

    # -----------------------------------------------------------------------
    # Game Launch & Actions
    # -----------------------------------------------------------------------

    def _start_classic_game(self) -> None:
        SoundSynthesizer.play("harvest")
        self.active_mode = "CLASSIC"
        self.classic_state = init_game()
        self.current_screen = "GAMEPLAY"
        self._reset_turn_inputs_for_new_turn()
        self.show_toast("Welcome, Hammurabi. Govern Sumeria for a 10-year term!")

    def _start_enhanced_game(self) -> None:
        SoundSynthesizer.play("harvest")
        self.active_mode = "ENHANCED"
        self.enhanced_state = init_enhanced_game(mode="ENHANCED")
        self.current_screen = "GAMEPLAY"
        self._reset_turn_inputs_for_new_turn()
        self.show_toast("Enhanced Mode: Royal Advisors and Chronicle active.")

    def _start_scenario(self, scen_id: str) -> None:
        SoundSynthesizer.play("harvest")
        self.active_mode = "ENHANCED"
        self.enhanced_state = init_enhanced_game(mode="SCENARIO", scenario_id=scen_id)
        self.current_screen = "GAMEPLAY"
        self._reset_turn_inputs_for_new_turn()
        scen_title = SCENARIOS[scen_id].title
        self.show_toast(f"Scenario Started: {scen_title}")

    def _reset_turn_inputs_for_new_turn(self) -> None:
        st = self._get_current_game_state()
        if not st:
            return

        self.input_buy.set_value(0)
        self.input_sell.set_value(0)

        # Default feeding to exact requirement (20 per person)
        exact_feed = st.population * 20
        self.input_feed.set_value(min(st.bushels, exact_feed))

        # Default planting to sustainable safe amount
        grain_left = max(0, st.bushels - self.input_feed.value)
        safe_plant = min(st.acres, st.population * 8, grain_left * 2)
        self.input_plant.set_value(safe_plant)

        # Reset active status and error messages
        for inp in [self.input_buy, self.input_sell, self.input_feed, self.input_plant]:
            inp.is_active = False
            inp.error_message = None

        self._on_input_changed(0)

    def _on_execute_turn(self) -> None:
        st = self._get_current_game_state()
        if not st:
            return

        # 1. Parse all 4 inputs (validating integers, empty strings, letters, decimals)
        ok_buy, buy, err_buy = self.input_buy.parse_integer()
        ok_sell, sell, err_sell = self.input_sell.parse_integer()
        ok_feed, feed, err_feed = self.input_feed.parse_integer()
        ok_plant, plant, err_plant = self.input_plant.parse_integer()

        # Reject malformed inputs safely without modifying game state
        if not ok_buy:
            self.input_buy.error_message = err_buy
            self.show_toast(err_buy)
            SoundSynthesizer.play("warning")
            return
        if not ok_sell:
            self.input_sell.error_message = err_sell
            self.show_toast(err_sell)
            SoundSynthesizer.play("warning")
            return
        if not ok_feed:
            self.input_feed.error_message = err_feed
            self.show_toast(err_feed)
            SoundSynthesizer.play("warning")
            return
        if not ok_plant:
            self.input_plant.error_message = err_plant
            self.show_toast(err_plant)
            SoundSynthesizer.play("warning")
            return

        # Clear error tags if syntax was valid
        self.input_buy.error_message = None
        self.input_sell.error_message = None
        self.input_feed.error_message = None
        self.input_plant.error_message = None

        # 2. Check for negative numbers (Historical Classic Rule: lines 321, 341, 412, 442)
        if buy < 0 or sell < 0 or feed < 0 or plant < 0:
            SoundSynthesizer.play("warning")
            fired_state = GameState(
                year=st.year, population=st.population, bushels=st.bushels, acres=st.acres,
                land_price=st.land_price, starved_this_year=0, starved_total=st.starved_total,
                starved_pct_avg=st.starved_pct_avg, immigrants_this_year=0, harvest_yield=0,
                rats_ate=0, plague_struck=False, plague_next_year=False, is_over=True,
                game_over_reason="STEWARD_FIRED"
            )
            self._handle_game_over(fired_state)
            return

        # 3. In Classic Mode, buying land forbids selling land in the same year
        if self.active_mode == "CLASSIC" and buy > 0 and sell > 0:
            msg = "HAMURABI: You cannot both buy and sell land in the same year!"
            self.input_buy.error_message = msg
            self.input_sell.error_message = msg
            self.show_toast(msg)
            SoundSynthesizer.play("warning")
            return

        # 4. Validate Buy Land
        if buy > 0:
            res_buy = validate_buy_land(st, buy)
            if not res_buy.is_valid:
                self.input_buy.error_message = res_buy.message
                self.show_toast(res_buy.message.replace("\n", " "))
                SoundSynthesizer.play("warning")
                return

        # 5. Validate Sell Land
        if sell > 0:
            res_sell = validate_sell_land(st, sell, strict_historical=True)
            if not res_sell.is_valid:
                self.input_sell.error_message = res_sell.message
                self.show_toast(res_sell.message.replace("\n", " "))
                SoundSynthesizer.play("warning")
                return

        # 6. Validate Feed People
        grain_after_land = st.bushels - buy * st.land_price if buy > 0 else st.bushels + sell * st.land_price
        acres_after_land = st.acres + buy - sell
        temp_state = GameState(
            year=st.year, population=st.population, bushels=grain_after_land,
            acres=acres_after_land, land_price=st.land_price, starved_this_year=0,
            starved_total=st.starved_total, starved_pct_avg=st.starved_pct_avg,
            immigrants_this_year=0, harvest_yield=0, rats_ate=0, plague_struck=False,
            plague_next_year=False, is_over=False
        )
        res_feed = validate_feed_people(temp_state, feed)
        if not res_feed.is_valid:
            self.input_feed.error_message = res_feed.message
            self.show_toast(res_feed.message.replace("\n", " "))
            SoundSynthesizer.play("warning")
            return

        # 7. Validate Plant Seed
        grain_after_feed = grain_after_land - feed
        res_plant = validate_plant_seed(temp_state, plant, available_grain=grain_after_feed, strict_historical=True)
        if not res_plant.is_valid:
            self.input_plant.error_message = res_plant.message
            self.show_toast(res_plant.message.replace("\n", " "))
            SoundSynthesizer.play("warning")
            return

        # 8. All orders verified valid -> Advance simulation!
        decisions = TurnDecisions(buy_acres=buy, sell_acres=sell, feed_bushels=feed, plant_acres=plant)
        prior_pop = st.population
        prior_bushels = st.bushels
        prior_acres = st.acres

        # Advance Simulation
        if self.active_mode == "ENHANCED" and self.enhanced_state:
            self.enhanced_state = step_enhanced_year(self.enhanced_state, decisions)
            new_st = self.enhanced_state.classic_state
        else:
            self.classic_state = step_year(self.classic_state, decisions)
            new_st = self.classic_state

        if hasattr(self, "day_night"):
            self.day_night.trigger_day_advance()

        # Compute summary metrics for annual report card
        pop_delta = new_st.population - prior_pop
        grain_delta = new_st.bushels - prior_bushels
        acres_delta = new_st.acres - prior_acres
        self.last_turn_summary = {
            "year": st.year,
            "starved": new_st.starved_this_year,
            "immigrants": new_st.immigrants_this_year,
            "plague": new_st.plague_struck,
            "yield": new_st.harvest_yield,
            "harvest_total": plant * new_st.harvest_yield,
            "rats_ate": new_st.rats_ate,
            "pop_delta": pop_delta,
            "grain_delta": grain_delta,
            "acres_delta": acres_delta,
        }

        # Sound and particle triggers
        if new_st.plague_struck:
            SoundSynthesizer.play("plague")
        elif new_st.rats_ate > 0:
            SoundSynthesizer.play("warning")
            self.world.trigger_rat_particles(30)
        elif plant > 0:
            SoundSynthesizer.play("gong")
            self.world.trigger_harvest_particles(35)
        else:
            SoundSynthesizer.play("harvest")

        # Check Game Over
        if new_st.is_over:
            self._handle_game_over(new_st)
            return

        self._reset_turn_inputs_for_new_turn()
        self.show_toast(f"Year {new_st.year} has arrived in Sumeria.")

        # Trigger genuine cinematic sequence if animations are enabled
        if self.animations_enabled:
            self.cinematics.trigger_turn_events(new_st)

    def _handle_game_over(self, state: GameState) -> None:
        delete_save_game()

        is_scenario = (
            self.active_mode == "ENHANCED"
            and self.enhanced_state is not None
            and self.enhanced_state.mode == "SCENARIO"
        )
        scen = (
            SCENARIOS.get(self.enhanced_state.scenario_id)
            if (is_scenario and self.enhanced_state and self.enhanced_state.scenario_id in SCENARIOS)
            else None
        )

        if state.game_over_reason == "STEWARD_FIRED":
            self.game_over_result = {
                "tier": 1,
                "title": "RULE TERMINATED: STEWARD DISMISSED",
                "acres_per_person": state.acres / state.population if state.population > 0 else 0.0,
                "avg_starved_pct": state.starved_pct_avg,
                "total_starved": state.starved_total,
                "message": "HAMURABI:  I CANNOT DO WHAT YOU WISH.\nGET YOURSELF ANOTHER STEWARD!!!!!",
                "state": state,
                "is_scenario": is_scenario,
                "scenario": scen,
            }
            SoundSynthesizer.play("warning")
        elif state.game_over_reason == "IMPEACHED":
            self.game_over_result = {
                "tier": 1,
                "title": "RULE TERMINATED: IMPEACHMENT",
                "acres_per_person": state.acres / state.population if state.population > 0 else 0.0,
                "avg_starved_pct": state.starved_pct_avg,
                "total_starved": state.starved_total,
                "message": (
                    f"YOU STARVED {state.starved_this_year} PEOPLE IN ONE YEAR!!!\n"
                    "DUE TO THIS EXTREME MISMANAGEMENT YOU HAVE NOT ONLY\n"
                    "BEEN IMPEACHED AND THROWN OUT OF OFFICE BUT YOU HAVE\n"
                    "ALSO BEEN DECLARED NATIONAL FINK!!!!"
                ),
                "state": state,
                "is_scenario": is_scenario,
                "scenario": scen,
            }
            SoundSynthesizer.play("warning")
        elif state.game_over_reason == "SCENARIO_WON":
            scen_title = scen.title if scen else "Scenario"
            self.game_over_result = {
                "tier": 4,
                "title": f"SCENARIO VICTORY: {scen_title.upper()}",
                "acres_per_person": state.acres / state.population if state.population > 0 else 0.0,
                "avg_starved_pct": state.starved_pct_avg,
                "total_starved": state.starved_total,
                "message": (
                    self.enhanced_state.status_message
                    if (self.enhanced_state and self.enhanced_state.status_message)
                    else f"A MAGNIFICENT TRIUMPH! You achieved all objectives for '{scen_title}'!"
                ),
                "state": state,
                "is_scenario": True,
                "scenario": scen,
            }
            SoundSynthesizer.play("bell")
            self.world.trigger_victory_fireworks(60)
        elif state.game_over_reason == "SCENARIO_LOST":
            scen_title = scen.title if scen else "Scenario"
            self.game_over_result = {
                "tier": 1,
                "title": f"SCENARIO DEFEAT: {scen_title.upper()}",
                "acres_per_person": state.acres / state.population if state.population > 0 else 0.0,
                "avg_starved_pct": state.starved_pct_avg,
                "total_starved": state.starved_total,
                "message": (
                    self.enhanced_state.status_message
                    if (self.enhanced_state and self.enhanced_state.status_message)
                    else f"Term concluded without achieving all requirements for '{scen_title}'."
                ),
                "state": state,
                "is_scenario": True,
                "scenario": scen,
            }
            SoundSynthesizer.play("warning")
        else:
            eval_res = evaluate_term(state)
            self.game_over_result = {
                "tier": eval_res.tier,
                "title": "TEN-YEAR GOVERNANCE EVALUATION",
                "acres_per_person": eval_res.acres_per_person,
                "avg_starved_pct": eval_res.avg_starved_pct,
                "total_starved": eval_res.total_starved,
                "message": eval_res.message,
                "state": state,
                "is_scenario": False,
                "scenario": None,
            }
            if eval_res.tier == 4:
                SoundSynthesizer.play("bell")
                self.world.trigger_victory_fireworks(50)
            else:
                SoundSynthesizer.play("warning")
        self.current_screen = "GAME_OVER"

    def _save_game_action(self) -> None:
        if self.active_mode == "ENHANCED" and self.enhanced_state:
            if save_game_state(self.enhanced_state):
                self.show_toast("Game successfully saved to retrorevive_save.json!")
                SoundSynthesizer.play("coin")
            else:
                self.show_toast("Failed to save game.")
        else:
            # Wrap classic state to save
            wrap = EnhancedGameState(classic_state=self.classic_state, mode="CLASSIC")
            if save_game_state(wrap):
                self.show_toast("Classic game progress saved!")
                SoundSynthesizer.play("coin")

    def _resume_game_action(self) -> None:
        loaded = load_game_state()
        if loaded:
            if loaded.mode == "CLASSIC":
                self.active_mode = "CLASSIC"
                self.classic_state = loaded.classic_state
            else:
                self.active_mode = "ENHANCED"
                self.enhanced_state = loaded
            self.current_screen = "GAMEPLAY"
            self._reset_turn_inputs_for_new_turn()
            self.show_toast(f"Game resumed from Year {self._get_current_game_state().year}!")
            SoundSynthesizer.play("harvest")
        else:
            self.show_toast("No valid save file found.")

    def _open_profile_modal(self) -> None:
        prof = self.auth.get_current_profile()
        initial_mode = "PROFILE" if (prof and not prof.is_guest) else "LOGIN"
        self.auth_modal = AuthModal(self.auth, on_success=self._on_auth_success, initial_mode=initial_mode)

    def _open_save_slots_modal(self, action: str = "SAVE") -> None:
        self.auth_modal = AuthModal(self.auth, on_success=self._on_auth_success, initial_mode="SAVES")
        self.auth_modal.set_save_context(
            action=action,
            state_getter=self._get_state_for_save_dict,
            on_load=self._on_load_state_from_dict,
        )

    def _on_auth_success(self) -> None:
        uname = self.auth.get_current_username()
        if hasattr(self, "btn_profile"):
            self.btn_profile.text = f"RULER: {uname[:10]}"
        if hasattr(self, "btn_menu_profile"):
            self.btn_menu_profile.text = f"SOVEREIGN: {uname[:16]}"

    def _toggle_command_deck(self) -> None:
        self.is_command_deck_collapsed = not self.is_command_deck_collapsed
        if hasattr(self, "btn_toggle_view"):
            self.btn_toggle_view.text = "EXPAND" if self.is_command_deck_collapsed else "PANORAMA"
        SoundSynthesizer.play("click")

    def _get_state_for_save_dict(self) -> Optional[dict]:
        st = self._get_current_game_state()
        if not st:
            return None
        return {
            "mode": self.active_mode,
            "year": st.year,
            "population": st.population,
            "bushels": st.bushels,
            "acres": st.acres,
            "land_price": st.land_price,
            "starved_this_year": st.starved_this_year,
            "immigrants_this_year": st.immigrants_this_year,
            "harvest_yield": st.harvest_yield,
            "rats_ate": st.rats_ate,
            "starved_total": st.starved_total,
            "starved_pct_avg": st.starved_pct_avg,
            "plague_struck": st.plague_struck,
            "game_over": st.is_over,
            "game_over_reason": st.game_over_reason,
            "enhanced_mode": self.enhanced_state.mode if self.enhanced_state else "CLASSIC",
            "scenario_id": self.enhanced_state.scenario_id if self.enhanced_state else None,
        }

    def _on_load_state_from_dict(self, data: dict) -> None:
        from game_logic import GameState
        mode = data.get("mode", "CLASSIC")
        st = GameState(
            year=data.get("year", 1),
            starved_this_year=data.get("starved_this_year", 0),
            immigrants_this_year=data.get("immigrants_this_year", 5),
            population=data.get("population", 100),
            harvest_yield=data.get("harvest_yield", 3),
            bushels=data.get("bushels", 2800),
            rats_ate=data.get("rats_ate", 200),
            acres=data.get("acres", 1000),
            land_price=data.get("land_price", 19),
            starved_total=data.get("starved_total", 0),
            starved_pct_avg=data.get("starved_pct_avg", 0.0),
            plague_struck=data.get("plague_struck", False),
            is_over=data.get("game_over", False),
            game_over_reason=data.get("game_over_reason", None),
        )
        if mode == "CLASSIC":
            self.active_mode = "CLASSIC"
            self.classic_state = st
            self.enhanced_state = None
        else:
            self.active_mode = "ENHANCED"
            self.enhanced_state = EnhancedGameState(
                classic_state=st,
                mode=data.get("enhanced_mode", "CLASSIC"),
                scenario_id=data.get("scenario_id", None),
            )
        self.current_screen = "GAMEPLAY"
        self._reset_turn_inputs_for_new_turn()
        self.show_toast(f"Empire restored from parchment scroll (Year {st.year})!")

    def show_toast(self, message: str) -> None:
        self.active_toast = UIToast(message)

    # -----------------------------------------------------------------------
    # Modals & Dialogs
    # -----------------------------------------------------------------------

    def _open_advisors_modal(self) -> None:
        st = self._get_current_game_state()
        if not st:
            return
        advice = get_advisor_advice(st)
        lines = [
            f"1. THE GRAND VIZIER (Economy & Famine Assessment):",
            f"   \"{advice.vizier}\"",
            "",
            f"2. THE MASTER OF GRANARIES (Grain Rations & Silo Safety):",
            f"   \"{advice.granary_master}\"",
            f"   Recommended Rations: {advice.recommended_feed} bushels (20 bu/citizen)",
            "",
            f"3. THE ROYAL SURVEYOR (Land Trade & Cultivation):",
            f"   \"{advice.surveyor}\"",
            f"   Land Valuation: [{advice.land_price_rating}] at {st.land_price} bu/acre | Recommended Crop: {advice.recommended_plant} acres",
        ]
        if advice.recommended_sell > 0:
            lines.append(f"   Emergency Land Sale: Recommend selling {advice.recommended_sell} acres at {st.land_price} bu/ac to fund sustenance.")
        elif advice.recommended_buy > 0:
            lines.append(f"   Land Investment: Recommend purchasing {advice.recommended_buy} acres at bargain rate.")

        def apply_advice():
            if advice.recommended_sell > 0:
                self.input_buy.set_value(0)
                self.input_sell.set_value(advice.recommended_sell)
            elif advice.recommended_buy > 0:
                self.input_sell.set_value(0)
                self.input_buy.set_value(advice.recommended_buy)
            else:
                self.input_buy.set_value(0)
                self.input_sell.set_value(0)
            self.input_feed.set_value(advice.recommended_feed)
            self.input_plant.set_value(advice.recommended_plant)
            self.active_modal = None
            self.show_toast("Royal council recommendations applied to decree.")

        buttons = [
            ("APPLY ADVICE", apply_advice),
            ("CLOSE", lambda: setattr(self, "active_modal", None)),
        ]
        self.active_modal = UIModal("THE ROYAL COUNCIL OF SUMERIA", lines, buttons, width=860, height=520)

    def _open_chronicle_modal(self) -> None:
        if not (self.active_mode == "ENHANCED" and self.enhanced_state):
            self.show_toast("Chronicle Log is available in Enhanced Mode.")
            return

        entries = self.enhanced_state.chronicle
        if not entries:
            lines = ["No historical records yet. Enact decrees to record kingdom history."]
        else:
            lines = [f"{'YR':<4} {'POP':<6} {'GRAIN':<7} {'LAND':<7} {'HARVEST':<9} {'RATS':<7} {'STARVED':<8} {'EVENTS'}"]
            lines.append("-" * 72)
            total_starved = sum(e.starved for e in entries)
            for e in entries[-9:]:
                evt = "PLAGUE" if e.plague else ("FAMINE" if e.starved > 0 else "PEACE")
                trade_str = f"+{e.bought_acres}" if e.bought_acres > 0 else (f"-{e.sold_acres}" if e.sold_acres > 0 else "")
                land_display = f"{e.acres}{'(' + trade_str + ')' if trade_str else ''}"
                lines.append(
                    f"{e.year:<4} {e.population_end:<6} {e.bushels:<7} {land_display:<7} "
                    f"+{e.harvested_total:<8} -{e.rats_ate:<6} {e.starved:<8} {evt}"
                )
            lines.append("-" * 72)
            lines.append(f"Cumulative Chronicle: Total Starved: {total_starved} | Recorded Years: {len(entries)}")

        buttons = [("CLOSE", lambda: setattr(self, "active_modal", None))]
        self.active_modal = UIModal("SUMERIAN ROYAL CHRONICLE", lines, buttons, width=820, height=480, monospace=True)

    def _open_scenario_goals_modal(self) -> None:
        if not (self.active_mode == "ENHANCED" and self.enhanced_state and self.enhanced_state.scenario_id in SCENARIOS):
            return
        scen = SCENARIOS[self.enhanced_state.scenario_id]
        st = self._get_current_game_state()
        lines = [
            f"Scenario: {scen.title.upper()} — {scen.subtitle}",
            "",
            scen.description,
            "",
            "VICTORY CRITERIA:",
            f"• Target Term: Reach Year {scen.target_year} without impeachment (Current: Year {st.year if st else 1})",
            f"• Maximum Average Starvation: <{scen.max_avg_starvation_pct:.0f}% (Current: {st.starved_pct_avg:.1f}%)" if st else f"• Maximum Average Starvation: <{scen.max_avg_starvation_pct:.0f}%",
        ]
        if scen.min_final_bushels > 0:
            lines.append(f"• Minimum Final Grain: >={scen.min_final_bushels} bushels (Current: {st.bushels if st else 0})")
        if scen.min_final_acres > 0:
            lines.append(f"• Minimum Final Land: >={scen.min_final_acres} acres (Current: {st.acres if st else 0})")
        if scen.min_final_population > 0:
            lines.append(f"• Minimum Final Population: >={scen.min_final_population} citizens (Current: {st.population if st else 0})")

        buttons = [("CLOSE", lambda: setattr(self, "active_modal", None))]
        self.active_modal = UIModal(f"SCENARIO OBJECTIVES: {scen.title.upper()}", lines, buttons, width=820, height=480)

    def _open_pause_modal(self) -> None:
        lines = [
            "Game is paused. What is your decree, Sire?",
            "",
            f"Current Mode: {self.active_mode}",
            f"Audio Effects: {'ENABLED' if SoundSynthesizer.is_enabled() else 'MUTED'}",
            f"Animations: {'ENABLED' if self.animations_enabled else 'REDUCED'}",
        ]

        def toggle_sound():
            SoundSynthesizer.set_enabled(not SoundSynthesizer.is_enabled())
            self._open_pause_modal()

        def toggle_anim():
            self.animations_enabled = not self.animations_enabled
            self._open_pause_modal()

        buttons = [
            ("RESUME", lambda: setattr(self, "active_modal", None)),
            ("SOUND", toggle_sound),
            ("ANIM", toggle_anim),
            ("SAVE", self._save_game_action),
            ("MAIN MENU", self._return_to_main_menu),
        ]
        self.active_modal = UIModal("PAUSE & GOVERNANCE", lines, buttons, width=720, height=380)

    def _open_settings_modal(self) -> None:
        lines = [
            "RetroRevive Configuration:",
            "",
            f"1. Audio Sound Effects: {'[ENABLED]' if SoundSynthesizer.is_enabled() else '[MUTED]'}",
            f"2. Visual Animations: {'[ACTIVE]' if self.animations_enabled else '[REDUCED]'}",
            "3. Canvas Layout: 1280x720 (Logical HD Scaling)",
            "4. Game Engine: Python Standard Library + Pygame",
        ]

        def toggle_sound():
            SoundSynthesizer.set_enabled(not SoundSynthesizer.is_enabled())
            self._open_settings_modal()

        def toggle_anim():
            self.animations_enabled = not self.animations_enabled
            self._open_settings_modal()

        buttons = [
            ("TOGGLE SOUND", toggle_sound),
            ("TOGGLE ANIM", toggle_anim),
            ("CLOSE", lambda: setattr(self, "active_modal", None)),
        ]
        self.active_modal = UIModal("SETTINGS & DISPLAY", lines, buttons, width=680, height=380)

    def _return_to_main_menu(self) -> None:
        self.active_modal = None
        self.active_toast = None
        for inp in [self.input_buy, self.input_sell, self.input_feed, self.input_plant]:
            inp.is_active = False
            inp.error_message = None
        self.current_screen = "MAIN_MENU"
        self._init_menu_buttons()

    def _open_scenarios_screen(self) -> None:
        self.active_modal = None
        self.active_toast = None
        self.current_screen = "SCENARIOS"

    def _open_instructions_screen(self) -> None:
        self.active_modal = None
        self.active_toast = None
        self.tutorial_step = 0
        self.current_screen = "INSTRUCTIONS"

    def quit(self) -> None:
        if self.on_exit_to_library:
            self.on_exit_to_library()
        else:
            self.is_running = False

    # -----------------------------------------------------------------------
    # Main Loop, Event Handling & Canvas Scaling
    # -----------------------------------------------------------------------

    def _compute_viewport(self) -> Tuple[int, int, int, int]:
        """Calculates letterbox viewport offset and dimensions for current window size."""
        win_w = max(1, self.screen_width)
        win_h = max(1, self.screen_height)
        target_aspect = BASE_WIDTH / BASE_HEIGHT

        win_aspect = win_w / win_h
        if win_aspect >= target_aspect:
            vp_h = win_h
            vp_w = int(win_h * target_aspect)
            vp_x = (win_w - vp_w) // 2
            vp_y = 0
        else:
            vp_w = win_w
            vp_h = int(win_w / target_aspect)
            vp_x = 0
            vp_y = (win_h - vp_h) // 2
        return vp_x, vp_y, max(1, vp_w), max(1, vp_h)

    def _screen_to_canvas(self, screen_pos: Tuple[int, int]) -> Tuple[int, int]:
        """Transforms window/screen coordinates to logical 1280x720 canvas coordinates."""
        vp_x, vp_y, vp_w, vp_h = self._compute_viewport()
        sx, sy = screen_pos
        cx = int((sx - vp_x) * (BASE_WIDTH / vp_w))
        cy = int((sy - vp_y) * (BASE_HEIGHT / vp_h))
        return cx, cy

    def handle_event(self, event: pygame.event.Event) -> None:
        # Window resize event
        if event.type == pygame.VIDEORESIZE:
            self.screen_width = event.w
            self.screen_height = event.h
            self.window = pygame.display.set_mode((event.w, event.h), pygame.RESIZABLE)

        # Map screen mouse position to logical canvas coordinates
        raw_pos = getattr(event, "pos", pygame.mouse.get_pos())
        canvas_mouse = self._screen_to_canvas(raw_pos)

        # Allow skipping cinematic with any key or mouse click
        if self.cinematics.is_playing():
            if event.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN):
                self.cinematics.skip()
                return

        # Modal event consumption
        if getattr(self, "auth_modal", None) and self.auth_modal.is_open:
            if self.auth_modal.handle_event(event, canvas_mouse):
                return

        if self.active_modal:
            self.active_modal.handle_event(event, canvas_mouse)
            return

        # Screen-specific routing
        if self.current_screen == "MAIN_MENU":
            self._handle_menu_events(event, canvas_mouse)
        elif self.current_screen == "GAMEPLAY":
            self._handle_gameplay_events(event, canvas_mouse)
        elif self.current_screen == "GAME_OVER":
            self._handle_game_over_events(event, canvas_mouse)
        elif self.current_screen == "SCENARIOS":
            self._handle_scenarios_events(event, canvas_mouse)
        elif self.current_screen == "INSTRUCTIONS":
            self._handle_instructions_events(event, canvas_mouse)
        elif self.current_screen == "MILITARY":
            self.military_dashboard.handle_event(event)
        elif self.current_screen == "AGRICULTURE":
            self.agriculture_dashboard.handle_event(event, canvas_mouse)
        elif self.current_screen == "VIDEO_CREATOR":
            self.video_creator.handle_event(event, canvas_mouse)

    def _handle_menu_events(self, event: pygame.event.Event, mouse_pos: Tuple[int, int]) -> None:
        if event.type == pygame.KEYDOWN:
            # Hotkey P triggers the royal prologue cinematic
            if event.key == pygame.K_p:
                self.cinematics.trigger_prologue()
                return

            # Numeric keys 1-7 map directly to visible menu options
            key_map = {
                pygame.K_1: 0, pygame.K_KP1: 0,
                pygame.K_2: 1, pygame.K_KP2: 1,
                pygame.K_3: 2, pygame.K_KP3: 2,
                pygame.K_4: 3, pygame.K_KP4: 3,
                pygame.K_5: 4, pygame.K_KP5: 4,
                pygame.K_6: 5, pygame.K_KP6: 5,
                pygame.K_7: 6, pygame.K_KP7: 6,
            }
            if event.key in key_map:
                idx = key_map[event.key]
                if 0 <= idx < len(self.menu_buttons):
                    self.selected_menu_idx = idx
                    self.menu_buttons[idx].trigger()
                    return
            elif event.key == pygame.K_UP:
                self.selected_menu_idx = (self.selected_menu_idx - 1) % len(self.menu_buttons)
                for i, btn in enumerate(self.menu_buttons):
                    btn.is_focused = (i == self.selected_menu_idx)
                SoundSynthesizer.play("click")
                return
            elif event.key == pygame.K_DOWN:
                self.selected_menu_idx = (self.selected_menu_idx + 1) % len(self.menu_buttons)
                for i, btn in enumerate(self.menu_buttons):
                    btn.is_focused = (i == self.selected_menu_idx)
                SoundSynthesizer.play("click")
                return
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                if 0 <= self.selected_menu_idx < len(self.menu_buttons):
                    self.menu_buttons[self.selected_menu_idx].trigger()
                return

        if hasattr(self, "btn_menu_profile") and self.btn_menu_profile.handle_event(event, mouse_pos):
            return
        if hasattr(self, "btn_menu_saves") and self.btn_menu_saves.handle_event(event, mouse_pos):
            return

        if hasattr(self, "btn_watch_prologue") and self.btn_watch_prologue.handle_event(event, mouse_pos):
            return
        if hasattr(self, "btn_military") and self.btn_military.handle_event(event, mouse_pos):
            return
        if hasattr(self, "btn_agriculture") and self.btn_agriculture.handle_event(event, mouse_pos):
            return
        if hasattr(self, "btn_studio") and self.btn_studio.handle_event(event, mouse_pos):
            return

        for btn in self.menu_buttons:
            btn.handle_event(event, mouse_pos)

    def _handle_gameplay_events(self, event: pygame.event.Event, mouse_pos: Tuple[int, int]) -> None:
        # In-Game Header Buttons
        if hasattr(self, "btn_profile") and self.btn_profile.handle_event(event, mouse_pos):
            return
        if hasattr(self, "btn_save") and self.btn_save.handle_event(event, mouse_pos):
            return
        if hasattr(self, "btn_toggle_view") and self.btn_toggle_view.handle_event(event, mouse_pos):
            return
        if hasattr(self, "btn_pause") and self.btn_pause.handle_event(event, mouse_pos):
            return

        # Scenario Goals button in header
        if (
            self.active_mode == "ENHANCED"
            and self.enhanced_state is not None
            and self.enhanced_state.mode == "SCENARIO"
        ):
            if hasattr(self, "btn_goals") and self.btn_goals.handle_event(event, mouse_pos):
                return

        # District navigation pins & dock tabs
        dist_clicked = self.districts.handle_event(event, mouse_pos)
        if dist_clicked:
            st = self._get_current_game_state()
            if dist_clicked == "palace":
                self._on_execute_turn()
            elif dist_clicked == "granary":
                self.is_command_deck_collapsed = False
                self.input_feed.is_active = True
                self.show_toast(f"Granary Silos: {st.bushels if st else 0} bu stored.")
            elif dist_clicked == "farmland":
                self._open_agriculture_screen()
            elif dist_clicked == "market":
                self.is_command_deck_collapsed = False
                self.input_buy.is_active = True
                self.show_toast(f"Marketplace: Land trading at {st.land_price if st else 0} bu/ac.")
            elif dist_clicked == "archives":
                self._open_chronicle_modal()
            elif dist_clicked == "temple":
                SoundSynthesizer.play("bell")
                self.show_toast("The High Priest of Shamash offers prayers on the Ziggurat!")
            elif dist_clicked == "gates":
                self._open_military_screen()
            return

        # Floating panorama controls
        if getattr(self, "is_command_deck_collapsed", False):
            if hasattr(self, "btn_quick_enact") and self.btn_quick_enact.handle_event(event, mouse_pos):
                return
            if hasattr(self, "btn_expand_deck") and self.btn_expand_deck.handle_event(event, mouse_pos):
                return

        # Execute & Reset Buttons
        if self.btn_execute_turn.handle_event(event, mouse_pos):
            return
        if self.btn_reset_turn.handle_event(event, mouse_pos):
            return

        # Advisors and Chronicle (Enhanced Mode only)
        if self.active_mode == "ENHANCED":
            if self.btn_advisors.handle_event(event, mouse_pos):
                return
            if self.btn_chronicle.handle_event(event, mouse_pos):
                return

        inputs = [self.input_buy, self.input_sell, self.input_feed, self.input_plant]

        # Keyboard shortcuts
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_TAB:
                active_idx = -1
                for i, inp in enumerate(inputs):
                    if inp.is_active:
                        active_idx = i
                        inp.is_active = False
                for offset in range(1, len(inputs) + 1):
                    cand_idx = (active_idx + offset) % len(inputs)
                    if inputs[cand_idx].is_enabled:
                        inputs[cand_idx].is_active = True
                        break
                return
            elif event.key == pygame.K_RETURN:
                any_was_active = False
                for inp in inputs:
                    if inp.is_active:
                        inp.is_active = False
                        any_was_active = True
                if not any_was_active:
                    self._on_execute_turn()
                return
            elif not any(inp.is_active for inp in inputs):
                # Gameplay Hotkeys (when not actively editing numbers)
                if event.key == pygame.K_a and self.active_mode == "ENHANCED":
                    self._open_advisors_modal()
                    return
                elif event.key == pygame.K_c and self.active_mode == "ENHANCED":
                    self._open_chronicle_modal()
                    return
                elif (
                    event.key == pygame.K_g
                    and self.active_mode == "ENHANCED"
                    and self.enhanced_state is not None
                    and self.enhanced_state.mode == "SCENARIO"
                ):
                    self._open_scenario_goals_modal()
                    return
                elif event.key == pygame.K_s:
                    self._save_game_action()
                    return
                elif event.key == pygame.K_r:
                    self._reset_turn_inputs_for_new_turn()
                    return
                elif event.key in (pygame.K_p, pygame.K_ESCAPE):
                    self._open_pause_modal()
                    return

        # Forward event to inputs (steppers and typing)
        clicked_any_input = False
        for inp in inputs:
            if inp.handle_event(event, mouse_pos):
                clicked_any_input = True

        # Click outside blur
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and not clicked_any_input:
            for inp in inputs:
                inp.is_active = False

    def _handle_game_over_events(self, event: pygame.event.Event, mouse_pos: Tuple[int, int]) -> None:
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_1, pygame.K_r, pygame.K_RETURN, pygame.K_SPACE):
                self._start_classic_game()
                return
            elif event.key in (pygame.K_2, pygame.K_m, pygame.K_ESCAPE):
                self._return_to_main_menu()
                return

        if self.btn_game_over_replay.handle_event(event, mouse_pos):
            return
        if self.btn_game_over_menu.handle_event(event, mouse_pos):
            return

    def _handle_scenarios_events(self, event: pygame.event.Event, mouse_pos: Tuple[int, int]) -> None:
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_ESCAPE, pygame.K_b):
                self._return_to_main_menu()
                return
            scen_keys = list(SCENARIOS.keys())
            if event.key in (pygame.K_1, pygame.K_KP1) and len(scen_keys) >= 1:
                self._start_scenario(scen_keys[0])
                return
            elif event.key in (pygame.K_2, pygame.K_KP2) and len(scen_keys) >= 2:
                self._start_scenario(scen_keys[1])
                return
            elif event.key in (pygame.K_3, pygame.K_KP3) and len(scen_keys) >= 3:
                self._start_scenario(scen_keys[2])
                return
            elif event.key in (pygame.K_4, pygame.K_KP4) and len(scen_keys) >= 4:
                self._start_scenario(scen_keys[3])
                return

        if self.btn_scenarios_back.handle_event(event, mouse_pos):
            return
        for btn in self.scenario_play_buttons.values():
            if btn.handle_event(event, mouse_pos):
                return

    def _handle_instructions_events(self, event: pygame.event.Event, mouse_pos: Tuple[int, int]) -> None:
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_ESCAPE, pygame.K_b):
                self._return_to_main_menu()
                return
            elif event.key in (pygame.K_RIGHT, pygame.K_SPACE, pygame.K_RETURN):
                if self.tutorial_step < 4:
                    self._next_tutorial_step()
                return
            elif event.key == pygame.K_LEFT:
                if self.tutorial_step > 0:
                    self._prev_tutorial_step()
                return

        if self.btn_instructions_back.handle_event(event, mouse_pos):
            return
        if self.btn_tutorial_prev.handle_event(event, mouse_pos):
            return
        if self.btn_tutorial_next.handle_event(event, mouse_pos):
            return

    def _next_tutorial_step(self) -> None:
        self.tutorial_step = min(4, self.tutorial_step + 1)
        SoundSynthesizer.play("click")

    def _prev_tutorial_step(self) -> None:
        self.tutorial_step = max(0, self.tutorial_step - 1)
        SoundSynthesizer.play("click")

    # -----------------------------------------------------------------------
    # Rendering Screens onto Canvas
    # -----------------------------------------------------------------------

    def update(self, dt: float) -> None:
        st = self._get_current_game_state()
        if hasattr(self, "day_night"):
            self.day_night.update(dt, st)
        if self.animations_enabled:
            self.world.update(dt)
            if hasattr(self, "hammurabi"):
                self.hammurabi.update(dt)
            if hasattr(self, "advisor_portrait"):
                self.advisor_portrait.update(dt)
            if hasattr(self, "districts"):
                self.districts.update(dt)
        if hasattr(self, "cinematics"):
            self.cinematics.update(dt)
        if self.current_screen == "MILITARY" and hasattr(self, "military_dashboard"):
            self.military_dashboard.update(dt)
        elif self.current_screen == "AGRICULTURE" and hasattr(self, "agriculture_dashboard"):
            self.agriculture_dashboard.update(dt, st)
        elif self.current_screen == "VIDEO_CREATOR" and hasattr(self, "video_creator"):
            self.video_creator.update(dt)

    def draw(self) -> None:
        # Render active screen onto logical 1280x720 canvas
        if self.current_screen == "MAIN_MENU":
            self._draw_main_menu()
        elif self.current_screen == "GAMEPLAY":
            self._draw_gameplay()
        elif self.current_screen == "GAME_OVER":
            self._draw_game_over()
        elif self.current_screen == "SCENARIOS":
            self._draw_scenarios()
        elif self.current_screen == "INSTRUCTIONS":
            self._draw_instructions()
        elif self.current_screen == "MILITARY" and hasattr(self, "military_dashboard"):
            self.military_dashboard.draw(self.canvas, self._get_current_game_state(), self.world.time_elapsed)
        elif self.current_screen == "AGRICULTURE" and hasattr(self, "agriculture_dashboard"):
            self.agriculture_dashboard.draw(self.canvas, self._get_current_game_state())
        elif self.current_screen == "VIDEO_CREATOR" and hasattr(self, "video_creator"):
            self.video_creator.draw(self.canvas, self._get_current_game_state())

        # Modal dialogs
        if self.active_modal:
            self.active_modal.draw(self.canvas)

        # Auth & Profile modal
        if getattr(self, "auth_modal", None) and self.auth_modal.is_open:
            self.auth_modal.draw(self.canvas)

        # Active toast notifications
        if self.active_toast:
            if self.active_toast.is_alive():
                self.active_toast.draw(self.canvas)
            else:
                self.active_toast = None

        # Cinematic Cutscenes Overlay (plays over any screen with letterboxing)
        if hasattr(self, "cinematics") and self.cinematics.is_playing():
            self.cinematics.draw(self.canvas)

        # Scale virtual canvas to letterboxed viewport
        vp_x, vp_y, vp_w, vp_h = self._compute_viewport()
        if vp_w == BASE_WIDTH and vp_h == BASE_HEIGHT and vp_x == 0 and vp_y == 0:
            self.window.blit(self.canvas, (0, 0))
        else:
            scaled_surf = pygame.transform.smoothscale(self.canvas, (vp_w, vp_h))
            self.window.fill((0, 0, 0))
            self.window.blit(scaled_surf, (vp_x, vp_y))
        pygame.display.flip()

    def _draw_main_menu(self) -> None:
        # Background living world scene
        self.world.render(self.canvas)

        # Main Menu Top Header Bar (Deep Sapphire Glass)
        m_hdr_rect = pygame.Rect(0, 0, BASE_WIDTH, 64)
        pygame.draw.rect(self.canvas, Palette.SAPPHIRE_PANEL, m_hdr_rect)
        pygame.draw.line(self.canvas, Palette.GOLD_BASE, (0, 64), (BASE_WIDTH, 64), 2)

        # Title on left of header
        top_title = FontManager.header(16).render("RETROREVIVE KINGDOM SYSTEM: ANCIENT BABYLON", True, Palette.GOLD_LIGHT)
        self.canvas.blit(top_title, (24, 22))

        # Profile and multi-slot saves buttons on top right
        if hasattr(self, "btn_menu_saves"):
            self.btn_menu_saves.draw(self.canvas)
        if hasattr(self, "btn_menu_profile"):
            self.btn_menu_profile.draw(self.canvas)

        # -------------------------------------------------------------
        # Left Royal Pavilion: King Hammurabi
        # -------------------------------------------------------------
        left_w, left_h = 310, 580
        lx, ly = 30, 85
        pygame.draw.rect(self.canvas, Palette.SAPPHIRE_PANEL, (lx, ly, left_w, left_h), border_radius=12)
        pygame.draw.rect(self.canvas, Palette.GOLD_BASE, (lx, ly, left_w, left_h), width=2, border_radius=12)

        # Hammurabi animated bust with breathing, blinking, and sceptre gleam
        self.hammurabi.draw_bust(self.canvas, center_x=lx + left_w // 2, center_y=ly + 195, size=210)

        # Royal Plaque underneath the bust
        plaque_rect = pygame.Rect(lx + 20, ly + 360, left_w - 40, 70)
        pygame.draw.rect(self.canvas, Palette.SAPPHIRE_BASE, plaque_rect, border_radius=6)
        pygame.draw.rect(self.canvas, Palette.GOLD_BASE, plaque_rect, width=1, border_radius=6)
        k_title = FontManager.header(19).render("KING HAMMURABI", True, Palette.GOLD_PALE)
        k_sub = FontManager.small(12).render("Sixth King of Babylon", True, Palette.SAND_LIGHT)
        k_dyn = FontManager.small(11).render("Dynasty of the Amorites (c. 1792 BCE)", True, Palette.TEXT_MUTED)
        self.canvas.blit(k_title, k_title.get_rect(center=(lx + left_w // 2, ly + 380)))
        self.canvas.blit(k_sub, k_sub.get_rect(center=(lx + left_w // 2, ly + 402)))
        self.canvas.blit(k_dyn, k_dyn.get_rect(center=(lx + left_w // 2, ly + 418)))

        # Sceptre and rod inscription
        ins_lines = [
            "\"I established law and justice",
            "in the language of the land,",
            "and promoted the welfare",
            "of the people.\"",
        ]
        iy = ly + 448
        for il in ins_lines:
            i_surf = FontManager.italic(13).render(il, True, Palette.GOLD_LIGHT)
            self.canvas.blit(i_surf, i_surf.get_rect(center=(lx + left_w // 2, iy)))
            iy += 20

        # -------------------------------------------------------------
        # Center Menu Card: Title and Game Modes
        # -------------------------------------------------------------
        overlay = pygame.Surface((540, 580), pygame.SRCALPHA)
        overlay.fill(Palette.SAPPHIRE_PANEL)
        ox = (BASE_WIDTH - 540) // 2
        oy = 85
        self.canvas.blit(overlay, (ox, oy))
        pygame.draw.rect(self.canvas, Palette.GOLD_BASE, (ox, oy, 540, 580), width=2, border_radius=12)

        # Game Title & Subtitles
        title_surf = FontManager.title(42).render("RETROREVIVE", True, Palette.GOLD_PALE)
        sub_surf = FontManager.header(21).render("HAMMURABI — THE LIVING EMPIRE", True, Palette.SAND_LIGHT)
        track_surf = FontManager.small(12).render("Ancient Babylonian Strategy Simulation  •  1978 BASIC Core", True, Palette.TEXT_MUTED)

        self.canvas.blit(title_surf, title_surf.get_rect(center=(BASE_WIDTH // 2, oy + 36)))
        self.canvas.blit(sub_surf, sub_surf.get_rect(center=(BASE_WIDTH // 2, oy + 70)))
        self.canvas.blit(track_surf, track_surf.get_rect(center=(BASE_WIDTH // 2, oy + 94)))

        # Menu buttons
        for btn in self.menu_buttons:
            btn.draw(self.canvas)

        # Bottom divider & shortcut help
        has_save = os.path.exists("retrorevive_save.json")
        hint_label = "[1-7] Quick Select  |  [P] Royal Prologue  |  [Enter] Confirm" if has_save else "[1-6] Quick Select  |  [P] Royal Prologue  |  [Enter] Confirm"
        pygame.draw.line(self.canvas, Palette.PANEL_BORDER, (ox + 40, oy + 540), (ox + 500, oy + 540), 1)
        hint = FontManager.small(12).render(hint_label, True, Palette.TEXT_MUTED)
        self.canvas.blit(hint, hint.get_rect(center=(BASE_WIDTH // 2, oy + 558)))

        # -------------------------------------------------------------
        # Right Diorite Stele: Code of Hammurabi & Prologue Action
        # -------------------------------------------------------------
        rx, ry = 940, 85
        rw, rh = 310, 580
        pygame.draw.rect(self.canvas, Palette.SAPPHIRE_PANEL, (rx, ry, rw, rh), border_radius=12)
        pygame.draw.rect(self.canvas, Palette.GOLD_BASE, (rx, ry, rw, rh), width=2, border_radius=12)

        s_hdr = FontManager.header(18).render("THE ROYAL STELE", True, Palette.GOLD_PALE)
        s_sub = FontManager.small(11).render("PROCLAMATION OF JUSTICE", True, Palette.TEXT_MUTED)
        self.canvas.blit(s_hdr, s_hdr.get_rect(center=(rx + rw // 2, ry + 24)))
        self.canvas.blit(s_sub, s_sub.get_rect(center=(rx + rw // 2, ry + 44)))
        pygame.draw.line(self.canvas, Palette.GOLD_BASE, (rx + 24, ry + 58), (rx + rw - 24, ry + 58), 1)

        # Cuneiform decorative motif & Pillars of State
        pillars = [
            ("GOVERNANCE PILLARS", Palette.GOLD_LIGHT),
            ("• Sustenance: 20 bu / citizen", Palette.TEXT_BODY),
            ("• Cultivation: 2 bu / seeded ac", Palette.TEXT_BODY),
            ("• Labor Capacity: 10 ac / person", Palette.TEXT_BODY),
            ("• Term: 10 Years of Rule", Palette.TEXT_BODY),
            ("• Land Market: 17–26 bu / ac", Palette.TEXT_BODY),
            ("• Famine Limit: < 45% annual", Palette.TEXT_BODY),
        ]
        py_cur = ry + 75
        for p_txt, p_col in pillars:
            p_s = FontManager.small(13).render(p_txt, True, p_col)
            self.canvas.blit(p_s, (rx + 24, py_cur))
            py_cur += 24

        pygame.draw.line(self.canvas, Palette.PANEL_BORDER, (rx + 24, py_cur + 8), (rx + rw - 24, py_cur + 8), 1)

        # Cuneiform quote excerpt
        quote_lines = [
            "\"That the strong may not",
            "oppress the weak, to counsel",
            "the orphan and widow,",
            "I wrote these precious words",
            "upon my stone stele.\"",
        ]
        qy = py_cur + 24
        for ql in quote_lines:
            qs = FontManager.italic(13).render(ql, True, Palette.SAND_LIGHT)
            self.canvas.blit(qs, qs.get_rect(center=(rx + rw // 2, qy)))
            qy += 22

        # Action Buttons on Right Stele
        if hasattr(self, "btn_watch_prologue"):
            self.btn_watch_prologue.draw(self.canvas)
        if hasattr(self, "btn_military"):
            self.btn_military.draw(self.canvas)
        if hasattr(self, "btn_agriculture"):
            self.btn_agriculture.draw(self.canvas)
        if hasattr(self, "btn_studio"):
            self.btn_studio.draw(self.canvas)

    def _draw_gameplay(self) -> None:
        st = self._get_current_game_state()
        if not st:
            return

        # 1. Background living world
        self.world.render(self.canvas, state=st)

        # 1b. Living kingdom district pins and interactive hotspots
        self.districts.draw_world_pins(self.canvas, st, pygame.mouse.get_pos())

        # 1c. Dynamic Day/Night lighting and atmospheric weather overlay
        if hasattr(self, "day_night"):
            self.day_night.render_night_overlay(self.canvas)
            self.day_night.render_weather(self.canvas)

        # 2. Top HUD Bar (Deep Sapphire Glass)
        hud_rect = pygame.Rect(0, 0, BASE_WIDTH, 62)
        pygame.draw.rect(self.canvas, Palette.SAPPHIRE_PANEL, hud_rect)
        pygame.draw.line(self.canvas, Palette.GOLD_BASE, (0, 62), (BASE_WIDTH, 62), 2)

        # Mode Badge & Scenario Status
        is_scenario = (
            self.active_mode == "ENHANCED"
            and self.enhanced_state is not None
            and self.enhanced_state.mode == "SCENARIO"
        )
        scen = (
            SCENARIOS.get(self.enhanced_state.scenario_id)
            if (is_scenario and self.enhanced_state and self.enhanced_state.scenario_id in SCENARIOS)
            else None
        )
        if is_scenario and scen:
            mode_label = f"[{scen.title.upper()}]"
            badge_col = Palette.GOLD_LIGHT
            target_yr = scen.target_year
        elif self.active_mode == "CLASSIC":
            mode_label = "[CLASSIC 1978]"
            badge_col = Palette.SAND_LIGHT
            target_yr = 10
        else:
            mode_label = "[ENHANCED REALM]"
            badge_col = Palette.LAPIS_LIGHT
            target_yr = 10

        b_surf = FontManager.header(15).render(mode_label, True, badge_col)
        self.canvas.blit(b_surf, (16, 21))

        # Year Indicator
        yr_surf = FontManager.header(19).render(f"YEAR {st.year} OF {target_yr}", True, Palette.GOLD_PALE)
        yr_x = 16 + b_surf.get_width() + 14
        self.canvas.blit(yr_surf, (yr_x, 20))

        # Quick Stats in HUD
        hud_stat = (
            f"Pop: {st.population:,}  |  Land: {st.acres:,} ac  |  "
            f"Grain: {st.bushels:,} bu  |  Price: {st.land_price} bu/ac"
        )
        stat_x = yr_x + yr_surf.get_width() + 16
        stat_surf = FontManager.body(15).render(hud_stat, True, Palette.TEXT_BODY)
        self.canvas.blit(stat_surf, (stat_x, 21))

        # In-game buttons (Profile, Saves, Panorama View, Pause Menu, Goals)
        if hasattr(self, "btn_profile"):
            self.btn_profile.rect = pygame.Rect(720, 14, 130, 36)
            self.btn_profile.draw(self.canvas)
        if hasattr(self, "btn_save"):
            self.btn_save.rect = pygame.Rect(856, 14, 85, 36)
            self.btn_save.draw(self.canvas)
        if hasattr(self, "btn_toggle_view"):
            self.btn_toggle_view.rect = pygame.Rect(947, 14, 110, 36)
            self.btn_toggle_view.draw(self.canvas)
        if hasattr(self, "btn_pause"):
            self.btn_pause.rect = pygame.Rect(1063, 14, 85, 36)
            self.btn_pause.draw(self.canvas)
        if is_scenario and hasattr(self, "btn_goals"):
            self.btn_goals.rect = pygame.Rect(1154, 14, 85, 36)
            self.btn_goals.draw(self.canvas)

        # -------------------------------------------------------------
        # PANORAMA COLLAPSED MODE (>90% of screen displays kingdom)
        # -------------------------------------------------------------
        if getattr(self, "is_command_deck_collapsed", False):
            preview = DecreePreviewData(st, self.input_buy.value, self.input_sell.value, self.input_feed.value, self.input_plant.value)
            pill_rect = pygame.Rect(30, 615, 1220, 48)
            pygame.draw.rect(self.canvas, Palette.SAPPHIRE_PANEL, pill_rect, border_radius=8)
            pygame.draw.rect(self.canvas, Palette.GOLD_BASE, pill_rect, width=2, border_radius=8)

            p_txt = f"PANORAMA VIEW  |  Year {st.year}  |  Citizens: {st.population:,}  |  Est. Balance: {preview.grain_balance:,} bu  |  Rationed: {preview.citizens_fed}/{st.population}"
            p_surf = FontManager.header(14).render(p_txt, True, Palette.GOLD_PALE)
            self.canvas.blit(p_surf, (pill_rect.x + 18, pill_rect.y + 14))

            self.btn_quick_enact.rect = pygame.Rect(pill_rect.right - 180, pill_rect.y + 5, 168, 38)
            self.btn_expand_deck.rect = pygame.Rect(pill_rect.right - 350, pill_rect.y + 5, 160, 38)
            self.btn_expand_deck.draw(self.canvas)
            self.btn_quick_enact.draw(self.canvas)

            # District Dock at bottom
            self.districts.draw_district_dock(self.canvas, getattr(self.districts.selected_district, "district_id", None))
            return

        # -------------------------------------------------------------
        # STANDARD DOCK MODE: Upper Floating Cards & Bottom Command Deck
        # -------------------------------------------------------------
        # 3. Annual Report Briefing Card (Upper Floating Card - Sapphire Glass)
        card_w, card_h = 570, 205
        card_x, card_y = 28, 74
        pygame.draw.rect(self.canvas, Palette.SAPPHIRE_GLASS, (card_x, card_y, card_w, card_h), border_radius=8)
        pygame.draw.rect(self.canvas, Palette.GOLD_BASE, (card_x, card_y, card_w, card_h), width=2, border_radius=8)

        # Header in briefing
        rep_hdr = FontManager.header(17).render(f"HAMURABI: REPORT FOR YEAR {st.year}", True, Palette.GOLD_PALE)
        self.canvas.blit(rep_hdr, (card_x + 16, card_y + 10))

        # Event Badges on Top Right of Briefing Card
        badge_tags = []
        if st.plague_struck:
            badge_tags.append(("PLAGUE", Palette.CRIMSON))
        if st.rats_ate > 0:
            badge_tags.append((f"RATS -{st.rats_ate}bu", Palette.AMBER_WARN))
        if st.harvest_yield == 5:
            badge_tags.append(("BUMPER HARVEST", Palette.SUCCESS_GREEN))
        elif st.harvest_yield == 1:
            badge_tags.append(("DROUGHT", (180, 80, 30)))

        tag_x = card_x + card_w - 12
        for t_text, t_col in reversed(badge_tags):
            t_surf = FontManager.mono(11).render(t_text, True, Palette.TEXT_TITLE)
            tw = t_surf.get_width() + 14
            th = 20
            tag_x -= tw
            tag_rect = pygame.Rect(tag_x, card_y + 9, tw, th)
            pygame.draw.rect(self.canvas, t_col, tag_rect, border_radius=4)
            self.canvas.blit(t_surf, t_surf.get_rect(center=tag_rect.center))
            tag_x -= 6

        # Report lines (all displayed cleanly without truncation)
        lines = []
        if st.plague_struck:
            lines.append(("• HORRIBLE PLAGUE STRUCK! Half the living people died.", Palette.CRIMSON_LIGHT))

        if st.starved_this_year > 0:
            lines.append((f"• FAMINE: {st.starved_this_year} citizens starved to death.", Palette.CRIMSON_LIGHT))
        else:
            lines.append((f"• Sustenance: 0 citizens starved. All people fed.", Palette.SUCCESS_GREEN))

        lines.append((f"• Newcomers: {st.immigrants_this_year} arrived. Population now {st.population}.", Palette.TEXT_BODY))
        lines.append((f"• Harvest: Reaped {st.harvest_yield} bu/acre across sown acreage.", Palette.TEXT_BODY))
        lines.append((f"• Silos: {st.rats_ate} bu eaten by rats. Store now {st.bushels} bushels.", Palette.TEXT_BODY))
        lines.append((f"• Land Market: Trading at {st.land_price} bushels per acre.", Palette.TEXT_MUTED))

        curr_y = card_y + 34
        line_spacing = 19 if len(lines) > 5 else 21
        for text, col in lines:
            l_surf = FontManager.small(13).render(text, True, col)
            self.canvas.blit(l_surf, (card_x + 16, curr_y))
            curr_y += line_spacing

        # Summary delta footer if previous turn recorded
        if self.last_turn_summary:
            p_yr = self.last_turn_summary["year"]
            p_pop = self.last_turn_summary["pop_delta"]
            p_grain = self.last_turn_summary["grain_delta"]
            delta_str = f"Net from YR {p_yr}: Pop {p_pop:+} | Grain {p_grain:+} bu | Rats -{self.last_turn_summary['rats_ate']} bu"
            delta_surf = FontManager.small(11).render(delta_str, True, Palette.GOLD_LIGHT)
            self.canvas.blit(delta_surf, (card_x + 16, card_y + card_h - 22))

        # 3b. Grand Vizier's Live Ministerial Council Card (Upper Right Card: 618 to 1252)
        adv_x, adv_y = 618, 74
        adv_w, adv_h = 634, 205
        pygame.draw.rect(self.canvas, Palette.SAPPHIRE_GLASS, (adv_x, adv_y, adv_w, adv_h), border_radius=8)
        pygame.draw.rect(self.canvas, Palette.GOLD_BASE, (adv_x, adv_y, adv_w, adv_h), width=2, border_radius=8)

        # Header
        viz_hdr = FontManager.header(17).render("MINISTERIAL AUDIENCE & STRATEGY", True, Palette.GOLD_PALE)
        self.canvas.blit(viz_hdr, (adv_x + 16, adv_y + 10))

        # Determine Vizier mood from game state
        if st.plague_struck or st.starved_this_year > 0 or st.harvest_yield <= 2:
            adv_mood = "alarmed"
            mood_label = "CRITICAL SITUATION"
            mood_col = Palette.CRIMSON
        elif st.harvest_yield >= 5 or st.immigrants_this_year >= 10:
            adv_mood = "celebratory"
            mood_label = "ABUNDANT PROSPERITY"
            mood_col = Palette.SUCCESS_GREEN
        else:
            adv_mood = "normal"
            mood_label = "ORDER RESTORED"
            mood_col = Palette.GOLD_BASE

        # Badge on top right of council card
        m_surf = FontManager.mono(11).render(mood_label, True, Palette.TEXT_TITLE)
        mw, mh = m_surf.get_width() + 14, 20
        m_rect = pygame.Rect(adv_x + adv_w - mw - 12, adv_y + 9, mw, mh)
        pygame.draw.rect(self.canvas, mood_col, m_rect, border_radius=4)
        self.canvas.blit(m_surf, m_surf.get_rect(center=m_rect.center))

        # Animated Vizier Portrait (Left side of council card)
        self.advisor_portrait.draw(self.canvas, adv_x + 68, adv_y + 108, size=115, mood=adv_mood)
        v_title = FontManager.small(11).render("VIZIER BELSHAZZAR", True, Palette.GOLD_LIGHT)
        self.canvas.blit(v_title, v_title.get_rect(center=(adv_x + 68, adv_y + 172)))

        # Speech & Advice on right side of council card
        content_x = adv_x + 138
        content_w = adv_w - 150

        if st.plague_struck:
            speech = "My Sovereign! A terrifying plague swept our streets. Half of our brethren fell to the dust. We must conserve food and protect survivors."
        elif st.starved_this_year > 0:
            speech = f"Sire! {st.starved_this_year} citizens perished from famine! Ensure at least {st.population * 20} bushels are distributed for sustenance."
        elif st.rats_ate > 0:
            speech = f"Grain vermin consumed {st.rats_ate} bushels from our silos! We must plant vigorously to replace lost reserves."
        elif st.harvest_yield == 5:
            speech = "Praise Shamash and Marduk! The fertile silt has granted a bumper harvest of 5 bushels per acre! The granaries overflow!"
        elif st.harvest_yield == 1:
            speech = "The river dropped low and drought scorched our stalks; our yield was only 1 bu/acre. Manage treasury with great vigilance."
        else:
            speech = "The Euphrates rises calmly, Sire. The farmers stand ready in the fields, awaiting your royal commands."

        # Word-wrap speech text
        words = speech.split()
        s_lines = []
        cur_s = []
        f_speech = FontManager.small(13)
        for w in words:
            test_line = " ".join(cur_s + [w])
            if f_speech.size(test_line)[0] > content_w and cur_s:
                s_lines.append(" ".join(cur_s))
                cur_s = [w]
            else:
                cur_s.append(w)
        if cur_s:
            s_lines.append(" ".join(cur_s))

        sy = adv_y + 36
        for sl in s_lines[:3]:
            sl_surf = f_speech.render(sl, True, Palette.TEXT_TITLE)
            self.canvas.blit(sl_surf, (content_x, sy))
            sy += 18

        # Divider line
        pygame.draw.line(self.canvas, Palette.PANEL_BORDER, (content_x, sy + 4), (adv_x + adv_w - 16, sy + 4), 1)

        # Strategic Key Metrics
        sy += 12
        req_food = st.population * 20
        max_work = st.population * 10
        m_lines = [
            (f"• Sustenance Need: {req_food:,} bu (prevents famine for {st.population} people)", Palette.SUCCESS_GREEN if st.bushels >= req_food else Palette.CRIMSON_LIGHT),
            (f"• Labor Capacity: {max_work:,} acres (1 worker cultivates up to 10 ac)", Palette.SAND_LIGHT),
            (f"• Land Valuation: {st.land_price} bu/acre (Historical market range: 17–26 bu)", Palette.GOLD_LIGHT),
        ]
        for m_txt, m_c in m_lines:
            m_s = FontManager.small(12).render(m_txt, True, m_c)
            self.canvas.blit(m_s, (content_x, sy))
            sy += 19

        # 4. Interactive Turn Decision Panel (Bottom half: y = 428 to 710 - Sapphire Panel)
        panel_rect = pygame.Rect(16, 428, 1248, 282)
        pygame.draw.rect(self.canvas, Palette.SAPPHIRE_PANEL, panel_rect, border_radius=10)
        pygame.draw.rect(self.canvas, Palette.GOLD_BASE, panel_rect, width=2, border_radius=10)

        # Title of Decision Panel & Shortcut hints
        dec_title = FontManager.header(17).render("ROYAL DECREES & RESOURCE ALLOCATION", True, Palette.GOLD_PALE)
        self.canvas.blit(dec_title, (28, 436))

        hint_text = FontManager.small(12).render("[Tab] Focus  |  [Enter] Enact Decree  |  [R] Reset Inputs  |  [Esc] Menu", True, Palette.TEXT_MUTED)
        self.canvas.blit(hint_text, (self.canvas.get_width() - hint_text.get_width() - 36, 438))

        # Render Number Inputs
        self.input_buy.draw(self.canvas)
        self.input_sell.draw(self.canvas)
        self.input_feed.draw(self.canvas)
        self.input_plant.draw(self.canvas)

        # Render Royal Scribe's Decree Preview Ledger
        preview = DecreePreviewData(st, self.input_buy.value, self.input_sell.value, self.input_feed.value, self.input_plant.value)
        self.preview_widget.draw(self.canvas, preview)

        # Action Buttons
        if self.active_mode == "ENHANCED":
            self.btn_execute_turn.rect = pygame.Rect(1058, 560, 196, 68)
            self.btn_advisors.rect = pygame.Rect(1058, 462, 196, 44)
            self.btn_chronicle.rect = pygame.Rect(1058, 511, 196, 44)
            self.btn_reset_turn.rect = pygame.Rect(1058, 638, 196, 38)
            self.btn_advisors.draw(self.canvas)
            self.btn_chronicle.draw(self.canvas)
            self.btn_execute_turn.draw(self.canvas)
            self.btn_reset_turn.draw(self.canvas)
        else:
            self.btn_execute_turn.rect = pygame.Rect(1058, 462, 196, 68)
            self.btn_reset_turn.rect = pygame.Rect(1058, 538, 196, 40)
            self.btn_execute_turn.draw(self.canvas)
            self.btn_reset_turn.draw(self.canvas)

            badge_box = pygame.Rect(1058, 588, 196, 96)
            pygame.draw.rect(self.canvas, Palette.SAPPHIRE_BASE, badge_box, border_radius=6)
            pygame.draw.rect(self.canvas, Palette.PANEL_BORDER, badge_box, width=1, border_radius=6)
            self.canvas.blit(FontManager.header(13).render("CLASSIC 1978 RULES", True, Palette.GOLD_LIGHT), (1068, 598))
            self.canvas.blit(FontManager.small(11).render("• Microsoft BASIC engine", True, Palette.TEXT_MUTED), (1068, 622))
            self.canvas.blit(FontManager.small(11).render("• D < 10*P strict labor limit", True, Palette.TEXT_MUTED), (1068, 642))
            self.canvas.blit(FontManager.small(11).render("• Advisors inactive in Classic", True, Palette.TEXT_MUTED), (1068, 662))

        # Bottom District Navigation Dock
        self.districts.draw_district_dock(self.canvas, getattr(self.districts.selected_district, "district_id", None))

    def _draw_game_over(self) -> None:
        self.world.render(self.canvas)

        panel_w, panel_h = 760, 520
        px, py = (BASE_WIDTH - panel_w) // 2, 70
        pygame.draw.rect(self.canvas, Palette.SAPPHIRE_PANEL, (px, py, panel_w, panel_h), border_radius=12)
        pygame.draw.rect(self.canvas, Palette.GOLD_BASE, (px, py, panel_w, panel_h), width=3, border_radius=12)

        if not self.game_over_result:
            return

        res = self.game_over_result
        tier = res["tier"]

        # -------------------------------------------------------------
        # Left Royal Hammurabi Card
        # -------------------------------------------------------------
        lx, ly = 24, 70
        lw, lh = 216, 520
        pygame.draw.rect(self.canvas, Palette.SAPPHIRE_PANEL, (lx, ly, lw, lh), border_radius=12)
        pygame.draw.rect(self.canvas, Palette.GOLD_BASE, (lx, ly, lw, lh), width=2, border_radius=12)
        self.hammurabi.draw_bust(self.canvas, center_x=lx + lw // 2, center_y=ly + 190, size=190)

        # Title under bust
        if tier == 4:
            r_title = "GREAT HAMMURABI"
            r_col = Palette.GOLD_LIGHT
            r_desc = "Father of Babylon"
        elif tier == 3:
            r_title = "JUST GOVERNOR"
            r_col = Palette.SAND_LIGHT
            r_desc = "Keeper of the Realm"
        elif tier == 2:
            r_title = "HARSH STEWARD"
            r_col = Palette.AMBER_WARN
            r_desc = "Troubled Reign"
        else:
            r_title = "NERONIAN TYRANT"
            r_col = Palette.CRIMSON_LIGHT
            r_desc = "Cast into Ignominy"

        p_rect = pygame.Rect(lx + 12, ly + 340, lw - 24, 60)
        pygame.draw.rect(self.canvas, Palette.SAPPHIRE_BASE, p_rect, border_radius=6)
        pygame.draw.rect(self.canvas, Palette.PANEL_BORDER, p_rect, width=1, border_radius=6)
        self.canvas.blit(FontManager.header(14).render(r_title, True, r_col), FontManager.header(14).render(r_title, True, r_col).get_rect(center=(lx + lw // 2, ly + 358)))
        self.canvas.blit(FontManager.small(11).render(r_desc, True, Palette.TEXT_MUTED), FontManager.small(11).render(r_desc, True, Palette.TEXT_MUTED).get_rect(center=(lx + lw // 2, ly + 382)))

        # -------------------------------------------------------------
        # Right Imperial Vizier Archive Card
        # -------------------------------------------------------------
        rx, ry = 1040, 70
        rw, rh = 216, 520
        pygame.draw.rect(self.canvas, (24, 18, 14, 235), (rx, ry, rw, rh), border_radius=12)
        pygame.draw.rect(self.canvas, Palette.GOLD_LIGHT, (rx, ry, rw, rh), width=2, border_radius=12)
        self.advisor_portrait.draw(self.canvas, center_x=rx + rw // 2, center_y=ly + 170, size=130, mood=("celebratory" if tier >= 3 else "alarmed"))

        ap_rect = pygame.Rect(rx + 12, ly + 340, rw - 24, 60)
        pygame.draw.rect(self.canvas, (32, 24, 16), ap_rect, border_radius=6)
        pygame.draw.rect(self.canvas, Palette.PANEL_BORDER, ap_rect, width=1, border_radius=6)
        self.canvas.blit(FontManager.header(14).render("IMPERIAL ARCHIVE", True, Palette.GOLD_PALE), FontManager.header(14).render("IMPERIAL ARCHIVE", True, Palette.GOLD_PALE).get_rect(center=(rx + rw // 2, ly + 358)))
        self.canvas.blit(FontManager.small(11).render("Judgment Recorded", True, Palette.TEXT_MUTED), FontManager.small(11).render("Judgment Recorded", True, Palette.TEXT_MUTED).get_rect(center=(rx + rw // 2, ly + 382)))

        # Banner Title
        if res.get("title"):
            title_text = res["title"]
        elif res["state"].game_over_reason == "STEWARD_FIRED":
            title_text = "RULE TERMINATED: STEWARD DISMISSED"
        elif res["state"].year == 11 and not res["state"].game_over_reason:
            title_text = "TEN-YEAR GOVERNANCE EVALUATION"
        else:
            title_text = "RULE TERMINATED: IMPEACHMENT"
        t_surf = FontManager.title(30).render(title_text, True, Palette.GOLD_PALE)
        self.canvas.blit(t_surf, t_surf.get_rect(center=(BASE_WIDTH // 2, py + 45)))

        # Summary Metrics
        st = res["state"]
        if res.get("is_scenario") and res.get("scenario"):
            scen = res["scenario"]
            m_lines = [
                f"Scenario: {scen.title.upper()} ({scen.subtitle})",
                f"Term Reached: Year {min(st.year, scen.target_year)} of {scen.target_year}  |  Avg Starvation: {res['avg_starved_pct']:.1f}% (Limit: <{scen.max_avg_starvation_pct:.0f}%)",
                f"Surviving Citizens: {st.population} (Req: >={scen.min_final_population})  |  Grain: {st.bushels} bu (Req: >={scen.min_final_bushels})",
                f"Territory: {st.acres} ac (Req: >={scen.min_final_acres})  |  Acres per citizen: {res['acres_per_person']:.2f} ac",
            ]
        elif st.game_over_reason == "STEWARD_FIRED":
            m_lines = [
                "Your steward refused your order and abandoned your court.",
                f"Year of abdication: Year {st.year} of 10.",
                f"Final Population: {st.population} citizens  |  Final Land: {st.acres} acres",
                f"Grain remaining in store: {st.bushels} bushels",
            ]
        else:
            m_lines = [
                f"Total Citizens Starved: {res['total_starved']} people died across your reign.",
                f"Average Annual Starvation: {res['avg_starved_pct']:.1f}% per year.",
                f"Final Land Distribution: {res['acres_per_person']:.2f} acres per citizen (Started with 10.00).",
                f"Surviving Population: {st.population} citizens  |  Final Land: {st.acres} acres",
            ]

        curr_y = py + 105
        for line in m_lines:
            lsurf = FontManager.body(18).render(line, True, Palette.TEXT_BODY)
            self.canvas.blit(lsurf, (px + 40, curr_y))
            curr_y += 30

        # Historical Outcome Box
        box_rect = pygame.Rect(px + 40, curr_y + 10, panel_w - 80, 160)
        pygame.draw.rect(self.canvas, Palette.SAPPHIRE_BASE, box_rect, border_radius=8)
        border_col = Palette.GOLD_BASE if tier == 4 else Palette.CRIMSON_LIGHT if tier == 1 else Palette.PANEL_BORDER
        pygame.draw.rect(self.canvas, border_col, box_rect, width=2, border_radius=8)

        # Historic Text
        h_lines = res["message"].split("\n")
        hy = box_rect.y + 20
        for hl in h_lines:
            h_surf = FontManager.header(18).render(hl, True, Palette.GOLD_PALE if tier == 4 else Palette.TEXT_TITLE)
            self.canvas.blit(h_surf, (box_rect.x + 20, hy))
            hy += 28

        # Persistent Buttons
        self.btn_game_over_replay.draw(self.canvas)
        self.btn_game_over_menu.draw(self.canvas)

        # Keyboard shortcut hints
        go_hint = FontManager.small(12).render("[1 / R] Play Again  |  [2 / M / Esc] Main Menu", True, Palette.TEXT_MUTED)
        self.canvas.blit(go_hint, go_hint.get_rect(center=(BASE_WIDTH // 2, py + panel_h - 14)))

    def _draw_scenarios(self) -> None:
        self.world.render(self.canvas)

        header_surf = FontManager.title(36).render("SCENARIO CHALLENGES", True, Palette.GOLD_PALE)
        self.canvas.blit(header_surf, header_surf.get_rect(center=(BASE_WIDTH // 2, 50)))

        self.btn_scenarios_back.draw(self.canvas)

        # 4 Scenario Cards
        card_w, card_h = 270, 520
        start_x = 55
        card_y = 110
        scen_keys = list(SCENARIOS.keys())

        for i, key in enumerate(scen_keys):
            scen = SCENARIOS[key]
            cx = start_x + i * (card_w + 25)
            c_rect = pygame.Rect(cx, card_y, card_w, card_h)

            pygame.draw.rect(self.canvas, Palette.SAPPHIRE_PANEL, c_rect, border_radius=10)
            pygame.draw.rect(self.canvas, Palette.GOLD_BASE, c_rect, width=2, border_radius=10)

            # Card Header
            title_s = FontManager.header(17).render(scen.title, True, Palette.GOLD_PALE)
            sub_s = FontManager.small(12).render(scen.subtitle, True, Palette.SAND_LIGHT)
            self.canvas.blit(title_s, (cx + 14, card_y + 15))
            self.canvas.blit(sub_s, (cx + 14, card_y + 40))

            # Difficulty Badge
            diff_map = {
                "drought": ("HARD", Palette.AMBER_WARN),
                "boom": ("MEDIUM", Palette.LAPIS_LIGHT),
                "granary": ("HARD", Palette.AMBER_WARN),
                "empire": ("MASTER", Palette.CRIMSON),
            }
            d_text, d_col = diff_map.get(key, ("CHALLENGE", Palette.GOLD_BASE))
            d_badge = pygame.Rect(cx + card_w - 74, card_y + 15, 60, 22)
            pygame.draw.rect(self.canvas, d_col, d_badge, border_radius=4)
            d_label = FontManager.mono(11).render(d_text, True, Palette.TEXT_TITLE)
            self.canvas.blit(d_label, d_label.get_rect(center=d_badge.center))

            pygame.draw.line(self.canvas, Palette.GOLD_BASE, (cx + 14, card_y + 64), (cx + card_w - 14, card_y + 64), 1)

            # Description (word wrapped cleanly)
            words = scen.description.split()
            desc_lines = []
            cur_line = []
            font_desc = FontManager.small(13)
            for w in words:
                test_str = " ".join(cur_line + [w])
                if font_desc.size(test_str)[0] > (card_w - 28) and cur_line:
                    desc_lines.append(" ".join(cur_line))
                    cur_line = [w]
                else:
                    cur_line.append(w)
            if cur_line:
                desc_lines.append(" ".join(cur_line))

            dy = card_y + 74
            for dl in desc_lines[:6]:
                d_surf = font_desc.render(dl, True, Palette.TEXT_BODY)
                self.canvas.blit(d_surf, (cx + 14, dy))
                dy += 20

            # Objectives list
            obj_y = card_y + 215
            pygame.draw.rect(self.canvas, (24, 18, 14), (cx + 12, obj_y, card_w - 24, 185), border_radius=6)
            self.canvas.blit(FontManager.header(15).render("VICTORY GOALS:", True, Palette.GOLD_LIGHT), (cx + 20, obj_y + 10))

            goals = [
                f"• Term: Survive {scen.target_year} Years",
                f"• Start Grain: {scen.starting_bushels} bu",
                f"• Starve Limit: <{scen.max_avg_starvation_pct:.0f}%",
            ]
            if scen.min_final_bushels > 0:
                goals.append(f"• Final Grain: >={scen.min_final_bushels} bu")
            if scen.min_final_acres > 0:
                goals.append(f"• Final Land: >={scen.min_final_acres} ac")
            if scen.min_final_population > 0:
                goals.append(f"• Final Pop: >={scen.min_final_population}")

            gy = obj_y + 36
            for g in goals:
                self.canvas.blit(FontManager.small(13).render(g, True, Palette.TEXT_MUTED), (cx + 20, gy))
                gy += 22

            # Start Scenario Button (persistent instance)
            if key in self.scenario_play_buttons:
                self.scenario_play_buttons[key].draw(self.canvas)

        # Bottom navigation hint
        hint = FontManager.small(12).render("[1-4] Quick Launch  |  [Esc / B] Return to Main Menu", True, Palette.TEXT_MUTED)
        self.canvas.blit(hint, hint.get_rect(center=(BASE_WIDTH // 2, card_y + card_h + 28)))

    def _draw_instructions(self) -> None:
        self.world.render(self.canvas)

        panel_w, panel_h = 920, 580
        px, py = (BASE_WIDTH - panel_w) // 2, 70
        pygame.draw.rect(self.canvas, Palette.SAPPHIRE_PANEL, (px, py, panel_w, panel_h), border_radius=12)
        pygame.draw.rect(self.canvas, Palette.GOLD_BASE, (px, py, panel_w, panel_h), width=3, border_radius=12)

        self.btn_instructions_back.draw(self.canvas)

        tutorial_cards = [
            (
                "TUTORIAL: THE THREE PILLARS OF SUMERIA",
                [
                    "Welcome, ruler. Hammurabi is an ancient resource-management simulation.",
                    "To govern successfully for a 10-year term, you must balance three interconnected resources:",
                    "",
                    "1. CITIZENS (POPULATION): Your workforce. Citizens tend your crops and bring wealth.",
                    "2. ACRES (LAND): Your territorial foundation. Land trades between 17 and 26 bushels/acre.",
                    "3. GRAIN (BUSHELS): Your currency and lifeblood. Used to feed citizens, plant seeds, and trade land.",
                    "",
                    "Every decision you make this year directly impacts your kingdom next year!",
                ]
            ),
            (
                "FEEDING YOUR CITIZENS & FAMINE PREVENTION",
                [
                    "Each living citizen strictly requires 20 BUSHELS OF GRAIN per year to survive.",
                    "",
                    "- If you feed 20 bushels per person: Zero starvation occurs.",
                    "- If you feed LESS than 20 bushels: Citizens will starve to death (Deaths = Pop - Fed).",
                    "- CATASTROPHIC FAMINE: If more than 45% of your population starves in a SINGLE year,",
                    "  the people will violently revolt. You will be impeached and declared NATIONAL FINK!",
                    "",
                    "RULE OF THUMB: Always allocate 20 * Population to food before planting or buying land.",
                ]
            ),
            (
                "SOWING SEED & CROP HARVESTS",
                [
                    "Farming is how you replenish your grain silos every year:",
                    "",
                    "- SEED COST: Sowing 2 acres requires exactly 1 BUSHEL OF GRAIN (Acres // 2).",
                    "- WORKFORCE LIMIT: One citizen can cultivate up to 10 ACRES of land.",
                    "  (Historical quirk: 100 citizens can tend up to 999 acres).",
                    "- HARVEST YIELDS: Mother Nature provides a random yield from 1 to 5 bushels per acre.",
                    "",
                    "A yield of 5 is a bumper harvest! A yield of 1 is a harsh drought.",
                ]
            ),
            (
                "HAZARDS OF ANCIENT MESOPOTAMIA",
                [
                    "Beware the perils that strike ancient rulers without warning:",
                    "",
                    "- RAT INFESTATIONS: Rats have a 40% chance of invading your silos every year.",
                    "  When they strike, they devour between 25% and 50% of your stored grain!",
                    "  Crucial Timing: Rats eat your existing store BEFORE new harvest grain is added.",
                    "",
                    "- THE PLAGUE: A deadly epidemic carries a 20% random probability.",
                    "  When plague strikes, half of your living citizens instantly perish.",
                ]
            ),
            (
                "ACHIEVING THE GOLDEN AGE (EVALUATION TIERS)",
                [
                    "At the end of your 10-year term, your full record is judged by Hammurabi:",
                    "",
                    "- TIER 4 (FANTASTIC): Starvation <= 3% AND Land >= 10 acres per citizen.",
                    "  \"Charlemagne, Disraeli, and Jefferson combined could not have done better!\"",
                    "- TIER 3 (MEDIOCRE): Starvation <= 10% AND Land >= 9 acres per citizen.",
                    "- TIER 2 (TYRANT): Smacks of Nero and Ivan IV. The people frankly hate your guts!",
                    "- TIER 1 (FINK): Starvation > 33% OR Land < 7 acres/person. Impeached and thrown out!",
                ]
            ),
        ]

        card_title, card_lines = tutorial_cards[self.tutorial_step]

        # Step progress indicator pills
        for s in range(5):
            dot_x = px + 360 + s * 32
            dot_rect = pygame.Rect(dot_x, py + 26, 22, 20)
            if s == self.tutorial_step:
                pygame.draw.rect(self.canvas, Palette.GOLD_LIGHT, dot_rect, border_radius=4)
                d_col = Palette.TEXT_DARK
            else:
                pygame.draw.rect(self.canvas, Palette.SAPPHIRE_BASE, dot_rect, border_radius=4)
                pygame.draw.rect(self.canvas, Palette.PANEL_BORDER, dot_rect, width=1, border_radius=4)
                d_col = Palette.TEXT_MUTED
            num_surf = FontManager.mono(11).render(str(s + 1), True, d_col)
            self.canvas.blit(num_surf, num_surf.get_rect(center=dot_rect.center))

        # Step indicator text
        step_str = f"STEP {self.tutorial_step + 1} OF 5"
        self.canvas.blit(FontManager.header(16).render(step_str, True, Palette.GOLD_LIGHT), (px + panel_w - 160, py + 26))

        # Card Title
        self.canvas.blit(FontManager.header(24).render(card_title, True, Palette.GOLD_PALE), (px + 60, py + 80))
        pygame.draw.line(self.canvas, Palette.GOLD_BASE, (px + 60, py + 115), (px + panel_w - 60, py + 115), 2)

        # Card Text
        cy = py + 140
        for cl in card_lines:
            col = Palette.GOLD_LIGHT if "TIER 4" in cl or "RULE OF THUMB" in cl else Palette.CRIMSON_LIGHT if "CATASTROPHIC" in cl or "PLAGUE" in cl else Palette.TEXT_BODY
            self.canvas.blit(FontManager.body(18).render(cl, True, col), (px + 60, cy))
            cy += 32

        # Step navigation buttons with visual disabled state
        self.btn_tutorial_prev.is_enabled = (self.tutorial_step > 0)
        self.btn_tutorial_next.is_enabled = (self.tutorial_step < 4)
        self.btn_tutorial_prev.draw(self.canvas)
        self.btn_tutorial_next.draw(self.canvas)

        # Bottom navigation hint
        nav_hint = FontManager.small(12).render("[← / →] Navigate Steps  |  [Esc] Menu", True, Palette.TEXT_MUTED)
        self.canvas.blit(nav_hint, (px + 60, py + panel_h - 52))

    # -----------------------------------------------------------------------
    # Main Game Loop
    # -----------------------------------------------------------------------

    def run(self) -> None:
        """Runs the 60 FPS event and rendering loop."""
        while self.is_running:
            dt = self.clock.tick(60) / 1000.0
            # Cap delta time to prevent physics jump on window drag
            dt = min(dt, 0.1) * self.animation_speed

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.is_running = False
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    if self.active_modal:
                        self.active_modal = None
                    elif self.current_screen == "GAMEPLAY":
                        self._open_pause_modal()
                    elif self.current_screen != "MAIN_MENU":
                        self._return_to_main_menu()
                else:
                    self.handle_event(event)

            self.update(dt)
            self.draw()

        pygame.quit()


def main() -> None:
    """CLI launcher for the graphical desktop application."""
    start_fullscreen = "--fullscreen" in sys.argv
    app = GameApp(start_fullscreen=start_fullscreen)
    app.run()


if __name__ == "__main__":
    main()
