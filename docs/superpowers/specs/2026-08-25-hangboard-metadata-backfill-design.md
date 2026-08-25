# Catalog-wide Hangboard Metadata Backfill Design

## Goal

Raise the source-supported metadata quality of every one of the 44 bundled
hangboard packages. Every populated optional hold field must be traceable to
primary manufacturer evidence and the exact canonical hold it describes.
Every reviewed but unsupported value remains absent from `board.json` and has
an evidence-specific reason in the source-audit ledger.

## Current state

The catalog contains 672 hold records. It currently has 373
`sizeMillimeters` values, 36 `depthRangeMillimeters` values, 204
`fingerCapacity` values, zero `handCapacity` values, 43 `gripType` values, and
58 explicit `features` values. All 672 holds structurally declare a `kind`,
but their type assignments have not been revalidated contact by contact against
current primary evidence. Recent work added the schema and editor support
for several of these fields, but did not establish per-contact evidence for the
catalog as a whole.

## Scope and non-goals

The work covers the mandatory physical `kind` plus these optional
physical/semantic fields:

- `kind`

- `sizeMillimeters`
- `depthRangeMillimeters`
- `fingerCapacity`
- `handCapacity`
- `gripType`
- `features`

It does not add user-interface states, default values, inferred measurements,
automated image analysis, or any change to canonical hold geometry. A missing
field continues to mean that the package does not make that claim.

Only a primary manufacturer product page, manual, hold diagram, or official
product view can establish a value. A grouped product claim is insufficient
unless a manual review maps it to an exact physical contact. Sloper diameters,
radii, and similarly non-depth measurements must stay in a source-backed hold
name or remain absent; they must never be written as a depth merely to improve
coverage.

## Evidence ledger

Add a catalog-level machine-readable ledger at
`docs/source-audits/2026-08-25-hangboard-metadata-ledger.json`. It is an audit
document, not a board-package sidecar and is never loaded by the app.

The ledger declares its complete `reviewedBoardIDs` set and has one record per
reviewed mapping or blank-field rule. Each record identifies the board ID,
stable hold ID or explicit set of hold IDs, field name, review date, HTTPS
primary source URL, `manufacturer` source kind, source position/label, and one
of these
outcomes:

- `verified`: records the exact scalar, range, enum, or feature set that must
  appear in `board.json`.
- `unavailable`: documents a source-specific reason that the official material
  does not establish the value for the named contact(s); the JSON field must be
  absent.
- `notApplicable`: documents a semantic non-applicability, such as finger
  capacity for a non-pocket contact; the JSON field must be absent.

Every hold has exactly one `kind` record and it must be `verified`; neither
blank outcome is valid for `kind`.

Rules may cover an explicit list of stable hold IDs only. They may not use
geometry, screen coordinates, wildcards, or inferred hold classes. This makes
the audit reviewable when a board inventory changes.

The existing Markdown source audits remain the human-readable narrative and
source mapping. Each batch extends the relevant audit with its URLs, mapping
table, review date, values added, and any verified unavailable fields.

## Hold-ID visual review

Before a mapping is entered, render the existing canonical hold geometry with
the stable JSON ID overlaid at each hold's geometry-union center. Store all
review-only images under a workspace-owned `.context` directory; do not commit
them and do not use them to generate or alter geometry.

An operator manually compares each labelled render with the official front,
oblique, and numbered manufacturer sources. The audit records the resulting
hold-ID-to-source-position mapping. This is a review aid only: paths remain
the pre-existing, directly authored source of rendering and hit testing.

## Validation

Extend `Tools/HangboardPackages` with a metadata-audit validator and focused
pytest coverage. Given the ledger and discovered board packages, it must:

1. reject unknown or duplicate board/hold/field records;
2. reject absent or malformed HTTPS URLs, a non-`manufacturer` source kind,
   and invalid review dates;
3. require every `verified` value to match the corresponding JSON field
   exactly, including fractional numeric values and both range endpoints;
4. require `unavailable` and `notApplicable` records to keep the JSON field
   absent;
5. for every board in `reviewedBoardIDs`, reject a hold/field that lacks either
   a verified mapping or an explicit blank-field rule, and reject a non-verified
   `kind` record; and
6. print deterministic per-field and per-board before/after coverage totals.

The validator is additive to package-schema validation. Every batch also runs
`rtk scripts/hangboard-packages.sh validate --root Hangboards --final-inventory`
and the focused Python tests. App-level schema changes are out of scope.

## Batches

The rollout is six independently reviewable, pushed batches:

1. Metolius: 10 packages.
2. Tension and So iLL: 7 packages.
3. Beastmaker, Lattice, Moon, Nature, Target10a, and The Hangboard: 7
   packages.
4. Escape, Frictitious, Evolv, and DeWoodstok: 6 packages.
5. Trango: 4 packages.
6. YY Vertical and Zlagboard: 10 packages.

Metolius is the pilot because its official numbered diagrams give the clearest
vertical slice of the mapping workflow. The same validator, review process,
and completion gates apply to every later batch.

## Completion and reporting

A batch is complete only when its audit-ledger tests pass, all of its package
fields are source-mapped or explicitly accounted for, labelled-overlay review
is complete, and final-inventory validation passes.

Each batch is committed and pushed. Its PR description and chat handoff must
state: reviewed packages; official evidence used; metadata fields and values
added; coverage totals before and after; the location of review-only overlays;
and each verified remaining blank with its source-specific rationale. This
reporting requirement applies even when no new runtime field can be safely
added.
