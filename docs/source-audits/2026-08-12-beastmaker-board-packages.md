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
type guide for the 17 mixed front contacts below:

- `front-middle-1` through `front-middle-9`;
- `front-lower-2` through `front-lower-4` and `front-lower-6` through
  `front-lower-8`; and
- the nested contacts `hold-26` and `hold-27`.

Those source families mix a four-finger jug, big and little edges, several
pocket families, and monos. The official unlabelled front does not establish
which stable ID belongs to which family. Therefore their existing mandatory
`kind` values are unchanged but not certified. The already source-mapped
exceptions are the five top slopers, the two upper “Back 2 Pockets,” and the
central 22 mm middle edge. A later source re-review also established
`front-lower-{1,9}` as the mirrored outer “Big and little edges” pair, as
recorded in the [all-board audit](2026-08-25-all-board-hold-audit.md#corrected-mapping-beastmaker-2000).
A Beastmaker-published positioned guide or direct written manufacturer
clarification is required before this board can enter `reviewedBoardIDs`; a
retailer diagram or a visual-width inference is not a substitute.

The board is instead declared in the metadata ledger's disjoint
`sloperOnlyBoardIDs` scope. That supplemental audit contains exactly one
`sloper` outcome for each of the 27 canonical holds: the five source-identified
slopers are unavailable because the manufacturer does not publish a flat or
round subtype, and the other 22 contacts are not applicable. Records for any
other metadata field remain forbidden in this scope, so it does not imply a
complete source audit of the unresolved front-contact kinds.

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

## 2026-08-26 correction: positioned secondary mappings and primary conflicts

This correction supersedes the current-state conclusions in the dated sections
above; it does not alter their historical evidence record. The packages and
ledger now use the positioned secondary mapping from [The Hangboard Beastmaker
1000/2000 comparison](https://thehangboard.com/pages/beastmaker-1000-vs-2000)
where it does not conflict with primary evidence. No stable ID, canonical path,
or geometry changed.

### Beastmaker 1000

The comparison diagram identifies `pocket-top-{left,right}` (#2) as 30 mm
three-finger **edges**, not pockets. Their runtime `kind` is consequently
`edge`, and `fingerCapacity` is absent/not applicable; the retained stable IDs
are historical identifiers, not type evidence.

The same secondary diagram identifies `pocket-top-outer-{left,right}` (#1) as
15 mm. The official [Beastmaker 1000 product page](https://www.beastmaker.co.uk/products/beastmaker-1000-series)
instead specifies its two small four-finger pockets as 10 mm. The ledger records
both facts and retains the primary **10 mm** runtime value for this mapped pair.

The secondary diagram and textual list both label `pocket-middle-center` (#6)
as a 50 mm four-finger edge.

### Beastmaker 2000

The secondary diagram and textual list both label `front-middle-5` (#6) as a
50 mm four-finger edge. Separately, the
user-provided annotated 2000 diagram received on 2026-08-26 labels
`front-lower-5` **21 mm**. The official [Beastmaker 2000 product page](https://www.beastmaker.co.uk/products/beastmaker-2000-series)
specifies the lower-center edge as **22 mm**; the runtime value remains 22 mm.
The ledger's manufacturer provenance explicitly records the 21-vs-22 conflict.

## 2026-09-09 Stage 0 model-migration evidence ruling

This entry records the approval-ready Stage 0 packets for the two-board model
migration. The durable packet trees, retained source bytes, and packet SHA-256
values are uncommitted workspace evidence under `.context/`.

### Beastmaker 1000 current revision

Primary retained sources are the current [1000 Series product page](https://www.beastmaker.co.uk/products/beastmaker-1000-series), current [1000 Beech/shared-layout page](https://www.beastmaker.co.uk/products/beastmaker-1000-beech), official [Tulip front media](https://cdn.shopify.com/s/files/1/0107/6442/files/1000_Small_Tulip.jpg?v=1756733068), the official [downloads page](https://www.beastmaker.co.uk/pages/downloads), and official [mounting guide](https://www.beastmaker.co.uk/pages/how-to-mount-your-beastmaker). Their retained snapshots and hashes are:

| packet path | SHA-256 |
| --- | --- |
| `.context/shaky-rat-beastmaker-1000/references/beastmaker-1000-series.html` | `4c3dc54c7a16a03f29fbbd87fb3d725c8a547a81a7c694a2da462ea2efc43900` |
| `.context/shaky-rat-beastmaker-1000/references/beastmaker-1000-beech.html` | `d1f5c20650a4c8572acea1fe804ca9831990c709f6f0e0fdca6a8575261dc1a2` |
| `.context/shaky-rat-beastmaker-1000/references/beastmaker-1000-tulip.jpg` | `b97c4a0fc1c6f8971cb7610a2ec2a979415e6c9018398c18ab76ed90034fdfae` |
| `.context/shaky-rat-beastmaker-1000/references/beastmaker-downloads.html` | `c2a646971be96829371814e21d8a6f44feb820dce22907ce07a99feb64822c7f` |
| `.context/shaky-rat-beastmaker-1000/references/beastmaker-mounting-guide.html` | `7dc0ad212297ddeb535d69ee3ac10d642da3805f1927ce92e6bd4ac957734d4e` |

The packet SHA-256 was `1f5a57be0c32ee1fffa4b10c5d494d0540e4d7c7e03ecec78edb25837450b0cf` before the multi-angle corrections; the current packet SHA-256 is `510def2516477dedb248ea85e3ec858129d0f298014b28c3e7ef9b19bd41cce0`. Its earlier Astra handoff SHA-256 was `34a91d0b0d799a31c232691ba29e270899c063f49305337860f363f240f5d3a6`; the handoff content now carries the updated packet hash. The face is sourced as 580 × 150 mm. The Beech/shared-layout page supplies the qualified 58 mm display depth; the current Tulip page's final `5 mm` text is retained as a conflict and is not treated as a Tulipwood thickness fact. The stable 22-ID logical inventory is retained as existing-package identity. Human review of the official front records 17 cavity contacts, 3 sloper surfaces, and 2 jugs; grouped marketing quantities do not delete visible contacts. Neither source assigns individual stable IDs, positions, or edge-versus-pocket kinds, so those mappings remain inherited package metadata rather than manufacturer per-ID facts. The packet preserves the source's literal “FCS certified Beech” wording. Cavity sections, profiles, back profile, radii, and exact positions remain unknown for Astra. Generic original pale wood is the approved display material. Screw holes, mounting hardware, countersinks, and logos are deliberate display omissions.

### Metolius Wood Grips Compact II current revision

Primary retained sources are the current [Wood Grips II product page](https://www.metoliusclimbing.com/products/wood-grips-ii-training-boards), official [Compact front media](https://www.metoliusclimbing.com/cdn/shop/files/Wood-Grips-II-Compact-Training-Board.jpg?v=1759460952&width=2000), and official [depth diagram](https://www.metoliusclimbing.com/cdn/shop/files/woodgrips-boards-depths.jpg?v=1762201428&width=2000). Their retained snapshots and hashes are:

| packet path | SHA-256 |
| --- | --- |
| `.context/shaky-rat-metolius-wood-grips-compact-ii/references/metolius-wood-grips-ii.html` | `b782a4fb7dbde84fd0f96cf716807fca7943f2671de255103c0899a2c1a7b5fc` |
| `.context/shaky-rat-metolius-wood-grips-compact-ii/references/compact-training-board.jpg` | `d72c7027d82980306e0e2a50d94394c174dce8ba0fd9bb239c704f099f05ed03` |
| `.context/shaky-rat-metolius-wood-grips-compact-ii/references/woodgrips-boards-depths.jpg` | `56dde7dce6f82395a06793e7e3de4600465b5e97a108b963b03a6a5cccb898ce` |


Both packets validate with `Tools/HangboardModels/validate_evidence_packet.py` and contain no geometry proposals, paths, contours, masks, coordinates, radii, or sections. The Beastmaker negative fixture retains valid search-snippet bytes and hash, then rejects at the validator's manufacturer-search-result URL rule with exit 2; the Compact missing-commerce-snapshot fixture rejects with the retained-source error and exit 2. The minimal Beastmaker `invalid-unknown-hold.blend` compiler fixture rejects with `unknown hold_id`, emits no descriptor, and its scratch directory is removed and verified absent. Astra geometry work remains gated on human approval of these packets and the matched retained official media.

### 2026-09-09 multi-angle Stage 0 correction

The user requires at least two retained exact-revision visual sources per board before Astra resumes, with materially different angles where available. The manufacturer 1000 Series page supplies one complete straight-on front image. The manufacturer downloads and mounting-guide pages were also checked; their old Vimeo embeds and user setup photographs do not provide a complete exact-1000 profile/side/back source. A complete replacement angle was found on FluxPerfect, an established Austrian outdoor retailer (FluxPerfect GmbH & Co OG), and is retained explicitly as commerce-gap evidence.

All candidates were retrieved 2026-09-09 in locale `en-GB`; exact page linkage, tier, original pixels/hash, angle verdict, and geometric support limits are recorded below and in the packet. Only the first two rows are the approval-ready set.

| tier | retained path | SHA-256 | dimensions | view / verdict | page linkage |
| --- | --- | --- | --- | --- | --- |
| manufacturer | `.context/shaky-rat-beastmaker-1000/references/beastmaker-1000-tulip.jpg` | `b97c4a0fc1c6f8971cb7610a2ec2a979415e6c9018398c18ab76ed90034fdfae` | 2500 × 735 | straight-on front | [Beastmaker 1000 Series](https://www.beastmaker.co.uk/collections/fingerboards/products/beastmaker-1000-series) |
| commerce gap | `.context/shaky-rat-beastmaker-1000/references/fluxperfect-beastmaker-1000-ansicht-1.jpg` | `959801633efd53b10dba145a659988290d5189ea2bcc171329fedd1e6d52a3ff` | 1080 × 1080 | **qualifies** — complete elevated three-quarter/top-and-side reveal; visible top plane, outer side/depth, rounded end | [FluxPerfect Beastmaker 1000 Series](https://www.fluxperfect.at/products/beastmaker-1000-series-hangboard) |
| commerce gap | `.context/shaky-rat-beastmaker-1000/references/9c-beastmaker-1000-03.jpg` | `db2bdac139d56951a04d674020e1ab50d2f36c1cb40aed158838da4bce195356` | 1800 × 513 | **rejected** — near-front variant; no usable top/side/profile depth | [9c Climbing 1000 Series](https://9cclimbing.com/fr/products/1000-series-hangboard) |
| commerce candidate | `.context/shaky-rat-beastmaker-1000/references/fluxperfect-beastmaker-1000-ansicht-2.jpg` | `7fe065025f73a90b91515ff5450f2e845586200f48b5343b707842b80cc31a6f` | 1080 × 1080 | rejected close oblique crop; local cavity-wall/side-edge only | [FluxPerfect 1000 Series](https://www.fluxperfect.at/products/beastmaker-1000-series-hangboard) |
| commerce candidate | `.context/shaky-rat-beastmaker-1000/references/fluxperfect-beastmaker-1000-ansicht-3.jpg` | `aa85e5d3740dcb13b27cf25236def2edb066bed25a84a80e1dd6ccf6cb139d69` | 1080 × 1080 | rejected partial front crop; front-layout corroboration only | [FluxPerfect 1000 Series](https://www.fluxperfect.at/products/beastmaker-1000-series-hangboard) |
| commerce candidate | `.context/shaky-rat-beastmaker-1000/references/fluxperfect-beastmaker-1000-ansicht-4.jpg` | `52205774377c9e4c1da46f54c9d5459ce5fe2312777eb610db4252d53c068125` | 1080 × 1080 | rejected close oblique crop; local pocket-wall only | [FluxPerfect 1000 Series](https://www.fluxperfect.at/products/beastmaker-1000-series-hangboard) |
| commerce candidate | `.context/shaky-rat-beastmaker-1000/references/fluxperfect-beastmaker-1000-ansicht-5.jpg` | `cd861578405510dc71594d5bb9e55005850f2b717ace3ccdcb497d66dfd9695a` | 1080 × 1080 | rejected partial rotated crop; local cavity-wall only | [FluxPerfect 1000 Series](https://www.fluxperfect.at/products/beastmaker-1000-series-hangboard) |
| commerce candidate | `.context/shaky-rat-beastmaker-1000/references/fluxperfect-beastmaker-1000-ansicht-6.jpg` | `80279060397953363b4ef1b21ee384d1bb7db0e4148cb956e30fae4f06d1a03f` | 1080 × 1080 | rejected partial rotated crop; local cavity-wall only | [FluxPerfect 1000 Series](https://www.fluxperfect.at/products/beastmaker-1000-series-hangboard) |
| commerce candidate | `.context/shaky-rat-beastmaker-1000/references/ellis-brigham-1000-01.jpg` | `600387f9c7335e674b2791804e3b01aaff77607fb11ad3761fefd7b2ca960da9` | 2000 × 2800 | rejected near-front; minor elevation only | [Ellis Brigham 1000 Series](https://www.ellis-brigham.com/beastmaker-1000-series-fingerboard-131800900) |
| commerce candidate | `.context/shaky-rat-beastmaker-1000/references/ellis-brigham-1000-02.jpg` | `a911c61d306f18cbcdcf4e8c7d573973903145ea389b7fd8ceed350a426f6777` | 2000 × 2800 | rejected oblique detail crop; local top/side-depth only | [Ellis Brigham 1000 Series](https://www.ellis-brigham.com/beastmaker-1000-series-fingerboard-131800900) |
| commerce candidate | `.context/shaky-rat-beastmaker-1000/references/ellis-brigham-1000-03.jpg` | `5fddaa72271807b690d3fd5f58e3a47de1b96a18c8df7b83c9dfee10960c792e` | 2000 × 2800 | rejected oblique detail crop; local top/side-depth only | [Ellis Brigham 1000 Series](https://www.ellis-brigham.com/beastmaker-1000-series-fingerboard-131800900) |

The FluxPerfect page's retained JSON identifies vendor Beastmaker, product
“Beastmaker 1000 Series Hangboard”, and its linked `Ansicht_1` asset; the
image visibly carries the “1000 SERIES” mark and matching 22-contact layout.
The Ellis Brigham page identifies the 1000 Series and SKU `131800900`, but its
02/03 candidates crop the board. The 9c page title and image mark identify the
same layout, but original-resolution review rejects it as near-front. No
commerce candidate overrides dimensions, inventory, material, or other
manufacturer claims. The qualifying front/three-quarter set exposes no hidden
back geometry, measured depth, cavity sections, or radii. Crops, duplicate
views, search thumbnails, and ambiguous revision media were rejected.

## 2026-09-09 final model-package promotion

The earlier Stage 0 and Astra-gate language above is historical. Both target
packages are now promoted and human-approved: Beastmaker 1000 after the
corrected export recorded approval `8ebbdb78` (after `c3a15af5`), and Compact II
after the final export recorded approval `e4130730` (after `b8596eae`). Each
package contains exactly `board.json`, `assets/primary.usdz`, and
`assets/primary.model.json`; target `primary.png` files are absent. The
standalone `HangTen/Resources/BoardModels/wood-grips-compact-ii.usdz` is also
absent. Both use generic pale/original wood; omitted screws, mounting holes,
countersinks, hardware, and logos are deliberate display simplifications.

| package | model SHA-256 | descriptor SHA-256 | inventory |
| --- | --- | --- | --- |
| Beastmaker 1000 | `e15bae1d9664b834ee68853cecba47076617bdd382458b26700d18e321e146e3` | `2c392869087b6729870010d7606dd3a500eb659d48f80fe851115ff62b71984b` | 22 holds / 23 nodes |
| Compact II | `220c68ea5519b0bed80cd2aac08b35f5f2c2a7d2200596f62c3a84996efb94a3` | `300a26886362dd0c510c729e1a9fd4e6a35f47497aed5e7f12d33a2fdb7068fe` | 19 holds / 20 nodes |

The packet hashes are Beastmaker `510def2516477dedb248ea85e3ec858129d0f298014b28c3e7ef9b19bd41cce0` and Compact `fe4a13559dfc8b734e349005444599407cb8cb7358350a095c0c3cdd451f62c3`; the earlier Beastmaker handoff hash was `444dc99cacf1e68fc8b564667a22b965d5e9a624b3e38953a6f98ab07edea5ea`. Beastmaker is 580 × 150 mm with a qualified Beech/shared-layout 58 mm depth; the Tulip page's 5 mm is retained as a conflicting non-thickness claim. Compact is 610 × 157 mm; its #2/#9 56 mm callouts are slopers only, while 64 mm body Z is an authored estimate.

Host-native SceneKit proof passes all 41 nearest face-center rays and body nil
probes. Simulator XCTest/app visual validation remains pending because
CoreSimulatorService has been unavailable; no simulator screenshots, taps, or
app visual review are claimed. Stale references found in historical plans,
manifests, or generator/tooling output are non-production; production package,
source, and app references are absent. Remote GitHub model sync, iOS model
editing, and Workbench model editing remain deferred/read-only/unavailable.
