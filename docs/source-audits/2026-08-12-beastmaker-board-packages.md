# Beastmaker board-package source audit

Checked 2026-08-12. This is a historical evidence audit, not current package
or runtime state. Its old readiness conclusions are superseded by the current
flat-package schema and `docs/ADDING_A_BOARD.md`; unsupported optional metadata
is omitted, while visible paths are directly authored from primary evidence.

## Candidates

| slug | board id | official product URL | official front image URL |
| --- | --- | --- | --- |
| `beastmaker-1000` | `beastmaker.1000` | https://www.beastmaker.co.uk/products/beastmaker-1000-series | https://cdn.shopify.com/s/files/1/0107/6442/files/1000_Small_Tulip.jpg?v=1756733068 |
| `beastmaker-2000` | `beastmaker.2000` | https://www.beastmaker.co.uk/products/beastmaker-2000-series | https://cdn.shopify.com/s/files/1/0107/6442/files/2000_Small_Tulip.jpg?v=1756734230 |

The official product pages establish each board's identity, published overall
dimensions, a grouped inventory of hold types, and the associated official
front image. The audit found no Beastmaker-published numbered hold guide,
depth diagram, manual, or measurement source for either board. No official
oblique image or per-hold measurement source was found that could assign every
individual depth or capacity.

## Current authoring interpretation

- For `beastmaker-1000`, the grouped inventory supports pocket families and
  one 10 mm pair at product level, but does not position a capacity or depth on
  an individual stable ID. Unsupported per-contact values remain omitted.
- For `beastmaker-2000`, the grouped description supports the clearly central
  22 mm edge, but not a complete depth assignment. Unsupported values remain
  omitted.
- Visible contact boundaries may be directly authored from the official front
  imagery and reviewed by a person. They are not measurements.

Both completed packages were later authored and visually reviewed independently
of the removed draft art.

## 2026-08-25 Beastmaker 1000 source-audited metadata certification

The current [Beastmaker 1000 product
page](https://www.beastmaker.co.uk/products/beastmaker-1000-series) and its
linked [official straight-on
front](https://cdn.shopify.com/s/files/1/0107/6442/files/1000_Small_Tulip.jpg?v=1756733068)
were manually reconciled with the stable-ID capture at
`.context/hangboard-metadata-backfill-icky-cow/beastmaker-1000-certification/beastmaker-1000--4fee18798954.png`.
The capture is a review aid for existing canonical paths only; it supplied no
measurement, capacity, posture, feature, kind, or geometry.

### Inventory conflict and ruling

The official front visibly contains 22 separate physical contacts: two outer
top jugs, three top sloper surfaces, and 17 front cavities. The product copy
instead lists two jugs, a paired 35-degree sloper, a 20-degree sloper, and
pocket families whose quantities total only 15. The copy is therefore short by
two pockets relative to the manufacturer's own current front.

All 22 existing records and canonical paths remain unchanged. Deleting two
visible cavities to force agreement with the marketing arithmetic would make
the package less faithful to the physical product. The mandatory kinds use an
explicit group-level ruling:

| Stable IDs | Source-backed `kind` ruling |
| --- | --- |
| `jug-{left,right}` | `jug`, from the exact “2 Jugs” family mapped to the two outer top contacts. |
| `sloper-35-{left,right}`, `sloper-center` | `sloper`, from the paired 35-degree and center 20-degree sloper families mapped to the only three top sloper surfaces. The degrees are angles, not depths. |
| All 17 `pocket-*` IDs | `pocket`, because the exhaustive front-contact inventory is pocket-only and the official front shows 17 separate cavities. This certifies the shared kind, not a per-position depth or finger subtype. |

`sloper-center` keeps its stable ID and is display-labelled “20 Degree Center
Sloper.” No geometry or presentation asset changed.

### Deliberate optional blanks

Every optional field is absent on all 22 contacts. In particular:

- The product page does not publish an exact scalar or lower/upper depth range
  for a jug or sloper. Sloper degrees are not millimetre depth.
- Its sole numeric depth claim is an unpositioned 10 mm pocket pair; no stable
  ID receives that value.
- The listed two-, three-, and four-finger pocket families are neither
  positioned nor reconcilable with the 17 visible cavities, so no exact pocket
  gets `fingerCapacity` or a pocket grip enum. Finger capacity is not
  applicable to the five source-identified jugs/slopers.
- The source does not state simultaneous hand capacity, prescribe one exact
  supported grip posture, or publish an exact supported feature-tag array for
  any stable ID. Existing guessed jug posture/capacity/features, pocket scalar
  depths, and duplicated pocket feature tags were removed.

The canonical ledger accounts for all 154 required outcomes: 22 verified
mandatory kinds, 127 unavailable optional fields, five not-applicable finger
capacities, and zero unaccounted fields. Beastmaker 2000 remains outside this
certification; no value or ruling from the 1000 was transferred to it.

## 2026-08-25 Beastmaker 2000 conservative metadata cleanup

The current [Beastmaker 2000 product
page](https://www.beastmaker.co.uk/products/beastmaker-2000-series), its linked
[official straight-on
front](https://cdn.shopify.com/s/files/1/0107/6442/files/2000_Small_Tulip.jpg?v=1756734230),
and the post-repair stable-ID capture at
`.context/hangboard-metadata-backfill-icky-cow/beastmaker-2000-geometry-repair/beastmaker-2000--305c473cc719.png`
were manually reconciled. The capture identifies existing canonical paths; it
does not supply a physical type, measurement, capacity, posture, or feature.

### Mandatory-kind blocker

The package remains deliberately excluded from the canonical reviewed metadata
ledger. Beastmaker publishes a grouped inventory, but no numbered or positioned
type guide for the 19 mixed front contacts below:

- `front-middle-1` through `front-middle-9`;
- `front-lower-1` through `front-lower-4` and `front-lower-6` through
  `front-lower-9`; and
- the nested contacts `hold-26` and `hold-27`.

Those source families mix a four-finger jug, big and little edges, several
pocket families, and monos. The official unlabelled front does not establish
which stable ID belongs to which family. Therefore their existing mandatory
`kind` values are unchanged but not certified. The already source-mapped
exceptions are the five top slopers, the two upper “Back 2 Pockets,” and the
central 22 mm middle edge. A Beastmaker-published positioned guide or direct
written manufacturer clarification is required before this board can enter
`reviewedBoardIDs`; a retailer diagram or a visual-width inference is not a
substitute.

No `kind`, geometry, presentation asset, stable ID, or hold count changed in
this cleanup. In particular, the directly reviewed compound parent paths
`front-middle-{3,7}` and nested paths `hold-{26,27}` remain intact and
non-overlapping.

### Deliberate optional blanks

All 24 existing `fingerCapacity` values were removed because the grouped source
does not position a capacity on an exact stable ID. This includes four top
slopers (`top-sloper-1`, `top-sloper-2`, `top-sloper-4`, and `hold-28`), all 19
unmapped mixed front contacts (including both compound parents and both nested
contacts), and `front-lower-5`. The latter remains the source-backed
`sizeMillimeters: 22` center edge, but an edge depth does not establish its
three-finger capacity.

The exact package state after cleanup is:

| Optional field | Populated contacts | Intentionally blank contacts |
| --- | --- | ---: |
| `sizeMillimeters` | `front-lower-5`: 22 mm | 26 |
| `depthRangeMillimeters` | none | 27 |
| `fingerCapacity` | none | 27 |
| `handCapacity` | none | 27 |
| `gripType` | none | 27 |
| `features` | none | 27 |

The grouped angle labels are not depth measurements, and the source publishes
no exact per-contact range, simultaneous hand capacity, supported grip enum, or
closed feature-tag array. These blanks are intentional evidence boundaries,
not incomplete metadata.
