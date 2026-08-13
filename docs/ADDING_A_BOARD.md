# Adding a hangboard

This guide is the active contract for adding a physical hangboard to Hang Ten.
It keeps factual hold metadata, artwork, and their source mappings together in
one canonical package.

## 1. Establish the physical source of truth

Collect primary manufacturer evidence before naming holds or drawing artwork:

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

Every package is a single flat directory below `Hangboards/`; lifecycle names
do not appear in its path.

```text
Hangboards/
  catalog.json
  manufacturer-model/
    board.json
    evidence.json
    semantics.json
    artwork.json
    assets/
```

`catalog.json` is the registry. It has exactly two statuses:

```json
{"id": "manufacturer.model", "path": "manufacturer-model", "status": "draft"}
{"id": "manufacturer.model", "path": "manufacturer-model", "status": "approved"}
```

In review shorthand, `status: draft` is the non-shipping state and
`status: approved` is the only shipping-eligible state.

Use `draft` while evidence, hold facts, semantics, or artwork still need
review. A draft may retain imported reference material below its package, but
it is not a factual source and drafts never ship. Do not add runtime facts,
routine mappings, or app assets from a draft.

An `approved` entry requires all four package documents, their source-backed
evidence mappings, valid artwork, and an approved package validator result.
Promotion is a review decision: do not manufacture missing evidence or fill a
hold field from an image alone.

Validate the registry after every package or status change:

```sh
scripts/hangboard-tools.sh catalog validate --catalog Hangboards/catalog.json
scripts/hangboard-tools.sh catalog status --catalog Hangboards/catalog.json
```

The importer keeps the previous generated-catalog material as draft review
inventory. Its historical rationale is recorded in
[the catalog history](history/HANGBOARD_GENERATIVE_CATALOG.md); that material
is not active package evidence or runtime input.

## 3. Bundle approved packages directly

The app bundles only approved packages plus `catalog.json`. Xcode invokes
`scripts/stage-approved-board-packages.py` during the build and copies the
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

## 4. Optional onboarding work

The staged onboarding tool produces review artifacts under `.context/`. Those
artifacts can support a later human-authored package, but a completed run is
not itself an approved package and is never bundled directly.

```sh
scripts/hangboard-tools.sh onboard \
  --product-name "Manufacturer Model" \
  --source /absolute/path/to/front-photo.jpg \
  --output .context/hangboard-onboarding/manufacturer-model
```

Review and retain only source-backed facts when preparing the package. Keep
unfinished runs and generated previews in `.context/`; they are not part of
the app or the canonical registry.

## Completion checklist

- Primary manufacturer sources and review date are recorded in `evidence.json`.
- The package has a flat slug path and one registry entry.
- The entry is `draft` until the package is complete and reviewed.
- An approved package passes catalog validation with source-backed metadata,
  semantics, and artwork.
- The app build stages only approved package directories.
- Portrait and landscape normal and active hold states are inspected on the
  dedicated simulator before shipping.
