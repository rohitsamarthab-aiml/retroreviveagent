"""
cinematics_3d.py - 3D Real-Time In-Engine Cinematic Event Director.

Drives genuine real-time 3D camera choreographies and atmospheric events:
1. Royal Court of Babylon (Throne room column tracking toward King Hammurabi)
2. Golden Harvest (Low sweep across waving wheat rows and working reapers)
3. Euphrates Flood (Torrential storm overcast and surging water level)
4. Scorched Earth Drought (Amber sirocco dust storm across parched fields)
5. Military March (Low tracking angle along the marching infantry phalanx)
6. Royal Coronation (Summit ziggurat fireworks and royal brazier illumination)
7. Ishtar Gate Celebration (Processional march through glazed blue gateway)
8. Kingdom Expansion (Grand aerial ascent overlooking the empire)
"""

from typing import Callable, Optional
from panda3d.core import Vec3

from engine3d.atmosphere_3d import Atmosphere3D
from engine3d.camera_system import CameraController3D


class CinematicEvent3D:
    def __init__(
        self,
        event_id: str,
        name: str,
        duration: float,
        start_eye: Vec3,
        end_eye: Vec3,
        look_at: Vec3,
        weather: str = "CLEAR",
        on_complete: Optional[Callable[[], None]] = None,
    ) -> None:
        self.event_id = event_id
        self.name = name
        self.duration = duration
        self.elapsed = 0.0
        self.start_eye = start_eye
        self.end_eye = end_eye
        self.look_at = look_at
        self.weather = weather
        self.on_complete = on_complete
        self.is_active = True

    def update(self, dt: float, camera: CameraController3D, atmosphere: Atmosphere3D) -> bool:
        if not self.is_active:
            return False

        self.elapsed += dt
        t = min(1.0, self.elapsed / self.duration)

        # Smooth spline camera interpolation
        smooth_t = t * t * (3.0 - 2.0 * t)  # Smoothstep
        camera.current_eye = self.start_eye + (self.end_eye - self.start_eye) * smooth_t
        camera.current_target = self.look_at
        camera._apply_camera()

        atmosphere.set_weather(self.weather)

        if self.elapsed >= self.duration:
            self.is_active = False
            if self.on_complete:
                self.on_complete()
            return False
        return True


class CinematicDirector3D:
    """Orchestrates 3D cutscenes and camera choreographies."""

    def __init__(self, camera: CameraController3D, atmosphere: Atmosphere3D) -> None:
        self.camera = camera
        self.atmosphere = atmosphere
        self.current_event: Optional[CinematicEvent3D] = None

    def is_playing(self) -> bool:
        return self.current_event is not None and self.current_event.is_active

    def stop_current(self) -> None:
        if self.current_event:
            self.current_event.is_active = False
            self.current_event = None
            self.camera.set_preset("AERIAL_KINGDOM")
            self.atmosphere.set_weather("CLEAR")

    def play_event(self, event_id: str, on_complete: Optional[Callable[[], None]] = None) -> None:
        """Launches one of the 8 signature 3D cinematic events."""
        events = {
            "royal_court": CinematicEvent3D(
                event_id="royal_court",
                name="Royal Court of Babylon",
                duration=4.5,
                start_eye=Vec3(75.0, 30.0, 10.0),
                end_eye=Vec3(75.0, 62.0, 8.5),
                look_at=Vec3(75.0, 75.0, 9.2),
                weather="CLEAR",
                on_complete=on_complete,
            ),
            "golden_harvest": CinematicEvent3D(
                event_id="golden_harvest",
                name="Golden Alluvial Harvest",
                duration=4.5,
                start_eye=Vec3(40.0, -210.0, 14.0),
                end_eye=Vec3(150.0, -150.0, 20.0),
                look_at=Vec3(90.0, -170.0, 2.0),
                weather="CLEAR",
                on_complete=on_complete,
            ),
            "euphrates_flood": CinematicEvent3D(
                event_id="euphrates_flood",
                name="Euphrates Inundation",
                duration=4.5,
                start_eye=Vec3(-40.0, -250.0, 35.0),
                end_eye=Vec3(-20.0, -50.0, 15.0),
                look_at=Vec3(-30.0, 20.0, 4.0),
                weather="FLOOD",
                on_complete=on_complete,
            ),
            "scorched_drought": CinematicEvent3D(
                event_id="scorched_drought",
                name="Scorched Earth Drought",
                duration=4.5,
                start_eye=Vec3(160.0, -120.0, 40.0),
                end_eye=Vec3(60.0, -180.0, 12.0),
                look_at=Vec3(100.0, -160.0, 0.0),
                weather="DROUGHT",
                on_complete=on_complete,
            ),
            "military_march": CinematicEvent3D(
                event_id="military_march",
                name="Imperial Phalanx March",
                duration=4.5,
                start_eye=Vec3(-16.0, -30.0, 6.0),
                end_eye=Vec3(-16.0, 50.0, 6.0),
                look_at=Vec3(0.0, 30.0, 4.0),
                weather="CLEAR",
                on_complete=on_complete,
            ),
            "royal_coronation": CinematicEvent3D(
                event_id="royal_coronation",
                name="Royal Coronation",
                duration=5.0,
                start_eye=Vec3(-120.0, 20.0, 50.0),
                end_eye=Vec3(-120.0, 95.0, 88.0),
                look_at=Vec3(-120.0, 110.0, 86.0),
                weather="CLEAR",
                on_complete=on_complete,
            ),
            "ishtar_celebration": CinematicEvent3D(
                event_id="ishtar_celebration",
                name="Ishtar Gate Processional",
                duration=4.5,
                start_eye=Vec3(0.0, -130.0, 7.0),
                end_eye=Vec3(0.0, -35.0, 12.0),
                look_at=Vec3(0.0, -60.0, 24.0),
                weather="CLEAR",
                on_complete=on_complete,
            ),
            "kingdom_expansion": CinematicEvent3D(
                event_id="kingdom_expansion",
                name="Kingdom Expansion",
                duration=5.0,
                start_eye=Vec3(0.0, -100.0, 40.0),
                end_eye=Vec3(0.0, -380.0, 220.0),
                look_at=Vec3(0.0, 40.0, 20.0),
                weather="CLEAR",
                on_complete=on_complete,
            ),
        }

        if event_id in events:
            self.current_event = events[event_id]

    def update(self, dt: float) -> None:
        if self.current_event:
            active = self.current_event.update(dt, self.camera, self.atmosphere)
            if not active:
                self.current_event = None
                self.camera.set_preset("AERIAL_KINGDOM")

