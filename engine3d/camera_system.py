"""
camera_system.py - Cinematic 6-Mode 3D Camera System with Spline Interpolation.

Provides professional camera directors matching user reference viewpoints:
1. AERIAL_KINGDOM: Monumental high-altitude establishing vista along the Euphrates (User Image 4)
2. THRONE_ROOM: Intimate court audience camera facing King Hammurabi on the Lion Throne (User Image 2)
3. ISHTAR_PROCESSION: Street-level perspective looking up at the Glazed Blue Ishtar Gate (User Image 1 & 3)
4. AGRARIAN_MINISTRY: Sweeping overlook across the canals, fields and granaries
5. MILITARY_COMMAND: Low-angle tracking shot along the marching phalanx
6. FREE_ORBIT: Player-controlled orbital pan, tilt, and zoom
- Smooth dampening and cinematic transition sweeps between viewpoints
- Opening cinematic camera sweep from clouds to throne
"""

import math
from typing import Dict, Optional, Tuple
from panda3d.core import (
    NodePath,
    Vec3,
)


class CameraPreset:
    def __init__(self, name: str, eye: Vec3, look_at: Vec3, description: str) -> None:
        self.name = name
        self.eye = eye
        self.look_at = look_at
        self.description = description


PRESETS: Dict[str, CameraPreset] = {
    # High altitude establishing view looking down river at Ziggurat & Palace (Image 4)
    "AERIAL_KINGDOM": CameraPreset(
        name="Aerial Imperial Vista",
        eye=Vec3(0.0, -320.0, 190.0),
        look_at=Vec3(-20.0, 40.0, 35.0),
        description="Panoramic aerial view of the Euphrates, Etemenanki Ziggurat, and Babylon.",
    ),
    # Intimate Throne Room audience with King Hammurabi (Image 2)
    "THRONE_ROOM": CameraPreset(
        name="Royal Throne Room",
        eye=Vec3(75.0, 58.0, 8.5),
        look_at=Vec3(75.0, 75.0, 9.2),
        description="Audience before Sovereign Hammurabi seated upon the Royal Lion Throne.",
    ),
    # Street level view of Ishtar Gate and crowds (Image 1 & 3)
    "ISHTAR_PROCESSION": CameraPreset(
        name="Ishtar Gate Processional",
        eye=Vec3(0.0, -110.0, 8.0),
        look_at=Vec3(0.0, -50.0, 22.0),
        description="Monumental processional street leading toward the glazed lapis Ishtar Gate.",
    ),
    # Agricultural Ministry & fields
    "AGRARIAN_MINISTRY": CameraPreset(
        name="Agricultural Ministry",
        eye=Vec3(110.0, -260.0, 48.0),
        look_at=Vec3(100.0, -160.0, 10.0),
        description="Overlook of the Euphrates canal irrigation network, fields and granaries.",
    ),
    # Military barracks and parade phalanx
    "MILITARY_COMMAND": CameraPreset(
        name="Military Command",
        eye=Vec3(-18.0, -10.0, 12.0),
        look_at=Vec3(0.0, 30.0, 4.0),
        description="Inspection of the Royal Babylonian infantry phalanx and battlements.",
    ),
}


class CameraController3D:
    """Manages camera positions, smooth transitions, and free-orbit inputs."""

    def __init__(self, camera_node: NodePath) -> None:
        self.camera = camera_node

        self.current_mode = "AERIAL_KINGDOM"
        self.current_eye = Vec3(0, -320.0, 190.0)
        self.current_target = Vec3(-20.0, 40.0, 35.0)

        self.target_eye = Vec3(self.current_eye)
        self.target_look_at = Vec3(self.current_target)

        # Free Orbit parameters
        self.orbit_center = Vec3(0, 0, 15.0)
        self.orbit_distance = 180.0
        self.orbit_heading = 0.0
        self.orbit_pitch = 30.0

        # Cinematic flyover state
        self.is_cinematic_playing = False
        self.cinematic_time = 0.0
        self.cinematic_duration = 6.0

        # Apply initial preset
        self.set_preset("AERIAL_KINGDOM", instant=True)

    def set_preset(self, preset_name: str, instant: bool = False) -> None:
        if preset_name in PRESETS:
            self.current_mode = preset_name
            p = PRESETS[preset_name]
            self.target_eye = Vec3(p.eye)
            self.target_look_at = Vec3(p.look_at)
            if instant:
                self.current_eye = Vec3(self.target_eye)
                self.current_target = Vec3(self.target_look_at)
                self._apply_camera()

    def set_free_orbit(self, heading_delta: float = 0.0, pitch_delta: float = 0.0, zoom_delta: float = 0.0) -> None:
        self.current_mode = "FREE_ORBIT"
        self.orbit_heading = (self.orbit_heading + heading_delta) % 360.0
        self.orbit_pitch = max(10.0, min(80.0, self.orbit_pitch + pitch_delta))
        self.orbit_distance = max(20.0, min(400.0, self.orbit_distance + zoom_delta))

        # Calculate spherical coordinates
        rad_h = math.radians(self.orbit_heading)
        rad_p = math.radians(self.orbit_pitch)

        ox = self.orbit_center.x + self.orbit_distance * math.sin(rad_h) * math.cos(rad_p)
        oy = self.orbit_center.y - self.orbit_distance * math.cos(rad_h) * math.cos(rad_p)
        oz = self.orbit_center.z + self.orbit_distance * math.sin(rad_p)

        self.target_eye = Vec3(ox, oy, oz)
        self.target_look_at = Vec3(self.orbit_center)

    def trigger_opening_cinematic(self) -> None:
        """Launches grand opening flyover: Clouds -> River sweep -> Ishtar Gate -> Palace Throne."""
        self.is_cinematic_playing = True
        self.cinematic_time = 0.0
        self.current_mode = "OPENING_CINEMATIC"

    def update(self, dt: float) -> None:
        if self.is_cinematic_playing:
            self.cinematic_time += dt
            t = min(1.0, self.cinematic_time / self.cinematic_duration)

            # Curved camera trajectory
            # Start: High clouds over Euphrates (0, -400, 240)
            # Midpoint: Sweeping low through Ishtar Gate (0, -80, 16)
            # End: Throne Room facing Hammurabi (75, 58, 8.5)
            if t < 0.5:
                # Segment 1: Sky to Ishtar Gate
                seg_t = t / 0.5
                self.current_eye = Vec3(0, -400.0 + seg_t * 320.0, 240.0 - seg_t * 224.0)
                self.current_target = Vec3(0, -60.0, 20.0)
            else:
                # Segment 2: Ishtar Gate to Throne Room
                seg_t = (t - 0.5) / 0.5
                self.current_eye = Vec3(seg_t * 75.0, -80.0 + seg_t * 138.0, 16.0 - seg_t * 7.5)
                self.current_target = Vec3(seg_t * 75.0, 75.0, 9.2)

            if t >= 1.0:
                self.is_cinematic_playing = False
                self.set_preset("THRONE_ROOM")

            self._apply_camera()
            return

        # Smooth exponential dampening interpolation (lerp) toward target
        lerp_rate = min(1.0, 6.0 * dt)
        self.current_eye += (self.target_eye - self.current_eye) * lerp_rate
        self.current_target += (self.target_look_at - self.current_target) * lerp_rate

        self._apply_camera()

    def _apply_camera(self) -> None:
        if self.camera is not None and not self.camera.is_empty():
            self.camera.set_pos(self.current_eye)
            self.camera.look_at(self.current_target)
