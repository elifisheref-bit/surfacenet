import numpy as np
import pytest

from surfacenet.types import (
    CameraMetadata,
    Face2D,
    GlueTab,
    Mesh,
    PlanarPatch,
    UnfoldedNet,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_unit_cube_mesh() -> Mesh:
    """Unit cube [0,1]^3: 8 vertices, 12 triangular faces."""
    vertices = np.array([
        [0, 0, 0],  # 0
        [1, 0, 0],  # 1
        [1, 1, 0],  # 2
        [0, 1, 0],  # 3
        [0, 0, 1],  # 4
        [1, 0, 1],  # 5
        [1, 1, 1],  # 6
        [0, 1, 1],  # 7
    ], dtype=np.float64)

    faces = np.array([
        [0, 1, 2], [0, 2, 3],  # bottom (z=0)
        [4, 6, 5], [4, 7, 6],  # top    (z=1)
        [0, 5, 1], [0, 4, 5],  # front  (y=0)
        [2, 3, 7], [2, 7, 6],  # back   (y=1)
        [0, 3, 7], [0, 7, 4],  # left   (x=0)
        [1, 5, 6], [1, 6, 2],  # right  (x=1)
    ], dtype=np.int32)

    v0 = vertices[faces[:, 0]]
    v1 = vertices[faces[:, 1]]
    v2 = vertices[faces[:, 2]]
    cross = np.cross(v1 - v0, v2 - v0)
    lengths = np.linalg.norm(cross, axis=1, keepdims=True)
    normals = cross / lengths

    return Mesh(vertices=vertices, faces=faces, normals=normals)


@pytest.fixture
def cube_mesh() -> Mesh:
    return _make_unit_cube_mesh()


# ---------------------------------------------------------------------------
# Mesh tests
# ---------------------------------------------------------------------------

class TestMesh:
    def test_num_vertices(self, cube_mesh):
        assert cube_mesh.num_vertices == 8

    def test_num_faces(self, cube_mesh):
        assert cube_mesh.num_faces == 12

    def test_face_vertices_shape(self, cube_mesh):
        for i in range(cube_mesh.num_faces):
            assert cube_mesh.face_vertices(i).shape == (3, 3)

    def test_face_vertices_values(self, cube_mesh):
        # face 0 = [0,1,2] → (0,0,0), (1,0,0), (1,1,0)
        verts = cube_mesh.face_vertices(0)
        np.testing.assert_array_equal(verts[0], [0, 0, 0])
        np.testing.assert_array_equal(verts[1], [1, 0, 0])
        np.testing.assert_array_equal(verts[2], [1, 1, 0])

    def test_face_area_each(self, cube_mesh):
        # every triangle is half a unit square → area 0.5 m²
        for i in range(cube_mesh.num_faces):
            area = cube_mesh.face_area(i)
            assert abs(area - 0.5) < 1e-10, f"face {i}: area={area}"

    def test_total_surface_area(self, cube_mesh):
        # 6 faces × 1 m² per face = 6 m² total
        total = sum(cube_mesh.face_area(i) for i in range(cube_mesh.num_faces))
        assert abs(total - 6.0) < 1e-10

    def test_bounding_box_values(self, cube_mesh):
        lo, hi = cube_mesh.bounding_box()
        np.testing.assert_array_almost_equal(lo, [0, 0, 0])
        np.testing.assert_array_almost_equal(hi, [1, 1, 1])

    def test_bounding_box_shapes(self, cube_mesh):
        lo, hi = cube_mesh.bounding_box()
        assert lo.shape == (3,)
        assert hi.shape == (3,)

    def test_normals_are_unit_length(self, cube_mesh):
        lengths = np.linalg.norm(cube_mesh.normals, axis=1)
        np.testing.assert_allclose(lengths, 1.0, atol=1e-10)

    def test_vertex_colours_default_none(self, cube_mesh):
        assert cube_mesh.vertex_colours is None

    def test_vertex_colours_optional(self, cube_mesh):
        colours = np.zeros((8, 3), dtype=np.uint8)
        mesh = Mesh(
            vertices=cube_mesh.vertices,
            faces=cube_mesh.faces,
            normals=cube_mesh.normals,
            vertex_colours=colours,
        )
        assert mesh.vertex_colours is not None
        assert mesh.vertex_colours.shape == (8, 3)


# ---------------------------------------------------------------------------
# PlanarPatch tests
# ---------------------------------------------------------------------------

class TestPlanarPatch:
    def test_construction(self):
        patch = PlanarPatch(
            face_indices=[0, 1],
            plane_normal=np.array([0.0, 0.0, 1.0]),
            plane_point=np.array([0.0, 0.0, 0.0]),
            plane_d=0.0,
        )
        assert patch.face_indices == [0, 1]
        assert patch.plane_d == 0.0
        assert patch.plane_normal.shape == (3,)


# ---------------------------------------------------------------------------
# Face2D tests
# ---------------------------------------------------------------------------

class TestFace2D:
    def test_construction_defaults(self):
        verts = np.array([[0.0, 0.0], [1.0, 0.0], [0.5, 1.0]])
        face = Face2D(original_face_idx=3, vertices_2d=verts)
        assert face.original_face_idx == 3
        assert face.vertices_2d.shape == (3, 2)
        assert face.is_root is False

    def test_is_root_flag(self):
        face = Face2D(original_face_idx=0, vertices_2d=np.zeros((3, 2)), is_root=True)
        assert face.is_root is True


# ---------------------------------------------------------------------------
# GlueTab tests
# ---------------------------------------------------------------------------

class TestGlueTab:
    def test_construction(self):
        tab = GlueTab(
            edge_start_2d=np.array([0.0, 0.0]),
            edge_end_2d=np.array([1.0, 0.0]),
            tab_polygon_2d=np.zeros((4, 2)),
            tab_number=1,
            partner_face_idx=5,
        )
        assert tab.tab_number == 1
        assert tab.partner_face_idx == 5
        assert tab.tab_polygon_2d.shape == (4, 2)
        assert tab.edge_start_2d.shape == (2,)
        assert tab.edge_end_2d.shape == (2,)


# ---------------------------------------------------------------------------
# UnfoldedNet tests
# ---------------------------------------------------------------------------

class TestUnfoldedNet:
    def test_defaults(self):
        net = UnfoldedNet(faces=[], fold_edges=[], cut_edges=[], tabs=[])
        assert net.scale_factor == 1.0
        assert net.overlap_count == 0
        assert net.source_mesh is None

    def test_with_source_mesh(self, cube_mesh):
        net = UnfoldedNet(
            faces=[], fold_edges=[], cut_edges=[], tabs=[],
            source_mesh=cube_mesh,
        )
        assert net.source_mesh is cube_mesh


# ---------------------------------------------------------------------------
# CameraMetadata tests
# ---------------------------------------------------------------------------

class TestCameraMetadata:
    def test_construction(self):
        cam = CameraMetadata(
            fx=1598.0, fy=1598.0, cx=960.0, cy=540.0,
            width=1920, height=1080,
        )
        assert cam.fx == 1598.0
        assert cam.fy == 1598.0
        assert cam.cx == 960.0
        assert cam.cy == 540.0
        assert cam.width == 1920
        assert cam.height == 1080
        assert cam.unit == "metres"

    def test_custom_unit(self):
        cam = CameraMetadata(
            fx=800.0, fy=800.0, cx=320.0, cy=240.0,
            width=640, height=480, unit="mm",
        )
        assert cam.unit == "mm"
