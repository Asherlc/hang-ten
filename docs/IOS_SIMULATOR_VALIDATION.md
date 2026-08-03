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

Create a uniquely named device using identifiers copied from those lists. The
name must begin with the exact workspace marker `Hang Ten Conductor
$CONDUCTOR_WORKSPACE_NAME`, and its UUID must be recorded before any boot or
build work:

```sh
set -euo pipefail

workspace_path="$PWD"
workspace_name="$CONDUCTOR_WORKSPACE_NAME"
test -n "$workspace_name"
mkdir -p "$workspace_path/.context"
simulator_name="Hang Ten Conductor $workspace_name Review"
device_type_id="${DEVICE_TYPE_ID:?Set DEVICE_TYPE_ID from xcrun simctl list devicetypes}"
runtime_id="${RUNTIME_ID:?Set RUNTIME_ID from xcrun simctl list runtimes}"

cleanup() {
  CONDUCTOR_WORKSPACE_PATH="$workspace_path" \
  CONDUCTOR_WORKSPACE_NAME="$workspace_name" \
  "$workspace_path/scripts/conductor-resource-cleanup.sh" archive
}
signal_exit() {
  trap - INT TERM
  exit "$1"
}
trap cleanup EXIT
trap 'signal_exit 130' INT
trap 'signal_exit 143' TERM

simulator_uuid="$(xcrun simctl create "$simulator_name" "$device_type_id" "$runtime_id")"
if ! printf '%s\n' "$simulator_uuid" >> "$workspace_path/.context/conductor-owned-simulators"; then
  xcrun simctl delete "$simulator_uuid" || true
  exit 1
fi
```

Use `$simulator_uuid` as `<uuid>` in the following commands. Do not use
`booted`, a common device name, a broad process kill, or another workspace's
review device in later commands. The trap is idempotent: it runs on successful
completion, failure, or interruption and archives only manifest UUIDs whose
names carry this workspace's exact marker.

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
  -derivedDataPath .context/DerivedData \
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
  .context/DerivedData/Build/Products/Debug-iphonesimulator/HangTen.app
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
| `HANGTEN_REVIEW_REQUEST_HEALTH=1` | Request the Health permission sheet after opening Progress. DEBUG validation only. |
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
- Launch with `HANGTEN_REVIEW_HEALTH=1`, tap Connect Apple Health, inspect the
  system permission sheet, and complete a short debug session on a signed
  build. Simulator behavior does not replace a physical-device HealthKit test
  before release.
- For non-interactive screenshot validation, combine
  `HANGTEN_REVIEW_HEALTH=1` and `HANGTEN_REVIEW_REQUEST_HEALTH=1`. The latter
  invokes the same authorization method as the visible button and exists only
  in DEBUG; production permission requests remain user-initiated.

See `docs/IOS_RUNTIME_SERVICES.md` for the implementation contract.

## Cleanup

The creation trap calls `scripts/conductor-resource-cleanup.sh archive`; leave
it installed for the whole validation. It verifies each manifest entry against
the exact `Hang Ten Conductor $CONDUCTOR_WORKSPACE_NAME ` name prefix, shuts
down the matching device if necessary, and runs `xcrun simctl delete` on that
exact UUID. This is immediate workspace cleanup, while the Conductor archive
hook is a failsafe for an abandoned workspace.

Do not delete or shut down a shared/unknown simulator. The cleanup script must
not receive an unrecorded UUID or a simulator without the exact workspace
ownership marker.
