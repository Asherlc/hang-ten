# 3D model hangboard cord audit

Initial audit: 2026-09-13; latest coverage addendum: 2026-09-20
Scope: every model-media package discovered under `Hangboards/`  
Decision: approved for package promotion after human review of the retained
exact-revision views and attachment views

## Result

The audit covers all 34 discovered model packages. Nine have documented
suspended presentation evidence and render transient cord geometry; 25 remain
excluded because their reviewed product evidence does not establish a
suspended presentation. Optional user-provided rope or bungee is sufficient
for documented suspended presentation, but it is never described as supplied
or integral.

| Decision | Count | Packages |
|---|---:|---|
| `represented` | 9 | `captain-fingerfood.dual`, `captain-fingerfood.pocket`, `captain-fingerfood.unlevel`, `j-bryant.ftg-32`, `lattice.mxedge-lift-large`, `lattice.mxedge-lift-small`, `nature.stone-hanger`, `tension.flash-board`, `yy.baguette-evo` |
| `excluded` | 25 | Beastmaker 1000/2000; Clavellium Training Block; deWOODSTOK Woodbord; Escape Beta 22/Unlimited; Evolv Kilter Basic Long; Lattice Triple Rung; Mammut Diamond Finger; Metolius Climber's Edge/Contact/Foundry/Prime Rib/Project/Simulator 3-D/Wood Grips Compact II/Wood Grips Deluxe II; Moon Armstrong; Nature Stoak Board III; So iLL Iron Palm 2/Split Palm/Training Tiles; Target10a Linebreaker Base; The Hangboard; Trango Rock Prodigy Training Center |

The machine-readable record is [`2026-09-13-model-hangboard-cord-audit.json`](2026-09-13-model-hangboard-cord-audit.json). Its record set is deliberately closed: the cord-audit command discovers model media directly and requires exact equality with the manifest package IDs.

## Evidence review and approval

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
{"decisions":{"excluded":25,"represented":9},"modelPackageIDs":["beastmaker-1000","beastmaker-2000","captain-fingerfood.dual","captain-fingerfood.pocket","captain-fingerfood.unlevel","clavellium-training-block","dewoodstok-woodbord","escape-beta-22","escape.unlimited","evolv-kilter-basic-long","j-bryant.ftg-32","lattice-triple-rung","lattice.mxedge-lift-large","lattice.mxedge-lift-small","mammut.diamond-finger","metolius.climbers-edge","metolius.contact","metolius.foundry","metolius.prime-rib","metolius.project","metolius.simulator-3d","metolius.wood-grips-compact-ii","metolius.wood-grips-deluxe-ii","moon.armstrong","nature.stoak-board-iii","nature.stone-hanger","soill.iron-palm-2","soill.split-palm","soill.training-tiles","target10a.linebreaker-base","tension.flash-board","the-hangboard.the-hangboard","trango.rock-prodigy-training-center","yy.baguette-evo"]}
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
