"""
ui_agriculture.py - Agricultural Ministry, Crop Cultivation & Irrigation Simulation.

Features:
- Seasonal Mesopotamia agrarian cycle (Spring Sowing, Summer Nurturing, Autumn Harvest, Winter Fallow)
- Multi-stage crop cultivation plots (Bare Soil -> Sown -> Sprouting -> Golden Mature -> Reaped)
- Dynamic Euphrates irrigation canal network with turning waterwheels
- Real-time animated harvesting farmers and golden grain chaff particle physics
- Comprehensive Agricultural Dashboard displaying Land Cultivation %, Food Security Index,
  Granary Reserves, and labor allocation
"""

import math
import random
from typing import List, Optional, Tuple
import pygame

from game_logic import GameState
from ui_theme import FontManager, Palette, SoundSynthesizer, UIButton


class SeasonalCycle:
    """Mesopotamian agricultural seasons linked to simulation progression."""

    SEASONS = ["SPRING SOWING", "SUMMER CANAL IRRIGATION", "AUTUMN BUMPER HARVEST", "WINTER GRANARY STORAGE"]
    DESCRIPTIONS = [
        "Silt-rich floods recede; oxen plow furrows and farmers sow barley across all alluvial plains.",
        "Scorching sun dominates; sluice gates open to flood the irrigation canal networks.",
        "Fields gleam with golden grain; reapers sweep through the rows with curved bronze sickles.",
        "Surplus grain is stored in royal sealed silos; field canals are cleared of silt for the new term.",
    ]

    @classmethod
    def get_season_for_year(cls, year: int) -> Tuple[str, str, Tuple[int, int, int]]:
        idx = (year - 1) % 4
        season = cls.SEASONS[idx]
        desc = cls.DESCRIPTIONS[idx]
        colors = [
            Palette.PALM_GREEN,
            Palette.GOLD_BASE,
            Palette.GOLD_LIGHT,
            Palette.CLAY_DEEP,
        ]
        return season, desc, colors[idx]


class AnimatedField:
    """Individual agricultural plot with waving crops and seasonal growth stages."""

    def __init__(self, rect: pygame.Rect, plot_id: int) -> None:
        self.rect = rect
        self.plot_id = plot_id
        self.stage = 3  # 0=plowed, 1=sown, 2=sprouting, 3=mature, 4=reaped
        self.time = random.uniform(0.0, 6.28)

    def update(self, dt: float, stage: int) -> None:
        self.time += dt
        self.stage = stage

    def draw(self, surface: pygame.Surface, time_elapsed: float) -> None:
        r = self.rect
        # Furrowed earth base
        pygame.draw.rect(surface, (68, 46, 26), r, border_radius=4)
        pygame.draw.rect(surface, Palette.CLAY_DEEP, r, width=2, border_radius=4)

        # Furrow lines
        for y in range(r.top + 8, r.bottom - 4, 12):
            pygame.draw.line(surface, (45, 30, 18), (r.left + 6, y), (r.right - 6, y), 2)

        # Crop stalks based on stage
        if self.stage == 1:
            # Seed dots
            for x in range(r.left + 12, r.right - 10, 18):
                for y in range(r.top + 10, r.bottom - 6, 14):
                    pygame.draw.circle(surface, (180, 145, 90), (x, y), 2)

        elif self.stage == 2:
            # Young green sprouts
            sway = math.sin(time_elapsed * 4.0 + self.plot_id) * 2.0
            for x in range(r.left + 10, r.right - 8, 14):
                for y in range(r.top + 12, r.bottom - 6, 14):
                    pygame.draw.line(surface, Palette.CROP_GREEN, (x, y), (x + int(sway), y - 7), 2)

        elif self.stage >= 3:
            # Mature golden barley/wheat
            sway = math.sin(time_elapsed * 3.2 + self.plot_id * 0.7) * 4.0
            stalk_col = Palette.CROP_GOLD if self.stage == 3 else (160, 120, 50)
            for x in range(r.left + 8, r.right - 6, 10):
                for y in range(r.top + 14, r.bottom - 6, 12):
                    top_x = x + int(sway)
                    pygame.draw.line(surface, stalk_col, (x, y), (top_x, y - 11), 2)
                    # Grain head ear
                    pygame.draw.circle(surface, Palette.GOLD_LIGHT, (top_x, y - 12), 2)


class IrrigationCanal:
    """Animated irrigation canal with flowing waters and turning noria waterwheel."""

    def __init__(self, rect: pygame.Rect) -> None:
        self.rect = rect
        self.time = 0.0
        self.wheel_angle = 0.0

    def update(self, dt: float) -> None:
        self.time += dt
        self.wheel_angle += 1.8 * dt

    def draw(self, surface: pygame.Surface) -> None:
        r = self.rect
        # Stone embankment
        pygame.draw.rect(surface, (110, 95, 75), r)
        # Flowing blue water
        water_rect = pygame.Rect(r.left + 4, r.top + 4, r.width - 8, r.height - 8)
        pygame.draw.rect(surface, (35, 80, 120), water_rect)

        # Sinusoidal wave caustics
        for i in range(r.width // 40):
            wx = r.left + 8 + i * 40 + int(self.time * 26.0) % 40
            wy = r.centery + int(math.sin(self.time * 4.0 + i) * 3)
            if r.left < wx < r.right - 20:
                pygame.draw.arc(surface, (140, 200, 240, 180), (wx, wy - 3, 22, 6), 0.2, 2.9, width=2)

        # Noria Wooden Waterwheel at canal junction
        wheel_cx = r.left + 24
        wheel_cy = r.centery
        wheel_r = 16
        pygame.draw.circle(surface, (80, 50, 25), (wheel_cx, wheel_cy), wheel_r, width=3)
        pygame.draw.circle(surface, Palette.GOLD_DARK, (wheel_cx, wheel_cy), 3)
        for spk in [0.0, 1.05, 2.09, 3.14, 4.19, 5.24]:
            ang = self.wheel_angle + spk
            ex = wheel_cx + int(math.cos(ang) * wheel_r)
            ey = wheel_cy + int(math.sin(ang) * wheel_r)
            pygame.draw.line(surface, (95, 60, 30), (wheel_cx, wheel_cy), (ex, ey), 2)


class HarvestParticle:
    """Golden chaff particle floating from the harvest."""

    def __init__(self, x: float, y: float) -> None:
        self.x = x
        self.y = y
        self.vx = random.uniform(-25, 25)
        self.vy = random.uniform(-40, -10)
        self.life = random.uniform(0.8, 1.6)
        self.max_life = self.life
        self.size = random.randint(2, 4)

    def update(self, dt: float) -> bool:
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.life -= dt
        return self.life > 0

    def draw(self, surface: pygame.Surface) -> None:
        alpha = int((self.life / self.max_life) * 255)
        s = pygame.Surface((self.size * 2, self.size * 2), pygame.SRCALPHA)
        pygame.draw.circle(s, (245, 215, 110, alpha), (self.size, self.size), self.size)
        surface.blit(s, (int(self.x) - self.size, int(self.y) - self.size))


class AgriculturalDashboard:
    """Full-screen Agricultural Ministry Command Screen."""

    def __init__(self, on_return: Optional[callable] = None) -> None:
        self.on_return = on_return
        self.time_elapsed = 0.0

        # Plots setup (6 dynamic plots)
        self.plots: List[AnimatedField] = []
        start_x, start_y = 60, 260
        plot_w, plot_h = 240, 130
        for row in range(2):
            for col in range(3):
                px = start_x + col * (plot_w + 35)
                py = start_y + row * (plot_h + 35)
                self.plots.append(AnimatedField(pygame.Rect(px, py, plot_w, plot_h), len(self.plots)))

        # Irrigation canals running between plots
        self.canals: List[IrrigationCanal] = [
            IrrigationCanal(pygame.Rect(50, 400, 830, 20)),
            IrrigationCanal(pygame.Rect(310, 245, 20, 310)),
            IrrigationCanal(pygame.Rect(585, 245, 20, 310)),
        ]

        self.particles: List[HarvestParticle] = []
        self.btn_return = UIButton((50, 645, 220, 44), "← RETURN TO EMPIRE", self._return_action, color_scheme="gold")

    def _return_action(self) -> None:
        if self.on_return:
            self.on_return()

    def update(self, dt: float, state: Optional[GameState] = None) -> None:
        self.time_elapsed += dt
        yield_rate = getattr(state, "harvest_yield", 3) if state else 3
        # Select plot growth stage based on yield
        stage = 3 if yield_rate >= 3 else (2 if yield_rate == 2 else 1)
        for plot in self.plots:
            plot.update(dt, stage)
        for canal in self.canals:
            canal.update(dt)

        # Spontaneous harvest chaff particles
        if random.random() < 0.35:
            self.particles.append(HarvestParticle(random.uniform(70, 860), random.uniform(270, 560)))

        self.particles = [p for p in self.particles if p.update(dt)]

    def handle_event(self, event: pygame.event.Event, mouse_pos: Tuple[int, int]) -> bool:
        if self.btn_return.handle_event(event, mouse_pos):
            return True
        return False

    def draw(self, surface: pygame.Surface, state: Optional[GameState] = None) -> None:
        # 1. Warm agrarian background
        surface.fill((28, 22, 16))

        # Top Header Bar (Deep Sapphire Glass with Gold Filigree)
        hdr_rect = pygame.Rect(0, 0, 1280, 68)
        pygame.draw.rect(surface, Palette.SAPPHIRE_PANEL, hdr_rect)
        pygame.draw.line(surface, Palette.GOLD_BASE, (0, 68), (1280, 68), 2)

        title = FontManager.header(20).render("AGRICULTURAL MINISTRY — BABYLONIAN BREADBASKET", True, Palette.GOLD_LIGHT)
        sub = FontManager.small(12).render("Euphrates Alluvial Irrigation  •  Cereal Cultivation  •  Granary Preservation", True, Palette.SAND_LIGHT)
        surface.blit(title, (40, 14))
        surface.blit(sub, (40, 40))

        # Seasonal status card
        year = getattr(state, "year", 1) if state else 1
        s_title, s_desc, s_color = SeasonalCycle.get_season_for_year(year)
        s_card = pygame.Rect(50, 85, 830, 145)
        pygame.draw.rect(surface, Palette.SAPPHIRE_PANEL, s_card, border_radius=8)
        pygame.draw.rect(surface, Palette.GOLD_BASE, s_card, width=2, border_radius=8)

        season_badge = FontManager.header(17).render(f"CURRENT SEASON: {s_title}", True, s_color)
        season_desc = FontManager.body(13).render(s_desc, True, Palette.TEXT_BODY)
        surface.blit(season_badge, (75, 102))
        surface.blit(season_desc, (75, 134))

        # Agrarian summary pill
        yield_rate = getattr(state, "harvest_yield", 3) if state else 3
        yield_str = f"Estimated Yield: {yield_rate} bushels/acre"
        surface.blit(FontManager.small(13).render(yield_str, True, Palette.GOLD_LIGHT), (75, 172))

        # 2. Draw Canals
        for canal in self.canals:
            canal.draw(surface)

        # 3. Draw Cultivation Plots
        for plot in self.plots:
            plot.draw(surface, self.time_elapsed)

        # 4. Draw Harvest Particles
        for p in self.particles:
            p.draw(surface)

        # -------------------------------------------------------------
        # Right Side: Imperial Agricultural Metric Ledger
        # -------------------------------------------------------------
        ledger_rect = pygame.Rect(915, 85, 320, 600)
        pygame.draw.rect(surface, Palette.SAPPHIRE_PANEL, ledger_rect, border_radius=10)
        pygame.draw.rect(surface, Palette.GOLD_BASE, ledger_rect, width=2, border_radius=10)

        l_hdr = FontManager.header(18).render("AGRARIAN LEDGER", True, Palette.GOLD_PALE)
        surface.blit(l_hdr, l_hdr.get_rect(center=(915 + 160, 115)))
        pygame.draw.line(surface, Palette.GOLD_BASE, (935, 138), (1215, 138), 1)

        pop = getattr(state, "population", 100) if state else 100
        bushels = getattr(state, "bushels", 2800) if state else 2800
        acres = getattr(state, "acres", 1000) if state else 1000

        food_security = min(100.0, (bushels / max(1, pop * 20)) * 100.0)
        farmer_count = pop // 5
        storage_util = min(100.0, (bushels / 8000.0) * 100.0)
        land_util = min(100.0, (acres / 1500.0) * 100.0)

        metrics = [
            ("TOTAL CULTIVATED LAND", f"{acres:,} Acres", Palette.SAND_LIGHT),
            ("STORED GRAIN SURPLUS", f"{bushels:,} Bushels", Palette.GOLD_LIGHT),
            ("POPULATION SUSTENANCE", f"{pop:,} Citizens", Palette.TEXT_BODY),
            ("ACTIVE FARMER WORKFORCE", f"{farmer_count:,} Reapers", Palette.PALM_GREEN),
            ("HARVEST PRODUCTIVITY", f"{yield_rate} bu / acre", Palette.GOLD_LIGHT),
            ("FOOD SECURITY INDEX", f"{food_security:.1f}%", Palette.GOLD_BASE if food_security >= 100 else Palette.CRIMSON_LIGHT),
        ]

        cur_y = 155
        for m_lbl, m_val, m_col in metrics:
            surface.blit(FontManager.small(11).render(m_lbl, True, Palette.TEXT_MUTED), (935, cur_y))
            surface.blit(FontManager.header(15).render(m_val, True, m_col), (935, cur_y + 16))
            cur_y += 42

        pygame.draw.line(surface, Palette.PANEL_BORDER, (935, cur_y + 4), (1215, cur_y + 4), 1)
        cur_y += 18

        # Progress bars: Food Security & Granary Storage
        def draw_progress(label: str, pct: float, y_pos: int, color: Tuple[int, int, int]) -> None:
            surface.blit(FontManager.small(12).render(f"{label}: {pct:.0f}%", True, Palette.TEXT_BODY), (935, y_pos))
            bar_bg = pygame.Rect(935, y_pos + 18, 280, 14)
            pygame.draw.rect(surface, (25, 20, 18), bar_bg, border_radius=4)
            fill_w = int(280 * (min(100.0, pct) / 100.0))
            if fill_w > 0:
                pygame.draw.rect(surface, color, (935, y_pos + 18, fill_w, 14), border_radius=4)
            pygame.draw.rect(surface, Palette.PANEL_BORDER, bar_bg, width=1, border_radius=4)

        draw_progress("Grain Satiety Index", food_security, cur_y, Palette.CROP_GREEN if food_security >= 100 else Palette.CRIMSON_LIGHT)
        draw_progress("Granary Silo Fill Rate", storage_util, cur_y + 44, Palette.GOLD_BASE)
        draw_progress("Crown Land Utilization", land_util, cur_y + 88, Palette.SAND_LIGHT)

        # Return Button
        self.btn_return.draw(surface)
