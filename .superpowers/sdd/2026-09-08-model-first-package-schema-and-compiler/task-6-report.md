# Task 6 implementation report

## Scope and result

Completed the one-time migration of every discovered raster board package to
schema version 2, then removed unversioned/v1 acceptance from the Python and
Swift board-package parsers. The migration is deterministic and idempotent;
logical hold metadata remains on the board while exact raster geometry is now
owned by typed presentation media.

The Task 6 brief's expected count of 53 was stale. Runtime discovery found 61
complete direct-child packages and zero drafts, so all 61 were migrated and
validated. This work does not require repeating a manual migration for each
future board: new packages are authored directly in schema v2, and the shared
converter handled the existing catalog in one pass.

## Inherited work and recovery audit

The recovery session inherited an uncommitted converter, all 61 converted
`board.json` files, the initial Python/Swift v1-removal edits, and focused
converter tests from an interrupted Luna worker. It did not redo the successful
bulk conversion. Instead, it audited that state with package validation,
idempotence checks, a type- and order-sensitive semantic comparison against
`HEAD`, and the complete Python and Swift parser suites.

The two simulators used by earlier interrupted workers were already
archive-cleaned before recovery:

- `D03DCA83-0160-4C20-88DE-BDE236FF3D8F`
- `314F31C6-9876-4578-A5C7-9453B47A896B`

Both were absent and both workspace simulator manifests were empty at recovery
start. No prior XCTest summary was recoverable, so the recovery session ran the
required focused Swift suite against the final state and captured a fresh
result summary.

## Implementation

- Added `Tools/HangboardPackages/scripts/migrate_to_schema_v2.py`.
  - Discovers packages at execution time through the canonical catalog
    discovery API.
  - Rejects duplicate JSON keys, non-raster input, invalid ownership, and
    malformed legacy geometry.
  - Moves each legacy hold path verbatim into its canonical raster
    presentation's `media.holdGeometry`.
  - Converts legacy presentation flags to `isDefault` plus typed
    `derivation`, and gives derived raster presentations their canonical
    source geometry.
  - Removes only the legacy spatial `geometry` and `presentationID` fields
    from logical holds.
  - Treats an already-valid schema-v2 document as an idempotent no-op.
- Converted all 61 discovered `Hangboards/*/board.json` documents to schema v2.
- Made the Python catalog parser require schema v2 and migrated all package
  fixtures and board-specific geometry assertions to typed presentation media.
- Made `BoardPackageStore` require schema v2 and removed its dead v1 document
  adapters and validators.
- Migrated all `BoardPackageStoreTests` fixtures to schema v2 and retained an
  explicit legacy fixture solely to prove rejection.
- Corrected two defects exposed by final runtime validation:
  - Raster validation now validates only the current presentation's geometry
    keys, while the existing package-level check still requires all raster
    presentations collectively to own every logical hold.
  - An omitted logical-hold `equipmentObjectID` still defaults to `primary`,
    but an explicitly null value now fails closed, matching the Python parser.
- Updated the package README with the schema-v2 contract, exact current
  inventory, one-time write command, and idempotent check command.

`TrainingModels.swift` required no additional Task 6 edit: Task 5 had already
landed the logical-hold and typed-media runtime types. Task 6 removed only the
remaining legacy parser boundary.

## TDD and debugging evidence

The converter's original missing-file RED run occurred before the inherited
recovery state and was not reproducible without discarding successful work.
The recovery audit preserved that work and obtained the following fresh RED
and GREEN evidence instead.

Full Python package suite on the inherited half-migrated fixtures:

```text
91 failed, 366 passed
```

The failures were stale v1-shaped shared and board-specific fixtures. After
migrating those fixtures through shared typed-geometry helpers:

```text
457 passed in 39.16s
```

The first focused Swift run built but failed before XCTest connected:

```text
0 passed, 1 infrastructure failure
Early unexpected exit; test host crashed with SIGTRAP before establishing connection
```

The exact `.ips` stack identified `BoardCatalog.packageStore` at
`TrainingModels.swift:1334`. The exact device log supplied the cause:

```text
Board captain-fingerfood.dual is invalid: presentation primary has invalid
holdGeometry for curved-edge-20
```

That board deliberately splits its logical holds across primary and reverse
presentations. The Swift guard had been changed to subset-plus-collective
ownership, but its validation loop still iterated every board hold for every
presentation. The Python reference and an existing Swift scoped-holds test
both iterate only the current presentation's keys. A one-line loop correction
was applied and retested on the same UUID.

The next explicit XCTest summary proved the host bootstrap fix and exposed
only remaining migration mismatches:

```text
84 passed, 6 failed, 0 skipped, total 90
```

The six failures were two fixtures that changed logical hold IDs without
changing typed media geometry, two assertions retaining legacy error wording,
one unknown-key fixture still targeting removed hold-level geometry, and the
explicit-null Swift/Python parity defect. The null case passed in isolation,
then the six migrated focused cases passed together. Final authoritative
summary:

```text
90 passed, 0 failed, 0 skipped, total 90, result Passed
```

## Preservation and catalog evidence

The semantic audit compared every migrated document with its `HEAD` v1 source
without relying on diff line counts. It was type-sensitive and order-sensitive
and verified:

- every non-presentation root field was identical except the new
  `schemaVersion`;
- logical holds remained in the same order with identical metadata after
  removing only `geometry` and `presentationID`;
- presentation IDs, names, aspect ratios, defaults, and asset paths were
  preserved;
- every canonical geometry scalar, path command, piece order, and treatment
  was identical under its new typed owner;
- derived presentations reused exactly their canonical source geometry.

Result:

```text
semantic audit passed: 61 packages, 897 logical holds,
89 original presentations, 7 derived presentations
```

Additional final checks:

```text
packages=61 schema_v2=61 other=0
checked 61 schema-v2 board packages
final inventory: 61 complete packages, 0 drafts
git diff --check: passed
```

The converter `--check` invokes migration on each already-v2 document and
compares the result with the input, so the successful check is also the
catalog-wide idempotence proof. The Python suite includes direct conversion,
idempotence, split-presentation preservation, and unversioned-parser rejection
tests. The Swift suite includes bundled v2 loading and explicit legacy-v1
rejection.

No geometry was detected, inferred, simplified, or regenerated. The converter
only relocated already-reviewed JSON geometry and preserved its exact values
and ordering.

## Simulator ownership and cleanup

- Exact name: `Hang Ten Paseo shaky-rat Review`
- Exact UUID: `8269AAD9-D2EF-4937-AB16-4A826F7B1904`
- Runtime: iPhone 16, iOS 26.5 (23F77)
- The UUID was recorded in both workspace manifests and protected by an exit
  cleanup trap before testing.
- Every build/test destination used the exact UUID; no `booted` destination was
  used.
- First-boot migration completed under a bounded 150-second wait in 2 minutes
  36 seconds. Every XCTest command used a PTY and was polled within 30 seconds.
- Cleanup ran the workspace archive hook, removed only Task 6's exact XCTest
  bundles and `.context/DerivedData`, and then verified:
  - the exact UUID/name is absent from `simctl list devices available`;
  - `.context/paseo-pending-simulators` is empty;
  - `.context/paseo-owned-simulators` is empty;
  - `.context/DerivedData` and both result bundles are absent.

Shared, standard, and unknown simulators were left untouched.

## Commit

Commit message: `feat: migrate board packages to schema v2`.
The immutable commit hash is reported to the controller after commit because a
commit cannot contain its own final hash.

## Reusable skill candidate

The semantic migration pattern is reusable enough to consider adding to the
`migrate-hangboard-to-3d` guidance: discover the live inventory, use a
type/order-sensitive before/after comparator for metadata and path commands,
require an idempotent `--check`, and verify exact parser-count parity. No skill
was changed as part of this implementation task.
