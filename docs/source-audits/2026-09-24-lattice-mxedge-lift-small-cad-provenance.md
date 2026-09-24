# lattice-mxedge-lift-small CAD authoring provenance

Date: 2026-09-24

This record preserves the provenance carried by the retired one-off migration
script `Tools/HangboardCAD/migration/author_lattice_mxedge_lift_small.py`, which authored
`Hangboards/lattice-mxedge-lift-small/lattice-mxedge-lift-small.FCStd`. The script was never a build input: the
committed FCStd stands alone, and its embedded `HangTenBoardManifest` is now the
source of `board.json` (`Tools/HangboardCAD/board_manifest.py`). The script was
removed because re-running it would recreate the document without that manifest.

Nothing below is new evidence. The module docstring, recorded constants, inline
notes, and pre-save checks are copied from the script so the trail from
published product facts and the measured Git reference to the authored document
survives. Where the script distinguished PUBLISHED values from MEASURED ones, or
recorded a stated deviation, that wording is kept as written.

## Recovering the script

- Last commit that modified the script: `9700d1238723f99d113a0427a9b7be40272e7735`
- Last commit containing the script before its removal: `060eba8ebd6d5ba44ae8becd3a538232d483eaa9`

```sh
git show 060eba8ebd6d5ba44ae8becd3a538232d483eaa9:Tools/HangboardCAD/migration/author_lattice_mxedge_lift_small.py
```

The script imported the shared helpers `Tools/HangboardCAD/reference.py`
(`load_reference`, which resolves the approved reference USDZ from Git at the
recorded pre-migration commit) and ran under the pinned FreeCAD interpreter
(for example through `Tools/HangboardCAD/run_freecad.py`), reading extra site
directories such as the one providing `pxr` from `HANGTEN_CAD_PYTHONPATH`.

## Module docstring (verbatim)

```text
One-off migration: author Hangboards/lattice-mxedge-lift-small/lattice-mxedge-lift-small.FCStd.

Migration tool only — not a build input.

Provenance:
* Overall envelope 168 x 34 x 98 mm (±84 / ±17 / ±49) and grip depths 18 / 14 / 8 / 25 mm
  from board.json / reference mesh packaging. Catalogue copy "20 × 11 × 5 cm" is rounded
  marketing and is **not** used to rescale the body.
* MXSMALL grips (Lattice MXEdge Lift): MX18, MX14, MX8 + 25 mm mono — area-equivalent
  labels; true depth varies along length (crowned floors).
* Front geometry measured from the Git-resolved reference USDZ (pre-migration commit via
  reference.load_reference) by depth-mapping its front surface on a 0.5 mm grid:
  - the front carries **two stadium troughs**, not four separate openings. Every x column
    of the reference front has exactly two recessed runs, z [10.5, 34.5] and
    z [-32.5, -8.5], both spanning the full width. The four published grips are a
    *partition of those two troughs*, not four pockets: edge-8 and edge-14 are the upper
    and lower walls of the upper trough (their reference AABBs meet at z = 23), and
    edge-18 and mono-25 split the lower one;
  - each trough is a stadium: arc centres at x = +/-48 mm. The reference rim radius is
    14 mm (opening height 28 mm); this model widens openings to rim radius **18 mm**
    (opening height 36 mm) so the stadiums read as usable pockets rather than thin
    slots. Centres at z = 23.5 (upper) and z = -21.5 (lower) keep a clear front bar
    between troughs and stay inside |z| <= 49;
  - each trough wall is a **front roll, a straight face, then a roll into the floor** —
    the published MXEdge cross-section (front radius, top face, back radius), not one
    continuous ogee. Sections cut at 0.1 mm through the reference give a face that
    plateaus at 56-58 deg (upper trough) and 65-66 deg (lower), with each roll spanning
    3.5-4 mm of inset:

        upper, x = 0.3   apex 12.50 mm   roll 0->3.5   face 56-58 deg   roll 7.5->11.2
        upper, x = 48    apex 10.06 mm   roll 0->4.0   face 51-55 deg   roll 7.5->11.0
        lower, x = 0.3   apex 16.60 mm   roll 0->4.0   face 65-66 deg   roll 6.5->10.7

    The rolls are progressive rather than circular: the sculpt's osculating radius at the
    rim is under 1.5 mm and grows along the roll, so the rim reaches 30 deg within 1.0 mm
    of inset and reads as a knife edge rather than a bevel;
  - the walls are what the reference renders as one dark band (upper wall, facing down)
    and one bright band (lower wall, facing up) per trough;
  - **the floor is crowned along the trough's length** — deepest at the centre and
    shallower toward the ends, which is the published MXEdge behaviour ("true depth
    varies along length"). The reference wall is one uniform depth scaling of its centre
    profile: at every z the measured depth is depth(x = 0) * (1 - c * (x/48)^2), holding
    to 0.03 mm for c = 0.1952 (upper) and c = 0.1885 (lower). The rim outline itself does
    not change along x. Cutters therefore scale depth by that parabola and leave the
    inset profile alone. The physical / reference upper trough is **one** stadium opening
    with **one** floor (no stepped shelf); MX8 and MX14 are partitions of that trough;
  - measured trough centre depths are 12.5 mm (upper) and 16.5 mm (lower). This model
    uses the published 14 mm / 18 mm instead, so each exported region's depth equals the
    depth board.json publishes. Stated deviation: floors 1.5 mm deeper than measured;
  - the mono is a bore inside the lower trough's right end: measured rim r 10.7 mm at
    (x 48.4, z -20.3), near-cylindrical to a floor of r 9.2 mm. The floor is placed at
    the published 25 mm (measured 27.2 mm);
  - front and back perimeter roll r 4 mm (the measured front face is flat only to
    |z| <= 45 mm), outer corner radius 15 mm. Both come from the reference silhouette:
    a 15 mm corner reproduces its measured max |x| at |z| = 36/40/44/46/48 to 0.25 mm.
* Display material texture embedded from the same reference package.
* Measured approximation of a sculpted display mesh — not manufacturing geometry.

Region partition. `compile_board` requires each region's extent along the depth axis to
equal the published grip depth, and the reference's own nodes do not (its edge-8 node
spans the full upper trough). The upper trough is authored as **one stadium opening with
one crowned floor** at the published 14 mm (x = 0). edge-8 / edge-14 split on z = 24
(0.5 mm above the widened upper centre, same relative placement as the reference meet
line at z = 23 on the measured centre 22.5):

    edge-8   upper trough above z = 24: upper-wall lip only     y [-17, -9]  span  8
    edge-14  upper trough below z = 24: wall + single floor     y [-17, -3]  span 14
    edge-18  lower trough, lower wall, full depth               y [-17, +1]  span 18
    mono-25  lower trough right end + bore incl. floor          y [-17, +8]  span 25

edge-8 is therefore the front 8 mm of the upper wall (the lip actually gripped), not a
second floor. The single upper floor belongs to edge-14.

Floor half-width and wall front radius. Measured apex insets (upper 11.2 mm, lower
11.0 mm) on the reference's r = 14 rim leave a floor half-width of only ~2.8 mm — visually
thin slots. This model sets apex inset **12.0 mm** on both troughs so floor half-width
is **6.0 mm** (TROUGH_RADIUS 18 − inset 12) at the rim — roomier pocket floors in the
5–7 mm target band. Lattice publishes ~10 mm front radius on the physical edge. With
inset 12.0 mm and a 2 mm back roll, a 10 mm front roll does not leave a measurable
straight face on the upper trough. This model uses **9.9 mm** — the largest front radius
≤ 10 mm that still leaves a measurable straight face on both troughs (≥ 2.6 mm upper,
≥ 6.3 mm lower). Stated residual vs Lattice ~10 mm: **0.1 mm**. Preferring the roomier
floor over maximising front radius if the inset budget tightens further. The roll opens
toward the trough's ends under crown depth-scaling (published behaviour: larger front
radius at the ends, smaller at the centre).

Because the floor is crowned, a region's deepest face is the one at x = 0; each of those
spans reaches the published depth there and no deeper.
```

## Recorded constants

```python
PACKAGE = "lattice-mxedge-lift-small"
BOARD_JSON = REPOSITORY / "Hangboards" / PACKAGE / "board.json"
DESTINATION = REPOSITORY / "Hangboards" / PACKAGE / f"{PACKAGE}.FCStd"
BODY_PRIM = "/root/body/Body_actual_surface_001"
Y_FRONT = -17.0
BODY_X = 168.0
BODY_Y = 34.0
BODY_Z = 98.0
HALF_X = BODY_X / 2.0
HALF_Z = BODY_Z / 2.0
Y_BACK = Y_FRONT + BODY_Y
# Outer envelope: 15 mm XZ corners plus a 4 mm roll into the front and back faces.
# Planar facets throughout — an OCCT fillet leaves a tessellation-vs-Area gap at compile.
CORNER_R = 15.0
CORNER_SEGMENTS = 12
CORNER_CENTER_X = HALF_X - CORNER_R
CORNER_CENTER_Z = HALF_Z - CORNER_R
EDGE_ROLL_R = 4.0
EDGE_ROLL_SEGMENTS = 4
GRIP_DEPTH_MM = {
    "edge-18": 18.0,
    "edge-14": 14.0,
    "edge-8": 8.0,
    "mono-25": 25.0,
}
# Stadium openings: arc centres at x = +/-48. Reference rim radius 14 mm; authored 18 mm
# widens each opening to 36 mm tall so pockets read as usable troughs, not thin slots.
TROUGH_HALF_LEN = 48.0
TROUGH_RADIUS = 18.0
# Even, so a vertex lands exactly on z = z_center and no facet straddles the wall that
# divides the trough's two regions.
TROUGH_ARC_SEGMENTS = 14
# Chords of the crowned floor parabola; 10 holds it to under 0.01 mm.
TROUGH_STRAIGHT_SEGMENTS = 10
TROUGHS = {
    "upper": {
        # Nudged +1 mm from measured 22.5 so the r=18 rim keeps a clear front bar vs lower.
        "z_center": 23.5,
        "depth": GRIP_DEPTH_MM["edge-14"],
        "crown_fraction": 0.1952,
        # Floor half-width = TROUGH_RADIUS - apex_inset = 6.0 mm (target 5–7). Measured
        # insets on r=14 left only ~2.8 mm — deliberately widened for usable pocket floors.
        "apex_inset": 12.0,
        # 0.5 mm above z_center (same offset as reference meet line 23 on centre 22.5);
        # partitions the one opening (wall lip vs wall+floor), not two floor levels.
        "split_z": 24.0,
    },
    "lower": {
        # Nudged -1 mm from measured -20.5; pairs with upper centre for a clear front bar.
        "z_center": -21.5,
        "depth": GRIP_DEPTH_MM["edge-18"],
        "crown_fraction": 0.1885,
        "apex_inset": 12.0,
    },
}
# Wall cross-section: front roll, straight face, roll into the floor. The radii are of the
# centre profile; depth-scaling by the crown opens both rolls toward the trough's ends.
# Lattice publishes ~10 mm front; 9.9 mm is the largest ≤10 that still leaves a straight
# face inside the 12.0 mm inset budget with the 2 mm back roll (see module docstring).
WALL_FRONT_RADIUS = 9.9
WALL_BACK_RADIUS = 2.0
# Segment counts per profile zone. The front roll carries the most because it is the band
# whose shading gradient is what reads as the bevel.
WALL_FRONT_SEGMENTS = 9
WALL_FACE_SEGMENTS = 3
WALL_BACK_SEGMENTS = 3
# Cutters start this far in front of the board so no boolean face is coplanar with it.
PROUD_MM = 0.3
# Partition boundaries measured on the reference's own contact nodes.
CONTACT_X_LIMIT = 57.0
MONO_X_MIN = 37.5
MONO_CENTER_X = 48.4
MONO_CENTER_Z = -20.3
MONO_RIM_R = 10.7
MONO_TAPER_R = 10.2
MONO_FLOOR_R = 9.2
MONO_TAPER_DEPTH = 4.0
# Planar n-gon only — a true Cylinder fails compile_board partition (distToShape 1e-4).
MONO_SIDES = 48
NODE_IDS = {
    "body": "Body_actual_surface_001",
    "edge-18": "edge_18_actual_surface_001",
    "edge-14": "edge_14_actual_surface_001",
    "edge-8": "edge_8_actual_surface_001",
    "mono-25": "mono_25_actual_surface_001",
}
MATERIAL_NAME = "neutral_tulipwood"
MATERIAL_BASE_COLOR = "0.72,0.55,0.36"
MATERIAL_ROUGHNESS = 0.58
MATERIAL_METALLIC = 0.0
```

## Inline authoring notes

- `_wall_face_angle()`:
  - Docstring: Angle of the wall's straight face from the front face plane. The wall leaves the rim tangent to the front face, turns through `front_radius` to the face angle t, runs straight, then turns back through `back_radius` tangent to the floor. Each roll displaces the profile by r*(sin t, 1 - cos t), so inset_max = (front_radius + back_radius) sin t + straight cos t depth = (front_radius + back_radius) (1 - cos t) + straight sin t and eliminating `straight` leaves one equation in t, increasing on (0, pi/2): inset_max sin t - depth cos t = (front_radius + back_radius) (1 - cos t)
- `_wall_stations()`:
  - Docstring: (inset mm, depth fraction) stations down one wall of a trough. The inset is authored in millimetres and the depth is carried as a fraction, so a station off the trough's centre takes the same fraction of its own crowned depth. That keeps the wall one uniform depth scaling of its centre profile, which is what the reference measures as, and it opens the rolls toward the trough's ends. When `lip_depth` is set, a station is inserted at fraction lip_depth/depth so a contact boundary can land exactly on a published grip depth at x = 0.
- `_insert_fraction()`:
  - Docstring: Insert a wall station at `target_fraction` by interpolating inset.
- `_loft_solid()`:
  - Docstring: Ruled loft through polygonal sections, capped. Every section shares its arc centres with the others and differs only in radius, so each lateral face is a planar trapezoid and tessellates exactly.
- `_triangle_solid()`:
  - Docstring: Closed solid from an explicit triangle soup, outward-oriented. The crowned trough floor makes a quad between two wall stations non-planar, and a non-planar face would break `compile_board`'s surface-area partition check, which assumes tessellation is exact. Triangles are planar by construction, so the cutter is authored as triangles rather than lofted through polygon wires.
- `_rounded_rect_points()`:
  - Docstring: CCW XZ envelope outline whose corner radius is `radius` (corner centres fixed).
- `_body_solid()`:
  - Docstring: Envelope with 15 mm XZ corners and a 4 mm roll into the front and back faces.
- `_trough_depth()`:
  - Docstring: Local trough depth at a station on the stadium core segment. The reference wall is one uniform depth scaling of its centre profile, so the whole wall — not just the floor — follows this parabola.
- `_stadium_template()`:
  - Docstring: CCW ring of (core_x, outward normal) samples of the stadium's core segment. A point of the outline inset by `s` is `(core_x + (R - s)*nx, z_center + (R - s)*nz)`, so every station reuses one template and corresponding samples stay aligned. The straight runs are subdivided because that is where the crowned floor bends.
- `_ring()`:
  - Docstring: One closed ring of cutter vertices at one station of the wall profile. A station fixes the inset in millimetres and the depth as a *fraction* of the local trough depth rather than as an absolute y, which is what keeps the wall a uniform scaling of the centre profile as the floor crowns.
- `_cap_triangles()`:
  - Docstring: Close a stadium ring with facets that follow the crowned floor. A fan from one centre point would replace the parabolic floor with a cone, so the straight run is bridged strip by strip between its top and bottom samples, which pair up by x. Each end arc's samples all share one core x and therefore one y, so an arc is flat and can be fanned from its own axis point.
- `_trough_cutter()`:
  - Docstring: Stadium trough with a parabolically crowned floor, as planar triangles.
- `_mono_cutter()`:
  - Docstring: Bore inside the lower trough's right end; no Cylinder, planar n-gon only.
  - Stay cylindrical until below the crowned trough floor across the whole bore mouth, so the taper starts in solid material rather than part way across the floor.
- `_is_trough_floor()`:
  - Docstring: True if `face` lies on the crowned trough floor rather than a wall. Floor facets sit in the apex band around z_center and at the local floor depth band. They must go to the deep-side contact (edge-14 / edge-18): a single floor spans the full apex in z and would otherwise straddle the wall split line.
- `_wall_filter()`:
  - Docstring: Match trough faces on one side of the split line, no deeper than `y_max`. The side test is on the face's whole extent, not its centroid. Each x strip of a wall band is one plane, so the boolean can hand back a face spanning a wide z run, and a centroid test would assign it by whichever side a rounding error fell on. A wall face that straddles the split line belongs to neither side and stays with the body, which is also where the reference's own node split leaves it. The single crowned floor is the exception: it spans the apex across the split and belongs to the deep side (the published deeper grip that owns the floor).
- `_mono_filter()`:
  - Docstring: Match the lower trough's right end plus the bore walls and floor.
- `main()`:
  - Rolled envelope is authored into the solid (not a post-cut Shape assign on Part::Cut).
  - Below z = 24: lower wall of the upper trough plus the single crowned floor.
  - Above z = 24: front 8 mm of the upper wall — the lip actually gripped.
  - The reference hands the lower trough's right end to the mono, not to edge-18.
  - Bake into Part::Feature so a later recompute cannot wipe the solid (Part::Cut is Base/Tool).

## Checks the script enforced before saving

Each guard below raised `ValueError` and aborted authoring (source lines verbatim).

```python
if len(names) != 1:
    raise ValueError(f"expected exactly one reference texture, found {names}")
if blend >= inset_max or blend > depth:
    raise ValueError( f"wall rolls {blend} mm do not fit an inset of {inset_max} mm " f"and a depth of {depth} mm" )
if abs(stations[-1][0] - inset_max) > 1e-6 or abs(stations[-1][1] - depth) > 1e-6:
    raise ValueError( f"wall profile ends at {stations[-1]}, expected ({inset_max}, {depth})" )
if not 0.0 < lip_depth < depth:
    raise ValueError(f"lip depth {lip_depth} mm is outside (0, {depth})")
if index == 0:
    raise ValueError(f"lip fraction {target_fraction} is before the rim")
if span <= 0.0:
    raise ValueError("wall stations are not ordered by fraction")
raise ValueError(f"lip fraction {target_fraction} is past the floor")
if not shell.isClosed():
    raise ValueError("triangulated cutter shell is not closed")
if solid.Volume <= 0.0:
    raise ValueError(f"triangulated cutter has non-positive volume {solid.Volume}")
if not faces:
    raise ValueError("no body faces matched the contact predicate")
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
