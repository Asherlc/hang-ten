# 3D model hangboard cord audit

Initial audit: 2026-09-13; latest coverage addendum: 2026-09-20
Scope: every model-media package discovered under `Hangboards/`  
Decision: approved for package promotion after human review of the retained
exact-revision views and attachment views

## Result

The audit covers all 40 discovered model packages after the 2026-09-21 Rock
Prodigy Pivot promotion and the 2026-09-20 J Bryant FTG-32 addition. Thirteen
have documented suspended presentation evidence and render transient cord
geometry; twenty-seven remain
excluded because their reviewed product evidence does not establish a
suspended presentation. Optional user-provided rope or bungee is sufficient
for documented suspended presentation, but it is never described as supplied
or integral.

| Decision | Count | Packages |
|---|---:|---|
| `represented` | 13 | `yy.penta-evo`, `metolius.rock-rings-3d`, `metolius.light-rail-2`, `crimptonite.helium-mobile`, `j-bryant.ftg-32`, `tension.flash-board`, `captain-fingerfood.dual`, `captain-fingerfood.pocket`, `captain-fingerfood.unlevel`, `lattice.mxedge-lift-large`, `lattice.mxedge-lift-small`, `nature.stone-hanger`, `yy.baguette-evo` |
| `excluded` | 27 | Trango Rock Prodigy Pivot; Owl Climb Poker; Beastmaker 1000/2000; Clavellium Training Block; DeWoodstok Woodbord; Escape Unlimited/Beta 22; Evolv Kilter Basic Long; Lattice Triple Rung; Mammut Diamond Finger; Metolius Climber's Edge/Contact/Foundry/Prime Rib/Project/Simulator 3-D/Wood Grips Compact II/Wood Grips Deluxe II; Moon Armstrong; Nature Stoak Board III; So iLL Iron Palm II/Split Palm/Training Tiles; Target10a Linebreaker Base; The Hangboard; Trango Rock Prodigy Training Center |

The machine-readable record is [`2026-09-13-model-hangboard-cord-audit.json`](2026-09-13-model-hangboard-cord-audit.json). Its record set is deliberately closed: the cord-audit command discovers model media directly and requires exact equality with the manifest package IDs.

## Evidence review and approval

### Trango Rock Prodigy Pivot reauthored model promotion — 2026-09-21

Ruling: **noDocumentedSuspension; pulley-kit ropes are not Pivot suspension.**

All four approved exact manufacturer originals are retained as regular files
`trango-rock-prodigy-pivot-front.jpg`, `-dual-oblique.jpg`,
`-single-oblique.jpg` and `-close-up.jpg` under the snapshot directory. Their
URLs and unchanged SHA-256 values are recorded in the canonical JSON evidence
entries. Together with the manufacturer Quick Start and depth guide facts in
the closed
[Batch 04 source register](2026-09-20-batch-04-3d-source-register.json) they
establish the nine physical contacts per half, the four selectable quarter-turn
positions, and the separate external Quad Cleat mounting hardware. They do not
establish board suspension. The separately sold pulley kit's ropes are training
accessories, not a suspended Pivot presentation, so no cord, anchor, passage or
suspension metadata is promoted.

The delivered Batch 04 Pivot GLB
(`0c342998ced0a3fa99172ff08adf1d605933405df5520ec0833db23d5c2edda8`) remains
**rejected as production geometry and retained as audit evidence only**. The
promoted USDZ is one manually reauthored canonical half: a continuous moulded
perimeter rim around a recessed field, a broad integrated concave wing, two
supported crimp ledges with opposed moulded end stops, a scalloped three-finger
trough, a continuous variable-depth rail cove and a lower wave sloper. The
descriptor is v2 and the right half is reflection metadata, never a second
baked mesh.

Exactly two genuine openings are retained: the `two-finger-opening` through
window and the `three-finger-end-window`. All six delivered fastener holes,
every bolt counterbore and set-screw bore, and every screw, Quad Cleat,
rail/backer and bracket mesh are omitted from the display model. That omission
does not imply the physical product lacks them.

Sourced PV5 depths (top sloped 12.5, side sloped 11.5, rail 16–31, medium
9–10, large 11–12, two-finger 32–28, three-finger 28–17 mm) are preserved. The
overall envelope, rear surface, silhouette radii, scallop count, wing section,
along-rail depth gradient direction, material and camera are explicitly
`authored-display-estimate`; the depth guide's L→R labels are relative to each
illustration, so the gradient direction is authored rather than sourced. Only
`p1`, `p2`, `p3` and `p5` are selectable; `p4` is Orientation 3 Switch
transition evidence and is deliberately not selectable. Current-source app
visual acceptance remains the Batch 04 Task 14 gate.

### Owl Climb Poker model promotion — 2026-09-20

Ruling: **noDocumentedSuspension; excluded.**

All four approved exact manufacturer originals are retained as regular files
`owl-climb-poker-face-a.jpg` through `owl-climb-poker-face-d.jpg` under the
snapshot directory. Their URLs and unchanged SHA-256 values are recorded in
the canonical JSON evidence entries. They establish the four same-face
inventories (7, 9, 9, 9 contacts); the only delivered-mesh omissions restored
are `face-d-left-deep-rounded-recess` and
`face-d-right-deep-rounded-recess`. The supplied black end brackets are
external mounting hardware, omitted from the display along with all screws,
mounting holes and fasteners. They do not establish suspension.

Independent manufacturer research on 2026-09-20 corroborates the
[100 × 100 × 660 mm beam, four usable faces and rounded edges](https://owlclimb.com/index.php/en/prds-2/poker/).
The conflicting retailer envelope remains excluded. The manufacturer lists
depth families but does not map individual depths or cyclic order to the
photographs. All unsurveyed depth assignments, cyclic assembly, cross-face
transitions, radii, materials and display rotations remain
`authored-display-estimate`. Neutral face A–D labels follow the approved
photo sequence, not a claimed manufacturer numbering scheme. The single-
and dual-finger pocket sequence runs in the same left-to-right order at both
ends in all four photographs; it must not be mirrored.

The one descriptor-v1 model has no suspension, anchor, attachment, passage,
cord or hardware nodes. Four model positions rotate that one beam about its
long axis; each exposes only its same-face canonical contacts. Current-source
app visual acceptance remains the Batch 04 Task 14 gate.

### YY Penta Evo reusable-unit promotion — 2026-09-20

Ruling: **two independent paired exterior loops through the existing central ring; no invented channel or knot.**

The approved intact YY front/reverse and close-up originals are retained as
`yy-penta-evo-front-reverse.webp` (SHA-256
`83b95adc297d634659654f6f27bb43ebae1c53b171b747568ac5e022754e6571`)
and `yy-penta-evo-close-up.webp` (SHA-256
`1107039ef6d2877cd68a293683c72ec93f3166633199d45484f58c13b48aa2fc`).
Both reference the [official product page](https://www.yyvertical.com/en/products/penta-evo).
Their original binary URLs remain unknown; the page is not asserted to be a
download URL. Distinct retained views, regular files and verified hashes
establish the two evidence artifacts even though their reference URL is shared.
The original source register retains `binaryURL: null` and `status: unhashed`.

Independent research on 2026-09-20 confirmed that YY enumerates seven grips
(25/20/15/10 mm, mono, duo, tray), despite an eight-grip headline, and documents
360-degree rotation with retaining notches. Its
[installation article](https://www.yyvertical.com/en/blogs/news/installer-cordelettes-agres-penta-evo-guide-complet-4-noeuds)
explicitly passes the short cord through the existing ring. This corroborates
the photographed exterior top-band loop without establishing a hidden channel.
The article's knots and extensions are not part of the model or training copy.

One manually authored asymmetric unit is exported once and rendered as
`left-penta` and `right-penta`, both identical and unreflected. Its seven generic
slots map to fourteen unchanged contact identities. Front 25/20/15 pockets,
rear 10 pocket, through mono/duo, central ring and lower inner tray are retained.
The reverse 10 mm pocket shares the physical front-15 band; it is not a second
unit or a mirrored asset. Only the central ring and mono/duo are through
openings. The lower band is intact; retired small passages, mounting/screw holes,
hardware, knots and baked cords are absent.

`primary` exposes twelve front/through contacts, excluding the rear-only 10 mm
pair. `reverse` exposes the eight rear-10/mono/duo/tray contacts. Each unit uses
identity rotation in primary and the same 180-degree Y rotation in reverse,
with independent pose translations X = ±0.15 m and identity bases. This makes
workout selection expose the actual contact face while preserving identity.

Each unit owns two exterior leads, front and rear, around its existing upper
band into the central ring. Explicit pose `cordContactPoints` preserve the
reviewed route in both positions. The front/rear straight routes sit 3.5 mm
from the corresponding face, round into the ring, and end separately at model
coordinates (0, 0.061, ±0.004) m. Each unit has a separate fixed invisible
anchor at (±0.15, 0.325000002, 0) m, 0.300 m rest allowance per lead and 2 mm
cord radius. All these values and the unsurveyed outline/material/camera are
`authored-display-estimate`, not measured physical rope, factory radii or a
supplied knot. Source photographs show the rope continuing into a complete
loop; the narrow paired-lead representation does not invent that unseen join.

The hash-checked USDZ passes structural checks with one connected component,
10,396 triangles, exactly three through openings, zero nonmanifold edges,
degenerate triangles or reversed normals. Both instances in both positions
pass the production solver and mesh/tube clearance gate. Native selected-state
tests establish separated units and camera framing of both active cord systems;
full current-source app visual acceptance remains the Batch 04 Task 14 gate.

The human review retained exact-revision source responses where the cited page
was available. Every retained evidence entry records its exact revision ID,
source tier, source URL, and the SHA-256/path of its own downloaded artifact.
The validator rejects reuse of one artifact for two distinct represented views
and rejects markdown audit ledgers as source snapshots. When a cited source
cannot be retained, the record remains blocked from representation until the
evidence is retained; it is not silently treated as proof that a documented
optional suspension does not exist. A package with documented suspension
metadata cannot receive an `excluded` decision. Each record also carries the
independent `sourceFact` (`documentedSuspension` or
`noDocumentedSuspension`); both decisions require retained evidence, and the
validator rejects a documented-suspension source fact classified as excluded
even after rendering metadata is removed.
Every record also carries an explicit `humanApproval` object; the validator
rejects missing or incomplete provenance and approvals.

### 2026-09-15 model-only coverage addendum — excluded

The six packages promoted to model-only media after the initial audit have no
`media.suspension` metadata. Each retains a distinct manufacturer artifact in
the snapshot directory and an approved exclusion record. The artifacts
establish product identity and visible board arrangement only; none establishes
a suspended presentation. Each exclusion records `noDocumentedSuspension`;
it does not infer a cord from mounting openings. Accordingly, this addendum adds no cord,
attachment, topology, or hidden-route claim.

| Package | Retained manufacturer artifact |
|---|---|
| `metolius.climbers-edge` | [Climber's Edge product image](https://www.metoliusclimbing.com/cdn/shop/files/The-Climber_s-Edge-Training-Board_67ebe212-d205-4f2c-9ca9-048b1792351d.jpg?v=1765309719), `metolius-climbers-edge-product.jpg` |
| `metolius.contact` | [Contact product image](https://www.metoliusclimbing.com/cdn/shop/files/Contact-Hangboard-black-white.jpg?v=1759459002), `metolius-contact-product.jpg` |
| `metolius.simulator-3d` | [Simulator 3-D product image](https://www.metoliusclimbing.com/cdn/shop/files/Simulator-black-white.jpg?v=1759460469), `metolius-simulator-product.jpg` |
| `soill.training-tiles` | [Training Tiles product image](https://soillholds.com/cdn/shop/products/training-tiles-so-ill-x-meagan-martin-so-ill-white-12-01-so-ill-670960_2048x.jpg?v=1677258630), `soill-training-tiles-front.jpg` |
| `the-hangboard.the-hangboard` | [The Hangboard product image](https://cdn.shopify.com/s/files/1/0764/5210/2426/files/hangboard-straight-2.png), `the-hangboard-straight.png` |
| `trango.rock-prodigy-training-center` | [Rock Prodigy Training Center product image](https://trango.com/cdn/shop/files/22830_Rock_Prodigy_Training_Center_Main_Image.jpg?v=1737728750&width=1946), `trango-rock-prodigy-training-center-main.jpg` |

### Tension Flash Board — `twoBranchCord`

- Exact-revision manufacturer view: [Tension Flash Board](https://tensionclimbing.com/products/flash-board-2), retained as `tension-flash-product.html`.
- Exact-revision training view: [Flash Board training article](https://tensionclimbing.com/blogs/training-tools/hangboard-overview-the-flash-board), retained as `tension-flash-training-blog.html`.
- The Backcountry and Amazon responses were unavailable as usable source artifacts at audit time, so they are not represented as evidence.
- The retained packet establishes the supplied portable cord, two ordered
  passage pairs, and four canonical positions. Existing suspension metadata and
  descriptor bytes were unchanged by the suspension audit at that stage. The
  later contact-first integration migrated the descriptor schema; the current
  post-integration hash boundary is recorded below.

### Captain Fingerfood DUAL, POCKET Lines, and UNLEVEL — `pairedLeadCord`

- Current DUAL, POCKET Lines, and UNLEVEL manufacturer product pages publish
  total rope length (1 m for DUAL and UNLEVEL; 1 m for POCKET Lines). The
  renderer's `restLength` is per lead. After the 2026-09-14 user visual review,
  DUAL, POCKET, and UNLEVEL use compact 0.275 m, 0.27 m, and 0.28 m display
  estimates respectively. These are conservative compact capacities that
  cover every canonical routed pose; they do not revise the published 1 m
  total or claim measured individual lead lengths.
- The retained title images show two ropes descending over the upper lip into
  the recessed channel for each exact revision. They do not establish a
  through-hole or complete hidden interior route.
- Each package therefore binds two distinct recess terminals on its existing
  importer-visible body node and preserves the visible upper-lip path with two
  default ordered `contactPointsInModel` per lead. Selected inverted and end
  poses use `attachmentPoints` and `cordContactPoints` to delimit the visible
  cord in that pose's upper channel, avoiding a loop across the face and white
  floor apertures. These are explicitly display estimates of the visible
  portion, not newly asserted physical mouths or hidden interior routes.
  All free spans and contact surfaces retain the production clearance gate.
- The shared anchor offset is the user-approved compact 0.15 m display
  estimate, 50% below the prior presentation value.
- Attachment coordinates, anchor offsets, cord radius, and pose camera values
  are explicitly display estimates. The suspension edit left contact IDs,
  positions, model bytes, descriptor bytes, and orientation values unchanged
  at that stage; the later contact-first integration migrated contact-related
  board and descriptor fields.

### J Bryant FTG-32 — `pairedLeadCord` (2026-09-20)

The approved exact-revision gallery and human topology confirmation establish
one physical loop passing through the two centered holes and around the rear
of one block. Its runtime presentation shows two exterior leads from one
shared invisible anchor; the known rear connecting segment is deliberately
omitted. This does not claim two physical loops or an unseen rendered route.
Both attachment and terminal-passage records bind to `Cube_001`; the two
selectable ledges remain `edge-16` and `edge-25` contact nodes.

The record retains the exact user-supplied suspended-front and material-oblique
bytes under their original commerce URLs, with SHA-256 values
`f276704568bb877405617446e7527183ad81291df8e9231611487e52cadd533c` and
`13e329556225441266c61d7ee4f0aea8bdb49129c02450cd2ae1756fce50adb7`.
The independently fetched front response has different bytes; the distinction
is retained in the [FTG-32 source audit](2026-09-20-j-bryant-ftg-32-3d.md).
The manifest records the 2026-09-20 user approval and commerce source tier.
All unpublished attachment, exterior guide, anchor, cord and camera values
remain `displayEstimate`; no rope length, material, rating or safety fact is
inferred from the presentation.

### YY Vertical Baguette Evo — `twoBranchCord`

- Exact-revision manufacturer view: [manufacturer English listing](https://www.yyvertical.com/en/products/baguette-evo), retained as `yy-baguette.html`.
- Exact-revision manufacturer product image: [Baguette Evo product image](https://www.yyvertical.com/cdn/shop/files/YY_BAGUETTE_EVO_02_FG.webp?v=1751469206), retained as `yy-baguette-evo-image.webp`.
- The current **Baguette Evo, Turn & Pull version**, SKU `YY BAGUETTE EVO`,
  EAN `3760305271822`, is the retained revision. Primary evidence explicitly
  supports suspended use with rope or bungee; this is represented as a
  documented presentation and does not claim either accessory is supplied.
- The prior source-reviewed `twoBranchCord` metadata is restored with its
  four ordered through-bores, two branches, invisible anchor, and all five
  canonical poses. The 0.2 m anchor offset makes the visible suspension 50%
  shorter than the prior presentation. The source-marker Z-up coordinates are
  converted into importer Y-up coordinates as `(x,z,-y)`, aligning all four
  existing bores with the actual USDZ openings. Pose-specific exterior
  `cordContactPoints` clear the cylinder while retaining the same four bores
  and ordered pairs. Its 0.945 m per-branch display estimate covers the longest
  0.944143 m route. This capacity does not set visible hanging height.
  The `paired-12-8-6` and `rounded-tray` cameras are 30° oblique display
  estimates, retaining the selected face while exposing the hanging V instead
  of looking along the cord toward the board.
  All route, anchor, radius, and pose values marked `displayEstimate` remain
  presentation estimates.

### Lattice MXEdge Lift Large and Small — `pairedLeadCord`

- Exact-revision product view: [MXEdge Lift](https://latticetraining.com/product/mxedge-lift/), retained as `lattice-mxedge-product.html`.
- Exact-revision warning/configuration view: [MXEdge Lift warnings](https://latticetraining.com/warnings/mxedge-lift/), retained as `lattice-mxedge-warnings.html`.
- The cited instruction MP4 was not retained in this audit, so the page and warning artifacts are the complete basis for the promotion.
- The product and official instruction evidence establish the supplied cord
  arrangement and two exterior leads for both size-specific inventories. The
  Large remains MX22/MX16/MX12/28 mm mono; the Small remains
  MX18/MX14/MX8/25 mm mono.
- Each package binds two distinct external points on its existing body node.
  The shared body node is intentional and is permitted by the approved binding
  correction in `d04b611d4`; the points themselves remain distinct. The
  `pairedLeadCord` renderer draws two independent leads from one invisible
  anchor and does not invent a lead-to-lead or interior segment.

### Nature Climbing Stone Hanger — `pairedLeadCord`

- Exact-revision front gallery: [Stone Hanger — Granite](https://natureclimbing.com/products/stone-hanger-1), retained as `nature-stone-hanger.html`.
- Exact-revision oblique/gallery variant: [Granite Stone Hanger variant](https://natureclimbing.com/products/stone-hanger-1?variant=47783638597970), retained as `nature-stone-hanger-granite-variant.html`.
- The fragment-only attachment URL was not treated as a separate artifact because it resolves to the same page response; the two retained page responses are the complete basis for the promotion.
- The retained `current-gallery-2026-09-11` packet identifies the standard
  oak/Granite product, SKU `STONE_HANGER`, Shopify product `8768741048658`,
  variant `47783638597970`. The earlier identification of side hardware as
  hanging-cord mouths was incorrect; the manufacturer front image visibly
  places the hanging leads at the two upper corners.
- The interior route is explicitly **unknown**. The source technical drawing
  is not sectional engineering evidence; the model intentionally retains only
  the existing lateral hardware/sleeves, which do not determine the hanging
  cord endpoints. The package therefore
  uses `pairedLeadCord`, not a fabricated through-bore or central attachment.

## 2026-09-14 native route correction

Native SceneKit clearance rejected the old Lattice side-midpoint estimate
56 mm from its declared attachment (segment 26 of 31, 2.826 mm from wood with
3 mm required clearance). This was a real body crossing, not endpoint rounding.
After correcting the route, residual terminal contacts lie 1.17–1.52 mm along
the cord from its mouth, with nearby wood within the tube's clearance envelope.
Paired leads permit this contact only on the last segment, on the explicitly
bound nonselectable body, within a terminal span of one tube radius plus its
required clearance (5 mm in these packages). The entire remaining free span is
rechecked against the same triangle, and neighboring segments and other nodes
retain full clearance. A regression keeps the former 56 mm body-crossing
route unavailable. Conservative expanded triangle bounds skip only pairs that
cannot contact, reducing native loading time without changing the threshold.

Direct visual review of these manufacturer images establishes the exterior
mouth locations. Coordinates remain manually authored display estimates, not
pixel measurements or recovered model geometry:

| Retained image | Manufacturer URL | SHA-256 |
| --- | --- | --- |
| `2026-09-13-model-cord-snapshots/lattice-mxl-front.jpg` | https://latticetraining.com/app/uploads/2024/04/MXL-Front.jpg | `0811e08f36674e305d7c31c56a78bc3c77225b28ac41fa999170f9e55ec9aee8` |
| `2026-09-13-model-cord-snapshots/lattice-mxs-front.jpg` | https://latticetraining.com/app/uploads/2024/04/MXS-Front.jpg | `c2cac22888cc13ddf5f90054f52006db1c934ac7caccd3f19cafd71ecfead59c` |
| `2026-09-13-model-cord-snapshots/nature-granite-front.jpg` | https://natureclimbing.com/cdn/shop/files/Stone_Hanger_Granite_1.jpg?v=1760101291 | `8e8df7719638e42d4018a43254b3dac0bf3bfb5ac0d6ba149e9c92f634254f40` |

Both Lattice images show the upper pair of lead exits and the opposite bottom
cord return. Upright poses use the upper mouths; inverted poses explicitly
select the opposite mouths using `canonicalPoses.<position>.attachmentPoints`.
That optional map must provide both existing lead IDs and two distinct finite
points inside the model bounds. It is accepted only for `pairedLeadCord`.
Bindings, invisible anchor, board transforms, and exported meshes are unchanged.
The unseen internal route and visible bottom return
remain deliberately omitted by this two-exterior-lead display contract.

Nature's hanging cord similarly exits the upper corners, rather than the
mid-height side hardware. Its front/reverse poses share those top mouths.
No new internal route is claimed.

Verification used `Hang Ten Paseo gorgeous-dugong Review`, UUID
`5D2208DF-CC17-4EDC-9749-A7C3232E07CF`, iPhone 17 Pro / iOS 26.5, with
`xcodebuild test -project HangTen.xcodeproj -scheme HangTen -configuration Debug
-destination platform=iOS Simulator,id=5D2208DF-CC17-4EDC-9749-A7C3232E07CF
-derivedDataPath .context/DerivedData -parallel-testing-enabled NO` and explicit
focused test selectors. All real paired packages passed every canonical pose
with two visible non-pickable cylinder groups; the former invalid side route
remained unavailable. Parser preservation and pose-mouth solving passed (five
focused tests). The full suspension solver class plus existing Flash/native
and synthetic paired-lead regressions passed (43 tests). The shared malformed
parser matrix passed after registering the four new fixture names. Python
model/parser/audit validation was rerun after this correction: all 63 packages
remain valid and the cord audit now retains 8 represented / 6 excluded. A
subsequent branch verification used the tracked workspace virtual environment
to run the complete HangboardPackages pytest suite successfully. That Python
result does not establish iOS app or Simulator validation.

Actual DEBUG app detail screens were launched with
`HANGTEN_REVIEW_BOARD_DETAIL=1` and each `HANGTEN_REVIEW_BOARD_ID`. The four
workspace captures `gorgeous-dugong-lattice-large-cords.png`,
`gorgeous-dugong-lattice-small-cords.png`, `gorgeous-dugong-nature-cords.png`,
and `gorgeous-dugong-flash-cords.png` were visually inspected: all show a loaded
3D board, visible hanging leads, and an active highlighted contact. These are
simulator app-integration evidence, not physical-device PBR parity proof.

## Package changes

The promoted suspension edits were limited to `board.json` metadata. Physical
contacts, logical positions, media paths, orientation blocks, USDZ files, and
descriptor files were unchanged by those suspension edits. The subsequent
contact-first integration migrated board and descriptor schemas and was then
merged into this branch. At that historical post-integration boundary, comparison
against `origin/main` commit
`d7ca9c5c95953e296adaf763c89dd892d8c40cf9` shows no branch diff for any USDZ
or `.model.json` file. No cord, hardware, anchor, or raster fallback was baked
into a USDZ. The 2026-09-20 FTG-32 addition promotes its new hash-bound model
package; its exact artifact boundary is included in the table below.

| Package | Topology | Attachment/passage binding | USDZ `modelSHA256` | Descriptor file SHA-256 |
|---|---|---|---|---|
| `tension.flash-board` | `twoBranchCord` (existing) | Existing four ordered passages on `flash_board_body_008` | `4098ba4f8d8211683e6ec5c4466cd2725c0a040caae4a75e561d705315757524` | `f00bb82da1c5b9389c492dc78770e94f497367cc6cd6dc1e1d721b52ad3b56c0` |
| `captain-fingerfood.dual` | `pairedLeadCord` | Two ordered upper-lip routes to distinct recess terminals on `DUAL_skin_body_001`; through-hole/interior route omitted | `d7fbadb80de6eceee7617e12515a79acbf4347a0aebaa139bf2f5a4fc669da0e` | `1320ccae333047e2ffcdea0ac747923ec7e90c4cd16780df43cfb4aa81b6929e` |
| `captain-fingerfood.pocket` | `pairedLeadCord` | Two ordered upper-lip routes to distinct recess terminals on `body_skin_001`; through-hole/interior route omitted | `3c6194af77718c6a05b56a6f0968c14274ae3811b248c982e3ed9696cf8e848f` | `376e58a9dce8cae876c14ac286429e02780daf6c5c02a244e58703fd81cd4bc3` |
| `captain-fingerfood.unlevel` | `pairedLeadCord` | Two ordered upper-lip routes to distinct recess terminals on `Body_EditableSkin_001`; through-hole/interior route omitted | `ab52e45b9cdc1c011cfc8a3a6a75cf7c06d19b76f74dab5f53972a9a734b867b` | `e03da79d95fe6d2259d1ca15e4e709544742d67e6d6e874fdac11e13d15784ab` |
| `j-bryant.ftg-32` | `pairedLeadCord` | Two distinct centered front mouths on `Cube_001`; one physical loop, rear connecting segment deliberately omitted | `5b9c6eac0f5e2381d8d28833bdf0c723a4e512e94d034b000817f5230ac3bc3d` | `7b45d01a7bd46f71da3c0c1159afb89853a62d18b8d49bb002ed3fb0aaa4fbfa` |
| `yy.baguette-evo` | `twoBranchCord` | Four ordered through-bores on `body_mesh_001` | `a155242e9f1d230eca31c4b5ce855a1eddc82722ca3da7187ce3c3efc8a4c6bc` | `1b6f5a4048104a9d0b5b1a1c60002270332ddb54bd0e9a13f057594f34487f47` |
| `lattice.mxedge-lift-large` | `pairedLeadCord` | Two distinct points on `MXL_body_editable_skin_001` | `b8f9b7f75002f91b4ec45cf9b5212c7ae8a1ea6dffe9af9d5421a7566b9b2f25` | `831885d16fcd234ef7f7cbd224d931c18700d9fff64b569590d0b6e6a0bda4cb` |
| `lattice.mxedge-lift-small` | `pairedLeadCord` | Two distinct points on `Body_actual_surface_001` | `662f0681bea5356ba835df7b2505292ba59a1af090ec29281ef0a55d006777ee` | `0a029569bf3c9d232a335196a0fe77c41d27d34647318e005600a75aa8d5c2a4` |
| `nature.stone-hanger` | `pairedLeadCord` | Two distinct upper-corner mouths on `body_oak_mesh_001` | `177f1fddada5ca508b241bc3a3b211280e8e6c6f8886ce2729d154de9b0b97c1` | `569fdaaf067ace45b36c5954f23b4b226b4adc3740d249a14cf6b5383c68e97b` |

Every new attachment, passage, branch, anchor, cord, and canonical-pose
provenance includes `displayEstimate` where the source does not publish a
numeric display value. These values communicate the reviewed configuration;
they are not load, safety, knot, or physics claims.

## Validation

The audit command was run from the repository root:

```text
rtk scripts/hangboard-packages.sh audit-cords --root Hangboards --manifest docs/source-audits/2026-09-13-model-hangboard-cord-audit.json
```

Current result (2026-09-20; older dated verification entries below remain historical):

```json
{"decisions":{"excluded":27,"represented":13},"modelPackageIDs":["beastmaker-1000","beastmaker-2000","captain-fingerfood.dual","captain-fingerfood.pocket","captain-fingerfood.unlevel","clavellium-training-block","crimptonite.helium-mobile","dewoodstok-woodbord","escape-beta-22","escape.unlimited","evolv-kilter-basic-long","j-bryant.ftg-32","lattice-triple-rung","lattice.mxedge-lift-large","lattice.mxedge-lift-small","mammut.diamond-finger","metolius.climbers-edge","metolius.contact","metolius.foundry","metolius.light-rail-2","metolius.prime-rib","metolius.project","metolius.rock-rings-3d","metolius.simulator-3d","metolius.wood-grips-compact-ii","metolius.wood-grips-deluxe-ii","moon.armstrong","nature.stoak-board-iii","nature.stone-hanger","owl-climb.poker","soill.iron-palm-2","soill.split-palm","soill.training-tiles","target10a.linebreaker-base","tension.flash-board","the-hangboard.the-hangboard","trango.rock-prodigy-pivot","trango.rock-prodigy-training-center","yy.baguette-evo","yy.penta-evo"]}
```

`python3 -m json.tool` passed for all four edited board packages and
`git diff --check` passed. The focused XCTest invocation was attempted for the
new Baguette and paired-lead tests; this checkout could not start CoreSimulator
and could not resolve uncached SwiftPM dependencies while network access was
restricted. The tests remain committed as the executable acceptance contract;
the parent validation pass should rerun them in the prepared simulator/Xcode
environment.

### Task 5 verification record

- `PYTHONPATH=Tools/HangboardPackages/src python3 -m hangboard_packages.cli validate --root Hangboards --final-inventory` passed: 63 complete boards, zero drafts.
- `PYTHONPATH=Tools/HangboardPackages/src python3 -m hangboard_packages.cli status --root Hangboards` passed with the same complete inventory.
- `PYTHONPATH=Tools/HangboardPackages/src python3 -m hangboard_packages.cli audit-cords --root Hangboards --manifest docs/source-audits/2026-09-13-model-hangboard-cord-audit.json` passed after the 2026-09-15 coverage addendum: 20 model packages, 8 represented, 12 excluded.
- `PYTHONPATH=Tools/HangboardPackages/src python3 -m compileall -q Tools/HangboardPackages/src` passed, and `git diff --check` passed.
- At the time of Task 5, the system Python lacked `pytest` and restricted networking prevented a new environment from being bootstrapped. This historical environment limitation is superseded for the branch: the existing tracked workspace virtual environment subsequently ran the complete HangboardPackages pytest suite successfully.
- `xcodebuild build-for-testing ...` was blocked before compilation: CoreSimulatorService was unavailable and uncached Swift packages could not be cloned because `github.com` could not resolve. The focused and full XCTest suites therefore could not run in this environment.
- Temporary Xcode output was created under `.context/gorgeous-dugong-task5-xcode/`, then removed and verified absent.

### 2026-09-20 Batch 04 source-evidence handoff

Unpromoted Batch 04 packages remain outside this closed machine-readable
manifest until they become model-media packages: the validator requires record IDs to
equal the discovered model inventory, so adding future records now would make
the current audit invalid. The complete pre-promotion source decisions are
retained in [`2026-09-20-batch-04-3d-source-register.json`](2026-09-20-batch-04-3d-source-register.json)
and its source-to-contact audit. When each package is promoted, its exact
source fact and ruling must move into the closed manifest without changing the
retained byte evidence:

| Package | Source fact | Promotion decision/ruling |
| --- | --- | --- |
| `crimptonite.helium-mobile` | `documentedSuspension` | Promoted 2026-09-20: represented `pairedLeadCord` exterior leads only; no inferred interior route or `twoBranchCord`. |
| `metolius.light-rail-2` | `documentedSuspension` | Promoted 2026-09-20: represented `pairedLeadCord` upper-entry exterior leads only; no underside mouth or hidden vertical bore. |
| `metolius.rock-rings-3d` | `documentedSuspension` | Promoted 2026-09-20: two independent pairedLeadCord systems; no inter-unit connection or central through-bore. |
| `yy.penta-evo` | `documentedSuspension` | Promoted 2026-09-20: two independent paired exterior loops through the existing central ring; no invented channel or knot. |
| `owl-climb.poker` | `noDocumentedSuspension` | exclude. |
| `trango.rock-prodigy-pivot` | `noDocumentedSuspension` | exclude; pulley-kit ropes are not Pivot suspension. |

### 2026-09-20 Helium model promotion — `pairedLeadCord`

Astra reviewed the exact retained HE2 front and HE6 reverse originals and
manually authored the final capsule, three front recesses, rounded rear, and
four exterior mouth surfaces. The delivered GLB remains PARTIAL, with
`sourceFidelityApproval: false`, and was inspected but not promoted. The
manufacturer HE1 envelope is 400 × 58 × 24 mm and the nominal opposing lips
remain 14/22 mm and 10/18 mm. No wood species, factory rounding radius, recess
width, bore diameter, or hidden route is inferred.

Ruling: `pairedLeadCord exterior leads only; no inferred interior route or twoBranchCord.`
The two retained source views are regular-file snapshots in
`2026-09-13-model-cord-snapshots/crimptonite-helium-mobile-front.jpg` (SHA-256
`9f5dea470c326d32c6bde1dd5427f2bfb95a81b99ae258c320ae9deec0384a40`) and
`crimptonite-helium-mobile-reverse.jpg` (SHA-256
`5d5c18d45ae6d30e6e951aa158a30b303d42d4583d18d4a6d82075ff5de50f6a`).
Their original URLs and retailer hosting tier remain explicit in the JSON.

Source-Z-up markers `(x,y,z)` convert to descriptor Y-up as `(x,z,-y)`:
front `[-0.186,0,0.012]` / `[0.186,0,0.012]`, reverse
`[-0.186,0,-0.012]` / `[0.186,0,-0.012]`. Only the two front endpoints bind
the exterior leads to nonselectable attachment geometry. Reverse mouths remain
visible geometry with no lead-to-lead connection. Each short mouth surface
ends at an authored display clipping depth; that cut-off is not a claim that
the physical opening is blind. The paired-lead schema requires one point-only
mouth record for each lead; these repeat the two front endpoints and supply no
entry/exit bore or ordered passage pair. The invisible anchor offset is
`[0,0.12,0.34]` and per-lead rest length is `0.41` m, both
`authored-display-estimate`. The front offset keeps the 2 mm cord clear of the
small mouth rim and front face; it does not establish physical hanging geometry.

All unsurveyed silhouette rounding, recess widths/transitions, mouth diameters
and clipping depths, constant pale-timber material, camera values, primary
identity pose, invisible anchor offset and per-lead rest length are
`authored-display-estimate`. HE1's supplied 4 mm cord supports the 2 mm radius;
its total length is unknown. Cord meshes and anchor are transient runtime
metadata, absent from USDZ, picking, and accessibility. All mounting/screw
holes, screws, cleats, brackets, hardware, logos, raster textures, and fallback
media are omitted from this display model. Omission is not a claim that such
hardware could never be used with the physical product.

The original `primary` presentation ID is preserved. Historical presentation
remediation lifecycle conversion is deferred to Task 14 under the controller's
ID-collision ruling; this promotion does not alter that manifest.

### 2026-09-20 Light Rail 2.0 model promotion — `pairedLeadCord`

Ruling: `pairedLeadCord upper-entry exterior leads only; no underside mouth or hidden vertical bore.`

Astra directly authored one reversible rounded rail with the continuous front
recess seen in the exact LR2 manufacturer product image and archived Treeline
field image. The delivered GLB remains PARTIAL source material, not promoted
geometry. Manufacturer labels 40/20/40/15 govern the four canonical contacts;
the retailer 40/26/19/15 conflict does not create another contact.

| Source patch | Canonical contact | Imported node |
| --- | --- | --- |
| `lr-top-jug-40` | `jug-40-20mm-side` | `lr_top_jug_40_001` |
| `lr-recess-lower-20` | `edge-20` | `lr_recess_lower_20_001` |
| `lr-bottom-jug-40` | `jug-40-15mm-side` | `lr_bottom_jug_40_001` |
| `lr-recess-upper-15` | `edge-15` | `lr_recess_upper_15_001` |

Retained regular-file snapshots are
`2026-09-13-model-cord-snapshots/metolius-light-rail-2-product.jpg` (SHA-256
`7b263d3e31773efe6abdb4dcaeee7e9fcea532696427dbbabfefbb5ba72bb272`) and
`metolius-light-rail-2-field.jpg` (SHA-256
`93cc83c29d011c0b1b84aa02b51f8f1df4e167805ab27bffde48938c83c7fa4a`).
The manufacturer URL and independent exact archive replay URL/tier are in the
JSON. The live Treeline replacement bytes remain unaccepted, as documented in
the Batch 04 source-to-contact audit.

The approved source-Z-up entry markers `[-0.213,0,0.038]` and
`[0.213,0,0.038]` map via `(x,y,z) → (x,z,-y)` to descriptor Y-up points
`[-0.213,0.038,0]` and `[0.213,0.038,0]`. Each binds only its corresponding
nonselectable `left_upper_entry_001` or `right_upper_entry_001` surface. The
saved Y coordinate is `0.037999999`, a 1 nm inward clamp to the float32-imported
descriptor bound, preserving the same source entry region. The
schema-required point-only passage repeats that endpoint, not a bore route.
The two exterior entry regions clip 3 mm below the top surface as an
`authored-display-estimate`; this cut-off does not claim the physical entry is
blind. No underside mouth, hidden connection or supplied knot is modeled.

The 457 × 76 × 38 mm envelope follows the retained manufacturer metric facts.
Nominal 40 mm jug labels do not enlarge the 38 mm body thickness. Unsurveyed
roundovers, channel width/returns/back transition, entry radii/clipping, rear
profile and constant pale wood material are `authored-display-estimate`.
The final imported surface is closed, has Euler characteristic 2 (no handles
or through-holes), and exact underside rays at both entry X coordinates meet
solid surfaces. Its seven nodes comprise one body, four contacts and two
attachments. No screws, mounting holes, hardware, textures, raster media or
fallback geometry is retained. Hardware omission describes the display model,
not a physical safety or installation claim.

Positions retain the exact historical functional grouping: `20mm-side` owns
`jug-40-20mm-side` and `edge-20`; `15mm-side` owns `jug-40-15mm-side` and
`edge-15`. Upright rotation is identity; inverted rotation is a normalized
180° turn about the front axis (`[0,0,1,0]`). Both bind the same two original
upper-entry attachment regions. Inversion moves those existing physical
regions underneath the displayed rail; it does not create new underside
mouths. Explicit `cordContactPoints` guide each visible lead around its outer
end silhouette and approach its original rotated endpoint from outside.
These controller-approved exterior guides are `authored-display-estimate`,
not a claim that the reference establishes their exact bends or hidden route.
There are no attachment overrides, internal segments, extra attachment nodes,
or connections between leads.

After visual review, inverted guides follow the existing 6 mm rounded end
profile at a 3.4 mm cord-centerline offset (the production clearance requirement
is 3 mm), with maximum X = ±0.2319 m. This replaces the rejected 16.5 mm
offset/88 mm floating verticals with close, rounded exterior bends. A 6 mm
upright exterior entry approach centers each tube in the same approved mouth.

The invisible anchor is 0.24 m above the untransformed upper bound. Both leads
have the same 0.431878843 m display rest length and 2 mm estimated radius.
Upright translation `[0,-0.133053677,0]` and inverted zero translation
reconcile the extra exterior route consumed by inversion with that fixed
length. Each complete pose route requires about 0.430378843 m, leaving 1.5 mm
of display slack. All anchor/translation/route/radius/material/camera values
are `authored-display-estimate`. The approximately 0.133 m change in displayed
board height is intentional and included in camera reframing, not asserted
physical metrology. Both final imported-USDZ poses pass the unmodified production solver
and clearance gate. Front, inverted, rear, end, oblique, four contact-highlight
and production-solved cord captures are retained under the task-owned review
evidence directory; current-source iOS behavior remains final Task 14 review.

Historical presentation-remediation conversion remains Task 14.

### 2026-09-20 Rock Rings reusable-unit promotion

Ruling: two independent pairedLeadCord systems; no inter-unit connection or central through-bore.

The exact approved manufacturer black/white photograph and owner front/rear
and lateral photographs are copied as regular files into the canonical snapshot
directory. Their original URLs, SHA-256 values and revision/provenance caveats
remain in the manifest and the Batch 04 source register. RR3 supports the two
roof exits per unit; RR6 shows a solid rear; RR7 shows the lateral access mouth.
The older bright-spot interpretation does not authorize a central through-bore.

One manually authored 146 × 184 × 57 mm physical unit has four generic slots:
`jug`, `pocket-40`, `pocket-32`, `pocket-25`. Two identical, unreflected instances
map them to the eight existing left/right contact identities. The top jug and
three inward pockets remain distinct selectable surfaces. Roof exits and lateral
windows are nonselectable attachment geometry; only roof points bind the two
visible leads of each independent cord system. No route through the side
windows or between openings is claimed. Clipped shallow aperture geometry,
unsurveyed radii, perimeter/rear sections and neutral resin appearance are
`authored-display-estimate`; clipping does not claim a physically blind cavity.
All mounting/screw holes and hardware are omitted.

The current reusable paired-lead solver preserves fixed world anchors, and
the package parser validates suspension poses without instance-base context.
Consequently each unit has an identity base and its own `primary` pose
translation (X = ±0.105 m). Its independent invisible anchor has matching
world X, 0.19 m above the unit bounds. These positions, cord radius/rest length
and camera choices are display estimates. This uses the existing complete
suspension-pose mechanism without changing the renderer or inventing routing.
Historical presentation-remediation conversion remains Task 14.

### 2026-09-15 Batch 01 fixed-board exclusion addendum

The closed manifest now covers the six Batch 01 model packages below. Each
reviewed source packet supports a fixed/wall-mounted presentation and does not
document a supplied or integral suspension system. Mounting information is not
treated as evidence of a cord.

| Catalog package ID | Retained manufacturer artifact | Exact revision ID | SHA-256 |
| --- | --- | --- | --- |
| `dewoodstok-woodbord` | `dewoodstok-woodbord-manufacturer-product-2026-09-15.html` | `dewoodstok-woodbord-current-2026-09-15` | `d5943951b72683ec0cdde126e86c6c4834db78b71f03dbd8d19cc1ffc4236ef7` |
| `escape.unlimited` | `escape-unlimited-manufacturer-product-2026-09-15.html` | `escape-unlimited-current-2026-09-15` | `1a72a7b98971ee6b14816ab2e933180d7289dae1444918b69d422ad004192cc3` |
| `evolv-kilter-basic-long` | `evolv-kilter-basic-long-manufacturer-product-2026-09-15.html` | `evolv-basic-training-board-long-current-2026-09-15` | `9bdfd3691762591ba86e145d57ba49c0d9c86c3211b39f2706718ec561b53163` |
| `metolius.wood-grips-deluxe-ii` | `metolius-wood-grips-deluxe-ii-manufacturer-product-2026-09-15.html` | `metolius-wood-grips-deluxe-ii-current-2026-09-15` | `0bd3c297deb023356fafa181a48a193c93723e779321d054a3d0f3cc82c9ad82` |
| `moon.armstrong` | `moon-armstrong-manufacturer-product-2026-09-15.html` | `moon-armstrong-ash-current-2026-09-15` | `7ef4629d7164f3c62469db4a65ab303636fb82eae5d690bc7d131b1d3b5e639d` |
| `target10a.linebreaker-base` | `target10a-linebreaker-base-manufacturer-product-2026-09-15.html` | `target10a-linebreaker-base-current-2026-09-15` | `65afde30db091cc985306c2b2b9cb077c4fde392d45b7ee8c64ab4385180757d` |

The retained artifacts are literal 2026-09-15 HTTPS manufacturer responses;
they supersede the packets' earlier unavailable-download limitation. The
source-register observations remain the basis for the fixed/wall-mounted fact.
`target10a-linebreaker-base` is the package-directory/artifact slug; the
catalog and manifest use its canonical `target10a.linebreaker-base` ID.

Historical inventory validation after all six packages became model-backed:

```json
{"decisions":{"excluded":18,"represented":8}}
```
