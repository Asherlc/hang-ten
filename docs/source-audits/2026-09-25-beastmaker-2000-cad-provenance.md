# beastmaker-2000 CAD authoring provenance

Date: 2026-09-25

`Hangboards/beastmaker-2000/beastmaker-2000.FCStd` was authored by a throwaway
script under `.context/`, which was not committed (see
`docs/freecad-authoring-migration.md`). The committed FCStd stands alone. Its
embedded `HangTenBoardManifest` is the previously hand-authored `board.json`,
and the regenerated file is byte-identical to it. That includes the top-level
and presentation `aspectRatio` `3.8666664053333437`, which is kept as the
pre-migration value rather than re-derived from the model bounds (580 / 150).

The source is vector geometry only. Every profile is a Sketcher line, circular
arc, or circle. The body is made of extrusions of those sketches, and every
cavity is a ruled loft of capsule or circle sketches cut from the body. There is
no mesh, polyline fit, or faceted solid.

## Dimension source

Unlike the Beastmaker 1000, this board has no generator in Git. Its only
geometry evidence is the approved display mesh, which was imported with the
batch-01/02 model packages (`73d2fff12`). The reference is resolved through
`Tools/HangboardCAD/reference.py` at commit `6b828e15`. That commit follows the
mounting-bore removal (`e89ad9957`), and its SHA-256 is
`f234f39e672c776fb98b0df7c835642e54f9b2e43c3ffad05ec68fae3cee159f`.
The later material strip (`2039505e3`) did not change the geometry.

Every number below was **measured** from that mesh with plane slices, circle
fits, and line fits, then rounded. It is a measured approximation of a display
mesh. It is **not** recovered manufacturing geometry, and nothing here supports
a product-accuracy or load-bearing claim. Mounting holes, countersinks,
hardware, and logos stay omitted under the repository's screw-hole and hardware
omission policy.

The native frame maps the measurement frame (x right, y up, z front, back plane
z = 0) as `X = x`, `Y = -z`, `Z = y`.

## Web cross-reference (2026-09-25)

<https://www.beastmaker.co.uk/products/beastmaker-2000-series> (manufacturer)
lists "580mm X 150mm X 58mm". This agrees with `board.json` `dimensions` and
with the compiled `modelBounds` (580 × 150 × 58 mm). The page's hold inventory
names "45 Degree Slopers", "35 Degree Slopers" and a "20 Degree Sloper", plus a
"22m middle edge" and pocket and mono families. No per-hold positions or depths
are given.

**Recorded conflict:** the reference mesh's top planes measure 40.2°, 33.3° and
20.9° from horizontal (line-fit residual ≤ 0.28 mm). The page does not say how
its angles are measured, so the source keeps the measured display geometry
rather than re-angling the top from a catalogue label. No number was taken from
the page.

## Sourced versus approximated fields

| Field | Status | Evidence |
| --- | --- | --- |
| Face 580 × 150 mm, depth 58 mm | Published | manufacturer page (above); `board.json` `dimensions` |
| 27-contact inventory, kinds, names, capacities, and depths | Carried unchanged from `board.json` | `2026-08-12-beastmaker-board-packages.md` (2026-08-25 conservative cleanup; nested `hold-26`/`hold-27`) |
| Cavity depth equals the published depth (the compiler's published-depth gate) | Published, via `board.json` | every region's native Y extent measures exactly that depth |
| `front-middle-2`/`-8` floors at z = 3 (55 mm) | **Published depth wins over the mesh** | the reference floors sat at z = 7.05, which is 50.95 mm deep |
| `front-middle-5` floor at z = 8 (50 mm) | **Published depth wins over the mesh** | the reference floor sat at z = 9.06, which is 48.94 mm deep |
| Section: back z = 0, bottom y = 0, lower face z = 37, step soffit y = 43, upper face z = 58, top y = 150 | Measured | plane fits (±0.1 mm) at seven x stations |
| Rounds: back-bottom r 12 at (12, 12); back-top r 12 at (12, 138); front-bottom r 1.5; step r 4.5 at (41.5, 38.5); soffit-to-face r 1.5 | Measured | circle fits (residual ≤ 0.03 mm), consistent at every station |
| Top slopes: each line passes through (z 0, y 156) and meets z = 58 at y 107.0 (outer), 117.9 (second), 133.7 (centre) | Measured | line fits over 23 stations per segment |
| Front-top rounds r 4 / 6 / 4 (outer / second / centre) | Measured | circle fits |
| Top segments: outer \|x\| 190–290, second 90–190, centre \|x\| < 90; centre has a flat top at y 150 back to the slope | Measured | front-view and plan slices |
| Step walls between top segments | **Sharp** | the reference has ~2 mm convex and concave rounds there. This is a stated display simplification |
| End rounds r 12 on the end↔back, end↔bottom, and end↔58 mm-face edges; end↔lower face and end↔top slope sharp | Measured | ray casts at 15 × 15 stations match r 12 to ≤ 0.3 mm |
| End round representation | **Three-prism intersection** | a plan-view and a front-view r 12 rounded rectangle trim the extruded sections. The reference corners are spherical, and the trim differs by up to ~0.7 mm there |
| Pocket centres: ±240, ±179, ±134, ±77, 0 (lower y 23.5, middle y 73), ±41 (upper y 108) | Measured | slice extents; symmetric to ≤ 0.02 mm |
| Pocket wall radii (lower 9.35, middle 9.75, circles 9.3, `front-middle-5` 8.9, upper 10.15) and straight half-lengths | Measured | mid-depth slice extents |
| Nested holes `hold-26`/`-27`: circle r 8.9 at x ±123 from the parent floor (z 23) to z 8 | Measured | circle fits (residual ≤ 0.09 mm) |
| Mouth rounds 1.7 / 2.0 / 1.8 / 3.0 / 1.9 mm and floor rounds 3.0 / 3.5 / 2.4 / 3.4 / 3.0 mm | Measured size, **represented as 45° chamfers** | growth-curve fits; chamfers follow the Beastmaker 1000 and Deluxe II precedent (lessons §15, §16) |
| Material | None | model material policy (`AGENTS.md`): `MaterialName` is empty and the USDZ ships unbound meshes |
| Node IDs (`BoardBody_surface_001_001_001_001` body, `<contact>_surface_001_001_002_002` contacts) | Carried | reference descriptor; every contact keeps its node ID |

## Document structure

Document properties: `HangTenSchemaVersion` 1, `HangTenPresentationID`
`primary`, `HangTenSourceKind` `native-parametric-measured-profile`,
`HangTenCoordinateFrame` `freecad-mm-z-up-front-negative-y`,
`HangTenTessellationDeflection` 0.05, and `HangTenCurvedRegionPartition` true.
The partition flag is needed because the front-top rounds are cylinders and the
cavity chamfers are cones.

- `SectionOuterLeft`, `SectionSecondLeft`, `SectionCentre`, `SectionSecondRight`,
  `SectionOuterRight`: blocked section sketches of lines and arcs, each extruded
  over its x span (`Segment*`, `Part::Extrusion`). The outer spans run 1 mm past
  x = ±290 so that the trim defines the ends. They are fused by `SectionBody`
  (`Part::MultiFuse`, `Refine = False`).
- `OutlinePlan` (x–y) and `OutlineFront` (x–z) are r 12 rounded-rectangle
  sketches, extruded as `OutlinePlanPrism` and `OutlineFrontPrism`.
  `OutlineTrim` (`Part::MultiCommon`) keeps the body inside both.
- `Capsule_<hold>_0..3` and `Cutter_<hold>`: for each of the 20 cavities, a ruled
  `Part::Loft` of four capsule (or circle) sketches:
  1. the mouth grown by chamfer + 1 mm, 1 mm in front of the face;
  2. the nominal outline one chamfer behind the face;
  3. the nominal outline one floor chamfer above the floor;
  4. the outline shrunk by the floor chamfer, at the floor.

  `Cutter_hold_26`/`_27` are five-section circle lofts from 1 mm above the parent
  floor down to z = 8. `HoldCutters` fuses the cutters, and `BoardBody`
  (`Part::Cut`) is the exported body node.
- 27 `Contact_*` `Part::Feature` objects. Each is a copy of the body faces its
  hold owns and carries `NodeID`, `ContactID`, and `HangTenHoldOutline`:
  - A cavity owns every body face on its cutter's shell. The outline is the
    mouth grown by its chamfer.
  - `hold-26`/`-27` own their hole faces plus the parent pocket's non-planar
    end-cap faces on the hole side (mouth chamfer, wall, and floor chamfer).
    The parent keeps its floor, straight walls, and far end cap. This gives the
    nested hold a region from the face to its floor, so the published 50 mm
    depth gates. The outline is the parent end-cap circle (r 9.75) at the hole
    centre.
  - A top sloper owns the slope plane and front-top round faces in its x span.
    Its outline is the front-view band from the round's face tangent up to the
    crest, lowered by the r 12 corner at the board ends.

  Because these are static copies, editing a cutter moves the body but not its
  contact object. The published-depth gate catches that mismatch. The
  sketch-edit-propagation suite is not claimed.

## Evidence

- Compile: 36,890 triangles (reference 22,941), `modelBounds` 580 × 150 × 58 mm,
  and every published-depth gate exact. `verify_reproducible.py` rebuilds it
  byte-identically on the pinned toolchain (FreeCAD 1.1.3, macOS arm64).
- Descriptor `facePlaneAABB` against the reference: every cavity is within
  0.82 mm. The slopers are within 2.94 mm, because the outline now starts at
  the front-top round's tangent on the face rather than partway up the round.
  All 28 node IDs are unchanged.
- `compare_exports` two-way sampled worst deviation: 4.05 mm (candidate to
  reference 3.53 mm; limit 0.5 mm). **Accepted deviation** per
  `docs/freecad-authoring-migration.md`, where it is evidence, not a gate. It
  comes from:
  - the pockets deepened to their published depths;
  - chamfers standing in for the rounds;
  - the sharp segment steps;
  - the three-prism end trim.
- Winding: in the reference, the deep holes and pockets on the right half render
  black in `preview.py` (reversed winding). Every node of the new asset faces
  outward.
- In app: iPhone 17 Pro simulator (iOS 26.5), Debug board-detail review route,
  in a workspace-owned simulator that was deleted afterwards. Four holds were
  selected and confirmed via `boardDetail.selectedHold.<id>`:
  - `top-sloper-1`, the default selection;
  - `top-sloper-2`, `front-middle-5`, and `hold-26`, by deep link. `hold-26`
    highlights as the hole at the right end of `front-middle-3`.

  An A/B build of the prior commit on the same route showed the old asset as a
  dark, artifact-heavy mesh. The new asset renders cleanly, with deep cavities
  shaded dark by the default lighting.
- Not verified: suspension, accessibility, and performance.
