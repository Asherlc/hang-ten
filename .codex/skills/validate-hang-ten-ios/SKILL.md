---
name: validate-hang-ten-ios
description: Build, install, launch, and visually validate Hang Ten on an isolated iOS Simulator, including DEBUG review routes, landscape screenshots, spoken countdowns, and HealthKit permission wiring. Use after board, routine, workout, audio, orientation, or Apple Health changes, especially in parallel Conductor workspaces.
---

# Validate Hang Ten iOS

Read `docs/IOS_SIMULATOR_VALIDATION.md` and
`docs/IOS_RUNTIME_SERVICES.md` completely before running validation.

## Workflow

1. Create or resolve a simulator owned by this workspace. Use its explicit UUID
   for every operation; never target `booted`.
2. Wait for launch services, then build with a workspace-specific Derived Data
   path and explicit destination.
3. Keep signing enabled for HealthKit validation. Install the exact built app
   and confirm its app container when parallel builds share the bundle ID.
4. Use `SIMCTL_CHILD_HANGTEN_REVIEW_*` routes to reach the plan, workout step,
   grip, Health card, landscape layout, and automatic countdown deterministically.
5. Capture and orient screenshots. Inspect board geometry, highlight alignment,
   hand mirroring, text clipping, and timer continuity.
6. Exercise spoken 3-2-1 and task cues, audio-off behavior, rotation while
   running/paused, the user-triggered Health permission sheet, and workout save.
7. Shut down only the dedicated simulator UUID when review is complete.

## Validation standard

Do not accept a successful compile as visual or runtime validation. Report the
exact build command, simulator identity, states inspected, screenshots reviewed,
and any behavior that still requires a physical device.
