# All-board hold audit

**Reviewed:** 2026-08-25  
**Scope:** all 44 discoverable `Hangboards/*/board.json` packages.

This is a hold-metadata reconciliation, not an image-derived geometry process.
For each package, the review render placed its stable JSON hold ID at the
center of that hold's existing canonical geometry union. Those review-only
PNG files live in the workspace-owned `.context/audit-board-hold-id-overlays/`
directory and are deliberately not package content. The full Workbench capture
of every board and rendered region lives alongside them in
`.context/audit-board-holds-overlays-full/`.

## Evidence and field rules

The manufacturer source and per-model hold mapping are maintained in the
catalog source audits listed below; each source links the official product page
plus, where supplied, the manufacturer's front/oblique image and numbered
depth or hold guide.

- [2026-08-19 catalog metadata audit](2026-08-19-all-board-metadata-hold-audit.md)
  covers the original 33-package catalog.
- [2026-08-20 catalog-completion audit](2026-08-20-complete-hangboard-catalog.md)
  covers Foundry, Prime Rib, Wood Grips II Deluxe, The Hangboard, Flash Board,
  Light Rail 2.0, Rock Rings 3D, TravelBoard, La Baguette, Baguette Evo, and
  Penta Evo.
- [2026-08-12 Metolius audit](2026-08-12-metolius-board-packages.md) supplies
  the direct numbered diagrams used for the Contact correction below.

`kind` is retained only where a primary product page, official labelled diagram,
or official product view establishes the surface class. `fingerCapacity` is
retained only for explicitly named mono/duo/finger-pocket positions. Published
edge and pocket depths are recorded as `sizeMillimeters`; the separate
`depthRangeMillimeters` field is reserved for genuinely variable measurements.
Sloper radii, round-surface diameters, and unsupported values are kept in a
source-backed name or omitted, never coerced into a depth field.

## Reconciliation ledger

The `kind` column is a complete per-board count of the reviewed IDs. Capacity
and fixed-depth values are exactly the non-omitted fields in the package and
are traceable to the linked audits; an em dash means the source did not justify
that optional value. The product URL is the current primary manufacturer page.

| Package | IDs | Kind counts | Source |
| --- | ---: | --- | --- |
| beastmaker-1000 | 22 | edge 7; jug 2; pocket 10; sloper 3 | [manufacturer](https://www.beastmaker.co.uk/collections/fingerboards/products/beastmaker-1000-series); [positioned secondary comparison](https://thehangboard.com/pages/beastmaker-1000-vs-2000) |
| beastmaker-2000 | 27 | edge 6; pocket 16; sloper 5 | [manufacturer](https://www.beastmaker.co.uk/products/beastmaker-2000-series); [positioned secondary comparison](https://thehangboard.com/pages/beastmaker-1000-vs-2000) |
| dewoodstok-woodbord | 17 | pocket 16; sloper 1 | [manufacturer](https://www.dewoodstok.nl/product/hangboard-woodbord/) |
| escape-beta-22 | 22 | edge 8; jug 4; pinch 4; sloper 6 | [manufacturer](https://escapeclimbing.com/products/ec72100) |
| escape.unlimited | 7 | edge 6; sloper 1 | [manufacturer](https://escapeclimbing.com/products/ec72000) |
| evolv-kilter-basic-long | 4 | edge 3; jug 1 | [manufacturer](https://www.evolvsports.com/en-us/basic-training-board-_long_-66-0000082105) |
| frictitious.doormount-pro-7 | 13 | edge 10; jug 1; pocket 2 | [manufacturer](https://frictitiousclimbing.com/en-ca/products/doormount-pro) |
| frictitious.megalith | 18 | edge 15; jug 1; pocket 2 | [manufacturer](https://frictitiousclimbing.com/products/megalith) |
| lattice-triple-rung | 3 | edge 3 | [manufacturer](https://latticetraining.com/product/triple-rung-wooden-hangboard/) |
| metolius.climbers-edge | 15 | edge 10; jug 2; sloper 3 | [manufacturer](https://www.metoliusclimbing.com/products/climbers-edge-board) |
| metolius.contact | 33 | edge 4; jug 2; pinch 2; pocket 22; sloper 3 | [manufacturer](https://www.metoliusclimbing.com/products/contact-training-board) |
| metolius.foundry | 18 | edge 3; jug 2; pinch 2; pocket 10; sloper 1 | [manufacturer](https://www.metoliusclimbing.com/products/foundry-training-board) |
| metolius.light-rail-2 | 4 | edge 2; jug 2 | [manufacturer](https://www.metoliusclimbing.com/products/light-rail) |
| metolius.prime-rib | 3 | edge 3 | [manufacturer](https://www.metoliusclimbing.com/products/prime-rib) |
| metolius.project | 15 | edge 4; jug 2; pocket 8; sloper 1 | [manufacturer](https://www.metoliusclimbing.com/products/project-training-board) |
| metolius.rock-rings-3d | 8 | jug 2; pocket 6 | [manufacturer](https://www.metoliusclimbing.com/collections/training-equipment/products/rock-rings-3d) |
| metolius.simulator-3d | 29 | edge 8; jug 3; pocket 16; sloper 2 | [manufacturer](https://www.metoliusclimbing.com/collections/training-boards/products/simulator-training-board) |
| metolius.wood-grips-compact-ii | 19 | edge 4; jug 2; pocket 10; sloper 3 | [manufacturer](https://www.metoliusclimbing.com/products/wood-grips-ii-training-boards) |
| metolius.wood-grips-deluxe-ii | 26 | edge 6; jug 2; pocket 15; sloper 3 | [manufacturer](https://www.metoliusclimbing.com/products/wood-grips-ii-training-boards) |
| moon.armstrong | 21 | edge 12; jug 3; pocket 4; sloper 2 | [manufacturer](https://moonclimbing.com/moon-armstrong-fingerboard-beech.html) |
| nature.stoak-board-iii | 7 | edge 6; jug 1 | [manufacturer](https://natureclimbing.com/products/stoak-board-iii) |
| soill.iron-palm-2 | 8 | edge 3; jug 1; pinch 2; sloper 2 | [manufacturer](https://soillholds.com/products/iron-palm-2-0) |
| soill.split-palm | 14 | edge 8; jug 2; sloper 4 | [manufacturer](https://soillholds.com/products/split-palm) |
| soill.training-tiles | 16 | edge 10; pocket 2; sloper 4 | [manufacturer](https://soillholds.com/products/training-tiles-so-ill-x-meagan-martin) |
| target10a.linebreaker-base | 24 | edge 6; jug 2; pocket 12; sloper 4 | [manufacturer](https://www.target10a.com/en/linebreaker-boards/409-linebreaker-base-trainingsboard.html) |
| tension.flash-board | 7 | edge 7 | [manufacturer](https://tensionclimbing.com/products/flash-board-2) |
| tension.grindstone | 14 | edge 13; jug 1 | [manufacturer](https://tensionclimbing.com/products/grindstone) |
| tension.honestone | 12 | edge 9; pocket 2; sloper 1 | [manufacturer](https://tensionclimbing.com/products/honestone) |
| tension.whetstone | 12 | edge 9; jug 1; pocket 2 | [manufacturer](https://tensionclimbing.com/products/whetstone) |
| the-hangboard.the-hangboard | 15 | edge 12; jug 2; sloper 1 | [manufacturer](https://thehangboard.com/products/hangboard) |
| trango.rock-prodigy-forge | 20 | edge 8; pocket 8; sloper 4 | [manufacturer](https://trango.com/products/rock-prodigy-forge) |
| trango.rock-prodigy-natural | 14 | edge 6; jug 2; pocket 6 | [manufacturer](https://trango.com/products/rock-prodigy-natural) |
| trango.rock-prodigy-pivot | 18 | edge 10; pinch 2; pocket 4; sloper 2 | [manufacturer](https://trango.com/products/rock-prodigy-pivot?variant=33101615890537) |
| trango.rock-prodigy-training-center | 24 | edge 6; jug 2; pinch 4; pocket 10; sloper 2 | [manufacturer](https://trango.com/products/rock-prodigy-training-center) |
| yy.baguette-evo | 19 | edge 18; jug 1 | [manufacturer](https://www.yyvertical.com/en/products/baguette-evo) |
| yy.baguette | 6 | edge 5; jug 1 | [manufacturer](https://www.yyvertical.com/en/products/la-baguette-poutre-escalade) |
| yy.penta-evo | 14 | edge 8; jug 2; pocket 4 | [manufacturer](https://www.yyvertical.com/en/products/penta-evo) |
| yy.travelboard | 6 | edge 3; jug 1; pocket 2 | [manufacturer](https://www.yyvertical.com/en/products/la-travelboard-poutre-dentrainement) |
| yy.verticalboard-evo | 25 | edge 9; jug 3; pocket 8; sloper 5 | [manufacturer](https://www.yyvertical.com/en/products/verticalboard-evo) |
| yy.verticalboard-first | 17 | edge 12; jug 2; sloper 3 | [manufacturer](https://www.yyvertical.com/en/products/verticalboard-first) |
| yy.verticalboard-light | 12 | edge 7; jug 2; sloper 3 | [manufacturer](https://www.yyvertical.com/en/products/verticalboard-light) |
| yy.verticalboard-one | 20 | edge 10; jug 3; pocket 4; sloper 3 | [manufacturer](https://www.yyvertical.com/en/products/verticalboard-one) |
| zlagboard.evo | 21 | edge 7; jug 2; sloper 12 | [manufacturer](https://www.zlagboard.com/hangboards) |
| zlagboard.pro | 28 | edge 14; jug 2; sloper 12 | [manufacturer](https://www.zlagboard.com/hangboards) |

## Corrected mapping: Beastmaker 1000 and 2000

The positioned [secondary comparison](https://thehangboard.com/pages/beastmaker-1000-vs-2000)
now maps exact front contacts for both Beastmakers. Its values and finger labels
are recorded as secondary provenance in the metadata ledger, not as
manufacturer claims. The complete stable-ID mapping and the two diagram/text
discrepancies—1000 center **53 vs 50 mm**, 2000 `front-middle-5` **52 vs 50
mm**—are documented in the [Beastmaker source audit](2026-08-12-beastmaker-board-packages.md).

`front-lower-9` is the direct geometry mirror of `front-lower-1`. The
positioned map also establishes all of the explicitly labelled mirrored pairs.

## Corrected mapping: Metolius Contact

The current [Metolius Contact product page](https://www.metoliusclimbing.com/products/contact-training-board)
states that the board has variable-width pinches, 11 pocket forms with 2-,
3-, and 4-finger variants, four central edges, top-mounted jugs, rounded
slopers, and a flat sloper. Its official [numbered depth diagram](https://www.metoliusclimbing.com/cdn/shop/files/con-num-dep_341f2901-a11e-4256-a4c3-0531110c730e.jpg?v=1762201170)
maps the exact positions: mirrored `1` pinches, `2` outer jugs, `3` 63 mm
round slopers, pockets `4`–`14`, center flat sloper `15`, and center edges
`16`–`19`.

| Source position | Correct JSON IDs | Kind | Capacity | Depth treatment |
| --- | --- | --- | ---: | --- |
| 1 | `pinch-left`, `pinch-right` | pinch | — | omitted |
| 2 | `jug-left`, `jug-right` | jug | — | omitted |
| 3 | `round-sloper-3-left`, `round-sloper-3-right` | sloper | — | 63 mm describes a round sloper, not a published edge/pocket depth |
| 4–14 | `pocket-4-*` through `pocket-14-*` | pocket | source-labelled 2, 3, or 4 | `sizeMillimeters` maps the published pocket depth |
| 15 | `flat-sloper-center` | sloper | — | 53 mm remains a source-backed sloper label, not a structured edge/pocket depth |
| 16–19 | `edge-16-center` through `edge-19-center` | edge | — | 15, 35, 28, and 23 mm in `sizeMillimeters` |

This audit replaces the generic `hold-31`/`hold-32` identifiers with their
manufacturer-supported right-side jug and pinch identities and adds the two
missing source-labelled round sloper contacts. No finger capacity or depth is
invented for those surfaces.
