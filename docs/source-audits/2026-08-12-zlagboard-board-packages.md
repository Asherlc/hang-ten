# Zlagboard Evo and Pro package-source audit

Rechecked 2026-08-19. This audit supersedes the removed 14-contact Evo and
21-contact Pro candidates. Those old candidates represented only cavity rows,
omitted the seven continuous top contacts, and carried unsupported generic
classification. Neither old package nor any automated image output was used as
authoring input.

## Primary source set

| field | Evo evidence | Pro 2.0 evidence | package decision |
| --- | --- | --- | --- |
| identity, intended range, named hold families, material | [Official Zlagboard hangboards page](https://www.zlagboard.com/hangboards) names `Zlagboard.Evo`, describes it as compact and lists crimps, pockets, slopers, and jugs; the same page says all Zlagboards use noble lime wood. | The [same official page](https://www.zlagboard.com/hangboards) names `Zlagboard.Pro`, describes its varied ergonomic holds, and says all Zlagboards use noble lime wood. The [official app page](https://www.zlagboard.com/app) separately identifies Pro 1.0 and Pro 2.0. | Identity, conservative subtitle, manufacturer, product URL, and lime-wood material wording only. No performance claim was converted into hold metadata. |
| straight-on presentation image | [Official Evo product PNG](https://www.zlagboard.com/assets/web/Zlagboard_EVO-newscreen2x-fb153e0817b3e2ffc54e8fabd042ed5e7fffa804ef80388787da3b777004da3f.png), 1302 × 404. | [Official current Pro product PNG](https://www.zlagboard.com/assets/web/Zlagboard-2019-smaller2x-8011f7e115f3707e78d58c5b3587d3a15fd82b009c421a6c6dbc9f560e50dc1b.png), 1302 × 462. | Stored byte-for-byte as `assets/primary.png`; image dimensions establish package aspect ratio and geometry coordinates. |
| exhaustive physical hold map | [Official Evo hold map](https://www.zlagboard.com/assets/web/zlagboard-evo-holds-014x2x-00d8566361fdbbb0740896a8a7805e652d20e09b2fbe54eb2d36b4b7ecb66d10.png). | [Official Pro 2 hold map](https://www.zlagboard.com/assets/web/zlagboard-pro2-holds-014x2x-af05a1450fd55d0cdba84c0bcd43206f2798cf426cb31f5bf762d33acb66d34d.png); its filename and the official app's distinct Pro 2.0 entry identify the pictured current model. | Exact contact inventory, row order, left/right pairing, top `JUG`, `32°`, `20°`, and `sloper JUG` labels, plus every printed millimeter depth and `sloper`/`incut` qualifier. |
| required dimensions field | [Bananafingers Evo listing](https://bananafingers.co.uk/zlagboard-evo-p3554z) reports `70 × 23 × 6 cm`. | [Chalkr Pro 2.0 listing](https://chalkr.de/vertical-life-zlagboard-pro-trainingsboard.html) reports length 70.5 cm, depth 25 cm, and height 8 cm. | Limited secondary fallback because schema version 1 requires a nonempty dimensions fact and the current first-party page publishes none. Recorded as `70 × 23 × 6 cm` and `70.5 × 25 × 8 cm`; no weight or secondary material claim was imported. |

The secondary dimension sources are not used for inventory, kinds, sizes,
geometry, or product identity. A separate Evo retailer mixes a `6 cm` headline
with an `8 cm` technical depth, so it was intentionally excluded rather than
used to broaden or overwrite the single corroborated package string.

## Frozen physical inventory

Both official maps are exhaustive seven-column layouts. Every colored top
segment and every colored cavity is a distinct continuous physical contact.

### `zlagboard-evo` — 21 contacts

- Top row, left to right: jug; 32-degree sloper; 20-degree sloper; center
  sloper jug; 20-degree sloper; 32-degree sloper; jug.
- First cavity row, left to right: 30 mm edge; 30 mm sloper edge; 25 mm
  sloper edge; 35 mm center edge; mirrored 25 mm sloper, 30 mm sloper, and
  30 mm edge.
- Second cavity row, left to right: 20 mm edge; 25 mm sloper edge; 30 mm
  inner edge; 30 mm center sloper edge; mirrored 30 mm edge, 25 mm sloper,
  and 20 mm edge.

### `zlagboard-pro` — 28 contacts

- The same seven top contacts and first two seven-contact cavity rows shown on
  the Evo map.
- Third cavity row, left to right: incut 15 mm edge; 15 mm edge; inner incut
  30 mm edge; center incut 10 mm edge; mirrored incut 30 mm, 15 mm, and incut
  15 mm edges.

The old 14/21 counts were incomplete because they counted only two/three rows
of cavities. No two visible contacts were merged, and no continuous contact
was split into multiple logical holds.

## Geometry and constraint decisions

- Geometry was drawn directly against the official straight-on product PNGs.
  The official maps supplied the exhaustive topology and label mapping; they
  were not traced, registered, segmented, or vectorized.
- Left/right frames are exact normalized mirrors because both official product
  images and maps establish bilateral symmetry. The irregular seven top paths
  are freeform; their paired canonical commands are mirrored exactly.
- Each machined cavity mouth is a regular horizontal capsule. An operator
  selected the Workbench `pill` constraint for all 14 Evo cavity paths and all
  21 Pro cavity paths. Workbench's production primitive serialized the exact
  cubic canonical paths. The constraint remains metadata only; those paths are
  the rendering, highlighting, and hit-testing truth.
- Capacities, grip posture, feature tags, and any measurement not printed in
  the official hold maps are omitted. The map's degree labels are preserved in
  top-hold names because schema version 1 has no angle field.

## Validation evidence

- Final-inventory package validation reports complete direct-child packages
  with zero drafts.
- Strict Workbench loading reports 21 Evo regions and 28 Pro 2.0 regions; all
  49 paths are closed.
- Exact bilateral mirror checks pass. Zero-delta constrained resize is byte
  exact for all 35 constrained cavity pieces.
- Normal overlays, exhaustive one-active-contact-per-tile sheets, real
  Workbench screenshots, and DOM hit-test results were reviewed.
- Owned isolated iOS validation covered the four YY and two Zlag boards:
  normal and exhaustive-active screenshots visually passed, all 12/12
  production `BoardHoldPathShape` probes passed, and cleanup completed.

## 2026-08-25 source-audited metadata certification

The two exhaustive official hold maps were re-opened and checked column by
column against all 49 visible stable IDs in
`.context/hangboard-metadata-backfill-icky-cow/yy-zlagboard/`. `icky-cow` is
the workspace-owned fallback because `CONDUCTOR_WORKSPACE_NAME` was unset.
Unmodified copies of the maps used for manual review remain under
`.context/hangboard-metadata-backfill-icky-cow/yy-zlagboard-task9-official/`.
The captures and maps were used only to reconcile manufacturer labels with
existing IDs; geometry did not change.

### Exact stable-ID field map

Every row's map label verifies the listed `kind`. Printed millimetres populate
`sizeMillimeters`; `grip` and `feature` name exact enum mappings. The ID groups
are exhaustive for each map label.

| Boards | Stable hold IDs | Official map label | Kind | Size | Grip | Feature |
| --- | --- | --- | --- | ---: | --- | --- |
| Evo + Pro | `top-jug-{left,right}` | `JUG` | `jug` | — | — | `jug` |
| Evo + Pro | `top-sloper-32-{left,right}` | `32°` top sloper | `sloper` | — | `sloper` | — |
| Evo + Pro | `top-sloper-20-{left,right}` | `20°` top sloper | `sloper` | — | `sloper` | — |
| Evo + Pro | `top-sloper-jug-center` | `sloper JUG` | `sloper` | — | `sloper` | `jug` |
| Evo + Pro | `edge-30-{left,right}` | `30 mm` | `edge` | 30 | — | — |
| Evo + Pro | `sloper-edge-30-{left,right}` | `sloper 30 mm` | `sloper` | 30 | `sloper` | — |
| Evo + Pro | `sloper-edge-25-{left,right}` | `sloper 25 mm` | `sloper` | 25 | `sloper` | — |
| Evo + Pro | `edge-35-center` | `35 mm` | `edge` | 35 | — | — |
| Evo + Pro | `edge-20-{left,right}` | `20 mm` | `edge` | 20 | — | — |
| Evo + Pro | `sloper-edge-25-lower-{left,right}` | `sloper 25 mm` | `sloper` | 25 | `sloper` | — |
| Evo + Pro | `edge-30-inner-{left,right}` | `30 mm` | `edge` | 30 | — | — |
| Evo + Pro | `sloper-edge-30-center` | `sloper 30 mm` | `sloper` | 30 | `sloper` | — |
| Pro | `edge-incut-15-{left,right}` | `incut 15 mm` | `edge` | 15 | — | `incutEdge` |
| Pro | `edge-15-{left,right}` | `15 mm` | `edge` | 15 | — | — |
| Pro | `edge-incut-30-{left,right}` | `incut 30 mm` | `edge` | 30 | — | `incutEdge` |
| Pro | `edge-incut-10-center` | `incut 10 mm` | `edge` | 10 | — | `incutEdge` |

This preserves both words in the compound `sloper JUG` label without forcing
a false binary classification: its mandatory `kind` remains `sloper`, its
`gripType` is `sloper`, and its exact qualifier is stored as feature `jug`.

### Coverage and deliberate blanks

The ledger certifies all 49 kinds, 35 scalar depths, 24 sloper grip enums, and
11 feature arrays (six `jug`, five `incutEdge`). Every other field has an
explicit blank outcome. The maps publish fixed values, not depth intervals;
degree labels are not converted to millimetres. Both boards' general marketing
copy mentions pockets, but neither exhaustive map assigns a pocket family or
finger count to a contact, so no hold is reclassified and no capacity is
guessed from a cavity's appearance. The sources also do not state simultaneous
hand capacity or prescribe an edge posture enum.
