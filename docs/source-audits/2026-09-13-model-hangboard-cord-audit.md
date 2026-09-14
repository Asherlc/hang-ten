# 3D model hangboard cord audit

Date: 2026-09-13  
Scope: every model-media package discovered under `Hangboards/`  
Decision: approved for package promotion after human review of the retained
exact-revision views and attachment views

## Result

The audit covers all 14 discovered model packages. Five have a source-backed
supplied/integral cord and render a transient cord presentation; nine are
excluded because their reviewed product evidence does not establish a supplied
or integral cord.

| Decision | Count | Packages |
|---|---:|---|
| `represented` | 5 | `tension.flash-board`, `yy.baguette-evo`, `lattice.mxedge-lift-large`, `lattice.mxedge-lift-small`, `nature.stone-hanger` |
| `excluded` | 9 | Beastmaker 1000/2000; Captain Fingerfood DUAL/POCKET/UNLEVEL; Lattice Triple Rung; Metolius Prime Rib/Project/Wood Grips Compact II |

The machine-readable record is [`2026-09-13-model-hangboard-cord-audit.json`](2026-09-13-model-hangboard-cord-audit.json). Its record set is deliberately closed: the cord-audit command discovers model media directly and requires exact equality with the manifest package IDs.

## Evidence review and approval

The human review retained two materially distinct exact-revision views and an
attachment view for every represented board. The URLs below are the primary
source entries recorded in the JSON manifest; query/fragment variants identify
the reviewed gallery or attachment region, not a different product revision.

### Tension Flash Board — `twoBranchCord`

- Exact-revision manufacturer view: [Tension Flash Board](https://tensionclimbing.com/products/flash-board-2).
- Exact-revision hanging view: [Backcountry Flash Board](https://www.backcountry.com/tension-flash-board).
- Attachment detail: [Flash Board listing](https://www.amazon.com/Tension-Climbing-Flash-Board/dp/B07H8JYQ5G).
- The retained packet establishes the supplied portable cord, two ordered
  passage pairs, and four canonical positions. Existing suspension metadata and
  descriptor hashes were preserved byte-for-byte.

### YY Vertical Baguette Evo — `twoBranchCord`

- Exact-revision manufacturer views: [manufacturer English listing](https://www.yyvertical.com/en/products/baguette-evo) and [manufacturer EU listing](https://www.yyvertical.com/en-eu/products/baguette-evo).
- Attachment detail: [four-bore gallery region](https://www.yyvertical.com/en/products/baguette-evo#cord-passages).
- The current **Baguette Evo, Turn & Pull version**, SKU `YY BAGUETTE EVO`,
  EAN `3760305271822`, is the retained revision. The evidence packet states
  that the supplied continuous cord is visibly configured through four physical
  bores, ordered left-to-right in the front view. It does not claim an exact
  hidden rope traversal, bore tolerance, or cord dimensions.
- The package declares four ordered through-bores (`cord-passage-1` through
  `cord-passage-4`) on `body_mesh_001`, paired as left and right branches. All
  route, anchor, radius, and pose values marked `displayEstimate` are display
  metadata, not product specifications.

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

| Package | Topology | Attachment/passage binding | Descriptor SHA-256 |
|---|---|---|---|
| `tension.flash-board` | `twoBranchCord` (existing) | Existing four ordered passages on `flash_board_body_008` | `fd2c3e057c9feee1d6da57448bd9e4d58510ae8a6c60120282e51b13c228019c` |
| `yy.baguette-evo` | `twoBranchCord` | Four ordered through-bores on `body_mesh_001` | `6eb4159f02b4dd35a4a2a7708faf94286d21cfab41f93cab68e28e0b20fb8c` |
| `lattice.mxedge-lift-large` | `pairedLeadCord` | Two distinct points on `MXL_body_editable_skin_001` | `ed755fce098c3471e8ad8070c58f1fa8092954c560f7b0ecc38a084749e3b16` |
| `lattice.mxedge-lift-small` | `pairedLeadCord` | Two distinct points on `Body_actual_surface_001` | `f619520ff5493ad4df26154e69cb1cac2998b7ae0bfb1332551d6199fd991419` |
| `nature.stone-hanger` | `pairedLeadCord` | Two distinct lateral-mouth points on `body_oak_mesh_001` | `a35adb07928a69ea7a39d5756f1cbbeebcbd2964b4ae613f3cd088552c7432d9` |

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
{"decisions":{"excluded":9,"represented":5},"modelPackageIDs":["beastmaker-1000","beastmaker-2000","captain-fingerfood.dual","captain-fingerfood.pocket","captain-fingerfood.unlevel","lattice-triple-rung","lattice.mxedge-lift-large","lattice.mxedge-lift-small","metolius.prime-rib","metolius.project","metolius.wood-grips-compact-ii","nature.stone-hanger","tension.flash-board","yy.baguette-evo"]}
```

`python3 -m json.tool` passed for all four edited board packages and
`git diff --check` passed. The focused XCTest invocation was attempted for the
new Baguette and paired-lead tests; this checkout could not start CoreSimulator
and could not resolve uncached SwiftPM dependencies while network access was
restricted. The tests remain committed as the executable acceptance contract;
the parent validation pass should rerun them in the prepared simulator/Xcode
environment.
