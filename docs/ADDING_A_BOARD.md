# Adding a hangboard

This guide is the contract for adding a physical hangboard to Hang Ten. It
separates factual hold metadata from visual geometry so future routines can
target a board correctly while every board still shares one coherent design
language.

## 1. Establish the physical source of truth

Collect primary manufacturer evidence before drawing or naming holds:

1. The current product page and official dimensions.
2. A straight-on image for silhouette, spacing, and count.
3. An oblique or side image for jugs, slopers, shelves, and recess depth.
4. A manufacturer hold-depth diagram, numbered guide, or manual when one
   exists.
5. The date the evidence was checked and direct URLs in the change summary or
   a source note.

Do not infer hold depth, finger count, or grip type from appearance when an
official diagram exists. Product photos establish shape; a hold diagram
establishes semantics.

The Compact II audit used these official sources (checked August 1, 2026):

- [Product page](https://www.metoliusclimbing.com/collections/training-boards/products/wood-grips-ii-training-boards)
- [Hold-depth diagram](https://www.metoliusclimbing.com/cdn/shop/files/woodgrips-boards-depths.jpg?v=1762201428)
- [Training-board manual](https://cdn.shopify.com/s/files/1/0955/0030/4457/files/Training-Board-instructions.pdf?v=1759261826)

## 2. Run the staged onboarding pipeline

The canonical package is the source of truth for Compact II:

```text
Hangboards/
  catalog.json
  metolius-wood-grips-compact-ii/
    board.json
    onboarding/runs/<run-id>/...
```

Lifecycle states for `board.json` are `draft`, `onboarding`, `approved`, and
`shipped`.

While onboarding, keep temporary runs under `.context/...` and validate the
registry without mutating the repository:

```sh
scripts/hangboard-tools.sh catalog validate --catalog Hangboards/catalog.json
scripts/hangboard-tools.sh catalog status --catalog Hangboards/catalog.json
```

After a run is approved, copy it into the canonical package. Registration only
accepts symlink-free `.context` runs, advances the board lifecycle when
appropriate, and never downgrades a shipped board:

```sh
scripts/hangboard-tools.sh catalog register \
  --catalog Hangboards/catalog.json \
  --board metolius.wood-grips-compact-ii \
  --run .context/hangboard-onboarding/manufacturer-model \
  --run-id manufacturer-model
```

After the canonical `board.json` is marked `shipped`, regenerate the checked-in
Swift catalog from JSON before shipping app updates:

```sh
scripts/export-board-catalog.sh
scripts/export-board-catalog.sh --check
```

Hang Ten vendors the reviewed onboarding tool under
`Tools/HangboardOnboarding`. Its model-facing contract is deliberately small:
one batched semantic response supplies generic grip hints, while deterministic
local processing owns masks, boundaries, normalized paths, previews, and hash
validation. Exact semantic responses are cached by source pixels, prompt,
schema, provider, model, and request kind. The active repository contract is
the
[unified hangboard repository design](superpowers/specs/2026-08-07-unified-hangboard-repository-design.md).

First prove that the accepted Compact II evidence still replays exactly with
zero model calls:

```sh
scripts/hangboard-tools.sh benchmark
```

Start a new identifiable commercial product in ignored workspace storage:

```sh
scripts/hangboard-tools.sh onboard \
  --product-name "Manufacturer Model" \
  --source /absolute/path/to/front-photo.jpg \
  --output .context/hangboard-onboarding/manufacturer-model
```

At every stop, review only the generated stage image before approving and
resuming:

```sh
scripts/hangboard-tools.sh onboard \
  --output .context/hangboard-onboarding/manufacturer-model \
  --approve stage-0
scripts/hangboard-tools.sh onboard \
  --output .context/hangboard-onboarding/manufacturer-model \
  --resume
```

Repeat approval and resume through Stage 4. The visual checkpoints are:

1. Stage 0: source registration, complete silhouette, and crop.
2. Stage 1: clean transparent product illustration.
3. Stage 2: every usable logical grip labeled once with the correct type.
4. Stage 3: smooth normalized hold boundaries and stable region IDs.
5. Stage 4: normal product, all-highlight, per-type, mixed, and symmetric-pair
   interaction previews.

Use `--status` at any time for read-only hash and state validation. If a local
geometry gate cannot resolve one region, escalate only that crop; do not lower
a gate, request model-generated contours, or infer an unobserved grip from
symmetry. The accepted Compact II replay fixture is versioned at
`Tools/HangboardOnboarding/boards/metolius-wood-grips-compact-ii/`; it is a
test fixture, not the canonical board package.

Only complete runs with approved checkpoints through Stage 4 may be published
into the canonical `Hangboards/<board-folder>/board.json` package. Keep every
unfinished run under the ignored `.context/` directory; the accepted run under
`Tools/HangboardOnboarding/boards/` remains a replay fixture for tests.

## 3. Keep metadata and artwork separate

`TrainingBoard` and `BoardHold` in `HangTen/Models/TrainingModels.swift`
describe what the board is:

- a stable, namespaced board ID;
- manufacturer, model, dimensions, aspect ratio, and product URL;
- one stable ID per selectable physical hold;
- factual depth/finger labels, `HoldKind`, `GripType`, and semantic
  `HoldFeature` values;
- a normalized fallback `HoldFrame` for boards that do not yet have bespoke
  artwork.

`BoardDesign` in `HangTen/Views/BoardDesignLanguage.swift` describes how it is
drawn:

- `silhouette`: the complete outer contour;
- `layers`: top, face, separator, seam, shelf, and bottom planes;
- `holds`: exact selectable contact geometry;
- `palette`: shared textureless materials and depth shading.

Put a bespoke design beside `MetoliusCompactIIDesign.swift` and register it in
`BoardDesignCatalog`. Every `BoardHold.id` must have rendered geometry with the
same `BoardHoldPiece.holdID`, and no rendered hold ID may be orphaned. A DEBUG
assertion enforces this equality for registered designs.

Add the board's semantic mapping to the versioned plan document through
`BuiltInPlanLibraryDefinition` in `PlanStorage.swift`, then regenerate
`PlanLibrary.json` with `scripts/export-plan-library.sh`. A plan is shown only
when every target resolves on the selected board.

## 4. Use generated artifacts as calibration, not interaction geometry

The staged pipeline's accepted raster and SVG are useful when the first Swift
vector draft is too crude. Treat them as calibration evidence:

1. Use the accepted Stage 1 RGBA image for silhouette and dimensional planes.
2. Use Stage 2 for the authoritative logical grip inventory and stable IDs.
3. Translate Stage 3 normalized paths into `BoardShape` commands, using mirrored
   Swift geometry only where the physical source supports symmetry.
4. Compare the Swift normal and highlighted simulator screenshots with the
   accepted Stage 4 previews at the same aspect ratio.
5. Keep iterating until the silhouette, hold boundaries, and highlights align.

Do not use color-thresholding or a separately positioned overlay for active
holds. A raster image may guide the eye, but it cannot be the source for hit
testing or highlights. Runtime geometry must remain deterministic and scalable.

## 5. Build normalized, mirrorable geometry

All design coordinates are normalized from `0...1` inside the board rectangle.
This makes one design scale consistently in cards, portrait workouts,
landscape workouts, and future iPad layouts.

Work from large forms to small ones:

1. Match the real outer silhouette, including taper and overhangs. Do not force
   a rectangle if the physical board is wider at the top or curves at the ends.
2. Add the major dimensional planes. Depth should come from restrained
   gradients, bevels, and shadows—not photographic texture.
3. Place the centerline geometry.
4. Define each left-side pair once, then use
   `CGRect.mirroredHorizontally` and `BoardShape.mirroredHorizontally` for the
   right side. Encode real asymmetry only when supported by evidence.
5. Add hold contact geometry last and verify row spacing against the reference.

The shared visual policy is smooth and sculpted: no wood texture, mounting
bolts, or manufacturer branding unless a future product requirement explicitly
changes that policy. Those details do not help an athlete select a hold.

## 6. Preserve the highlight invariant

Choose the treatment that matches the physical contact:

- `.surface` for slopers and top-contact areas;
- `.shelf` for protruding or rail-like contacts;
- `.recess` for pockets and carved edges, with an explicit deep/shallow
  profile.

`BoardDesign.draw` creates the inactive and active states from the same
`BoardHoldPiece.shape`. For a recess or shelf, it also derives the same inset
contact path before applying either normal shading or the active gradient.
`interactionFrame(for:)` unions the frames for all pieces sharing a hold ID.

Never add a second highlight frame in a view. If a highlight looks misaligned,
fix the declared hold path or treatment.

## 7. Add semantic hold features

Routines should not know a board's private IDs when the manufacturer names a
hold by function. Add the most specific truthful features to each hold:

- slopers: `roundSloper` or `largeSlope`;
- edges: `largeEdge`, `mediumEdge`, `smallEdge`, and only evidence-supported
  flat/incut equivalents;
- pockets: `pocket` plus `twoFingerPocket`, `threeFingerPocket`, or
  `fourFingerPocket`;
- jugs: `jug`.

If a board lacks an exact feature, document any closest-equivalent mapping in
the routine review. Do not silently relabel a different hold type.

For reference, Metolius's Compact II diagram identifies outer jugs; two 56 mm
flat slopers; one 56 mm round sloper; 29 and 19 mm side edges; paired 29 and
19 mm two- and three-finger pockets; and centered 29 and 19 mm four-finger
pockets. That source corrected an early visual-only model that had mislabeled
the lower center pocket as a sloper.

## 8. Validate the completed board

Follow `docs/IOS_SIMULATOR_VALIDATION.md` on a dedicated simulator.

At minimum, capture and inspect:

- the inactive board in portrait and landscape;
- one active `.surface`, `.shelf`, deep `.recess`, and shallow `.recess` hold;
- each distinct semantic pair used by a routine;
- left/right symmetry and center alignment;
- the hand cue for every finger-count or grip type introduced.

Compare screenshots with both the front and oblique sources. Check silhouette,
hold count, centers, widths, top/bottom taper, dimensional planes, and exact
active-path alignment. Build only after every model hold resolves to artwork.

## Completion checklist

- Primary manufacturer sources recorded.
- Board dimensions and aspect ratio verified.
- Every physical selectable hold has stable metadata.
- Every model hold ID equals a rendered hold ID.
- Paired geometry is mirrored unless evidence says otherwise.
- No raster overlay, bolts, branding, or texture leaked into the runtime map.
- Surface, shelf, and recess highlights align pixel-for-pixel.
- Portrait and landscape simulator screenshots reviewed.
- Relevant routines resolve to non-empty, truthful hold sets.
- Versioned board mappings validate and `PlanLibrary.json` is regenerated.
