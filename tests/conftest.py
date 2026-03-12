"""
Shared pytest fixtures for the SurfaceNet test suite.

Provides pre-built Mesh objects matching the geometry of the fixture files
in tests/fixtures/. Fixture files (OBJ/PLY) are used by test_ingest.py;
these fixtures are used by all other test modules that need Mesh inputs.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from surfacenet.types import Mesh

FIXTURES_DIR = Path(__file__).parent / "fixtures"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _normals(vertices: np.ndarray, faces: np.ndarray) -> np.ndarray:
    """Compute per-face unit normals via cross product."""
    v0 = vertices[faces[:, 0]]
    v1 = vertices[faces[:, 1]]
    v2 = vertices[faces[:, 2]]
    cross = np.cross(v1 - v0, v2 - v0)
    lengths = np.linalg.norm(cross, axis=1, keepdims=True)
    return cross / lengths


# ---------------------------------------------------------------------------
# Path fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def fixtures_dir() -> Path:
    """Path to tests/fixtures/."""
    return FIXTURES_DIR


@pytest.fixture(scope="session")
def cube_obj_path(fixtures_dir) -> Path:
    return fixtures_dir / "cube.obj"


@pytest.fixture(scope="session")
def cube_ply_path(fixtures_dir) -> Path:
    return fixtures_dir / "cube.ply"


@pytest.fixture(scope="session")
def tetrahedron_obj_path(fixtures_dir) -> Path:
    return fixtures_dir / "tetrahedron.obj"


@pytest.fixture(scope="session")
def l_shape_obj_path(fixtures_dir) -> Path:
    return fixtures_dir / "l_shape.obj"


@pytest.fixture(scope="session")
def metadata_json_path(fixtures_dir) -> Path:
    return fixtures_dir / "metadata_sample.json"


# ---------------------------------------------------------------------------
# Mesh fixtures — geometry matches the OBJ/PLY files exactly
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def cube_mesh() -> Mesh:
    """
    Unit cube centred at origin [-0.5, 0.5]^3.
    8 vertices, 12 triangular faces.
    Matches tests/fixtures/cube.obj and cube.ply.
    """
    vertices = np.array([
        [-0.5, -0.5, -0.5],  # 0
        [ 0.5, -0.5, -0.5],  # 1
        [ 0.5,  0.5, -0.5],  # 2
        [-0.5,  0.5, -0.5],  # 3
        [-0.5, -0.5,  0.5],  # 4
        [ 0.5, -0.5,  0.5],  # 5
        [ 0.5,  0.5,  0.5],  # 6
        [-0.5,  0.5,  0.5],  # 7
    ], dtype=np.float64)

    faces = np.array([
        [0, 2, 1], [0, 3, 2],  # bottom  (z = -0.5), normal -z
        [4, 5, 6], [4, 6, 7],  # top     (z = +0.5), normal +z
        [0, 1, 5], [0, 5, 4],  # front   (y = -0.5), normal -y
        [3, 7, 6], [3, 6, 2],  # back    (y = +0.5), normal +y
        [0, 4, 7], [0, 7, 3],  # left    (x = -0.5), normal -x
        [1, 2, 6], [1, 6, 5],  # right   (x = +0.5), normal +x
    ], dtype=np.int32)

    return Mesh(vertices=vertices, faces=faces, normals=_normals(vertices, faces))


@pytest.fixture(scope="session")
def tetrahedron_mesh() -> Mesh:
    """
    Regular tetrahedron with edge length 1 m.
    4 vertices, 4 triangular faces.
    Matches tests/fixtures/tetrahedron.obj.
    """
    s3 = 0.8660254037844387   # sqrt(3)/2
    s36 = 0.28867513459481287 # sqrt(3)/6
    h = 0.816496580927726     # sqrt(2/3)

    vertices = np.array([
        [0.0, 0.0, 0.0],
        [1.0, 0.0, 0.0],
        [0.5, s3,  0.0],
        [0.5, s36, h  ],
    ], dtype=np.float64)

    faces = np.array([
        [0, 2, 1],  # bottom (z=0),        normal -z
        [0, 1, 3],  # front  (low-y face),  normal roughly -y
        [1, 2, 3],  # back-right,           normal roughly +x+y
        [0, 3, 2],  # left,                 normal roughly -x+y
    ], dtype=np.int32)

    return Mesh(vertices=vertices, faces=faces, normals=_normals(vertices, faces))


@pytest.fixture(scope="session")
def l_shape_mesh() -> Mesh:
    """
    L-shaped prism: 2x2x1 footprint with 1x1x1 notch cut from upper-right.
    Cross-section in xz-plane: (0,0)-(2,0)-(2,1)-(1,1)-(1,2)-(0,2).
    Extruded from y=0 to y=1.
    12 vertices, 20 triangular faces.
    Matches tests/fixtures/l_shape.obj.
    """
    vertices = np.array([
        [0, 0, 0],  # 0   front-bottom-left
        [2, 0, 0],  # 1   front-bottom-right
        [2, 0, 1],  # 2   front-step-right
        [1, 0, 1],  # 3   front-step-inner
        [1, 0, 2],  # 4   front-top-inner
        [0, 0, 2],  # 5   front-top-left
        [0, 1, 0],  # 6   back-bottom-left
        [2, 1, 0],  # 7   back-bottom-right
        [2, 1, 1],  # 8   back-step-right
        [1, 1, 1],  # 9   back-step-inner
        [1, 1, 2],  # 10  back-top-inner
        [0, 1, 2],  # 11  back-top-left
    ], dtype=np.float64)

    faces = np.array([
        # front (y=0), fan from vertex 0
        [0, 1, 2], [0, 2, 3], [0, 3, 4], [0, 4, 5],
        # back (y=1), fan from vertex 6 (reversed for +y normal)
        [6, 11, 10], [6, 10, 9], [6, 9, 8], [6, 8, 7],
        # bottom (z=0)
        [0, 6, 7], [0, 7, 1],
        # right (x=2)
        [1, 7, 8], [1, 8, 2],
        # inner horizontal step (z=1, x=1..2)
        [2, 8, 9], [2, 9, 3],
        # inner vertical step (x=1, z=1..2)
        [3, 9, 10], [3, 10, 4],
        # top (z=2)
        [4, 10, 11], [4, 11, 5],
        # left (x=0)
        [5, 11, 6], [5, 6, 0],
    ], dtype=np.int32)

    return Mesh(vertices=vertices, faces=faces, normals=_normals(vertices, faces))
