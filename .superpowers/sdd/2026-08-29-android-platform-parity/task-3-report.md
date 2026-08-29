# Task 3 — Android BLE force sensors and measured recording

## Delivered

- Ported the reviewed Motherboard parser, signed 24-bit framing, bounded receive
  buffer, calibration interpolation, polarity-before-tare conversion, stream
  commands, software tare, hysteretic threshold/debounce, interval merge, and
  20,000-sample persistence cap.
- Added reviewed Progressor and PitchSix profile contracts, command payloads,
  advertisement matching, and frame decoding.
- Added Android BLE scan/GATT/notification transport behind a deterministic
  fake; runtime Bluetooth permissions are requested only from the explicit
  Settings **Connect sensor** action.
- Added a Settings profile selector, live kgf meter, tare control, workout
  measurement handoff, per-session DataStore round-trip persistence, and a
  backward-compatible history decoder.

## Automated evidence

- RED: initial protocol/controller tests were compiled and exercised against
  absent adapters, then exposed the Android-runtime `List.removeLast` ABI issue.
  The recorder now uses `removeAt(lastIndex)`.
- GREEN: `:app:testDebugUnitTest --tests 'com.hangten.android.sensors.*'
  --tests 'com.hangten.android.workout.SessionHistoryRepositoryTest'
  --rerun-tasks` — **BUILD SUCCESSFUL**, 14 tests.
- Full local verification: `:app:testDebugUnitTest :app:lintDebug
  :app:assembleDebug` and then `:app:lintDebug :app:assembleDebug` —
  **BUILD SUCCESSFUL**.

## Emulator and physical hardware

The deterministic fake transport is covered by the focused unit/controller
suite. No emulator system image or AVD was already owned by this workspace;
the temporary owned SDK contained API 36 platform/build tools only. To avoid
using a shared AVD or asserting an unrun device test, no emulator BLE claim is
made. This is a required remaining release validation gate.

Before release, on a physical Motherboard, Tindeq Progressor, and PitchSix:

1. Tap Connect sensor and verify Android's Bluetooth prompt occurs only then.
2. Scan/connect each device, verify the selected profile and live kgf meter.
3. Motherboard: verify all calibration rows, `C`, `S30`/`Stream:30`, tare, and
   raw/sample/battery values against a captured notification trace.
4. Progressor/PitchSix: verify start, tare, stop, values/unit conversion, and
   reconnect/disconnect behavior against each device.
5. Complete a workout and inspect local history for samples, thresholds,
   intervals, profile, and 20,000-sample truncation marker.

## Owned resource cleanup

The temporary SDK/cache is named
`.context/android-sdk-bitter-scorpion-0o9ylkoo`; it is deleted and checked for
absence before this task is handed off.

## Review-remediation evidence

- GATT connection now suspends through service discovery; descriptor enablement
  suspends through its callback. Discovery, descriptor, and setup disconnect
  errors reach the controller before subscribe/start can proceed.
- The controller retains requested and resolved profiles separately, delivers
  every measurement through a non-conflated channel, and creates monotonic
  generic-profile sample IDs. Workout recording accepts samples only in the
  active session and emits unmeasured records for untouched plan steps.
- Re-run: `:app:testDebugUnitTest :app:lintDebug :app:assembleDebug` — BUILD
  SUCCESSFUL. `:app:compileDebugAndroidTestKotlin` also passed.
- Added `SensorSettingsUiTest` for the deterministic fake Settings connect,
  meter, and tare flow. It was compiled but could not be executed because the
  uniquely-owned AVD could not be created. `sdkmanager --list` advertises
  `system-images;android-36;google_apis;arm64-v8a`, but repeated install calls
  left no image package under the owned SDK and `avdmanager create avd` returned
`Package path is not valid` with valid paths `null`. No shared/corrupt AVD was
used. This remains an infrastructure release gate, not a passed emulator run.

### Provisioning diagnosis

A fresh owned root, `.context/android-sdk-bitter-scorpion-0o9ylkoo-retry`, was
used for a single explicit install attempt. The runner terminated the initial
command-line-tools download after roughly 28 seconds, leaving a 97 MB partial
archive. An HTTP resume produced a 155,049,280-byte archive, but `unzip -t`
still reported `At least one error was detected`. Thus `sdkmanager` and
`avdmanager` never ran from a verified command-line-tools package; this is an
execution-environment download interruption, not an emulator result. The exact
retry root is deleted after recording this evidence. The instrumentation test
compiles, but its connected-device execution must be rerun in an environment
where the owned SDK archive download can complete uninterrupted.

The persistent-PTY recovery confirmed that diagnosis: the first download
stopped at 143,224,832 bytes, then `curl --continue-at -` completed a valid
153,607,488-byte archive (`unzip -t`: no errors). Command-line tools and
licenses installed successfully. One sequential `sdkmanager` install of only
the platform tools, emulator, build tools, API 36 platform, and API 36 ARM64
image was again terminated by the runner after about 28 seconds. Inspection
found only `emulator/.installer`, no `system-images/**/package.xml`; therefore
no AVD was created. All three exact owned SDK roots were then deleted.

### Final transport hardening

- Streaming disconnects now move the controller to `Disconnected` with a
  visible error. Notifications use an explicit bounded queue: queue overflow
  is surfaced as an error rather than silently dropping a sample. GATT writes
  now suspend through `onCharacteristicWrite` and surface write/disconnect
  failures to Start, Tare, and Stop callers.
- Focused sensor tests, full `:app:testDebugUnitTest`, `:app:lintDebug`, and
  `:app:assembleDebug` were rerun using the minimal owned SDK and finished
  **BUILD SUCCESSFUL**. The exact minimal SDK root was removed after the run.
