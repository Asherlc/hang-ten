# VerticalBoard delivery CI follow-up

CI run [36621669794](https://github.com/Asherlc/hang-ten/actions/runs/36621669794)
failed in `InitialWeightSetupUITests.testInlineChoicesDefaultToSkipAndKeepManualDraft`:
the bodyweight switch remained off after a synthesized thumb tap on iOS 26.5.
The retained XCTest attachment showed a switch frame of `(303, 423, 61, 28)`
and an actual tap at `(321.3, 437)`, inside the off-state thumb. The recording
showed an unobstructed native switch. The unchanged test reproduced the same
assertion failure on a workspace-owned iPhone 17 Pro iOS 26.5 simulator.
Its runner was stopped after recording the assertion because result finalization
stalled; that red invocation did not exit normally.

An initial short drag also failed on repetition: XCTest used its default
500-pixel-per-second velocity with a 0.1-second press and no endpoint hold.
The two tests that turn on this switch now drag its thumb from normalized
`(0.3, 0.5)` to `(0.8, 0.5)` with a 0.5-second press, explicit slow velocity,
and a 0.2-second endpoint hold. The existing switch-value assertion, manual-draft
persistence checks, and purchased-workout weight-summary checks remain intact.
Production UI behavior and board geometry are unchanged.

Main's Whetstone migration (`b9d05c9e5`) was integrated while correcting CI.
Both native-model test functions, both sets of generated-manifest ignores,
and all four migrated package entries are retained. The combined delivery lock
is `ec63a290383db0b18f3c2604908325258494f3be90a45464da6bdfaff4b623fa`;
verification passed for 53 models and 122 files. The three VerticalBoard source,
descriptor, and USDZ bytes remain unchanged.

Validation on the combined branch:

- Rebuilt the iOS Simulator app and test targets successfully.
- All three `InitialWeightSetupUITests` and the purchased manual-weight summary
  test ran twice each: eight executions, zero failures.
- Python CAD/model/package suites: 492 passed, 14 skipped, 24 subtests.
- Full merged Swift unit suite: 1,235 tests, three skipped, zero failures.
- Delivery verification: 53 models, 122 files, exact locked identity confirmed.
- Both CI-fix simulators were shut down/deleted, ownership manifests consumed,
  and workspace DerivedData removed; deletion was verified against simulator
  inventory.

Local CI logs and result bundles are retained under
`.context/supreme-zebra-cad-validation/ci-fix-*`.
