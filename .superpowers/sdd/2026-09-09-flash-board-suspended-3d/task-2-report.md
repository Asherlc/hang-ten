# Task 2 report — suspended model package contract

Implemented the shared descriptor/package suspension contract for one
model-only presentation.

## Contract changes

- Added the optional `attachment` descriptor node role. It is non-logical,
  cannot carry `holdID`, is limited to one node, remains importer-visible and
  material-validated, and never contributes to derived hold frames.
- Added closed `singleCord` suspension parsing in Python and Swift for the
  attachment point, invisible fixed anchor offset, cord parameters, and
  position-keyed canonical poses.
- Validated finite vectors, normalized quaternions (1e-6 tolerance), positive
  cord values, inclusive attachment bounds, exact position/pose keys, body or
  attachment node binding, fixed unposed anchor evaluation, and endpoint/rest
  length feasibility.
- Preserved model-only isolation: raster siblings, multiple model
  presentations, baked/unknown descriptor roles, unknown suspension fields,
  and duplicate raw JSON members are rejected.
- Extended the shared fixture matrix and Python/Swift consumers with the
  required malformed suspension and attachment cases.

## Verification

Passed:

- Python byte compilation for all changed Python modules and tests.
- Swift syntax parsing for `TrainingModels.swift` and `BoardPackageStore.swift`.
- Standard-library Python harness: valid shared suspended package loads; all
  malformed matrix cases reject; duplicate canonical-pose JSON key rejects;
  descriptor/compiler attachment checks pass.
- `git diff --check`.

Round 1 review fix: extended the shared parity matrix with independent
`nonpositive-rest-length` and `baked-anchor-role` fixtures (alongside the
existing radius and rope-role cases), and updated the Swift matrix-name
assertion. The direct Python mutation harness now rejects all 27 ordinary
malformed cases; Swift syntax parsing and Python byte compilation remain
green.

Unavailable in this environment:

- Focused pytest: `pytest` is not installed; a disposable venv install was
  attempted but package download failed because DNS/network access is
  unavailable. The venv was removed.
- Focused `xcodebuild test`: simulator services were unavailable and Swift
  package resolution could not clone the network dependencies. Disposable
  derived-data/source-package directories were removed.
