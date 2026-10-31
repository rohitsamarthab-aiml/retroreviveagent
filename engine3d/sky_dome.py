"""
sky_dome.py — Procedural sky dome and atmospheric sky for the Babylon 3D engine.

Creates:
  - A hemisphere sky dome with golden-hour gradient texture
  - A visible sun disc (billboard glowing sphere near horizon)
  - Animated cloud billboards drifting across the sky
  - Dust haze layer at ground level for desert atmosphere
"""

from __future__ import annotations

import math

try:
    from panda3d.core import (
        NodePath, GeomVertexData, GeomVertexFormat, GeomVertexWriter,
        GeomTriangles, Geom, GeomNode, LColor, LVector3f, LPoint3f,
        CardMaker, TransparencyAttrib, BillboardEffect, AntialiasAttrib,
        ColorBlendAttrib, RenderState,
    )
    _PANDA_AVAILABLE = True
except ImportError:
    _PANDA_AVAILABLE = False


def _build_dome_geometry(radius: float = 300.0, h_segs: int = 24, v_segs: int = 12) -> "GeomNode":
    """Create a hemisphere (sky dome) with UV coordinates for texture mapping."""
    fmt  = GeomVertexFormat.get_v3t2()   # position + UV
    vdata = GeomVertexData("sky_dome", fmt, Geom.UH_static)
    vdata.set_num_rows((h_segs + 1) * (v_segs + 1))

    vwriter = GeomVertexWriter(vdata, "vertex")
    twriter = GeomVertexWriter(vdata, "texcoord")

    # Build hemisphere vertices
    for vi in range(v_segs + 1):
        phi = (math.pi / 2) * vi / v_segs   # 0 = horizon, pi/2 = zenith
        for hi in range(h_segs + 1):
            theta = 2 * math.pi * hi / h_segs
            x = radius * math.cos(phi) * math.cos(theta)
            y = radius * math.cos(phi) * math.sin(theta)
            z = radius * math.sin(phi)
            vwriter.add_data3f(x, y, z)
            u = hi / h_segs
            v = vi / v_segs
            twriter.add_data2f(u, v)

    # Build triangles
    tris = GeomTriangles(Geom.UH_static)
    for vi in range(v_segs):
        for hi in range(h_segs):
            i0 = vi * (h_segs + 1) + hi
            i1 = i0 + 1
            i2 = i0 + (h_segs + 1)
            i3 = i2 + 1
            # inside-facing triangles (normals point inward)
            tris.add_vertices(i0, i2, i1)
            tris.add_vertices(i1, i2, i3)

    geom = Geom(vdata)
    geom.add_primitive(tris)
    node = GeomNode("sky_dome")
    node.add_geom(geom)
    return node


def _build_sun_disc() -> "GeomNode":
    """Simple glowing sun disc geometry (flat circle in XY plane)."""
    fmt  = GeomVertexFormat.get_v3c4()
    vdata = GeomVertexData("sun_disc", fmt, Geom.UH_static)
    segs = 32
    vdata.set_num_rows(segs + 2)

    vwriter = GeomVertexWriter(vdata, "vertex")
    cwriter = GeomVertexWriter(vdata, "color")

    # centre
    vwriter.add_data3f(0, 0, 0)
    cwriter.add_data4f(1.0, 0.95, 0.7, 1.0)    # bright warm white

    r = 8.0
    for i in range(segs + 1):
        a = 2 * math.pi * i / segs
        vwriter.add_data3f(r * math.cos(a), r * math.sin(a), 0)
        cwriter.add_data4f(1.0, 0.85, 0.4, 0.0)  # fade to transparent at edge

    tris = GeomTriangles(Geom.UH_static)
    for i in range(1, segs + 1):
        tris.add_vertices(0, i, i % segs + 1)

    geom = Geom(vdata)
    geom.add_primitive(tris)
    node = GeomNode("sun_disc")
    node.add_geom(geom)
    return node


class SkyDome:
    """
    Manages the sky dome, sun disc, and cloud layer.

    Usage::

        sky = SkyDome(render)
        sky.set_time_of_day(0.65)   # 0.0 midnight, 0.25 dawn, 0.65 golden hour
        sky.update(dt)
    """

    # (zenith_color, horizon_color, sun_intensity) keyed by time-of-day label
    _TOD_PRESETS = {
        "dawn":        (LColor(0.3, 0.35, 0.6, 1), LColor(0.9, 0.55, 0.3, 1), 0.6),
        "golden_hour": (LColor(0.35, 0.5, 0.8, 1),  LColor(0.95, 0.70, 0.28, 1), 1.0),
        "noon":        (LColor(0.25, 0.55, 0.95, 1), LColor(0.75, 0.88, 0.98, 1), 1.4),
        "dusk":        (LColor(0.2, 0.25, 0.5, 1),  LColor(0.85, 0.42, 0.18, 1), 0.5),
        "night":       (LColor(0.04, 0.06, 0.18, 1), LColor(0.06, 0.08, 0.20, 1), 0.05),
    }

    def __init__(self, render: "NodePath") -> None:
        if not _PANDA_AVAILABLE:
            return

        self._render = render
        self._time   = 0.0      # 0–1 full day cycle
        self._cloud_offset = 0.0

        # --- Dome node ---
        dome_geom = _build_dome_geometry(radius=290, h_segs=36, v_segs=18)
        self._dome_np = render.attach_new_node(dome_geom)
        self._dome_np.set_name("sky_dome")
        self._dome_np.set_two_sided(True)
        self._dome_np.set_depth_write(False)
        self._dome_np.set_depth_test(False)
        self._dome_np.set_bin("background", 0)
        self._dome_np.set_light_off()
        self._dome_np.set_shader_off()

        # Apply sky gradient texture
        try:
            from engine3d.texture_manager import TextureManager
            tm = TextureManager.instance()
            sky_tex = tm.get("sky_gradient")
            if sky_tex:
                self._dome_np.set_texture(sky_tex)
        except Exception:
            # fallback: plain blue
            self._dome_np.set_color(0.25, 0.55, 0.85, 1.0)

        # --- Sun disc ---
        sun_geom = _build_sun_disc()
        self._sun_np = render.attach_new_node(sun_geom)
        self._sun_np.set_name("sun_disc")
        self._sun_np.set_transparency(TransparencyAttrib.M_alpha)
        self._sun_np.set_depth_write(False)
        self._sun_np.set_light_off()
        self._sun_np.set_shader_off()
        self._sun_np.set_bin("background", 1)
        self._sun_np.set_scale(1.0)

        # --- Clouds (simple flat billboards) ---
        self._clouds: list["NodePath"] = []
        self._create_clouds(12)

        # Default: golden hour
        self.set_time_of_day(0.65)

    def _create_clouds(self, count: int) -> None:
        """Create card-based cloud billboards."""
        import random
        rng = random.Random(42)
        cm = CardMaker("cloud")
        cm.set_frame(-1, 1, -0.35, 0.35)

        for i in range(count):
            cloud_np = self._render.attach_new_node(cm.generate())
            cloud_np.set_name(f"cloud_{i}")
            cloud_np.set_color(
                rng.uniform(0.90, 1.0),
                rng.uniform(0.85, 0.95),
                rng.uniform(0.70, 0.85),
                rng.uniform(0.25, 0.55),
            )
            cloud_np.set_transparency(TransparencyAttrib.M_alpha)
            cloud_np.set_depth_write(False)
            cloud_np.set_light_off()
            cloud_np.set_shader_off()
            cloud_np.set_bin("background", 2)

            # Position on dome
            theta = rng.uniform(0, 2 * math.pi)
            phi   = rng.uniform(0.3, 0.8)   # mid-sky
            r     = 260.0
            x = r * math.cos(phi) * math.cos(theta)
            y = r * math.cos(phi) * math.sin(theta)
            z = r * math.sin(phi)
            cloud_np.set_pos(x, y, z)
            sw = rng.uniform(20, 60)
            cloud_np.set_scale(sw, sw, sw * 0.4)
            cloud_np.look_at(0, 0, 0)
            self._clouds.append(cloud_np)

    def set_time_of_day(self, t: float) -> None:
        """
        Update sky colours for time-of-day *t* in [0, 1].
        0.0=midnight, 0.25=dawn, 0.5=noon, 0.65=golden-hour, 0.75=dusk.
        """
        self._time = t % 1.0

        # Pick preset
        if self._time < 0.15 or self._time > 0.92:
            preset = "night"
        elif self._time < 0.3:
            preset = "dawn"
        elif self._time < 0.55:
            preset = "noon"
        elif self._time < 0.78:
            preset = "golden_hour"
        else:
            preset = "dusk"

        _zenith, horizon, _sun_int = self._TOD_PRESETS[preset]

        # Tint the dome
        self._dome_np.set_color(
            horizon.x * 0.9, horizon.y * 0.8, horizon.z * 0.7, 1.0
        )

        # Position sun on arc
        sun_angle = (t * 2 * math.pi) - math.pi / 2   # rises east, sets west
        sun_r     = 280.0
        sun_elev  = max(0.05, math.sin(t * math.pi))
        sx = sun_r * math.cos(sun_angle)
        sy = sun_r * math.sin(sun_angle)
        sz = sun_r * sun_elev
        self._sun_np.set_pos(sx, sy, sz)
        self._sun_np.look_at(0, 0, 0)
        sun_scale = 1.0 + 0.5 * (1.0 - sun_elev)   # bigger near horizon
        self._sun_np.set_scale(sun_scale * 8)

    def update(self, dt: float, wind_speed: float = 1.0) -> None:
        """Drift clouds slowly across the sky (call each frame)."""
        self._cloud_offset += dt * 0.008 * wind_speed
        for i, cloud_np in enumerate(self._clouds):
            # Rotate cloud positions slowly around Z axis
            pos = cloud_np.get_pos()
            angle = math.atan2(pos.y, pos.x) + dt * 0.003 * (1 + i % 3 * 0.2)
            r     = math.sqrt(pos.x ** 2 + pos.y ** 2)
            cloud_np.set_x(r * math.cos(angle))
            cloud_np.set_y(r * math.sin(angle))

    def set_weather_tint(self, state: str) -> None:
        """Override sky tint for weather states: 'clear', 'flood', 'drought', 'sandstorm'."""
        tints = {
            "clear":     (0.75, 0.85, 0.95),
            "flood":     (0.45, 0.55, 0.70),
            "drought":   (0.85, 0.78, 0.55),
            "sandstorm": (0.90, 0.72, 0.38),
        }
        t = tints.get(state, tints["clear"])
        self._dome_np.set_color(*t, 1.0)

