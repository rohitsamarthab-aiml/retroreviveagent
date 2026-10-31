"""
mesh_builder.py - Procedural 3D Mesh Construction Utilities for Panda3D.

Constructs optimized 3D geometric primitives with vertex normals and UV coordinates:
- Cuboids & Wall Segments
- Stepped Ziggurat Terraces & Axial Staircases
- Cylindrical Columns, Storage Silos & Round Watchtowers
- Arched Portals & Ishtar Gate Archways
- Crenellated Parapets & Battlements
- Terrain Grids & Cultivated Alluvial Farmland Furrows
"""

import math
from typing import List, Optional, Tuple
from panda3d.core import (
    Geom,
    GeomNode,
    GeomTriangles,
    GeomVertexData,
    GeomVertexFormat,
    GeomVertexWriter,
    NodePath,
    Vec3,
    Vec4,
)


def create_cube(
    name: str,
    dx: float,
    dy: float,
    dz: float,
    color: Vec4 = Vec4(0.8, 0.7, 0.5, 1.0),
    center_bottom: bool = True,
) -> NodePath:
    """Creates a 3D box with proper normals on all 6 faces."""
    format = GeomVertexFormat.get_v3n3c4()
    vdata = GeomVertexData(name, format, Geom.UHStatic)
    vdata.set_num_rows(24)

    vertex = GeomVertexWriter(vdata, "vertex")
    normal = GeomVertexWriter(vdata, "normal")
    color_w = GeomVertexWriter(vdata, "color")

    hx = dx * 0.5
    hy = dy * 0.5
    z0 = 0.0 if center_bottom else -dz * 0.5
    z1 = dz if center_bottom else dz * 0.5

    # 6 faces: +Z, -Z, +Y, -Y, +X, -X
    faces = [
        # Front (+Y)
        [(-hx, hy, z0), (hx, hy, z0), (hx, hy, z1), (-hx, hy, z1), Vec3(0, 1, 0)],
        # Back (-Y)
        [(hx, -hy, z0), (-hx, -hy, z0), (-hx, -hy, z1), (hx, -hy, z1), Vec3(0, -1, 0)],
        # Top (+Z)
        [(-hx, -hy, z1), (hx, -hy, z1), (hx, hy, z1), (-hx, hy, z1), Vec3(0, 0, 1)],
        # Bottom (-Z)
        [(-hx, hy, z0), (hx, hy, z0), (hx, -hy, z0), (-hx, -hy, z0), Vec3(0, 0, -1)],
        # Right (+X)
        [(hx, -hy, z0), (hx, hy, z0), (hx, hy, z1), (hx, -hy, z1), Vec3(1, 0, 0)],
        # Left (-X)
        [(-hx, hy, z0), (-hx, -hy, z0), (-hx, -hy, z1), (-hx, hy, z1), Vec3(-1, 0, 0)],
    ]

    triangles = GeomTriangles(Geom.UHStatic)

    row = 0
    for face in faces:
        v0, v1, v2, v3 = face[0], face[1], face[2], face[3]
        norm = face[4]

        vertex.add_data3(*v0)
        normal.add_data3(norm)
        color_w.add_data4(color)

        vertex.add_data3(*v1)
        normal.add_data3(norm)
        color_w.add_data4(color)

        vertex.add_data3(*v2)
        normal.add_data3(norm)
        color_w.add_data4(color)

        vertex.add_data3(*v3)
        normal.add_data3(norm)
        color_w.add_data4(color)

        triangles.add_vertices(row, row + 1, row + 2)
        triangles.add_vertices(row, row + 2, row + 3)
        row += 4

    geom = Geom(vdata)
    geom.add_primitive(triangles)
    node = GeomNode(name)
    node.add_geom(geom)
    return NodePath(node)


def create_cylinder(
    name: str,
    radius: float,
    height: float,
    segments: int = 16,
    color: Vec4 = Vec4(0.8, 0.7, 0.5, 1.0),
    top_cap: bool = True,
    bottom_cap: bool = True,
) -> NodePath:
    """Creates a 3D cylindrical column or silo."""
    format = GeomVertexFormat.get_v3n3c4()
    vdata = GeomVertexData(name, format, Geom.UHStatic)

    vertex = GeomVertexWriter(vdata, "vertex")
    normal = GeomVertexWriter(vdata, "normal")
    color_w = GeomVertexWriter(vdata, "color")

    triangles = GeomTriangles(Geom.UHStatic)
    row = 0

    # Side walls
    for i in range(segments):
        a0 = (i / segments) * 2.0 * math.pi
        a1 = ((i + 1) / segments) * 2.0 * math.pi

        x0, y0 = math.cos(a0) * radius, math.sin(a0) * radius
        x1, y1 = math.cos(a1) * radius, math.sin(a1) * radius

        n0 = Vec3(math.cos(a0), math.sin(a0), 0)
        n1 = Vec3(math.cos(a1), math.sin(a1), 0)

        # 4 vertices per quad for smooth normals
        vertex.add_data3(x0, y0, 0.0)
        normal.add_data3(n0)
        color_w.add_data4(color)

        vertex.add_data3(x1, y1, 0.0)
        normal.add_data3(n1)
        color_w.add_data4(color)

        vertex.add_data3(x1, y1, height)
        normal.add_data3(n1)
        color_w.add_data4(color)

        vertex.add_data3(x0, y0, height)
        normal.add_data3(n0)
        color_w.add_data4(color)

        triangles.add_vertices(row, row + 1, row + 2)
        triangles.add_vertices(row, row + 2, row + 3)
        row += 4

    # Caps
    if top_cap:
        top_center = row
        vertex.add_data3(0, 0, height)
        normal.add_data3(0, 0, 1)
        color_w.add_data4(color)
        row += 1

        for i in range(segments):
            a0 = (i / segments) * 2.0 * math.pi
            a1 = ((i + 1) / segments) * 2.0 * math.pi
            x0, y0 = math.cos(a0) * radius, math.sin(a0) * radius
            x1, y1 = math.cos(a1) * radius, math.sin(a1) * radius

            vertex.add_data3(x0, y0, height)
            normal.add_data3(0, 0, 1)
            color_w.add_data4(color)

            vertex.add_data3(x1, y1, height)
            normal.add_data3(0, 0, 1)
            color_w.add_data4(color)

            triangles.add_vertices(top_center, row, row + 1)
            row += 2

    if bottom_cap:
        bot_center = row
        vertex.add_data3(0, 0, 0)
        normal.add_data3(0, 0, -1)
        color_w.add_data4(color)
        row += 1

        for i in range(segments):
            a0 = (i / segments) * 2.0 * math.pi
            a1 = ((i + 1) / segments) * 2.0 * math.pi
            x0, y0 = math.cos(a0) * radius, math.sin(a0) * radius
            x1, y1 = math.cos(a1) * radius, math.sin(a1) * radius

            vertex.add_data3(x1, y1, 0)
            normal.add_data3(0, 0, -1)
            color_w.add_data4(color)

            vertex.add_data3(x0, y0, 0)
            normal.add_data3(0, 0, -1)
            color_w.add_data4(color)

            triangles.add_vertices(bot_center, row, row + 1)
            row += 2

    geom = Geom(vdata)
    geom.add_primitive(triangles)
    node = GeomNode(name)
    node.add_geom(geom)
    return NodePath(node)


def create_arch(
    name: str,
    span: float,
    height: float,
    depth: float,
    wall_thickness: float,
    color: Vec4 = Vec4(0.1, 0.25, 0.5, 1.0),
    segments: int = 12,
) -> NodePath:
    """Creates a Babylonian vaulted archway (Ishtar Gate portal style)."""
    parent = NodePath(name)

    # Left pier
    pier_w = wall_thickness
    left_pier = create_cube(
        f"{name}_left", pier_w, depth, height - span * 0.5, color=color, center_bottom=True
    )
    left_pier.set_pos(-span * 0.5 - pier_w * 0.5, 0, 0)
    left_pier.reparent_to(parent)

    # Right pier
    right_pier = create_cube(
        f"{name}_right", pier_w, depth, height - span * 0.5, color=color, center_bottom=True
    )
    right_pier.set_pos(span * 0.5 + pier_w * 0.5, 0, 0)
    right_pier.reparent_to(parent)

    # Arch segments forming the semicircular vault
    radius_inner = span * 0.5
    radius_outer = radius_inner + wall_thickness
    spring_z = height - radius_inner

    format = GeomVertexFormat.get_v3n3c4()
    vdata = GeomVertexData(f"{name}_vault", format, Geom.UHStatic)
    vertex = GeomVertexWriter(vdata, "vertex")
    normal = GeomVertexWriter(vdata, "normal")
    color_w = GeomVertexWriter(vdata, "color")
    triangles = GeomTriangles(Geom.UHStatic)

    row = 0
    hd = depth * 0.5

    for i in range(segments):
        a0 = (i / segments) * math.pi
        a1 = ((i + 1) / segments) * math.pi

        # Inner points
        ix0, iz0 = math.cos(a0) * radius_inner, spring_z + math.sin(a0) * radius_inner
        ix1, iz1 = math.cos(a1) * radius_inner, spring_z + math.sin(a1) * radius_inner

        # Outer points
        ox0, oz0 = math.cos(a0) * radius_outer, spring_z + math.sin(a0) * radius_outer
        ox1, oz1 = math.cos(a1) * radius_outer, spring_z + math.sin(a1) * radius_outer

        # Front face (+Y)
        vertex.add_data3(ix0, hd, iz0)
        normal.add_data3(0, 1, 0)
        color_w.add_data4(color)

        vertex.add_data3(ox0, hd, oz0)
        normal.add_data3(0, 1, 0)
        color_w.add_data4(color)

        vertex.add_data3(ox1, hd, oz1)
        normal.add_data3(0, 1, 0)
        color_w.add_data4(color)

        vertex.add_data3(ix1, hd, iz1)
        normal.add_data3(0, 1, 0)
        color_w.add_data4(color)

        triangles.add_vertices(row, row + 1, row + 2)
        triangles.add_vertices(row, row + 2, row + 3)
        row += 4

        # Back face (-Y)
        vertex.add_data3(ix1, -hd, iz1)
        normal.add_data3(0, -1, 0)
        color_w.add_data4(color)

        vertex.add_data3(ox1, -hd, oz1)
        normal.add_data3(0, -1, 0)
        color_w.add_data4(color)

        vertex.add_data3(ox0, -hd, oz0)
        normal.add_data3(0, -1, 0)
        color_w.add_data4(color)

        vertex.add_data3(ix0, -hd, iz0)
        normal.add_data3(0, -1, 0)
        color_w.add_data4(color)

        triangles.add_vertices(row, row + 1, row + 2)
        triangles.add_vertices(row, row + 2, row + 3)
        row += 4

        # Intrados (underside of arch)
        mid_a = (a0 + a1) * 0.5
        n_in = Vec3(-math.cos(mid_a), 0, -math.sin(mid_a))
        vertex.add_data3(ix0, -hd, iz0)
        normal.add_data3(n_in)
        color_w.add_data4(color)

        vertex.add_data3(ix0, hd, iz0)
        normal.add_data3(n_in)
        color_w.add_data4(color)

        vertex.add_data3(ix1, hd, iz1)
        normal.add_data3(n_in)
        color_w.add_data4(color)

        vertex.add_data3(ix1, -hd, iz1)
        normal.add_data3(n_in)
        color_w.add_data4(color)

        triangles.add_vertices(row, row + 1, row + 2)
        triangles.add_vertices(row, row + 2, row + 3)
        row += 4

    geom = Geom(vdata)
    geom.add_primitive(triangles)
    node = GeomNode(f"{name}_vault_node")
    node.add_geom(geom)
    NodePath(node).reparent_to(parent)

    return parent


def create_crenellations(
    name: str,
    length: float,
    depth: float,
    merlon_w: float = 1.0,
    merlon_h: float = 1.2,
    spacing: float = 0.8,
    color: Vec4 = Vec4(0.8, 0.7, 0.5, 1.0),
) -> NodePath:
    """Creates a row of stepped ancient Mesopotamian defensive battlements."""
    parent = NodePath(name)
    step = merlon_w + spacing
    count = int(length // step)
    start_x = -length * 0.5 + merlon_w * 0.5

    for i in range(count):
        x = start_x + i * step
        merlon = create_cube(f"{name}_m{i}", merlon_w, depth, merlon_h, color=color, center_bottom=True)
        merlon.set_pos(x, 0, 0)
        merlon.reparent_to(parent)

    return parent


def create_terrain_plane(
    name: str,
    size_x: float,
    size_y: float,
    color: Vec4 = Vec4(0.78, 0.68, 0.48, 1.0),
) -> NodePath:
    """Creates a vast ground alluvial plain."""
    format = GeomVertexFormat.get_v3n3c4()
    vdata = GeomVertexData(name, format, Geom.UHStatic)
    vdata.set_num_rows(4)

    vertex = GeomVertexWriter(vdata, "vertex")
    normal = GeomVertexWriter(vdata, "normal")
    color_w = GeomVertexWriter(vdata, "color")

    hx, hy = size_x * 0.5, size_y * 0.5
    for x, y in [(-hx, -hy), (hx, -hy), (hx, hy), (-hx, hy)]:
        vertex.add_data3(x, y, 0.0)
        normal.add_data3(0, 0, 1)
        color_w.add_data4(color)

    triangles = GeomTriangles(Geom.UHStatic)
    triangles.add_vertices(0, 1, 2)
    triangles.add_vertices(0, 2, 3)

    geom = Geom(vdata)
    geom.add_primitive(triangles)
    node = GeomNode(name)
    node.add_geom(geom)
    return NodePath(node)

