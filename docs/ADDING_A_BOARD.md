# Adding a hangboard

This guide is the active contract for adding a physical hangboard to Hang Ten.
Physical identity, hold metadata, and exact selectable geometry live in one
`board.json`; research and training-plan semantics stay outside board packages.

## 1. Establish the physical source of truth

Collect primary manufacturer evidence before naming or classifying holds:

1. The current product page and official dimensions.
2. A straight-on image for spacing and hold count.
3. An oblique or side image for jugs, slopers, shelves, and recess depth.
4. A manufacturer hold-depth diagram, numbered guide, or manual when one exists.
5. Source URLs, review date, and field mappings in a source-audit document.

Do not infer measurements, finger capacity, or grip posture when the source does
not establish them. Omit unknown optional fields instead of supplying defaults.

## 2. Create one direct-child package

Every board is a flat directory below `Hangboards/`. Direct discovery treats a
directory containing `board.json` as app content. A finished package contains
exactly:

```text
Hangboards/
  manufacturer-model/
    board.json
    assets/
      primary.png
```

A primary-only directory is a migration draft that the Workbench can open. It
is ignored by app staging until `board.json` is complete. Do not add a registry,
sidecar JSON, source photo, README, review directory, or duplicate geometry.

`board.json` contains product identity and physical holds. Every hold requires
`id`, `name`, one of `jug`, `edge`, `pocket`, `pinch`, or `sloper`, and a
nonempty `geometry` array. Each geometry piece contains a normalized `frame`, a
closed supported `shape`, and optional physical treatment. Measurements, depth
ranges, finger capacity, grip posture, and feature tags are optional.

Set `presentation.assetPath` to exactly `assets/primary.png`. Any other value is
rejected by the loader.

Validate direct discovery and the single-file package contract after every
package change:

```sh
scripts/hangboard-tools.sh packages validate --root Hangboards
```

Use `--final-inventory` only when every primary-only draft has been authored;
that mode rejects any directory missing `board.json`.

## 3. Bundle discovered packages directly

Xcode invokes `scripts/stage-board-packages.py` during every build. It validates
each complete direct child and copies only those package directories into the
app resource bundle. It does not generate a registry or app-side board catalog.

Confirm the package loader compiles with the normal bounded simulator build:

```sh
xcodebuild build-for-testing -project HangTen.xcodeproj -scheme HangTen \
  -destination 'generic/platform=iOS Simulator'
```

## 4. Optional onboarding work

Onboarding artifacts belong under `.context/`. They can support later human
authoring but are not package content and are never bundled directly.

```sh
scripts/hangboard-tools.sh onboard \
  --product-name "Manufacturer Model" \
  --source /absolute/path/to/front-photo.jpg \
  --output .context/hangboard-onboarding/manufacturer-model
```

## Completion checklist

- Source URLs and field mappings are recorded in a source audit.
- The package contains exactly `board.json` and `assets/primary.png`.
- Every hold has unique identity and nonempty normalized geometry.
- Unsupported optional physical facts remain omitted.
- Direct discovery and staging tests pass.
- Normal, active, and hit-testing paths are inspected on an owned simulator.
