# All-board visual and presentation audit

Reviewed 2026-08-18. This audit covers every completed direct-child package
currently discovered under `Hangboards/`: seven boards, 132 logical holds, and
136 geometry pieces. The 27 primary-only draft directories were discovered but
were not modified or promoted.

The official images below are comparison evidence. They support the visible
product envelope used to review the runtime artwork and exact-path overlays;
they are not runtime assets and were not used to add or change hold facts.

## Catalog results and official comparison sources

| board | official product page | official front image | canvas before → after (px) | holds / pieces | editable points before → after | max piece boundary error (px) | max piece symmetric difference |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: |
| Beastmaker 1000 | [product](https://www.beastmaker.co.uk/products/beastmaker-1000-series) | [front image](https://www.beastmaker.co.uk/cdn/shop/files/1000_Small_Tulip_1200x1200.jpg?v=1756733068) | 1000×259 → 1000×259 | 22 / 22 | 395 → 395 | 0.0 | 0.0000% |
| Beastmaker 2000 | [product](https://www.beastmaker.co.uk/products/beastmaker-2000-series) | [front image](https://www.beastmaker.co.uk/cdn/shop/files/2000_Small_Tulip_1200x1200.jpg?v=1756734230) | 2172×724 → 2037×564 | 25 / 25 | 341 → 339 | 0.0 | 0.0000% |
| DeWoodstok Woodbord | [product](https://www.dewoodstok.nl/product/hangboard-woodbord/) | [front image](https://www.dewoodstok.nl/wp-content/uploads/2025/08/05_E_woodbord.jpg) | 1774×887 → 1685×465 | 17 / 17 | 255 → 255 | 0.0 | 0.0000% |
| Escape Beta 22 | [product](https://escapeclimbing.com/products/ec72100) | [front image](https://escapeclimbing.com/cdn/shop/products/2020_Website_ProductImage_BetaBoardListing_01-02.jpg?v=1700454580) | 1536×1024 → 1503×394 | 22 / 22 | 274 → 274 | 0.0 | 0.0000% |
| Lattice Triple Rung | [product](https://latticetraining.com/product/triple-rung-wooden-hangboard/) | [front image](https://latticetraining.com/app/uploads/2020/07/Triple-Rung-Web-1.jpg) | 1536×1024 → 1477×396 | 3 / 3 | 57 → 57 | 0.0 | 0.0000% |
| Metolius Wood Grips Compact II | [product](https://www.metoliusclimbing.com/products/wood-grips-ii-training-boards) | [front image](https://www.metoliusclimbing.com/cdn/shop/files/Wood-Grips-II-Compact-Training-Board.jpg?v=1759460952) | 1774×457 → 1774×457 | 19 / 19 | 78 → 78 | 0.0 | 0.0000% |
| Trango Rock Prodigy Training Center | [product](https://trango.com/products/rock-prodigy-training-center) | [front image](https://trango.com/cdn/shop/files/22830_Rock_Prodigy_Training_Center_Main_Image.jpg?v=1737728750) | 1254×1254 → 1233×435 | 24 / 28 | 520 → 504 | 0.0 | 0.0000% |

Catalog total: 1,920 → 1,902 editable points. The final mixed-path simplifier
reported nine accepted safe-candidate removals across five geometry pieces,
with nine evaluated candidates, zero rejected or complexity-skipped candidates,
and 13
unsupported rounded rectangles. It removed two points from Beastmaker 2000's
`top-sloper-3` and four points from each of the four geometry pieces belonging
to Trango's `pinch-medium-left` and `pinch-medium-right`. Each accepted piece
has measured maximum boundary error 0.0 px and symmetric difference 0.0000%.

This is a reasonably minimal result within the generic simplifier's supported
safe-candidate surface. It is not a claim that every curve representation in
the catalog is globally irreducible. The 13 rounded rectangles remain
byte-for-byte unchanged and are explicitly counted as unsupported by the path
simplifier.

## Transformation and field mapping

| evidence or operation | supports | changed fields | explicitly not supported or changed |
| --- | --- | --- | --- |
| Official product pages and front images | Product comparison and the visible board envelope used during visual review | None; the downloaded evidence is not committed runtime content | Hold identity, name, kind, measurements, depth, grip type, finger capacity, features, treatment, and training semantics |
| Generic hold-path simplifier | Equivalent lower-point path commands only when native-pixel boundary deviation is at most 1 px, symmetric difference is at most 0.25%, and editable points strictly decrease | `shape.commands` for the five accepted pieces only | Board and hold inventory, geometry-piece count/type/order, frames, treatments, and all non-geometry hold facts |
| Generic presentation normalizer | The union of border-connected visible content and every geometry piece's pixel bounds, plus the catalog-wide 1% padding policy | For the five cropped packages: `aspectRatio`, every `holds[].geometry[].frame`, and `assets/primary.png` dimensions/bytes | Path commands, rounded-rectangle parameters, treatments, hold facts, board identity/facts, hold or piece order, and `presentation.assetPath` |

Frame changes are exact coordinate reprojections into the cropped canvas. They
do not move a geometry piece relative to its source pixels. The final PNG for
each changed board is an exact pixel crop of its prior PNG; no resampling or
restyling occurred.

## Preservation and visual review

The before, post-simplification, and after inventories were compared in order.
All seven board IDs and paths, all 132 ordered hold IDs, every non-geometry hold
hash, every geometry-piece count and shape type, and every treatment hash
match. Shape hashes differ only for the five pieces reported by the
simplifier. A generic comparison checked every reported before/after point
count and raster-error gate, unchanged frames and PNGs, and finite positive
normalized bounds. It completed 2,020 assertions without an error.

The same generic exact-path renderer produced the before and after overlays.
All seven native-resolution renders and the full official/runtime/overlay
contact sheets were visually inspected. Every one of the 132 logical hold
targets (136 geometry pieces) remains on its prior physical contact and no
board or hold is clipped. A fresh final-fix comparison of each complete before
overlay against its after overlay is pixel-identical for all seven boards,
including the Beastmaker sloper and four Trango pinch pieces whose editable
commands changed.

Presentation findings by board:

- Beastmaker 1000 and Metolius Wood Grips Compact II were already tight and
  remain byte-for-byte unchanged.
- Beastmaker 2000, DeWoodstok Woodbord, Escape Beta 22, and Lattice Triple Rung
  lose surrounding empty presentation space while retaining their full visible
  envelopes and every contact path.
- Trango Rock Prodigy Training Center loses the square canvas's unused vertical
  space while retaining both board halves and all 28 pieces for its 24 holds.

## Simulator screenshots

These retained screenshots come from dedicated iPhone 17 Pro / iOS 26.5 signed
Debug review routes: the portrait plan route shows the first-hold highlight,
and the landscape workout route shows the next-hold highlight. They document
the review states without claiming that all boards are shown.

![Portrait plan route with first-hold highlight](assets/2026-08-18-all-board-visual-audit/plan-portrait.png)

![Landscape workout route with next-hold highlight](assets/2026-08-18-all-board-visual-audit/workout-landscape.png)

## Validation

The completed catalog passes `packages validate`. After the original
catalog-wide presentation normalization and the final catalog-wide mixed-path
simplification, fresh dry runs of both operations report `changed: false` for
all seven completed packages.
The required generic iOS Simulator `build-for-testing` completed successfully
with these staged package resources.
