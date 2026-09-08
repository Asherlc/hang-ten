# Metolius Rock Rings 3D single-unit catalog audit

Reviewed 2026-09-07 against the current [Metolius Rock Rings 3D product page](https://www.metoliusclimbing.com/products/rock-rings-3d), the official [black-and-white product photograph](https://www.metoliusclimbing.com/cdn/shop/files/Rock-Rings-black-white.jpg?v=1759460123), and the official [depth guide](https://www.metoliusclimbing.com/cdn/shop/files/Rock-Ring-Depts.jpg?v=1762201543).

Metolius sells Rock Rings 3D as a pair. At the user's explicit direction, Hang Ten represents one physical training ring as the selectable catalog unit. This is a product-model adaptation, not a claim that Metolius sells a single ring.

## Source-to-package mapping

| Package field | Evidence and decision |
| --- | --- |
| Identity and dimensions | The product page supports `Metolius`, `Rock Rings 3D`, and `184 × 146 × 57 mm`. |
| Physical contacts | The official guide supports one upper jug and three descending pockets on each physical ring. |
| Pocket metadata | The guide supports 40 mm / four-finger, 32 mm / three-finger, and 25 mm / two-finger pockets. These remain `sizeMillimeters`, `fingerCapacity`, and the corresponding structural pocket `gripType`; no hand capacity or feature tags were invented. |
| Suspension | The official pair photograph supports one suspension per physical ring, entering the two upper shoulders. The routed rig uses two body ports and coincident world ports to render one compact, world-up apex. |
| Material | The uniform unpatterned off-white resin is a user-requested visual adaptation. It is not presented as an official Metolius colorway; the first-party imagery shows patterned production colors. |

## Stable identity and intentional removals

The board ID `metolius.rock-rings-3d`, presentation ID `front-pair`, equipment-object ID `left-ring`, and the four retained legacy hold IDs remain stable:

- `jug-left`
- `pocket-40-four-left`
- `pocket-32-three-left`
- `pocket-25-two-left`

The legacy `-left` spelling now identifies the sole catalog ring; display names are side-neutral. The user explicitly authorized removal of `right-ring` and these four records:

- `jug-right`
- `pocket-40-four-right`
- `pocket-32-three-right`
- `pocket-25-two-right`

`left-ring.missingHandCapacityPolicy` is `unavailable`. Because the source does not establish a two-hand capacity for one contact, the package omits `handCapacity`; the unavailable policy prevents the legacy nil-capacity fallback from treating the sole object as bilateral. A single-hand request for either side resolves the sole matching object, while a double-hand request cannot resolve a nonexistent second ring.

Existing exact-ID workout resolution filters removed IDs out when they are unavailable (`WorkoutActivityRecording.swift`). Custom-routine draft compatibility likewise filters to known IDs (`CustomRoutineDraft.swift`), and routine validation reports an `unknownHoldID` issue (`CustomRoutineStore.swift`). No bundled board-specific plan references the four removed right-side IDs. Older user-created routines that explicitly stored one of those IDs can therefore lose that target or require reselection; this scoped migration does not rewrite saved user data.

## Authored geometry, rig, and approved assets

The four canonical hold paths and routed rig were deliberately authored and reviewed in Workbench. No image-driven detection, segmentation, tracing, registration, vectorization, cropping, or automatic path processing was used. The production geometry and rig are exactly equal to the approved fixture subtrees; their compact JSON SHA-256 values are:

- routed `cordRig`: `3a04cf8d77dbb6708b0ee7498f8edd517b251dac4d8cc5a9c02d103f90e05e88`
- four retained geometry arrays: `fb2d131cac56575b9782f35ddda0b388b79f4fccc4f85d24186139a7aeaa09d8`

The production source asset is the exact approved `1254 × 1254` RGBA PNG, SHA-256 `a01ce830b020d49d593528426eb403bb88cddf2ebf02bdb604381bd6639b43fb`. The canonical presentation uses a `1200 × 1464` portrait scene, square `900 × 900` inner face frame, one shared source asset, and exactly the four retained IDs in `availableHoldIDs`.

The approved standalone production Workbench render is `review-assets/2026-09-07-rock-ring-single-unit-approved.png`, a `1200 × 1464` RGBA PNG with SHA-256 `5691dcc5783f17e721438735dbe8dcc041fd868de4e97706c6631dd3f0cef580`. It is byte-identical to the previously approved fixture render and shows the full ring, two taut shoulder legs, one high rounded apex, no overlays, and transparent surrounding canvas. It is review evidence, not an app screenshot or a second production presentation asset.

## Verification boundary

Focused Python tests cover the single object/four-hold inventory, retained metadata, effective hold availability, square RGBA source asset, portrait scene, loader parsing, and upward routed spans. Final catalog validation and status both report 61 complete packages and 0 drafts.

The three catalog-dependent XCTest expectations were updated, and a small two-object fixture preserves generic bilateral resolver coverage. Per the user's image-review workflow constraint, no simulator, app launch, broad native setup, or XCTest execution was performed for this migration; native test passing is not claimed.
