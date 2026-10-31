"""
hammurabi_model.py - 3D Character Model of King Hammurabi & The Lion Throne.

Implements the royal Mesopotamian monarch matching historical iconography
and user reference images:
- Royal Lion Throne flanked by two carved stone guardian lions with jewel inlays
- Conical Tiara of Kingship adorned with the Golden Horns of Divinity and solar crest
- Braided Mesopotamian square beard bound with tiered golden ring clasps
- Tyrian purple royal mantle with diagonal golden sash and lapis pectoral medallion
- Golden Sceptre bearing the sacred Rod and Ring of Justice
- Procedural animation states: SITTING_ON_THRONE, SPEAKING_DECREE, IDLE_BREATHING, STANDING_AUDIENCE
"""

import math
from typing import Optional
from panda3d.core import (
    NodePath,
    Vec3,
    Vec4,
)

from engine3d.mesh_builder import (
    create_cube,
    create_cylinder,
)


COLOR_PURPLE_ROYAL = Vec4(0.32, 0.12, 0.42, 1.0)
COLOR_GOLD = Vec4(0.92, 0.78, 0.25, 1.0)
COLOR_GOLD_LIGHT = Vec4(1.0, 0.88, 0.45, 1.0)
COLOR_SKIN = Vec4(0.85, 0.68, 0.52, 1.0)
COLOR_BEARD = Vec4(0.12, 0.08, 0.06, 1.0)
COLOR_LAPIS = Vec4(0.08, 0.22, 0.55, 1.0)
COLOR_STONE_LION = Vec4(0.78, 0.68, 0.50, 1.0)


class LionThrone3D:
    """The Royal Babylonian Throne flanked by carved stone guardian lions."""

    def __init__(self, parent: NodePath) -> None:
        self.root = NodePath("lion_throne")
        self.root.reparent_to(parent)

        # 3-stepped royal dais
        dais_w, dais_d = 12.0, 10.0
        for i in range(3):
            step = create_cube(
                f"dais_step_{i}",
                dais_w - i * 1.5,
                dais_d - i * 1.5,
                0.8,
                color=COLOR_LAPIS,
                center_bottom=True,
            )
            step.set_pos(0, 0, i * 0.8)
            step.reparent_to(self.root)

            gold_trim = create_cube(
                f"dais_trim_{i}",
                dais_w - i * 1.5 + 0.2,
                dais_d - i * 1.5 + 0.2,
                0.1,
                color=COLOR_GOLD,
                center_bottom=True,
            )
            gold_trim.set_pos(0, 0, (i + 1) * 0.8)
            gold_trim.reparent_to(self.root)

        base_z = 2.4

        # Massive Throne Seat
        seat = create_cube("throne_seat", 5.0, 4.0, 2.0, color=COLOR_GOLD, center_bottom=True)
        seat.set_pos(0, 0, base_z)
        seat.reparent_to(self.root)

        # Cushioned velvet purple pad
        cushion = create_cube("throne_cushion", 4.4, 3.6, 0.6, color=COLOR_PURPLE_ROYAL, center_bottom=True)
        cushion.set_pos(0, 0, base_z + 2.0)
        cushion.reparent_to(self.root)

        # High Backrest with solar winged disc
        backrest = create_cube("throne_backrest", 5.0, 1.0, 8.5, color=COLOR_GOLD, center_bottom=True)
        backrest.set_pos(0, 1.6, base_z + 2.0)
        backrest.reparent_to(self.root)

        # Lapis lazuli mosaic inset in backrest
        mosaic = create_cube("throne_mosaic", 4.0, 0.4, 7.0, color=COLOR_LAPIS, center_bottom=True)
        mosaic.set_pos(0, 1.0, base_z + 3.0)
        mosaic.reparent_to(self.root)

        # Golden Winged Sun Crest
        crest = create_cylinder("throne_crest", radius=1.8, height=0.6, segments=16, color=COLOR_GOLD_LIGHT)
        crest.set_p(90)
        crest.set_pos(0, 1.6, base_z + 10.8)
        crest.reparent_to(self.root)

        # Flanking Carved Stone Guardian Lions (Matching user's Image 2)
        for lx in [-3.8, 3.8]:
            lion = NodePath(f"guardian_lion_{lx}")
            lion.set_pos(lx, -0.5, base_z)
            lion.reparent_to(self.root)

            # Body
            l_body = create_cube("l_body", 1.8, 3.4, 2.8, color=COLOR_STONE_LION, center_bottom=True)
            l_body.set_pos(0, 0, 0)
            l_body.reparent_to(lion)

            # Head
            l_head = create_cube("l_head", 1.6, 1.8, 1.8, color=COLOR_STONE_LION, center_bottom=True)
            l_head.set_pos(0, -1.2, 2.4)
            l_head.reparent_to(lion)

            # Mane
            l_mane = create_cube("l_mane", 2.0, 1.4, 2.2, color=COLOR_GOLD, center_bottom=True)
            l_mane.set_pos(0, -0.4, 2.0)
            l_mane.reparent_to(lion)


class HammurabiCharacter3D:
    """3D Model of King Hammurabi with regal accessories and animation."""

    def __init__(self, parent: NodePath, pos: Vec3 = Vec3(0, 0, 4.8)) -> None:
        self.root = NodePath("king_hammurabi_3d")
        self.root.reparent_to(parent)
        self.root.set_pos(pos)

        self.time = 0.0
        self.state = "SITTING_ON_THRONE"  # SITTING_ON_THRONE, SPEAKING, AUDIENCE

        # Hierarchical node structure for animation
        self.hips = NodePath("hips")
        self.hips.reparent_to(self.root)

        self.spine = NodePath("spine")
        self.spine.set_pos(0, 0, 1.8)
        self.spine.reparent_to(self.hips)

        self.head = NodePath("head")
        self.head.set_pos(0, 0, 3.4)
        self.head.reparent_to(self.spine)

        self.arm_r = NodePath("arm_right")
        self.arm_r.set_pos(1.8, 0, 2.8)
        self.arm_r.reparent_to(self.spine)

        self.arm_l = NodePath("arm_left")
        self.arm_l.set_pos(-1.8, 0, 2.8)
        self.arm_l.reparent_to(self.spine)

        self._build_mesh()

    def _build_mesh(self) -> None:
        # 1. Robed Torso & Tyrian Purple Mantle
        torso = create_cube("torso", 3.0, 2.0, 3.2, color=COLOR_PURPLE_ROYAL, center_bottom=True)
        torso.set_pos(0, 0, 0)
        torso.reparent_to(self.spine)

        # Diagonal Golden Sash
        sash = create_cube("sash", 1.2, 2.1, 3.3, color=COLOR_GOLD, center_bottom=True)
        sash.set_pos(0.2, 0, 0)
        sash.set_r(22)
        sash.reparent_to(self.spine)

        # Lapis Lazuli Pectoral Medallion
        medallion = create_cylinder("medallion", radius=0.6, height=0.3, segments=12, color=COLOR_GOLD)
        medallion.set_p(90)
        medallion.set_pos(0, -1.05, 2.2)
        medallion.reparent_to(self.spine)

        gem = create_cylinder("med_gem", radius=0.35, height=0.35, segments=12, color=COLOR_LAPIS)
        gem.set_p(90)
        gem.set_pos(0, -1.1, 2.2)
        gem.reparent_to(self.spine)

        # Robed Sitting Lap & Skirt
        lap = create_cube("lap", 2.8, 3.0, 1.8, color=COLOR_PURPLE_ROYAL, center_bottom=True)
        lap.set_pos(0, -0.6, -1.6)
        lap.reparent_to(self.hips)

        # 2. Regal Head & Facial Features
        head_cube = create_cube("head_base", 1.4, 1.4, 1.6, color=COLOR_SKIN, center_bottom=True)
        head_cube.set_pos(0, 0, 0)
        head_cube.reparent_to(self.head)

        # Aquiline nose
        nose = create_cube("nose", 0.3, 0.4, 0.7, color=COLOR_SKIN, center_bottom=True)
        nose.set_pos(0, -0.8, 0.4)
        nose.reparent_to(self.head)

        # Traditional Square Braided Mesopotamian Beard with Gold Rings
        beard = create_cube("square_beard", 1.2, 0.8, 2.2, color=COLOR_BEARD, center_bottom=True)
        beard.set_pos(0, -0.6, -1.8)
        beard.reparent_to(self.head)

        # Golden beard rings
        for ring_z in [-0.6, -1.2]:
            ring = create_cube(f"beard_ring_{ring_z}", 1.3, 0.9, 0.25, color=COLOR_GOLD, center_bottom=True)
            ring.set_pos(0, -0.6, ring_z)
            ring.reparent_to(self.head)

        # Mustache
        mustache = create_cube("mustache", 1.0, 0.3, 0.3, color=COLOR_BEARD, center_bottom=True)
        mustache.set_pos(0, -0.8, 0.25)
        mustache.reparent_to(self.head)

        # 3. Conical Crown / Tiara of Supreme Rule with Bull Horns
        tiara = create_cylinder("tiara", radius=0.9, height=2.2, segments=16, color=COLOR_GOLD)
        tiara.set_pos(0, 0, 1.4)
        tiara.reparent_to(self.head)

        # Golden Horns of Divinity (Symbol of Ancient Divine Kingship)
        horn_l = create_cube("horn_l", 0.3, 0.3, 1.2, color=COLOR_GOLD_LIGHT, center_bottom=True)
        horn_l.set_pos(-0.9, -0.2, 2.0)
        horn_l.set_r(40)
        horn_l.reparent_to(self.head)

        horn_r = create_cube("horn_r", 0.3, 0.3, 1.2, color=COLOR_GOLD_LIGHT, center_bottom=True)
        horn_r.set_pos(0.9, -0.2, 2.0)
        horn_r.set_r(-40)
        horn_r.reparent_to(self.head)

        # Sunburst Finial at crown apex
        finial = create_cylinder("finial", radius=0.3, height=0.5, segments=8, color=COLOR_GOLD_LIGHT)
        finial.set_pos(0, 0, 3.6)
        finial.reparent_to(self.head)

        # 4. Arms & Royal Sceptre (The Sacred Rod & Ring of Justice)
        # Right Arm (holding upright sceptre)
        arm_r_mesh = create_cube("arm_r_mesh", 0.7, 0.7, 2.4, color=COLOR_PURPLE_ROYAL, center_bottom=True)
        arm_r_mesh.set_pos(0, 0, -2.2)
        arm_r_mesh.reparent_to(self.arm_r)

        # Sceptre staff
        sceptre_staff = create_cylinder("sceptre_staff", radius=0.12, height=5.5, segments=8, color=COLOR_GOLD)
        sceptre_staff.set_pos(0.2, -0.6, -1.0)
        sceptre_staff.reparent_to(self.arm_r)

        # Ring of Justice at top of sceptre
        ring_core = create_cylinder("justice_ring", radius=0.5, height=0.15, segments=12, color=COLOR_GOLD_LIGHT)
        ring_core.set_p(90)
        ring_core.set_pos(0.2, -0.6, 4.4)
        ring_core.reparent_to(self.arm_r)

        # Left Arm (resting regally on throne armrest)
        arm_l_mesh = create_cube("arm_l_mesh", 0.7, 0.7, 2.4, color=COLOR_PURPLE_ROYAL, center_bottom=True)
        arm_l_mesh.set_pos(0, 0, -2.2)
        arm_l_mesh.reparent_to(self.arm_l)

    def update(self, dt: float) -> None:
        """Procedural breathing, head sway, and speaking gestures."""
        self.time += dt

        # Idle breathing
        breath = math.sin(self.time * 2.2) * 1.5
        self.spine.set_p(breath)

        # Head looking slightly left/right slowly
        head_pan = math.sin(self.time * 0.8) * 4.0
        self.head.set_h(head_pan)

        # Sceptre subtle hand elevation
        if self.state == "SPEAKING":
            gesture = math.sin(self.time * 4.5) * 6.0
            self.arm_r.set_p(-15.0 + gesture)
        else:
            self.arm_r.set_p(-5.0 + breath * 0.5)

    def set_speaking(self, is_speaking: bool) -> None:
        self.state = "SPEAKING" if is_speaking else "SITTING_ON_THRONE"


class RoyalCourtScene3D:
    """Combines Lion Throne and King Hammurabi inside the Royal Palace Throne Room."""

    def __init__(self, parent: NodePath, pos: Vec3 = Vec3(75.0, 75.0, 0)) -> None:
        self.root = NodePath("royal_court_scene")
        self.root.reparent_to(parent)
        self.root.set_pos(pos)

        self.throne = LionThrone3D(self.root)
        self.king = HammurabiCharacter3D(self.root, pos=Vec3(0, 0, 4.8))

    def update(self, dt: float) -> None:
        self.king.update(dt)

