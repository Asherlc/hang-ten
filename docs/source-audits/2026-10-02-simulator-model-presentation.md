# Simulator board presentation

PR 524 CI run [37023425282](https://github.com/Asherlc/hang-ten/actions/runs/37023425282)
failed five Batch05 board cases: three blank bodies and two stale rendered orbits.
The retained screenshots and existing framebuffer investigations locate observed
failures beyond model acquisition and projected camera state. They do not establish
an internal framework defect.

Interactive Simulator maps now select asynchronous drawable presentation through
Apple's public [CAMetalLayer.presentsWithTransaction](https://developer.apple.com/documentation/quartzcore/cametallayer/presentswithtransaction)
property. This avoids requiring a worker-thread Core Animation transaction to
commit before the drawable appears. The code is compiled only for Simulator and
only attached to interactive maps. It searches public layer ancestry for one
Metal layer matching the map's window coordinates, rejects ambiguity, and bounds
initial discovery to 120 attempts. A viewport change or restored transaction mode
restarts discovery. Pending work is cancelled when the view leaves its window.
No private class names, debugger hooks, global transaction commits, camera changes,
geometry edits, or acceptance-test changes are involved.

## Local validation

Xcode 27.0 / 27A266a, iOS 26.5 / 23F77, iPhone 17 Pro.
An unchanged local Evo/Pro baseline passed two tests; the fault is intermittent.
The first asynchronous candidate passed all six portrait sequences, but Forge
and Natural went blank in landscape. Its logs confirmed six initial layer matches.
The revised candidate reconfigures after rotation: all six tests passed with zero
failures in 294.478 seconds, and xcodebuild finalized with exit zero. Its logs
record asynchronous presentation at portrait, landscape, and return-to-portrait
viewports for every board. This is successful local validation of a workaround,
not proof of the Simulator driver's internal cause or remote CI success.

The final build command was:

```sh
CI=true xcodebuild -project HangTen.xcodeproj -scheme HangTen \
  -configuration Debug \
  -destination 'platform=iOS Simulator,id=DBBB66CE-D52C-419B-9CAE-12995C28051D' \
  -parallel-testing-enabled NO -maximum-parallel-testing-workers 1 \
  -only-testing:HangTenUITests/Batch05BoardModelInteractionUITests \
  -derivedDataPath .context/DerivedData -showBuildTimingSummary \
  -xcconfig .context/ci-fix/review.xcconfig COMPILER_INDEX_STORE_ENABLE=NO \
  CODE_SIGNING_ALLOWED=YES CODE_SIGNING_REQUIRED=YES CODE_SIGN_IDENTITY=- \
  build-for-testing
```

The same arguments with `test-without-building` and
`-resultBundlePath .context/ci-fix/supreme-zebra-metal-resize-run.xcresult`
ran the original physical selection, rendered highlight/orbit, physical retap
preservation, and rendered landscape assertions. All six final landscape screenshots
were visually reviewed: DoorMount, Evo, Forge, Megalith, Natural, and Pro render
visible boards with the selected hold highlighted. Logs, screenshots, diagnostics,
and all three result bundles remain under workspace-owned `.context/ci-fix`.

All three exact workspace-owned simulators were deleted and checked against the
final inventory; ownership manifests were consumed and `.context/DerivedData` was
removed. The first failing candidate's stalled post-test diagnostic collector was
stopped only after all six tests completed, preserving its exit-65 result.
Device rendering uses the existing implementation; no physical-device behavior
claim follows from this Simulator validation. Required remote checks remain the
final acceptance gate.
