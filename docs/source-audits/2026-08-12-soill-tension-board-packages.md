# So iLL and Tension board-package evidence audit

Checked 2026-08-12. This audit covers six generated-image candidates in
`Hangboards/`. A candidate raster is presentation material only; it is not
manufacturer evidence for the complete, per-hold package contract. None of the
six candidates is registered in `Hangboards/catalog.json`.

The package schema requires a cited, model-specific source for every physical
hold and every runtime hold field (`id`, name, label, detail, kind, normalized
frame, size/depth, grip type, finger capacity, cue style, and features).
Product photos can support selection of a retained primary image, but cannot
supply source-backed hold frames, unlabelled physical semantics, or app-specific
fields. The
tables below identify the exact official source keys reviewed for each
independent model; source keys are not shared between models.

| Candidate | Official source keys and URLs | Fields that source does establish | Exact package blocker | Result |
| --- | --- | --- | --- | --- |
| `soill-iron-palm-2` | `product`: [Iron Palm 2.0 product page](https://soillholds.com/products/iron-palm-2-0); `front-photos`: the product-page gallery | Product identity; the product description calls out slopers, pinches, edges, an incut top rung, thumb catches, and various edge sizes. | So iLL publishes no overall dimensions, numbered/depth hold chart, installation/manual hold map, or per-hold specification. The gallery has no labels that map those categories or sizes to each physical boundary. It cannot establish every hold's size/depth, finger capacity, grip type, cue style, or feature list. | Keep `assets/primary.png` only; unregistered. |
| `soill-split-palm` | `product`: [Split Palm product page](https://soillholds.com/products/split-palm); `front-photos`: the product-page gallery | Product identity and gallery images. | The official product page supplies no manufacturer hold specification, dimensions, hold count, depth/size list, or layout/numbered guide. A customer review is not manufacturer evidence. Gallery images cannot establish required per-hold semantics or app-specific cue/feature values. | Keep `assets/primary.png` only; unregistered. |
| `soill-training-tiles` | `product`: [Training Tiles product page](https://soillholds.com/products/training-tiles-so-ill-x-meagan-martin); `workouts`: [Meagan Martin Training Tiles workouts](https://soillholds.com/pages/meagan-martin-training-tiles-workouts); `front-photos`: product-page gallery | Product identity, collaboration name, gallery images, and the existence of four official workout videos. | Neither source publishes board dimensions, a physical-hold diagram, a named/depth hold inventory, or a mapping from a workout cue to a physical hold. The videos/page do not provide the required record for each hold or support cue-style/feature fields. | Keep `assets/primary.png` only; unregistered. |
| `tension-grindstone` | `product`: [Grindstone product page](https://tensionclimbing.com/collections/shop-all/products/grindstone); `overview`: [Tension hangboards overview](https://tensionclimbing.com/pages/hangboards); `front-photos`: product-page imagery | Overall dimensions; full-width bar-style jug; 50 mm center one-arm edge; 30/25/20/15/10/8 mm edge families; timer phone slot. | The sources do not publish a numbered/layout hold map that maps every physical left/right edge boundary to its stated depth. They also do not establish the package-required per-hold grip type, finger capacity, cue style, feature tokens, or normalized frame. Assigning those fields from the image or another Tension model would be inference. | Keep `assets/primary.png` only; unregistered. |
| `tension-honestone` | `product`: [Honestone product page](https://tensionclimbing.com/products/honestone); `overview`: [Tension hangboards overview](https://tensionclimbing.com/pages/hangboards); `front-photos`: product-page imagery | Overall dimensions; 35°/45° macro-textured top slopers; 25 mm center incut edge; 25 mm one-finger pockets; 20/15/10/8 mm edge families and the stated radius for 10/8 mm edges. | The sources list families, not a canonical individual-hold diagram or count/location map. They leave each physical hold's required grip type, finger capacity beyond the named pockets, cue style, feature list, and normalized frame unsupported. Product photography cannot fill those fields. | Keep `assets/primary.png` only; unregistered. |
| `tension-whetstone` | `product`: [Whetstone product page](https://tensionclimbing.com/products/whetstone); `overview`: [Tension hangboards overview](https://tensionclimbing.com/pages/hangboards); `front-photos`: product-page imagery | Overall dimensions; top ergo-bump jug; 40 mm center incut edge; 40 mm two-finger pockets; 40/30/25/20 mm edge families. | The sources do not provide a numbered or dimensioned physical-hold layout that ties each image boundary to a feature family. They do not establish every physical hold's grip type, finger capacity, cue style, feature list, or normalized frame. Inference from the image or descriptions would violate the evidence contract. | Keep `assets/primary.png` only; unregistered. |

## Exact blockers

### `soill-iron-palm-2`

The exact source-backed package blocker is recorded in this candidate's table row above.

### `soill-split-palm`

The exact source-backed package blocker is recorded in this candidate's table row above.

### `soill-training-tiles`

The exact source-backed package blocker is recorded in this candidate's table row above.

### `tension-grindstone`

The exact source-backed package blocker is recorded in this candidate's table row above.

### `tension-honestone`

The exact source-backed package blocker is recorded in this candidate's table row above.

### `tension-whetstone`

The exact source-backed package blocker is recorded in this candidate's table row above.

To register any candidate, its manufacturer must publish model-specific material
that maps every physical hold and supports the missing runtime fields, or the
package schema must be redesigned to make those fields genuinely optional with
a separately approved evidence contract. Until then, the one generated primary
image per candidate is intentionally the only retained package file.
