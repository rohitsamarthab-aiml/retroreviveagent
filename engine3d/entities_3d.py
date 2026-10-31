"""
entities_3d.py - Animated 3D Living Entities for the Babylonian Kingdom.

Implements realistic animated Mesopotamian characters and units:
- Babylonian Spearman (Conical bronze helmet, bronze scale armor, shield, and tall spear)
- Marching Military Phalanx Formations along city battlements and barracks
- Reaping Farmers working in the agricultural fields
- Walking Citizens in traditional Mesopotamian robes crossing streets and bridges
- Merchant Trade Carts with pack oxen transporting grain sacks
- Population-driven dynamic density scaling
"""

import math
import random
from typing import List, Optional
from panda3d.core import (
    NodePath,
    Vec3,
    Vec4,
)

from engine3d.mesh_builder import (
    create_cube,
    create_cylinder,
)


COLOR_BRONZE = Vec4(0.65, 0.45, 0.25, 1.0)
COLOR_GOLD = Vec4(0.88, 0.72, 0.22, 1.0)
COLOR_SKIN = Vec4(0.82, 0.65, 0.48, 1.0)
COLOR_TUNIC_WHITE = Vec4(0.88, 0.85, 0.78, 1.0)
COLOR_TUNIC_BLUE = Vec4(0.18, 0.35, 0.58, 1.0)
COLOR_TUNIC_RED = Vec4(0.60, 0.20, 0.20, 1.0)
COLOR_TIMBER = Vec4(0.42, 0.28, 0.16, 1.0)
COLOR_OX = Vec4(0.55, 0.40, 0.28, 1.0)


class SoldierUnit3D:
    """3D Babylonian infantry spearman with walking and guard animations."""

    def __init__(self, parent: NodePath, pos: Vec3 = Vec3(0, 0, 0), facing: float = 0.0) -> None:
        self.root = NodePath("soldier_3d")
        self.root.reparent_to(parent)
        self.root.set_pos(pos)
        self.root.set_h(facing)

        self.walk_phase = random.uniform(0.0, 6.28)
        self.is_marching = True

        # Hierarchical joints
        self.legs = NodePath("legs")
        self.legs.reparent_to(self.root)

        self.leg_l = create_cube("leg_l", 0.4, 0.5, 1.8, color=COLOR_SKIN, center_bottom=True)
        self.leg_l.set_pos(-0.35, 0, 0)
        self.leg_l.reparent_to(self.legs)

        self.leg_r = create_cube("leg_r", 0.4, 0.5, 1.8, color=COLOR_SKIN, center_bottom=True)
        self.leg_r.set_pos(0.35, 0, 0)
        self.leg_r.reparent_to(self.legs)

        # Torso with scale bronze armor
        self.torso = create_cube("s_torso", 1.4, 0.9, 1.8, color=COLOR_BRONZE, center_bottom=True)
        self.torso.set_pos(0, 0, 1.8)
        self.torso.reparent_to(self.root)

        # Conical Babylonian bronze helmet
        self.head = NodePath("s_head")
        self.head.set_pos(0, 0, 3.6)
        self.head.reparent_to(self.root)

        head_cube = create_cube("s_head_cube", 0.7, 0.7, 0.8, color=COLOR_SKIN, center_bottom=True)
        head_cube.set_pos(0, 0, 0)
        head_cube.reparent_to(self.head)

        helmet = create_cylinder("s_helmet", radius=0.45, height=0.9, segments=12, color=COLOR_GOLD)
        helmet.set_pos(0, 0, 0.7)
        helmet.reparent_to(self.head)

        # Shield in left hand
        self.shield = create_cylinder("s_shield", radius=0.8, height=0.15, segments=12, color=COLOR_BRONZE)
        self.shield.set_p(90)
        self.shield.set_pos(-0.9, 0.2, 2.4)
        self.shield.reparent_to(self.root)

        # Tall bronze spear in right hand
        self.spear = create_cylinder("s_spear", radius=0.06, height=4.2, segments=6, color=COLOR_TIMBER)
        self.spear.set_pos(0.9, 0.2, 0.8)
        self.spear.reparent_to(self.root)

        spearhead = create_cylinder("spear_tip", radius=0.14, height=0.6, segments=6, color=COLOR_GOLD)
        spearhead.set_pos(0.9, 0.2, 5.0)
        spearhead.reparent_to(self.root)

    def update(self, dt: float) -> None:
        if self.is_marching:
            self.walk_phase += 6.5 * dt
            swing = math.sin(self.walk_phase) * 24.0
            self.leg_l.set_p(swing)
            self.leg_r.set_p(-swing)
            self.spear.set_p(swing * 0.2)


class SoldierPhalanx3D:
    """3x3 Regiment of soldiers marching in cohesive formation."""

    def __init__(self, parent: NodePath, start_pos: Vec3, end_pos: Vec3) -> None:
        self.root = NodePath("phalanx_formation")
        self.root.reparent_to(parent)
        self.root.set_pos(start_pos)

        self.start_pos = start_pos
        self.end_pos = end_pos
        self.speed = 12.0
        self.progress = 0.0
        self.direction = 1

        self.soldiers: List[SoldierUnit3D] = []

        # 3 rows x 3 columns
        spacing = 2.4
        for r in range(3):
            for c in range(3):
                sx = (c - 1) * spacing
                sy = (r - 1) * spacing
                soldier = SoldierUnit3D(self.root, pos=Vec3(sx, sy, 0), facing=0.0)
                self.soldiers.append(soldier)

    def update(self, dt: float) -> None:
        # Move back and forth along patrol corridor
        delta = self.end_pos - self.start_pos
        dist = delta.length()
        if dist > 0.01:
            self.progress += (self.speed * dt / dist) * self.direction
            if self.progress >= 1.0:
                self.progress = 1.0
                self.direction = -1
                self.root.set_h(180.0)
            elif self.progress <= 0.0:
                self.progress = 0.0
                self.direction = 1
                self.root.set_h(0.0)

            cur_pos = self.start_pos + delta * self.progress
            self.root.set_pos(cur_pos)

        for s in self.soldiers:
            s.update(dt)


class Farmer3D:
    """Animated Mesopotamian peasant reaping crops in the fields."""

    def __init__(self, parent: NodePath, pos: Vec3) -> None:
        self.root = NodePath("farmer_3d")
        self.root.reparent_to(parent)
        self.root.set_pos(pos)

        self.time = random.uniform(0.0, 6.28)

        # Body
        body = create_cube("f_body", 1.0, 0.7, 1.6, color=COLOR_TUNIC_WHITE, center_bottom=True)
        body.set_pos(0, 0, 1.4)
        body.reparent_to(self.root)

        # Head & Straw Sun Hat
        head = create_cube("f_head", 0.6, 0.6, 0.6, color=COLOR_SKIN, center_bottom=True)
        head.set_pos(0, 0, 3.0)
        head.reparent_to(self.root)

        hat = create_cylinder("f_hat", radius=1.0, height=0.2, segments=12, color=COLOR_TIMBER)
        hat.set_pos(0, 0, 3.6)
        hat.reparent_to(self.root)

        # Reaping Sickle Arm
        self.arm = NodePath("f_sickle_arm")
        self.arm.set_pos(0.6, 0, 2.4)
        self.arm.reparent_to(self.root)

        sickle_blade = create_cylinder("sickle_blade", radius=0.4, height=0.1, segments=8, color=COLOR_GOLD)
        sickle_blade.set_p(90)
        sickle_blade.set_pos(0, 0.5, 0)
        sickle_blade.reparent_to(self.arm)

    def update(self, dt: float) -> None:
        self.time += 3.2 * dt
        # Sickle swing motion
        swing = math.sin(self.time) * 35.0
        self.arm.set_p(swing)


class Citizen3D:
    """Walking Babylonian citizen traversing roads and quays."""

    def __init__(self, parent: NodePath, path_start: Vec3, path_end: Vec3, color: Vec4 = COLOR_TUNIC_BLUE) -> None:
        self.root = NodePath("citizen_3d")
        self.root.reparent_to(parent)
        self.root.set_pos(path_start)

        self.start_pos = path_start
        self.end_pos = path_end
        self.speed = random.uniform(5.0, 8.0)
        self.progress = random.uniform(0.0, 1.0)
        self.direction = 1
        self.time = random.uniform(0.0, 6.28)

        # Draped Mesopotamian Robe
        robe = create_cube("c_robe", 1.0, 0.8, 2.6, color=color, center_bottom=True)
        robe.set_pos(0, 0, 0.4)
        robe.reparent_to(self.root)

        # Head & Headband
        head = create_cube("c_head", 0.6, 0.6, 0.7, color=COLOR_SKIN, center_bottom=True)
        head.set_pos(0, 0, 3.0)
        head.reparent_to(self.root)

        headband = create_cylinder("c_band", radius=0.38, height=0.15, segments=8, color=COLOR_GOLD)
        headband.set_pos(0, 0, 3.5)
        headband.reparent_to(self.root)

    def update(self, dt: float) -> None:
        self.time += dt
        delta = self.end_pos - self.start_pos
        dist = delta.length()
        if dist > 0.01:
            self.progress += (self.speed * dt / dist) * self.direction
            if self.progress >= 1.0:
                self.progress = 1.0
                self.direction = -1
                self.root.set_h(180.0)
            elif self.progress <= 0.0:
                self.progress = 0.0
                self.direction = 1
                self.root.set_h(0.0)

            cur_pos = self.start_pos + delta * self.progress
            # Stride bob
            bob = math.sin(self.time * 9.0) * 0.15
            self.root.set_pos(cur_pos.x, cur_pos.y, cur_pos.z + bob)


class MerchantCart3D:
    """Merchant guiding pack ox with timber cart piled with grain sacks."""

    def __init__(self, parent: NodePath, path_start: Vec3, path_end: Vec3) -> None:
        self.root = NodePath("merchant_cart")
        self.root.reparent_to(parent)
        self.root.set_pos(path_start)

        self.start_pos = path_start
        self.end_pos = path_end
        self.speed = 6.0
        self.progress = 0.0
        self.direction = 1
        self.wheel_angle = 0.0

        # Pack Ox
        self.ox = NodePath("ox")
        self.ox.set_pos(0, 5.0, 0)
        self.ox.reparent_to(self.root)

        ox_body = create_cube("ox_body", 1.8, 3.6, 2.2, color=COLOR_OX, center_bottom=True)
        ox_body.set_pos(0, 0, 1.2)
        ox_body.reparent_to(self.ox)

        ox_head = create_cube("ox_head", 1.2, 1.6, 1.6, color=COLOR_OX, center_bottom=True)
        ox_head.set_pos(0, 2.2, 2.2)
        ox_head.reparent_to(self.ox)

        # Wooden Cart
        cart = create_cube("cart_box", 3.2, 4.4, 1.6, color=COLOR_TIMBER, center_bottom=True)
        cart.set_pos(0, 0, 1.2)
        cart.reparent_to(self.root)

        # Grain Sacks
        for gx, gy in [(-0.8, -0.8), (0.8, -0.8), (0.0, 0.8), (0.0, 0.0)]:
            sack = create_cube(f"sack_{gx}_{gy}", 1.4, 1.4, 1.0, color=COLOR_TUNIC_WHITE, center_bottom=True)
            sack.set_pos(gx, gy, 2.8)
            sack.reparent_to(self.root)

        # Spoked Wheels
        self.wheel_l = create_cylinder("wheel_l", radius=1.5, height=0.3, segments=12, color=COLOR_TIMBER)
        self.wheel_l.set_r(90)
        self.wheel_l.set_pos(-1.8, 0, 1.5)
        self.wheel_l.reparent_to(self.root)

        self.wheel_r = create_cylinder("wheel_r", radius=1.5, height=0.3, segments=12, color=COLOR_TIMBER)
        self.wheel_r.set_r(90)
        self.wheel_r.set_pos(1.8, 0, 1.5)
        self.wheel_r.reparent_to(self.root)

    def update(self, dt: float) -> None:
        delta = self.end_pos - self.start_pos
        dist = delta.length()
        if dist > 0.01:
            self.progress += (self.speed * dt / dist) * self.direction
            if self.progress >= 1.0:
                self.progress = 1.0
                self.direction = -1
                self.root.set_h(180.0)
            elif self.progress <= 0.0:
                self.progress = 0.0
                self.direction = 1
                self.root.set_h(0.0)

            cur_pos = self.start_pos + delta * self.progress
            self.root.set_pos(cur_pos)

        self.wheel_angle += 45.0 * dt
        self.wheel_l.set_p(self.wheel_angle)
        self.wheel_r.set_p(self.wheel_angle)


class EntitiesManager3D:
    """Manages all animated entities and adapts density to game state."""

    def __init__(self, parent: NodePath) -> None:
        self.root = NodePath("entities_manager")
        self.root.reparent_to(parent)

        self.soldiers: List[SoldierUnit3D] = []
        self.phalanxes: List[SoldierPhalanx3D] = []
        self.farmers: List[Farmer3D] = []
        self.citizens: List[Citizen3D] = []
        self.carts: List[MerchantCart3D] = []

        self._spawn_world_entities()

    def _spawn_world_entities(self) -> None:
        # 1. Phalanx marching along the Processional Way
        ph1 = SoldierPhalanx3D(self.root, start_pos=Vec3(0, -40.0, 0.4), end_pos=Vec3(0, 110.0, 0.4))
        self.phalanxes.append(ph1)

        # 2. Sentries guarding Palace Gates
        g1 = SoldierUnit3D(self.root, pos=Vec3(58.0, 48.0, 0), facing=0.0)
        g2 = SoldierUnit3D(self.root, pos=Vec3(92.0, 48.0, 0), facing=0.0)
        self.soldiers.extend([g1, g2])

        # 3. Sentries on City Wall Battlement
        w1 = SoldierUnit3D(self.root, pos=Vec3(-40.0, -60.0, 20.0), facing=90.0)
        w2 = SoldierUnit3D(self.root, pos=Vec3(40.0, -60.0, 20.0), facing=-90.0)
        self.soldiers.extend([w1, w2])

        # 4. Farmers working the cultivated field plots
        farmer_coords = [
            Vec3(75.0, -170.0, 0.6),
            Vec3(110.0, -175.0, 0.6),
            Vec3(150.0, -165.0, 0.6),
            Vec3(85.0, -145.0, 0.6),
        ]
        for fpos in farmer_coords:
            farmer = Farmer3D(self.root, fpos)
            self.farmers.append(farmer)

        # 5. Walking Citizens along quayside and residential streets
        cit_routes = [
            (Vec3(-20.0, -30.0, 0.2), Vec3(-20.0, 80.0, 0.2), COLOR_TUNIC_BLUE),
            (Vec3(-140.0, -30.0, 0), Vec3(-140.0, 40.0, 0), COLOR_TUNIC_RED),
            (Vec3(60.0, 20.0, 4.0), Vec3(-60.0, 20.0, 4.0), COLOR_TUNIC_WHITE),  # Crossing Bridge
            (Vec3(30.0, -20.0, 0), Vec3(30.0, 60.0, 0), COLOR_TUNIC_BLUE),
        ]
        for start_p, end_p, col in cit_routes:
            cit = Citizen3D(self.root, start_p, end_p, color=col)
            self.citizens.append(cit)

        # 6. Merchant Cart traversing through the Ishtar Gate
        cart = MerchantCart3D(self.root, path_start=Vec3(0, -90.0, 0.4), path_end=Vec3(0, 30.0, 0.4))
        self.carts.append(cart)

    def update(self, dt: float) -> None:
        for p in self.phalanxes:
            p.update(dt)
        for s in self.soldiers:
            s.update(dt)
        for f in self.farmers:
            f.update(dt)
        for c in self.citizens:
            c.update(dt)
        for cart in self.carts:
            cart.update(dt)

