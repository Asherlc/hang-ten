# target10a-linebreaker-base CAD authoring provenance

Date: 2026-09-25

`Hangboards/target10a-linebreaker-base/target10a-linebreaker-base.FCStd` was
authored by a throwaway script under `.context/`, which was not committed (see
`docs/freecad-authoring-migration.md`). The committed FCStd stands alone. Its
embedded `HangTenBoardManifest` is the previously hand-authored `board.json`,
and the regenerated file was byte-identical to it before one deliberate change:
the presentation `aspectRatio` is now `3.8666664053333437`, the new
`modelBounds` x/y ratio (580 × 150 mm). The old value, `3.885558901066122`, was
the bounds ratio of the smoothed reference (578.9 × 149.0 mm).
`test_fixed_front_model_presentation_ratios_match_descriptor_bounds` requires
the two to agree for this package. The top-level `aspectRatio` (`4/3`) is
unchanged.

The source is vector geometry only. Every profile is a blocked Sketcher
polygon or a capsule of two lines and two tangent arcs. The body is made from
extrusions, cuts, two sequential `Part::Fillet` rim rounds, and ruled capsule
lofts. There is no mesh, polyline fit, or faceted solid.

## Dimension source

The approved pre-migration asset was generated from explicit numbers, not
traced from images. Its generator is the retained batch-01 signed-distance
source. Its numeric configuration and geometry module can be read with:

```sh
git show 2dd5182b4:.context/migration/source/hangboards-batch-01/models/target10a-linebreaker-base/source/geometry-config.json
git show 2dd5182b4:.context/migration/source/hangboards-batch-01/models/target10a-linebreaker-base/source/geometry.py
git show da2a18af1:.context/migration/target10a-linebreaker-base/contact-mapping.json
```

The generator frame is millimetres, X right, Y toward the back (front face at
y = −55, back at y = 0), and Z up (bottom at z = 0). That is already the native
FreeCAD frame (front −Y), so every number was used without a transform. The
reference USDZ was resolved from Git at `7e747c60d` (the pre-migration HEAD,
after mounting-bore removal and the clay strip), SHA-256
`da9dd116d43575d1c021f0cfe106a9cec89bb74bba7e3caab8829b196ed29374`, and used only
for comparison. Mounting bores stay omitted under the repository's
screw-hole/hardware omission policy.

## Web cross-reference (2026-09-25)

No new page was fetched for this migration. The manufacturer facts are those
already recorded for this package in
`2026-08-12-single-board-documentation-packages.md` and the generator's
`sources.md`:

- <https://www.target10a.com/en/linebreaker-boards/409-linebreaker-base-trainingsboard.html>
  (manufacturer): 58 × 15 × 5.5 cm, yellow poplar, two jugs, 32.5° and 22.5°
  slopers, 16 / 20 / 18 mm bars, 37 / 28 / 45 / 24 / 30 / 50 mm pockets, and a
  35°, 35 mm sloper bar. The 580 × 150 × 55 mm envelope matches `board.json`
  `dimensions` and the new `modelBounds` exactly.
- <https://www.target10a.com/935-thickbox_default/linebreaker-base-trainingsboard.jpg>
  (manufacturer position map): both outer top slopers are 32.5°, and the
  22.5° sloper is the centre top. This is why `board.json` names
  `sloper-32-left` and `sloper-32-right`.

**Recorded conflict (sloper angle).** The generator cut the left top sloper at
32.5° and the right one at 22.5°. Its own limitations say that handed
assignment was "a display choice, not a manufacturer claim". The source cuts
both at 32.5°, following the manufacturer position map and the `board.json`
contact names. This is the one deliberate shape change from the reference: the
right sloper's front edge is 12.3 mm lower (z = 97.0 instead of 109.2). The 22.5° centre sloper
(`sloper-22-center`) is not in the current contact inventory. That is
unchanged, and this migration does not re-open it.

## Sourced versus approximated fields

| Field | Status | Evidence |
| --- | --- | --- |
| Envelope 580 × 150 × 55 mm | Published | manufacturer page; generator `dimensionsMm` |
| 23-contact inventory, kinds, names, depths, capacities | Carried unchanged from `board.json` | 2026-08-12 and 2026-08-25 records named above |
| Contact → node binding (`hold_<generator id>_001`) | Carried | `contact-mapping.json` (da2a18af1) and the reference descriptor; all 24 node IDs are unchanged |
| Front outline: 28-vertex polygon | Retained estimate | generator `outlineXZ`, authored as `OutlineSketch` |
| Rounded-rectangle slab clip (16 mm corners) | **Omitted** | the polygon lies inside it everywhere except a ≤ 2.8 mm sliver at the top outer corners (x ≈ ±265..275) |
| Perimeter rim round 3.5 mm | Retained estimate | generator `rimRadiusMm`; front and back `Part::Fillet`. At the back, the step between x = ±76 and ±187 is left square: there, the sloper planes meet the back face exactly on the z = 132 outline, and OCCT cannot round it |
| Top slopers: plane z = 132 + tan(32.5°)·y over x ∈ [81, 180] (mirrored), 2 mm front round | Angle published (manufacturer map, both sides); span and round are retained estimates | generator `bodyCuts` `planePatch`; right-side angle changed, see the conflict above |
| Lower-tier recess: front face at y = −36 for \|x\| ≤ 176 | Retained estimate | generator `profileVoid` |
| Lower-tier transition (−36, 41) → (−42, 49) → (−55, 57) | **Adapted**: generator is (−36, 37) → (−42, 45) → (−55, 53) | raised 4 mm. The lower-row cavities (z = 14..38, plus a 2 mm mouth chamfer to z = 40) otherwise break through the tier crease, and their front-to-floor depth would miss the published 16 / 18 mm by up to 2.3 mm |
| Tier blend 4 mm, rim 3 mm; slab-to-sloper blend 3 mm | **Omitted** | sharp creases |
| 19 cavity centres, widths, heights, stadium radii (height / 2) | Retained estimate | generator `pockets` |
| Cavity floors: front face − floor = published depth | Published depth, via `board.json` | every cavity region's Y extent is exactly its published depth (report below) |
| Mouth round 2 mm, floor round 1.2 mm | Retained sizes, **represented as 45° chamfers** | generator `lipRound` and `floorFillet`, as ruled capsule lofts (Beastmaker 1000 and Deluxe II precedent: small toroidal fillets over-tessellate) |
| Centre sloper bar floor: 35° (`floorSlopeZ` 0.7002), 122 × 23 mm | Angle published; size retained | generator. **Adapted pivot**: the generator put the 35 mm depth at the bar's centre line (43 mm at its top). The source puts the deepest point at the published 35 mm (y = −20 at z = 92.5, 18.9 mm at the bottom), which is how every other cavity's depth is defined. The floor has no 1.2 mm chamfer |
| Material `linebreaker_poplar`, base colour 0.65, 0.58, 0.36 | Compile-time source metadata only | generator `color`. Under the model material policy, the USDZ ships unbound |

## Document structure

Document properties: `HangTenSchemaVersion` 1, `HangTenPresentationID`
`primary`, `HangTenSourceKind` `native-parametric-measured-profile`,
`HangTenCoordinateFrame` `freecad-mm-z-up-front-negative-y`,
`HangTenTessellationDeflection` 0.05, and `HangTenCurvedRegionPartition` true
(the cavity walls are cylinders, the chamfers are cones, and the rim rounds are
cylinders).

- `OutlineSketch` → `OutlinePrism` (`Part::Extrusion`, 55 mm toward −Y).
- `TierVoidSketch` → `TierVoid`, and `SloperCutLeftSketch` /
  `SloperCutRightSketch` → `SloperCutLeft` / `SloperCutRight` (extrusions along
  +X). They are fused as `ReliefCuts` and cut from the outline prism as
  `RawBody`. `Refine` is off throughout.
- `FrontRim` and `BackRim` are sequential `Part::Fillet`s.
- For each cavity, `Capsule_<hold>_0..3` are capsule sketches: the mouth grown
  3 mm, 1 mm in front of the face; the nominal capsule 2 mm behind the face;
  the nominal capsule 1.2 mm above the floor; and the capsule shrunk by 1.2 mm
  at the floor. `Cutter_<hold>` is a ruled `Part::Loft` of the four. The sloper
  bar instead fuses a mouth loft (`Mouth_…`) with a capsule prism (`Prism_…`),
  cut by a rotated box (`FloorPlane_…`) whose face is the 35° floor.
  `HoldCutters` fuses all 19 cutters, and `BoardBody` (`Part::Cut`) is the
  exported body node `body_001`.
- 23 `Contact_*` `Part::Feature` objects, each a copy of the body faces its hold
  owns, carrying `NodeID`, `ContactID`, and `HangTenHoldOutline`:
  - A cavity owns every body face that lies on its cutter's shell (13 faces;
    9 for the sloper bar). Its outline is the mouth capsule grown by 2 mm.
  - A top hold owns the non-front, non-back body faces whose centre of mass lies
    in the generator's `surfaceContacts` x/z box (for the slopers, z from
    95 mm, so the front round is included). Its outline is the convex hull of
    those faces' front projection.

  These are static copies. Editing a cutter moves the body but not its contact
  object, and the published-depth gate catches that mismatch. The
  sketch-edit-propagation suite is not claimed.

## Evidence

- Compile: 29,676 triangles (the reference has 45,304), a 838 KB USDZ (4.36 MB
  before), and `modelBounds` 580 × 150 × 55 mm. Every published-depth gate is
  exact: 16 / 18 / 20 / 24 / 28 / 30 / 35 / 37 / 45 / 50 mm.
  `verify_reproducible.py` rebuilds it byte-identically on the pinned
  toolchain (FreeCAD 1.1.3, macOS arm64, OCCT 7.8.1).
- Region orientation: a point 0.3 mm along every contact face normal lies
  outside the body (0 flipped faces).
- Descriptor `facePlaneAABB` against the reference: 15 of the 19 cavities agree
  within 2.4 mm, and the sloper bar within 0.3 mm. `pocket-24-right` (2.6 mm),
  `edge-20-right` (4.9 mm), `pocket-50-right` (6.6 mm), and `pocket-45-right`
  (10.1 mm) differ because the reference's box selectors spilled onto
  neighbouring surface (`pocket-45-right` reached x = −2.6, across the centre
  line). The top holds differ by 10–19 mm for the same reason: the reference
  jug-right node reached down to z = 103, and its sloper nodes spanned
  x = ±59..198. The CAD regions are exactly the hold faces.
- `compare_exports` two-way sampled worst deviation: 10.02 mm (reverse
  8.50 mm; limit 0.5 mm; 45,304 reference vs 29,676 candidate triangles, both in
  the shared native frame with no transform).
  **Accepted deviation:** the reference is a 0.8 mm voxel marching-cubes mesh
  of smooth signed-distance blends, decimated to 45k triangles. The difference
  comes from the omitted blends, chamfers standing in for rounds, the raised
  tier kink, the sloper-bar pivot, and the right sloper angle. Per
  `docs/freecad-authoring-migration.md`, this is evidence, not a gate.
- In app: iPhone 17 Pro simulator (iOS 26.5), Debug board-detail review route,
  in a workspace-owned simulator that was deleted afterwards. Four holds were
  each selected and confirmed via `boardDetail.selectedHold.<id>`:
  - `jug-left`, the default selection, highlights the outer top block;
  - `sloper-bar-35-center`, by deep link, highlights as one capsule, with
    depth 35 mm;
  - `edge-16-left` and `sloper-32-right`, from the hold map, highlight the
    lower-tier bar and the whole 32.5° sloper plane;
  - `pocket-50-right`, by tapping the model, is selected with depth 50 mm and
    capacity 2.
- Previews: `2026-09-25-target10a-linebreaker-base-cad-preview.png` shows a
  three-quarter view of the reference (top) and the CAD asset (bottom), with
  front views and the in-app selections.
- Not verified: suspension, accessibility, and performance.
