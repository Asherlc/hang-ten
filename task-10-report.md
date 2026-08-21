# Task 10 report — Metolius Rock Rings 3D

Completed 2026-08-21 in workspace `giant-pug`.

## Outcome

Created the complete schema-v2 package at
`Hangboards/metolius-rock-rings-3d/` with one honest paired-front
presentation, eight source-supported left/right physical contacts, one
AI-simplified PNG, and no undeclared package files. Added the complete official
source/field audit to
`docs/source-audits/2026-08-20-complete-hangboard-catalog.md` and focused
inventory/mirror assertions to
`Tools/HangboardPackages/tests/test_approved_board_packages.py`.

## Exact official sources

1. Current product page:
   `https://www.metoliusclimbing.com/collections/training-equipment/products/rock-rings-3d`
   - Establishes `Metolius`, `Rock Rings 3D`, two independent units,
     portable identity, flexible single-point suspension, CAD/CAM perfect
     symmetry, and metric dimensions of 184 × 146 × 57 mm.
2. Official paired product photographs:
   - `https://www.metoliusclimbing.com/cdn/shop/files/Rock-Rings-black-white.jpg?v=1759460123`
   - `https://www.metoliusclimbing.com/cdn/shop/files/Rock-Rings-blue-white.jpg?v=1759460123`
   - Establish two separately suspended units, paired left/right layout,
     cord routing, one upper contact, and three separated pocket openings per
     unit; the two current colors share one physical layout.
3. Official numbered depth diagram:
   `https://www.metoliusclimbing.com/cdn/shop/files/Rock-Ring-Depts.jpg?v=1762201543`
   - Freezes the per-unit order and facts: jug; 40 mm four-finger pocket;
     32 mm three-finger pocket; 25 mm two-finger pocket.
4. Official Rock Ring training guide and its layout images:
   - `https://www.metoliusclimbing.com/pages/rock-ring-training-guide`
   - `https://cdn.shopify.com/s/files/1/0955/0030/4457/files/Rock_Rings-th.jpg?v=1759521022`
   - `https://cdn.shopify.com/s/files/1/0955/0030/4457/files/roc-num-dep.jpg?v=1759521022`
   - Independently support compact portable single-point suspension and the
     same paired numbered layout. No routine text was imported.
5. Official Training Board and Rock Rings instructions:
   `https://cdn.shopify.com/s/files/1/0955/0030/4457/files/Training-Board-instructions.pdf?v=1759261826`
   - Expressly classify Rock Rings as suspended devices. The generic manual
     adds no model-specific contact or alternate usable face.

No reseller evidence was used for identity, inventory, metadata,
presentation mapping, measurement, or geometry.

## Presentation and contact mapping

The package declares one `front-pair` presentation because every current
official layout view shows the same usable front contacts. Flexible joint
rotation is a suspension behavior, not evidence of a second usable surface.
No rear or rotated presentation was fabricated.

The two independent devices remain separately selectable:

| Unit | Contacts |
| --- | --- |
| Left | `jug-left`, `pocket-40-four-left`, `pocket-32-three-left`, `pocket-25-two-left` |
| Right | `jug-right`, `pocket-40-four-right`, `pocket-32-three-right`, `pocket-25-two-right` |

Pocket sizes and finger capacities are copied directly from the official
numbered diagram. Unsupported posture, feature tags, depth ranges, material,
color, coaching text, and training semantics are omitted.

## Artwork provenance

`assets/primary.png` was generated with the built-in image-generation tool in
`product-mockup` mode. The official pair photograph was reference Image 1 and
the numbered depth diagram was reference Image 2. The exact prompt is preserved
verbatim in the source audit.

- `assets/primary.png`: 1536 × 1024, aspect 1.5, SHA-256
  `679f403f74b50b63099574b1fc8a39c75c54c27f1a70d66a1a0ec637d4ea6837`.

The illustration is explicitly NON-evidence. All physical facts were frozen
from the official sources before generation. The accepted output was copied
directly into the package with no crop, registration, detection, segmentation,
mask, contour extraction, vectorization, simplification, or generated geometry
operation.

## Manual path authoring and review

The four left-unit canonical paths were deliberately authored in normalized
coordinates against the accepted illustration and checked against the official
pair photograph and depth diagram. Under Metolius's explicit perfect-symmetry
claim, the corresponding right frames are exact horizontal mirrors. Each
regular pocket uses an operator-selected `roundedRectangle` constraint; each
curved jug uses a custom path. Saved paths remain the sole normal, active, and
hit-test source of truth.

| Contact pair | Left normalized frame; right exact mirror | Manual boundary decision |
| --- | --- | --- |
| Jugs | `x .145, y .322, w .306, h .143` | Broad upper contact only; excludes cord, background, and 40 mm pocket. |
| 40 mm pockets | `x .206, y .454, w .176, h .091` | Upper four-finger pocket opening only. |
| 32 mm pockets | `x .231, y .615, w .136, h .082` | Middle three-finger pocket opening only. |
| 25 mm pockets | `x .248, y .760, w .096, h .068` | Lower two-finger pocket opening only. |

Workbench extraction of the real package returned one 1536 × 1024
`front-pair` presentation and exactly eight regions in the source-backed order.
It retained six rounded-rectangle constraints and two custom jug paths. Surface
switching is deliberately inapplicable because the primary evidence supports
only one presentation; the existing focused Workbench v2 switching tests still
passed.

## Verification

- `rtk scripts/hangboard-packages.sh validate --root Hangboards --final-inventory`
  — passed with `metolius.rock-rings-3d` discovered and zero drafts.
- `rtk scripts/hangboard-packages.sh status --root Hangboards`
  — passed and listed the package.
- Focused approved-package tests (`direct_discovery`,
  `complete_presentation_asset_set`, `rock_rings`) — 4 passed.
- Full `Tools/HangboardPackages/tests` suite — 85 passed.
- Direct Workbench extraction — one `front-pair` presentation, eight expected
  regions, six constraints, and two custom paths.
- Focused Workbench v2 extraction/switching/preservation tests — 3 passed.
- Full Workbench `test_board_package.py` suite — 85 passed.
- Real `scripts/stage-board-packages.py` invocation with an isolated Xcode
  resource destination — passed; staged only `board.json` and
  `assets/primary.png`, with staged hashes matching their sources.

## Limitations and deferred review

This task does not claim the catalog-wide iOS simulator normal/active/hit-test
review assigned to Task 12. It adds no routine, coaching guidance, or
manufacturer training claims. The art is simplified non-photographic app
content, and its canvas aspect is presentation metadata rather than a physical
dimension.

No alternate face is represented because no current official Metolius source
identifies another usable contact surface. If primary evidence later documents
one, it should be added as a separate presentation rather than overlaid on this
paired-front view.

## Cleanup

- The isolated staging tree `/private/tmp/giant-pug-task10-staging` was removed
  by its EXIT trap, and a post-run check verified it absent.
- Workspace-owned official source downloads under
  `.context/giant-pug-task10-rock-rings` were removed after review.
- No Workbench listener, simulator, container, or other external resource was
  created for this task.
- Official source photographs and guide images are not package artifacts and
  were not committed.
