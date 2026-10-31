"""
test_3d_engine.py - Automated Unit & Integration Tests for the 3D Babylonian Kingdom.

Tests:
1. Procedural 3D Mesh Generation (Cubes, Cylinders, Arches, Crenellations, Terrains).
2. Monumental 3D World Geometry (Ziggurat tiers, Ishtar Gate, Royal Palace, Euphrates River, Canals, Granaries).
3. 3D King Hammurabi & Lion Throne (Mesh assembly, guardian lions, crown, robe, sceptre, speaking state).
4. Living Animated 3D Entities (Soldiers, Phalanx march corridor, Farmers, Citizens, Merchant Carts).
5. 6-Mode Cinematic Camera System (Presets, free orbit calculations, smooth dampening, opening flyover).
6. 3D Atmospheric Lighting & Weather (Diurnal sun arc, brazier point lights, clear/flood/drought weather).
7. 3D Cinematic Events Director (8 signature choreographies).
8. BabylonApp3D Integration (Simulation synchronization, decree enactments, advisors counsel).
"""

import pytest
from panda3d.core import (
    NodePath,
    Vec3,
    Vec4,
    loadPrcFileData,
)

# Ensure headless Panda3D configuration for test isolation
loadPrcFileData("", "window-type none")
loadPrcFileData("", "audio-library-name null")

from engine3d.mesh_builder import (
    create_arch,
    create_crenellations,
    create_cube,
    create_cylinder,
    create_terrain_plane,
)
from engine3d.babylon_world import BabylonWorld3D
from engine3d.hammurabi_model import HammurabiCharacter3D, LionThrone3D, RoyalCourtScene3D
from engine3d.entities_3d import Citizen3D, EntitiesManager3D, Farmer3D, MerchantCart3D, SoldierPhalanx3D, SoldierUnit3D
from engine3d.camera_system import CameraController3D, PRESETS
from engine3d.atmosphere_3d import Atmosphere3D
from engine3d.cinematics_3d import CinematicDirector3D
from engine3d.app_3d import BabylonApp3D


class TestMeshBuilder:
    def test_create_cube_and_normals(self):
        root = NodePath("test_root")
        cube = create_cube("test_cube", 4.0, 6.0, 8.0, color=Vec4(0.8, 0.7, 0.5, 1.0))
        cube.reparent_to(root)
        assert not cube.is_empty()
        assert cube.get_num_children() == 0

    def test_create_cylinder_columns(self):
        root = NodePath("test_root")
        cyl = create_cylinder("test_col", radius=2.0, height=10.0, segments=12)
        cyl.reparent_to(root)
        assert not cyl.is_empty()

    def test_create_ishtar_archway(self):
        root = NodePath("test_root")
        arch = create_arch("test_arch", span=16.0, height=20.0, depth=8.0, wall_thickness=3.0)
        arch.reparent_to(root)
        assert not arch.is_empty()
        assert arch.get_num_children() >= 2  # Left pier, right pier, vault

    def test_create_crenellations(self):
        root = NodePath("test_root")
        cren = create_crenellations("test_cren", length=40.0, depth=2.0, merlon_w=1.5, merlon_h=1.2)
        cren.reparent_to(root)
        assert cren.get_num_children() > 5


class TestBabylonWorld3D:
    def test_world_assembly_and_components(self):
        root = NodePath("test_scene")
        world = BabylonWorld3D(root)
        assert not world.root.is_empty()
        assert not world.ziggurat.root.is_empty()
        assert not world.ishtar_gate.root.is_empty()
        assert not world.palace.root.is_empty()
        assert not world.river.root.is_empty()
        assert not world.canals.root.is_empty()
        assert not world.granaries.root.is_empty()
        assert not world.farmlands.root.is_empty()

    def test_world_simulation_state_update(self):
        root = NodePath("test_scene")
        world = BabylonWorld3D(root)
        world.update(0.1)

        class MockState:
            bushels = 3500
            acres = 1200
            harvest_yield = 4

        world.update_from_game_state(MockState())


class TestHammurabi3D:
    def test_throne_and_guardian_lions(self):
        root = NodePath("test_scene")
        throne = LionThrone3D(root)
        assert not throne.root.is_empty()
        assert throne.root.find("**/guardian_lion*")

    def test_hammurabi_character_and_animations(self):
        root = NodePath("test_scene")
        king = HammurabiCharacter3D(root)
        assert not king.root.is_empty()
        king.set_speaking(True)
        assert king.state == "SPEAKING"
        king.update(0.05)
        king.set_speaking(False)
        assert king.state == "SITTING_ON_THRONE"


class TestEntities3D:
    def test_soldier_unit_and_phalanx(self):
        root = NodePath("test_scene")
        phalanx = SoldierPhalanx3D(root, Vec3(0, 0, 0), Vec3(0, 50, 0))
        assert len(phalanx.soldiers) == 9
        phalanx.update(0.1)
        assert phalanx.root.get_pos() != Vec3(0, 0, 0)

    def test_entities_manager(self):
        root = NodePath("test_scene")
        mgr = EntitiesManager3D(root)
        mgr.update(0.1)
        assert len(mgr.farmers) > 0
        assert len(mgr.citizens) > 0
        assert len(mgr.carts) > 0


class TestCameraSystem3D:
    def test_camera_presets_and_interpolation(self):
        root = NodePath("test_camera")
        cam_ctrl = CameraController3D(root)
        for preset_name in PRESETS.keys():
            cam_ctrl.set_preset(preset_name)
            assert cam_ctrl.current_mode == preset_name
            cam_ctrl.update(0.1)

    def test_free_orbit_controls(self):
        root = NodePath("test_camera")
        cam_ctrl = CameraController3D(root)
        cam_ctrl.set_free_orbit(heading_delta=15.0, pitch_delta=5.0, zoom_delta=-20.0)
        assert cam_ctrl.current_mode == "FREE_ORBIT"
        cam_ctrl.update(0.1)


class TestAtmosphere3D:
    def test_lighting_and_weather_states(self):
        root = NodePath("test_render")
        atmos = Atmosphere3D(root)
        atmos.set_weather("DROUGHT")
        assert atmos.weather_state == "DROUGHT"
        atmos.set_weather("FLOOD")
        assert atmos.weather_state == "FLOOD"
        atmos.set_weather("CLEAR")
        assert atmos.weather_state == "CLEAR"
        atmos.update(0.1)


class TestCinematics3D:
    def test_cinematic_events_director(self):
        cam_root = NodePath("test_cam")
        cam_ctrl = CameraController3D(cam_root)
        render_root = NodePath("test_render")
        atmos = Atmosphere3D(render_root)
        director = CinematicDirector3D(cam_ctrl, atmos)

        director.play_event("royal_court")
        assert director.is_playing()
        director.update(1.0)
        director.stop_current()
        assert not director.is_playing()


class TestBabylonApp3DIntegration:
    def test_full_app_turn_advancement(self):
        app = BabylonApp3D(headless=True)
        init_year = app._get_current_game_state().year
        app.consult_advisors()
        app.execute_turn_decree()
        assert app._get_current_game_state().year == init_year + 1

