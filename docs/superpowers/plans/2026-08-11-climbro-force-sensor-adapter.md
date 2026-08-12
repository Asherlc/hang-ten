# Climbro Force-Sensor Adapter Implementation Plan

**Goal:** Add a source-faithful, protocol-level Climbro BLE adapter and focused tests without runtime Bluetooth integration.

**Architecture:** `ClimbroProtocolAdapter` declares case-sensitive name-prefix discovery, the evidenced UART notification contract, recorded-but-unexposed TX/control-point UUIDs, no capabilities, no writes, and no commands. `ClimbroProtocolParser` owns explicit marker state across notifications and returns validated `ForceSensorSample` values.

**Tech Stack:** Swift 5, Foundation `Data` and `UUID`, XCTest, Xcode project registration.

## Global Constraints

- Source authority is immutable commit `1cf3d4f7a00ffd5de6000e4aa77f86819765ee43`, verified blob `4257b024609ebf545f6131319d65fd61e2cadd3e`, at `packages/core/src/models/device/climbro.model.ts` in `Stevie-Ray/hangtime-grip-connect`.
- Do not invent Climbro writes, commands, start/stop behavior, hardware tare, battery clamping, packet-size limits, timeout/resynchronization rules, runtime Bluetooth integration, UI, history, or session routing.
- Named discovery is case-sensitive `name.hasPrefix("Climbro")`; no advertised-service requirement is added.
- UART notification service and characteristic are `49535343-fe7d-4ae5-8fa9-9fafd205e455` and `49535343-1e4d-4bd9-ba61-23c647249616`.
- TX `49535343-8841-43f4-a8d4-ecbe34729bb3` and control point `49535343-4c8a-39b3-2f49-511cff073b7e` are recorded constants only; no write API exposes them.
- Parser state persists across `decode(_:receivedAt:)`: `0xF0` selects battery mode, `0xF5` selects sensor mode, and `0xF6` is a 36 kg sensor sentinel.
- Sensor bytes are mapped to kgf only as a Hang Ten storage adaptation pending vendor proof, and every emission goes through `ForceSensorSample` validation.

## File Structure

- `HangTen/Models/ClimbroProtocol.swift`: adapter and stateful byte-stream parser.
- `HangTenTests/ClimbroProtocolTests.swift`: executable source fixtures and discovery coverage.
- `docs/source-audits/2026-08-11-climbro-protocol.md`: immutable source links, verified blob, mappings, and caveats.
- `HangTen.xcodeproj/project.pbxproj`: file references, groups, and source build phases for both Swift files.

## Implementation Checklist

- [x] Safely update branch onto `origin/agent/force-sensor-entralpi`.
- [x] Preserve Climbro-only branch scope and drop unrelated PitchSix replay during rebase.
- [x] Write/verify failing focused tests for stricter audited contract and parser API.
- [x] Implement the adapter with empty capabilities, UART notification contract, no write characteristic, and nil command payloads.
- [x] Implement explicit parser state, raw UInt8 battery conversion, pre-marker suppression, sensor sentinel handling, and validated sample emission.
- [x] Register Swift files in the Xcode project with unique IDs.
- [x] Document every supported fact and caveat in the source audit.
- [x] Run diff checks and focused build verification.
- [x] Push branch and open draft PR against `agent/force-sensor-entralpi`.

## Verification Commands

```bash
rtk git hash-object .context/climbro-audit/climbro.model.ts
rtk git diff --check HEAD
rtk xcodebuild build-for-testing -project HangTen.xcodeproj -scheme HangTen -destination 'generic/platform=iOS Simulator' -only-testing:HangTenTests/ClimbroProtocolTests
rtk timeout 90 xcodebuild test-without-building -xctestrun /Users/asherlc/Library/Developer/Xcode/DerivedData/HangTen-dhfjlqlhugvxomeviwfsvybjscow/Build/Products/HangTen_iphonesimulator26.5-arm64-x86_64.xctestrun -destination 'id=01EB15DD-D284-440E-AC59-A30B0EFA869B' -only-testing:HangTenTests/ClimbroProtocolTests
```

The final `test-without-building` command is expected to be reported from actual execution. If the simulator runner stalls, record its timeout instead of claiming tests pass.
