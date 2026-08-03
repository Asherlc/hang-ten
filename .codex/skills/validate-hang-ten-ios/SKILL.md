---
name: validate-hang-ten-ios
description: Build, install, launch, and visually validate Hang Ten on an isolated iOS Simulator, including DEBUG review routes, landscape screenshots, spoken countdowns, and HealthKit permission wiring. Use after board, routine, workout, audio, orientation, or Apple Health changes, especially in parallel Conductor workspaces.
---

# Validate Hang Ten iOS

Read `docs/IOS_SIMULATOR_VALIDATION.md` and
`docs/IOS_RUNTIME_SERVICES.md` completely before running validation.

## Workflow

1. Capture `workspace_path="$PWD"` and
   `workspace_name="$CONDUCTOR_WORKSPACE_NAME"`, require the workspace name, and
   create the `.context` manifest directory. Define cleanup that runs
   `scripts/conductor-resource-cleanup.sh archive` with the current workspace
   path and name, then install `EXIT`, `INT`, and `TERM` traps before any
   `simctl create`. Create a simulator named
   `Hang Ten Conductor $CONDUCTOR_WORKSPACE_NAME Review`, then immediately append
   the exact returned UUID to `.context/conductor-owned-simulators` before any
   boot or build. Use that UUID for every simulator operation; never target
   `booted`.
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
7. On success, failure, or interruption, the cleanup trap shuts down and deletes
   the exact owned UUID recorded in the manifest after verifying its workspace
   marker. Do not delete shared or unknown simulators.

## Validation standard

Do not accept a successful compile as visual or runtime validation. Report the
exact build command, simulator identity, states inspected, screenshots reviewed,
and any behavior that still requires a physical device.
