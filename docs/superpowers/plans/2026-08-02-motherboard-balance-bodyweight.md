# Motherboard Balance and Bodyweight Calibration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add left/right Motherboard load proportions, live percentage-of-bodyweight feedback, and a tare/bodyweight setup sequence before sensor-backed workouts.

**Architecture:** Keep calibrated raw measurements and derived side metrics in the Motherboard model, and keep the timed bodyweight capture lifecycle in the existing `@MainActor` Bluetooth service. Add a focused SwiftUI preparation sheet that sequences the service’s tare and bodyweight operations before `WorkoutView` starts its existing timer, while the meter and saved summary consume optional derived values.

**Tech Stack:** Swift 5, SwiftUI, CoreBluetooth, Combine, XCTest, Xcode iOS Simulator.

## Global Constraints

- Preserve the existing CoreBluetooth NUS transport, calibration parsing, stream acknowledgement, reconnect, timeout, recorder, history, and sensor-optional workout behavior.
- Use the device-specific side grouping `left = calibrated channels 0 + 2`, `right = calibrated channels 1 + 3`, isolated in one model helper.
- Use 15 unloaded samples for tare and a default five-second bodyweight capture; bodyweight duration is user-configurable from 3–10 seconds in one-second steps.
- Existing persisted `WorkoutSessionRecord` values must decode when the new optional bodyweight field is absent.
- DEBUG autostart review routes must bypass the preparation sheet so existing simulator review flows still reach the workout surface.
- DEBUG simulation must model the full sensor-backed flow without hardware: unloaded tare samples, a stable five-second jug hang for bodyweight capture, and changing non-equal left/right loads during the workout.
- Add tests before production changes and observe each new test fail for the intended missing behavior.

---

### Task 1: Measurement distribution and settings model

**Files:**
- Modify: `HangTen/Models/MotherboardModels.swift`
- Modify: `HangTenTests/MotherboardModelsTests.swift`
- Modify: `HangTenTests/AppStoreTests.swift` only if a persisted bodyweight fixture needs compatibility coverage

**Interfaces:**
- `MotherboardMeasurement.leftLoadKGF`, `.rightLoadKGF`, `.leftShare`, `.rightShare`, and `bodyweightPercentage(for:)` are computed, non-persisted metrics.
- `MotherboardSettingsStore.bodyweightCaptureDuration` is a persisted `TimeInterval` normalized to `3...10`, default `5`.
- `WorkoutSessionRecord.bodyweightKGF` is an optional Codable field with a default of `nil`.

- [ ] **Step 1: Write failing model/settings tests**

Add tests proving that sensor loads `[2, 1, 3, 4]` produce left `5`, right `5`, and equal shares; that `[3, 1, 1, 5]` produces 40/60 shares; that a 20 kgf bodyweight yields a 50% reading for a 10 kgf aggregate; and that bodyweight duration defaults to 5, clamps invalid stored values, persists edits, and survives an optional-field-free session record decode.

- [ ] **Step 2: Run the focused tests and verify RED**

Run:

```sh
rtk proxy xcodebuild test -quiet -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,id=5BD0C30F-C006-43F1-9EFC-4B47B93EA488' -derivedDataPath .context/DerivedData-bodyweight-red -parallel-testing-enabled NO -maximum-parallel-testing-workers 1 -only-testing:HangTenTests/MotherboardModelsTests -only-testing:HangTenTests/AppStoreTests
```

Expected: the new symbols and assertions fail because distribution metrics, duration persistence, and the optional record field do not exist.

- [ ] **Step 3: Implement the minimal model/settings behavior**

Add the side-index helper and finite/zero-safe share calculations, add `bodyweightCaptureDuration` with the existing UserDefaults pattern, and add the optional session field without changing existing aggregate decoding.

- [ ] **Step 4: Run the focused tests and verify GREEN**

Rerun the command from Step 2; expected result is PASS with the existing model/store tests still green.

- [ ] **Step 5: Commit**

```sh
rtk git add HangTen/Models/MotherboardModels.swift HangTenTests/MotherboardModelsTests.swift HangTenTests/AppStoreTests.swift
rtk git commit -m "feat: model Motherboard balance and bodyweight"
```

### Task 2: Timed bodyweight capture in the Bluetooth service

**Files:**
- Modify: `HangTen/Models/MotherboardBluetoothService.swift`
- Modify: `HangTenTests/MotherboardBluetoothServiceTests.swift`

**Interfaces:**
- `MotherboardBluetoothService.bodyweightKGF: Double?` publishes the completed baseline.
- `MotherboardBluetoothService.isMeasuringBodyweight: Bool`, `.bodyweightMeasurementStartedAt: Date?`, and `.bodyweightSampleCount: Int` publish capture state.
- `beginBodyweightMeasurement(duration:) -> Bool` starts a timed average only while streaming; cleanup/session reset cancels it.

- [ ] **Step 1: Write failing service tests**

Add `@MainActor` tests that start the fake service in streaming state, call `beginBodyweightMeasurement(duration: 0.05)`, emit measurements with aggregate loads 8, 10, and 12, await completion, and assert a 10 kgf average plus cleared active state. Add tests for rejecting capture while disconnected, cancellation on disconnect, and a second capture replacing the prior baseline.

- [ ] **Step 2: Run focused service tests and verify RED**

Run the existing explicit-simulator command restricted to `HangTenTests/MotherboardBluetoothServiceTests`; expected failure is missing capture API/state.

- [ ] **Step 3: Implement the minimal timed sampler**

Collect finite aggregate samples from the existing raw-packet path while `isMeasuringBodyweight` is true, schedule a cancellable `Task` for the requested duration, average samples on completion, publish the baseline, and clear the task/samples in all cleanup paths. Keep the existing tare sampler independent.

- [ ] **Step 4: Run focused service tests and verify GREEN**

Rerun the restricted service suite; expected result is PASS with all existing connection/tare tests green.

- [ ] **Step 5: Commit**

```sh
rtk git add HangTen/Models/MotherboardBluetoothService.swift HangTenTests/MotherboardBluetoothServiceTests.swift
rtk git commit -m "feat: capture Motherboard bodyweight baseline"
```

### Task 3: Preparation state and workout integration

**Files:**
- Create: `HangTen/Models/MotherboardWorkoutPreparation.swift`
- Create: `HangTen/Views/MotherboardWorkoutPreparationView.swift`
- Modify: `HangTen/Views/RootView.swift`
- Modify: `HangTen.xcodeproj/project.pbxproj`
- Modify: `HangTenTests/MotherboardWorkoutRecorderTests.swift` or add `HangTenTests/MotherboardWorkoutPreparationTests.swift`

**Interfaces:**
- `MotherboardWorkoutPreparationStep` represents `.tare`, `.bodyweight`, and `.ready` transitions.
- The preparation view receives an observed `MotherboardBluetoothService`, force unit, duration, `onComplete`, and `onSkip` closures.
- `WorkoutView` presents preparation only for an initial start while the service is streaming; resume, sensorless workouts, skip, and DEBUG autostart retain current behavior.

- [ ] **Step 1: Write failing preparation transition tests**

Test that a preparation state advances tare → bodyweight → ready only after the service reports completion, that skip exits without a baseline, and that an initial sensor-backed start is gated while a resumed workout is not. Keep this test independent of SwiftUI rendering by exercising the small preparation state type and its transitions.

- [ ] **Step 2: Run the focused preparation tests and verify RED**

Run the new preparation test target restriction; expected failure is the absent state type/transitions.

- [ ] **Step 3: Implement the preparation state and sheet**

Build a compact sheet with explicit “Tare board”, automatic bodyweight capture instructions (“Hang relaxed on the jugs”), a duration/countdown/progress indicator, captured bodyweight confirmation, retry/skip actions, and completion. Wire `WorkoutView` so the routine’s three-second countdown starts only from `onComplete`; pass the optional bodyweight value into the meter and saved session.

- [ ] **Step 4: Preserve DEBUG and sensorless routes**

Update the DEBUG autostart branch to mark setup complete before calling `toggleRunning`, and ensure a non-streaming service still starts the routine directly. Add the new source file to the Xcode project and keep the existing simulator transport route unchanged.

- [ ] **Step 5: Run focused preparation/integration tests and verify GREEN**

Run the focused tests plus a Debug build using the dedicated simulator; expected result is PASS and the app compiles with the new sheet.

- [ ] **Step 6: Commit**

```sh
rtk git add HangTen/Models/MotherboardWorkoutPreparation.swift HangTen/Views/MotherboardWorkoutPreparationView.swift HangTen/Views/RootView.swift HangTen.xcodeproj/project.pbxproj HangTenTests/MotherboardWorkoutPreparationTests.swift
rtk git commit -m "feat: gate workouts on sensor calibration"
```

### Task 4: Live balance and bodyweight UI/settings/history

**Files:**
- Modify: `HangTen/Views/MotherboardViews.swift`
- Modify: `HangTen/Views/WorkoutSummaryView.swift`
- Modify: `HangTen/Models/SimulatedMotherboardTransport.swift`
- Modify: `HangTenTests/WorkoutSummaryTests.swift`
- Modify: `HangTenTests/SimulatedMotherboardTransportTests.swift`

**Interfaces:**
- `MotherboardMeterView` accepts optional bodyweight and renders side shares plus a bodyweight percentage line without hiding current/peak force.
- `MotherboardSettingsView` exposes bodyweight capture duration in seconds and preserves the existing threshold/force/tare controls.
- Saved summaries show the optional captured bodyweight while read-only history remains non-mutating.
- The DEBUG transport exposes deterministic phase-aware samples so the preparation flow and live workout meter visibly exercise tare, bodyweight, balance, and percentage feedback in the simulator.

- [ ] **Step 1: Write failing UI-facing/model tests**

Add tests for summary bodyweight text data and simulator phase samples: unloaded tare frames, stable bodyweight-hang frames, and non-equal left/right workout frames. Keep tests on pure model values where SwiftUI inspection is not already present.

- [ ] **Step 2: Run focused tests and verify RED**

Run the summary and simulator test restrictions; expected failure is absent bodyweight display data/split fixture behavior.

- [ ] **Step 3: Implement the meter/settings/summary changes**

Render left/right percentages as a balanced split, show “% bodyweight” only when a valid baseline exists, add the duration picker/slider and copy, include the captured baseline in read-only summary detail, and make the DEBUG stream cycle through unloaded, bodyweight-hang, and dynamic workout samples.

- [ ] **Step 4: Run focused tests and verify GREEN**

Rerun the focused restrictions and confirm all pass.

- [ ] **Step 5: Commit**

```sh
rtk git add HangTen/Views/MotherboardViews.swift HangTen/Views/WorkoutSummaryView.swift HangTen/Models/SimulatedMotherboardTransport.swift HangTenTests/WorkoutSummaryTests.swift HangTenTests/SimulatedMotherboardTransportTests.swift
rtk git commit -m "feat: show Motherboard balance and bodyweight"
```

### Task 5: Granular Motherboard sample persistence

**Files:**
- Modify: `HangTen/Models/MotherboardModels.swift`
- Modify: `HangTen/Models/MotherboardProtocol.swift`
- Modify: `HangTen/Views/RootView.swift`
- Modify: `HangTen/Views/WorkoutSummaryView.swift`
- Modify: `HangTenTests/MotherboardModelsTests.swift`
- Modify: `HangTenTests/MotherboardProtocolTests.swift`
- Modify: `HangTenTests/AppStoreTests.swift` only if the persisted session fixture needs compatibility coverage

**Interfaces:**
- `MotherboardMeasurement` retains raw ADC channel values alongside calibrated sensor loads, with backward-compatible Codable defaults.
- `WorkoutSessionRecord.motherboardMeasurements` stores every streamed measurement received during the running routine, including rest intervals, with missing-field decode fallback for existing records.

- [ ] **Step 1: Write failing persistence and raw-packet tests**

Add tests proving protocol decoding carries all raw ADC values into the calibrated measurement, measurement/session Codable round-trips retain timestamps, battery, raw channels, sensor loads, and aggregate values, and legacy session JSON without the new sample field still decodes.

- [ ] **Step 2: Run focused tests and verify RED**

Run the model/protocol/AppStore restrictions; expected failure is absent raw-channel/session sample fields.

- [ ] **Step 3: Implement granular capture and persistence**

Add raw ADC values to `MotherboardMeasurement` with decode defaults, pass packet ADCs through `MotherboardProtocol.decode`, append each streamed measurement from `WorkoutView` while its actual routine timer is running (including rest intervals), and persist the captured array in `WorkoutSessionRecord`. Keep threshold-based recorder behavior unchanged and use the existing notification timestamps as the source of truth.

- [ ] **Step 4: Add a read-only summary data-count cue**

Show the optional sample count in the session summary when granular data exists without making history mutable or exposing a misleading count for old records.

- [ ] **Step 5: Run focused tests and verify GREEN**

Rerun model/protocol/summary/AppStore restrictions and confirm all pass.

- [ ] **Step 6: Commit**

```sh
rtk git add HangTen/Models/MotherboardModels.swift HangTen/Models/MotherboardProtocol.swift HangTen/Views/RootView.swift HangTen/Views/WorkoutSummaryView.swift HangTenTests/MotherboardModelsTests.swift HangTenTests/MotherboardProtocolTests.swift HangTenTests/AppStoreTests.swift
rtk git commit -m "feat: persist granular Motherboard samples"
```

### Task 6: Full verification and PR update

**Files:**
- Modify: `README.md` or `docs/IOS_RUNTIME_SERVICES.md` only if the new setup/review route needs a user-facing note

- [ ] **Step 1: Run the complete XCTest suite**

```sh
rtk proxy timeout 180s xcodebuild test -quiet -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,id=5BD0C30F-C006-43F1-9EFC-4B47B93EA488' -derivedDataPath .context/DerivedData-bodyweight-final -parallel-testing-enabled NO -maximum-parallel-testing-workers 1
```

Expected: all tests pass with zero failures/skips.

- [ ] **Step 2: Build the Debug simulator app**

```sh
rtk proxy timeout 180s xcodebuild build -quiet -project HangTen.xcodeproj -scheme HangTen -sdk iphonesimulator -configuration Debug -destination 'platform=iOS Simulator,id=5BD0C30F-C006-43F1-9EFC-4B47B93EA488' -derivedDataPath .context/DerivedData-bodyweight-final-build CODE_SIGNING_ALLOWED=NO
```

Expected: `BUILD SUCCEEDED`.

- [ ] **Step 3: Run static checks and review the diff**

Run `rtk git diff --check origin/main...HEAD`, inspect `rtk git diff --stat origin/main...HEAD`, confirm the PR branch is clean, and verify no physical-hardware claim is made without a real Motherboard.

- [ ] **Step 4: Commit verification notes and push**

Update the implementation report with the fresh test/build results, commit any intentional documentation change, push the branch, and update the existing draft PR body/title if the final scope needs it.
