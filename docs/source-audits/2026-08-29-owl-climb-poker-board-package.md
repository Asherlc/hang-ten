# Owl Climb Poker source audit

Reviewed 2026-08-29 for package `owl-climb-poker` and board ID
`owl-climb.poker`.

## Evidence and caveats

| Source | Package use | Caveat |
| --- | --- | --- |
| [Owl Climb Poker product page](https://owlclimb.com/index.php/en/prds-2/poker/) | Primary identity, canonical `productURL`, four-face construction, `660 × 100 × 100 mm` dimensions, named outer slots, single- and dual-finger holes, central pull-up holes, two 35° slopers, and two 100 mm half-circles. | The page gives depth ranges by feature family but does not label individual faces or left/right contacts with their depth. |
| [Owl Climb official image 0](https://i0.wp.com/owlclimb.com/wp-content/uploads/2019/03/owlclimb_poker19_0.jpg?resize=790%2C309&ssl=1), [1](https://i0.wp.com/owlclimb.com/wp-content/uploads/2019/03/owlclimb_poker19_1.jpg?resize=790%2C309&ssl=1), [2](https://i0.wp.com/owlclimb.com/wp-content/uploads/2019/03/owlclimb_poker19_2.jpg?resize=790%2C309&ssl=1), and [3](https://i0.wp.com/owlclimb.com/wp-content/uploads/2019/03/owlclimb_poker19_3.jpg?resize=790%2C309&ssl=1) | Primary visual evidence for the four face layouts, all visible contacts, bilateral symmetry, central Owl-logo block, and black end supports. | Product photos, not a numbered hold guide. The source does not identify Face A–D or assign exact depths to an individual pictured contact. |
| [BananaFingers Owl Climb Poker listing](https://bananafingers.com/us/owl-climb-poker-hangboard) | Secondary identity and retail-listing corroboration supplied with the request. | Third party; not used for dimensions, hold metadata, art, or geometry. |

## Frozen contact inventory and field mapping

The visual inventory is frozen from the four official faces. All faces visibly
share seven contacts: two outer slots, two single-finger pockets, two
dual-finger pockets, and one center pull-up slot. The remaining central
contacts are face-specific and are represented only on the official face where
they are visible. This makes 34 records: Face A has 7; Faces B, C, and D have
9 each.

| IDs | Source-backed mapping | Omitted or adapted fields |
| --- | --- | --- |
| `face-*-left/right-outer-slot` | The product page names outer slots; the official images show one on each end of all four faces. They are `edge` records. | No per-face slot depth: the published depth list is not photo-mapped. |
| `face-*-left/right-single-pocket` | The page names single-finger holes; the images show one circular pocket per side on all faces. They are `pocket` records with `fingerCapacity: 1`. | No depth, posture, or hand-capacity field. |
| `face-*-left/right-dual-pocket` | The page names dual-finger holes; the images show one horizontal two-finger pocket per side on all faces. They are `pocket` records with `fingerCapacity: 2`. | No depth, posture, or hand-capacity field. |
| `face-*-center-pull-up-slot` | The page describes central pull-up holes; each official face visibly has one centered horizontal slot. They are conservatively represented as `edge` contacts. | No capacity or per-face depth. |
| `face-b-left/right-deep-sloper` | Official image 1 visibly shows the pair of large, deep rectangular central sloping contacts. The page independently documents a pair of 35° slopers. | No size/depth assignment beyond the page's pair-level statement. |
| `face-c-left/right-shallow-half-round` | Official image 2 visibly shows the pair of shallow central half-round contacts. The page independently documents two 100 mm half-circles. They are `sloper` records because the schema has no half-circle kind. | `sizeMillimeters: 100` is retained only for this documented pair; no posture/capacity/depth is asserted. |
| `face-d-left/right-deep-rounded-recess` | Official image 3 visibly shows a separate pair of deep rounded central contact recesses. | These records intentionally carry only visual-contact geometry and conservative `sloper` kind. The primary page does not publish a distinct named family or dimension for this face, so none is inferred. |

`Face A` through `Face D` are neutral presentation identifiers for the official
image sequence; they do not claim a manufacturer-published ordering or a
depth-to-face mapping. The central Owl-logo block and black end supports are
faithful non-contact presentation features, not hold records.

## Art and geometry review boundary

Each `assets/face-*.png` is a new straight-on studio render, generated as a
product mockup from written physical requirements after human review of the
official images. The official photos were evidence only: they were not copied,
cropped, traced, registered, vectorized, segmented, or transformed into these
assets. The renders retain pale wood, recessed contact interiors, soft studio
lighting, central Owl block, black end supports, and an off-white background.

The assets were reviewed alongside `dewoodstok-woodbord` as the comparable
wood catalog render, then the saved normalized paths were deliberately authored
against the accepted presentation images. Regular slots and pockets use
operator-selected pill/oval constraints. The six center-contact profiles are
freeform closed paths; no contour was extracted from a photo. The saved paths
remain the normal rendering, active rendering, and hit-test truth.

## Validation

`rtk scripts/hangboard-packages.sh validate --root Hangboards --final-inventory`
and `rtk scripts/hangboard-packages.sh status --root Hangboards` pass with no
drafts after the correction. App-rendered screenshots and interaction alignment
will only be represented in the PR if the focused simulator test completes for
this corrected asset/geometry revision.
