# So iLL and Tension board-package evidence audit

Checked 2026-08-12. This historical audit preserves the official So iLL and
Tension sources reviewed for six models. Their old incomplete package art was
removed. Future geometry is directly authored from primary evidence under
`docs/ADDING_A_BOARD.md`; unsupported optional facts remain omitted.

The tables identify the official sources reviewed for each independent model;
sources are never shared across models. Official product views support visible
boundaries for direct path authoring. They do not establish optional depth,
capacity, posture, or feature values unless those facts are explicitly labeled.

| Candidate | Official source keys and URLs | Fields that source establishes | Historical evidence limitation |
| --- | --- | --- | --- |
| `soill-iron-palm-2` | `product`: [Iron Palm 2.0 product page](https://soillholds.com/products/iron-palm-2-0); `front-photos`: the product-page gallery | Product identity; slopers, pinches, edges, an incut top rung, thumb catches, and various edge sizes. | The reviewed page did not publish overall dimensions or a numbered/depth hold chart. |
| `soill-split-palm` | `product`: [Split Palm product page](https://soillholds.com/products/split-palm); `front-photos`: the product-page gallery | Product identity and gallery images. | The reviewed page did not publish dimensions or a numbered hold guide. |
| `soill-training-tiles` | `product`: [Training Tiles • So iLL x Meagan Martin](https://soill.ca/products/training-tiles-so-ill-x-meagan-martin); `workouts`: [official workouts](https://soillholds.com/pages/meagan-martin-training-tiles-workouts); `front-photos`: product-page gallery | Product identity; each tile approximately `14 × 8 in`; grouped 3 in top pocket, 25°/54 mm and 12°/64 mm slopers, 44/50 mm middle positive edges, and 36/31/24 mm bottom flat edges. | The Canada source does not map those grouped facts to Hang Ten’s 20 selectable IDs; its singular top-pocket group does not correspond one-to-one to the app’s four top-pocket regions. |
| `tension-grindstone` | `product`: [Grindstone product page](https://tensionclimbing.com/collections/shop-all/products/grindstone); `overview`: [Tension hangboards](https://tensionclimbing.com/pages/hangboards) | Overall dimensions; full-width jug; 50 mm center edge; 30/25/20/15/10/8 mm edge families. | The reviewed sources did not map every listed depth to a numbered left/right contact. |
| `tension-honestone` | `product`: [Honestone product page](https://tensionclimbing.com/products/honestone); `overview`: [Tension hangboards](https://tensionclimbing.com/pages/hangboards) | Overall dimensions; 35°/45° top slopers; 25 mm center edge and one-finger pockets; 20/15/10/8 mm edge families. | The reviewed sources listed families rather than a numbered contact map. |
| `tension-whetstone` | `product`: [Whetstone product page](https://tensionclimbing.com/products/whetstone); `overview`: [Tension hangboards](https://tensionclimbing.com/pages/hangboards) | Overall dimensions; top jug; 40 mm center edge and two-finger pockets; 40/30/25/20 mm edge families. | The reviewed sources did not provide a numbered or dimensioned contact map. |

## Current authoring interpretation

For each model, reconcile the named hold families with every visible physical
contact, preserve continuous stepped cavities as one logical hold when
appropriate, and mirror only verified symmetric pairs. Directly author each
path, omit unsupported optional facts, validate the complete flat package, and
visually review normal and active alignment.

## Tension direct-authoring addendum

Checked 2026-08-19 against the current product pages, the official Hangboards
overview, and the linked official gallery images. The three Tension packages
were authored from scratch; no removed draft geometry was restored or used as
an input.

### Shared evidence and geometry mapping

- [`overview`](https://tensionclimbing.com/pages/hangboards) establishes each
  model's named hold families and supplies the official front, close, oblique,
  and in-use views.
- The model-specific `front` image is preserved pixel-for-pixel as
  `assets/primary.png`. It establishes visible contact boundaries and the
  engraved left/right depth layout. The canonical normalized paths were drawn
  directly against that image and reviewed against the official oblique and
  in-use view. A fresh retrieval of the three linked CDN files on 2026-08-19
  produced zero differing pixels for every package image (`magick compare
  -metric AE` = `0`). Grindstone and Honestone retained the retrieved PNG
  encoding, while Whetstone is a lossless PNG re-encode. Provenance is based on
  decoded pixel equality rather than mutable CDN response-byte hashes.
- The visible paired stepped recess on each side is one continuous physical
  contact even though it exposes two labeled depths. It is therefore one hold,
  and the range is retained in its descriptive name rather than collapsed into
  a single `sizeMillimeters` value.
- Regular stepped-recess and center-edge boundaries use operator-selected
  `roundedRectangle` or `pill` constraints. The continuous top contacts and
  the sculpted pocket boundaries remain freeform. The saved paths remain the
  rendering and highlight source of truth.
- Exact left/right frame mirroring is used for the paired product geometry
  shown symmetrically in the official front views. No optional grip posture or
  feature taxonomy was inferred.

### `tension-grindstone`

- `product`: [Grindstone](https://tensionclimbing.com/products/grindstone)
- `front`: [Grindstone1.png](https://tensionclimbing.com/cdn/shop/files/Grindstone1.png?v=1726542525)
- `close`: [Grindstone2.png](https://tensionclimbing.com/cdn/shop/files/Grindstone2.png?v=1726542525)
- `in-use`: [Grindstone3.jpg](https://tensionclimbing.com/cdn/shop/files/Grindstone3.jpg?v=1726542525)
- Identity and dimensions map directly to `manufacturer`, `name`,
  `productURL`, and `dimensions`. The product feature list and engraved front
  view establish exactly eight physical contacts under the continuous-contact
  rule: one full-width bar-style top jug, one 50 mm center one-arm edge, and
  mirrored continuous 30/25, 20/15, and 10/8 mm stepped edges. Only the center
  contact receives a scalar `sizeMillimeters` value. The six named stepped
  contacts map to `depthRangeMillimeters` ranges of 25...30, 15...20, and
  8...10 respectively; their two documented depths remain a range because
  each pair is one continuous physical contact.

### `tension-honestone`

- `product`: [Honestone](https://tensionclimbing.com/products/honestone)
- `front`: [Honestone1.png](https://tensionclimbing.com/cdn/shop/files/Honestone1.png?v=1726542571)
- `close`: [Honestone2.png](https://tensionclimbing.com/cdn/shop/files/Honestone2.png?v=1726542571)
- `in-use`: [Honestone3.jpg](https://tensionclimbing.com/cdn/shop/files/Honestone3.jpg?v=1726542571)
- Identity and dimensions map directly to `manufacturer`, `name`,
  `productURL`, and `dimensions`. Tension describes the top as 35° and 45°
  slopers with continuously variable curvature; the uninterrupted sculpted
  contact is represented once, not split at its changing angle. Together with
  the 25 mm center incut edge, mirrored 25 mm one-finger pockets, and mirrored
  continuous 20/15 and 10/8 mm stepped edges, that yields eight physical
  contacts. Scalar size and capacity metadata is retained only for the center
  edge and explicitly named one-finger pockets.

### `tension-whetstone`

- `product`: [Whetstone](https://tensionclimbing.com/products/whetstone)
- `front`: [Whetstone1.png](https://tensionclimbing.com/cdn/shop/files/Whetstone1.png?v=1726542637)
- `close`: [Whetstone2.png](https://tensionclimbing.com/cdn/shop/files/Whetstone2.png?v=1726542637)
- `in-use`: [Whetstone3.jpg](https://tensionclimbing.com/cdn/shop/files/Whetstone3.jpg?v=1752612393)
- Identity and dimensions map directly to `manufacturer`, `name`,
  `productURL`, and `dimensions`. The product feature list and engraved front
  view establish exactly eight physical contacts: one continuous sculpted
  ergo-bump top jug, one 40 mm center incut edge, mirrored 40 mm two-finger
  pockets, and mirrored continuous 40/30 and 25/20 mm stepped edges. Scalar
  size and capacity metadata is retained only for the center edge and explicitly
  named two-finger pockets.

## So iLL direct-authoring addendum

Checked 2026-08-19 against the current So iLL product pages, the product-page
feature metafields embedded by the manufacturer, and the official straight-on
gallery images below. The three packages were authored from scratch. No removed
draft geometry was restored or used as an input.

### Shared evidence and geometry mapping

- Each `front` JPEG is the product page's official straight-on gallery image.
  It was losslessly decoded and re-encoded as the required
  `assets/primary.png`; decoded-pixel comparison against the retrieved source
  is zero for all three assets (`magick compare -metric AE` = `0`). No crop,
  registration, source alignment, mask, contour generation, vectorization, or
  automatic geometry operation was performed.
- Every canonical normalized path was deliberately drawn against that complete
  2000 × 2000 presentation image. The official front views show purposefully
  sculpted, organic resin boundaries even on the rails, so every contact is
  retained as freeform geometry. No shape constraint was inferred or attached.
- The product views establish bilateral mirrored layouts for the paired
  contacts. The right-side canonical paths are exact horizontal mirrors of the
  reviewed left-side paths. One logical hold is retained for every distinct
  physical contact surface.
- The feature metafields establish measurements and product-level hold
  families. A measurement is attached to an individual hold only when the
  manufacturer maps it to that named physical contact. Finger capacities,
  grip posture, feature tags, and unsupported material claims are omitted.

### `soill-iron-palm-2`

- `product`: [Iron Palm 2.0](https://soillholds.com/products/iron-palm-2-0)
- `front`: [official straight-on image](https://cdn.shopify.com/s/files/1/0424/1145/products/iron-palm-20-so-ill-white-12-01-so-ill-218626.jpg?v=1677258150)
- The product description establishes slopers, pinches, edges, a thicker incut
  top rung, and thumb catches. The current feature metafield establishes
  `27 × 11.5 × 4 in`, two 3-inch pinches, the top jug rail, and top-to-bottom
  40 mm rounded, 25 mm flat, and 15 mm flat crimp rails. Together with the two
  visible slopers, that freezes exactly eight contacts. The current
  manufacturer value for the second rail is **25 mm**; the earlier 35 mm
  working note was stale and is not retained.

### `soill-split-palm`

- `product`: [Split Palm](https://soillholds.com/products/split-palm)
- `front`: [official straight-on image](https://cdn.shopify.com/s/files/1/0424/1145/products/split-palm-so-ill-white-12-01-so-ill-385627.jpg?v=1677258498)
- The product description establishes a two-piece Jason Kehl design. The
  current feature metafield establishes each piece at
  `16.5 × 11 × 3 7/8 in` (`419 × 279.4 × 98.4 mm`) and explicitly enumerates,
  per piece, an incut top-center jug, large sloper, smaller sloper, 38.1 mm
  center sloping rail, 25.4 mm center flat rail, 12.7 mm outer crimp rail, and
  12.7 mm bottom-center sloping crimp rail. That freezes exactly seven contacts
  per piece and fourteen total. The exact decimal rail measurements are recorded
  in `sizeMillimeters` for their corresponding contacts.

### `soill-training-tiles`

- `product`: [Training Tiles • So iLL x Meagan Martin](https://soill.ca/products/training-tiles-so-ill-x-meagan-martin)
- `workouts`: [official workout page](https://soillholds.com/pages/meagan-martin-training-tiles-workouts)
- `front`: [official straight-on image](https://cdn.shopify.com/s/files/1/0424/1145/products/training-tiles-so-ill-x-meagan-martin-so-ill-white-12-01-so-ill-670960.jpg?v=1677258630)
- The Canada product listing establishes the two-piece collaboration, each tile
  at approximately `14 × 8 in`, and grouped family facts: a 3 in top pocket;
  25°/54 mm and 12°/64 mm slopers; 44/50 mm middle positive edges; and
  36/31/24 mm bottom flat edges. It does not supply a 20-contact ID map. Its
  singular top-pocket group has no one-to-one correspondence with Hang Ten’s
  four top-pocket regions, so the app’s 20 descriptive roles remain explicitly
  adapted and no grouped size, angle, depth, or capacity is assigned to an
  individual contact.

## 2026-08-25 source-audited metadata batch

The seven current product pages and the official gallery views linked above
were re-opened on 2026-08-25. So iLL's current product HTML still exposes the
manufacturer feature text used in the 2026-08-19 addendum: Iron Palm 2.0's
40/25/15 mm crimp rails and Split Palm's exact 38.1/25.4/12.7/12.7 mm rails
per piece. The Canada Training Tiles listing supplies the grouped facts recorded
above, but not a per-contact map from them to the app’s 20 selectable IDs.
Tension's current pages still publish the Flash Board's global edge list and
the exact Grindstone, Honestone, and Whetstone feature lists.

Stable-ID overlays were generated and manually reviewed in a workspace-owned
`.context` directory. Flash Board was reviewed in both `three-edge` and `two-edge`
presentations; the other six packages each use one presentation. The overlays
are review aids only. They did not change geometry or establish a kind or
measurement.

No review capture supplies a manufacturer Training Tiles contact map. The Canada
listing supports the grouped family facts, but they remain unassigned to
individual app contacts because the source’s grouped pocket/contact count and
the app’s 20 selections do not map one-to-one.

The tables below are the complete contact-by-contact type audit. Exact
left/right pairs are grouped only after both visible stable IDs were compared
with the named manufacturer source position. So iLL's terms `rail` and `crimp
rail` map to the schema's closed `edge` kind; that is a source-term taxonomy
mapping, not a classification inferred from pixels.

### Tension-reviewed label map

| Board | Exact manufacturer label / position | Stable hold ID(s) | Verified kind | Verified optional value |
| --- | --- | --- | --- | --- |
| Flash Board | `Edges: 8 mm, 10 mm, 15 mm, 20 mm`; official three-edge view | `three-edge-left`, `three-edge-center`, `three-edge-right` | `edge` | none; depths are not position-mapped |
| Flash Board | same global edge list; official two-edge views | `two-edge-left`, `two-edge-right` | `edge` | none; depths are not position-mapped |
| Flash Board | `Edges: Small Crimps`; official two-edge views | `small-crimp-left`, `small-crimp-right` | `edge` | none; the separate overview's approximately 6 mm category is not exact |
| Grindstone | `Full Width "Bar-style" Top Jug` | `top-jug` | `jug` | none |
| Grindstone | `10 mm edges`; `8 mm edges` | `edge-10-8-left`, `edge-10-8-right` | `edge` | `depthRangeMillimeters` 8–10 |
| Grindstone | `30 mm edges`; `25 mm edges` | `edge-30-25-left`, `edge-30-25-right` | `edge` | `depthRangeMillimeters` 25–30 |
| Grindstone | `50 mm center one-arm edge` | `edge-50-center` | `edge` | `sizeMillimeters` 50 |
| Grindstone | `20 mm edges`; `15 mm edges` | `edge-20-15-left`, `edge-20-15-right` | `edge` | `depthRangeMillimeters` 15–20 |
| Honestone | One continuous `35°`/`45°` macro sloper with continuously variable curvature | `macro-sloper-left`, `macro-sloper-left-center`, `macro-sloper-right-center`, `macro-sloper-right` | adapted `sloper` regions | none; angles/curvature are not scalar depth |
| Honestone | `25 mm 1-finger pockets` | `mono-left`, `mono-right` | `pocket` | size 25; finger capacity 1 |
| Honestone | `20 mm edges`; `15 mm edges` | `edge-20-15-left`, `edge-20-15-right` | `edge` | `depthRangeMillimeters` 15–20 |
| Honestone | `25 mm center edge w/10 degree incut` | `edge-25-center` | `edge` | `sizeMillimeters` 25 |
| Honestone | `10 mm edges`; `8 mm edge` | `edge-10-8-left`, `edge-10-8-right` | `edge` | `depthRangeMillimeters` 8–10 |
| Whetstone | `Custom jug profile with ergo-bumps` | `top-ergo-jug` | `jug` | none |
| Whetstone | `40 mm 2-finger pockets` | `pocket-40-left`, `pocket-40-right` | `pocket` | size 40; finger capacity 2; `twoFingerPocket` |
| Whetstone | `40 mm edges`; `30 mm edges` | `edge-40-30-left`, `edge-40-30-right` | `edge` | `depthRangeMillimeters` 30–40 |
| Whetstone | `40 mm center edge w/10 degree incut` | `edge-40-center` | `edge` | `sizeMillimeters` 40 |
| Whetstone | `25 mm edges`; `20 mm edges` | `edge-25-20-left`, `edge-25-20-right` | `edge` | `depthRangeMillimeters` 20–25 |

The engraved official front views supply the spatial mapping for the three
fixed Tension boards. Each paired two-depth recess is visibly and physically
continuous, so its two published shelves remain one stable hold with a range.
No range was collapsed to a scalar value.

### So iLL reviewed label map

| Board | Exact manufacturer label / position | Stable hold ID(s) | Verified kind | Verified optional value |
| --- | --- | --- | --- | --- |
| Iron Palm 2.0 | `Big Slopers`; description: `Slopers` | `sloper-left`, `sloper-right` | `sloper` | none |
| Iron Palm 2.0 | `2 Pinches: 3" Width` | `pinch-left`, `pinch-right` | `pinch` | none; width is not depth |
| Iron Palm 2.0 | `Top Jug Rail`; description: `thicker, comfy incut top rung` | `top-incut-jug` | `jug` | none |
| Iron Palm 2.0 | `Edges`; `First Crimp Rail (slightly rounded): 40mm` | `rounded-edge-40` | `edge` | `sizeMillimeters` 40 |
| Iron Palm 2.0 | `Edges`; `Second Crimp Rail (flat): 25mm` | `flat-edge-25` | `edge` | `sizeMillimeters` 25 |
| Iron Palm 2.0 | `Edges`; `Bottom Crimp Rail (flat): 15mm` | `flat-edge-15` | `edge` | `sizeMillimeters` 15 |
| Split Palm | `Top Center Rail: Incut Jug` (one per piece) | `jug-left`, `jug-right` | `jug` | none |
| Split Palm | `Large Sloper` (one per piece) | `large-sloper-left`, `large-sloper-right` | `sloper` | none |
| Split Palm | `Smaller Sloper` (one per piece) | `small-sloper-left`, `small-sloper-right` | `sloper` | none |
| Split Palm | `Center Sloping Rail: 1.5" (38.1mm)` (one per piece) | `sloping-rail-38-left`, `sloping-rail-38-right` | `edge` | `sizeMillimeters` 38.1 |
| Split Palm | `Center Flat Rail: 1" (25.4mm)` (one per piece) | `flat-edge-25-left`, `flat-edge-25-right` | `edge` | `sizeMillimeters` 25.4 |
| Split Palm | `Outer Crimp Rail: 1/2" (12.7mm)` (one per piece) | `outer-crimp-12-left`, `outer-crimp-12-right` | `edge` | `sizeMillimeters` 12.7 |
| Split Palm | `Bottom Center Sloping Crimp Rail - 1/2" (12.7mm)` (one per piece) | `bottom-sloping-crimp-12-left`, `bottom-sloping-crimp-12-right` | `edge` | `sizeMillimeters` 12.7 |
| Training Tiles | Canada listing: each tile `14 × 8 in`; grouped 3 in top pocket, 25°/54 mm and 12°/64 mm slopers, 44/50 mm middle positive edges, and 36/31/24 mm bottom flat edges; no 20-contact ID map | `top-jug-*`, `top-pocket-{outer,inner}-*`, `upper-sloper-{outer,inner}-*`, `middle-edge-{outer,inner}-*`, `bottom-edge-{outer,center,inner}-*` | adapted visual jug, pocket, sloper, and edge roles | none; grouped facts are not assigned to individual contacts because the source’s top-pocket group and the app’s four top-pocket regions do not map one-to-one |

### Field outcomes and retained package data

Every reviewed hold has an explicit ledger outcome for each field. The current
reconciliation distinguishes manufacturer-verified kinds from deliberately
labelled app adaptations. Training Tiles has 20 adapted visual roles and no
per-contact optional values. In particular:

- the 14 Tension stepped-edge values remain ranges on continuous contacts;
- Honestone's one-finger pockets retain size and capacity but no `gripType`,
  because the checked-in schema has no one-finger-pocket enum;
- Training Tiles has Canada-source grouped family facts but no 20-contact ID
  map; the source’s top-pocket group does not map one-to-one to the app’s four
  top-pocket regions, so its app-adapted contacts carry no size, range,
  capacity, posture, or feature value;
- Flash Board retains no scalar depth because the global size list is not
  mapped to its five recess IDs, and its small crimp value is only approximate
  on the separate overview page;
- pinch width, sloper angle/radius, and product dimensions are not written as
  contact depth; and
- no source states simultaneous hand capacity or an exact package feature-tag
  array. Non-pocket finger capacity is recorded as not applicable; every other
  unsupported optional field remains absent with a source-specific ledger
  reason.

## 2026-08-26 Iron Palm 2.0 presentation-asset correction

- `product`: [Iron Palm 2.0](https://soillholds.com/products/iron-palm-2-0)
  (the accepted So iLL product source already recorded above).
- Defect: seed-based enclosed-background clearing treated pale Iron Palm board
  material as background and made it transparent. The package is removed from
  `_ENCLOSED_BACKGROUND_SEEDS`; its presentation is not eligible for that
  migration behavior.
- Replacement-art prompt: “Create a clean, front-on, faithful simplified
  illustration of the same So iLL Iron Palm 2.0. Preserve the wide horizontal
  presentation, bilateral large round top slopers, bilateral lower 3-inch
  pinches and thumb catches, and three centered horizontal rails in the same
  positions and proportions. Keep every board surface opaque on a perfectly
  flat solid `#00ff00` chroma-key background, with no shadows, text, or
  watermark.” The generated chroma-key image was converted using the supported
  chroma-key workflow; no repository backdrop-removal migration was used.
- The final 1536 × 1024 RGBA presentation was reviewed on a dark canvas. A
  second bounded isolated-simulator run (iPhone 17 Pro / iOS 26.3) displayed
  the normal board plus the in-app active 25 mm flat-rail preview and active
  round-sloper state; their overlays aligned with opaque board material. A
  focused XCTest UI test now launches the existing Debug board picker, opens
  Iron Palm, taps its accessibility-exposed `Right sloper` board-map button,
  and observes `boardDetail.selectedHold.sloper-right`. The test log records
  the deterministic `Tap "Right sloper" Button` event before that selected-hold
  assertion passes, establishing the selected canonical path's in-app tap
  resolution without changing geometry. The app's interaction path remains
  the canonical `BoardHoldPathShape` used for the visual overlay.
