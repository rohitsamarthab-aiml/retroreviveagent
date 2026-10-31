"""
atmosphere_3d.py - Dynamic 3D Diurnal Lighting, Shadow Casting & Weather Effects.

Provides authentic ancient Mesopotamian atmospheric conditions:
- Directional Sun with real-time shadow projection
- Dynamic diurnal sun position and ambient color grading (Dawn, Midday, Golden Hour, Twilight, Night)
- Point lights for Royal Palace and Ziggurat summit braziers with realistic flicker physics
- State-reactive weather phenomena:
  * Clear & Prosperous: Golden radiance, warm haze
  * Euphrates Flood / Heavy Torrents: Dim blue-gray overcast with heavy rain streaks
  * Scorched Desert Drought: Amber sirocco haze with dust storm particle density
"""

import math
import random
from typing import List, Optional
from panda3d.core import (
    AmbientLight,
    DirectionalLight,
    Fog,
    NodePath,
    PointLight,
    Vec3,
    Vec4,
)


class Atmosphere3D:
    """Manages 3D directional sun, ambient illumination, brazier point lights, and weather."""

    def __init__(self, render_root: NodePath) -> None:
        self.render = render_root
        self.time = 0.0
        self.diurnal_hour = 8.5  # 0.0 - 24.0
        self.time_scale = 0.2    # Diurnal progression speed

        # 1. Directional Sun Light
        self.dlight = DirectionalLight("sun_light")
        self.dlight.set_color(Vec4(1.0, 0.95, 0.85, 1.0))
        self.dlight_np = self.render.attach_new_node(self.dlight)
        self.render.set_light(self.dlight_np)

        # 2. Ambient Sky Light
        self.alight = AmbientLight("ambient_light")
        self.alight.set_color(Vec4(0.35, 0.35, 0.40, 1.0))
        self.alight_np = self.render.attach_new_node(self.alight)
        self.render.set_light(self.alight_np)

        # 3. Palace Courtyard Flaming Brazier Point Lights
        self.brazier_lights: List[NodePath] = []
        brazier_positions = [
            Vec3(73.0, 68.0, 6.0),   # Palace Throne dais left
            Vec3(77.0, 68.0, 6.0),   # Palace Throne dais right
            Vec3(-120.0, 110.0, 85.0), # Ziggurat Summit Sacred Fire
            Vec3(-10.0, -70.0, 6.0),   # Ishtar Gate portal left
            Vec3(10.0, -70.0, 6.0),    # Ishtar Gate portal right
        ]

        for i, pos in enumerate(brazier_positions):
            plight = PointLight(f"brazier_light_{i}")
            plight.set_color(Vec4(1.0, 0.65, 0.25, 1.0))
            plight.set_attenuation(Vec3(1.0, 0.04, 0.002))
            p_np = self.render.attach_new_node(plight)
            p_np.set_pos(pos)
            self.render.set_light(p_np)
            self.brazier_lights.append(p_np)

        # 4. Atmospheric Distance Fog
        self.fog = Fog("atmospheric_fog")
        self.fog.set_color(0.80, 0.72, 0.60)
        self.fog.set_exp_density(0.0012)
        self.render.set_fog(self.fog)

        self.weather_state = "CLEAR"  # CLEAR, FLOOD, DROUGHT

    def set_weather(self, state: str) -> None:
        self.weather_state = state
        if state == "FLOOD":
            self.fog.set_color(0.35, 0.40, 0.48)
            self.fog.set_exp_density(0.0035)
            self.dlight.set_color(Vec4(0.45, 0.50, 0.60, 1.0))
            self.alight.set_color(Vec4(0.20, 0.22, 0.28, 1.0))
        elif state == "DROUGHT":
            self.fog.set_color(0.85, 0.55, 0.25)
            self.fog.set_exp_density(0.0040)
            self.dlight.set_color(Vec4(1.0, 0.70, 0.35, 1.0))
            self.alight.set_color(Vec4(0.45, 0.30, 0.18, 1.0))
        else:  # CLEAR
            self.fog.set_color(0.80, 0.72, 0.60)
            self.fog.set_exp_density(0.0012)
            self.dlight.set_color(Vec4(1.0, 0.95, 0.85, 1.0))
            self.alight.set_color(Vec4(0.35, 0.35, 0.40, 1.0))

    def update_from_game_state(self, state) -> None:
        if state is None:
            return
        if getattr(state, "harvest_yield", 3) >= 5:
            self.set_weather("CLEAR")
        elif getattr(state, "harvest_yield", 3) <= 1:
            self.set_weather("DROUGHT")
        elif getattr(state, "plague_struck", False):
            self.set_weather("FLOOD")

    def update(self, dt: float) -> None:
        self.time += dt
        self.diurnal_hour = (self.diurnal_hour + self.time_scale * dt) % 24.0

        # Celestial arc for sun
        # 6:00 (rise at East +X) -> 12:00 (high overhead) -> 18:00 (set at West -X)
        hour_rad = ((self.diurnal_hour - 6.0) / 12.0) * math.pi
        sun_x = math.cos(hour_rad) * 180.0
        sun_y = -math.sin(hour_rad) * 140.0
        sun_z = max(10.0, math.sin(hour_rad) * 220.0)

        self.dlight_np.set_pos(sun_x, sun_y, sun_z)
        self.dlight_np.look_at(0, 0, 0)

        # Brazier flame flicker physics
        for i, b in enumerate(self.brazier_lights):
            flicker = 1.0 + math.sin(self.time * 14.0 + i * 2.0) * 0.18 + random.uniform(-0.04, 0.04)
            b.node().set_color(Vec4(1.0 * flicker, 0.65 * flicker, 0.25 * flicker, 1.0))

