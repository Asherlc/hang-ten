# Isolated iOS Simulator validation

Conductor can run several agents against the same Mac simultaneously. A device
addressed as `booted` is therefore shared mutable state: another agent can
install a different build under the same bundle ID while a review is in
progress. Hang Ten validation must use a dedicated device and its explicit
UUID for every command.

## Create and identify a dedicated device

Inspect available identifiers:

```sh
xcrun simctl list devicetypes
xcrun simctl list runtimes
```

Create a uniquely named device using identifiers copied from those lists:

```sh
xcrun simctl create \
  "HangTen <workspace> Review" \
  <device-type-id> \
  <runtime-id>
```

Save the returned UUID. Do not use `booted`, a common device name, a broad
process kill, or another workspace's review device in later commands.

## Boot and wait for real readiness

Fresh simulators can report `Booted` before launch services are ready. Boot the
exact UUID, then poll a short command with a timeout:

```sh
xcrun simctl boot <uuid>

simulator_ready=0
for attempt in {1..40}; do
  if perl -e 'alarm 4; exec @ARGV' \
    xcrun simctl spawn <uuid> launchctl print system >/dev/null; then
    simulator_ready=1
    break
  fi
  sleep 3
done

if (( simulator_ready == 0 )); then
  echo "Simulator did not become ready" >&2
  exit 1
fi
```

`xcrun simctl bootstatus <uuid> -b` is convenient when it returns normally, but
the bounded readiness poll proved more reliable on a newly created device.

## Build for that destination

Use a workspace-specific Derived Data path and explicit destination:

```sh
xcodebuild \
  -project HangTen.xcodeproj \
  -scheme HangTen \
  -configuration Debug \
  -destination 'platform=iOS Simulator,id=<uuid>' \
  -derivedDataPath .context/DerivedData-lima \
  build
```

`CODE_SIGNING_ALLOWED=NO` is acceptable for a compile-only check. Do not use it
for HealthKit permission validation: the installed app needs its simulator
signature and generated simulated HealthKit entitlement. Xcode may keep that
entitlement in an intermediate `HangTen.app-Simulated.xcent` file even when
`codesign -d --entitlements` reports an empty entitlement dictionary for the
simulator app. Inspect the `*-Simulated.xcent` file for
`com.apple.developer.healthkit = true` when validating a simulator build.

## Install and launch explicitly

```sh
xcrun simctl terminate <uuid> com.hangten.training || true
xcrun simctl install \
  <uuid> \
  .context/DerivedData-lima/Build/Products/Debug-iphonesimulator/HangTen.app
xcrun simctl launch <uuid> com.hangten.training
```

First install or launch on a fresh device can take noticeably longer. Bound a
stuck command with `perl -e 'alarm 40; exec @ARGV' ...`, then inspect device
logs before assuming it failed.

Confirm the installed container when builds from several workspaces share a
bundle ID:

```sh
xcrun simctl get_app_container <uuid> com.hangten.training app
```

When provenance is in doubt, compare a checksum or identifying strings from
the built and installed `HangTen` binaries. This caught a shared-device case in
which an older routine build replaced the app between screenshots.

## DEBUG review routes

Pass app environment through `simctl` with the `SIMCTL_CHILD_` prefix:

| Variable | Effect |
| --- | --- |
| `HANGTEN_REVIEW_PLAN=1` | Open the featured plan detail. |
| `HANGTEN_REVIEW_PLANS=1` | Select the full Plans tab. |
| `HANGTEN_REVIEW_PLAN_ID=<TrainingPlan.id>` | Make a specific plan the featured plan. |
| `HANGTEN_REVIEW_WORKOUT=1` | Open the featured workout. |
| `HANGTEN_REVIEW_STEP=<step number>` | Preview any plan step without waiting. |
| `HANGTEN_REVIEW_GRIP=<GripType raw value>` | Override the plan-detail grip preview. |
| `HANGTEN_REVIEW_HEALTH=1` | Select the Progress tab and Health card. |
| `HANGTEN_REVIEW_LANDSCAPE=1` | Request landscape-right scene geometry. |
| `HANGTEN_REVIEW_PORTRAIT=1` | Request portrait scene geometry. |
| `HANGTEN_REVIEW_AUTOSTART=1` | Start the three-second countdown on launch. |

Example:

```sh
SIMCTL_CHILD_HANGTEN_REVIEW_WORKOUT=1 \
SIMCTL_CHILD_HANGTEN_REVIEW_STEP=2 \
SIMCTL_CHILD_HANGTEN_REVIEW_LANDSCAPE=1 \
xcrun simctl launch <uuid> com.hangten.training
```

These hooks are compiled only in DEBUG and do not affect production launches.

## Capture and orient screenshots

```sh
xcrun simctl io <uuid> screenshot .context/workout-raw.png
cp .context/workout-raw.png .context/workout-landscape.png
sips -r 270 .context/workout-landscape.png
```

On the simulator runtimes used during development, a landscape interface could
still be emitted in the hardware-native portrait pixel buffer. Inspect the raw
image before rotating; use 90 instead of 270 when the interface is turned the
other direction.

Review portrait and landscape separately. For a board change, capture inactive
and highlighted surface, shelf, deep-recess, and shallow-recess states. For a
routine change, preview every distinct hold target and finger cue.

## Validate runtime services

- Launch a new workout and confirm it visibly begins at step 1. Before start,
  and throughout the initial 3-2-1 countdown, confirm the Routine and Skip
  step controls are disabled.
- Open Routine and inspect its numbered, labeled step rows. While running,
  select a later step and confirm that the workout keeps running from that
  step's start. Pause, select an earlier step, and confirm it stays paused at
  that step's start. Tap the current row and confirm it is a no-op.
- Skip during timed work and confirm that it advances at the current step's
  full boundary, including any following rest.
- Skip during timed rest and confirm the next step starts after the full step
  duration, including rest. Skip the final step and confirm the existing
  completion state appears. Repeat the Routine and Skip step checks in both
  portrait and landscape, inspecting the resulting timer, board highlights,
  hand cues, and re-cued audio.
- Start a routine and observe 3, 2, 1, task-start, final-three, and completion
  speech with audio enabled. Repeat with the speaker toggle disabled.
- Rotate while paused and while running; timer state and selected holds must
  remain stable.
- Open a plan containing a stopwatch activity in portrait and landscape. Check
  the `workout.stopwatch` accessibility element and
  `workout.stopwatch.toggle`; confirm the visible value is `00:00` before
  starting, the toggle is labeled “Start stopwatch,” changes to “Stop
  stopwatch” while running, and shows the observed value after stopping.
- Use the stopwatch's explicit Start/Stop control, then pause the workout and
  resume it. Confirm normal pause preserves the accumulated active seconds and
  does not advance the stopwatch while paused. Background or lock the app and
  confirm the same pause behavior; returning requires the normal workout
  resume.
- Exercise a fixed work/rest step and verify the rest boundary: work is
  recorded with its prescribed active duration, rest is a following ordered
  segment with its duration, and rest has no hold metadata. Confirm the UI
  finalizes an active stopwatch when entering rest, navigating to another
  step, or skipping the current step.
- Complete a session through the “Log session” control and confirm the
  completion handoff uses the selected board, not a default board. Inspect
  selected-board cues in the workout and verify resolved hold type and explicit
  physical size where the board supplies one. Confirm a never-started
  stopwatch and a genuinely untimed work segment have no duration value.
- Launch with `HANGTEN_REVIEW_HEALTH=1` on a fresh or permission-reset
  dedicated simulator. This route opens the Progress tab and Health card; it
  does not request authorization. Leave the visible Connect Apple Health
  action untouched while triggering a Progress/scene refresh and completing a
  short routine. Confirm the session remains in local fallback history and no
  HealthKit workout is saved, imported, or migrated before Connect is tapped.
- Tap Connect Apple Health to start the user-initiated flow and persist the
  HealthKit history-sync request flag.
- Confirm the system permission sheet requests both read and write access to
  workouts and shows the revised read usage text about restoring progress on a
  new device. Record the displayed authorization/status copy, including
  `Not connected`, `Access denied`, `Connected`, and `Open app settings` as
  applicable.
- Before granting HealthKit access, complete a short routine and tap Log
  session. Confirm the session count increases once, the Health card shows
  `History stored on this device until Apple Health is connected.`, and the
  session remains after leaving and returning to Progress. Tap End session in
  a separate check and confirm it does not create a history record.
- Grant HealthKit access later by tapping Connect Apple Health when it is
  available, or by enabling Hang Ten's workout access in Settings after a
  denial. Return to the app and wait for the scene-activation refresh. Confirm
  the pending local session syncs to HealthKit, the source copy changes to
  `History synced from Apple Health.`, and the same session is still counted
  exactly once. If a successful query has no accepted Hang Ten history, treat
  the empty `.healthKit` result as ambiguous: preserve any local fallback,
  keep Connect Apple Health available as a conservative recovery action, and
  do not treat the empty result as proof of no history or denied access. When
  accepted HealthKit history is visible, no action is shown; local fallback
  maps to Open app settings, while denied and unavailable behavior remains
  unchanged.
- Relaunch the app on the same explicit simulator UUID, open Progress, and
  confirm the HealthKit-backed count and latest plan title persist. Refresh or
  relaunch again and verify migration does not double-count the session.
- Open app Settings from the denied/local-fallback state, change Hang Ten's
  Health permissions, return to the app, and confirm authorization and history
  refresh automatically without a new permission prompt on appearance.
- Preserve the signed HealthKit entitlement check. Inspect the installed app
  and, for simulator builds, the intermediate `HangTen.app-Simulated.xcent`
  under the workspace-specific Derived Data path; verify
  `com.apple.developer.healthkit = true` and the generated read/write usage
  descriptions. Use the exact simulator UUID for every command and never use
  `booted`.
- Simulator validation covers the permission flow, local fallback, migration,
  and deduplication. It does not prove cross-device HealthKit restoration;
  repeat that scenario on two physical devices using the same HealthKit
  account before release.
- On a signed build, open Progress, tap Connect Apple Health, and inspect the
  user-triggered HealthKit authorization sheet. After authorization, complete a
  short session and verify the write path is exercised; the saved metadata
  must include the board ID/name and versioned activity-segment JSON. The
  simulator validates wiring and permission flow, but final metadata inspection
  still requires a physical device.
- Choose “End session” and confirm the session dismisses without the completion
  handoff and without logging an Apple Health workout.
- Launch with `HANGTEN_REVIEW_HEALTH=1`, tap Connect Apple Health, inspect the
  system permission sheet, and complete a short debug session on a signed
  build. Simulator behavior does not replace a physical-device HealthKit test
  before release.

See `docs/IOS_RUNTIME_SERVICES.md` for the implementation contract.

## Cleanup

Shut down only the dedicated UUID you created:

```sh
xcrun simctl shutdown <uuid>
```

Do not delete or shut down a shared/unknown simulator. Delete the dedicated
device only when its exact UUID and ownership are certain.
