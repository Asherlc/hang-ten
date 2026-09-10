# Task 3 report — deterministic two-branch suspended-cord solver

## Result

Implemented the pure two-branch presentation solver in
`HangTen/Views/SuspendedBoardPresentation.swift` and added focused policy
tests in `HangTenTests/SuspendedBoardPresentationTests.swift`.

The new overload transforms all four passage points by the canonical pose,
keeps one fixed world-space anchor, and returns two ordered branch solutions.
Each branch is assembled as:

```text
anchor -> passage[0] -> passage[1] -> anchor
```

The modeled passage-to-passage span is retained as the exact straight
interior route. The declared branch length is reserved for that route first,
then the remaining free length is distributed proportionally to the two
anchor-to-passage endpoint separations before invoking the existing fixed
32-sample catenary solver. The solver rejects invalid/nonfinite inputs,
impossible route lengths, zero-length passage spans, unsolved catenaries, and
nonfinite/wrong-length results. It does not certify mesh clearance; the
returned ordered samples, tube radius, and radius-plus-clearance threshold are
the downstream probe contract.

The existing single-cord overload and its behavior remain intact. The only
solver-wide change is naming the already-required `1e-5 m` taut tolerance as a
shared constant.

## Test-first evidence

The new tests were added before the implementation and the requested focused
test command was run. The test invocation was blocked before compilation by
the environment: CoreSimulatorService was unavailable and Xcode's global
Swift/SwiftPM caches were not writable. A workspace-owned `swiftc -parse`
check passed. A workspace-owned typecheck reached unrelated pre-existing
model dependency errors (`SemanticHoldMappingDefinition`, `BoardPackageStore`,
and color extensions); it reported no error in the new solver section before
those missing-project-context errors.

Focused command:

```bash
xcodebuild test -project HangTen.xcodeproj -scheme HangTen \
  -destination 'platform=iOS Simulator,name=iPhone 16 Pro' \
  -only-testing:HangTenTests/SuspendedBoardPresentationTests
```

No geometry, board package, or current dirty generator files were changed.

## Round-1 review remediation

The assembled branch now receives a closed-path self-intersection validation
after concatenation. It checks crossings and non-adjacent endpoint contacts
across both free catenaries and the exact interior passage route, while
allowing the intentional first/last shared anchor and adjacent passage joins.
Added regression coverage forces an interior-route/free-span crossing and
expects `.selfIntersection`, plus a two-branch exact-taut case that verifies
both free spans are straight, fixed 32-sample segments and the composite
route length is exact.

The focused XCTest was rerun after the remediation but remains blocked before
compilation by unavailable CoreSimulatorService and inaccessible global
Swift/SwiftPM caches. `swiftc -parse` and `git diff --check` pass.

An owned standalone Swift probe executed both new regression scenarios after
the fix: exact-taut branches completed with 32-sample straight free spans,
and the interior-route/free-span crossing was rejected as
`.selfIntersection`. The probe and its compiler cache were removed after
execution.
