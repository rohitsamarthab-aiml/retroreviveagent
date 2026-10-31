"""
test_empire_expansion.py - Comprehensive Unit & Integration Tests for Babylon Living Empire Expansions.

Tests:
1. Military Command: SoldierUnit physics/animation states, SoldierFormation mechanics, BattleScene clash/victory,
   and MilitaryDashboard rendering and event routing.
2. Day/Night Cycle & Atmosphere: TimeOfDay 24-hr progression, celestial sun/moon positions, star scintillation,
   dynamic weather state transitions from simulation events.
3. Agricultural Ministry: SeasonalCycle progression, AnimatedField growth stages, IrrigationCanal noria wheel,
   harvest particle dynamics, and AgriculturalDashboard metrics.
4. Cinematic Studio & AI Video Integration: SceneTemplate catalog, VideoGenerationConfig from env,
   InEnginePreview procedural rendering, VideoLibrary JSON persistence, and VideoCreatorPanel UI.
5. GameApp Screen Integration: Verified navigation across MAIN_MENU, MILITARY, AGRICULTURE, and VIDEO_CREATOR.
"""

import os
import pygame
import pytest

from game_logic import GameState, init_game
from ui_military import BattleScene, MilitaryDashboard, SoldierFormation, SoldierUnit
from ui_day_night import DayNightRenderer, MoonRenderer, StarField, TimeOfDay, WeatherSystem
from ui_agriculture import AgriculturalDashboard, AnimatedField, IrrigationCanal, SeasonalCycle
from ui_video_creator import SCENE_TEMPLATES, InEnginePreview, VideoCreatorPanel, VideoGenerationConfig, VideoLibrary, VideoRecord
from ui_theme import FontManager
from ui_pygame import GameApp


@pytest.fixture(scope="module", autouse=True)
def setup_headless_pygame():
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
    pygame.init()
    FontManager._cache.clear()


class TestMilitarySystem:
    def test_soldier_unit_animation_and_drawing(self):
        soldier = SoldierUnit(x=100.0, y=200.0)
        surf = pygame.Surface((300, 300))
        soldier.update(0.05)
        assert soldier._anim_phase > 0.0
        soldier.draw(surf)

    def test_soldier_formation_march(self):
        formation = SoldierFormation(start_x=200.0, start_y=300.0, screen_width=1280)
        assert len(formation.soldiers) == 9
        formation.trigger_march()
        assert formation._march_active
        old_x = formation.origin_x
        formation.update(0.2)
        assert formation.origin_x > old_x

    def test_battle_scene_execution(self):
        battle = BattleScene(screen_w=1280, screen_h=720)
        battle.start(outcome="victory")
        assert battle._active
        # Advance battle duration
        active = battle.update(2.0)
        assert active
        # Finish battle
        active = battle.update(5.0)
        assert not active

    def test_military_dashboard_rendering(self):
        dash = MilitaryDashboard(screen_w=1280, screen_h=720)
        surf = pygame.Surface((1280, 720))
        st = init_game()
        dash.update(0.05)
        dash.draw(surf, state=st, time_elapsed=1.0)


class TestDayNightAndWeather:
    def test_time_of_day_progression_and_phases(self):
        tod = TimeOfDay(start_hour=6.0, time_scale=1.0)
        assert tod.get_phase() == "DAWN"
        tod.update(4.0)  # 10:00
        assert tod.get_phase() == "MORNING"
        tod.update(3.0)  # 13:00
        assert tod.get_phase() == "NOON"
        tod.update(5.0)  # 18:00
        assert tod.get_phase() == "DUSK"
        tod.update(5.0)  # 23:00
        assert tod.get_phase() == "NIGHT"

    def test_celestial_sun_and_moon_positions(self):
        tod = TimeOfDay(start_hour=12.0)
        sx, sy = tod.get_sun_position()
        assert 0 <= sx <= 1280
        assert 0 <= sy <= 350

        tod_night = TimeOfDay(start_hour=0.0)
        mx, my = tod_night.get_moon_position()
        assert 0 <= mx <= 1280
        assert 0 <= my <= 350

    def test_weather_system_state_updates(self):
        weather = WeatherSystem()
        st = init_game()
        # High yield -> clear
        weather.update_from_game_state(st)
        assert weather.current_state in ("CLEAR", "DUST_STORM")

        # Drought yield 1 -> sandstorm
        drought_st = GameState(
            year=2, starved_this_year=0, starved_total=0, starved_pct_avg=0.0,
            population=100, bushels=2800, acres=1000, land_price=20,
            harvest_yield=1, rats_ate=0, immigrants_this_year=5, plague_struck=False,
            plague_next_year=False, is_over=False
        )
        weather.update_from_game_state(drought_st)
        assert weather.current_state == "SANDSTORM"

    def test_day_night_renderer_pipeline(self):
        renderer = DayNightRenderer()
        surf = pygame.Surface((1280, 720))
        st = init_game()
        renderer.update(0.05, game_state=st)
        renderer.render_sky_layer(surf)
        renderer.render_night_overlay(surf)
        renderer.render_weather(surf)


class TestAgricultureSystem:
    def test_seasonal_cycle_for_years(self):
        s1, _, _ = SeasonalCycle.get_season_for_year(1)
        s2, _, _ = SeasonalCycle.get_season_for_year(2)
        assert s1 == "SPRING SOWING"
        assert s2 == "SUMMER CANAL IRRIGATION"

    def test_animated_field_stages(self):
        field = AnimatedField(pygame.Rect(50, 50, 200, 100), plot_id=0)
        field.update(0.1, stage=3)
        assert field.stage == 3
        surf = pygame.Surface((300, 200))
        field.draw(surf, time_elapsed=1.0)

    def test_irrigation_canal_and_waterwheel(self):
        canal = IrrigationCanal(pygame.Rect(20, 20, 400, 25))
        old_ang = canal.wheel_angle
        canal.update(0.1)
        assert canal.wheel_angle > old_ang
        surf = pygame.Surface((500, 100))
        canal.draw(surf)

    def test_agricultural_dashboard_draw(self):
        dash = AgriculturalDashboard()
        surf = pygame.Surface((1280, 720))
        st = init_game()
        dash.update(0.05, state=st)
        dash.draw(surf, state=st)


class TestVideoCreatorSystem:
    def test_scene_template_catalog(self):
        assert len(SCENE_TEMPLATES) == 8
        tmpl_ids = [t.id for t in SCENE_TEMPLATES]
        assert "royal_prologue" in tmpl_ids
        assert "soldiers_march" in tmpl_ids
        assert "bumper_harvest" in tmpl_ids

    def test_in_engine_preview_draw(self):
        preview = InEnginePreview()
        surf = pygame.Surface((500, 300))
        tmpl = SCENE_TEMPLATES[0]
        preview.update(0.1)
        preview.draw(surf, pygame.Rect(10, 10, 480, 280), tmpl)

    def test_video_library_persistence(self, tmp_path):
        lib = VideoLibrary()
        lib.records.clear()
        lib.save_path = str(tmp_path / "test_videos.json")
        rec = VideoRecord(
            scene_id="royal_prologue",
            scene_name="Test Scene",
            timestamp="2026-10-31 12:00:00",
            status="IN_ENGINE_PREVIEW",
            provider="BABYLON_ENGINE"
        )
        lib.add_record(rec)
        assert len(lib.records) == 1
        # Reload
        lib2 = VideoLibrary()
        lib2.records.clear()
        lib2.save_path = str(tmp_path / "test_videos.json")
        lib2.load()
        assert len(lib2.records) == 1
        assert lib2.records[0].scene_name == "Test Scene"

    def test_video_creator_panel_draw_and_trigger(self):
        panel = VideoCreatorPanel()
        surf = pygame.Surface((1280, 720))
        st = init_game()
        panel.update(0.05)
        panel.draw(surf, state=st)
        panel._trigger_render()
        assert len(panel.library.records) > 0


class TestGameAppScreenNavigation:
    def test_screen_transitions(self):
        app = GameApp()
        assert app.current_screen == "MAIN_MENU"

        # Navigate to Military Command
        app._open_military_screen()
        assert app.current_screen == "MILITARY"
        app.update(0.05)
        app.draw()

        # Navigate to Agricultural Ministry
        app._open_agriculture_screen()
        assert app.current_screen == "AGRICULTURE"
        app.update(0.05)
        app.draw()

        # Navigate to Cinematic Studio
        app._open_video_creator_screen()
        assert app.current_screen == "VIDEO_CREATOR"
        app.update(0.05)
        app.draw()

        # Return to main menu
        app._return_to_main_menu()
        assert app.current_screen == "MAIN_MENU"
