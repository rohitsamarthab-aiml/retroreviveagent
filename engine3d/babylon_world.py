"""
babylon_world.py - Monumental 3D Ancient Babylonian Kingdom Environment.

Assembles the full authentic 3D Mesopotamian metropolis:
- Grand Ziggurat of Etemenanki (7 stepped tiers, axial stairs, summit lapis shrine)
- Monumental Ishtar Gate (glazed lapis-blue towers, arched portal, golden lion reliefs)
- Royal Palace of Babylon (colonnaded porticos, throne hall, courtyard braziers)
- The Processional Way (paved limestone avenue with crenellated parapets)
- Euphrates River & Branching Irrigation Canals with rotating Noria Waterwheels
- Alluvial Agricultural Fields with dynamic wheat crop development
- Royal Granary Silos with visible grain levels
- Defensive Mudbrick City Walls, Watchtowers & Residential Quarters
"""

import math
from typing import List, Optional, Tuple
from panda3d.core import (
    NodePath,
    Vec3,
    Vec4,
)

from engine3d.mesh_builder import (
    create_arch,
    create_crenellations,
    create_cube,
    create_cylinder,
    create_terrain_plane,
)


# Authentic Babylonian Architectural Palette
COLOR_SANDSTONE = Vec4(0.82, 0.70, 0.52, 1.0)
COLOR_MUD_BRICK = Vec4(0.72, 0.58, 0.40, 1.0)
COLOR_LAPIS_GLAZE = Vec4(0.08, 0.22, 0.48, 1.0)      # Iconic Ishtar Gate blue
COLOR_LAPIS_LIGHT = Vec4(0.15, 0.35, 0.65, 1.0)
COLOR_GOLD = Vec4(0.88, 0.72, 0.22, 1.0)             # Royal Babylonian gold
COLOR_BRONZE = Vec4(0.65, 0.45, 0.25, 1.0)
COLOR_RIVER_WATER = Vec4(0.18, 0.42, 0.55, 0.85)     # Silt-laden Euphrates
COLOR_CANAL_WATER = Vec4(0.15, 0.38, 0.50, 0.85)
COLOR_EARTH_FERTILE = Vec4(0.35, 0.25, 0.15, 1.0)   # Alluvial mud
COLOR_WHEAT_GOLD = Vec4(0.85, 0.70, 0.20, 1.0)
COLOR_WHEAT_GREEN = Vec4(0.35, 0.60, 0.25, 1.0)
COLOR_TIMBER = Vec4(0.45, 0.30, 0.18, 1.0)


class Ziggurat3D:
    """The 7-tiered stepped pyramid of Etemenanki / Temple of Marduk."""

    def __init__(self, parent: NodePath, pos: Vec3 = Vec3(-120, 140, 0)) -> None:
        self.root = NodePath("ziggurat")
        self.root.reparent_to(parent)
        self.root.set_pos(pos)

        # 7 stepped tiers
        tier_dims = [
            (100.0, 100.0, 16.0),  # Tier 1 Base
            (82.0, 82.0, 14.0),    # Tier 2
            (66.0, 66.0, 12.0),    # Tier 3
            (52.0, 52.0, 10.0),    # Tier 4
            (40.0, 40.0, 9.0),     # Tier 5
            (30.0, 30.0, 8.0),     # Tier 6
            (22.0, 22.0, 8.0),     # Tier 7 (Summit Base)
        ]

        cur_z = 0.0
        for i, (dx, dy, dz) in enumerate(tier_dims):
            color = COLOR_LAPIS_GLAZE if i == 6 else (COLOR_LAPIS_LIGHT if i == 5 else COLOR_SANDSTONE)
            tier = create_cube(f"zig_tier_{i+1}", dx, dy, dz, color=color, center_bottom=True)
            tier.set_pos(0, 0, cur_z)
            tier.reparent_to(self.root)

            # Crenellations on lower terraces
            if i < 4:
                cren_n = create_crenellations(f"zig_cren_n_{i}", dx, 1.0, merlon_w=1.2, merlon_h=1.0, color=COLOR_GOLD)
                cren_n.set_pos(0, dy * 0.5 - 0.5, cur_z + dz)
                cren_n.reparent_to(self.root)

            cur_z += dz

        # Summit High Temple (Sanctuary of Marduk)
        shrine_w, shrine_d, shrine_h = 16.0, 16.0, 12.0
        shrine = create_cube("summit_shrine", shrine_w, shrine_d, shrine_h, color=COLOR_LAPIS_GLAZE, center_bottom=True)
        shrine.set_pos(0, 0, cur_z)
        shrine.reparent_to(self.root)

        # Gold cornice and dome
        gold_cornice = create_cube("shrine_cornice", shrine_w + 1.5, shrine_d + 1.5, 1.5, color=COLOR_GOLD, center_bottom=True)
        gold_cornice.set_pos(0, 0, cur_z + shrine_h)
        gold_cornice.reparent_to(self.root)

        dome = create_cylinder("shrine_dome", radius=5.0, height=4.0, segments=16, color=COLOR_GOLD)
        dome.set_pos(0, 0, cur_z + shrine_h + 1.5)
        dome.reparent_to(self.root)

        # Monumental Axial Stairway climbing from ground to 3rd terrace
        stair_w, stair_slope_l, stair_rise = 10.0, 60.0, 42.0
        stair_ramp = create_cube("grand_staircase", stair_w, stair_slope_l, stair_rise * 0.5, color=COLOR_MUD_BRICK, center_bottom=True)
        stair_ramp.set_pos(0, -70.0, 0)
        stair_ramp.set_p(32)  # Incline pitch
        stair_ramp.reparent_to(self.root)


class IshtarGate3D:
    """The Monumental Glazed Blue Ishtar Gate matching user reference images."""

    def __init__(self, parent: NodePath, pos: Vec3 = Vec3(0, -60, 0)) -> None:
        self.root = NodePath("ishtar_gate")
        self.root.reparent_to(parent)
        self.root.set_pos(pos)

        tower_w, tower_d, tower_h = 18.0, 18.0, 42.0
        gate_span = 20.0

        # Left Monumental Tower
        left_tower = create_cube("ishtar_tower_left", tower_w, tower_d, tower_h, color=COLOR_LAPIS_GLAZE, center_bottom=True)
        left_tower.set_pos(-gate_span * 0.5 - tower_w * 0.5, 0, 0)
        left_tower.reparent_to(self.root)

        # Left tower battlements
        left_cren = create_crenellations("ishtar_cren_left", tower_w, 1.2, merlon_w=1.4, merlon_h=1.8, color=COLOR_GOLD)
        left_cren.set_pos(-gate_span * 0.5 - tower_w * 0.5, tower_d * 0.5 - 0.6, tower_h)
        left_cren.reparent_to(self.root)

        # Right Monumental Tower
        right_tower = create_cube("ishtar_tower_right", tower_w, tower_d, tower_h, color=COLOR_LAPIS_GLAZE, center_bottom=True)
        right_tower.set_pos(gate_span * 0.5 + tower_w * 0.5, 0, 0)
        right_tower.reparent_to(self.root)

        # Right tower battlements
        right_cren = create_crenellations("ishtar_cren_right", tower_w, 1.2, merlon_w=1.4, merlon_h=1.8, color=COLOR_GOLD)
        right_cren.set_pos(gate_span * 0.5 + tower_w * 0.5, tower_d * 0.5 - 0.6, tower_h)
        right_cren.reparent_to(self.root)

        # Central Arched Portal
        portal = create_arch("ishtar_portal", span=gate_span, height=28.0, depth=14.0, wall_thickness=5.0, color=COLOR_LAPIS_GLAZE)
        portal.set_pos(0, 0, 0)
        portal.reparent_to(self.root)

        # Decorative Golden Lion Relief Bands across the facade
        for ly in [-4.0, 4.0]:
            for z_band in [8.0, 16.0, 24.0]:
                band = create_cube(f"lion_band_l_{z_band}_{ly}", tower_w - 2.0, 0.8, 1.8, color=COLOR_GOLD, center_bottom=True)
                band.set_pos(-gate_span * 0.5 - tower_w * 0.5, ly, z_band)
                band.reparent_to(self.root)

                band_r = create_cube(f"lion_band_r_{z_band}_{ly}", tower_w - 2.0, 0.8, 1.8, color=COLOR_GOLD, center_bottom=True)
                band_r.set_pos(gate_span * 0.5 + tower_w * 0.5, ly, z_band)
                band_r.reparent_to(self.root)

        # Flaming Braziers flanking the archway
        for bx in [-gate_span * 0.5 - 2.0, gate_span * 0.5 + 2.0]:
            pillar = create_cylinder(f"brazier_base_{bx}", radius=1.0, height=5.0, segments=8, color=COLOR_BRONZE)
            pillar.set_pos(bx, -10.0, 0)
            pillar.reparent_to(self.root)

            bowl = create_cylinder(f"brazier_bowl_{bx}", radius=2.0, height=1.2, segments=12, color=COLOR_GOLD)
            bowl.set_pos(bx, -10.0, 5.0)
            bowl.reparent_to(self.root)


class Palace3D:
    """Royal Palace of Babylon containing the Throne Court and Colonnades."""

    def __init__(self, parent: NodePath, pos: Vec3 = Vec3(80, 80, 0)) -> None:
        self.root = NodePath("royal_palace")
        self.root.reparent_to(parent)
        self.root.set_pos(pos)

        # Main Palace Hall
        palace_w, palace_d, palace_h = 75.0, 55.0, 24.0
        main_hall = create_cube("palace_main", palace_w, palace_d, palace_h, color=COLOR_SANDSTONE, center_bottom=True)
        main_hall.set_pos(0, 0, 0)
        main_hall.reparent_to(self.root)

        # Glazed Lapis Facade Portal
        facade_w, facade_d, facade_h = 35.0, 4.0, 28.0
        facade = create_cube("palace_facade", facade_w, facade_d, facade_h, color=COLOR_LAPIS_GLAZE, center_bottom=True)
        facade.set_pos(0, -palace_d * 0.5 - 2.0, 0)
        facade.reparent_to(self.root)

        # Grand Portico Columns with Palm Capitals
        col_spacing = 6.0
        for i in range(-2, 3):
            cx = i * col_spacing
            column = create_cylinder(f"palace_col_{i}", radius=1.2, height=22.0, segments=12, color=COLOR_SANDSTONE)
            column.set_pos(cx, -palace_d * 0.5 - 6.0, 0)
            column.reparent_to(self.root)

            capital = create_cylinder(f"palace_cap_{i}", radius=2.0, height=2.0, segments=12, color=COLOR_GOLD)
            capital.set_pos(cx, -palace_d * 0.5 - 6.0, 22.0)
            capital.reparent_to(self.root)

        # Gold frieze cornice along roof
        cornice = create_cube("palace_cornice", palace_w + 2.0, palace_d + 2.0, 2.0, color=COLOR_GOLD, center_bottom=True)
        cornice.set_pos(0, 0, palace_h)
        cornice.reparent_to(self.root)

        # Roof battlements
        cren_f = create_crenellations("palace_cren_front", palace_w, 1.2, merlon_w=1.4, merlon_h=1.6, color=COLOR_BRONZE)
        cren_f.set_pos(0, -palace_d * 0.5, palace_h + 2.0)
        cren_f.reparent_to(self.root)


class EuphratesRiver3D:
    """Flowing River Euphrates with stone embankments and bridge."""

    def __init__(self, parent: NodePath, length: float = 500.0, width: float = 45.0) -> None:
        self.root = NodePath("euphrates_river")
        self.root.reparent_to(parent)
        self.root.set_pos(0, 0, 0.2)

        # Water surface
        water = create_terrain_plane("river_surface", size_x=width, size_y=length, color=COLOR_RIVER_WATER)
        water.set_pos(-30.0, 0, 0)
        water.set_r(0)
        water.reparent_to(self.root)

        # Embankment quay walls
        left_quay = create_cube("quay_left", 3.0, length, 4.0, color=COLOR_MUD_BRICK, center_bottom=True)
        left_quay.set_pos(-30.0 - width * 0.5 - 1.5, 0, 0)
        left_quay.reparent_to(self.root)

        right_quay = create_cube("quay_right", 3.0, length, 4.0, color=COLOR_MUD_BRICK, center_bottom=True)
        right_quay.set_pos(-30.0 + width * 0.5 + 1.5, 0, 0)
        right_quay.reparent_to(self.root)

        # Monumental stone bridge spanning the river
        bridge_w, bridge_l, bridge_h = 12.0, width + 10.0, 6.0
        bridge = create_cube("royal_bridge", bridge_l, bridge_w, 2.0, color=COLOR_SANDSTONE, center_bottom=True)
        bridge.set_pos(-30.0, 20.0, 4.0)
        bridge.reparent_to(self.root)

        # Bridge piers in river
        for px in [-30.0 - width * 0.25, -30.0 + width * 0.25]:
            pier = create_cube(f"pier_{px}", 4.0, 8.0, 4.0, color=COLOR_MUD_BRICK, center_bottom=True)
            pier.set_pos(px, 20.0, 0)
            pier.reparent_to(self.root)


class IrrigationCanalNetwork3D:
    """Irrigation feeder canals and rotating wooden Noria waterwheels."""

    def __init__(self, parent: NodePath) -> None:
        self.root = NodePath("irrigation_network")
        self.root.reparent_to(parent)

        self.waterwheels: List[NodePath] = []

        # Canal 1 running east toward the farmlands
        c1 = create_cube("canal_east", 160.0, 6.0, 2.0, color=COLOR_CANAL_WATER, center_bottom=True)
        c1.set_pos(80.0, -110.0, 0.4)
        c1.reparent_to(self.root)

        # Canal 2 branching south
        c2 = create_cube("canal_south", 6.0, 140.0, 2.0, color=COLOR_CANAL_WATER, center_bottom=True)
        c2.set_pos(120.0, -180.0, 0.4)
        c2.reparent_to(self.root)

        # 3D Noria Waterwheel at canal junction
        wheel_root = NodePath("noria_wheel")
        wheel_root.set_pos(0.0, -110.0, 4.0)
        wheel_root.reparent_to(self.root)

        # Rim
        rim = create_cylinder("noria_rim", radius=6.0, height=1.2, segments=16, color=COLOR_TIMBER)
        rim.set_p(90)
        rim.reparent_to(wheel_root)

        # Spokes
        for s in range(6):
            spoke = create_cube(f"noria_spk_{s}", 0.4, 0.6, 12.0, color=COLOR_TIMBER, center_bottom=False)
            spoke.set_r(s * 30.0)
            spoke.reparent_to(wheel_root)

        self.waterwheels.append(wheel_root)

    def update(self, dt: float) -> None:
        """Rotates waterwheels."""
        for wheel in self.waterwheels:
            wheel.set_r(wheel.get_r() + 25.0 * dt)


class Granaries3D:
    """Cylindrical mudbrick storage silos with visible dynamic grain height."""

    def __init__(self, parent: NodePath, pos: Vec3 = Vec3(130, -50, 0)) -> None:
        self.root = NodePath("granaries")
        self.root.reparent_to(parent)
        self.root.set_pos(pos)

        self.silos: List[NodePath] = []
        self.grain_indicators: List[NodePath] = []

        spacing = 16.0
        for i in range(3):
            sx = i * spacing
            # Silo tower
            silo = create_cylinder(f"silo_{i}", radius=6.0, height=20.0, segments=16, color=COLOR_MUD_BRICK)
            silo.set_pos(sx, 0, 0)
            silo.reparent_to(self.root)
            self.silos.append(silo)

            # Dome
            dome = create_cylinder(f"silo_dome_{i}", radius=6.2, height=3.0, segments=16, color=COLOR_SANDSTONE)
            dome.set_pos(sx, 0, 20.0)
            dome.reparent_to(self.root)

            # Grain level visual bar inside viewing slot
            grain_bar = create_cube(f"grain_fill_{i}", 1.5, 0.8, 14.0, color=COLOR_GOLD, center_bottom=True)
            grain_bar.set_pos(sx, -6.1, 2.0)
            grain_bar.reparent_to(self.root)
            self.grain_indicators.append(grain_bar)

    def update_grain_levels(self, bushels: int) -> None:
        """Scales grain level indicator based on current state bushels."""
        for i, bar in enumerate(self.grain_indicators):
            fill_pct = min(1.0, max(0.1, (bushels - i * 1000) / 1000.0))
            bar.set_sz(fill_pct)


class FarmlandFields3D:
    """3D Agricultural field plots reacting to game state acreage and harvest yield."""

    def __init__(self, parent: NodePath, pos: Vec3 = Vec3(80, -180, 0)) -> None:
        self.root = NodePath("farmland_3d")
        self.root.reparent_to(parent)
        self.root.set_pos(pos)

        self.plots: List[NodePath] = []
        self.wheat_nodes: List[NodePath] = []

        # 6 agricultural plots
        rows, cols = 2, 3
        pw, pd = 40.0, 32.0
        for r in range(rows):
            for c in range(cols):
                px = c * (pw + 8.0)
                py = r * (pd + 8.0)

                # Alluvial soil bed
                bed = create_cube(f"field_bed_{r}_{c}", pw, pd, 0.6, color=COLOR_EARTH_FERTILE, center_bottom=True)
                bed.set_pos(px, py, 0)
                bed.reparent_to(self.root)
                self.plots.append(bed)

                # Furrows & crop stalks
                wheat_group = NodePath(f"wheat_{r}_{c}")
                wheat_group.set_pos(px, py, 0.6)
                wheat_group.reparent_to(self.root)

                # Wheat rows
                for fy in range(int(-pd * 0.4), int(pd * 0.4), 6):
                    furrow = create_cube(f"fur_{fy}", pw * 0.9, 1.2, 1.4, color=COLOR_WHEAT_GOLD, center_bottom=True)
                    furrow.set_pos(0, fy, 0)
                    furrow.reparent_to(wheat_group)

                self.wheat_nodes.append(wheat_group)

    def update_from_game_state(self, acres: int, yield_rate: int) -> None:
        """Adapts crop visual density and coloring based on simulation state."""
        col = COLOR_WHEAT_GOLD if yield_rate >= 3 else (COLOR_WHEAT_GREEN if yield_rate == 2 else COLOR_EARTH_FERTILE)
        scale_z = 1.0 if yield_rate >= 3 else (0.6 if yield_rate == 2 else 0.2)
        for wn in self.wheat_nodes:
            wn.set_color_scale(col)
            wn.set_sz(scale_z)


class BabylonCityWalls3D:
    """Monumental crenellated double perimeter walls and corner bastions."""

    def __init__(self, parent: NodePath) -> None:
        self.root = NodePath("city_walls")
        self.root.reparent_to(parent)

        wall_h, wall_d = 20.0, 8.0

        # North Wall segment
        nw = create_cube("wall_north", 360.0, wall_d, wall_h, color=COLOR_MUD_BRICK, center_bottom=True)
        nw.set_pos(0, 220.0, 0)
        nw.reparent_to(self.root)
        cren_n = create_crenellations("cren_north", 360.0, wall_d, merlon_w=2.0, merlon_h=1.8, color=COLOR_SANDSTONE)
        cren_n.set_pos(0, 220.0, wall_h)
        cren_n.reparent_to(self.root)

        # South Wall segment (with opening for Ishtar Gate)
        sw_left = create_cube("wall_south_l", 160.0, wall_d, wall_h, color=COLOR_MUD_BRICK, center_bottom=True)
        sw_left.set_pos(-100.0, -60.0, 0)
        sw_left.reparent_to(self.root)

        sw_right = create_cube("wall_south_r", 160.0, wall_d, wall_h, color=COLOR_MUD_BRICK, center_bottom=True)
        sw_right.set_pos(100.0, -60.0, 0)
        sw_right.reparent_to(self.root)

        # Corner Watchtowers
        for tx, ty in [(-180.0, 220.0), (180.0, 220.0), (-180.0, -60.0), (180.0, -60.0)]:
            tower = create_cube(f"corner_tower_{tx}_{ty}", 16.0, 16.0, 26.0, color=COLOR_SANDSTONE, center_bottom=True)
            tower.set_pos(tx, ty, 0)
            tower.reparent_to(self.root)


class BabylonWorld3D:
    """Master 3D Scene Node assembling the complete explorable Babylonian realm."""

    def __init__(self, parent: NodePath) -> None:
        self.root = NodePath("babylon_world_3d")
        self.root.reparent_to(parent)

        # 1. Vast Alluvial Plain (Ground)
        self.terrain = create_terrain_plane("alluvial_plain", size_x=900.0, size_y=900.0, color=COLOR_SANDSTONE)
        self.terrain.set_pos(0, 0, 0)
        self.terrain.reparent_to(self.root)

        # 2. Grand Ziggurat of Ur / Etemenanki
        self.ziggurat = Ziggurat3D(self.root, pos=Vec3(-120.0, 110.0, 0))

        # 3. Monumental Ishtar Gate
        self.ishtar_gate = IshtarGate3D(self.root, pos=Vec3(0, -60.0, 0))

        # 4. Processional Way of Babylon (Limestone paved road)
        self.procession_way = create_cube("procession_road", 18.0, 180.0, 0.4, color=Vec4(0.90, 0.86, 0.78, 1.0), center_bottom=True)
        self.procession_way.set_pos(0, 30.0, 0)
        self.procession_way.reparent_to(self.root)

        # 5. Royal Palace of Babylon
        self.palace = Palace3D(self.root, pos=Vec3(75.0, 75.0, 0))

        # 6. River Euphrates & Bridges
        self.river = EuphratesRiver3D(self.root, length=700.0, width=50.0)

        # 7. Irrigation Canals & Waterwheels
        self.canals = IrrigationCanalNetwork3D(self.root)

        # 8. Royal Granaries
        self.granaries = Granaries3D(self.root, pos=Vec3(115.0, -40.0, 0))

        # 9. Cultivated Agricultural Fields
        self.farmlands = FarmlandFields3D(self.root, pos=Vec3(60.0, -180.0, 0))

        # 10. City Walls & Fortifications
        self.walls = BabylonCityWalls3D(self.root)

        # 11. Residential Mudbrick Quarter (Blocks of houses with courtyards)
        self._build_residential_quarter()

    def _build_residential_quarter(self) -> None:
        """Populates urban district with authentic Mesopotamian flat-roof houses."""
        quarter_root = NodePath("residential_district")
        quarter_root.reparent_to(self.root)
        rng_seed = 1792
        import random
        rng = random.Random(rng_seed)

        start_x, start_y = -160.0, -40.0
        for r in range(4):
            for c in range(3):
                hx = start_x + c * 18.0 + rng.uniform(-2, 2)
                hy = start_y + r * 18.0 + rng.uniform(-2, 2)
                hw = rng.uniform(8.0, 12.0)
                hd = rng.uniform(8.0, 12.0)
                hh = rng.uniform(6.0, 10.0)

                house = create_cube(f"house_{r}_{c}", hw, hd, hh, color=COLOR_MUD_BRICK, center_bottom=True)
                house.set_pos(hx, hy, 0)
                house.reparent_to(quarter_root)

                # Parapet on roof
                parapet = create_crenellations(f"house_p_{r}_{c}", hw, 0.6, merlon_w=0.8, merlon_h=0.8, color=COLOR_SANDSTONE)
                parapet.set_pos(hx, hy + hd * 0.5 - 0.3, hh)
                parapet.reparent_to(quarter_root)

    def update(self, dt: float) -> None:
        """Updates animated dynamic elements (waterwheels, river)."""
        self.canals.update(dt)

    def update_from_game_state(self, state) -> None:
        """Connects simulation state to 3D geometry."""
        if state is None:
            return
        # Granaries
        self.granaries.update_grain_levels(getattr(state, "bushels", 2800))
        # Fields
        self.farmlands.update_from_game_state(
            getattr(state, "acres", 1000),
            getattr(state, "harvest_yield", 3),
        )

