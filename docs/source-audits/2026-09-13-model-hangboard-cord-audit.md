# 3D model hangboard cord audit

Date: 2026-09-13  
Scope: every model-media package discovered under `Hangboards/`  
Decision: approved for package promotion after human review of the retained
exact-revision views and attachment views

## Result

The audit covers all 14 discovered model packages. Eight have documented
suspended presentation evidence and render transient cord geometry; six remain
excluded because their reviewed product evidence does not establish a
suspended presentation. Optional user-provided rope or bungee is sufficient
for documented suspended presentation, but it is never described as supplied
or integral.

| Decision | Count | Packages |
|---|---:|---|
| `represented` | 8 | `tension.flash-board`, `captain-fingerfood.dual`, `captain-fingerfood.pocket`, `captain-fingerfood.unlevel`, `lattice.mxedge-lift-large`, `lattice.mxedge-lift-small`, `nature.stone-hanger`, `yy.baguette-evo` |
| `excluded` | 6 | Beastmaker 1000/2000; Lattice Triple Rung; Metolius Prime Rib/Project/Wood Grips Compact II |

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

### Tension Flash Board — `twoBranchCord`

- Exact-revision manufacturer view: [Tension Flash Board](https://tensionclimbing.com/products/flash-board-2), retained as `tension-flash-product.html`.
- Exact-revision training view: [Flash Board training article](https://tensionclimbing.com/blogs/training-tools/hangboard-overview-the-flash-board), retained as `tension-flash-training-blog.html`.
- The Backcountry and Amazon responses were unavailable as usable source artifacts at audit time, so they are not represented as evidence.
- The retained packet establishes the supplied portable cord, two ordered
  passage pairs, and four canonical positions. Existing suspension metadata and
  descriptor hashes were preserved byte-for-byte.

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
  ordered `contactPointsInModel` per lead. The renderer draws the free span and
  the authored exterior route without inventing a through-bore, knot, hardware,
  or safety claim.
- The shared anchor offset is the user-approved compact 0.15 m display
  estimate, 50% below the prior presentation value.
- Attachment coordinates, anchor offsets, cord radius, and pose camera values
  are explicitly display estimates. Existing hold IDs, positions, model bytes,
  descriptor bytes, and orientation values are unchanged.

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
  shorter than the prior presentation. Its 0.885 m per-branch display estimate
  is the minimum rounded capacity that keeps every fixed route solvable; the
  originally proposed exact-half 0.7 m value is shorter than the directed
  route. All route, anchor, radius, and pose values marked `displayEstimate`
  remain presentation estimates.

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
remain valid and the cord audit now retains 8 represented / 6 excluded. The
focused Python test command remains unavailable in this checkout because the
`pytest` module is not installed; the equivalent package validation, JSON
parsing, audit, and bytecode checks passed.

Actual DEBUG app detail screens were launched with
`HANGTEN_REVIEW_BOARD_DETAIL=1` and each `HANGTEN_REVIEW_BOARD_ID`. The four
workspace captures `gorgeous-dugong-lattice-large-cords.png`,
`gorgeous-dugong-lattice-small-cords.png`, `gorgeous-dugong-nature-cords.png`,
and `gorgeous-dugong-flash-cords.png` were visually inspected: all show a loaded
3D board, visible hanging leads, and an active highlighted hold. These are
simulator app-integration evidence, not physical-device PBR parity proof.

## Package changes

All promoted package edits are limited to `board.json` suspension metadata.
Holds, logical positions, media paths, orientation blocks, USDZ files, and
descriptor files were preserved. No cord, hardware, anchor, or raster fallback
was baked into a USDZ.

| Package | Topology | Attachment/passage binding | USDZ `modelSHA256` | Descriptor file SHA-256 |
|---|---|---|---|---|
| `tension.flash-board` | `twoBranchCord` (existing) | Existing four ordered passages on `flash_board_body_008` | `4098ba4f8d8211683e6ec5c4466cd2725c0a040caae4a75e561d705315757524` | `fd2c3e057c9feee1d6da57448bd9e4d58510ae8a6c60120282e51b13c228019c` |
| `captain-fingerfood.dual` | `pairedLeadCord` | Two ordered upper-lip routes to distinct recess terminals on `DUAL_skin_body_001`; through-hole/interior route omitted | unchanged | unchanged |
| `captain-fingerfood.pocket` | `pairedLeadCord` | Two ordered upper-lip routes to distinct recess terminals on `body_skin_001`; through-hole/interior route omitted | unchanged | unchanged |
| `captain-fingerfood.unlevel` | `pairedLeadCord` | Two ordered upper-lip routes to distinct recess terminals on `Body_EditableSkin_001`; through-hole/interior route omitted | unchanged | unchanged |
| `yy.baguette-evo` | `twoBranchCord` | Four ordered through-bores on `body_mesh_001` | `a155242e9f1d230eca31c4b5ce855a1eddc82722ca3da7187ce3c3efc8a4c6bc` | `6eb4159f02b4dd35a4a2a7708faf94286d21cfab41f93cab68e28e0b20fb8c` |
| `lattice.mxedge-lift-large` | `pairedLeadCord` | Two distinct points on `MXL_body_editable_skin_001` | `b8f9b7f75002f91b4ec45cf9b5212c7ae8a1ea6dffe9af9d5421a7566b9b2f25` | `ed755fce098c3471e8ad8070c58f1fa8092954c560f7b0ecc38a084749e3b16` |
| `lattice.mxedge-lift-small` | `pairedLeadCord` | Two distinct points on `Body_actual_surface_001` | `662f0681bea5356ba835df7b2505292ba59a1af090ec29281ef0a55d006777ee` | `f619520ff5493ad4df26154e69cb1cac2998b7ae0bfb1332551d6199fd991419` |
| `nature.stone-hanger` | `pairedLeadCord` | Two distinct upper-corner mouths on `body_oak_mesh_001` | `177f1fddada5ca508b241bc3a3b211280e8e6c6f8886ce2729d154de9b0b97c1` | `a35adb07928a69ea7a39d5756f1cbbeebcbd2964b4ae613f3cd088552c7432d9` |

Every new attachment, passage, branch, anchor, cord, and canonical-pose
provenance includes `displayEstimate` where the source does not publish a
numeric display value. These values communicate the reviewed configuration;
they are not load, safety, knot, or physics claims.

## Validation

The audit command was run from the repository root:

```text
PYTHONPATH=Tools/HangboardPackages/src Tools/HangboardPackages/.venv/bin/python -m hangboard_packages.cli audit-cords --root Hangboards --manifest docs/source-audits/2026-09-13-model-hangboard-cord-audit.json
```

Result:

```json
{"decisions":{"excluded":6,"represented":8},"modelPackageIDs":["beastmaker-1000","beastmaker-2000","captain-fingerfood.dual","captain-fingerfood.pocket","captain-fingerfood.unlevel","lattice-triple-rung","lattice.mxedge-lift-large","lattice.mxedge-lift-small","metolius.prime-rib","metolius.project","metolius.wood-grips-compact-ii","nature.stone-hanger","tension.flash-board","yy.baguette-evo"]}
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
- `PYTHONPATH=Tools/HangboardPackages/src python3 -m hangboard_packages.cli audit-cords --root Hangboards --manifest docs/source-audits/2026-09-13-model-hangboard-cord-audit.json` passed: 14 model packages, 8 represented, 6 excluded.
- `PYTHONPATH=Tools/HangboardPackages/src python3 -m compileall -q Tools/HangboardPackages/src` passed, and `git diff --check` passed.
- `python3 -m pytest Tools/HangboardPackages/tests -q` was unavailable because pytest is not installed. The repository wrapper could not bootstrap its virtual environment because restricted networking could not resolve the package index (`setuptools>=84.0.0`).
- `xcodebuild build-for-testing ...` was blocked before compilation: CoreSimulatorService was unavailable and uncached Swift packages could not be cloned because `github.com` could not resolve. The focused and full XCTest suites therefore could not run in this environment.
- Temporary Xcode output was created under `.context/gorgeous-dugong-task5-xcode/`, then removed and verified absent.
