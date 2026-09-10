# Task 2 — generic SceneKit model asset and cache

## Current implementation state

`HangTen/Views/BoardModelView.swift` has an uncommitted, test-first Task 2
implementation: `BoardModelKey`, a descriptor-hash-keyed detached decode cache,
package-store asset resolution, exact slash-separated importer path matching,
descriptor/node-set equality, body exclusion from picking, per-view geometry and
material cloning, and retained SceneKit camera, accessibility, on-demand render,
highlight restoration, and `SCNTransaction.flush()` behavior.

`HangTenTests/BoardModelTests.swift` was replaced before production code with
generic controlled-scene tests. They cover exact `Board/…` identities, rejection
of unmatched/materialless geometry, body nonselection, per-view material
independence/restore, camera rebinding, and the existing tap-dependent hit-test
switch.

## RED/GREEN evidence

The focused direct `rtk xcodebuild test` command used the exact owned iPhone 16
/ iOS 26.5 simulator `D693EB9B-26F5-4465-ABCF-51108D36512F`, named `Hang Ten
Paseo shaky-rat Review`. Its UUID was first appended to the pending manifest and
then to the owned manifest before booting.

The first native test result was a real XCTest RED: 3 passed and 2 failed out
of 5. One failure exposed the controlled-scene helper assuming the cloned
source root was the rendered root; the other exposed that `SCNBox` can retain an
implicit material. The test helper now reads the bound cloned hold directly and
explicitly clears `geometry.materials` for the materialless case. The remaining
RED was the intended materialless-mesh rejection: 4 passed, 1 failed.

The final focused result is 5 passed, 0 failed, 0 skipped. It proves exact
descriptor paths, node inventory/material rejection, body nonselection,
independent material clones and restore, camera/scene replacement, and
tap-dependent hit testing.

The separately focused `BoardPackageStoreTests` result is 108 passed, 0 failed,
0 skipped on the same UUID. Both result bundles and the locked resolver records
are retained under `.context/shaky-rat-task2-*`.

The first direct run that used relative workspace cache paths failed before
compilation with missing Amplitude/Sentry products. The local copies were
verified at the four `Package.resolved` commits and the retry used absolute
workspace-local `-clonedSourcePackagesDirPath` and `-packageCachePath` values,
with automatic resolution disabled, resolved-file-only, and package updates
skipped. It resolved all four pins without modifying shared caches or fetching
new revisions.

## Cleanup

`scripts/paseo-resource-cleanup.sh archive` removed the exact Review UUID after
the tests. Both pending and owned manifests are zero lines, the UUID/name is
absent from `simctl`, and the task-local DerivedData, source-package directory,
and package cache are absent. The two durable result bundles remain under
`.context`.
