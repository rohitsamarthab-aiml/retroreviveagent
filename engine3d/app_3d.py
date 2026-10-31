"""
app_3d.py - Master 3D Game Application for RetroRevive: The Living Empire.

Combines the full 3D hardware-accelerated Panda3D engine with authentic
ancient Babylonian simulation gameplay:
- Full 3D explorable kingdom: Ziggurat, Ishtar Gate, Palace, River, Canals, Farms, Walls
- 3D King Hammurabi upon the Lion Throne
- Living animated entities: Phalanxes, Sentries, Farmers, Citizens, Donkeys & Carts
- 6-Mode Cinematic Camera with smooth spline interpolation and free orbit
- Diurnal celestial lighting and state-reactive weather
- 8 Signature 3D cinematic events
- Sophisticated Royal Navy & Gold Management HUD overlay
- Direct integration with game_logic.py and modern_game_logic.py
"""

import os
import sys
from typing import Dict, Optional, Tuple
from direct.showbase.ShowBase import ShowBase
from direct.gui.OnscreenText import OnscreenText
from direct.gui.DirectGui import (
    DirectButton,
    DirectEntry,
    DirectFrame,
    DirectLabel,
)
from panda3d.core import (
    AntialiasAttrib,
    ClockObject,
    PandaNode,
    TextNode,
    Vec3,
    Vec4,
    WindowProperties,
    loadPrcFileData,
)

from game_logic import (
    GameState,
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
    EnhancedGameState,
    get_advisor_advice,
    init_enhanced_game,
    step_enhanced_year,
)
from engine3d.atmosphere_3d import Atmosphere3D
from engine3d.babylon_world import BabylonWorld3D
from engine3d.camera_system import CameraController3D, PRESETS
from engine3d.cinematics_3d import CinematicDirector3D
from engine3d.entities_3d import EntitiesManager3D
from engine3d.hammurabi_model import RoyalCourtScene3D
from engine3d.texture_manager import TextureManager
from engine3d.sky_dome import SkyDome
from engine3d.vegetation_3d import VegetationManager


# Premium Royal Babylonian UI Color Scheme
UI_NAVY = (0.06, 0.08, 0.16, 0.92)
UI_GOLD = (0.92, 0.78, 0.28, 1.0)
UI_SAND = (0.85, 0.75, 0.60, 1.0)
UI_CRIMSON = (0.65, 0.15, 0.15, 1.0)
UI_LAPIS = (0.10, 0.25, 0.50, 0.95)


class BabylonApp3D(ShowBase):
    """Master 3D Game Controller managing 3D world, camera, and simulation HUD."""

    def __init__(
        self,
        headless: bool = False,
        quality: str = "HIGH",
        on_exit: Optional[callable] = None,
    ) -> None:
        self.headless = headless
        self.quality = quality
        self.on_exit = on_exit

        # Configure Panda3D window properties
        if headless:
            loadPrcFileData("", "window-type none")
            loadPrcFileData("", "audio-library-name null")
        else:
            loadPrcFileData("", "window-title RetroRevive: The Living Empire (3D)")
            loadPrcFileData("", "win-size 1280 720")
            loadPrcFileData("", "show-frame-rate-meter #t")
            loadPrcFileData("", "sync-video #t")

        super().__init__()

        if not headless and hasattr(self, "win") and self.win:
            self.render.set_antialias(AntialiasAttrib.MAuto)

        # 0. Preload all procedural textures (sandstone, lapis, marble, etc.)
        self._texture_manager = TextureManager.instance()
        try:
            self._texture_manager.preload_all()
        except Exception:
            pass  # graceful fallback if PIL unavailable

        # 1. 3D Lighting & Atmosphere
        self.atmosphere = Atmosphere3D(self.render)

        # 1b. Sky dome with golden-hour gradient + clouds
        self._sky_dome: "SkyDome | None" = None
        if not headless:
            try:
                self._sky_dome = SkyDome(self.render)
            except Exception:
                pass

        # 2. 3D Architectural Metropolis
        self.world = BabylonWorld3D(self.render)
        # Apply procedural textures to all geometry
        try:
            self.world.apply_textures()
        except Exception:
            pass

        # 2b. Palm trees & vegetation matching reference images
        self._vegetation: "VegetationManager | None" = None
        try:
            self._vegetation = VegetationManager(self.render)
            self._vegetation.setup_babylon_vegetation()
        except Exception:
            pass

        # 3. 3D Royal Court with King Hammurabi on Lion Throne
        self.court = RoyalCourtScene3D(self.render, pos=Vec3(75.0, 75.0, 0))

        # 4. Living Animated 3D Entities
        self.entities = EntitiesManager3D(self.render)

        # In headless mode, ensure camera node exists
        if self.camera is None:
            self.camera = self.render.attach_new_node("headless_camera")

        # 5. Cinematic 6-Mode Camera Controller
        self.camera_ctrl = CameraController3D(self.camera)

        # 6. 3D Cinematic Director
        self.cinematics = CinematicDirector3D(self.camera_ctrl, self.atmosphere)

        # 7. Core Hammurabi Simulation Game State
        self.game_mode = "ENHANCED"
        self.enhanced_state: Optional[EnhancedGameState] = init_enhanced_game("ENHANCED")
        self.classic_state: Optional[GameState] = self.enhanced_state.classic_state

        # Command inputs
        self.input_buy_val = 0
        self.input_sell_val = 0
        self.input_feed_val = 2000
        self.input_plant_val = 1000

        self.is_command_deck_visible = True
        self.status_toast = "Welcome to Babylon, Sovereign Hammurabi. Issue your royal decree."
        self.toast_timer = 4.0

        # Build 2D/3D HUD Overlay
        if not headless:
            self._setup_hud_overlay()
            self._setup_key_bindings()

        # Connect simulation state to 3D world
        self._sync_world_to_simulation()

        # Main update task loop
        self.taskMgr.add(self._update_loop, "babylon_update_task")

    def _sync_world_to_simulation(self) -> None:
        st = self._get_current_game_state()
        if st:
            self.world.update_from_game_state(st)
            self.atmosphere.update_from_game_state(st)

    def _get_current_game_state(self) -> GameState:
        if self.game_mode == "ENHANCED" and self.enhanced_state:
            return self.enhanced_state.classic_state
        return self.classic_state

    def _setup_hud_overlay(self) -> None:
        """Constructs the royal navy and gold management HUD on pixel2d / aspect2d."""
        # Top HUD Bar (Title & State Metrics)
        self.top_bar = DirectFrame(
            frameColor=UI_NAVY,
            frameSize=(-1.8, 1.8, -0.07, 0.07),
            pos=(0, 0, 0.92),
        )

        self.title_text = OnscreenText(
            text="RETROREVIVE: THE LIVING EMPIRE  •  YEAR 1 OF 10",
            pos=(-1.2, 0.905),
            scale=0.045,
            fg=UI_GOLD,
            align=TextNode.ALeft,
            mayChange=True,
        )

        self.metrics_text = OnscreenText(
            text="POP: 100 | GRAIN: 2,800 bu | LAND: 1,000 ac | PRICE: 20 bu/ac | YIELD: 3 bu/ac",
            pos=(1.2, 0.905),
            scale=0.038,
            fg=UI_SAND,
            align=TextNode.ARight,
            mayChange=True,
        )

        # Camera Viewport Presets Dock (Top Left)
        self.cam_dock = DirectFrame(
            frameColor=UI_NAVY,
            frameSize=(-0.75, 0.75, -0.05, 0.05),
            pos=(0, 0, 0.81),
        )

        cam_buttons = [
            ("AERIAL", "AERIAL_KINGDOM", -0.60),
            ("THRONE", "THRONE_ROOM", -0.36),
            ("ISHTAR", "ISHTAR_PROCESSION", -0.12),
            ("AGRI", "AGRARIAN_MINISTRY", 0.12),
            ("ARMY", "MILITARY_COMMAND", 0.36),
            ("FLY", "FREE_ORBIT", 0.60),
        ]
        for label, preset, x_pos in cam_buttons:
            DirectButton(
                text=label,
                scale=0.035,
                pos=(x_pos, 0, 0.80),
                frameColor=UI_LAPIS,
                text_fg=UI_GOLD,
                command=lambda p=preset: self.set_camera_preset(p),
            )

        # Status Toast Text (Center Top)
        self.toast_text = OnscreenText(
            text=self.status_toast,
            pos=(0, 0.72),
            scale=0.04,
            fg=UI_GOLD,
            align=TextNode.ACenter,
            mayChange=True,
        )

        # Command Deck Panel (Bottom Center)
        self.deck_frame = DirectFrame(
            frameColor=UI_NAVY,
            frameSize=(-1.25, 1.25, -0.16, 0.16),
            pos=(0, 0, -0.78),
        )

        # Action decree buttons
        DirectButton(
            text="ENACT DECREE",
            scale=0.045,
            pos=(0.85, 0, -0.78),
            frameColor=UI_GOLD,
            text_fg=(0.1, 0.08, 0.05, 1.0),
            command=self.execute_turn_decree,
        )

        DirectButton(
            text="ROYAL ADVISORS",
            scale=0.035,
            pos=(-0.95, 0, -0.78),
            frameColor=UI_LAPIS,
            text_fg=UI_GOLD,
            command=self.consult_advisors,
        )

        DirectButton(
            text="3D CINEMATICS",
            scale=0.035,
            pos=(-0.55, 0, -0.78),
            frameColor=UI_LAPIS,
            text_fg=UI_GOLD,
            command=self.play_next_cinematic,
        )

        # Instructions / Controls Hint (Bottom)
        OnscreenText(
            text="[1-6] Camera Presets | [T] Throne | [M] Military | [A] Agriculture | [Space] Enact Decree | [P] Prologue",
            pos=(0, -0.96),
            scale=0.032,
            fg=UI_SAND,
            align=TextNode.ACenter,
        )

    def _setup_key_bindings(self) -> None:
        self.accept("1", self.set_camera_preset, ["AERIAL_KINGDOM"])
        self.accept("2", self.set_camera_preset, ["THRONE_ROOM"])
        self.accept("3", self.set_camera_preset, ["ISHTAR_PROCESSION"])
        self.accept("4", self.set_camera_preset, ["AGRARIAN_MINISTRY"])
        self.accept("5", self.set_camera_preset, ["MILITARY_COMMAND"])
        self.accept("6", self.set_camera_preset, ["FREE_ORBIT"])

        self.accept("t", self.set_camera_preset, ["THRONE_ROOM"])
        self.accept("m", self.set_camera_preset, ["MILITARY_COMMAND"])
        self.accept("a", self.set_camera_preset, ["AGRARIAN_MINISTRY"])
        self.accept("p", self.cinematics.play_event, ["royal_court"])

        self.accept("space", self.execute_turn_decree)
        self.accept("escape", self._on_escape_pressed)

        # Arrow keys for free orbit
        self.accept("arrow_left", self.camera_ctrl.set_free_orbit, [-10.0, 0, 0])
        self.accept("arrow_right", self.camera_ctrl.set_free_orbit, [10.0, 0, 0])
        self.accept("arrow_up", self.camera_ctrl.set_free_orbit, [0, 5.0, 0])
        self.accept("arrow_down", self.camera_ctrl.set_free_orbit, [0, -5.0, 0])
        self.accept("wheel_up", self.camera_ctrl.set_free_orbit, [0, 0, -15.0])
        self.accept("wheel_down", self.camera_ctrl.set_free_orbit, [0, 0, 15.0])

    def set_camera_preset(self, preset_name: str) -> None:
        self.camera_ctrl.set_preset(preset_name)
        if preset_name in PRESETS:
            self.show_toast(f"Camera: {PRESETS[preset_name].name}")

    def show_toast(self, message: str) -> None:
        self.status_toast = message
        self.toast_timer = 4.0
        if hasattr(self, "toast_text"):
            self.toast_text.setText(message)

    def consult_advisors(self) -> None:
        st = self._get_current_game_state()
        advice = get_advisor_advice(st)
        self.court.king.set_speaking(True)
        self.show_toast(f"Grand Vizier: '{advice.vizier}' (Feed: {advice.recommended_feed} bu)")

    def play_next_cinematic(self) -> None:
        events = ["royal_court", "golden_harvest", "military_march", "ishtar_celebration", "scorched_drought"]
        idx = getattr(self, "_cine_idx", 0)
        evt = events[idx % len(events)]
        self._cine_idx = idx + 1
        self.show_toast(f"Playing 3D Cinematic: {evt.replace('_', ' ').title()}")
        self.cinematics.play_event(evt)

    def execute_turn_decree(self) -> None:
        """Advances the simulation turn and updates 3D kingdom world."""
        st = self._get_current_game_state()
        if not st or st.is_over:
            return

        decisions = TurnDecisions(
            buy_acres=self.input_buy_val,
            sell_acres=self.input_sell_val,
            feed_bushels=min(st.bushels, st.population * 20),
            plant_acres=min(st.acres, st.population * 10),
        )

        prior_pop = st.population
        if self.game_mode == "ENHANCED" and self.enhanced_state:
            self.enhanced_state = step_enhanced_year(self.enhanced_state, decisions)
            new_st = self.enhanced_state.classic_state
        else:
            self.classic_state = step_year(self.classic_state, decisions)
            new_st = self.classic_state

        # Update 3D world geometry to reflect new game state
        self._sync_world_to_simulation()

        # King reaction
        self.court.king.set_speaking(True)

        # Report toast
        starved = new_st.starved_this_year
        if starved > 0:
            self.show_toast(f"Year {new_st.year}: Famine struck! {starved} citizens starved.")
        elif new_st.plague_struck:
            self.show_toast(f"Year {new_st.year}: The Plague swept the land! Population halved.")
        else:
            self.show_toast(f"Year {new_st.year}: Harvest yield {new_st.harvest_yield} bu/ac. Kingdom prosperous!")

        # Refresh HUD text
        self._refresh_hud_metrics(new_st)

    def _refresh_hud_metrics(self, st: GameState) -> None:
        if hasattr(self, "title_text"):
            self.title_text.setText(f"RETROREVIVE: THE LIVING EMPIRE  •  YEAR {st.year} OF 10")
        if hasattr(self, "metrics_text"):
            self.metrics_text.setText(
                f"POP: {st.population:,} | GRAIN: {st.bushels:,} bu | LAND: {st.acres:,} ac | "
                f"PRICE: {st.land_price} bu/ac | YIELD: {st.harvest_yield} bu/ac"
            )

    def _on_escape_pressed(self) -> None:
        if self.cinematics.is_playing():
            self.cinematics.stop_current()
            self.show_toast("Cinematic skipped.")
        elif self.on_exit:
            self.on_exit()
        else:
            self.userExit()

    def _update_loop(self, task):
        dt = globalClock.get_dt()
        dt = min(dt, 0.1)

        # Update sub-systems
        self.atmosphere.update(dt)
        self.world.update(dt)
        self.court.update(dt)
        self.entities.update(dt)
        self.camera_ctrl.update(dt)
        self.cinematics.update(dt)

        # Update sky dome clouds + sun position
        if self._sky_dome is not None:
            try:
                self._sky_dome.update(dt)
            except Exception:
                pass

        # Toast fade
        if self.toast_timer > 0:
            self.toast_timer -= dt

        return task.cont
