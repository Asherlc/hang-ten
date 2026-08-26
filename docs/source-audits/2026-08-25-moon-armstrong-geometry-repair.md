# Moon Armstrong geometry repair

Reviewed 2026-08-25. This repair restores the source-backed physical inventory
from 19 to 21 contacts. It does not certify the board in the shared metadata
ledger; that audit remains a separate step.

## Primary manufacturer evidence

- Product page and exact inventory:
  https://moonclimbing.com/moon-armstrong-fingerboard-beech.html
- Complete official straight-on front used by the package:
  https://moonclimbing.com/media/catalog/product/cache/8fbd88411911f97522c3f864e19b1b09/6/0/60-112-bec_moon_armstrong_fingerboard_bec_01.jpg
- Official oblique corroboration:
  https://moonclimbing.com/media/catalog/product/cache/8fbd88411911f97522c3f864e19b1b09/6/0/60-112-bec_moon_armstrong_fingerboard_bec_02.jpg

The product page explicitly specifies two 22 mm one-finger pockets and two
22 mm two-finger pockets. The straight-on front places each mono between its
same-side two-finger pocket and the center block. The much smaller holes near
the seams and center logo are mounting or pulley holes, not climbing contacts.

## Presentation provenance

The source JPEG is 1697 × 1200 pixels and has SHA-256
`29f03914993071b604d8262d04a85d9ce4c54765b4d0a67d5c4d456d7f8aa58f`.
It was encoded as the package PNG at the same 1697 × 1200 dimensions without
cropping, stretching, inpainting, masking, or generated content. The package
PNG has SHA-256
`f81b2d306afe070177eeda2464a9b4019e505916641ebdb9399141e19e129fa3`.
One white corner background pixel is transparent solely to satisfy the package
format contract; no product pixel was changed.

## Direct geometry review

All 19 retained canonical paths were deliberately reviewed against the complete
official front in its own coordinate system. Symmetric physical pairs use exact
horizontal mirrors. The two restored contacts are:

| Stable ID | Source contact | Canonical frame | Constraint |
| --- | --- | --- | --- |
| `mono-left` | Viewer-left 22 mm one-finger through-pocket | `x 0.335`, `y 0.586`, `w 0.026`, `h 0.036768333333` | operator-selected circle |
| `mono-right` | Viewer-right 22 mm one-finger through-pocket | `x 0.639`, `y 0.586`, `w 0.026`, `h 0.036768333333` | exact mirrored circle |

Each restored record is a `pocket` with exact source-supported
`sizeMillimeters: 22` and `fingerCapacity: 1`. Unsupported range, hand
capacity, grip enum, and features remain absent. The mono frames do not overlap
their adjacent two-finger pocket frames.

Workbench visible-ID evidence is stored at
`.context/hangboard-metadata-backfill-icky-cow/moon-armstrong-geometry-repair/capture/moon.armstrong--45a10ab74773.png`.
Its manifest records 21 rendered regions. Manual review confirmed all 21 labels
map to distinct source-supported contacts, including both circular monos, and
that no hold path covers a mounting or pulley hole.
