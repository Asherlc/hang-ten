# Unversioned content formats

## Goal

Use one fixed, unversioned data shape for bundled hangboard packages, the plan
library, and custom-routine persistence. The application has no user-created
boards or routines to migrate, so no compatibility reader or on-device data
migration is required.

## Scope

- Every `Hangboards/*/board.json` uses the current multi-presentation shape,
  but omits `schemaVersion`.
- Each board declares a non-empty `presentations` array with exactly one
  default. Every hold declares the ID of one declared presentation.
- `PlanLibrary.json`, `PlanLibraryDefinition`, and `CustomRoutineLibrary`
  omit schema/version fields. The plan-library metadata version is also
  removed; it is not part of the runtime model.
- Board, plan, routine, Workbench, package-tool, and test code accept only
  those fixed shapes.

The change does not remove application release versions, source-control
history, external manufacturer model names, or workout-session migration code;
those are not schemas for boards, plans, or routines.

## Data migration

One checked-in deterministic migration rewrites the 33 single-presentation
v1 board documents. For each board it:

1. Deletes `schemaVersion` and the legacy `presentation` object.
2. Adds a single default presentation named `Primary`, with ID `primary`,
   asset path `assets/primary.png`, and the existing `aspectRatio`.
3. Adds `presentationID: "primary"` to every existing hold.

The migration leaves board IDs, manufacturer metadata, image files, geometry
paths, semantic data, and all hold metadata byte-for-byte unchanged apart from
the required JSON fields. Existing v2 boards only lose their schema-version
field. The plan-library resource similarly loses its version fields without
changing plan content.

## Runtime design

`BoardPackageStore.swift`, Workbench `board_package.py`, and
`Tools/HangboardPackages` parse one board document form. They reject a
`schemaVersion` or legacy `presentation` key as an unknown field, require the
presentations list, and require a valid presentation ID for every hold. The
GitHub-backed catalog performs the same metadata-only checks without fetching
image blobs.

`PlanStorage.swift` decodes and validates one `PlanLibraryDefinition` shape;
the schema enum, validation issue, unsupported-schema error, and migration
branches are removed. `CustomRoutineStore.swift` stores only its routine list;
the schema field and unsupported-schema error are removed. No fallback decoder
or automatic rewrite remains.

## Failure handling

Malformed or stale versioned files fail during strict decoding with the
existing package/library error surfaces. The error identifies the malformed
resource or unknown field; it never silently treats a legacy document as the
new schema.

## Verification

- Deterministic migration tests assert every shipped board has no
  `schemaVersion`/legacy `presentation`, has exactly one default presentation,
  and every hold references a declared presentation.
- Workbench local and GitHub-backed catalog tests prove the catalog reads board
  metadata without downloading presentation images.
- iOS board package tests reject legacy keys and validate the complete bundled
  catalog.
- Plan and custom-routine tests assert version fields are absent, decoding is
  strict, and validation behavior is otherwise unchanged.
- Run the Workbench Python/TypeScript tests, HangboardPackages tests, and the
  affected Xcode test targets after migration.
