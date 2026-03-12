"""
Defines all shared data structures used across the pipeline.
All geometry uses metres as the base unit.
All angles in radians unless documented otherwise.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np


@dataclass
class Mesh:
    """Triangle mesh in 3D space."""
    vertices: np.ndarray        # (V, 3) float64 — xyz positions in metres
    faces: np.ndarray           # (F, 3) int32 — vertex indices per face
    normals: np.ndarray         # (F, 3) float64 — per-face unit normals
    vertex_colours: Optional[np.ndarray] = None  # (V, 3) uint8 — RGB per vertex

    @property
    def num_vertices(self) -> int:
        return len(self.vertices)

    @property
    def num_faces(self) -> int:
        return len(self.faces)

    def face_vertices(self, face_idx: int) -> np.ndarray:
        """Return (3, 3) array of vertex positions for a face."""
        return self.vertices[self.faces[face_idx]]

    def face_area(self, face_idx: int) -> float:
        """Area of a single face in m²."""
        verts = self.face_vertices(face_idx)
        edge1 = verts[1] - verts[0]
        edge2 = verts[2] - verts[0]
        return 0.5 * float(np.linalg.norm(np.cross(edge1, edge2)))

    def bounding_box(self) -> tuple[np.ndarray, np.ndarray]:
        """Return (min_corner, max_corner) each (3,)."""
        return self.vertices.min(axis=0), self.vertices.max(axis=0)


@dataclass
class PlanarPatch:
    """A group of coplanar mesh faces."""
    face_indices: list[int]        # indices into Mesh.faces
    plane_normal: np.ndarray       # (3,) unit normal
    plane_point: np.ndarray        # (3,) a point on the plane
    plane_d: float                 # signed distance: n·x + d = 0


@dataclass
class Face2D:
    """A single face projected into the unfolded 2D net."""
    original_face_idx: int
    vertices_2d: np.ndarray        # (3, 2) float64 — xy positions in metres
    is_root: bool = False


@dataclass
class GlueTab:
    """A trapezoidal glue tab along a cut edge."""
    edge_start_2d: np.ndarray      # (2,) float64
    edge_end_2d: np.ndarray        # (2,) float64
    tab_polygon_2d: np.ndarray     # (4, 2) float64 — trapezoid vertices
    tab_number: int                # assembly order label
    partner_face_idx: int          # the face this tab connects to


@dataclass
class UnfoldedNet:
    """Complete unfolded net ready for export."""
    faces: list[Face2D]
    fold_edges: list[tuple[np.ndarray, np.ndarray]]  # edges within spanning tree (dashed)
    cut_edges: list[tuple[np.ndarray, np.ndarray]]    # edges not in spanning tree (solid)
    tabs: list[GlueTab]
    scale_factor: float = 1.0      # metres per SVG unit
    overlap_count: int = 0         # number of face overlaps (0 = clean net)
    source_mesh: Optional[Mesh] = None


@dataclass
class CameraMetadata:
    """Camera intrinsics and capture metadata from iPhone."""
    fx: float
    fy: float
    cx: float
    cy: float
    width: int
    height: int
    unit: str = "metres"
