# beastmaker-1000 CAD authoring provenance

Date: 2026-09-25

`Hangboards/beastmaker-1000/beastmaker-1000.FCStd` was authored by a throwaway
script under `.context/`, which was not committed (see
`docs/freecad-authoring-migration.md`). The committed FCStd stands alone. Its
embedded `HangTenBoardManifest` is the previously hand-authored `board.json`,
and the regenerated file is byte-identical to it. That includes the top-level
and presentation `aspectRatio` `3.861003861003861`, which is kept as the
pre-migration value rather than re-derived from the model bounds (580 / 150).

The source is vector geometry only. Every profile is a Sketcher line, circular
arc, ellipse, or cubic Bézier. The body is made from extrusions and ruled lofts
of those sketches, and every pocket is a ruled loft of capsule sketches cut
from the body. There is no mesh, polyline fit, or faceted solid.

## Dimension source

The approved pre-migration asset was generated from explicit numbers, not
traced from images. Its generator is the retired Blender script
`Tools/HangboardModels/beastmaker_1000.py`, which labels every number an
analytic display estimate:

```sh
git show 830d07d58^:Tools/HangboardModels/beastmaker_1000.py
```

Its frame is millimetres, X right (0..580), Y up (0..150), and Z depth (0 at
the back, 58 at the front). The native FreeCAD frame is
`X = x - 290`, `Y = -z`, `Z = y`, so every number below was carried over with
only that rigid transform. The reference USDZ (`reference.py` commit
`6b828e15`, SHA-256
`4f9690d8969dddf8178ef4f7961c05115ab00266821e11982284ff8437b2ac6e`) was used
only as a comparison. Mounting holes, countersinks, hardware, and logos stay
omitted under the repository's screw-hole/hardware omission policy.

## Web cross-reference (2026-09-25)

<https://www.beastmaker.co.uk/products/beastmaker-1000-series> (manufacturer)
lists "580mm X 150mm Height X 5mm". It also lists 2 jugs, 35° and 20° slopers,
and pocket families including "2 Small 4 Finger Pockets (10mm)". The 580 × 150
mm face agrees with `board.json` `dimensions` and with the model bounds. The
"5mm" figure is still the known conflict recorded in
`2026-08-12-beastmaker-board-packages.md`: it is not a thickness fact, and the
58 mm depth remains the qualified shared-layout ruling carried by the
generator. No other number was taken from the page.

## Sourced versus approximated fields

| Field | Status | Evidence |
| --- | --- | --- |
| Face 580 × 150 mm; `board.json` `dimensions` `580 × 150 mm` | Published | manufacturer product page (above) |
| 22-contact inventory, kinds, names, and per-contact depths (10 / 30 / 45 / 50 / 20 / 25 mm) | Carried unchanged from `board.json` | ledger and mapping in `2026-08-12-beastmaker-board-packages.md` (2026-08-25 certification, 2026-08-26 correction) |
| Pocket cavity depth equals the published depth (the compiler's published-depth gate) | Published, via `board.json` | every region's Y extent measures exactly that depth (report below) |
| 58 mm body depth | Retained ruling | generator `D`; qualified Beech/shared-layout ruling, not a manufacturer thickness |
| Section profile: back plane, 3 mm back-bottom roll, 8 mm front-bottom roll, lower face at z = 41 (y 8..40), 3 mm step fillet, step soffit at y = 43, 4 mm upper roll, upper face at z = 58 | Retained estimate | generator `body_section` |
| Jug section: two cubic Béziers `(140,0) (141,10) (150,14) (150,27)` and `(150,27) (150,45) (137,58) (124,58)` in (y, z) | Retained estimate | generator `jug_section`; its Bézier control points are used directly as sketch poles |
| Sloper sections: nominal 35° and 20° lines with a 6 mm front roll | Angles published (product page); roll is a retained estimate | generator `sloper_section`. The 6 mm roll arc is authored as a cubic Bézier (standard 4/3·tan(θ/4) handles, under 0.002 mm from the circle), so that all top sections share one topology for the ruled lofts |
| Top region spans: body end x < 25; jug to 115.5; 35° sloper to 215.5; centre sloper to 364.5 (mirrored) | Retained estimate | generator `top_id` (116 / 215.5 boundaries). 115.5 is the midpoint of the 111–120 transition, so each loft half is a whole face |
| Top transitions: x = 111–120 (jug to 35°) and 212–219 (35° to 20°) | Retained span; **ruled rather than smoothstep** | the generator blends with `smoothstep`; the source uses ruled lofts through an exact mid section (averaged Bézier poles). This is a stated display choice |
| Front outline: straight top and bottom, elliptical ends with 65 mm horizontal and 75 mm vertical half-axes | Retained estimate | generator end silhouette (`sy`), authored as a trim by a sketched ellipse rather than a per-vertex scale |
| Pocket centres, throat widths, and 22 mm height | Retained estimate | generator `pocket_specs` |
| 2.8 mm mouth and floor blend up to 4 mm (`min(4, depth/3)`) | Retained size, **represented as 45° chamfers** | the generator's rounds are authored as chamfer lofts of the same size, following the Deluxe II precedent (lessons §15, §16). This is a stated display choice |
| Step end taper (30 mm) and 6 mm front-to-back end roll (`step_sy`, `sz`) | **Omitted** | the step runs straight to the elliptical end, and the end cap is a sharp-edged elliptical wall. This is the main visible difference from the reference (side view) |
| Material `canonical_neutral_wood`, base colour 0.69, 0.49, 0.28, roughness 0.62, metallic 0, texture `canonical-neutral-wood.png` | Carried as compile-time source metadata only | same texture bytes (`fdab3b78…`) as the reference USDZ and Compact II. Under the model material policy (`AGENTS.md`), `compile_board.py` validates these properties but writes every mesh unbound, so the USDZ ships with no material or texture |
| Node IDs `BeastmakerBody_023_001_001` (body) and `BeastmakerBody_024..045_001_002` (contacts) | Carried | reference descriptor; every contact keeps its node ID |

## Document structure

Document properties: `HangTenSchemaVersion` 1, `HangTenPresentationID`
`primary`, `HangTenSourceKind` `native-parametric-measured-profile`,
`HangTenCoordinateFrame` `freecad-mm-z-up-front-negative-y`,
`HangTenTessellationDeflection` 0.05, and `HangTenCurvedRegionPartition` true.
The partition is needed because the top holds are B-spline and ruled surfaces
and the pocket chamfers are cones.

- `Section00`..`Section14`: 15 blocked Sketcher section profiles on x planes
  (11 edges each: lines, arcs, and two Bézier top curves). The jug, 35°, and
  20° sections come from the generator. The two transition mid sections
  (`JugSloper35Mid`, `Sloper35Sloper20Mid`) are the pole averages.
- `Segment00`..`Segment14`: `Part::Extrusion` along +X where adjacent sections
  are the same, and ruled `Part::Loft` where they differ. They are fused by
  `SectionBody` (`Part::MultiFuse`, `Refine = False`), so the top-region
  boundaries are real edges.
- `OutlineMiddle`, `OutlineEndLeft`, and `OutlineEndRight` are sketches
  (rectangle and two ellipses) extruded through the depth and fused as
  `OutlinePrism`. `OutlineTrim` (`Part::Common`) keeps the body inside them.
- `Capsule_<hold>_0..3` and `Cutter_<hold>`: for each of the 17 cavities, a
  ruled `Part::Loft` of four capsule sketches. They are the mouth grown by
  2.8 mm, 1 mm in front of the face; the nominal capsule 2.8 mm behind the
  face; the nominal capsule at `floor - back`; and the capsule shrunk by `back`
  at the floor. `HoldCutters` fuses them, and `BoardBody` (`Part::Cut`) is the
  exported body node.
- 22 `Contact_*` `Part::Feature` objects, each a copy of the body faces its
  hold owns, carrying `NodeID`, `ContactID`, and `HangTenHoldOutline`:
  - A cavity owns every body face that lies on its cutter's surface (13 faces:
    mouth chamfer, wall, floor chamfer, and floor). Its outline is the mouth
    capsule grown by 2.8 mm.
  - A top hold owns the up-facing top faces within its x span, excluding the
    elliptical end caps. Its outline is the front-view band between the front
    top edge (linear across the lofts) and the crest (150 mm, or the ellipse
    near the ends).

  Because these are static copies, editing a cutter moves the body but not its
  contact object; the published-depth gate catches that mismatch. The
  sketch-edit-propagation suite is not claimed.

## Evidence

- Compile: 48,810 triangles, `modelBounds` 580 × 150 × 58 mm, and every
  published-depth gate exact (10 / 30 / 45 / 50 / 20 / 25 mm).
  `verify_reproducible.py` rebuilds it byte-identically on the pinned toolchain
  (FreeCAD 1.1.3, macOS), with the clay (unbound-mesh) compiler.
- Descriptor `facePlaneAABB` against the reference: every cavity is within
  0.16 mm, the jugs within 0.58 mm, and the slopers within 0.68 mm. All 22
  node IDs are unchanged.
- `compare_exports` two-way sampled worst deviation: 8.65 mm (reverse 7.07 mm; limit 0.5 mm;
  17,284 reference vs 48,810 candidate triangles). The reference is
  left-origin (x 0..580) and the CAD source is centred like every other CAD
  board, so a scratch copy of the reference was shifted by −290 mm in x first;
  unshifted, the tool reports that 290 mm offset..
  **Accepted deviation:** the reference is a subdivided display mesh of the
  same generator (later rounded in #427). The difference comes from the
  omitted end roll and step taper, chamfers standing in for rounds, and ruled
  rather than smoothstep transitions. Per `docs/freecad-authoring-migration.md`
  this is evidence, not a gate.
- Winding: in the reference, `pocket-top-outer-left` (`_040`) and
  `pocket-bottom-mid-right` (`_029`) have reversed triangle winding (0–1% of
  triangles face the front), so they render black in `preview.py`. Every node
  of the new asset faces outward.
- In app (checked on the pre-clay build, which carried the wood texture; the geometry, node IDs, and descriptor regions are unchanged by the clay compile): iPhone 17 Pro simulator (iOS 26.5), Debug board-detail review route, in a
  workspace-owned simulator that was deleted afterwards. The wood texture
  renders. Three holds were each selected and confirmed via
  `boardDetail.selectedHold.<id>`:
  - `jug-left`, the default selection, which highlights the jug top;
  - `sloper-center`, by deep link, which highlights as one band between the
    two 35° slopers;
  - `pocket-bottom-mid-right`, by tapping the model, which highlights as one
    capsule, walls and chamfers included. This is one of the two holds whose
    winding was reversed in the reference.
- Not verified: suspension, accessibility, and performance.
