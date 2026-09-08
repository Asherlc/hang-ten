# Beastmaker 1000 Interactive 3D Display Design

**Status:** Superseded by the revised user-approved contract below on 2026-09-08.
The original design after this section is retained as historical context, not
as implementation authority where it conflicts with this revision.

## Revised contract

The draft comparison precedes production integration. Compare independently
authored candidates using identical evidence, briefs, cameras, and lights;
isolate candidate code/artifacts and do not share candidate work. Inspect front,
oblique, clay, and detail views before selecting, recording render-engine
differences. Generic original wood is acceptable: species-specific tulipwood
fidelity is no longer required.

The later migration covers both Beastmaker 1000 and the previously migrated
Wood Grips Compact II. Remove their raster presentations and canonical 2D hold
geometry in full. `board.json` retains physical identity, source-backed logical
holds, equipment, positions, and stable IDs; byte-for-byte preservation is no
longer required. Explicitly tagged raster/model presentations allow unrelated
raster boards to coexist. Each migrated package owns its required USDZ and an
explicit mesh-to-logical-hold-ID binding, including disconnected mesh pieces
that share an ID. Mesh geometry alone drives rendering, highlighting, and
picking; do not maintain parallel raster paths or hand-edited spatial bounds.

Derive workout-matching centers and bounds from the mesh in a defined board
coordinate frame, optionally through a build-generated index bound to the model
hash so catalog loading need not eagerly decode USDZ. Separate camera
configuration from physical metadata; estimated geometry must not silently
become physical dimensions. Support model media in package validation, staging,
and sync. Workbench explicitly disables unsupported model geometry editing
without reconstructing raster geometry. Missing or malformed USDZ is a
validation/build defect; runtime failure shows an explicit unavailable state,
with no raster fallback for a migrated board.

The reusable authority is the updated
[`migrate-hangboard-to-3d` skill](../../../.codex/skills/migrate-hangboard-to-3d/SKILL.md).
Existing source audits remain evidence for physical metadata; the historical
byte-preservation, fallback, and mandatory-species requirements below do not
apply.

## Goal

Add a faithful, interactive 3D display for the current bundled tulipwood
Beastmaker 1000 while keeping the existing package, canonical selection
geometry, and 2D rendering path intact. The target is the exact package and
runtime identity `beastmaker-1000`, with overall display-model dimensions of
**580 × 150 × 58 mm** and exactly **22 selectable physical contacts**.

The first deliverable is a visual checkpoint, not an app-integrated asset. It
must make the model's silhouette, recesses, contact partitions, and surface
continuity cheap to reject or refine before final texture baking, export, and
iOS integration.

## Fixed product and compatibility contract

- Preserve [`Hangboards/beastmaker-1000/board.json`](../../../Hangboards/beastmaker-1000/board.json)
  byte-for-byte unless a separately approved package task is opened. Its ID,
  hold records, names, metadata, normalized paths, path commands, constraints,
  presentation ownership, and stable identities remain canonical.
- Preserve [`Hangboards/beastmaker-1000/assets/primary.png`](../../../Hangboards/beastmaker-1000/assets/primary.png)
  as the primary presentation and retain it for the editor and every 2D
  fallback state. The 3D model does not replace, redraw, or become an input to
  the PNG or its paths.
- Preserve all existing saved hold IDs and training-plan references. The 3D
  contact meshes are display/picking partitions that map back to those IDs;
  they are not new logical holds.
- Support only the unmodified bundled board's original, default, non-inverted
  `primary` presentation. Edited copies, other revisions, alternate or derived
  presentations, and inverted presentations remain 2D.
- Omit every screw hole, mounting hole, countersink, fastener, and item of
  mounting hardware. Reports and documentation must describe this as a
  deliberate display simplification and must not imply that the physical
  Beastmaker product lacks six installation openings/screws.
- Use the product's tulipwood appearance. The export must use an original
  procedural/baked tulipwood material, not copied pixels or grain from a source
  photograph and not the Beech variant's material.

## Evidence and modeling authority

Existing audits are the provenance record; this migration does not restart
broad web research or promote a photograph into geometry.

| Claim used by the model | Repository audit | Recorded source |
| --- | --- | --- |
| Exact tulipwood Beastmaker 1000 identity, 580 × 150 mm face, grouped jug/sloper/contact inventory, and official front appearance | [`2026-08-12-beastmaker-board-packages.md`](../../source-audits/2026-08-12-beastmaker-board-packages.md) | [Official Beastmaker 1000 product page](https://www.beastmaker.co.uk/products/beastmaker-1000-series) and [official tulipwood front image](https://cdn.shopify.com/s/files/1/0107/6442/files/1000_Small_Tulip.jpg?v=1756733068) |
| Source-audited 58 mm overall thickness | [`2026-08-19-all-board-metadata-hold-audit.md`](../../source-audits/2026-08-19-all-board-metadata-hold-audit.md) | [Official Beastmaker FAQ](https://www.beastmaker.co.uk/pages/faq) and the [official Beech variant page](https://www.beastmaker.co.uk/products/beastmaker-1000-beech), used only as cross-variant corroboration for the shared 58 mm depth |
| 580 × 150 × 58 mm wood layout, identical Beech/tulipwood hold layout, symmetric front face, and six real installation openings | [`2026-08-30-hangboard-presentation-remediation.md`](../../source-audits/2026-08-30-hangboard-presentation-remediation.md) | [Independent Beastmaker 1000 review](https://thehangboard.com/blogs/news/beastmaker-1000-review), corroborating rather than overriding first-party evidence |
| Positioned contact kinds and exact source-backed sizes already accepted into the package | [`2026-08-12-beastmaker-board-packages.md`](../../source-audits/2026-08-12-beastmaker-board-packages.md) and [`2026-08-25-hangboard-metadata-ledger.json`](../../source-audits/2026-08-25-hangboard-metadata-ledger.json) | [Official product page](https://www.beastmaker.co.uk/products/beastmaker-1000-series) where available, then the recorded [positioned comparison](https://thehangboard.com/pages/beastmaker-1000-vs-2000) where it does not conflict with primary evidence |

The 58 mm value belongs in the model and its provenance report even though the
current flat package deliberately exposes only `dimensions: "580 × 150 mm"`.
This migration must not backfill the package field. The Beech page corroborates
thickness and layout only; it is not evidence for this package's identity,
color, or material.

### Sourced dimensions versus estimates

The following values are sourced and may be asserted as exact in the model
report:

- overall bounds: 580 mm wide, 150 mm high, and 58 mm front-to-back;
- paired top outer edges: 10 mm;
- paired top edges: 30 mm;
- paired middle outer and inner contacts: 45 mm;
- paired middle two-finger pockets and the middle center edge: 50 mm;
- paired bottom outer and inner contacts: 20 mm; and
- paired bottom two-finger pockets: 25 mm.

The 10 mm value follows the first-party value retained by the audit despite a
conflicting 15 mm secondary label. These values describe the accepted contact
sizes in `board.json`; the build report must state the authored measurement
datum used to express each as a recess/edge section instead of presenting that
datum as manufacturer CAD.

Exact aperture positions and widths, lip and corner radii, jug rolls, sloper
sections, transition curves, recess wall/back profiles, back-face details,
edge rollover, and wood-grain realization are **visual display estimates**.
The 35° pair and 20° center sloper labels are source-backed angles, not pocket
depths. Every estimated parameter must be grouped separately from sourced
measurements in `model-report.json`; no report may flatten both categories into
an undifferentiated dimensions list.

## Canonical selectable inventory

The model consumes the current `board.json` inventory at build and verification
time and must contain these 22 IDs exactly:

- top contacts: `jug-left`, `jug-right`, `sloper-35-left`,
  `sloper-35-right`, `sloper-center`;
- top row: `pocket-top-outer-left`, `pocket-top-outer-right`,
  `pocket-top-left`, `pocket-top-right`;
- middle row: `pocket-middle-outer-left`, `pocket-middle-mid-left`,
  `pocket-middle-inner-left`, `pocket-middle-center`,
  `pocket-middle-inner-right`, `pocket-middle-mid-right`,
  `pocket-middle-outer-right`; and
- bottom row: `pocket-bottom-outer-left`, `pocket-bottom-mid-left`,
  `pocket-bottom-inner-left`, `pocket-bottom-inner-right`,
  `pocket-bottom-mid-right`, `pocket-bottom-outer-right`.

Historical `pocket-*` prefixes are stable identities, not permission to ignore
the current audited `kind`. Contact surface construction must follow the
current `edge`, `pocket`, `jug`, or `sloper` metadata and evidence mapping.

## Geometry and material design

Author the board as a full-depth analytic model in meters, with X across the
580 mm width, Z across the 150 mm height, and the working face oriented
consistently with the Compact II export convention. This is not a shallow
extrusion of the primary PNG or canonical paths.

The model must include:

- a directly authored outer silhouette, full 58 mm body section, front and back
  transitions, and rounded perimeter appropriate to the reviewed product;
- true carved/recessed geometry for every front edge and pocket, including
  mouth fillets, continuous sidewalls, and back transitions rather than dark
  decals or coplanar overlays;
- directly authored curved jug and sloper surfaces, including the paired 35°
  and center 20° working surfaces, with enough section samples to remain smooth
  in a close mobile oblique view;
- one exportable body mesh and one independently material-addressable contact
  mesh for each physical contact; and
- an original 2048 × 2048 tulipwood PBR base-color atlas with restrained grain,
  matte roughness, and complete material assignment on the body and contacts.

Author one side and mirror it exactly for genuinely symmetric paired geometry,
swapping the left/right canonical IDs after mirroring. Author center geometry
independently. Do not idealize asymmetry that evidence establishes as physical,
but do not copy incidental grain, lighting, lens distortion, or manufacturing
variation from a photographed specimen.

Do not use image-driven hold detection, tracing, segmentation, generated masks
or contours, source registration/alignment, vectorization, automatic path
simplification, automatic cropping, or proposal/refine/promote geometry. The
operator selects analytic coordinates and sections by visually reviewing the
existing evidence. The existing canonical paths are an identity and alignment
cross-check only; they are not automatically extruded or converted into the 3D
mesh.

## First-pass review gate

The first pass must already have the full silhouette, real recess topology,
curved top contacts, all 22 contact partitions, and a provisional original
tulipwood shader. Before final texture baking, GLB/USDZ export, native testing,
or app integration, render and present:

1. a centered orthographic `front.png`;
2. a lit `three-quarter.png` that makes overall depth and top sections legible;
3. a texture-free close `clay-detail.png` exposing pocket mouths, backs,
   fillets, normals, and surface continuity; and
4. an all-contact review consisting of a numbered overview/contact sheet plus
   22 individual highlight renders, one for every canonical ID.

The first-pass report records the Blender source hash and binds every highlight
image to that hash. Review can reject silhouette, depth profiles, continuity,
material, or contact partitions independently. A rejection returns to analytic
authoring and regenerates only invalidated views. No Beastmaker USDZ is copied
into the app bundle until this gate is explicitly accepted.

## Workspace artifacts and ownership

All generated source, evidence copies, renders, exports, and reports live under
`.context/shaky-rat-beastmaker-1000-3d/`. The build creates
`ownership.json` before other output with at least:

```json
{
  "owner": "shaky-rat",
  "resource": "beastmaker-1000-3d",
  "path": ".context/shaky-rat-beastmaker-1000-3d"
}
```

The complete reviewed output set is:

- editable `beastmaker-1000.blend`;
- `beastmaker-1000.glb` and `beastmaker-1000.usdz`;
- original baked texture assets;
- `front.png`, `three-quarter.png`, `clay-three-quarter.png`, and
  `clay-detail.png`;
- `highlights/` with its overview, contact sheet, 22 individual images,
  `index.html`, and report;
- isolated `glb-roundtrip.png`, `usdz-roundtrip.png`, and corresponding clay
  detail views;
- `model-report.json`, `export-verification.json`, and a native SceneKit
  verification report; and
- source/export/bundle SHA-256 values and the evidence-to-parameter mapping.

Build scripts create no external resources. Any later simulator or process
used for validation must use a workspace-owned name containing `shaky-rat`, be
recorded immediately, and be removed by the owning process's exit trap without
touching shared or unknown resources.

## Tooling and export verification

Use [`Tools/HangboardModels/wood_grips_compact_ii.py`](../../../Tools/HangboardModels/wood_grips_compact_ii.py),
[`verify_wood_grips_compact_ii.py`](../../../Tools/HangboardModels/verify_wood_grips_compact_ii.py),
and [`render_hold_highlights.py`](../../../Tools/HangboardModels/render_hold_highlights.py)
as structural precedents. Add a Beastmaker-specific generator and verifier;
parameterize shared highlight/report behavior where that removes fixed Compact
II assumptions without weakening Compact II regressions.

The editable source and GLB should preserve canonical `hold_id` custom
properties. USD prim-name normalization may replace hyphens with underscores,
but the custom property and the runtime's inventory-bounded normalization must
still resolve the original ID. Add temporary triangulation only for USDZ
export so SceneKit cannot fill Boolean cap n-gons; remove those modifiers from
the editable source after export.

For each actual GLB and USDZ, the verifier must open a clean scene, remove all
source-scene materials and images, import only the exported artifact, and then
assert:

- bounds of 0.580 × 0.058 × 0.150 m within the existing one-micrometer
  round-trip tolerance and with the expected axis order;
- exactly 22 unique canonical contact IDs and no missing or unknown ID;
- normally 23 meshes: one body plus one mesh per physical contact. A genuinely
  disconnected contact may use multiple meshes only when the report names the
  ID, explains the physical need, and the verifier adjusts the mesh count while
  retaining exactly 22 selectable IDs;
- nonempty geometry and image-backed material coverage on every exported mesh;
- a loaded embedded 2048-pixel tulipwood atlas rather than an accidental
  dependency on the source `.blend`;
- fewer than 150,000 triangles, with the actual total recorded;
- explicit triangle faces in USDZ; and
- visually continuous silhouette, pocket openings, pocket backs, jugs, and
  slopers in the round-trip and clay-detail renders.

The final reviewed USDZ is copied to
`HangTen/Resources/BoardModels/beastmaker-1000.usdz` only after the first-pass
gate and export verification pass. Source and destination SHA-256 values must
match before it is committed.

## Runtime architecture and data flow

Generalize the single-board code in
[`HangTen/Views/BoardModelView.swift`](../../../HangTen/Views/BoardModelView.swift)
into a small, explicit model registry. Do not duplicate the SceneKit renderer.
Each registry descriptor owns:

- the exact canonical board ID;
- USDZ resource name and extension;
- exact expected hold-ID set;
- camera target and portrait/landscape framing values; and
- board-level accessibility label.

The registry initially has two descriptors: the existing
`metolius.wood-grips-compact-ii` entry and the new `beastmaker-1000` entry.
The Beastmaker descriptor uses resource name `beastmaker-1000`, bounds
580 × 150 × 58 mm, a model center at `(0, 0.075, 0.029)` after SceneKit's
Y-up conversion, 8% fit padding, and accessibility label
`"Beastmaker 1000 hangboard"`. The Compact II descriptor retains resource name
`wood-grips-compact-ii`, its existing camera target and appearance, and label
`"Wood Grips Compact II hangboard"`. Framing computes the orthographic scale
from the descriptor's width/height and the live view aspect ratio, then applies
the descriptor padding; it does not special-case a board ID inside the view.
Matching requires equality with the currently bundled canonical board plus its
original default primary presentation, a nil source presentation, non-inverted
orientation, and exact inventory. Registry keys, cache keys, and SwiftUI task
identity must use the descriptor identity rather than one global board ID.

Data flows as follows:

```text
board + presentation
  -> exact registry match or 2D fallback
  -> descriptor-keyed asynchronous source-scene cache
  -> isolated scene/node/material clone
  -> material + exact inventory validation
  -> descriptor-specific camera, framing, and accessibility label
  -> highlight/accessibility projection/nearest-triangle tap handling
```

The 2D fallback remains visible while a model loads. When board or presentation
identity changes, clear any stale model immediately, cancel or disregard the
old task result, and bind the replacement scene **and its camera** only if its
descriptor still matches. Source-scene decoding remains asynchronous and
cached per descriptor, including an isolated cached failure. Each rendered
view receives cloned geometry/materials so highlights never leak between cards
or model identities. Rendering remains on demand.

Highlights accept only IDs in the active descriptor. Preview uses the existing
rest-blue semantics, active uses the existing active color, and clearing
restores the exact cloned tulipwood materials. The accessibility container uses
the descriptor's board label when taps are unavailable and stable per-hold
buttons/labels when taps are enabled.

Nearest-hit picking remains native SceneKit triangle picking. Body and unknown
nodes never produce a hold callback. A CPU-only native regression flushes the
SceneKit transaction and fires a parallel head-on ray through a valid interior
sample for **every one of the 22 contacts**; the nearest result must resolve to
that exact canonical ID, not the body or a neighboring contact.

## Error and fallback behavior

The 3D path fails closed to the existing 2D presentation. Use fallback without
a crash or partially interactive scene when:

- no registry descriptor exactly matches;
- the resource URL is missing or is not a regular file;
- SceneKit decode fails or returns an empty/invalid scene;
- any geometry has no material;
- the imported contact inventory is missing, duplicated ambiguously, or
  contains an unknown identity;
- an edited board happens to retain the same IDs but differs from the bundled
  canonical value; or
- the board is unsupported, derived, alternate, or inverted.

A load failure for Beastmaker must not poison the Compact II cache. Unknown
highlight IDs are ignored. Hits on body/unknown nodes do nothing. Relaunching
starts fresh process-local caches, so a valid bundled asset can recover after a
prior missing/invalid fixture test.

## Component boundaries

- `Tools/HangboardModels/beastmaker_1000.py`: direct analytic authoring,
  tulipwood material, editable source, draft/final renders, GLB/USDZ exports,
  ownership, and model report.
- `Tools/HangboardModels/verify_beastmaker_1000.py`: Beastmaker bounds,
  inventory, mesh, material, texture, triangle, and isolated round-trip checks.
- `Tools/HangboardModels/render_hold_highlights.py` and
  `test_model_reports.py`: board/model/output parameters and 22-contact report
  coverage while retaining Compact II behavior.
- `Tools/HangboardModels/README.md`: Beastmaker commands, evidence mapping,
  sourced-versus-estimated parameter table, screw-hole omission, review gate,
  hashes, and limitations.
- `.context/shaky-rat-beastmaker-1000-3d/`: generated source and review proof;
  never package input.
- `HangTen/Resources/BoardModels/beastmaker-1000.usdz`: only the approved,
  verified runtime artifact.
- `HangTen/Views/BoardModelView.swift`: descriptor registry, per-descriptor
  async cache, scene validation, rebinding, framing, accessibility, highlights,
  and picking.
- `HangTenTests/BoardModelTests.swift`: registry compatibility, both bundled
  assets, per-view isolation, camera rebinding, fallback matrix, all-contact
  nearest-hit picking, and highlight lifecycle.
- `HangTenTests/BoardSourceBoundaryAudit.swift` and
  `BoardSourceBoundaryTrackedPaths.txt`: update only as required to recognize
  the new display resource/registry without weakening package-source rules.

## Validation

Before bundling, run the model report regressions, generate the editable model,
complete the visual gate, render all 22 highlights, and pass isolated GLB and
USDZ verification. Inspect the images rather than treating scripts as visual
proof. Then run the native SceneKit material/inventory/picking harness against
the exact candidate USDZ.

After bundling, run focused model and source-boundary tests plus a build. Follow
the `validate-hang-ten-ios` workflow on an isolated simulator and inspect both
portrait and landscape at app viewing sizes. Validation covers:

- normal/rest state and legible recess depth;
- all 22 holds individually and all holds together;
- preview highlight, active highlight, clear/wood restoration, and repeated
  highlight changes;
- physical taps on all 22 contacts resolving to the expected hold;
- scene and camera rebinding across Compact II, Beastmaker, and 2D boards;
- disappearance/reappearance and app relaunch; and
- unsupported, edited-with-different-inventory, edited-with-same-inventory,
  inverted, missing-resource, malformed-resource, materialless, and
  wrong-inventory fallback fixtures.

## Acceptance criteria

The migration is accepted only when all of the following are true:

- the user approves the first-pass front, three-quarter, clay-detail, and full
  22-contact highlight review;
- the model visibly matches the reviewed Beastmaker 1000 silhouette, contact
  layout, real recess character, jug/sloper curvature, full 58 mm section, and
  tulipwood finish at front and oblique angles;
- screw holes and hardware are absent and every report labels the omission as
  a deliberate display simplification;
- sourced measurements and estimated sections/radii/profiles are separately
  and completely reported;
- the editable Blender source, GLB, USDZ, texture, reviews, ownership, evidence
  mapping, reports, and hashes exist under the owned `.context` directory;
- isolated import proves correct bounds, texture independence, material
  coverage, triangle budget, visual continuity, and exactly 22 selectable IDs;
- the normal export has 23 meshes, or every additional disconnected piece has
  the narrowly justified and verified exception described above;
- native SceneKit verifies materials and exact nearest-hit picking for all 22
  contacts against the actual USDZ;
- the bundled USDZ hash equals the approved candidate hash;
- both boards use one registry-backed bridge with independent async caching,
  cloned materials, identity-aware camera/scene rebinding, correct framing,
  highlights, accessibility, and fallback gating; and
- focused tests, the relevant build, and portrait/landscape iOS visual and
  interaction validation pass.

## Non-goals

- This is display geometry, not manufacturing CAD, a measurement reference, or
  a source for safe construction, mounting, or machining.
- Do not change board metadata, hold metadata, paths, presentation PNGs,
  training plans, exercise instructions, grip cues, or workout compatibility.
- Do not add logos, installation hardware, wall scenery, animations, camera
  controls, or a general-purpose asset manifest/plugin system.
- Do not migrate Beastmaker 2000 or any other board as part of this work.
