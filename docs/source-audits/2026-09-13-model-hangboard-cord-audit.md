# 3D model hangboard cord audit

Date: 2026-09-13  
Scope: every model-media package discovered under `Hangboards/`  
Decision: approved for package promotion after human review of the retained
exact-revision views and attachment views

## Result

The audit covers all 14 discovered model packages. Four have a source-backed
supplied/integral cord and render a transient cord presentation; ten are
excluded because their reviewed product evidence does not establish a supplied
or integral cord. Baguette Evo is excluded: YY Vertical's primary evidence
establishes optional rope or bungee use, not an included or integral cord.

| Decision | Count | Packages |
|---|---:|---|
| `represented` | 4 | `tension.flash-board`, `lattice.mxedge-lift-large`, `lattice.mxedge-lift-small`, `nature.stone-hanger` |
| `excluded` | 10 | Beastmaker 1000/2000; Captain Fingerfood DUAL/POCKET/UNLEVEL; Lattice Triple Rung; Metolius Prime Rib/Project/Wood Grips Compact II; YY Vertical Baguette Evo |

The machine-readable record is [`2026-09-13-model-hangboard-cord-audit.json`](2026-09-13-model-hangboard-cord-audit.json). Its record set is deliberately closed: the cord-audit command discovers model media directly and requires exact equality with the manifest package IDs.

## Evidence review and approval

The human review retained exact-revision evidence records for every discovered
model package. Every evidence entry records its exact revision ID, source tier,
retained snapshot SHA-256/path, and URL. Every record also carries an explicit
`humanApproval` object; the validator rejects missing or incomplete provenance
and approvals. The URLs below are the primary source entries recorded in the
JSON manifest; query/fragment variants identify the reviewed gallery or
attachment region, not a different product revision.

### Tension Flash Board — `twoBranchCord`

- Exact-revision manufacturer view: [Tension Flash Board](https://tensionclimbing.com/products/flash-board-2).
- Exact-revision hanging view: [Backcountry Flash Board](https://www.backcountry.com/tension-flash-board).
- Attachment detail: [Flash Board listing](https://www.amazon.com/Tension-Climbing-Flash-Board/dp/B07H8JYQ5G).
- The retained packet establishes the supplied portable cord, two ordered
  passage pairs, and four canonical positions. Existing suspension metadata and
  descriptor hashes were preserved byte-for-byte.

### YY Vertical Baguette Evo — excluded

- Exact-revision manufacturer views: [manufacturer English listing](https://www.yyvertical.com/en/products/baguette-evo) and [manufacturer EU listing](https://www.yyvertical.com/en-eu/products/baguette-evo).
- Attachment detail: [four-bore gallery region](https://www.yyvertical.com/en/products/baguette-evo#cord-passages).
- The current **Baguette Evo, Turn & Pull version**, SKU `YY BAGUETTE EVO`,
  EAN `3760305271822`, is the retained revision. Primary evidence establishes
  only optional use with rope or bungee; it does not establish that either is
  supplied or integral.
- The package retains its model, holds, positions, orientation, and descriptor
  unchanged, but has no `media.suspension` and renders no cord.

### Lattice MXEdge Lift Large and Small — `pairedLeadCord`

- Exact-revision product view: [MXEdge Lift](https://latticetraining.com/product/mxedge-lift/).
- Exact-revision warning/configuration view: [MXEdge Lift warnings](https://latticetraining.com/warnings/mxedge-lift/).
- Supplied-cord attachment view: [How to use the MXEdge Lift](https://latticetraining.com/app/uploads/2024/05/MXEdge-Lift-How-to.mp4).
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

- Exact-revision front gallery: [Stone Hanger — Granite](https://natureclimbing.com/products/stone-hanger-1).
- Exact-revision oblique/gallery variant: [Granite Stone Hanger variant](https://natureclimbing.com/products/stone-hanger-1?variant=47783638597970).
- Attachment detail: [lateral cord-port region](https://natureclimbing.com/products/stone-hanger-1#cord-ports).
- The retained `current-gallery-2026-09-11` packet identifies the standard
  oak/Granite product, SKU `STONE_HANGER`, Shopify product `8768741048658`,
  variant `47783638597970`, and two observed lateral cord-port mouths.
- The interior route is explicitly **unknown**. The source technical drawing
  is not sectional engineering evidence; the model intentionally retains only
  the observed lateral mouths and short display sleeves. The package therefore
  uses `pairedLeadCord`, not a fabricated through-bore or central attachment.

## Package changes

All promoted package edits are limited to `board.json` suspension metadata.
Holds, logical positions, media paths, orientation blocks, USDZ files, and
descriptor files were preserved. No cord, hardware, anchor, or raster fallback
was baked into a USDZ.

| Package | Topology | Attachment/passage binding | USDZ `modelSHA256` | Descriptor file SHA-256 |
|---|---|---|---|---|
| `tension.flash-board` | `twoBranchCord` (existing) | Existing four ordered passages on `flash_board_body_008` | `4098ba4f8d8211683e6ec5c4466cd2725c0a040caae4a75e561d705315757524` | `fd2c3e057c9feee1d6da57448bd9e4d58510ae8a6c60120282e51b13c228019c` |
| `yy.baguette-evo` (excluded) | none | No cord metadata; optional rope/bungee is not promoted | `a155242e9f1d230eca31c4b5ce855a1eddc82722ca3da7187ce3c3efc8a4c6bc` | `6eb4159f02b4dd35a4a2a7708faf94286d21cfab41f93cab68e28e0b20fb8c` |
| `lattice.mxedge-lift-large` | `pairedLeadCord` | Two distinct points on `MXL_body_editable_skin_001` | `b8f9b7f75002f91b4ec45cf9b5212c7ae8a1ea6dffe9af9d5421a7566b9b2f25` | `ed755fce098c3471e8ad8070c58f1fa8092954c560f7b0ecc38a084749e3b16` |
| `lattice.mxedge-lift-small` | `pairedLeadCord` | Two distinct points on `Body_actual_surface_001` | `662f0681bea5356ba835df7b2505292ba59a1af090ec29281ef0a55d006777ee` | `f619520ff5493ad4df26154e69cb1cac2998b7ae0bfb1332551d6199fd991419` |
| `nature.stone-hanger` | `pairedLeadCord` | Two distinct lateral-mouth points on `body_oak_mesh_001` | `177f1fddada5ca508b241bc3a3b211280e8e6c6f8886ce2729d154de9b0b97c1` | `a35adb07928a69ea7a39d5756f1cbbeebcbd2964b4ae613f3cd088552c7432d9` |

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
{"decisions":{"excluded":10,"represented":4},"modelPackageIDs":["beastmaker-1000","beastmaker-2000","captain-fingerfood.dual","captain-fingerfood.pocket","captain-fingerfood.unlevel","lattice-triple-rung","lattice.mxedge-lift-large","lattice.mxedge-lift-small","metolius.prime-rib","metolius.project","metolius.wood-grips-compact-ii","nature.stone-hanger","tension.flash-board","yy.baguette-evo"]}
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
- `PYTHONPATH=Tools/HangboardPackages/src python3 -m hangboard_packages.cli audit-cords --root Hangboards --manifest docs/source-audits/2026-09-13-model-hangboard-cord-audit.json` passed: 14 model packages, 4 represented, 10 excluded.
- `PYTHONPATH=Tools/HangboardPackages/src python3 -m compileall -q Tools/HangboardPackages/src` passed, and `git diff --check` passed.
- `python3 -m pytest Tools/HangboardPackages/tests -q` was unavailable because pytest is not installed. The repository wrapper could not bootstrap its virtual environment because restricted networking could not resolve the package index (`setuptools>=84.0.0`).
- `xcodebuild build-for-testing ...` was blocked before compilation: CoreSimulatorService was unavailable and uncached Swift packages could not be cloned because `github.com` could not resolve. The focused and full XCTest suites therefore could not run in this environment.
- Temporary Xcode output was created under `.context/gorgeous-dugong-task5-xcode/`, then removed and verified absent.
