# Tension Honestone native CAD source audit — 2026-09-29

## Approved evidence

The operator approved these exact manufacturer images in this session before
shape authoring. Neither the old raster nor image-derived geometry was used as
a CAD input. No tracing, detection, segmentation, pixel measurement, alignment,
or contour extraction was performed.

| Retained file | Primary URL | SHA-256 | Support |
| --- | --- | --- | --- |
| `2026-09-29-next-three-cad-sources/tension-honestone-1.png` | https://cdn.shopify.com/s/files/1/0653/3706/5653/files/Honestone1.png?v=1726542571 | `b41c5de625814fb685b5290fa779721287c40854c70afe4778292205056c276b` | Front arrangement, four connected stepped cavities, central capsule, two vertical monos, bottom contour, alternating top zones. |
| `2026-09-29-next-three-cad-sources/tension-honestone-3.jpg` | https://cdn.shopify.com/s/files/1/0653/3706/5653/files/Honestone3.jpg?v=1726542571 | `85ac5f15f8fb70814368c9762eee5d15372300f9c29bbbe6b7eb2e3c5e10bf39` | Installed oblique view, solid body thickness, real blind floors, stepped shared cavities, continuously curved top and broad macro texture. |

The manufacturer product page, https://tensionclimbing.com/products/honestone,
was independently checked on 2026-09-29. It specifies 25 × 6 × 2½ inches,
35°/45° top slopers with continuously variable curvature and macro texture,
a 25 mm center edge with 10° incut, 25 mm monos, 20/15 mm edges, and 10/8 mm
edges with a ⅛-inch edge radius. These agree with retained contact depth facts.

## Metadata and physical bindings

All 15 original `contacts` objects are preserved exactly, including identity,
names, equipment object, kind, finger capacity, grip types, and depth ranges.
Manufacturer, product URL, name, subtitle, dimensions, and top-level aspect
ratio remain unchanged. The primary presentation replaces raster geometry with
the USDZ/descriptor pair and uses the physical 635/152.4 front envelope ratio.
The CAD document owns the manifest; no package `board.json` remains.

There was a legacy raster binding error on the right wing: its right 15/8 mm
contacts were inward and right 20/10 mm contacts were outward. The approved
front image's engraved numerals show the sequence **20 then 15**, and **10 then
8**, from left to right on both wings. The 3D bindings correct that placement
while preserving the contact identities and all their factual metadata. Thus
the depth ordering is deliberately not mirrored. The four top zones also
alternate low/high/low/high and are not represented as a falsely symmetric top.

## Native geometry and authored estimates

Coordinates are native millimetres, X right, Z up, front Y = −63.5, back Y = 0.
The published overall envelope is exactly 635 × 152.4 × 63.5 mm. The published
pocket depths are exactly 25/20/15/10/8 mm along Y. The center pocket's custom
native direction `(0, 1, −tan(10°))`, with length measured along the sketch
normal, makes its physical bearing floor 10° incut while retaining 25 mm Y
depth. The lower cavity lips have native 3.175 mm fillets (the sourced ⅛ inch).

All other shape dimensions below are **operator-authored display estimates**
from visual judgment of the approved sources, not manufacturer measurements:

- The front top is 104 mm; rear low/high zones reach 140.4/152.4 mm. Nine body
  sections at Y `−63.5, −57, −49, −41, −33, −25, −17, −9, 0` loft smoothly.
  Their low heights are `104,105.7,107.8,113,115.8,123.1,126.5,134.5,140.4`;
  high heights are `104,106.5,110.7,116.5,121.5,129.6,136,144.5,152.4`.
  These form broad macro undulations and variable slopes; their waveform is
  an estimated visual representation, not a recovered manufacturing profile.
- Top transverse transition stations are X `−170,−145,−15,15,145,170`; blends
  are cubic Béziers with control offsets of 45% of their span. Four live
  contact regions cover the alternating top areas and transition surfaces.
- Upper cavity mouths span X `−250…−84` and `84…250`, split at `−168`/`168`,
  and Z `66…94`. Lower cavities use the same widths at Z `8…36`. Rounded
  outside corners have 5 mm plan radii; the internal split is open and the
  different depths create real floor steps. Upper mouth rounds are estimated
  2 mm. The lower 3.175 mm bearing radius is sourced as described above.
- The central mouth spans X `−57…57`, Z `36…62`, with 12 mm plan corner
  radii. Mono mouths span X `−303…−279` and `279…303`, Z `36…88`, with 11 mm
  plan corner radii. Their mouth rounds are estimated 2 mm.
- The bottom is deliberately drawn with cubic Bézier lobes. Low wing flats
  span X `−241…−87` and `87…241` at Z 0; the center flat spans `−61…61` at
  Z 22. Outer rounds run through X ±317.5 at Z 52 and join at X ±263/Z 23;
  intermediate poles set a smooth estimated contour. These are visual shape
  estimates rather than manufacturing tolerances.

Twenty fully constrained native Sketcher profiles feed one native
PartDesign additive loft, eleven native pocket features, and two native
fillets. All fifteen selectable regions are live SubShapeBinders of the
final body's own faces. There are no frozen imported shapes, mesh solids,
scripted runtime features, opening caps, floating contact patches, materials,
or textures. Mounting holes, fasteners, engraved branding/numerals, and wood
grain are intentionally omitted from the display model; the physical product
does have mounting hardware and engraving.

## Provenance and verification

The one-off author script is workspace-local:
`.context/supreme-zebra-next-cad-honestone/author.py`, SHA-256
`028a229e962855d394d63409d39f8374b0d8a18c1835e4e322a37677a7ac94e9`.
It is not a build dependency. `set_board_manifest.py` embeds the reviewed
manifest without modifying geometry. Compilation uses the pinned macOS
FreeCAD 1.1.3 toolchain and OpenUSD dependencies.

Retained regression checks are
`Tools/HangboardCAD/tests/honestone_native_source_checks.py` and
`test_honestone_native.py`. They check native recomputation, one valid solid,
the published envelope and every depth, constrained sketches, on-body regions,
the actual 10° floor normal, varying top slopes, corrected right-side physical
ordering, and a persisted 20→22 mm depth edit that moves its live contact while
the adjacent 15 mm region stays unchanged. Source bytes remain unchanged by
the regression.

Front/side/top diagnostic renders and comparisons with the prior committed
raster live under `.context/supreme-zebra-next-cad-honestone`. The prior asset
was raster-only; there is no honest prior side/top 3D reference. Comparisons
therefore show each new view beside the same prior front raster, labeled as
such. App-level review, delivery locking, and catalogue integration are handled
by the parent migration task.

Final compiler `--check` and publish both passed with unchanged source bytes and
identical model hashes. The native pytest regression passed (1 test, 7.61 s).
The result contains 16 nodes, 111,740 triangles, and a 2,361,159-byte USDZ.
Native fillets account for much of this tessellation; the compiler transports
the authored geometry without simplifying the ⅛-inch bearing surfaces.

- FCStd SHA-256: `9b647d84fc3258c3cf3657c1f045519ac0906669f0d17803c9d14c35d7da2c1e`
- USDZ SHA-256: `321a039d39299aca7213cb351bec05043a71493f5f48129717874f3f8e9f86c5`
- The reopened USDZ has zero Material/Shader prims and zero material bindings;
  its bytes match the descriptor hash.
- `/usr/bin/usdrecord --renderer Storm` rendered the final USDZ from front,
  side, top, and oblique cameras. These were visually inspected. The oblique
  view confirms the connected cavities' depth steps and the center incut.
  Final comparison: `.context/supreme-zebra-next-cad-honestone/honestone-comparison.png`;
  oblique view: `.context/supreme-zebra-next-cad-honestone/hydra-oblique.png`.
- Compiler temporary staging directories were removed automatically. The
  package contains only the FCStd and its two runtime assets; no backup, stale
  raster, board JSON, or temporary build file remains. No external resource or
  HTTP server was created.

The required model `display.camera` metadata uses the catalogue orthographic
view direction `[0, −0.3420201433, −0.9396926208]`, up `[0,1,0]`, and
`fitPadding: 0.08`. This is a presentation choice, not a physical product fact.
It was embedded with `set_board_manifest.py` after export; that metadata-only
operation preserved every geometry archive member and the USDZ hash. The
complete package subsequently passed `board_catalog.load_board_package`.

## Current display metadata — 2026-09-30

The FCStd hash above includes the catalog wood-finish assignment. The
[finish audit](2026-09-30-catalog-model-finishes.md) records this metadata-only
update and verifies every non-Document.xml archive member and runtime asset
unchanged. The geometry and visual review evidence in this audit still apply.
