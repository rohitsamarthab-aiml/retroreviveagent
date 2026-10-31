"""
vegetation_3d.py — Procedural palm trees, date palms and agricultural vegetation.

Builds realistic-looking palm trees matching the reference images:
  - Segmented cylindrical trunk with palm_bark texture
  - Curved frond crown using tapered geometry
  - Date palm clusters (dark fruit bunches)
  - Scattered placement manager
"""

from __future__ import annotations

import math
import random
from typing import List, Tuple

try:
    from panda3d.core import (
        NodePath, GeomVertexData, GeomVertexFormat, GeomVertexWriter,
        GeomTriangles, GeomLines, Geom, GeomNode,
        LColor, LPoint3f, LVector3f,
        TransparencyAttrib,
    )
    _PANDA_AVAILABLE = True
except ImportError:
    _PANDA_AVAILABLE = False


def _cylinder(
    parent: "NodePath",
    name: str,
    radius: float,
    height: float,
    segs_h: int = 8,
    segs_v: int = 2,
    color: tuple = (110, 75, 40),
    taper: float = 0.85,
) -> "NodePath":
    """Build a tapered cylinder (trunk segment)."""
    r_norm = tuple(c / 255.0 for c in color) + (1.0,)
    fmt  = GeomVertexFormat.get_v3n3c4()
    vdata = GeomVertexData(name, fmt, Geom.UH_static)
    vdata.set_num_rows((segs_v + 1) * (segs_h + 1))

    vw = GeomVertexWriter(vdata, "vertex")
    nw = GeomVertexWriter(vdata, "normal")
    cw = GeomVertexWriter(vdata, "color")

    for vi in range(segs_v + 1):
        t = vi / segs_v
        r = radius * (1.0 - t * (1.0 - taper))
        z = height * t
        for hi in range(segs_h + 1):
            a = 2 * math.pi * hi / segs_h
            x = r * math.cos(a)
            y = r * math.sin(a)
            vw.add_data3f(x, y, z)
            nw.add_data3f(math.cos(a), math.sin(a), 0)
            cw.add_data4f(*r_norm)

    tris = GeomTriangles(Geom.UH_static)
    for vi in range(segs_v):
        for hi in range(segs_h):
            i0 = vi * (segs_h + 1) + hi
            i1 = i0 + 1
            i2 = i0 + (segs_h + 1)
            i3 = i2 + 1
            tris.add_vertices(i0, i1, i2)
            tris.add_vertices(i1, i3, i2)

    geom = Geom(vdata)
    geom.add_primitive(tris)
    node = GeomNode(name)
    node.add_geom(geom)
    np_ = parent.attach_new_node(node)
    return np_


def _palm_frond(parent: "NodePath", angle_deg: float, droop: float = 0.55) -> "NodePath":
    """A single palm frond (tapered flat ribbon, drooping outward)."""
    fmt   = GeomVertexFormat.get_v3n3c4()
    vdata = GeomVertexData("frond", fmt, Geom.UH_static)
    segs  = 12
    vdata.set_num_rows(segs * 2 + 2)

    vw = GeomVertexWriter(vdata, "vertex")
    nw = GeomVertexWriter(vdata, "normal")
    cw = GeomVertexWriter(vdata, "color")

    angle_r = math.radians(angle_deg)
    frond_len = 3.5
    width_base = 0.35
    green = (0.22, 0.45, 0.12, 1.0)

    for i in range(segs + 1):
        t = i / segs
        # parametric arc: extends outward and droops downward
        rx = frond_len * t * math.cos(angle_r)
        ry = frond_len * t * math.sin(angle_r)
        rz = frond_len * t * (0.5 - droop * t)
        w  = width_base * (1.0 - t * 0.9)

        perp_x = -math.sin(angle_r) * w
        perp_y =  math.cos(angle_r) * w

        vw.add_data3f(rx - perp_x, ry - perp_y, rz)
        vw.add_data3f(rx + perp_x, ry + perp_y, rz)
        nw.add_data3f(0, 0, 1)
        nw.add_data3f(0, 0, 1)
        shade = max(0.05, 0.9 - t * 0.4)
        cw.add_data4f(green[0] * shade, green[1] * shade, green[2], 1.0)
        cw.add_data4f(green[0] * shade, green[1] * shade, green[2], 1.0)

    tris = GeomTriangles(Geom.UH_static)
    for i in range(segs):
        i0 = i * 2
        i1 = i0 + 1
        i2 = i0 + 2
        i3 = i0 + 3
        tris.add_vertices(i0, i1, i2)
        tris.add_vertices(i1, i3, i2)

    geom = Geom(vdata)
    geom.add_primitive(tris)
    node = GeomNode("frond")
    node.add_geom(geom)
    np_ = parent.attach_new_node(node)
    np_.set_two_sided(True)
    return np_


def build_palm_tree(
    parent: "NodePath",
    height: float = 9.0,
    seed: int = 0,
    lean_x: float = 0.0,
    lean_y: float = 0.0,
) -> "NodePath":
    """
    Build a complete date palm tree.

    Parameters
    ----------
    parent  : NodePath to attach the tree root to
    height  : trunk height
    seed    : random seed for variation
    lean_x/y: trunk lean in degrees
    """
    if not _PANDA_AVAILABLE:
        return parent

    rng = random.Random(seed)
    root = parent.attach_new_node(f"palm_{seed}")

    # Multi-segment trunk
    seg_count = 4
    seg_h = height / seg_count
    seg_parent = root
    for s in range(seg_count):
        col_var = rng.randint(-15, 15)
        col = (
            max(0, min(255, 110 + col_var)),
            max(0, min(255,  75 + col_var // 2)),
            max(0, min(255,  40 + col_var // 4)),
        )
        seg = _cylinder(
            seg_parent, f"trunk_s{s}",
            radius=0.30 - s * 0.04,
            height=seg_h,
            segs_h=10, segs_v=1,
            color=col,
            taper=0.90,
        )
        # apply trunk texture
        try:
            from engine3d.texture_manager import TextureManager
            tm = TextureManager.instance()
            tex = tm.get("palm_bark")
            if tex:
                seg.set_texture(tex)
        except Exception:
            pass

        seg.set_z(s * seg_h)
        # slight sway per segment
        seg.set_hpr(
            rng.uniform(-3, 3) + lean_x * s,
            rng.uniform(-2, 2) + lean_y * s,
            0
        )
        seg_parent = seg

    # Crown node at top of trunk
    crown_root = root.attach_new_node("crown")
    crown_root.set_z(height + 0.2)

    # Fronds
    n_fronds = rng.randint(10, 14)
    for i in range(n_fronds):
        base_angle = 360.0 * i / n_fronds + rng.uniform(-8, 8)
        frond = _palm_frond(crown_root, base_angle, droop=rng.uniform(0.4, 0.7))
        frond.set_hpr(0, rng.uniform(-20, 20), 0)

    # Date clusters (small dark-orange sphere approximations)
    cluster_count = rng.randint(3, 6)
    for _ in range(cluster_count):
        cang = rng.uniform(0, 360)
        cr   = rng.uniform(0.3, 0.9)
        cz   = rng.uniform(-0.8, -0.2)
        cluster = _cylinder(
            crown_root, "dates",
            radius=0.18, height=0.55,
            segs_h=6, segs_v=1,
            color=(160, 80, 20),
            taper=0.9,
        )
        cluster.set_pos(
            cr * math.cos(math.radians(cang)),
            cr * math.sin(math.radians(cang)),
            cz
        )

    return root


class VegetationManager:
    """
    Places palm trees around the 3D world matching the reference image layout.

    Reference placement:
      - Row of palms along Euphrates river banks
      - Cluster around ziggurat base
      - Scattered in residential district
      - Row in royal gardens behind throne room
    """

    def __init__(self, parent: "NodePath") -> None:
        self._parent = parent
        self._trees: list["NodePath"] = []

    def plant_row(
        self,
        start: Tuple[float, float, float],
        end: Tuple[float, float, float],
        count: int,
        height_range: Tuple[float, float] = (7.0, 11.0),
        seed_offset: int = 0,
    ) -> None:
        """Plant *count* palms evenly spaced from *start* to *end*."""
        rng = random.Random(seed_offset * 100)
        x0, y0, z0 = start
        x1, y1, z1 = end
        for i in range(count):
            t = i / max(1, count - 1)
            x = x0 + (x1 - x0) * t + rng.uniform(-1.5, 1.5)
            y = y0 + (y1 - y0) * t + rng.uniform(-1.5, 1.5)
            z = z0 + (z1 - z0) * t
            h = rng.uniform(*height_range)
            tree = build_palm_tree(
                self._parent, height=h,
                seed=seed_offset * 100 + i,
                lean_x=rng.uniform(-5, 5),
                lean_y=rng.uniform(-5, 5),
            )
            tree.set_pos(x, y, z)
            self._trees.append(tree)

    def plant_cluster(
        self,
        centre: Tuple[float, float, float],
        count: int,
        spread: float = 8.0,
        seed_offset: int = 1000,
    ) -> None:
        """Plant *count* palms in a loose cluster around *centre*."""
        rng = random.Random(seed_offset)
        cx, cy, cz = centre
        for i in range(count):
            angle  = rng.uniform(0, 2 * math.pi)
            radius = rng.uniform(2.0, spread)
            x = cx + radius * math.cos(angle)
            y = cy + radius * math.sin(angle)
            h = rng.uniform(6.0, 10.0)
            tree = build_palm_tree(
                self._parent, height=h, seed=seed_offset + i,
                lean_x=rng.uniform(-8, 8), lean_y=rng.uniform(-8, 8),
            )
            tree.set_pos(x, y, cz)
            self._trees.append(tree)

    def setup_babylon_vegetation(self) -> None:
        """Place vegetation matching the reference images of ancient Babylon."""

        # === River Banks (Euphrates, both sides) ===
        self.plant_row((-80, -45, 0), (80, -45, 0), 14, seed_offset=1)   # south bank
        self.plant_row((-80, -20, 0), (80, -20, 0), 12, seed_offset=2)   # north bank

        # === Ziggurat gardens ===
        self.plant_cluster((-5, 30, 0), count=8, spread=18, seed_offset=10)

        # === Royal Palace gardens (behind throne) ===
        self.plant_row((-18, 55, 0), (18, 55, 0), 6, (8, 13), seed_offset=20)

        # === Ishtar Gate Processional Way (lining the road) ===
        self.plant_row((-35, -5, 0), (-35, 25, 0), 5, (7, 9), seed_offset=30)
        self.plant_row(( 35, -5, 0), ( 35, 25, 0), 5, (7, 9), seed_offset=31)

        # === Residential district scattered ===
        self.plant_cluster((25, 10, 0), count=6, spread=12, seed_offset=40)
        self.plant_cluster((-22, 8, 0), count=5, spread=10, seed_offset=50)

        # === Farm boundary rows ===
        self.plant_row((-70, 60, 0), (-70, 90, 0), 6, (6, 9), seed_offset=60)
        self.plant_row((70, 60, 0),  (70, 90, 0),  6, (6, 9), seed_offset=61)

    @property
    def tree_count(self) -> int:
        return len(self._trees)

