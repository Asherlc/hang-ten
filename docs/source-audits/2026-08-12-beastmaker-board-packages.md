# Beastmaker board-package source audit

Updated 2026-08-26. This audit records the evidence behind the canonical
metadata; it does not change the directly authored hold paths.

## Sources and evidence tiers

| Board | Primary identity source | Positioned depth/type source |
| --- | --- | --- |
| Beastmaker 1000 | [Beastmaker 1000 Series](https://www.beastmaker.co.uk/products/beastmaker-1000-series) | [The Hangboard comparison page](https://thehangboard.com/pages/beastmaker-1000-vs-2000) — **secondary**, not manufacturer evidence. |
| Beastmaker 2000 | [Beastmaker 2000 Series](https://www.beastmaker.co.uk/products/beastmaker-2000-series) | [The Hangboard comparison page](https://thehangboard.com/pages/beastmaker-1000-vs-2000) — **secondary**, not manufacturer evidence. |

The Beastmaker pages establish product identity, overall dimensions, and the
top jug/sloper inventory. They do not publish a numbered per-contact depth
guide. The positioned comparison diagrams supply the stable-ID mapping used for
the exact front contacts below. The metadata ledger records those mapped facts
as `secondary`; it does not represent them as manufacturer claims.

## Beastmaker 1000 mapping

The secondary diagram maps all 17 front contacts. Mirrored pairs share a value:

| Diagram family | Canonical IDs | Type/capacity | Depth |
| --- | --- | --- | ---: |
| #1 | `pocket-top-outer-{left,right}` | 4-finger edge | 15 mm |
| #2 | `pocket-top-{left,right}` | 3-finger pocket | 30 mm |
| #3 | `pocket-middle-outer-{left,right}` | 4-finger edge | 45 mm |
| #4 | `pocket-middle-mid-{left,right}` | 2-finger pocket | 50 mm |
| #5 | `pocket-middle-inner-{left,right}` | 3-finger pocket | 45 mm |
| #6 | `pocket-middle-center` | 4-finger edge | 53 mm |
| #7 | `pocket-bottom-outer-{left,right}` | 4-finger edge | 20 mm |
| #8 | `pocket-bottom-mid-{left,right}` | 2-finger pocket | 25 mm |
| #9 | `pocket-bottom-inner-{left,right}` | 3-finger pocket | 20 mm |

### Recorded discrepancy

For #6, the comparison page's textual list says **50 mm**, while its
positioned annotated diagram says **53 mm**. The package uses **53 mm** because
the diagram identifies the exact canonical contact; the secondary provenance
label preserves the disagreement.

No depth or capacity is assigned to the two jugs or three slopers.

## Beastmaker 2000 mapping

The comparison diagram and list identify the following stable contacts. The
manufacturer-backed `front-lower-5: 22 mm` center edge remains unchanged.

| Diagram family | Canonical IDs | Type/capacity | Depth |
| --- | --- | --- | ---: |
| 4-finger edge | `front-middle-{1,9}` | edge | 33 mm |
| mono | `front-middle-{2,8}` | 1-finger pocket | 55 mm |
| back-2 pocket | `front-middle-{3,7}` | 2-finger pocket | 35 mm |
| back-2 pocket | `hold-{26,27}` | 2-finger pocket | 50 mm |
| 2-finger pocket | `front-middle-{4,6}` | 2-finger pocket | 30 mm |
| 4-finger edge | `front-middle-5` | edge | 52 mm |
| 3-finger pocket | `front-upper-1` | 3-finger pocket | 40 mm |
| 3-finger pocket | `front-upper-2` | 3-finger pocket | 20 mm |
| 4-finger edge | `front-lower-{1,9}` | edge | 15 mm |
| mono | `front-lower-{2,8}` | 1-finger pocket | 25 mm |
| 2-finger pocket | `front-lower-{3,7}` | 2-finger pocket | 20 mm |
| 2-finger pocket | `front-lower-{4,6}` | 2-finger pocket | 20 mm |
| manufacturer center edge | `front-lower-5` | edge | 22 mm |

### Recorded discrepancy

For `front-middle-5`, the comparison page's textual list calls the center
four-finger edge **50 mm** while its positioned annotated diagram labels it
**52 mm**. The package uses the diagram's **52 mm** value because it is the
positioned evidence. The existing primary-source 22 mm lower center edge is a
different contact and is retained as manufacturer-backed.

No depth or finger capacity is inferred for any 2000 sloper. The ledger also
keeps its unsupported range, hand-capacity, posture, and feature fields blank.
