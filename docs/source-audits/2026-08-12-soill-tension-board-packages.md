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
| `soill-training-tiles` | `product`: [Training Tiles product page](https://soillholds.com/products/training-tiles-so-ill-x-meagan-martin); `workouts`: [official workouts](https://soillholds.com/pages/meagan-martin-training-tiles-workouts); `front-photos`: product-page gallery | Product identity, collaboration name, gallery images, and four official workout videos. | The reviewed sources did not publish dimensions or a named/depth hold inventory. |
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
  contact receives a scalar `sizeMillimeters` value.

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
