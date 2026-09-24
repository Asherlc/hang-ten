# lattice-mxedge-lift-large CAD authoring provenance

Date: 2026-09-24

This record preserves the provenance carried by the retired one-off migration
script `Tools/HangboardCAD/migration/author_lattice_mxedge_lift_large.py`, which authored
`Hangboards/lattice-mxedge-lift-large/lattice-mxedge-lift-large.FCStd`. The script was never a build input: the
committed FCStd stands alone, and its embedded `HangTenBoardManifest` is now the
source of `board.json` (`Tools/HangboardCAD/board_manifest.py`). The script was
removed because re-running it would recreate the document without that manifest.

Nothing below is new evidence. The module docstring, recorded constants, inline
notes, and pre-save checks are copied from the script so the trail from
published product facts and the measured Git reference to the authored document
survives. Where the script distinguished PUBLISHED values from MEASURED ones, or
recorded a stated deviation, that wording is kept as written.

## Recovering the script

- Last commit that modified the script: `68cb1223ce18adb4b2d4cf7657314381d477e559`
- Last commit containing the script before its removal: `060eba8ebd6d5ba44ae8becd3a538232d483eaa9`

```sh
git show 060eba8ebd6d5ba44ae8becd3a538232d483eaa9:Tools/HangboardCAD/migration/author_lattice_mxedge_lift_large.py
```

The script imported the shared helpers `Tools/HangboardCAD/reference.py`
(`load_reference`, which resolves the approved reference USDZ from Git at the
recorded pre-migration commit) and ran under the pinned FreeCAD interpreter
(for example through `Tools/HangboardCAD/run_freecad.py`), reading extra site
directories such as the one providing `pxr` from `HANGTEN_CAD_PYTHONPATH`.

## Module docstring (verbatim)

```text
One-off migration: author Hangboards/lattice-mxedge-lift-large/lattice-mxedge-lift-large.FCStd.

Migration tool only — not a build input.

Provenance:
* Mesh envelope 168 x 34 x 98 mm (native X / depth Y / height Z), same brick as Small.
  board.json's "20 x 11 x 5 cm" is the shared rounded catalogue string. The committed
  descriptor modelBounds claims runtime Z +/-0.049 m; the reference mesh is +/-0.017 m.
  This source follows the mesh. Grip depths 22 / 16 / 12 / 28 mm are the published values.
* Front geometry measured from the Git-resolved reference USDZ
  (sha256 b8f9b7f75002f91b4ec45cf9b5212c7ae8a1ea6dffe9af9d5421a7566b9b2f25) on a 0.5 mm grid:
  - two stadium troughs, not four pockets. Upper recess sits near z [10, 34]; lower near
    z [-33, -12]. edge-12 and edge-16 split the upper trough (AABBs meet around z = 22);
    edge-22 is the lower trough's lower wall and mono-28 is the right-end bore;
  - stadium matches Small: arc centres x = +/-48 mm, rim radius 14 mm. Centres measured
    at z = 22 (upper; contact split) and z = -22 (lower; depth peak);
  - trough walls are **flat / vertical** (constant stadium radius, no ogee or entry
    bevel). MX grips are flat edges; the earlier Small-style smoothstep inset was a
    lambert readability choice and is intentionally omitted here;
  - floor crown c = 0.134 on depth(x) = depth(0) * (1 - c * (x/48)^2), fit on the upper
    floor (16.00, 15.87, 15.46, 14.79, 13.86 mm at x = 0, 12, 24, 36, 48) and the lower
    floor left of the mono (20.00, 19.83, 19.33 mm at x = 0, 12, 24);
  - measured centre floors are 16.0 mm (upper) and 20.0 mm (lower). Upper uses the
    published 16 mm. Lower uses the published 22 mm so the edge-22 region depth matches
    board.json. Stated deviation: lower floor 2 mm deeper than measured;
  - mono bore centred at (x 48, z -22). Radius tapers from 13.6 mm at the lip to
    11.7 mm at the published 28 mm floor (reference floor y = +10.5, r about 11.8);
  - two external cord mouths on the top edge, r 3.4 mm, 3 mm deep, at x = +/-69.75,
    y = 1. The reference omits the passage interior.
* Display material texture embedded from the same reference package.
* Measured approximation of a sculpted display mesh — not manufacturing geometry.
  compare_exports is evidence, not a gate.

Region partition (published depth is the region's Y extent at x = 0):

    edge-16  upper trough, lower wall, full depth        span 16
    edge-12  upper trough, upper wall, front 12 mm       span 12
    edge-22  lower trough, lower wall, left of the mono  span 22
    mono-28  lower trough right end + bore incl. floor   span 28
```

## Recorded constants

```python
PACKAGE = "lattice-mxedge-lift-large"
REFERENCE_SHA256 = "b8f9b7f75002f91b4ec45cf9b5212c7ae8a1ea6dffe9af9d5421a7566b9b2f25"
BOARD_JSON = REPOSITORY / "Hangboards" / PACKAGE / "board.json"
DESTINATION = REPOSITORY / "Hangboards" / PACKAGE / f"{PACKAGE}.FCStd"
BODY_PRIM = "/root/body/MXL_body_editable_skin_001"
Y_FRONT = -17.0
BODY_X = 168.0
BODY_Y = 34.0
BODY_Z = 98.0
HALF_X = BODY_X / 2.0
HALF_Z = BODY_Z / 2.0
Y_BACK = Y_FRONT + BODY_Y
# Outer envelope: 15 mm XZ corners plus a 4 mm roll into the front face only.
# Planar facets throughout — an OCCT fillet leaves a tessellation-vs-Area gap at compile.
CORNER_R = 15.0
CORNER_SEGMENTS = 12
CORNER_CENTER_X = HALF_X - CORNER_R
CORNER_CENTER_Z = HALF_Z - CORNER_R
EDGE_ROLL_R = 4.0
EDGE_ROLL_SEGMENTS = 4
GRIP_DEPTH_MM = {
    "edge-22": 22.0,
    "edge-16": 16.0,
    "edge-12": 12.0,
    "mono-28": 28.0,
}
# Measured stadium openings: arc centres at x = +/-48, rim radius = half the opening height.
TROUGH_HALF_LEN = 48.0
TROUGH_RADIUS = 14.0
# Even, so a vertex lands exactly on z = z_center and no facet straddles the wall that
# divides the trough's two regions.
TROUGH_ARC_SEGMENTS = 14
# Chords of the crowned floor parabola; 10 holds it to under 0.01 mm.
TROUGH_STRAIGHT_SEGMENTS = 10
TROUGHS = {
    "upper": {
        "z_center": 22.0,
        "depth": GRIP_DEPTH_MM["edge-16"],
        "crown_fraction": 0.134,
        # Flat vertical walls — no inward ogee/bevel.
        "apex_inset": 0.0,
    },
    "lower": {
        "z_center": -22.0,
        "depth": GRIP_DEPTH_MM["edge-22"],
        "crown_fraction": 0.134,
        "apex_inset": 0.0,
    },
}
# Depth fractions of the wall stations. With apex_inset 0 the rings share one
# stadium outline (flat walls); fractions still space the crowned floor and the
# absolute lip station for edge-12.
WALL_FRACTIONS = (
    0.0, 0.15, 0.35, 0.55, 0.75, 0.9, 1.0
)
# Micro inward ledge (mm) only at absolute lip stations. Flat vertical walls are
# otherwise coplanar and OCCT merges them into one face, which breaks the
# published-depth split (edge-12 = front 12 mm of the upper wall). This step is
# not an ogee/bevel; it is a hairline face break.
LIP_FACE_BREAK_MM = 0.25
STATION_MARGIN = 0.02
# Cutters start this far in front of the board so no boolean face is coplanar with it.
PROUD_MM = 0.3
CONTACT_X_LIMIT = 63.0
MONO_X_MIN = 34.4
MONO_CENTER_X = 48.0
MONO_CENTER_Z = -22.0
# Measured on the mono node around that centre: r 13.6 mm at y = -16, r 11.8 mm at
# y = 10 (the reference floor). The exported floor sits at the published 28 mm
# (y = 11), where the same taper is 11.7 mm.
MONO_RIM_R = 13.6
MONO_FLOOR_R = 11.7
# External cord mouths on the top edge. The reference only models the mouth
# (board.json: interior omitted): r 3.4 mm, 3 mm deep, centred at x = +/-69.75, y = 1.
HOLE_X = 69.75
HOLE_Y = 1.0
HOLE_RADIUS = 3.4
HOLE_DEPTH = 3.0
HOLE_SIDES = 24
# Planar n-gon only — a true Cylinder fails compile_board partition (distToShape 1e-4).
MONO_SIDES = 48
NODE_IDS = {
    "body": "MXL_body_editable_skin_001",
    "edge-22": "MXL_edge_22_editable_skin_001",
    "edge-16": "MXL_edge_16_editable_skin_001",
    "edge-12": "MXL_edge_12_editable_skin_001",
    "mono-28": "MXL_mono_28_editable_skin_001",
}
MATERIAL_NAME = "neutral_tulipwood"
MATERIAL_BASE_COLOR = "0.72,0.55,0.36"
MATERIAL_ROUGHNESS = 0.58
MATERIAL_METALLIC = 0.0
```

## Inline authoring notes

- `_inverse_smoothstep()`:
  - Docstring: Wall inset parameter for a depth fraction (exact inverse of a smoothstep).
- `_loft_solid()`:
  - Docstring: Ruled loft through polygonal sections, capped. Every section shares its arc centres with the others and differs only in radius, so each lateral face is a planar trapezoid and tessellates exactly.
- `_triangle_solid()`:
  - Docstring: Closed solid from an explicit triangle soup, outward-oriented. The crowned trough floor makes a quad between two wall stations non-planar, and a non-planar face would break `compile_board`'s surface-area partition check, which assumes tessellation is exact. Triangles are planar by construction, so the cutter is authored as triangles rather than lofted through polygon wires.
- `_rounded_rect_points()`:
  - Docstring: CCW XZ envelope outline whose corner radius is `radius` (corner centres fixed).
- `_body_solid()`:
  - Docstring: Envelope with 15 mm XZ corners and a 4 mm roll into the front face only. The back is a flat plane at Y_BACK — the manufacturer back is not rolled, and a mirrored back roll read as false indents in FreeCAD.
  - Flat back: full corner radius, no roll inset.
- `_trough_depth()`:
  - Docstring: Local trough depth at a station on the stadium core segment. The reference wall is one uniform depth scaling of its centre profile, so the whole wall — not just the floor — follows this parabola.
- `_stadium_template()`:
  - Docstring: CCW ring of (core_x, outward normal) samples of the stadium's core segment. A point of the outline inset by `s` is `(core_x + (R - s)*nx, z_center + (R - s)*nz)`, so every station reuses one template and corresponding samples stay aligned. The straight runs are subdivided because that is where the crowned floor bends.
- `_stations()`:
  - Docstring: Ordered wall stations of one trough, rim first. A ``fraction`` station rides the local trough depth, which is what keeps the wall a uniform scaling of the centre profile. An ``absolute`` station holds one constant y so a region boundary can land exactly on a published grip depth. Because the floor crowns, an absolute station sweeps across a band of fractions along the trough, and any fraction inside that band would cross it and fold the surface — so those are dropped and the ordering is then asserted at both ends of the sweep.
- `_ring()`:
  - Docstring: One closed ring of cutter vertices, one per template sample. Walls stay at the stadium rim radius (flat / vertical). Absolute lip stations take a `LIP_FACE_BREAK_MM` inward step so OCCT cannot merge the front lip band with the deeper wall into one coplanar face.
- `_cap_triangles()`:
  - Docstring: Close a stadium ring with facets that follow the crowned floor. A fan from one centre point would replace the parabolic floor with a cone, so the straight run is bridged strip by strip between its top and bottom samples, which pair up by x. Each end arc's samples all share one core x and therefore one y, so an arc is flat and can be fanned from its own axis point.
- `_trough_cutter()`:
  - Docstring: Stadium trough with a parabolically crowned floor, as planar triangles.
- `_mono_cutter()`:
  - Docstring: Tapered bore in the lower trough's right end; planar n-gon, no Cylinder.
- `_hole_cutter()`:
  - Docstring: Shallow vertical mouth in the top edge. Circle in XY, lofted in Z, n-gon only.
- `_wall_filter()`:
  - Docstring: Match trough-wall faces on one side of the apex, no deeper than `y_max`. The side test is on the face's whole extent, not its centroid. Each x strip of the floor is one plane, so the boolean hands it back as a single face spanning the full apex width, and a centroid test would assign it by whichever side a rounding error fell on. A face that straddles the centre line belongs to neither wall and stays with the body, which is also where the reference's own node split leaves it.
- `_mono_filter()`:
  - Docstring: Match the lower trough's right end plus the bore walls and floor.
- `main()`:
  - Rolled envelope is authored into the solid (not a post-cut Shape assign on Part::Cut).
  - The reference hands the lower trough's right end to the mono, not to edge-22.
  - Bake into Part::Feature so a later recompute cannot wipe the solid (Part::Cut is Base/Tool).

## Checks the script enforced before saving

Each guard below raised `ValueError` and aborted authoring (source lines verbatim).

```python
if len(names) != 1:
    raise ValueError(f"expected exactly one reference texture, found {names}")
if not shell.isClosed():
    raise ValueError("triangulated cutter shell is not closed")
if solid.Volume <= 0.0:
    raise ValueError(f"triangulated cutter has non-positive volume {solid.Volume}")
if depth >= depth_end:
    raise ValueError(f"absolute station {depth} mm is deeper than the trough end")
if any(b - a <= 1e-6 for a, b in zip(depths, depths[1:])):
    raise ValueError(f"wall stations are not ordered at core x {core_x}: {depths}")
if not faces:
    raise ValueError("no body faces matched the contact predicate")
if reference_digest != REFERENCE_SHA256:
    raise ValueError( f"reference digest {reference_digest} != pinned {REFERENCE_SHA256}" )
if abs(measured[key] - target) > 0.2:
    raise ValueError(f"reference {key} {measured[key]:.3f} mm != target {target}")
if any(abs(a - b) > 0.2 for a, b in zip(actual, expected)):
    raise ValueError(f"envelope bbox {actual} != expected {expected}")
if body_cut.Shape.isNull() or body_cut.Shape.Volume < 1.0:
    raise ValueError("boolean cut failed to produce a solid body")
if body_shape.isNull() or body_shape.Volume < 1.0:
    raise ValueError("cut body failed to produce a solid")
if stale:
    raise ValueError(f"document failed recompute: {stale}")
if abs(measured_depth - published) > 0.25:
    raise ValueError( f"{contact_id} region depth {measured_depth} mm != published {published} mm" )
```
