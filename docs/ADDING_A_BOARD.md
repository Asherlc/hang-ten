# Adding a hangboard

This guide is the active contract for adding a physical hangboard to Hang Ten.
It keeps factual hold metadata, normalized hold frames, exact Workbench
geometry, semantics, assets, and their source mappings together in one
canonical package.

## 1. Establish the physical source of truth

Collect primary manufacturer evidence before naming holds or defining frames:

1. The current product page and official dimensions.
2. A straight-on image for silhouette, spacing, and count.
3. An oblique or side image for jugs, slopers, shelves, and recess depth.
4. A manufacturer hold-depth diagram, numbered guide, or manual when one
   exists.
5. Direct source URLs and the review date in the package evidence.

Do not infer hold depth, finger count, or grip type from appearance when an
official diagram exists. Product photos establish shape; a hold diagram
establishes semantics.

The Compact II audit uses these official sources:

- [Product page](https://www.metoliusclimbing.com/collections/training-boards/products/wood-grips-ii-training-boards)
- [Hold-depth diagram](https://www.metoliusclimbing.com/cdn/shop/files/woodgrips-boards-depths.jpg?v=1762201428)
- [Training-board manual](https://cdn.shopify.com/s/files/1/0955/0030/4457/files/Training-Board-instructions.pdf?v=1759261826)

## 2. Create a flat package and registry entry

Every board is a single flat directory below `Hangboards/`. A board with only
`assets/primary.png` is a draft that can be opened in the Workbench. A complete
package listed in `catalog.json` is published. These are the only two repository
statuses; do not add lifecycle, review, confidence, approximation, automation,
or shipping fields or directories.

```text
Hangboards/
  catalog.json
  manufacturer-model/
    board.json
    artwork.json
    evidence.json
    semantics.json
    assets/
      primary.png
      original-source-photo.jpg # optional, unchanged, evidence-covered
```

`catalog.json` is the registry. Each entry has exactly an identifier and flat
package path:

```json
{"id": "manufacturer.model", "path": "manufacturer-model"}
```

Registered packages contain exactly `board.json`, `artwork.json`,
`evidence.json`, and `semantics.json`. `assets/primary.png` is the only board
visual. Each `board.json` hold frame is the factual normalized region generic
consumers use for taps and active or preview highlights. `artwork.json` is the
Workbench's exact, contiguous closed path for each physical hold; it is edited
directly and stays consistent with the corresponding frame. Do not add
`outline.json`, `outline.approx.json`, alternate derived images, a `review/`
directory, or a board README. An optional original source image must be a flat
`.jpg`, `.jpeg`,
`.webp`, or `.heic` asset and have an exact package-relative entry in
`evidence.json.assetEvidence`; it does not establish non-visible hold facts.

An unregistered draft board contains only `assets/primary.png` and no JSON
sidecars, README, review directory, outline, or parallel geometry. It is
editable Workbench input, but is not published app content. Keep research gaps
in the branch or a source-audit document, then author all four sidecars only
when official manufacturer evidence supports the board facts, hold frames,
exact hold geometry, and semantics.

Every registered package requires nonempty HTTPS evidence sources, an ISO
`checkedAt` date, and exact evidence mappings for each factual field, hold
field, semantic target, artwork element, and retained asset. Do not manufacture
missing evidence or fill a hold field, frame, or geometry from an image alone.

Validate the registry after every package change:

```sh
uv run --with pytest python -m pytest -q Tools/HangboardWorkbench/tests/test_board_package.py
```

The importer keeps generated catalog images as unregistered, primary-only
draft boards. Its historical rationale is recorded in
[the catalog history](history/HANGBOARD_GENERATIVE_CATALOG.md); that material
is not active package evidence or runtime input.

## 3. Bundle registered packages directly

The app bundles only registered packages plus `catalog.json`. Xcode invokes
`scripts/stage-board-packages.py` during the build and copies the
validated resources into the app bundle. Do not copy package files into an
asset catalog, add board definitions to Swift, or generate an app-side board
catalog.

Confirm the final package set with the normal build and package-store tests:

```sh
xcodebuild test -project HangTen.xcodeproj -scheme HangTen \
  -destination 'platform=iOS Simulator,name=iPhone 17 Pro' \
  -only-testing:HangTenTests/BoardPackageStoreTests
xcodebuild build -project HangTen.xcodeproj -scheme HangTen \
  -destination 'generic/platform=iOS Simulator'
```

## Completion checklist

- Primary manufacturer sources and review date are recorded in `evidence.json`.
- The package has a flat slug path, exactly four JSON sidecars, one generated
  `assets/primary.png`, and at most one evidence-covered original source photo.
- It has one registry entry only after source-backed metadata, semantics, and
  artwork pass catalog validation.
- Draft boards remain primary-only with no app/package lifecycle state.
- The app build stages only registered package directories.
- Portrait and landscape normal and active hold states are inspected on the
  dedicated simulator before shipping.
