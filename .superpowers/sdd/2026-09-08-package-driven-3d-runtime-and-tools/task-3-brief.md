# Task 3 brief — media-aware board map and unavailable UI

Owner: `shaky-rat`

## Scope

Characterize and preserve the Task 2-fix implementation of Task 3's typed
presentation routing. Raster presentations continue through the existing
package image and canonical-path map. Model presentations continue through the
generic SceneKit surface only; loading and load failure are non-interactive,
and failure uses `boardModel.unavailable` without a raster fallback.

## Focused regression

Add native coverage that a model view exposes accessibility elements only for
logical holds with descriptor-bound geometry nodes. This protects the model
surface from exposing a logical hold that cannot be rendered or picked.

## Verification plan

Use the locked local package configuration to build the native and UI test
targets. CoreSimulatorService is checked once before attempting the prescribed
owned simulator lifecycle. If unavailable, retain a compile-only result and
record the runtime XCTest/UI gate as pending rather than creating or reusing a
device.
