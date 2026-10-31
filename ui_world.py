"""
ui_world.py - Monumental Living Babylonian Kingdom Scene Renderer for RetroRevive.

Renders an authentic, layered ancient Mesopotamian environment:
- Celestial sky with golden sun corona, atmospheric haze, and layered volumetric clouds
- Distant Zagros mountain ridges with atmospheric depth perspective
- Monumental Babylonian Palace with columned porticos, glazed lapis-blue brick facade,
  and smoking ceremonial braziers
- Stepped Ziggurat of Ur / Etemenanki rising with grand staircases and sacred summit flames
- Flowing Euphrates River with animated wave caustics and trade barges
- Working agricultural fields with irrigation canals and waving golden wheat
- Living entities: King on royal overlook, patrolling guards, harvesting farmers,
  merchants with pack donkeys, and walking citizens
- Weather & state particles: Fire embers, smoke plumes, harvest chaff, and drought dust
"""

import math
import os
import random
from typing import List, Optional, Tuple
import pygame

from game_logic import GameState
from ui_characters import FarmerWorker, MerchantCart, PalaceGuard, RiverBoat
from ui_theme import Palette


class Cloud:
    """Drifting volumetric cloud with soft alpha shading."""

    def __init__(self, x: float, y: float, speed: float, width: int, height: int) -> None:
        self.x = x
        self.y = y
        self.speed = speed
        self.width = width
        self.height = height

    def update(self, dt: float) -> None:
        self.x += self.speed * dt
        if self.x > 1380:
            self.x = -self.width - random.randint(30, 120)
            self.y = random.uniform(25, 140)

    def draw(self, surface: pygame.Surface) -> None:
        cloud_surf = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        col_main = (255, 248, 235, 140)
        col_shadow = (220, 205, 190, 80)
        # Soft lower shadow
        pygame.draw.ellipse(cloud_surf, col_shadow, (0, self.height // 3, self.width, self.height * 2 // 3))
        # 3 volumetric billowing circles
        pygame.draw.circle(cloud_surf, col_main, (self.width // 4, self.height // 2), self.height // 2)
        pygame.draw.circle(cloud_surf, col_main, (self.width // 2, self.height * 2 // 5), int(self.height * 0.55))
        pygame.draw.circle(cloud_surf, col_main, (self.width * 3 // 4, self.height // 2), self.height // 2)
        surface.blit(cloud_surf, (int(self.x), int(self.y)))


class CitizenWalker:
    """Animated procedural Babylonian citizen walking back and forth."""

    def __init__(self, x: float, y: float, speed: float, min_x: float, max_x: float, color: Tuple[int, int, int]) -> None:
        self.x = x
        self.y = y
        self.speed = speed
        self.min_x = min_x
        self.max_x = max_x
        self.color = color
        self.facing = 1  # 1 = right, -1 = left
        self.walk_phase = random.uniform(0.0, 6.28)

    def update(self, dt: float) -> None:
        self.x += self.speed * self.facing * dt
        self.walk_phase += 8.0 * dt
        if self.x > self.max_x:
            self.facing = -1
        elif self.x < self.min_x:
            self.facing = 1

    def draw(self, surface: pygame.Surface) -> None:
        stride = math.sin(self.walk_phase) * 3
        bx = int(self.x)
        by = int(self.y)

        # Shadow
        pygame.draw.ellipse(surface, (20, 15, 10, 80), (bx - 5, by + 6, 10, 4))
        # Head & headband
        pygame.draw.circle(surface, (225, 185, 145), (bx, by - 14), 4)
        pygame.draw.line(surface, Palette.GOLD_DARK, (bx - 4, by - 16), (bx + 4, by - 16), 1)
        # Draped Mesopotamian robe
        body_poly = [
            (bx - 4, by - 10),
            (bx + 4, by - 10),
            (bx + 5, by + 3),
            (bx - 5, by + 3),
        ]
        pygame.draw.polygon(surface, self.color, body_poly)
        # Stride legs
        pygame.draw.line(surface, (150, 115, 80), (bx - 2, by + 3), (bx - 2 + int(stride), by + 8), 2)
        pygame.draw.line(surface, (150, 115, 80), (bx + 2, by + 3), (bx + 2 - int(stride), by + 8), 2)


class BirdFlock:
    """Procedural silhouette birds circling the summit of the Ziggurat."""

    def __init__(self) -> None:
        self.x = -80.0
        self.y = 80.0
        self.speed = 34.0
        self.offsets = [(0, 0), (-18, -12), (-36, -20), (-20, 14), (-38, 24), (-52, 6)]

    def update(self, dt: float) -> None:
        self.x += self.speed * dt
        if self.x > 1420:
            self.x = -140.0
            self.y = random.uniform(45, 130)
            self.speed = random.uniform(30.0, 46.0)

    def draw(self, surface: pygame.Surface, time_elapsed: float) -> None:
        col = (35, 28, 22)
        for ox, oy in self.offsets:
            bx = int(self.x + ox)
            by = int(self.y + oy)
            flap = math.sin(time_elapsed * 8.5 + ox * 0.1) * 3
            if 0 <= bx <= 1280 and 0 <= by <= 720:
                pygame.draw.line(surface, col, (bx, by), (bx - 5, by - int(3 + flap)), 1)
                pygame.draw.line(surface, col, (bx, by), (bx + 5, by - int(3 + flap)), 1)


class Particle:
    """Cosmetic particle for fire embers, smoke plumes, harvest dust, or fireworks."""

    def __init__(
        self,
        x: float,
        y: float,
        vx: float,
        vy: float,
        color: Tuple[int, int, int],
        lifetime: float,
        size: int = 3,
        gravity: float = 0.0,
    ) -> None:
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.color = color
        self.lifetime = lifetime
        self.max_life = lifetime
        self.size = size
        self.gravity = gravity

    def update(self, dt: float) -> bool:
        self.x += self.vx * dt
        self.vy += self.gravity * dt
        self.y += self.vy * dt
        self.lifetime -= dt
        return self.lifetime > 0

    def draw(self, surface: pygame.Surface) -> None:
        alpha = int(min(1.0, max(0.0, self.lifetime / self.max_life)) * 255)
        p_surf = pygame.Surface((self.size * 2, self.size * 2), pygame.SRCALPHA)
        r, g, b = self.color
        pygame.draw.circle(p_surf, (r, g, b, alpha), (self.size, self.size), self.size)
        surface.blit(p_surf, (int(self.x) - self.size, int(self.y) - self.size))


class WorldRenderer:
    """
    Manages procedural rendering, lighting, and animation of the living Babylonian Empire.
    """

    def __init__(self) -> None:
        self.time_elapsed = 0.0

        # Atmosphere & Clouds
        self.clouds: List[Cloud] = [
            Cloud(40, 40, 10.0, 140, 44),
            Cloud(380, 75, 14.0, 160, 48),
            Cloud(760, 30, 9.0, 120, 38),
            Cloud(1100, 85, 13.0, 150, 46),
        ]
        self.birds = BirdFlock()

        # Living Entities
        self.citizens: List[CitizenWalker] = [
            CitizenWalker(190, 396, 20.0, 130, 370, Palette.LAPIS_BASE),
            CitizenWalker(280, 406, 17.0, 160, 390, Palette.CLAY_DEEP),
            CitizenWalker(670, 412, 22.0, 610, 840, Palette.PALM_GREEN),
            CitizenWalker(740, 402, 19.0, 640, 890, Palette.GOLD_DARK),
            CitizenWalker(320, 392, 15.0, 210, 430, (140, 55, 55)),
        ]
        self.farmers: List[FarmerWorker] = [
            FarmerWorker(240, 490, work_rate=1.0),
            FarmerWorker(520, 520, work_rate=1.1),
            FarmerWorker(820, 480, work_rate=0.9),
            FarmerWorker(1040, 510, work_rate=1.2),
        ]
        self.guards: List[PalaceGuard] = [
            PalaceGuard(610, 372, facing=-1),
            PalaceGuard(695, 372, facing=1),
        ]
        self.merchant = MerchantCart(120, 388, speed=16.0)
        self.river_boat = RiverBoat(450, 412, speed=13.0)

        self.particles: List[Particle] = []

        # Sky gradient cache
        self._cached_sky_surf: Optional[pygame.Surface] = None
        self._cached_sky_year: Optional[int] = None

        # Photorealistic AAA World Background
        self.bg_image: Optional[pygame.Surface] = None
        bg_path = os.path.join(os.path.dirname(__file__), "assets", "babylon_world_bg.jpg")
        if os.path.exists(bg_path):
            try:
                raw_bg = pygame.image.load(bg_path)
                self.bg_image = pygame.transform.smoothscale(raw_bg, (1280, 720))
            except Exception:
                self.bg_image = None

    def _get_sky_surface(self, yr: int) -> pygame.Surface:
        if self._cached_sky_surf is not None and self._cached_sky_year == yr:
            return self._cached_sky_surf

        sky = pygame.Surface((1280, 340))
        # Atmospheric golden hour & dawn palette
        if yr <= 5:
            t = (yr - 1) / 4.0
            top_r = int(30 + (20 - 30) * t)
            top_g = int(55 + (75 - 55) * t)
            top_b = int(115 + (155 - 115) * t)
        else:
            t = (yr - 5) / 5.0
            top_r = int(20 + (85 - 20) * t)
            top_g = int(75 + (40 - 75) * t)
            top_b = int(155 + (90 - 155) * t)

        for y in range(0, 340):
            factor = y / 340.0
            r = int(top_r + (245 - top_r) * factor)
            g = int(top_g + (185 - top_g) * factor)
            b = int(top_b + (105 - top_b) * factor)
            pygame.draw.line(sky, (r, g, b), (0, y), (1280, y))

        self._cached_sky_surf = sky
        self._cached_sky_year = yr
        return sky

    def trigger_harvest_particles(self, count: int = 40) -> None:
        """Golden grain chaff sweeping over the cultivated fields."""
        for _ in range(count):
            px = random.uniform(200, 1200)
            py = random.uniform(460, 640)
            vx = random.uniform(-15, 25)
            vy = random.uniform(-45, -15)
            self.particles.append(Particle(px, py, vx, vy, Palette.GOLD_LIGHT, random.uniform(0.9, 1.8), size=random.randint(2, 4)))

    def trigger_rat_particles(self, count: int = 30) -> None:
        """Scurrying rodents near the granary silos."""
        for _ in range(count):
            px = random.uniform(770, 910)
            py = random.uniform(365, 435)
            vx = random.uniform(-55, 55)
            vy = random.uniform(-10, 15)
            self.particles.append(Particle(px, py, vx, vy, (45, 32, 25), random.uniform(1.0, 1.9), size=3))

    def trigger_victory_fireworks(self, count: int = 60) -> None:
        """Celebratory royal fireworks over the palace and ziggurat."""
        for _ in range(count):
            px = random.uniform(150, 1150)
            py = random.uniform(60, 240)
            angle = random.uniform(0, 6.28)
            spd = random.uniform(40, 130)
            vx = math.cos(angle) * spd
            vy = math.sin(angle) * spd
            col = random.choice([Palette.GOLD_LIGHT, Palette.LAPIS_LIGHT, Palette.CROP_GREEN, Palette.SAND_LIGHT, (255, 120, 60)])
            self.particles.append(Particle(px, py, vx, vy, col, random.uniform(1.2, 2.4), size=random.randint(2, 5), gravity=20.0))

    def update(self, dt: float) -> None:
        self.time_elapsed += dt
        for cloud in self.clouds:
            cloud.update(dt)
        self.birds.update(dt)
        for citizen in self.citizens:
            citizen.update(dt)
        for farmer in self.farmers:
            farmer.update(dt)
        for guard in self.guards:
            guard.update(dt)
        self.merchant.update(dt)
        self.river_boat.update(dt)

        # Ambient brazier smoke particles (emit from palace and temple braziers)
        if random.random() < 0.35:
            # Palace brazier 1
            self.particles.append(Particle(615, 335, random.uniform(-4, 4), random.uniform(-18, -10), (180, 170, 160), 1.5, size=random.randint(2, 4)))
            # Palace brazier 2
            self.particles.append(Particle(690, 335, random.uniform(-4, 4), random.uniform(-18, -10), (180, 170, 160), 1.5, size=random.randint(2, 4)))
            # Ziggurat summit brazier
            self.particles.append(Particle(215, 195, random.uniform(-5, 5), random.uniform(-22, -12), (200, 180, 150), 1.8, size=random.randint(2, 4)))

        self.particles = [p for p in self.particles if p.update(dt)]

    def render(self, surface: pygame.Surface, state: Optional[GameState] = None) -> None:
        """Renders the monumental living Babylonian environment."""
        if self.bg_image is not None:
            # 1. Photorealistic panoramic Babylon at golden hour
            surface.blit(self.bg_image, (0, 0))

            # 2. Dynamic atmospheric daylight / golden hour sun glow
            sun_pulse = math.sin(self.time_elapsed * 1.5) * 6
            glow_surf = pygame.Surface((240, 240), pygame.SRCALPHA)
            pygame.draw.circle(glow_surf, (255, 230, 140, 45), (120, 120), int(90 + sun_pulse))
            pygame.draw.circle(glow_surf, (255, 245, 180, 75), (120, 120), int(55 + sun_pulse * 0.5))
            surface.blit(glow_surf, (660 - 120, 195 - 120))

            # 3. Ambient volumetric clouds and circling birds in distance
            for cloud in self.clouds:
                cloud.draw(surface)
            self.birds.draw(surface, self.time_elapsed)

            # 4. Animated River waves / caustics along the Euphrates
            for i in range(12):
                rx = (i * 95 + int(self.time_elapsed * 28.0)) % 750 + 80
                wave_y = 480 + int(math.sin(self.time_elapsed * 2.8 + i) * 6) + (i % 4) * 16
                if wave_y < 700:
                    pygame.draw.arc(surface, (255, 245, 200, 130), (rx, wave_y, 40, 10), 0.2, 2.9, width=2)

            # 5. Temple brazier smoke & ember particles
            if random.random() < 0.25:
                # Ziggurat summit braziers
                self.particles.append(Particle(
                    x=835 + random.uniform(-8, 8),
                    y=125,
                    vx=random.uniform(-4, 8),
                    vy=random.uniform(-14, -26),
                    color=(240, 210, 140),
                    lifetime=2.5,
                    size=random.randint(2, 4),
                    gravity=-0.5
                ))
            if random.random() < 0.35:
                # City gate braziers
                self.particles.append(Particle(
                    x=1120 + random.uniform(-6, 6),
                    y=480,
                    vx=random.uniform(-6, 6),
                    vy=random.uniform(-18, -32),
                    color=(255, 140, 40),
                    lifetime=1.8,
                    size=random.randint(2, 3),
                    gravity=-1.0
                ))

            # 6. Dynamic Game State Overlays
            if state is not None:
                # Harvest / Bumper Golden Light
                if state.harvest_yield >= 5:
                    h_wash = pygame.Surface((1280, 720), pygame.SRCALPHA)
                    h_wash.fill((255, 215, 80, 22))
                    surface.blit(h_wash, (0, 0))
                # Drought Arid Dust Haze
                elif state.harvest_yield == 1:
                    d_wash = pygame.Surface((1280, 720), pygame.SRCALPHA)
                    d_wash.fill((190, 140, 70, 45))
                    surface.blit(d_wash, (0, 0))
                # Plague Somber Twilight Vignette
                elif state.plague_struck:
                    p_wash = pygame.Surface((1280, 720), pygame.SRCALPHA)
                    p_wash.fill((70, 30, 80, 55))
                    surface.blit(p_wash, (0, 0))

            # 7. Active particles (Embers, smoke plumes, fireworks)
            for particle in self.particles:
                particle.draw(surface)

        else:
            self._render_procedural_fallback(surface, state)

    def _render_procedural_fallback(self, surface: pygame.Surface, state: Optional[GameState] = None) -> None:
        """Renders procedural fallback when offline or when high-res assets are absent."""
        # 1. Base Dark Clearing
        surface.fill(Palette.BG_DARK)

        # 2. Celestial Sky Gradient
        yr = getattr(state, "year", 1) if state else 1
        sky_surf = self._get_sky_surface(yr)
        surface.blit(sky_surf, (0, 0))

        # 3. Radiant Celestial Sun with Multi-layered Corona
        sun_x, sun_y = 980, 95
        pulse = math.sin(self.time_elapsed * 2.0) * 3
        # Corona glows
        glow_surf = pygame.Surface((150, 150), pygame.SRCALPHA)
        pygame.draw.circle(glow_surf, (255, 220, 120, 35), (75, 75), int(60 + pulse))
        pygame.draw.circle(glow_surf, (255, 235, 145, 65), (75, 75), int(42 + pulse))
        pygame.draw.circle(glow_surf, (255, 245, 175, 110), (75, 75), int(26 + pulse))
        surface.blit(glow_surf, (sun_x - 75, sun_y - 75))
        pygame.draw.circle(surface, Palette.GOLD_PALE, (sun_x, sun_y), 20)

        # 4. Volumetric Drifting Clouds & Circling Birds
        for cloud in self.clouds:
            cloud.draw(surface)
        self.birds.draw(surface, self.time_elapsed)

        # 5. Distant Zagros Mountains with Atmospheric Haze
        self._draw_mountains(surface)

        # 6. Ancient Mud-brick City Walls of Babylon
        self._draw_city_walls(surface)

        # 7. Grand Stepped Ziggurat of Ur (Left skyline)
        self._draw_ziggurat(surface)

        # 8. Monumental Royal Palace of Babylon (Center skyline)
        self._draw_palace(surface)

        # 9. Granary Silo Storehouses (Right skyline)
        bushels = state.bushels if state else 2800
        self._draw_granary(surface, bushels)

        # 10. The Euphrates River (Flowing through middle ground)
        self._draw_river(surface)

        # 11. River Boat / Trade Barge
        self.river_boat.draw(surface)

        # 12. Riverbank Palms & Vegetation
        self._draw_palms(surface)

        # 13. Merchant Cart & Walking Citizens on Highway
        self.merchant.draw(surface)
        for citizen in self.citizens:
            citizen.draw(surface)

        # 14. Palace Sentry Guards
        for guard in self.guards:
            guard.draw(surface)

        # 15. Fertile Farmland, Irrigation Canals & Reaping Farmers
        acres = state.acres if state else 1000
        yield_rate = state.harvest_yield if state else 3
        self._draw_farmland(surface, acres, yield_rate)

        # 16. Farmers working in fields
        for farmer in self.farmers:
            farmer.draw(surface)

        # 17. Active Particles (Embers, smoke, chaff)
        for particle in self.particles:
            particle.draw(surface)

    def _draw_mountains(self, surface: pygame.Surface) -> None:
        """Distant Zagros mountain ridges with atmospheric haze."""
        poly_far = [
            (0, 310), (130, 220), (280, 265), (430, 200), (590, 255),
            (750, 195), (920, 245), (1080, 190), (1210, 230), (1280, 210),
            (1280, 340), (0, 340),
        ]
        pygame.draw.polygon(surface, (150, 115, 95), poly_far)

        poly_near = [
            (0, 325), (180, 260), (350, 290), (520, 245), (690, 280),
            (860, 235), (1030, 275), (1190, 240), (1280, 265),
            (1280, 350), (0, 350),
        ]
        pygame.draw.polygon(surface, (175, 135, 110), poly_near)

    def _draw_city_walls(self, surface: pygame.Surface) -> None:
        """Massive mudbrick battlements and fortified towers of ancient Babylon."""
        wall_y = 350
        wall_h = 32
        pygame.draw.rect(surface, Palette.SAND_DARK, (0, wall_y, 1280, wall_h))
        pygame.draw.rect(surface, Palette.CLAY_DEEP, (0, wall_y, 1280, wall_h), width=2)

        # Crenellations along wall parapet
        for wx in range(0, 1280, 18):
            pygame.draw.rect(surface, Palette.SAND_DARK, (wx, wall_y - 6, 10, 6))
            pygame.draw.rect(surface, Palette.CLAY_DEEP, (wx, wall_y - 6, 10, 6), width=1)

    def _draw_ziggurat(self, surface: pygame.Surface) -> None:
        """The monumental stepped temple of Ur / Etemenanki."""
        base_x = 75
        base_y = 380

        # Tier 1
        t1_w, t1_h = 240, 48
        pygame.draw.rect(surface, Palette.SAND_DARK, (base_x, base_y - t1_h, t1_w, t1_h), border_radius=3)
        pygame.draw.rect(surface, Palette.CLAY_DEEP, (base_x, base_y - t1_h, t1_w, t1_h), width=2, border_radius=3)

        # Tier 2
        t2_x = base_x + 36
        t2_w, t2_h = 168, 42
        t2_y = base_y - t1_h - t2_h
        pygame.draw.rect(surface, Palette.SAND_DARK, (t2_x, t2_y, t2_w, t2_h), border_radius=3)
        pygame.draw.rect(surface, Palette.CLAY_DEEP, (t2_x, t2_y, t2_w, t2_h), width=2, border_radius=3)

        # Tier 3
        t3_x = t2_x + 32
        t3_w, t3_h = 104, 38
        t3_y = t2_y - t3_h
        pygame.draw.rect(surface, Palette.SAND_DARK, (t3_x, t3_y, t3_w, t3_h), border_radius=2)
        pygame.draw.rect(surface, Palette.CLAY_DEEP, (t3_x, t3_y, t3_w, t3_h), width=2, border_radius=2)

        # Summit Lapis-Lazuli High Sanctum
        shrine_x = t3_x + 22
        shrine_w, shrine_h = 60, 32
        shrine_y = t3_y - shrine_h
        pygame.draw.rect(surface, Palette.LAPIS_BASE, (shrine_x, shrine_y, shrine_w, shrine_h))
        pygame.draw.rect(surface, Palette.GOLD_LIGHT, (shrine_x, shrine_y, shrine_w, shrine_h), width=2)
        # Golden dome
        pygame.draw.arc(surface, Palette.GOLD_LIGHT, (shrine_x + 6, shrine_y - 12, shrine_w - 12, 24), 0, 3.14, width=3)

        # Grand Axial Staircase
        stair_x = base_x + 105
        stair_poly = [
            (stair_x + 15, shrine_y + shrine_h),
            (stair_x - 14, base_y),
            (stair_x + 44, base_y),
            (stair_x + 15, shrine_y + shrine_h),
        ]
        pygame.draw.polygon(surface, Palette.CLAY_DEEP, stair_poly)
        for sy in range(shrine_y + shrine_h + 8, base_y, 7):
            w_step = 10 + int((sy - shrine_y) * 0.22)
            pygame.draw.line(surface, Palette.SAND_LIGHT, (stair_x + 15 - w_step // 2, sy), (stair_x + 15 + w_step // 2, sy), 2)

        # Summit Braziers
        flame = math.sin(self.time_elapsed * 12.0) * 3
        pygame.draw.circle(surface, (255, 140, 20), (shrine_x - 4, shrine_y + 8), int(5 + flame))
        pygame.draw.circle(surface, (255, 235, 70), (shrine_x - 4, shrine_y + 8), 3)
        pygame.draw.circle(surface, (255, 140, 20), (shrine_x + shrine_w + 4, shrine_y + 8), int(5 - flame))
        pygame.draw.circle(surface, (255, 235, 70), (shrine_x + shrine_w + 4, shrine_y + 8), 3)

    def _draw_palace(self, surface: pygame.Surface) -> None:
        """The monumental royal palace of Babylon with Ishtar Gate portico."""
        px, py = 580, 380
        pw, ph = 145, 62

        # Glazed Lapis-Blue Wall Facade (Classic Babylonian Royal Palace)
        pygame.draw.rect(surface, Palette.LAPIS_BASE, (px, py - ph, pw, ph), border_radius=4)
        pygame.draw.rect(surface, Palette.GOLD_BASE, (px, py - ph, pw, ph), width=2, border_radius=4)

        # Golden Rosette Frieze across cornice
        for fx in range(px + 10, px + pw - 10, 16):
            pygame.draw.circle(surface, Palette.GOLD_LIGHT, (fx, py - ph + 8), 4)
            pygame.draw.circle(surface, Palette.GOLD_DARK, (fx, py - ph + 8), 2)

        # Royal Grand Arch Gateway
        gate_w, gate_h = 36, 42
        gate_x = px + (pw - gate_w) // 2
        gate_y = py - gate_h
        pygame.draw.rect(surface, (24, 18, 14), (gate_x, gate_y, gate_w, gate_h), border_top_left_radius=18, border_top_right_radius=18)
        pygame.draw.rect(surface, Palette.GOLD_LIGHT, (gate_x, gate_y, gate_w, gate_h), width=2, border_top_left_radius=18, border_top_right_radius=18)

        # Palace Portico Columns
        for cx in [px + 16, px + 38, px + pw - 38, px + pw - 16]:
            pygame.draw.rect(surface, Palette.SAND_LIGHT, (cx - 4, py - ph + 16, 8, ph - 16))
            pygame.draw.circle(surface, Palette.GOLD_BASE, (cx, py - ph + 18), 5)

        # Flaming Royal Courtyard Braziers flanking gate
        flick = math.sin(self.time_elapsed * 10.0) * 2.5
        pygame.draw.rect(surface, Palette.GOLD_DARK, (gate_x - 14, py - 18, 8, 18))
        pygame.draw.circle(surface, (255, 140, 20), (gate_x - 10, py - 20), int(5 + flick))
        pygame.draw.circle(surface, (255, 235, 70), (gate_x - 10, py - 20), 3)

        pygame.draw.rect(surface, Palette.GOLD_DARK, (gate_x + gate_w + 6, py - 18, 8, 18))
        pygame.draw.circle(surface, (255, 140, 20), (gate_x + gate_w + 10, py - 20), int(5 - flick))
        pygame.draw.circle(surface, (255, 235, 70), (gate_x + gate_w + 10, py - 20), 3)

    def _draw_granary(self, surface: pygame.Surface, bushels: int) -> None:
        """The grand mudbrick royal granaries with dynamic grain level indicators."""
        gx, gy = 770, 380
        silo_w, silo_h = 36, 68
        spacing = 45

        for i in range(3):
            sx = gx + i * spacing
            sy = gy - silo_h
            # Cylindrical silo base
            pygame.draw.rect(surface, Palette.CLAY_DEEP, (sx, sy, silo_w, silo_h), border_top_left_radius=8, border_top_right_radius=8)
            pygame.draw.rect(surface, Palette.PANEL_BORDER, (sx, sy, silo_w, silo_h), width=2, border_top_left_radius=8, border_top_right_radius=8)

            # Silo clay dome
            pygame.draw.circle(surface, Palette.SAND_DARK, (sx + silo_w // 2, sy), silo_w // 2)
            pygame.draw.circle(surface, Palette.PANEL_BORDER, (sx + silo_w // 2, sy), silo_w // 2, width=1)

            # Dynamic Grain Level Indicator (Visible through window slot)
            fill_pct = min(1.0, max(0.0, (bushels - i * 1000) / 1000.0))
            if fill_pct > 0.0:
                filled_h = int((silo_h - 22) * fill_pct)
                fill_rect = pygame.Rect(sx + 6, gy - 8 - filled_h, silo_w - 12, filled_h)
                pygame.draw.rect(surface, Palette.GOLD_BASE, fill_rect, border_radius=2)

            # Lower ventilation grate
            pygame.draw.rect(surface, (20, 15, 12), (sx + 10, gy - 14, silo_w - 20, 12), border_top_left_radius=3, border_top_right_radius=3)

    def _draw_river(self, surface: pygame.Surface) -> None:
        """Renders the flowing Euphrates river with sinusoidal wave highlights."""
        river_poly = [
            (0, 390), (280, 400), (580, 390), (920, 405), (1280, 395),
            (1280, 445), (950, 452), (620, 440), (320, 450), (0, 440),
        ]
        pygame.draw.polygon(surface, Palette.RIVER_BLUE, river_poly)

        # Flowing water caustics
        for i in range(14):
            rx = (i * 105 + int(self.time_elapsed * 34.0)) % 1280
            wave_y = 402 + int(math.sin(self.time_elapsed * 3.0 + i) * 5) + (i % 3) * 10
            pygame.draw.arc(surface, Palette.RIVER_HIGHLIGHT, (rx, wave_y, 45, 12), 0, 3.14, width=2)

    def _draw_palms(self, surface: pygame.Surface) -> None:
        """Riverbank date palms with swaying fronds."""
        palms = [(360, 385), (550, 380), (745, 385), (935, 382)]
        for tx, ty in palms:
            # Curved trunk
            pygame.draw.arc(surface, (110, 80, 50), (tx - 15, ty - 46, 30, 50), 1.2, 2.5, width=4)
            # Fronds
            orig = (tx - 2, ty - 44)
            for angle in [-1.2, -0.6, 0.0, 0.6, 1.2]:
                sway = math.sin(self.time_elapsed * 2.2 + angle) * 4
                fx = orig[0] + int(math.sin(angle) * 22) + int(sway)
                fy = orig[1] - int(math.cos(angle) * 14)
                pygame.draw.line(surface, Palette.PALM_GREEN, orig, (fx, fy), 3)

    def _draw_farmland(self, surface: pygame.Surface, acres: int, yield_rate: int) -> None:
        """Agricultural plots, irrigation canals, and golden wheat stalks."""
        # Fertile alluvial mud base
        pygame.draw.rect(surface, Palette.FERTILE_EARTH, (0, 445, 1280, 275))

        # Blue irrigation feeder canals cutting between fields
        for cx in [220, 580, 940]:
            pygame.draw.line(surface, (35, 80, 115), (cx, 445), (cx - 40, 720), 4)

        # Cultivated furrow rows with waving wheat
        sway = math.sin(self.time_elapsed * 3.6) * 4.0
        crop_col = Palette.CROP_GOLD if yield_rate >= 3 else Palette.CROP_GREEN
        stalk_spacing = max(16, 52 - (acres // 55))

        for row_y in range(460, 715, 26):
            pygame.draw.line(surface, (72, 48, 28), (0, row_y), (1280, row_y), 2)
            for x in range(25, 1260, stalk_spacing):
                sx = x + int(sway)
                pygame.draw.line(surface, crop_col, (x, row_y), (sx, row_y - 15), 2)
                pygame.draw.circle(surface, Palette.GOLD_LIGHT, (sx, row_y - 16), 2)
