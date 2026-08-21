# Task 9 report — Metolius Light Rail 2.0

Completed 2026-08-21 in workspace `giant-pug`.

## Outcome

Created the complete schema-v2 package at
`Hangboards/metolius-light-rail-2/` with two explicitly declared reversible
presentations, four source-supported physical contacts, one AI-simplified PNG
per presentation, and no undeclared package files. Added the exact official
source/field audit to
`docs/source-audits/2026-08-20-complete-hangboard-catalog.md` and a focused
inventory test to
`Tools/HangboardPackages/tests/test_approved_board_packages.py`.

## Exact official sources

1. Product page:
   `https://www.metoliusclimbing.com/products/light-rail`
   - Establishes `Metolius`, `Light Rail 2.0`, portable/reversible identity,
     exactly four holds, 15/20/40 mm published depths, body-weight-only limit,
     weight, FSC certification, and 18 × 3 × 1.5 in dimensions.
2. Official product photograph:
   `https://www.metoliusclimbing.com/cdn/shop/files/Light-Rail-2-PT.jpg?v=1767727616`
   - Establishes the rail silhouette, single routed channel, suspension-cord
     routing, upright `40/20` markings, and inverted `15/40` markings.
3. Official Metolius usage video embedded by the product page:
   `https://www.youtube.com/watch?v=t208TAIW1LM`
   - Identifies the newer Light Rail/Light Rail 2.0; explicitly distinguishes
     the 20 mm edge on one side, 15 mm edge on the other side, and rounded jug
     on top; supplies close-up/use evidence only, never geometry.
4. Official instructions:
   `https://cdn.shopify.com/s/files/1/0955/0030/4457/files/Training-Board-instructions.pdf?v=1759261826`
   - Expressly classify Light Rails as suspended devices and document hanging
     them from a solid anchor. The generic manual adds no model-specific hold,
     size, capacity, posture, or training-plan fact.

No reseller source was used for product identity, inventory, metadata,
presentation mapping, contact kind, measurement, or geometry.

## Reversible presentation and hold mapping

The official four-hold claim is represented as two distinct contacts on each
usable suspended orientation. The flat cord-routing back is omitted because
no official source calls it a usable contact.

| Presentation | Asset | Physical contacts |
| --- | --- | --- |
| `20mm-side` (default) | `assets/primary.png` | `jug-40-20mm-side` (40 mm rounded jug), `edge-20` (20 mm edge) |
| `15mm-side` | `assets/15mm-surface.png` | `jug-40-15mm-side` (40 mm rounded jug), `edge-15` (15 mm edge) |

Every hold has an explicit `presentationID`; none is duplicated across views.
Unsupported finger capacities, grip postures, feature tags, coaching text, and
training semantics are omitted.

## Artwork provenance

Both assets were generated independently with the built-in image-generation
tool in `product-mockup` mode using the official product photograph as the
single reference image. The generation prompts are preserved verbatim in the
source audit.

- `assets/primary.png`: 1536 × 1024, aspect 1.5, SHA-256
  `ec94a25e2f653d7972eea4c755df5413aa70a81c393764365b0cdbaa8232fc12`.
- `assets/15mm-surface.png`: 1672 × 941, aspect `1672 / 941`, SHA-256
  `7b365965bb7d3c7b6f1fcd8c2503c5a77ddba8cc75084294c5a7766a90ef3705`.

The generated art is explicitly NON-evidence. Physical facts were frozen
before generation from the four official sources above. Each accepted PNG was
copied directly into the package with no crop, registration, segmentation,
mask, contour extraction, vectorization, simplification, or other automatic
geometry operation.

## Manual path authoring and review

The four paths were deliberately authored as normalized closed paths after
directly viewing each accepted surface image together with the official photo,
video close-up/use evidence, product-page inventory, and manual classification.
No pixel measurement, tracing, detection, segmentation, registration, mask,
or generated path proposal was used.

| Hold | Normalized frame | Manual boundary decision |
| --- | --- | --- |
| `jug-40-20mm-side` | `x .025, y .436, w .950, h .101` | Default image's upper rounded outer rail; cord, channel, and background excluded. |
| `edge-20` | `x .099, y .558, w .802, h .053` | Default image's long lower channel shelf only. |
| `jug-40-15mm-side` | `x .034, y .406, w .932, h .103` | Reversed image's upper rounded outer rail only. |
| `edge-15` | `x .083, y .551, w .834, h .047` | Reversed image's long lower channel shelf only. |

Each genuinely regular long contact uses an operator-selected
`roundedRectangle` constraint. The saved path, not the constraint or raster,
remains the rendering, highlight, and hit-test source of truth.

Live Workbench review on an owned temporary listener verified:

- the default surface extracts only `jug-40-20mm-side` and `edge-20`;
- switching to `15mm-side` changes the selected presentation/image URL and
  extracts only `jug-40-15mm-side` and `edge-15`;
- both served surface images are byte-identical to their checked-in assets;
- the four saved region paths and frames remain scoped to their declared
  presentation.

## Verification

- `rtk scripts/hangboard-packages.sh validate --root Hangboards --final-inventory`
  — passed with `metolius.light-rail-2` discovered and zero drafts.
- `rtk scripts/hangboard-packages.sh status --root Hangboards`
  — passed and listed the new package.
- Focused approved-package tests (`direct_discovery`,
  `complete_presentation_asset_set`, `light_rail`) — 3 passed.
- Focused Workbench v2 extraction/switching tests — 3 passed.
- Full `Tools/HangboardPackages/tests` suite — 83 passed.
- Real `scripts/stage-board-packages.py` invocation with an isolated Xcode
  resource destination — passed; staged `board.json`, `primary.png`, and
  `15mm-surface.png` only, with both staged PNG hashes matching their sources.
- Live Workbench API extraction/switching and exact image-byte comparisons —
  passed for both presentations.

## Limitations and deferred review

This Task 9 implementation does not claim the catalog-wide iOS simulator
normal/active/hit-test review assigned to Task 12 of the approved plan. It also
does not add a routine or training guidance. Product video exercise captions
were used only to identify the device/contact terms and were not imported as
training content.

The surface artwork is simplified, non-photographic app content. Its differing
canvas ratios are intentional and independently declared. Physical dimensions
come only from the product page, never from either canvas.

## Cleanup

- Temporary Workbench listener `127.0.0.1:4199` was stopped by its EXIT trap;
  `lsof` verified no listener remained.
- Workspace-owned source/video-review files and local decoder environment under
  `.context/giant-pug-task9` were deleted after review.
- Isolated staging output `/private/tmp/giant-pug-task9-staging` was deleted
  after hash verification.
- Official source photographs, video, captions, and manual are not package
  artifacts and were not committed.
