# Hangboard Canonical Package Design

## Goal

Make one repository-owned board package authoritative for hangboard identity,
hold identity, semantic metadata, lifecycle, and onboarding provenance while
keeping iOS-specific rendering code as a renderer rather than a second board
catalog.

## Scope

The first migration covers Metolius Wood Grips Compact II. The package format
must support boards that are still onboarding, including a source image with no
hold map and a hold map awaiting review. Other catalog images are not migrated
in this change.

## Canonical package

The repository gains this layout:

```text
Hangboards/
  catalog.json
  metolius-wood-grips-compact-ii/
    board.json
    onboarding/
      runs/<run-id>/...
```

`catalog.json` is a small registry containing board IDs, package paths, and
lifecycle states. Each `board.json` contains the stable board ID, product
identity, dimensions, source URLs, lifecycle state, onboarding references, and
the complete stable hold inventory. Each hold uses the iOS-compatible string
ID and may record the numeric onboarding region ID as provenance. Normalized
fallback frames remain board metadata; exact Swift path commands remain
renderer implementation details.

Lifecycle states are `draft`, `onboarding`, `approved`, and `shipped`. A board
can be registered while incomplete. The onboarding package stores run
manifests and stage artifacts; accepted runs remain immutable evidence.

## Tooling boundary

`hangboard-catalog` validates the registry and board packages, registers an
onboarding run into a board package, and reports its lifecycle. Registration
copies the run into the package rather than leaving the shared registry
pointing at ignored `.context` output. Existing staged onboarding commands
continue to generate temporary runs under `.context` until registration.

The validator rejects duplicate IDs, missing package paths, invalid lifecycle
states, duplicate hold IDs, missing normalized frames, and onboarding
references that escape the repository. It also verifies that an accepted run's
region count and numeric region mapping agree with the board manifest.

## iOS integration

The board manifest is converted into a checked-in generated Swift catalog by a
repository script. `TrainingModels.swift` retains the shared model types but
no longer manually defines the Compact II board inventory. The generated
catalog provides the same `BoardCatalog.all` API used by routines and views.

`BoardDesign` remains the iOS rendering adapter: its silhouette, layers, and
exact Swift shapes are not duplicated into the JSON manifest. Its existing
DEBUG hold-ID invariant continues to ensure every manifest hold has matching
rendered geometry. A generator check prevents the Swift catalog from drifting
from the JSON package.

## Verification

- Python tests cover catalog validation, lifecycle registration, path
  confinement, onboarding region mapping, and Swift generation.
- The generated Swift file is checked with `--check`.
- The iOS unit test suite and simulator Debug build validate that routines and
  board selection still resolve the Compact II board.
- Existing onboarding tests and the accepted replay fixture remain unchanged.
