# SurfaceNet — Architecture & Implementation Plan

*Last updated: 12 March 2026*
*Direction: A — Fabrication Tool (confirmed)*
*Implementation target: Claude Code with Sonnet 4.6*

---

## 1. What Is SurfaceNet?

SurfaceNet is a tool that takes a 3D scan from an iPhone's LiDAR sensor and produces a flat, printable net — a 2D pattern you can cut out and fold into a physical replica, or export as an STL for 3D printing.

The core workflow: **Scan → Reconstruct → Rectify → Unfold → Fabricate.**

Nothing on the market does this end-to-end on mobile. Desktop tools like Pepakura Designer handle the unfolding step, but they expect a clean mesh as input and have no connection to phone-based scanning. Phone scanning apps (Polycam, Scaniverse) export meshes and point clouds but stop there. SurfaceNet bridges the gap.


## 2. What's Genuinely Novel

| Claim | Status |
|-------|--------|
| No mobile app unfolds meshes into nets | **Confirmed.** Pepakura, PolyZamboni, Unfolder are all desktop/Mac. |
| No app connects LiDAR capture directly to fabrication output | **Confirmed.** Existing apps export .ply/.obj and leave it there. |
| Planar homography rectification on per-face patches | **Novel in this context.** Existing scanners don't rectify individual faces for texture-accurate unfolding. |
| Phone-based maritime/naval 3D scanning | **Untapped.** All documented naval scanning uses €50k+ terrestrial laser scanners. |
| Combined paper net + STL export from a single scan | **Not available anywhere on mobile.** |

What's *not* novel: the individual algorithms (RANSAC, homography, spanning-tree unfolding) are well-established. The novelty is in the integration and the mobile-first pipeline.


## 3. Decided Direction: SurfaceNet (Fabrication Tool)

- **User:** Maker, prototyper, naval engineer, hobbyist
- **Input:** LiDAR scan of a physical object
- **Output:** Printable net (SVG/PDF) or STL
- **Value proposition:** "Scan anything, build a replica"
- **Navy/OR angle:** Rapid prototyping, hull template generation, damage documentation

MarineRange (Direction B) is deferred. The homography code developed here transfers directly when that module is built later.


## 4. Dual-Mode Architecture

### 4.1 Design Principle

The app is architected around a **standard mesh interchange format** (.ply / .obj). The iPhone always captures and exports a mesh. Processing can happen either on-device or on a PC. Both paths consume the same data and produce the same output formats.

### 4.2 System Diagram

```
┌──────────────────────────────────────────────────────────────┐
│                    iPhone (always runs)                        │
│                                                                │
│  ARKit LiDAR + Scene Geometry API                             │
│  → Reconstructed triangle mesh (on-device, real-time)         │
│  → RGB camera frames + camera intrinsics                      │
│                                                                │
│  ┌─────────────────────┐    ┌──────────────────────────────┐  │
│  │  EXPORT PATH         │    │  ON-DEVICE PATH              │  │
│  │                      │    │                               │  │
│  │  Mesh → .ply / .obj  │    │  Mesh simplification          │  │
│  │  RGB → .jpg          │    │  RANSAC segmentation           │  │
│  │  Metadata → .json    │    │  Homography rectification      │  │
│  │  (camera intrinsics, │    │  Net unfolding                 │  │
│  │   scale, pose)       │    │  SVG/PDF export                │  │
│  │                      │    │                               │  │
│  │  Share via:          │    │  Share via:                    │  │
│  │  - Files app         │    │  - Files app (SVG/PDF/STL)    │  │
│  │  - AirDrop           │    │  - AirDrop                    │  │
│  │  - iCloud Drive      │    │  - Print directly             │  │
│  │  - USB               │    │                               │  │
│  └─────────────────────┘    └──────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
            │
            │  .ply / .obj + .jpg + .json
            ▼
┌──────────────────────────────────────────────────────────────┐
│                    Windows PC (optional)                       │
│                                                                │
│  Python + Open3D + trimesh + NumPy + OpenCV + Shapely         │
│                                                                │
│  surfacenet/                                                  │
│  ├── ingest.py          Load .ply/.obj + metadata             │
│  ├── reconstruct.py     Point cloud → mesh (if needed)        │
│  ├── segment.py         Multi-plane RANSAC                    │
│  ├── rectify.py         Per-face homography                   │
│  ├── unfold.py          Spanning tree net unfolding            │
│  ├── export.py          SVG / PDF / STL output                │
│  ├── pipeline.py        End-to-end orchestrator               │
│  └── cli.py             Command-line interface                │
│                                                                │
│  python -m surfacenet scan.ply --output net.svg               │
└──────────────────────────────────────────────────────────────┘
```

### 4.3 Export Data Bundle Format

When the iPhone exports data for PC processing, it packages a directory:

```
my_scan/
├── mesh.ply              # Triangle mesh (vertices + faces + normals + colours)
├── mesh.obj              # Same mesh in OBJ format (for Pepakura compat)
├── metadata.json         # Camera intrinsics, LiDAR calibration, scale
├── textures/
│   ├── frame_000.jpg     # RGB camera frames (if texture mode enabled)
│   ├── frame_001.jpg
│   └── ...
└── depth/
    ├── frame_000.png     # 16-bit depth maps (if raw export enabled)
    └── ...
```

The `metadata.json` schema:

```json
{
  "version": "1.0",
  "device": "iPhone 15 Pro",
  "capture_date": "2026-03-12T14:30:00Z",
  "camera_intrinsics": {
    "fx": 1598.0, "fy": 1598.0,
    "cx": 960.0, "cy": 540.0,
    "width": 1920, "height": 1080
  },
  "lidar_range_m": 5.0,
  "mesh_stats": {
    "num_vertices": 12450,
    "num_faces": 24800,
    "bounding_box_m": [0.15, 0.12, 0.08]
  },
  "scale_reference": {
    "type": "lidar_calibrated",
    "unit": "metres",
    "confidence": 0.95
  }
}
```

### 4.4 On-Device Feasibility Summary

| Pipeline Stage | On-Device? | iOS Framework | Difficulty |
|---|---|---|---|
| LiDAR → mesh | Yes | ARKit Scene Geometry | Easy (Apple provides) |
| Mesh simplification | Yes | Custom Swift + Metal | Medium (no library; port quadric decimation) |
| RANSAC segmentation | Yes | Custom Swift + Accelerate/SIMD | Medium (no library; straightforward to implement) |
| Homography rectification | Yes | Accelerate + SIMD | Medium |
| Net unfolding | Yes | Custom Swift (graph BFS) | Easy-Medium |
| Overlap detection | Yes | GEOSwift or iOverlay | Easy (libraries exist) |
| SVG/PDF export | Yes | PDFKit / SVGgh / SwiftDraw | Easy |

No fundamental barriers. The gap is library maturity, not computational power. A 200-face mesh processes in well under a second on any recent iPhone.


## 5. Python Processing Pipeline — Detailed Module Specifications

This section defines every module precisely enough for Claude Code (Sonnet 4.6) to implement directly. Each module specifies its function signatures, data types, algorithms, edge cases, and test criteria.

### 5.0 Project Structure

```
surfacenet/
├── pyproject.toml
├── README.md
├── surfacenet/
│   ├── __init__.py
│   ├── types.py            # Shared data types (dataclasses)
│   ├── ingest.py           # Module 1: File loading
│   ├── reconstruct.py      # Module 2: Point cloud → mesh
│   ├── simplify.py         # Module 2b: Mesh decimation
│   ├── segment.py          # Module 3: Planar segmentation
│   ├── rectify.py          # Module 4: Homography rectification
│   ├── unfold.py           # Module 5: Net unfolding
│   ├── tabs.py             # Module 5b: Glue tab generation
│   ├── export_svg.py       # Module 6a: SVG export
│   ├── export_pdf.py       # Module 6b: PDF export
│   ├── export_stl.py       # Module 6c: STL export
│   ├── pipeline.py         # End-to-end orchestrator
│   └── cli.py              # CLI entry point
├── tests/
│   ├── test_types.py
│   ├── test_ingest.py
│   ├── test_reconstruct.py
│   ├── test_simplify.py
│   ├── test_segment.py
│   ├── test_rectify.py
│   ├── test_unfold.py
│   ├── test_tabs.py
│   ├── test_export_svg.py
│   ├── test_export_pdf.py
│   ├── test_export_stl.py
│   ├── test_pipeline.py
│   └── fixtures/
│       ├── cube.ply
│       ├── cube.obj
│       ├── tetrahedron.obj
│       ├── l_shape.obj
│       └── metadata_sample.json
└── examples/
    ├── unfold_cube.py
    ├── unfold_from_scan.py
    └── sample_scans/
        └── .gitkeep
```

### 5.1 Module: types.py — Shared Data Types

```python
"""
Defines all shared data structures used across the pipeline.
All geometry uses metres as the base unit.
All angles in radians unless documented otherwise.
"""
from dataclasses import dataclass, field
import numpy as np
from typing import Optional

@dataclass
class Mesh:
    """Triangle mesh in 3D space."""
    vertices: np.ndarray       # (V, 3) float64 — xyz positions in metres
    faces: np.ndarray          # (F, 3) int32 — vertex indices per face
    normals: np.ndarray        # (F, 3) float64 — per-face unit normals
    vertex_colours: Optional[np.ndarray] = None  # (V, 3) uint8 — RGB per vertex

    @property
    def num_vertices(self) -> int: ...
    @property
    def num_faces(self) -> int: ...
    def face_vertices(self, face_idx: int) -> np.ndarray:
        """Return (3, 3) array of vertex positions for a face."""
        ...
    def face_area(self, face_idx: int) -> float:
        """Area of a single face in m²."""
        ...
    def bounding_box(self) -> tuple[np.ndarray, np.ndarray]:
        """Return (min_corner, max_corner) each (3,)."""
        ...

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
```

### 5.2 Module: ingest.py — File Loading

```
Function: load_mesh(path: str | Path) -> Mesh
  - Accept .ply and .obj files
  - Use trimesh.load() internally
  - Compute per-face normals if not present
  - Validate: must have ≥4 faces, must be manifold (warn if not)
  - Raise FileNotFoundError, ValueError on bad input

Function: load_metadata(path: str | Path) -> CameraMetadata
  - Load metadata.json from export bundle
  - Validate required fields
  - Return CameraMetadata dataclass

Function: load_scan_bundle(directory: str | Path) -> tuple[Mesh, Optional[CameraMetadata]]
  - Load mesh.ply (or mesh.obj) + metadata.json from a scan directory
  - Metadata is optional (PC-only workflows may not have it)
```

**Test criteria:**
- Load the cube.ply fixture → 8 vertices, 12 faces (triangulated cube)
- Load the tetrahedron.obj → 4 vertices, 4 faces
- Bad file path → FileNotFoundError
- Empty mesh → ValueError

### 5.3 Module: reconstruct.py — Point Cloud to Mesh

```
Function: point_cloud_to_mesh(
    points: np.ndarray,          # (N, 3) xyz
    normals: np.ndarray,         # (N, 3) estimated normals
    method: str = "poisson",     # "poisson" or "ball_pivot"
    depth: int = 8               # Poisson octree depth
) -> Mesh
  - Use Open3D internally
  - Poisson: open3d.geometry.TriangleMesh.create_from_point_cloud_poisson
  - Ball Pivot: compute radii from point spacing, then create_from_point_cloud_ball_pivoting
  - Clean result: remove degenerate faces, unreferenced vertices

Function: estimate_normals(
    points: np.ndarray,          # (N, 3)
    k_neighbours: int = 20
) -> np.ndarray                  # (N, 3) estimated normals
  - Use Open3D's estimate_normals with KNN
  - Orient normals consistently (Open3D orient_normals_consistent_tangent_plane)
```

**Test criteria:**
- 1000 random points on a unit sphere → mesh should approximate a sphere (Euler characteristic = 2)
- Points on a plane → mesh should be flat (all normals ≈ [0,0,1])

### 5.4 Module: simplify.py — Mesh Decimation

```
Function: simplify_mesh(
    mesh: Mesh,
    target_faces: int = 100,
    preserve_boundary: bool = True
) -> Mesh
  - Use Open3D simplify_quadric_decimation
  - Recompute normals after simplification
  - Validate output: no degenerate faces, target_faces ± 10%

Function: auto_target_faces(mesh: Mesh) -> int
  - Heuristic: aim for faces where the smallest face is ≥ 1cm² at scale
  - Clamp between 20 and 500
  - Return recommended target face count
```

**Test criteria:**
- 10,000-face sphere → simplify to 100 faces → still roughly spherical (bounding box similar)
- Cube (12 faces) → simplify to 12 → no change (already at target)
- Simplify to 6 → should reduce (may merge coplanar triangles)

### 5.5 Module: segment.py — Planar Segmentation

```
Function: segment_planes(
    mesh: Mesh,
    distance_threshold: float = 0.01,  # metres
    angle_threshold: float = 15.0,     # degrees — faces with normals within this are coplanar
    min_faces_per_patch: int = 1
) -> list[PlanarPatch]
  - For triangle meshes: group faces by normal similarity + spatial connectivity
  - Algorithm:
    1. For each face, compute its unit normal
    2. Build adjacency graph (faces sharing an edge)
    3. BFS/flood-fill: starting from unvisited face, expand to neighbours
       whose normal is within angle_threshold degrees
    4. Each connected component = one PlanarPatch
    5. Fit a least-squares plane to each patch's vertices
  - Return patches sorted by total area (largest first)

Function: segment_planes_ransac(
    points: np.ndarray,
    max_planes: int = 20,
    distance_threshold: float = 0.01,
    min_points: int = 50
) -> list[PlanarPatch]
  - For point cloud input (pre-meshing)
  - Iterative RANSAC using Open3D segment_plane
  - Remove inliers after each plane found
  - Stop when remaining points < min_points or max_planes reached
```

**Test criteria:**
- Cube mesh → exactly 6 patches (one per face direction)
- L-shaped mesh (two perpendicular rectangles) → 2–3 patches depending on threshold
- Single-plane mesh → 1 patch

### 5.6 Module: rectify.py — Homography Rectification

```
Function: project_face_to_2d(
    mesh: Mesh,
    face_idx: int
) -> np.ndarray  # (3, 2) — 2D coordinates in metres
  - Construct local coordinate frame on the face's plane:
    1. normal n = mesh.normals[face_idx]
    2. p0 = mesh.face_vertices(face_idx)[0]
    3. u = normalise(arbitrary vector ⊥ n)  # use cross product with [0,0,1] or [0,1,0]
    4. v = cross(n, u)
  - Project each vertex: (x, y) = ((p - p0)·u, (p - p0)·v)
  - Preserves true metric distances (result is in metres)

Function: compute_homography(
    points_3d: np.ndarray,       # (N, 3) points on a known plane
    camera_intrinsics: CameraMetadata,
    camera_pose: np.ndarray      # (4, 4) extrinsic matrix
) -> np.ndarray  # (3, 3) homography matrix
  - H = K @ [r1 r2 t] where R = camera_pose[:3,:3], t = camera_pose[:3,3]
  - r1, r2 are first two columns of R (aligned to plane's local frame)
  - K is intrinsic matrix from CameraMetadata

Function: rectify_texture(
    image: np.ndarray,           # (H, W, 3) RGB camera frame
    homography: np.ndarray,      # (3, 3)
    output_size: tuple[int, int] # (width, height) in pixels
) -> np.ndarray  # (H, W, 3) rectified texture
  - Use cv2.warpPerspective(image, H_inv, output_size)
  - Handle edge cases: region outside image → fill with neutral grey
```

**Test criteria:**
- project_face_to_2d on an equilateral triangle face → 2D triangle with correct edge lengths
- project_face_to_2d on a right-angle face → 2D right triangle preserving the 90° angle
- Homography of a frontal-facing square should be ≈ identity (up to scale/translation)

### 5.7 Module: unfold.py — Net Unfolding (Core Algorithm)

```
Function: build_dual_graph(mesh: Mesh) -> dict
  - Return adjacency structure:
    {face_idx: [(neighbour_face_idx, shared_edge_vertices), ...]}
  - shared_edge_vertices is a tuple of two vertex indices
  - Use trimesh.graph or compute from face arrays directly

Function: find_spanning_tree(
    dual_graph: dict,
    root_face: int = 0,
    strategy: str = "bfs"        # "bfs", "dfs", or "largest_first"
) -> dict
  - Return parent map: {face_idx: (parent_face_idx, shared_edge)}
  - root maps to (None, None)
  - "largest_first" = BFS but prioritise expanding to larger faces first
    (heuristic to reduce overlaps)

Function: unfold_spanning_tree(
    mesh: Mesh,
    spanning_tree: dict,
    root_face: int = 0
) -> list[Face2D]
  - Place root face flat using project_face_to_2d
  - For each face in BFS order from root:
    1. Get the shared edge with parent (two 3D vertex positions)
    2. Find those same vertices in parent's already-placed 2D positions
    3. Compute the dihedral angle between child face and parent face
    4. Rotate child face around the shared edge by (π - dihedral_angle)
    5. This places the child flat, adjacent to parent
  - Return list of Face2D with 2D positions

  Implementation detail for step 4:
    - The shared edge in 2D is a line segment (a, b)
    - The child's third vertex needs to be reflected/rotated to the correct side
    - Use 2D rotation matrix around the edge midpoint
    - The rotation formula:
      1. Translate so edge start is at origin
      2. Rotate so edge aligns with x-axis
      3. Place the third vertex using the face's edge lengths and the unfolding angle
      4. Reverse the translation and rotation

Function: detect_overlaps(faces: list[Face2D]) -> list[tuple[int, int]]
  - For each pair of non-adjacent faces, check polygon intersection
  - Use Shapely: Polygon(face.vertices_2d).intersects(other)
  - Exclude shared-edge adjacencies (they touch but don't overlap)
  - Return list of overlapping face pairs

Function: unfold_mesh(
    mesh: Mesh,
    max_attempts: int = 50,
    strategies: list[str] = ["bfs", "dfs", "largest_first"]
) -> UnfoldedNet
  - Try multiple spanning trees across strategies and root faces
  - For each attempt:
    1. Pick strategy and root face
    2. Build spanning tree
    3. Unfold
    4. Count overlaps
    5. If 0 overlaps → return immediately
  - If no zero-overlap solution found:
    - Return the best (fewest overlaps)
    - Set overlap_count on the result
  - Generate fold_edges, cut_edges, and call generate_tabs()
```

**Test criteria — these are critical:**
- Cube (12 triangulated faces) → unfolded net with 0 overlaps
- Tetrahedron (4 faces) → unfolded net with 0 overlaps
- The unfolded net, when "refolded" mathematically, should reconstruct the original vertex positions (round-trip test)
- Total surface area of unfolded faces should equal total surface area of original mesh
- All fold edges should connect exactly two adjacent faces
- All cut edges should have exactly one glue tab

### 5.8 Module: tabs.py — Glue Tab Generation

```
Function: generate_tabs(
    mesh: Mesh,
    unfolded_faces: list[Face2D],
    spanning_tree: dict,
    tab_width_m: float = 0.005   # 5mm default
) -> list[GlueTab]
  - For each edge in the mesh that is NOT in the spanning tree:
    1. This is a "cut edge" — needs a glue tab
    2. Find which face the tab attaches to (pick one side)
    3. Compute the tab trapezoid:
       - Base = the edge itself
       - Offset outward from the face by tab_width_m
       - Taper the ends slightly (80% width at tips) for easier folding
    4. Number tabs sequentially
  - Check that no tab overlaps another tab or face
  - If overlap: shrink tab or move to the other side of the edge

Function: classify_edges(
    mesh: Mesh,
    spanning_tree: dict,
    unfolded_faces: list[Face2D]
) -> tuple[list, list]
  - Return (fold_edges_2d, cut_edges_2d)
  - fold_edges: edges in the spanning tree (will be scored/dashed in SVG)
  - cut_edges: edges not in the spanning tree (will be solid lines, get tabs)
```

**Test criteria:**
- Cube net → 7 fold edges, 5 cut edges (for a 12-triangle cube: 11 tree edges, remaining are cuts)
- Every cut edge has exactly one tab
- No tab overlaps any face polygon

### 5.9 Module: export_svg.py — SVG Export

```
Function: net_to_svg(
    net: UnfoldedNet,
    output_path: str | Path,
    paper_size: str = "A4",        # "A4", "A3", "letter", "tabloid"
    scale: float = 1.0,            # 1.0 = true size, 0.5 = half size, etc.
    show_tabs: bool = True,
    show_face_numbers: bool = True,
    show_scale_bar: bool = True,
    line_widths: dict = None       # override defaults
) -> Path
  - Convert net coordinates (metres) to SVG coordinates (mm at scale)
  - Centre the net on the page
  - If net exceeds page → auto-scale to fit (with warning) or split across pages
  - Line styles:
    - Cut edges: solid black, 0.5pt
    - Fold edges: dashed grey, 0.3pt
    - Tab outlines: dotted light grey, 0.2pt
  - Face numbers: small text at centroid of each face
  - Tab numbers: small text at centroid of each tab
  - Scale bar: bottom-right corner, labelled in cm
  - Use svgwrite library
  - Return the output path

Function: auto_layout(
    net: UnfoldedNet,
    paper_width_mm: float,
    paper_height_mm: float,
    margin_mm: float = 10.0
) -> tuple[float, np.ndarray]
  - Compute optimal scale and translation to fit net on paper
  - Return (scale_factor, translation_offset)
```

**Test criteria:**
- Cube net → valid SVG file that opens in a browser
- SVG dimensions match specified paper size
- Scale bar length in SVG matches its label
- All faces visible (none clipped by page boundary)

### 5.10 Module: export_pdf.py — PDF Export

```
Function: net_to_pdf(
    net: UnfoldedNet,
    output_path: str | Path,
    paper_size: str = "A4",
    scale: float = 1.0
) -> Path
  - Render the SVG to PDF at true physical scale
  - Use reportlab or convert SVG → PDF via cairosvg
  - Multi-page if net exceeds one sheet (split into connected sub-nets)
  - Include assembly instructions on a separate page:
    - Tab numbering legend
    - Estimated dimensions
    - Fold direction indicators
```

### 5.11 Module: export_stl.py — STL Export

```
Function: mesh_to_stl(
    mesh: Mesh,
    output_path: str | Path,
    binary: bool = True
) -> Path
  - Export the original 3D mesh (pre-unfolding) as STL
  - Use numpy-stl
  - Binary format by default (smaller files)
```

### 5.12 Module: pipeline.py — End-to-End Orchestrator

```
Function: process_scan(
    input_path: str | Path,
    output_dir: str | Path,
    target_faces: int = 100,
    output_formats: list[str] = ["svg"],   # "svg", "pdf", "stl"
    paper_size: str = "A4",
    scale: float = 1.0,
    max_unfold_attempts: int = 50
) -> dict
  - Full pipeline:
    1. Load mesh (ingest)
    2. Simplify if needed (simplify)
    3. Segment planes (segment)
    4. Unfold (unfold)
    5. Generate tabs (tabs)
    6. Export in requested formats (export_*)
  - Return summary dict:
    {
      "input": str(input_path),
      "num_faces_original": int,
      "num_faces_simplified": int,
      "num_patches": int,
      "overlap_count": int,
      "outputs": {"svg": "path.svg", "pdf": "path.pdf", "stl": "path.stl"},
      "warnings": [...]
    }
```

### 5.13 Module: cli.py — Command-Line Interface

```
Usage:
  python -m surfacenet <input> [options]

Arguments:
  input                    Path to .ply, .obj, or scan bundle directory

Options:
  -o, --output DIR         Output directory (default: ./output/)
  -f, --format FMT         Output format(s): svg, pdf, stl (comma-separated)
  -n, --faces N            Target face count after simplification (default: 100)
  --paper SIZE             Paper size: A4, A3, letter, tabloid (default: A4)
  --scale FACTOR           Scale factor (default: 1.0 = true size)
  --no-tabs                Omit glue tabs from net
  --no-numbers             Omit face/tab numbers
  -v, --verbose            Verbose logging
  -h, --help               Show help

Examples:
  python -m surfacenet scan.ply -f svg,stl
  python -m surfacenet my_scan/ -f pdf --paper A3 --scale 0.5 -n 80
```


## 6. Development Phases — Claude Code Task Breakdown

Each phase below is structured as a sequence of tasks that Claude Code (Sonnet 4.6) can execute. Tasks are ordered by dependency. Each task specifies what to implement, what to test, and the acceptance criteria.

### Phase 0 — Proof of Concept: Cube → SVG Net

**Goal:** Prove the core unfolding algorithm works with a hardcoded cube mesh. Print the SVG, cut it out, fold it into a cube. If this fails, nothing else matters.

**Duration:** 1–2 sessions

#### Task 0.1: Project scaffolding
```
PROMPT: "Create the project structure for surfacenet. Set up pyproject.toml
with dependencies: numpy, scipy, shapely, svgwrite, trimesh, matplotlib,
pytest. Create the directory structure as specified in section 5.0 of the
architecture doc. All __init__.py files should exist but can be empty.
Create a pytest configuration in pyproject.toml."
```
- **Acceptance:** `pip install -e .` works, `pytest` runs with 0 tests collected

#### Task 0.2: Data types
```
PROMPT: "Implement surfacenet/types.py exactly as specified in section 5.1
of the architecture doc. All dataclasses, all properties, all type hints.
Write tests in tests/test_types.py: construct a Mesh from a unit cube
(8 vertices, 12 triangular faces), verify num_vertices, num_faces,
face_vertices returns correct shape, face_area returns correct area,
bounding_box is correct."
```
- **Acceptance:** All type tests pass. Mesh correctly represents a triangulated cube.

#### Task 0.3: Test fixtures
```
PROMPT: "Create test fixture files in tests/fixtures/:
  - cube.obj: unit cube (side length 1m, centred at origin, triangulated
    into 12 faces)
  - tetrahedron.obj: regular tetrahedron (side length 1m)
  - l_shape.obj: an L-shaped prism (like two cubes joined at a face,
    9 visible faces when triangulated)
Write a conftest.py with pytest fixtures that load these into Mesh objects."
```
- **Acceptance:** All fixture files are valid OBJ, loadable by trimesh.

#### Task 0.4: Mesh ingestion
```
PROMPT: "Implement surfacenet/ingest.py: the load_mesh function as specified
in section 5.2. Use trimesh internally. Compute per-face normals.
Validate manifoldness (warn, don't error). Write tests in
tests/test_ingest.py: load each fixture, verify face/vertex counts,
test error handling for missing files and empty meshes."
```
- **Acceptance:** All fixtures load correctly. Error cases handled.

#### Task 0.5: Core unfolding algorithm
```
PROMPT: "Implement surfacenet/unfold.py with all functions specified in
section 5.7: build_dual_graph, find_spanning_tree (all 3 strategies),
unfold_spanning_tree, detect_overlaps, unfold_mesh.

The critical implementation detail is unfold_spanning_tree. For each child
face being unfolded around a shared edge with its parent:
1. The shared edge gives you two 2D points (already placed from the parent).
2. The child's third vertex must be placed such that:
   a. Its distance to each shared vertex matches the 3D edge lengths
   b. It's on the opposite side of the shared edge from the parent's interior
3. Use the law of cosines or direct 2D triangle construction.

Write comprehensive tests in tests/test_unfold.py:
- Cube → 0 overlaps
- Tetrahedron → 0 overlaps
- Area preservation: sum of 2D face areas == sum of 3D face areas
- Edge length preservation: every edge in the net matches its 3D length
- Round-trip: the spanning tree + unfolded positions should be consistent"
```
- **Acceptance:** Cube and tetrahedron unfold with 0 overlaps. Area and edge lengths preserved to within 1e-10.

#### Task 0.6: Glue tab generation
```
PROMPT: "Implement surfacenet/tabs.py as specified in section 5.8.
Generate trapezoidal tabs on cut edges. Number them sequentially.
Classify all edges as fold or cut.

Tests in tests/test_tabs.py:
- Cube: correct number of fold vs cut edges
- Every cut edge has exactly one tab
- No tab overlaps any face (use Shapely intersection check)"
```
- **Acceptance:** Correct edge classification and tab placement for cube and tetrahedron.

#### Task 0.7: SVG export
```
PROMPT: "Implement surfacenet/export_svg.py as specified in section 5.9.
Render the unfolded net as an SVG with:
- Solid black lines for cut edges
- Dashed grey lines for fold edges
- Dotted light grey for tab outlines
- Face numbers at centroids
- Tab numbers at tab centroids
- A scale bar in the bottom-right

Test: generate SVG for the cube net, verify the file is valid SVG,
verify dimensions are reasonable for A4 paper."
```
- **Acceptance:** SVG opens in a browser and shows a recognisable cube net.

#### Task 0.8: End-to-end Phase 0 demo
```
PROMPT: "Create examples/unfold_cube.py that:
1. Creates a unit cube Mesh (or loads cube.obj)
2. Unfolds it
3. Generates tabs
4. Exports to output/cube_net.svg
5. Prints a summary: face count, overlap count, edge counts

Run it and verify the SVG looks correct. Also create a visual test using
matplotlib: plot the unfolded net with fold/cut edges in different colours."
```
- **Acceptance:** cube_net.svg is a correct, printable cube net. If printed at scale, it folds into a 1m cube (or whatever scale is set).

### Phase 1 — Real Scan Integration

**Goal:** Load a real .ply scan from an iPhone → simplify → unfold → SVG.

**Duration:** 2–4 sessions

#### Task 1.1: Mesh simplification
```
PROMPT: "Implement surfacenet/simplify.py as specified in section 5.4.
Use Open3D for quadric decimation. Include the auto_target_faces heuristic.
Tests: simplify a high-poly sphere to 100 faces, verify bounding box is
preserved, verify face count is within ±10% of target."
```

#### Task 1.2: Planar segmentation
```
PROMPT: "Implement surfacenet/segment.py as specified in section 5.5.
Both the normal-similarity flood-fill (for meshed input) and RANSAC
(for point cloud input). Tests: cube → 6 patches, L-shape → correct
patch count."
```

#### Task 1.3: Surface reconstruction
```
PROMPT: "Implement surfacenet/reconstruct.py as specified in section 5.3.
Both Poisson and Ball Pivot methods. Include normal estimation.
Tests: sphere point cloud → valid mesh, plane point cloud → flat mesh."
```

#### Task 1.4: Pipeline orchestrator
```
PROMPT: "Implement surfacenet/pipeline.py as specified in section 5.12.
Wire all modules together. Handle the case where input is already a mesh
(skip reconstruction). Include logging at each step.
Test: run the full pipeline on cube.obj → produces SVG."
```

#### Task 1.5: CLI
```
PROMPT: "Implement surfacenet/cli.py as specified in section 5.13.
Use argparse. Wire to pipeline.process_scan.
Test: python -m surfacenet tests/fixtures/cube.obj -f svg -o /tmp/test/"
```

#### Task 1.6: Real scan test
```
PROMPT: "Download a sample .ply point cloud (or use one from the
examples/sample_scans/ directory if available). Run the full pipeline:
load → reconstruct if needed → simplify to 100 faces → segment →
unfold → SVG. Document any issues encountered."
```

### Phase 2 — Homography & Texture

**Goal:** Add texture mapping. Given paired RGB + depth data, project camera images onto each face of the net.

**Duration:** 2–3 sessions

#### Task 2.1: Homography rectification
```
PROMPT: "Implement surfacenet/rectify.py as specified in section 5.6.
project_face_to_2d, compute_homography, rectify_texture.
Tests: verify metric preservation, verify frontal-facing homography ≈ identity."
```

#### Task 2.2: Textured SVG export
```
PROMPT: "Extend export_svg.py to optionally embed rectified textures
as clipped images within each face polygon. Use SVG <clipPath> elements.
The SVG should work with and without textures."
```

#### Task 2.3: Metadata ingestion
```
PROMPT: "Extend ingest.py to load the full scan bundle format
(mesh + metadata.json + texture frames). Parse camera intrinsics
from metadata.json into CameraMetadata."
```

### Phase 3 — Quality & Robustness

**Goal:** Handle edge cases, improve output quality, add PDF and STL export.

**Duration:** 2–3 sessions

#### Task 3.1: Multi-component nets
```
PROMPT: "Handle meshes that unfold with unavoidable overlaps by splitting
into multiple disconnected net pieces. Each piece gets its own numbering.
The SVG should lay out multiple pieces on the page."
```

#### Task 3.2: PDF export
```
PROMPT: "Implement export_pdf.py as specified in section 5.10.
True physical scale, multi-page layout, assembly instructions page."
```

#### Task 3.3: STL export
```
PROMPT: "Implement export_stl.py as specified in section 5.11.
Binary STL output. Verify with numpy-stl that the file is valid."
```

#### Task 3.4: Robustness hardening
```
PROMPT: "Add error handling throughout the pipeline:
- Degenerate faces (zero area) → skip with warning
- Non-manifold edges → warn and attempt to fix
- Very thin faces → merge with neighbour
- Scale validation: warn if net exceeds 2m in any dimension
Add integration tests with deliberately messy input."
```

### Phase 4 — iOS App (Requires Mac Access)

**Goal:** Native iOS capture + on-device processing, plus export path to PC.

**Duration:** 4–6 sessions

#### Task 4.1: Xcode project setup
```
PROMPT: "Create a new SwiftUI iOS project targeting iOS 16+.
Configure ARKit with sceneReconstruction. Set up the project
structure with separate files for: CaptureView, ProcessingEngine,
ExportManager, MeshTypes."
```

#### Task 4.2: LiDAR capture view
```
PROMPT: "Implement CaptureView: an AR camera view that shows the
reconstructed mesh overlay in real-time. Add a 'Capture' button
that snapshots the current mesh. Display face count and bounding box."
```

#### Task 4.3: Export path (MVP)
```
PROMPT: "Implement ExportManager: export the captured mesh as .ply
and .obj via the iOS share sheet. Include metadata.json with camera
intrinsics. This enables the PC processing path immediately."
```

#### Task 4.4: On-device processing
```
PROMPT: "Port the core algorithms to Swift:
- Mesh simplification (quadric decimation)
- Planar segmentation (normal flood-fill)
- Spanning tree unfolding
- Overlap detection (use GEOSwift or iOverlay)
Use Accelerate/SIMD for linear algebra."
```

#### Task 4.5: On-device SVG/PDF output
```
PROMPT: "Generate SVG using string templating (SVG is just XML).
Generate PDF using PDFKit. Share via Files app or AirDrop."
```


## 7. Open Questions (Updated)

### Resolved
- **Direction:** A (SurfaceNet / fabrication). Confirmed.
- **Platform:** Dual-mode (on-device + PC export). Both supported.

### Still Open

**Q1: Primary user for MVP?**
Maker/hobbyist vs. naval/OR researcher. Affects UI polish vs. metric accuracy priority.

**Q2: Minimum scan quality assumption?**
Cooperative conditions (good lighting, orbit around object) vs. worst-case (engine room, reflective metal).

**Q3: Texture priority?**
Deferred to Phase 2. Untextured nets first. Confirmed as the right sequencing.

**Q4: Paper vs. 3D printing as primary output?**
Paper nets are more novel. STL is trivial. Recommend paper-first.

**Q5: Offline requirement?**
Python on PC: trivially offline. iOS: ARKit works offline. Only AIS (future) needs connectivity.

**Q6: Academic paper?**
Best angle: "LiDAR-calibrated metric fabrication templates from consumer devices." Applied computational geometry venue.


## 8. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Unfolding produces unusable nets (too many overlaps) | Medium | High | Phase 0 tests this immediately with synthetic shapes |
| iPhone LiDAR scan quality too low for fabrication-grade nets | Medium | Medium | Mesh simplification + manual cleanup; test early with real scans |
| No Mac access blocks iOS development | Known | Medium | Python-first architecture; core product works without iOS |
| Scope creep across SurfaceNet and MarineRange | High | High | MarineRange explicitly deferred |
| Existing tool adds this feature (Polycam, Scaniverse) | Low | High | Move fast; unfolding is non-obvious to scanner app teams |
| Mesh simplification loses critical features | Medium | Medium | Tunable target face count; visual preview before export |
| Non-convex meshes produce unavoidable overlaps | Medium | Low | Multi-component net splitting (Phase 3) |


## 9. Dependency Stack

### Python (PC processing)
```
Python 3.10+
├── open3d          — point cloud I/O, meshing, plane segmentation, simplification
├── numpy           — all linear algebra
├── opencv-python   — homography computation, image warping (Phase 2+)
├── scipy           — spatial operations, KD-trees, optimisation
├── shapely         — 2D polygon intersection (overlap detection)
├── svgwrite        — SVG net export
├── numpy-stl       — STL mesh export
├── trimesh         — mesh loading, dual graph, adjacency
├── matplotlib      — visualisation during development
├── reportlab       — PDF export (Phase 3+)
└── pytest          — testing
```

### iOS (on-device, Phase 4+)
```
Swift 5.9+ / iOS 16+
├── ARKit           — LiDAR capture, Scene Geometry mesh
├── Metal           — GPU compute for mesh operations
├── Accelerate      — BLAS/LAPACK for linear algebra
├── SIMD            — Vector/matrix operations
├── ModelIO         — Mesh I/O (OBJ, USDZ export)
├── PDFKit          — PDF generation
├── GEOSwift        — 2D polygon operations (overlap detection)
└── SVGgh           — SVG rendering (or string-template SVG)
```


## 10. Immediate Next Steps

1. **Open a Claude Code session with Sonnet 4.6**
2. **Share this document** as context (or place it in the project root)
3. **Execute Phase 0 tasks sequentially** (Tasks 0.1 → 0.8)
4. **After Task 0.8:** Print the cube net SVG. Cut it out. Fold it. Photograph the result.
5. **If it works:** Proceed to Phase 1 with a real .ply scan
6. **If it doesn't:** Debug the unfolding algorithm before proceeding

The cube net is the single most important validation. Everything else is plumbing around it.

---

*This document is a living reference. Update it as decisions are made and the architecture evolves.*
