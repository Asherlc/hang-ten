# Task 2 report: closed two-branch suspension contract

## Scope

Implemented only the package/parser contract for `twoBranchCord`. The existing
`singleCord` document and runtime projections remain supported. No board
geometry, board promotion, or `Tools/HangboardModels/tension_flash_board.py`
changes were made.

## Contract

- Added immutable Python passage pairs, cord branches, and two-branch
  suspension types.
- Added the corresponding Swift value types and discriminator enum.
- `twoBranchCord` requires exactly two ordered passages on each side, four
  distinct passage IDs and importer node IDs, exactly two distinct branches,
  one ordered branch pair per side, one invisible common anchor, positive
  branch cord parameters, and canonical poses matching all declared
  positions.
- Passage nodes must resolve to descriptor `body` or `attachment` roles and
  never to `hold` nodes. Descriptor validation permits four attachment nodes
  only for the two-branch discriminator.
- Unknown members, explicit nulls, scalar-kind mismatches, duplicate raw keys,
  order violations, and discriminator/shape mismatches remain fail-closed.

## Test-first record

RED commands:

```text
python3 -m pytest Tools/HangboardPackages/tests/test_model_first_packages.py -q
```

Could not collect: system Python has no `pytest`.

```text
xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 16 Pro' -only-testing:HangTenTests/BoardPackageStoreTests
```

Could not run: CoreSimulatorService was unavailable and Xcode could not write
its global package/cache state. The new Swift test also initially failed at
the expected missing `twoBranchCord` enum case.

GREEN/verification checks:

```text
python3 -m py_compile Tools/HangboardPackages/src/hangboard_packages/board_catalog.py Tools/HangboardPackages/tests/test_model_first_packages.py
swiftc -parse HangTen/Models/TrainingModels.swift HangTen/Models/BoardPackageStore.swift
git diff --check
```

All passed. A dependency-free direct fixture run loaded the valid two-branch
base, loaded the existing single-cord base, and rejected all 52 shared
malformed matrix cases.

## Concerns

Full Python pytest and Swift XCTest remain unexecuted because the environment
has no installed pytest, no network access for dependencies, and no available
simulator service. Existing renderer call sites use compatibility projections
on the new Swift enum; a later renderer task should switch explicitly on the
discriminator before rendering two branches.

## Round 1 repair

The review identified two test-harness defects. The Swift shared fixture
builder now selects `specification["base"]` (defaulting to `model`), so the
valid and malformed two-branch cases actually exercise `twoBranchModel`.
Every matrix entry now carries a non-empty fixture-specific `pythonError`,
and the Python consumer requires and matches that field. A dedicated Python
proof test rejects missing or `.*` expectations, and a dedicated Swift proof
test inspects the generated fixture discriminator; both would fail with the
reviewed implementation.

Round-1 repair checks passed: all 52 matrix cases matched their declared
Python error regexes, Python syntax/JSON validation passed, Swift syntax parse
passed, and `git diff --check` passed. Full pytest/XCTest remain subject to
the environment limitations above.

## Round 2 repair

The rereview's compile and routing findings are repaired. Both branches of
the Swift `BoardModelSuspension.cord` compatibility projection now return a
`BoardModelCord`; the ordinary model-fixture helper no longer references the
parity function's `specification` variable; and discriminator inspection uses
a coding-key enum containing all suspension member names, making conflicting
single/two-branch shapes reach the explicit `shapeMismatch` invalid-package
path. Focused Swift tests cover the cord projection and the expected
`invalidPackage` category for the wrong discriminator.

Round-2 checks: Python fixture-specific matching remained 52/52, Python
syntax/JSON validation, Swift syntax parsing, and `git diff --check` passed.
`swiftc -typecheck` was attempted with a workspace-owned module cache but is
blocked by unrelated pre-existing missing project symbols and unavailable
global SDK/cache state; the prior full XCTest command remains blocked before
compilation by CoreSimulator and offline package resolution.
