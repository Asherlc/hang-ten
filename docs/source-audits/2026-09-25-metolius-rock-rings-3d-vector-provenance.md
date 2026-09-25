# metolius-rock-rings-3d vector source provenance

Date: 2026-09-25

This record covers the re-authoring of
`Hangboards/metolius-rock-rings-3d/metolius-rock-rings-3d.FCStd` from measured
polylines to vector primitives. It supersedes the geometry described in
[`2026-09-24-metolius-rock-rings-3d-cad-provenance.md`](2026-09-24-metolius-rock-rings-3d-cad-provenance.md).
That record still describes where the previous source came from. The board
metadata did not change: the `HangTenBoardManifest` was re-embedded with
`Tools/HangboardCAD/set_board_manifest.py`, and the generated `board.json` is
byte-identical to the one generated before this change.

The one-off authoring script was run from `.context/` and is not committed,
following `docs/freecad-authoring-migration.md`. Its constants, construction
and pre-save checks are recorded below. The committed FCStd stands alone.

## What changed

| Feature | Previous source | Vector source |
| --- | --- | --- |
| Outline | 70-segment measured polyline, top chord bowed 3 mm | 14 cubic Beziers (7 per side) with integer poles. The right half is dimensioned and the left half is held by `Symmetric` constraints |
| Pockets | Ruled loft between two 48-gon sections (opening, floor) | Six stadium stations per pocket, smooth loft. The inner stations follow the opening and floor by expressions |
| Jug | 1 mm recess in the front face, z 66..77 | The crown hump between the ears, split off the rounded solid (see "Jug") |
| Lateral cord windows | Straight extrusion of a 16-gon mouth | Ruled loft of ellipses (flared, blind). The left side is bound to the right side by expressions |
| Roof cord exits | Straight extrusion of a 10-gon mouth | Ruled loft of circles (flared, blind). The left side is bound to the right side by expressions |
| Body | `Part::Extrusion` and one 6 mm `Part::Fillet` | A PartDesign body (`Solid`): a symmetric `Pad` and two 6 mm `PartDesign::Fillet`s, front then back. OCCT fails to round both perimeters in one pass because of the kinks and the ear crease |
| Recess cuts | A chain of `Part::Cut` | One `Part::MultiFuse` of all tools (including the jug split box) and one `Part::Cut` (`Body`). Each cut stores a full body copy in the FCStd |
| Curved partition | off | `HangTenCurvedRegionPartition = True`, because the pocket, tunnel and crown surfaces are curved |

## Evidence

- Reference: `Hangboards/metolius-rock-rings-3d/assets/primary.usdz` at
  `6b828e156d4e14ec4a8aa0e3b8f17212336be7bc`, resolved with
  `Tools/HangboardCAD/reference.py`. SHA-256
  `4af718e4c5f1177dce1e440372af6975c0da0c3263e8cc3ea275b9173e956218`.
- Published facts: 184 × 146 × 57 mm, and pocket depths 40 / 32 / 25 mm
  (manifest `dimensions` and contact `depth.range`). Source: Metolius product page
  <https://www.metoliusclimbing.com/collections/training-equipment/products/rock-rings-3d>
  (source register `RR1`, `docs/source-audits/2026-09-20-hangboards-batch-04-model-imports/evidence/metolius-rock-rings-3d/source-register.json`).
- Product photographs, used for visual cross-checks only (no dimensions taken):
  the manufacturer photograph `RR3` (`Rock-Rings-black-white.jpg`) and the owner
  photographs `RR6` / `RR7` in the same evidence directory.

## Measured primitives

All values are native millimetres: +X right, +Z up, front −Y.

### Outline (fits the reference to 0.003 mm)

The reference side wall (every vertex of the y = +22.5 station, where the
perimeter round starts) is exactly a chain of cubic Beziers. Each span is
sampled at 12 uniform parameter steps, and the least-squares residual is about
5e-6 mm. Right half, bottom centre to crown centre:

| Span | Poles (x, z) |
| --- | --- |
| BaseFlat | (0, −92) (8, −92) (15, −92) (22, −90) |
| BaseCorner | (22, −90) (38, −86) (43, −71) (49, −43) |
| LowerFlank | (49, −43) (55, −17) (59, 6) (65, 19) |
| UpperFlank | (65, 19) (73, 35) (73, 57) (73, 76) |
| EarShoulder | (73, 76) (73, 87) (69, 92) (60, 92) |
| EarTail | (60, 92) (53, 92) (51, 83) (46, 83) |
| Crown | (46, 83) (38, 85) (18, 87) (0, 87) |

The crown spans come from the y = −22.5 station of the reference jug node,
where they fit exactly. The joins at (22, −90), (49, −43) and (65, 19) have
1–2° kinks in the reference data. They are kept as authored rather than forced
tangent. The join at (46, 83) is the ear crease. The outline's extremes are the
published 146 × 184 mm envelope.

Named dimensions: `<Span>P<k>X` / `<Span>P<k>Z` for each right-hand pole (Z is
stored as z + 92, so every value is positive), and `CrownP3Z`.

### Pockets (every station fits the reference to within 0.012 mm)

Each pocket is six stadium stations. Station k is the opening inset by
(0, 1.5, 3, 4.5, 6.5, 10) mm, placed at fraction (0, 0.05, 0.13, 0.74, 0.9, 1)
of the depth from the opening (y = −28.5) to the floor. The same insets and
fractions fit all three pockets exactly.

| Slot | Opening centre z | Opening half-width | Opening radius (half-height) | Published depth |
| --- | --- | --- | --- | --- |
| pocket-25 | −61 | 25 | 14 | 25 |
| pocket-32 | −19 | 38 | 16 | 32 |
| pocket-40 | 35 | 51 | 19 | 40 |

One reference vertex, (−4.750, −28.5, −74.988), sits 0.0117 mm inside
pocket-25's straight bottom edge (a T-junction in the reference mesh). This is
why the fit gate is 0.012 mm. Every other checked vertex is within 0.005 mm.

The reference joins the stations with straight facets. This source lofts them
smoothly (`Ruled = False`), which is a **stated display choice**: the surface
passes through every measured station and rounds the rim and floor blend
between them, as the photographed pockets do. The surface between stations is
not measured.

The inner stations are parametric. Each one's `Radius`, `StraightLength` and
`CentreHeight` are expressions on the opening sketch. Its `Placement.Base.y` is
an expression on the opening and floor placements. Moving `Floor_<slot>`
therefore carries the whole pocket with it.

### Cord tunnels (fit the reference to within 0.005 mm)

- Lateral window: ellipses centred at (y 0, z 48), semi-axes 1.4k × k, with k =
  7.8 / 9.2 / 10 at x = 65 / 68 / 71.5. The tunnel is blind at x = 65. A
  construction station at x = 75 (k = 10) carries it through the side wall.
- Roof exit: circles centred at (x 62, y 0), with r = 3.5 / 3.5 / 4.5 at z =
  84 / 88 / 91. The tunnel is blind at z = 84. A construction station at z = 94
  (r = 4.5) carries it through the ear.
- The left side uses its own sketches, bound to the right-hand sketches by
  expressions. `Part::Mirroring` was tried and rejected: the mirrored B-spline
  walls face into the body. The lateral left walls are reversed with
  `Part::Reverse` after clipping, because `Part::Common` drops a reversed
  B-spline face's orientation.

### Jug

The jug is the crown hump the fingers wrap over. It is the part of the rounded
solid (`Solid`) above z = 76 and within the ear creases (|x| ≤ 46), taken as a
`Part::Common` with a box (`JugSelector`). The same box is part of the body's
recess cut, so the body and the jug meet on the box planes. It therefore
includes the crown top and both 6 mm round-overs along the crown, plus the
top 5 mm of the flat front and back faces at the centre. That is what makes the
hold visible from the front. The reference jug's front-face boundary is similar
(z ≈ 77.6 at the creases to 81.3 at the centre).

- z = 76 is 1 mm below the point where the front round-over meets the ear
  crease (83 − 6 = 77). A split at exactly 77 is tangent to the round there,
  and OCCT returns an invalid solid.
- The seam faces on the box planes are internal. The jug's seam faces point
  into the body, are coincident with the body's own seam faces, and are hidden
  inside the board (the body's are claimed by the jug in the partition).
- A geometric split was chosen over binding the crown faces by name. A
  `SubShapeBinder` on the rounded solid's crown faces lost its element-map names
  after a crown edit, even though the topology was unchanged, and silently fell
  back to the whole solid (48 faces). This happened on both `Part::Fillet` and
  `PartDesign::Fillet`. The split has no names to lose. The native checks edit
  the crown (`CrownP3Z` 87 → 86 mm) and require the jug to follow it with the
  same 15 faces.

The reference mesh has something else here: a stepped scoop cut down into the
top from behind. The scoop is stadiums centred at y = 21, at z = 66 / 67 / 71 /
78, with half-width 28.5 / 34 / 42 / 48.5 and radius 9 / 14 / 19.5 / 23.5. That
data fits exactly. **It is not authored**, because the product is a convex hump
there. The manufacturer photograph `RR3` and the owner photographs `RR6` / `RR7`
show a rounded top between the ears, and neither shows a recess opening through
the back. The product owner also confirmed that it is "not a scoop … more like
a hump". The hump's width profile (the crown Beziers) is measured. Its
front-to-back profile is the flat depth plus the measured 6 mm perimeter
rounds, and no further doming is invented.

The jug's `HangTenHoldOutline` keeps the previous tap target (x ±50.3471,
z 66..87), so the jug's descriptor `facePlaneAABB` and `center` are unchanged.

### Unchanged

The 6 mm perimeter round (reference stations 22.5 + 6·sin θ), the 57 mm
depth, the material (`neutral_resin`, 0.82 / 0.80 / 0.76, roughness 0.45), the
0.08 mm tessellation deflection, the node IDs, the slot IDs and the manifest.

## Checks the script enforced before saving

- Every sketch solves (`status 0`) and is `FullyConstrained`. No Bezier pole
  moves while solving.
- The published dimensions (`184 × 146 × 57 mm`) and depths (25 / 32 / 40)
  match the manifest.
- Reference fit: the outline side wall, the crown, every pocket station, and the
  right and left tunnel stations are all within 0.012 mm.
- Each perimeter fillet rounds exactly 14 edges and yields a valid solid.
- Every object recomputes cleanly.
- Every exported region face points out of the board (a probe 0.3 mm along the
  face normal lies outside the solid). The jug's internal seam faces are exempt.
- Each pocket region's depth equals its published depth within 0.01 mm.
- The body's optimal bounding box is the published envelope within 0.001 mm.

## Verification

- Native checks (`Tools/HangboardCAD/tests/metolius_native_source_checks.py`):
  all pass. New checks cover the following, and the previous source fails them:
  every sketch is fully constrained; the outline is 14 cubic Beziers; no sketch
  is a polyline; every region faces out of the board; the jug covers the
  crown's round-overs; the inner pocket stations follow a floor edit; a
  right-hand outline edit (`LowerFlankP1X` 55 → 53) is mirrored on the left;
  and the jug follows a crown edit (`CrownP3Z` 87 → 86).
- Compile (`compile_board.py`, FreeCAD 1.1.3 macOS arm64, OCCT 7.8.1, the
  pinned toolchain): published-depth gate 25 / 32 / 40 mm. There are 87,789
  triangles (body 45,166, jug 18,832, pockets 5,622 / 6,410 / 7,218, lateral
  2,026, roof 2,515) and the asset is 1.95 MB. The previous source had 15,783
  triangles and 314 KB, and the reference has 8,742 triangles. The growth is
  OCCT's tessellation of the B-spline fillet faces at the pinned 0.08 mm
  deflection (compare migration trap 15). The FCStd is 7.4 MB, up from 1.3 MB,
  for the same reason: the fillet surfaces are stored in `BackRound`, `Body`
  and `Region_jug`.
- `verify_reproducible.py`: this board rebuilds byte-identically on the pinned
  toolchain.
- Descriptor against the previous one: `modelBounds` and the node inventory are
  identical. The jug `facePlaneAABB` is identical. The pocket `facePlaneAABB`
  values move by at most 0.0016 (normalised), and the pocket centres are now
  exactly x = 0.5 (previously 0.4997–0.49998).
- `compare_exports` against the reference (two-way sampled, `--chunk 256`):
  candidate → reference worst 20.999 mm over 526,734 samples, reference →
  candidate worst 10.000 mm over 52,452 samples. It fails the 0.5 mm limit, as
  expected, because of the deliberate jug change. A per-node nearest-point check
  (0.1 mm reference sampling) attributes the deviation:
  - lateral window ≤ 0.15 mm and roof exit ≤ 0.15 mm in both directions;
  - pockets ≤ 0.91 mm (p99 0.87), which is the smooth loft between the exact
    stations against the reference's facets;
  - jug ≤ 21.0 mm and body ≤ 10.0 mm, where the reference's scoop (floor
    z = 66) is now the solid crown hump (top z = 87);
  - body, reference → candidate: ≤ 1.9 mm (p99 0.36).
  This is evidence, not a gate (`docs/freecad-authoring-migration.md`,
  "Accepted deviation").
- Render: `docs/pr-screenshots/metolius-rock-rings-3d/previous-vector-reference.png`.
  Rows are the previous source, the vector source and the reference. Columns are
  front, front three-quarter, back three-quarter and top, with the jug in orange.
  It is a CPU z-buffer diagnostic render, not a SceneKit screenshot.
- Not run: in-app simulator validation, the Hydra `usdrecord` render, and the
  suspension audit. The suspension is package metadata and is unchanged. The
  cord windows and exits keep their positions.
