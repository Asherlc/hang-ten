# metolius-prime-rib CAD authoring provenance

Date: 2026-09-24

This record preserves the provenance carried by the retired one-off migration
script `Tools/HangboardCAD/migration/author_metolius_prime_rib.py`, which authored
`Hangboards/metolius-prime-rib/metolius-prime-rib.FCStd`, together with the
authoring audit that accompanied it
(`docs/source-audits/2026-09-24-metolius-prime-rib-freecad-source.md`, folded in
below and removed). The script was never a build input: the committed FCStd
stands alone, and its embedded `HangTenBoardManifest` is now the source of
`board.json` (`Tools/HangboardCAD/board_manifest.py`). The script was removed
because re-running it would recreate the document without that manifest.

Unlike the five earlier CAD boards, Prime Rib's profile is authored as vector
primitives (11 lines, 12 tangent arcs, two cubic Bezier spans) with named driving
dimensions rather than a measured polyline, and its source opts in to
`HangTenCurvedRegionPartition` (`Tools/HangboardCAD/compile_board.py`).

The board metadata was embedded after authoring with
`Tools/HangboardCAD/set_board_manifest.py`; only `Document.xml` changed, and the
generated `board.json` is byte-identical to the file that was committed at
`657a303df534a7bf324bcd924a0d8f36882bba62`.

Nothing below is new evidence. The module docstring, recorded constants, inline
notes, and pre-save checks are copied from the script so the trail from
published product facts and the measured Git reference to the authored document
survives. Where the script distinguished PUBLISHED values from MEASURED ones, or
recorded a stated deviation, that wording is kept as written. The script read
`board.json` from the package; that file is now generated from the source.

## Recovering the script

- Last commit that modified the script: `657a303df534a7bf324bcd924a0d8f36882bba62`
- Last commit containing the script before its removal: `3498f979355d60553e09fd557b85c87e745c0ba3`

```sh
git show 3498f979355d60553e09fd557b85c87e745c0ba3:Tools/HangboardCAD/migration/author_metolius_prime_rib.py
```

The script imported the shared helper `Tools/HangboardCAD/reference.py`
(`load_reference`, which resolves the approved reference USDZ from Git at the
recorded pre-migration commit) and ran under FreeCAD's interpreter (for example
through `Tools/HangboardCAD/run_freecad.py`), reading extra site directories such
as the one providing `pxr` from `HANGTEN_CAD_PYTHONPATH`. It was run on
conda-forge FreeCAD 1.1.3 (OCCT 7.9.3) on Linux, not the pinned macOS build.

## Module docstring (verbatim)

```text
One-off migration: author Hangboards/metolius-prime-rib/metolius-prime-rib.FCStd natively.

This script is a MIGRATION TOOL, not a build input. The saved FCStd must stand
alone: the shared compiler never runs this file, and nothing here is required to
rebuild the published runtime asset.

Acceptance bar (declared up front): the Prime Rib is a constant cross-section
board (three full-width rungs), so it is a swept profile, not a sculpted shell.
The reference cross-section is constant along X from -252.8 to +252.8 mm with a
1.2 mm round-over on both end perimeters; the only other features in the
reference body are the four flat mounting-bore cap patches left by
``Tools/HangboardModels/mounting_bore_repairs.json`` (x = +/-223 mm), which this
source deliberately does not author (screw-hole/hardware omission policy).

Provenance of every number written into the document:

* PUBLISHED (manufacturer page https://www.metoliusclimbing.com/products/prime-rib,
  "Specs & Details", fetched 2026-09-24; mirrored in ``board.json``):
  size 20" x 4.2" x 1.5" (50.8 x 10.66 x 3.8 cm) -> 508 x 106.68 x 38.1 mm, and
  edge depths 38 / 23 / 15 mm. The 38 mm top edge spans the full 1.5" (38.1 mm)
  board thickness; the compiler's published-depth gate tolerates the 0.1 mm.
* MEASURED from the approved reference asset, resolved from Git (never from the
  live runtime path), and then AUTHORED AS VECTOR PRIMITIVES: the end-cap
  boundary of the reference body is exactly (to <= 0.001 mm on every measured
  vertex) a chain of 11 straight lines, 12 tangent circular arcs and two cubic
  Bezier spans with round-number control points. Those primitives, their
  tangencies and their dimensions are what this script authors; no mesh vertex
  is copied into the sketch. The script re-measures the reference and refuses to
  save if any reference profile vertex lies more than
  ``PROFILE_FIT_TOLERANCE_MM`` from the authored sketch.
* The two top-surface spans (the rear lip and the shallow dip behind the top
  rung's crest) are genuinely free-form in the reference: no circle fits them
  (best single-arc residual 0.3-1.1 mm) but a cubic Bezier with round-number
  poles reproduces every sampled vertex to 6e-5 mm. They are authored as
  Sketcher B-splines (degree 3, clamped, unit weights), i.e. true Beziers, with
  every pole dimensioned. No polyline is used anywhere in the profile.
* Contact runs are the reference contact nodes' own profile runs (each spans
  X -252.8..+252.8, the prismatic span inside the end round-overs):
  edge-15: front face from the bottom round to the 15 mm slot's back-wall fillet;
  edge-23: same for the 23 mm slot; edge-38: front face above the top rung's
  lower nose, the crest, the top surface and the rear top round.
* Display material (``prime_rib_neutral_wood``, roughness 0.58, metallic 0) and
  its texture are carried over from the reference; base colour
  ``0.72,0.55,0.36`` is a stated display choice (same as the pilot).

The result is a measured, vector-authored approximation of a display mesh. It is
NOT recovered manufacturing geometry, and nothing here supports a product-
accuracy or load-bearing claim.

Sketch frame: local (u, v) maps to native (x, y, z) = (0, -u, v). u is the
distance from the back (wall) face toward the front, v the height above the
bottom face, so every authored coordinate and every driving dimension is
positive. Note on Sketcher sign semantics (verified on FreeCAD 1.1.3):
``DistanceX(g1, p1, g2, p2, d)`` solves ``x(g2.p2) - x(g1.p1) = d``, so the
argument ORDER sets the sign; ``DistanceX(point, -1, 1, d)`` therefore puts the
point at x = -d. Every dimension here is written low -> high.
```

## Recorded constants

```python
PACKAGE = "metolius-prime-rib"
BOARD_JSON = REPOSITORY / "Hangboards" / PACKAGE / "board.json"
DESTINATION = REPOSITORY / "Hangboards" / PACKAGE / f"{PACKAGE}.FCStd"
SCRATCH = Path(
    os.environ.get("HANGTEN_CAD_SCRATCH", str(REPOSITORY / ".context" / f"freecad-{PACKAGE}"))
)
BODY_PRIM = "/root/body/body_mesh_001"
CONTACT_PRIMS = {
    "edge-15": "/root/edge_15/edge_15_mesh_001",
    "edge-23": "/root/edge_23/edge_23_mesh_001",
    "edge-38": "/root/edge_38/edge_38_mesh_001",
}
PROFILE_FIT_TOLERANCE_MM = 0.01

# --- Published facts (manufacturer page and board.json) --------------------
INCH = 25.4
BOARD_WIDTH = 20.0 * INCH  # 508.0
BOARD_HEIGHT = 4.2 * INCH  # 106.68
BOARD_THICKNESS = 1.5 * INCH  # 38.1
GRIP_DEPTH_MM = {"edge-38": 38.0, "edge-23": 23.0, "edge-15": 15.0}

# --- Measured, authored as named driving dimensions (mm) --------------------
END_ROUNDOVER_RADIUS = 1.2
EDGE15_LEDGE_HEIGHT = 18.0  # bottom face -> 15 mm edge ledge
EDGE15_SLOT_HEIGHT = 21.0  # 15 mm ledge -> underside of the middle rung
MIDDLE_RUNG_THICKNESS = 18.0  # underside of the middle rung -> 23 mm ledge
EDGE23_SLOT_HEIGHT = 26.0  # 23 mm ledge -> underside of the top rung
REAR_TOP_HEIGHT = 103.0  # top surface height at the back edge
TOP_DIP_JOIN_DEPTH = 6.0  # rear-lip / dip Bezier join, from the back face
RADII = {
    "BackBottomRadius": 2.0,
    "FrontBottomRadius": 2.0,
    "Edge15LipRadius": 2.2,
    "Edge15SlotFloorFilletRadius": 3.4,
    "Edge15SlotCeilingFilletRadius": 3.4,
    "MiddleRungNoseRadius": 2.6,
    "Edge23LipRadius": 3.5,
    "Edge23SlotFloorFilletRadius": 6.0,
    "Edge23SlotCeilingFilletRadius": 6.0,
    "TopRungNoseRadius": 4.0,
    "CrestRadius": 7.5,
    "BackTopRadius": 2.0,
}
# Bezier handle dimensions (pole offsets), measured and rounded to the 0.1 mm the
# reference poles sit on.
REAR_LIP_HANDLE_OUT = 1.1  # rear-top round -> first pole, along u
REAR_LIP_HANDLE_IN = 1.5  # second pole -> dip join, along u
DIP_HANDLE_OUT = 9.0  # dip join -> first dip pole, along u
DIP_HANDLE_DROP = 1.5  # dip join height - first dip pole height
DIP_HANDLE_IN = 6.6  # second dip pole -> crest top, along u

MATERIAL_NAME = "prime_rib_neutral_wood"
MATERIAL_BASE_COLOR = "0.72,0.55,0.36"
MATERIAL_ROUGHNESS = 0.58
MATERIAL_METALLIC = 0.0
```

## Inline authoring notes

- `_derived_profile()`:
  - Docstring: Every profile coordinate, derived from the named dimensions above.
  - G1 at the join: the rear-lip's last handle is collinear with the dip's first.
- `ProfileBuilder.__init__()`:
  - (start_pos, end_pos) in traversal order; sketch arcs are always CCW.
- `ProfileBuilder` (class-level note above `line()`):
  - Lines and Beziers are stored against the (clockwise) traversal, i.e. in the same sense as the sketch's always-CCW convex arcs. An extruded sketch edge's face normal follows the edge's stored direction, so this makes every extruded region face point out of the board except the concave slot fillets, which the region construction reverses explicitly.
- `ProfileBuilder.arc()`:
  - The traversal is clockwise, so a clockwise arc is a convex corner.
- `_author_profile()`:
  - Docstring: Author the closed profile as named, fully constrained vector primitives. Traversal is clockwise in (u, v): up the back face, forward across the top, down the front and back along the bottom.
  - Every joint is G1: an endpoint-to-endpoint Tangent is coincidence plus tangency, so the profile is one smooth closed chain.
  - The three rung fronts are one plane: the front face of the board.
  - Anchor: the back face on the sketch V axis, the bottom face on the H axis.
  - Bezier poles: expose the construction pole circles, then dimension the interior poles. End poles are the curve ends (already constrained above); G1 at each Bezier end fixes the handle directions.
  - On FreeCAD 1.1.3 an endpoint Tangent between a circular arc and a B-spline end leaves the B-spline's end handle free to rotate (one DoF per joint); the Bezier-to-Bezier Tangent does bind. Both arc joints here meet the curve where the arc's tangent is horizontal, so the end handles are levelled explicitly. G1 at every joint is asserted numerically below.
- `main()`:
  - The contact runs include arcs and Bezier spans, so their body triangles are chords of curved faces; opt in to the curved-region partition so the body does not keep a duplicate of each curved hold surface (compile_board).
  - local X -> native -Y (toward the front), local Y -> native +Z, normal -> -X.
  - The sketch's Edge<n> sub-element names follow its Shape.Edges order (the sketch sorts its output into a wire), not the geometry index. Resolve each profile geometry to its shape edge by position; FreeCAD then stores the binding under the geometry's element-map name, so it follows that geometry through later dimension edits (checked by the native checks).
  - The region is the prismatic span of the board: it follows the pad length and stops where the end round-over begins, through native expressions rather than copied constants.
  - A concave fillet's extruded face points into the board; reverse it parametrically (Part::Reverse keeps the Source link) and combine the run into one contact surface.
  - optimalBoundingBox: the plain BoundBox of the filleted body is loose (-38.72 / 107.30 mm) around the end round-over's toroidal patches.
  - Front-plane (XZ) footprint of the band: the region an operator selects.

## Checks the script enforced before saving

Each guard below raised `ValueError` and aborted authoring (source lines verbatim).

```python
if len(names) != 1:
    raise ValueError(f"expected exactly one reference texture, found {names}")
if list(ids) != list(range(count)):
    raise ValueError(f"unexpected sketch geometry ids {ids}")
if len(match) != 1:
    raise ValueError(f"{name} pole {pole} has no unique construction circle")
if status != 0:
    raise ValueError(f"profile sketch failed to solve (status {status})")
if not sketch.FullyConstrained:
    raise ValueError("authored profile sketch is not fully constrained")
if (a - c).Length > 1e-6:
    raise ValueError(f"{b.names[i]} moved while solving: {a} -> {c}")
if out_dir.getAngle(in_dir) > 1e-6:
    raise ValueError(f"{b.names[i]} -> {b.names[j]} is not tangent-continuous")
if published != GRIP_DEPTH_MM:
    raise ValueError(f"board.json depths {published} disagree with {GRIP_DEPTH_MM}")
if board["dimensions"] != "20 × 4.2 × 1.5 in":
    raise ValueError(f"board.json dimensions changed: {board['dimensions']}")
if any(abs(a - e) > 0.01 for a, e in zip(measured_box, expected_box)):
    raise ValueError(f"reference envelope {measured_box} disagrees with published {expected_box}")
if (resolved.multVec(local) - expected).Length > 1e-9:
    raise ValueError("profile sketch frame does not map local (u, v) to native (0, -u, v)")
if fit > PROFILE_FIT_TOLERANCE_MM:
    raise ValueError( f"authored profile deviates {fit:.4f} mm from the reference cross-section " f"(limit {PROFILE_FIT_TOLERANCE_MM} mm)" )
if len(end_edges) != 2 * profile["count"]:
    raise ValueError(f"expected {2 * profile['count']} end-perimeter edges, found {len(end_edges)}")
if not fillet.Shape.isValid() or fillet.Shape.Volume <= 0:
    raise ValueError("end round-over fillet did not produce a valid solid")
if len(matches) != 1:
    raise ValueError(f"{profile['names'][i]} resolves to sketch edges {matches}")
if fillet.Shape.isInside(probe, 1e-6, True):
    raise ValueError(f"{contact_id} has a face whose normal points into the board")
if any(abs(a - e) > 1e-4 for a, e in zip(actual_box, expected_box)):
    raise ValueError(f"authored body frame {actual_box} does not match {expected_box}")
if abs(authored[axis][k] - ref[axis][k]) > 0.01:
    raise ValueError(f"{contact_id} run {authored} disagrees with reference {ref}")
if abs(rbox.YLength - GRIP_DEPTH_MM[contact_id]) > 0.25:
    raise ValueError(f"{contact_id} depth {rbox.YLength:.3f} disagrees with published")
if stale:
    raise ValueError(f"objects failed to recompute: {stale}")
```

## Sources consulted (2026-09-24 authoring audit)

| Source | Reachable | Used for |
| --- | --- | --- |
| https://www.metoliusclimbing.com/products/prime-rib | yes (HTTP 200, 2026-09-24) | "Specs & Details": *Edges Depth: 38 mm (1.49") 23 mm (0.90") 15 mm (0.59")*; *Size: 20" x 4.2" x 1.5" (50.8 cm x 10.66 cm x 3.8 cm)*; *Can be mounted with four screws (included)* |
| https://www.metoliusclimbing.com/products/prime-rib.json | yes | product id 15386925924425, SKU WOOD006, one image |
| https://cdn.shopify.com/s/files/1/0955/0030/4457/files/Prime-Rib-board.jpg?v=1759459292 | yes | visual cross-check only: three full-width rungs labelled 38 / 23 / 15 mm top to bottom, four screw holes, rounded ends. No dimensions were taken from the photo. |
| Pre-migration reference `Hangboards/metolius-prime-rib/assets/primary.usdz` at commit `6b828e15` (`Tools/HangboardCAD/reference.py`), SHA-256 `ddfb6f8f…8026` | yes (Git LFS) | cross-section primitives, contact runs, end round-over, material |
| `Hangboards/metolius-prime-rib/board.json` (committed then; now generated from the FCStd's `HangTenBoardManifest`) | yes | contact ids, names and depths (38 / 23 / 15 mm), `dimensions` "20 × 4.2 × 1.5 in" |

## Field mappings

Native frame: millimetres, +X right, +Z up, front −Y. Sketch local `(u, v)` =
native `(0, −u, v)`.

| Authored field | Value | Source |
| --- | --- | --- |
| Pad `Length` (board width) | 508.0 | manufacturer 20" (board.json) |
| `BoardHeight` | 106.68 | manufacturer 4.2" |
| `BoardThickness` | 38.1 | manufacturer 1.5" |
| `Edge15Depth`, `Edge23Depth` | 15, 23 | manufacturer edge depths (board.json `depth.range`) |
| edge-38 depth | 38.1 (full thickness) | manufacturer 38 mm (1.49") ≈ 1.5" thickness; the reference mesh also spans 38.1. The compiler's published-depth gate allows 0.25 mm. |
| `Edge15LedgeHeight` 18, `Edge15SlotHeight` 21, `MiddleRungThickness` 18, `Edge23SlotHeight` 26 | mm | measured: reference end-cap loop |
| 12 radii (`BackBottomRadius` 2, `FrontBottomRadius` 2, `Edge15LipRadius` 2.2, `Edge15SlotFloor/CeilingFilletRadius` 3.4, `MiddleRungNoseRadius` 2.6, `Edge23LipRadius` 3.5, `Edge23SlotFloor/CeilingFilletRadius` 6, `TopRungNoseRadius` 4, `CrestRadius` 7.5, `BackTopRadius` 2) | mm | measured: reference end-cap loop, exact circle fits |
| Top-surface Beziers: `RearTopHeight` 103, `TopDipJoinDepth` 6, `TopDipJoinHeight` 103, handles 1.1 / 1.5 / 9.0 / 1.5 (drop) / 6.6 | mm | measured: least-squares cubic Bezier fit to the reference top-surface samples (residual 6e-5 mm) |
| `EndRoundover.Radius` | 1.2 | measured: reference end stations x = 252.8…254 follow 1.2·sin θ |
| Contact runs | edge-15: bottom-rung front, lip, ledge, floor fillet. edge-23: middle-rung front, lip, ledge, floor fillet. edge-38: top-rung front, crest, both top Beziers, rear top round | measured: reference contact nodes' (y, z) extents, asserted to 0.01 mm |
| Contact X span | ±252.8 (`Pad.Length − 2·EndRoundover.Radius`) | measured: reference contact nodes |
| `HangTenHoldOutline` | front-plane rectangle of each run's extent | derived from the authored run |
| Node IDs | `body_mesh_001`, `edge_{15,23,38}_mesh_001` | kept from the reference, which `test_approved_board_packages.py` pins |
| Material `prime_rib_neutral_wood`, roughness 0.58, metallic 0, texture `prime-rib-neutral-wood-64199871cb68.png` | — | carried over from the reference USDZ. Base colour `0.72,0.55,0.36` is a stated display choice, as on the pilot. |

## Deliberately not authored

- **The four mounting bores** (x = ±223 mm, z = 28.5 / 70 mm, r = 5.5 mm).
  The repository's hardware-omission policy covers them
  (`docs/source-audits/2026-09-22-mounting-bore-repairs.json`, formerly
  `Tools/HangboardModels/mounting_bore_repairs.json`). The reference still
  carries their flat cap patches, and the native surface is continuous there.

## Verification evidence

- Reference fit: all 291 reference end-cap profile vertices lie within
  0.00006 mm of the authored sketch (the script's limit is 0.01 mm).
- Native checks (`Tools/HangboardCAD/tests/prime_rib_native_source_checks.py`)
  pass, including an `Edge23Depth` 23 → 26 mm edit that moves only edge-23.
- Compile (`compile_board.py`): published-depth gate 15.0 / 23.0 / 38.1 mm.
  Descriptor `facePlaneAABB` matches the reference to within 4e-8
  (normalized). `modelBounds` are identical.
- `compare_exports` against the reference, two-way sampled, limit 0.5 mm:
  - candidate → reference: worst 0.0782 mm over 336,912 samples.
  - reference → candidate: worst 0.0671 mm over 55,020 samples.
  - p99 is 0.014 mm in both directions.
  - Per contact: edge-15 0.0026 mm, edge-23 0.0046 mm, edge-38 0.078 mm.
  The residual is tessellation chord error at the 0.08 mm deflection. At its
  default `--chunk 2048`, the tool's reverse pass was OOM-killed on this
  56k-triangle mesh, so the same functions were run at a smaller chunk; the
  tool now has a `--chunk` option for that.
- Preview: `docs/pr-screenshots/metolius-prime-rib/native-vs-reference-preview.png`.
  This is a CPU lambert render, not a SceneKit screenshot.
- Not run: in-app simulator validation (no macOS here), the Hydra `usdrecord`
  render (the usd-core wheel has no Storm imaging), and suspension. The board
  has no suspension metadata.
