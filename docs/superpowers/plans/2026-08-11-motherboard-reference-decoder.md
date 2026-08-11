# Motherboard Reference Decoder Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Match Hang Ten's internal Motherboard force decoder to the public `hangtime-grip-connect` interpretation while retaining the existing two-side balance interface.

**Architecture:** Keep the parser's four raw 24-bit values and the four-channel calibration/tare lifecycle. The decoder computes all four signed calibrated slots, but only 0–2 contribute to force: 0 is left, 1 is inverted center, and 2 is inverted right. The existing balance view splits center load equally between sides; channel 3 remains diagnostic-only.

**Tech Stack:** Swift 5, XCTest, Xcode iOS Simulator.

## Global Constraints

- Follow the reference behavior exactly: use only force channels `0...2`; invert channel 1 and channel 2 before tare; exclude channel 3 from force and aggregate calculations.
- Preserve all raw ADC values, four-sensor calibration validation, and four-element tare arrays.
- Preserve finite-value protection and the non-negative aggregate clamp.
- Keep the current two-side UI: `displayedLeft = left + center / 2` and `displayedRight = right + center / 2`, applying the existing non-negative treatment per source channel.
- Document this as an unverified third-party compatibility choice, not manufacturer-verified wiring.
- Add tests before production changes and observe each new test fail for the intended missing behavior.
- Use `.context/DerivedData-motherboard-reference-decoder` for derived build data.

---

## File Structure

- `HangTen/Models/MotherboardProtocol.swift` — converts raw ADC data to signed calibrated loads and aggregate force.
- `HangTen/Models/MotherboardModels.swift` — derives the unchanged left/right UI properties.
- `HangTenTests/MotherboardProtocolTests.swift` — covers selection, polarity, tare ordering, and channel-3 exclusion.
- `HangTenTests/MotherboardModelsTests.swift` — covers neutral center distribution and channel-3 balance exclusion.
- `docs/IOS_RUNTIME_SERVICES.md` — records the deliberate compatibility rule and its limitation.

### Task 1: Reference-compatible protocol decoder

**Files:**
- Modify: `HangTen/Models/MotherboardProtocol.swift:174-195`
- Modify: `HangTenTests/MotherboardProtocolTests.swift:37-62`

**Interfaces:**
- Consumes: `MotherboardRawPacket.adcValues: [Int32]`, `MotherboardCalibration.massKGF(sensor:adc:) -> Double?`, and `tareKGF: [Double]`.
- Produces: four preserved `rawADCValues`, four signed/tare-adjusted `sensorLoadsKGF`, and `aggregateLoadKGF` computed from indexes `0...2`.
- Preserves: `MotherboardProtocol.decode(_:timestamp:calibration:tareKGF:)` and all four-sensor validation in `MotherboardBluetoothService`.

- [ ] **Step 1: Write the failing protocol tests**

Replace `testCalibrationInterpolatesAndSubtractsPerSensorTare` with tests using a shared `linearCalibration()` fixture (for each sensor, `0 -> 0 kgf`, `100 -> 10 kgf`).

```swift
func testDecodeUsesReferencePolarityBeforeApplyingPerSensorTare() {
    let result = MotherboardProtocol.decode(
        MotherboardRawPacket(sampleNumber: 1, batteryValue: 2, adcValues: [90, 60, 70, 100]),
        timestamp: Date(timeIntervalSince1970: 1),
        calibration: linearCalibration(),
        tareKGF: [1, -8, -9, 4]
    )

    XCTAssertEqual(result.rawADCValues, [90, 60, 70, 100])
    XCTAssertEqual(result.sensorLoadsKGF, [8, 2, 2, 6])
    XCTAssertEqual(result.aggregateLoadKGF, 12, accuracy: 0.0001)
}

func testDecodeExcludesFourthChannelFromAggregateForce() {
    let baseline = MotherboardProtocol.decode(
        MotherboardRawPacket(sampleNumber: 1, batteryValue: 2, adcValues: [90, 60, 70, 0]),
        timestamp: Date(timeIntervalSince1970: 1),
        calibration: linearCalibration(),
        tareKGF: [1, -8, -9, 0]
    )
    let fourthChannelChanged = MotherboardProtocol.decode(
        MotherboardRawPacket(sampleNumber: 2, batteryValue: 2, adcValues: [90, 60, 70, 100]),
        timestamp: Date(timeIntervalSince1970: 2),
        calibration: linearCalibration(),
        tareKGF: [1, -8, -9, 0]
    )

    XCTAssertEqual(baseline.aggregateLoadKGF, 12, accuracy: 0.0001)
    XCTAssertEqual(fourthChannelChanged.aggregateLoadKGF, 12, accuracy: 0.0001)
    XCTAssertNotEqual(baseline.sensorLoadsKGF[3], fourthChannelChanged.sensorLoadsKGF[3])
}
```

Expected RED reason: the old decoder keeps channels 1 and 2 positive and includes channel 3 in the aggregate.

- [ ] **Step 2: Run the protocol test target and verify RED**

Run:

```sh
xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 17 Pro' -derivedDataPath .context/DerivedData-motherboard-reference-decoder -only-testing:HangTenTests/MotherboardProtocolTests
```

Expected: the two new assertions fail, while existing protocol tests compile.

- [ ] **Step 3: Write the minimal decoder implementation**

In `MotherboardProtocol`, add the reference polarity constants and apply the selected polarity before per-sensor tare. Calibrate and tare all four values, but aggregate only the first three.

```swift
private static let channelPolarities: [Double] = [1, -1, -1, 1]
private static let forceChannelCount = 3

let sensorLoadsKGF = (0..<4).map { sensor in
    let adc = packet.adcValues.indices.contains(sensor) ? packet.adcValues[sensor] : 0
    let tare = tareKGF.indices.contains(sensor) ? tareKGF[sensor] : 0
    let calibrated = finiteLoad(calibration.massKGF(sensor: sensor, adc: adc) ?? 0)
    let polarity = channelPolarities.indices.contains(sensor) ? channelPolarities[sensor] : 1
    return finiteLoad(finiteLoad(calibrated * polarity) - finiteLoad(tare))
}
let aggregateLoadKGF = sensorLoadsKGF.prefix(forceChannelCount).reduce(0) { total, load in
    finiteLoad(total + load)
}
```

Do not change raw-packet parsing, calibration interpolation, `hasCompleteCalibration`, or the four-element tare collection.

- [ ] **Step 4: Run the protocol test target and verify GREEN**

Rerun Step 2. Expected: all `MotherboardProtocolTests` pass, including finite-value and JSON tests.

- [ ] **Step 5: Commit**

```sh
git add HangTen/Models/MotherboardProtocol.swift HangTenTests/MotherboardProtocolTests.swift
git commit -m "fix: match motherboard reference force decoding"
```

### Task 2: Derive balance from reference zones

**Files:**
- Modify: `HangTen/Models/MotherboardModels.swift:66-106`
- Modify: `HangTenTests/MotherboardModelsTests.swift:28-67`
- Modify: `docs/IOS_RUNTIME_SERVICES.md:10-34`

**Interfaces:**
- Consumes: indexes 0, 1, 2, and 3 of `sensorLoadsKGF` as reference left, center, right, and diagnostic-only loads.
- Produces: unchanged `leftLoadKGF`, `rightLoadKGF`, `leftShare`, and `rightShare`.
- Preserves: all `MotherboardViews` call sites and persistence schema; no center-zone UI is introduced.

- [ ] **Step 1: Write the failing balance tests**

Replace the current interleaved-grouping test with these tests and update the non-finite test to the new zone order:

```swift
func testMeasurementSplitsCenterLoadNeutrallyAcrossDisplayedSides() {
    let measurement = measurement(sensorLoads: [3, 4, 5, 100], aggregate: 12)

    XCTAssertEqual(measurement.leftLoadKGF, 5, accuracy: 0.0001)
    XCTAssertEqual(measurement.rightLoadKGF, 7, accuracy: 0.0001)
    XCTAssertEqual(measurement.leftShare, 5.0 / 12.0, accuracy: 0.0001)
    XCTAssertEqual(measurement.rightShare, 7.0 / 12.0, accuracy: 0.0001)
}

func testMeasurementIgnoresFourthChannelWhenCalculatingBalance() {
    let baseline = measurement(sensorLoads: [3, 4, 5, 0], aggregate: 12)
    let changed = measurement(sensorLoads: [3, 4, 5, 100], aggregate: 12)

    XCTAssertEqual(baseline.leftLoadKGF, changed.leftLoadKGF, accuracy: 0.0001)
    XCTAssertEqual(baseline.rightLoadKGF, changed.rightLoadKGF, accuracy: 0.0001)
    XCTAssertEqual(baseline.leftShare, changed.leftShare, accuracy: 0.0001)
    XCTAssertEqual(baseline.rightShare, changed.rightShare, accuracy: 0.0001)
}

func testMeasurementIgnoresNonFiniteAndNegativeReferenceZoneLoads() {
    let measurement = measurement(sensorLoads: [.nan, -1, 2, .infinity], aggregate: 2)

    XCTAssertEqual(measurement.leftLoadKGF, 0, accuracy: 0.0001)
    XCTAssertEqual(measurement.rightLoadKGF, 2, accuracy: 0.0001)
    XCTAssertEqual(measurement.leftShare, 0, accuracy: 0.0001)
    XCTAssertEqual(measurement.rightShare, 1, accuracy: 0.0001)
}
```

Expected RED reason: the old `[0, 2]` / `[1, 3]` groups include channel 3 and do not split channel 1.

- [ ] **Step 2: Run the balance test target and verify RED**

Run:

```sh
xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 17 Pro' -derivedDataPath .context/DerivedData-motherboard-reference-decoder -only-testing:HangTenTests/MotherboardModelsTests
```

Expected: the new balance expectations fail against the interleaved grouping.

- [ ] **Step 3: Implement the neutral center split and add provenance documentation**

Replace the interleaved arrays with reference-zone indexes and a weighted finite/non-negative accumulator:

```swift
private enum ReferenceZone {
    static let left = 0
    static let center = 1
    static let right = 2
}

var leftLoadKGF: Double {
    load(for: [(ReferenceZone.left, 1), (ReferenceZone.center, 0.5)])
}

var rightLoadKGF: Double {
    load(for: [(ReferenceZone.center, 0.5), (ReferenceZone.right, 1)])
}

private func load(for weightedChannels: [(index: Int, weight: Double)]) -> Double {
    weightedChannels.reduce(0) { total, channel in
        guard sensorLoadsKGF.indices.contains(channel.index),
              sensorLoadsKGF[channel.index].isFinite,
              channel.weight.isFinite else { return total }
        let weightedLoad = max(0, sensorLoadsKGF[channel.index]) * max(0, channel.weight)
        let sum = total + weightedLoad
        return sum.isFinite ? sum : .greatestFiniteMagnitude
    }
}
```

In the Motherboard section of `docs/IOS_RUNTIME_SERVICES.md`, add one paragraph stating that the first three values are an unofficial left/center/right compatibility model, center is split neutrally for the unchanged two-side UI, the fourth value is diagnostic-only, and calibration remains four-sensor.

- [ ] **Step 4: Run focused combined verification**

Run:

```sh
xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 17 Pro' -derivedDataPath .context/DerivedData-motherboard-reference-decoder -only-testing:HangTenTests/MotherboardModelsTests -only-testing:HangTenTests/MotherboardProtocolTests
```

Expected: both suites pass; protocol aggregate and displayed side loads remain 12 kgf in their new tests.

- [ ] **Step 5: Commit**

```sh
git add HangTen/Models/MotherboardModels.swift HangTenTests/MotherboardModelsTests.swift docs/IOS_RUNTIME_SERVICES.md
git commit -m "fix: derive motherboard balance from reference zones"
```

### Task 3: Full regression verification

**Files:**
- Verify only: `HangTen.xcodeproj`, Task 1–2 source/tests, and `docs/IOS_RUNTIME_SERVICES.md`.

**Interfaces:**
- Consumes: the completed Task 1 and Task 2 deliverables.
- Produces: fresh full-target evidence for the final review.

- [ ] **Step 1: Run the full XCTest target**

```sh
xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 17 Pro' -derivedDataPath .context/DerivedData-motherboard-reference-decoder
```

Expected: `TEST SUCCEEDED` and zero test failures.

- [ ] **Step 2: Inspect the final diff**

```sh
git diff --check main...HEAD
git diff --stat main...HEAD
git status --short
```

Expected: no whitespace errors; only the documented design/plan and Task 1–2 files have changed; the worktree is clean.

- [ ] **Step 3: Commit only a verification-driven correction**

If no correction is needed, create no empty commit. If a correction is needed, modify only the relevant task files, rerun the relevant focused test plus Step 1, and commit those exact files with a terse `fix:` message.

## Plan Self-Review

- **Spec coverage:** Task 1 covers selection, polarity-before-tare, raw preservation, aggregate exclusion, and the untouched four-channel lifecycle. Task 2 covers the neutral split, unchanged UI API, channel-3 exclusion, safety behavior, and provenance. Task 3 requires fresh full-suite evidence.
- **Placeholder scan:** No TBD/TODO markers or unspecified test behavior remain.
- **Type consistency:** The plan changes only the existing protocol decoder, model computed properties, tests, and runtime documentation; it adds no persistence schema or caller-facing type.

