"""
ui_day_night.py - Dynamic Day/Night Cycle, Celestial Rendering & Atmospheric Weather System.

Provides authentic Mesopotamian environmental progression:
- 24-hour diurnal lighting cycle (Dawn, Morning, Noon, Afternoon, Dusk, Evening, Night, Midnight)
- Dynamic celestial vault: Golden sun corona, lunar cycle with crescent/full phases, and twinkling star field
- Dynamic weather systems linked to simulation state: Clear, Overcast, Torrents of the Euphrates,
  and Arid Desert Dust Storms
- Atmospheric ambient color grading washes and lighting calculation
"""

import math
import random
from typing import List, Optional, Tuple
import pygame

from game_logic import GameState


class TimeOfDay:
    """Manages continuous diurnal time progression and lighting interpolation."""

    # Pre-defined sky gradients: (top_color, bottom_color)
    PHASE_COLORS = {
        "DAWN": ((60, 30, 80), (255, 120, 60)),
        "MORNING": ((80, 140, 200), (255, 210, 130)),
        "NOON": ((30, 90, 180), (200, 220, 255)),
        "AFTERNOON": ((50, 110, 190), (255, 190, 100)),
        "DUSK": ((30, 20, 60), (255, 80, 30)),
        "EVENING": ((15, 10, 40), (100, 40, 60)),
        "NIGHT": ((5, 5, 20), (20, 15, 40)),
        "MIDNIGHT": ((3, 3, 15), (10, 8, 25)),
    }

    def __init__(self, start_hour: float = 7.0, time_scale: float = 0.5) -> None:
        self.hour = start_hour  # 0.0 - 24.0
        self.time_scale = time_scale  # hours per real second
        self.day_count = 1

    def update(self, dt: float) -> None:
        self.hour += self.time_scale * dt
        if self.hour >= 24.0:
            self.hour -= 24.0
            self.day_count += 1

    def advance_to_next_day(self) -> None:
        """Called when a game year steps forward; resets to early morning golden hour."""
        self.hour = 7.0
        self.day_count += 1

    def get_phase(self) -> str:
        h = self.hour
        if 5.0 <= h < 7.0:
            return "DAWN"
        elif 7.0 <= h < 11.5:
            return "MORNING"
        elif 11.5 <= h < 14.0:
            return "NOON"
        elif 14.0 <= h < 17.5:
            return "AFTERNOON"
        elif 17.5 <= h < 19.5:
            return "DUSK"
        elif 19.5 <= h < 22.0:
            return "EVENING"
        elif 22.0 <= h < 24.0 or 0.0 <= h < 3.0:
            return "NIGHT"
        else:
            return "MIDNIGHT"

    def get_light_intensity(self) -> float:
        """Returns 0.0 (pitch dark) to 1.0 (bright midday)."""
        # Peak at 12:30, lowest at 00:30
        angle = ((self.hour - 6.0) / 12.0) * math.pi
        val = math.sin(angle)
        return max(0.08, min(1.0, (val + 1.0) / 2.0))

    def get_star_visibility(self) -> float:
        """Returns 1.0 during midnight/night, fades to 0.0 during daylight."""
        light = self.get_light_intensity()
        if light > 0.45:
            return 0.0
        return max(0.0, min(1.0, (0.45 - light) / 0.45))

    def get_sun_position(self) -> Tuple[int, int]:
        """Calculates celestial arc across the 1280x720 sky."""
        # 6:00 (rise at left) to 18:00 (set at right)
        if 5.0 <= self.hour <= 19.0:
            prog = (self.hour - 5.0) / 14.0
            x = int(100 + prog * 1080)
            # Parabolic trajectory
            y = int(320 - math.sin(prog * math.pi) * 240)
            return x, y
        # Sun below horizon
        return -100, 800

    def get_moon_position(self) -> Tuple[int, int]:
        """Calculates moon trajectory from 18:00 to 06:00."""
        # Normalize into 18:00 -> 30:00 (06:00)
        h = self.hour if self.hour >= 18.0 else self.hour + 24.0
        if 17.0 <= h <= 31.0:
            prog = (h - 17.0) / 14.0
            x = int(120 + prog * 1040)
            y = int(300 - math.sin(prog * math.pi) * 210)
            return x, y
        return -100, 800

    def get_sky_colors(self) -> Tuple[Tuple[int, int, int], Tuple[int, int, int]]:
        phase = self.get_phase()
        return self.PHASE_COLORS.get(phase, ((10, 10, 30), (30, 20, 50)))

    def get_ambient_overlay(self) -> Optional[Tuple[int, int, int, int]]:
        """Returns (R, G, B, Alpha) for fullscreen grading."""
        phase = self.get_phase()
        if phase == "DAWN":
            return (255, 140, 60, 28)
        elif phase == "DUSK":
            return (220, 80, 40, 35)
        elif phase in ("EVENING", "NIGHT", "MIDNIGHT"):
            # Deep blue-purple night wash
            alpha = int(140 * (1.0 - self.get_light_intensity()))
            return (15, 18, 55, min(160, alpha))
        return None


class StarField:
    """80 fixed celestial stars with procedural scintillation."""

    def __init__(self, count: int = 80) -> None:
        self.stars: List[Tuple[int, int, float, int]] = []
        # Deterministic seed for stable constellations
        rng = random.Random(1792)
        for _ in range(count):
            x = rng.randint(20, 1260)
            y = rng.randint(15, 310)
            phase = rng.uniform(0.0, 6.28)
            size = rng.choice([1, 1, 1, 2, 2, 3])
            self.stars.append((x, y, phase, size))

    def draw(self, surface: pygame.Surface, visibility: float, time_elapsed: float) -> None:
        if visibility <= 0.01:
            return

        star_surf = pygame.Surface((1280, 340), pygame.SRCALPHA)
        for x, y, phase, size in self.stars:
            twinkle = (math.sin(time_elapsed * 3.5 + phase) + 1.0) * 0.5
            alpha = int(visibility * (120 + twinkle * 135))
            col = (255, 250, 235, min(255, alpha))
            if size == 1:
                star_surf.set_at((x, y), col)
            else:
                pygame.draw.circle(star_surf, col, (x, y), size)
                if size >= 3 and twinkle > 0.7:
                    # Cross sparkle
                    pygame.draw.line(star_surf, (255, 255, 255, int(alpha * 0.8)), (x - 3, y), (x + 3, y), 1)
                    pygame.draw.line(star_surf, (255, 255, 255, int(alpha * 0.8)), (x, y - 3), (x, y + 3), 1)

        surface.blit(star_surf, (0, 0))


class MoonRenderer:
    """Renders the sacred Mesopotamian Moon of Sin with dynamic phases."""

    def __init__(self) -> None:
        pass

    def draw(self, surface: pygame.Surface, lunar_phase: float, position: Tuple[int, int]) -> None:
        x, y = position
        if x < -50 or x > 1330 or y < -50 or y > 750:
            return

        radius = 24
        # Multi-tiered ethereal soft glow
        halo = pygame.Surface((radius * 6, radius * 6), pygame.SRCALPHA)
        center = (radius * 3, radius * 3)
        pygame.draw.circle(halo, (180, 210, 255, 20), center, radius * 3)
        pygame.draw.circle(halo, (210, 230, 255, 45), center, int(radius * 1.9))
        pygame.draw.circle(halo, (240, 245, 255, 80), center, int(radius * 1.3))
        surface.blit(halo, (x - radius * 3, y - radius * 3))

        # Main moon disc
        pygame.draw.circle(surface, (245, 248, 255), (x, y), radius)

        # Lunar maria / craters
        pygame.draw.circle(surface, (220, 225, 235), (x - 6, y - 5), 5)
        pygame.draw.circle(surface, (215, 220, 230), (x + 7, y + 4), 6)
        pygame.draw.circle(surface, (225, 230, 240), (x - 2, y + 8), 4)

        # Shadow mask to simulate crescent phase
        # lunar_phase: 0.0 (new), 0.5 (full), 1.0 (new)
        if abs(lunar_phase - 0.5) > 0.08:
            offset = int((lunar_phase - 0.5) * radius * 2.2)
            shadow_surf = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
            pygame.draw.circle(shadow_surf, (15, 12, 30, 220), (radius + offset, radius), radius)
            surface.blit(shadow_surf, (x - radius, y - radius))


class WeatherParticle:
    """Represents rain drops or swirling desert dust specks."""

    def __init__(self, x: float, y: float, vx: float, vy: float, color: Tuple[int, int, int, int], length: int = 1) -> None:
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.color = color
        self.length = length

    def update(self, dt: float) -> bool:
        self.x += self.vx * dt
        self.y += self.vy * dt
        if self.y > 730 or self.x < -40 or self.x > 1320:
            return False
        return True


class WeatherSystem:
    """Dynamic weather linked to Babylonian harvest, famine, and Euphrates flood events."""

    def __init__(self) -> None:
        self.current_state = "CLEAR"  # CLEAR, OVERCAST, RAIN, HEAVY_RAIN, DUST_STORM, SANDSTORM
        self.particles: List[WeatherParticle] = []
        self.lightning_timer = 0.0
        self.is_flashing = False

    def set_weather(self, state: str) -> None:
        self.current_state = state
        self.particles.clear()

    def update_from_game_state(self, state: Optional[GameState]) -> None:
        if state is None:
            self.set_weather("CLEAR")
            return

        if getattr(state, "harvest_yield", 3) >= 5:
            self.set_weather("CLEAR")
        elif getattr(state, "harvest_yield", 3) == 1:
            self.set_weather("SANDSTORM")
        elif getattr(state, "harvest_yield", 3) == 2:
            self.set_weather("DUST_STORM")
        elif getattr(state, "plague_struck", False):
            self.set_weather("OVERCAST")
        else:
            self.set_weather("CLEAR")

    def update(self, dt: float) -> None:
        # Spawn particles based on weather
        if self.current_state in ("RAIN", "HEAVY_RAIN"):
            spawn_count = 14 if self.current_state == "HEAVY_RAIN" else 6
            for _ in range(spawn_count):
                x = random.uniform(-20, 1300)
                y = random.uniform(-40, 20)
                vx = random.uniform(-80, -40)
                vy = random.uniform(420, 680)
                length = random.randint(8, 16)
                alpha = random.randint(120, 220)
                self.particles.append(WeatherParticle(x, y, vx, vy, (180, 215, 255, alpha), length))

        elif self.current_state in ("DUST_STORM", "SANDSTORM"):
            spawn_count = 18 if self.current_state == "SANDSTORM" else 7
            for _ in range(spawn_count):
                x = random.uniform(1280, 1340)
                y = random.uniform(200, 700)
                vx = random.uniform(-380, -190)
                vy = random.uniform(-20, 30)
                alpha = random.randint(90, 180)
                col = (215, 160, 90, alpha) if self.current_state == "SANDSTORM" else (190, 150, 110, alpha)
                self.particles.append(WeatherParticle(x, y, vx, vy, col, length=random.randint(3, 7)))

        # Update and cull
        self.particles = [p for p in self.particles if p.update(dt)]

        # Lightning handling
        if self.current_state == "HEAVY_RAIN":
            self.lightning_timer -= dt
            if self.lightning_timer <= 0:
                self.is_flashing = random.random() < 0.35
                self.lightning_timer = random.uniform(4.0, 9.0)
            else:
                self.is_flashing = False

    def draw(self, surface: pygame.Surface) -> None:
        # Atmospheric weather tint
        if self.current_state == "OVERCAST":
            wash = pygame.Surface((1280, 720), pygame.SRCALPHA)
            wash.fill((60, 65, 80, 45))
            surface.blit(wash, (0, 0))
        elif self.current_state == "RAIN":
            wash = pygame.Surface((1280, 720), pygame.SRCALPHA)
            wash.fill((40, 55, 75, 40))
            surface.blit(wash, (0, 0))
        elif self.current_state == "HEAVY_RAIN":
            wash = pygame.Surface((1280, 720), pygame.SRCALPHA)
            wash.fill((25, 35, 55, 70))
            surface.blit(wash, (0, 0))
        elif self.current_state == "DUST_STORM":
            wash = pygame.Surface((1280, 720), pygame.SRCALPHA)
            wash.fill((190, 140, 70, 50))
            surface.blit(wash, (0, 0))
        elif self.current_state == "SANDSTORM":
            wash = pygame.Surface((1280, 720), pygame.SRCALPHA)
            wash.fill((210, 145, 60, 85))
            surface.blit(wash, (0, 0))

        # Lightning strike flash
        if self.is_flashing:
            flash = pygame.Surface((1280, 720), pygame.SRCALPHA)
            flash.fill((255, 255, 255, 140))
            surface.blit(flash, (0, 0))

        # Render particles
        if self.particles:
            part_surf = pygame.Surface((1280, 720), pygame.SRCALPHA)
            for p in self.particles:
                if p.length > 1:
                    # Tilted streak
                    angle = math.atan2(p.vy, p.vx)
                    ex = p.x - math.cos(angle) * p.length
                    ey = p.y - math.sin(angle) * p.length
                    pygame.draw.line(part_surf, p.color, (int(p.x), int(p.y)), (int(ex), int(ey)), 2)
                else:
                    pygame.draw.circle(part_surf, p.color, (int(p.x), int(p.y)), 2)
            surface.blit(part_surf, (0, 0))


class DayNightRenderer:
    """Master orchestrator for diurnal environment, celestial objects and weather."""

    def __init__(self) -> None:
        self.time_of_day = TimeOfDay(start_hour=8.0, time_scale=0.35)
        self.star_field = StarField(count=95)
        self.moon = MoonRenderer()
        self.weather = WeatherSystem()
        self.time_elapsed = 0.0

    @property
    def is_night(self) -> bool:
        return self.time_of_day.get_phase() in ("EVENING", "NIGHT", "MIDNIGHT")

    @property
    def current_phase(self) -> str:
        return self.time_of_day.get_phase()

    @property
    def ambient_light(self) -> float:
        return self.time_of_day.get_light_intensity()

    def trigger_day_advance(self) -> None:
        self.time_of_day.advance_to_next_day()

    def update(self, dt: float, game_state: Optional[GameState] = None) -> None:
        self.time_elapsed += dt
        self.time_of_day.update(dt)
        self.weather.update(dt)
        if game_state is not None:
            self.weather.update_from_game_state(game_state)

    def render_sky_layer(self, surface: pygame.Surface) -> None:
        """Renders sky gradient, celestial sun/moon, and twinkling stars."""
        top_col, bot_col = self.time_of_day.get_sky_colors()
        sky_surf = pygame.Surface((1280, 340))
        for y in range(340):
            t = y / 340.0
            r = int(top_col[0] + (bot_col[0] - top_col[0]) * t)
            g = int(top_col[1] + (bot_col[1] - top_col[1]) * t)
            b = int(top_col[2] + (bot_col[2] - top_col[2]) * t)
            pygame.draw.line(sky_surf, (r, g, b), (0, y), (1280, y))
        surface.blit(sky_surf, (0, 0))

        # Star field
        star_vis = self.time_of_day.get_star_visibility()
        self.star_field.draw(surface, star_vis, self.time_elapsed)

        # Sun
        sun_x, sun_y = self.time_of_day.get_sun_position()
        if sun_y < 350 and sun_x > -50:
            glow = pygame.Surface((180, 180), pygame.SRCALPHA)
            pulse = math.sin(self.time_elapsed * 2.0) * 4
            pygame.draw.circle(glow, (255, 230, 140, 55), (90, 90), int(75 + pulse))
            pygame.draw.circle(glow, (255, 245, 180, 100), (90, 90), int(45 + pulse * 0.5))
            surface.blit(glow, (sun_x - 90, sun_y - 90))
            pygame.draw.circle(surface, (255, 250, 220), (sun_x, sun_y), 22)

        # Moon
        moon_x, moon_y = self.time_of_day.get_moon_position()
        if moon_y < 350 and moon_x > -50:
            lunar_phase = (self.time_of_day.day_count % 8) / 8.0
            self.moon.draw(surface, lunar_phase, (moon_x, moon_y))

    def render_night_overlay(self, surface: pygame.Surface) -> None:
        """Applies ambient nighttime or golden-hour color grading overlay."""
        overlay_info = self.time_of_day.get_ambient_overlay()
        if overlay_info:
            r, g, b, a = overlay_info
            wash = pygame.Surface((1280, 720), pygame.SRCALPHA)
            wash.fill((r, g, b, a))
            surface.blit(wash, (0, 0))

    def render_weather(self, surface: pygame.Surface) -> None:
        """Renders precipitation, dust storms, and lightning flashes."""
        self.weather.draw(surface)
