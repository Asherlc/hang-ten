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
