# Isolated iOS Simulator validation

Conductor can run several agents against the same Mac simultaneously. A device
addressed as `booted` is therefore shared mutable state: another agent can
install a different build under the same bundle ID while a review is in
progress. Hang Ten validation must use a dedicated device and its explicit
UUID for every command.

## Workbench handoff boundary

The browser suite's **Validate** tool accepts only an explicit UUID from the
caller and formats copyable build, install, launch, and screenshot commands.
It does not create, delete, boot, erase, or archive simulators, and it never
commits, pushes, or synchronizes remotely. Before entering a UUID in the
browser, create and record the dedicated simulator under this ownership
contract. The caller is responsible for booting, reviewing, and cleaning up
that exact UUID; never substitute `booted` or another workspace's device.

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

```zsh
set -euo pipefail

workspace_path="$PWD"
workspace_name="$CONDUCTOR_WORKSPACE_NAME"
test -n "$workspace_name"
mkdir -p "$workspace_path/.context"
manifest="$workspace_path/.context/conductor-owned-simulators"
pending_manifest="$workspace_path/.context/conductor-pending-simulators"
simulator_name="Hang Ten Conductor $workspace_name Review"
device_type_id="${DEVICE_TYPE_ID:?Set DEVICE_TYPE_ID from xcrun simctl list devicetypes}"
runtime_id="${RUNTIME_ID:?Set RUNTIME_ID from xcrun simctl list runtimes}"
uuid_regex='^[0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12}$'
pending_simulator_uuid=""
pending_recorded_simulator_uuid=""

cleanup() {
  CONDUCTOR_WORKSPACE_PATH="$workspace_path" \
  CONDUCTOR_WORKSPACE_NAME="$workspace_name" \
  "$workspace_path/scripts/conductor-resource-cleanup.sh" archive
}
remove_pending_record() {
  if [[ -z "$pending_recorded_simulator_uuid" || ! -f "$pending_manifest" ]]; then
    return 0
  fi
  local tmp="$pending_manifest.tmp.$$"
  if ! awk -v uuid="$pending_recorded_simulator_uuid" '{ actual_uuid = $0; if (toupper(actual_uuid) != toupper(uuid)) print }' "$pending_manifest" > "$tmp"; then
    rm -f "$tmp"
    return 1
  fi
  if [[ -s "$tmp" ]]; then
    mv "$tmp" "$pending_manifest"
  else
    rm -f "$tmp" "$pending_manifest"
  fi
  pending_recorded_simulator_uuid=""
}
cleanup_pending_simulator() {
  if [[ -z "$pending_simulator_uuid" ]]; then
    return 0
  fi
  if [[ ! "$pending_simulator_uuid" =~ $uuid_regex ]]; then
    printf 'pending simulator create output is not a valid UUID: %s\n' "$pending_simulator_uuid" >&2
    return 1
  fi
  local simulator_record simulator_name simulator_state
  simulator_record="$(xcrun simctl list devices | awk -v uuid="$pending_simulator_uuid" '
    {
      line = $0
      sub(/^[[:space:]]+/, "", line)
      sub(/[[:space:]]+$/, "", line)
      state = line
      if (state !~ / \([^()]*\)$/) next
      sub(/^.* \(/, "", state)
      sub(/\)$/, "", state)
      fields = line
      sub(/ \([^()]*\)$/, "", fields)
      if (fields !~ / \([^()]*\)$/) next
      actual_uuid = fields
      sub(/^.* \(/, "", actual_uuid)
      sub(/\)$/, "", actual_uuid)
      if (toupper(actual_uuid) != toupper(uuid)) next
      name = fields
      sub(/ \([^()]*\)$/, "", name)
      print name "\t" state
      exit
    }
  ')"
  IFS=$'\t' read -r simulator_name simulator_state <<< "$simulator_record"
  if [[ -z "$simulator_record" || "$simulator_name" != "Hang Ten Conductor $workspace_name "* ]]; then
    printf 'pending simulator %s failed exact UUID/name ownership check\n' "$pending_simulator_uuid" >&2
    return 1
  fi
  if ! xcrun simctl delete "$pending_simulator_uuid"; then
    printf 'failed to delete pending simulator %s\n' "$pending_simulator_uuid" >&2
    return 1
  fi
  pending_simulator_uuid=""
}
cleanup_on_exit() {
  original_status=$?
  trap - EXIT INT TERM
  cleanup_status=0
  archive_cleanup_status=0
  if cleanup; then
    remove_pending_record || cleanup_status=$?
  else
    archive_cleanup_status=$?
    cleanup_status=$archive_cleanup_status
  fi
  fallback_cleanup_status=0
  cleanup_pending_simulator || fallback_cleanup_status=$?
  if (( cleanup_status == 0 && fallback_cleanup_status != 0 )); then
    cleanup_status=$fallback_cleanup_status
  fi
  artifact_cleanup_status=0
  rm -rf "$workspace_path/.context/DerivedData" \
    "$workspace_path/.context/workout-raw.png" \
    "$workspace_path/.context/workout-landscape.png" || artifact_cleanup_status=$?
  if (( cleanup_status == 0 && artifact_cleanup_status != 0 )); then
    cleanup_status=$artifact_cleanup_status
  fi
  if (( original_status != 0 )); then
    exit "$original_status"
  fi
  exit "$cleanup_status"
}
signal_exit() {
  trap - INT TERM
  exit "$1"
}
trap cleanup_on_exit EXIT
trap 'signal_exit 130' INT
trap 'signal_exit 143' TERM

pending_simulator_uuid="$(xcrun simctl create "$simulator_name" "$device_type_id" "$runtime_id")"
if [[ -z "$pending_simulator_uuid" || ! "$pending_simulator_uuid" =~ $uuid_regex ]]; then
  printf 'simctl create returned invalid simulator UUID: %s\n' "$pending_simulator_uuid" >&2
  exit 1
fi
simulator_uuid="$pending_simulator_uuid"
if printf '%s\n' "$simulator_uuid" >> "$pending_manifest"; then
  pending_recorded_simulator_uuid="$simulator_uuid"
  pending_simulator_uuid=""
else
  printf 'failed to write pending simulator record for %s\n' "$simulator_uuid" >&2
  pending_simulator_uuid="$simulator_uuid"
  exit 1
fi
if ! printf '%s\n' "$simulator_uuid" >> "$manifest"; then
  printf 'failed to write simulator manifest for %s\n' "$simulator_uuid" >&2
  exit 1
fi
pending_simulator_uuid=""
```

Use `$simulator_uuid` as `<uuid>` in the following commands. Do not use
`booted`, a common device name, a broad process kill, or another workspace's
review device in later commands. The trap is idempotent: it runs on successful
completion, failure, or interruption and archives only manifest UUIDs whose
names carry this workspace's exact marker. It keeps pending simulator records
until archive cleanup succeeds.

The trap removes only the exact workspace-local artifacts created by this guide:
`.context/DerivedData`, `.context/workout-raw.png`, and
`.context/workout-landscape.png`. The trap removes those exact artifacts
regardless of simulator cleanup status. If simulator archive cleanup fails,
both simulator manifests remain in place for a retry, and the original command
status is preserved.

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
| `HANGTEN_REVIEW_PLAN=1` | Open the featured plan detail from Train. |
| `HANGTEN_REVIEW_PLANS=1` | Select the full Plans tab. |
| `HANGTEN_REVIEW_HISTORY=1` | Select the History tab. |
| `HANGTEN_REVIEW_BOARD_PICKER=1` | Open the full-page board picker from Train. |
| `HANGTEN_REVIEW_SETTINGS=1` | Open Settings from Train. |
| `HANGTEN_REVIEW_PLAN_ID=<TrainingPlan.id>` | Make a specific plan the featured plan. |
| `HANGTEN_REVIEW_WORKOUT=1` | Open the featured workout. |
| `HANGTEN_REVIEW_STEP=<step number>` | Preview any plan step without waiting. |
| `HANGTEN_REVIEW_HEALTH=1` | Open Settings from Train with the Apple Health card visible. |
| `HANGTEN_REVIEW_MOTHERBOARD=1` | Open Settings from Train and use the deterministic sensor transport. |
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

For primary-navigation review, the Train gear is `train.settings`, its board
link is `train.changeBoard`, and the compact Plans board link is
`plans.changeBoard`. Both board links open the full-page picker; each choice is
`boardPicker.board.<TrainingBoard.id>`, selects and persists that board, then
returns to its originating screen. Settings exposes `settings.sensor`,
`health.historySource`, and either `health.connect` or `health.settings` when
that action is available. History is the third root tab and opens directly to
the chronological saved-session list.

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
- Skip during timed work and confirm the next step appears immediately with
  inactive holds, then observe and hear 5-4-3-2-1 before the next cue starts.
  Confirm the same behavior after pausing first; the session must be running
  once the countdown completes.
- During a skip countdown, confirm Routine and Skip step are disabled. Cancel
  it and verify the destination remains paused and resumable. Background the
  app during the countdown and verify it returns paused at that destination.
- Skip during timed rest and confirm the target still uses the full current
  step duration, including rest. Skip the final step and confirm completion
  appears immediately without a five-second countdown.
- Repeat these checks in portrait and landscape, including board highlights,
  grip cues, spoken audio, rotation, and the existing completion/logging path.
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
  dedicated simulator. This route opens Train's Settings destination with the
  Apple Health card visible; it
  does not request authorization. Leave the visible Connect Apple Health
  action untouched while triggering a Settings/scene refresh and completing a
  short routine. Confirm Settings continues to report the local-fallback
  source and History retains the detailed local session row. Use the relevant
  service tests to verify that no HealthKit workout is saved, imported, or
  migrated before Connect is tapped.
- Tap Connect Apple Health to start the user-initiated flow and persist the
  HealthKit history-sync request flag.
- Confirm the system permission sheet requests both read and write access to
  workouts and shows the revised read usage text about restoring progress on a
  new device. Record the displayed authorization/status copy, including
  `Not connected`, `Access denied`, `Connected`, and `Open app settings` as
  applicable.
- Before granting HealthKit access, complete a short routine and tap Log
  session. Confirm one new detailed local row appears in History, the Health
  card shows `History stored on this device until Apple Health is connected.`,
  and the row remains after leaving Settings and returning to History. That row
  comes from `AppStore.sessionHistory`, the app's local detailed session
  records; it is not proof of a HealthKit save or import. Tap End session in a
  separate check and confirm it does not create a local history record.
- Grant HealthKit access later by tapping Connect Apple Health when it is
  available, or by enabling Hang Ten's workout access in Settings after a
  denial. Return to the app and wait for the scene-activation refresh. Confirm
  the Apple Health card's source copy changes to
  `History synced from Apple Health.` and inspect its status and any error or
  action. If a successful query has no accepted Hang Ten history, treat the
  empty `.healthKit` result as ambiguous: preserve any local fallback and do
  not treat the empty result as proof of no history or denied access. Verify
  that an authorized empty result shows the `Connected` status and no Connect
  action. When the service reports accepted HealthKit history, no action is
  shown; local fallback maps to Open app settings, while denied and unavailable
  behavior remains unchanged.
- Relaunch the app on the same explicit simulator UUID. Open Settings and
  validate the Apple Health source, authorization status, and any sync error;
  that card reflects `AppStore.workoutHistory`. Then open History and confirm
  only that the local detailed row and latest plan title persist. A History row
  is not evidence of a HealthKit import. Validate HealthKit restoration,
  pending-record migration, and deduplication with
  `WorkoutHistoryServiceTests` and `AppStoreTests`, and inspect the actual
  HealthKit records on a signed physical-device build when validating the
  end-to-end behavior.
- From Train, open Settings with `train.settings`; from the denied or
  local-fallback state use `health.settings` to open system app settings,
  change Hang Ten's Health permissions, return to the app, and confirm the
  Settings authorization, source, and error states refresh automatically
  without a new permission prompt on appearance.
- Preserve the signed HealthKit entitlement check. Inspect the installed app
  and, for simulator builds, the intermediate `HangTen.app-Simulated.xcent`
  under the workspace-specific Derived Data path; verify
  `com.apple.developer.healthkit = true` and the generated read/write usage
  descriptions. Use the exact simulator UUID for every command and never use
  `booted`. After installing, inspect the embedded app `Info.plist` using the
  container path established above:

  ```sh
  app_path="$(xcrun simctl get_app_container <uuid> com.hangten.training app)"
  /usr/libexec/PlistBuddy -c 'Print :NSHealthShareUsageDescription' "$app_path/Info.plist"
  /usr/libexec/PlistBuddy -c 'Print :NSHealthUpdateUsageDescription' "$app_path/Info.plist"
  ```

  Both commands must print the non-empty read and write usage descriptions.
- Simulator validation covers the permission flow and the UI's local-fallback,
  source, status, and error states. The service tests cover migration and
  deduplication logic, but neither proves cross-device HealthKit restoration;
  repeat that scenario on two physical devices using the same HealthKit
  account before release.
- On a signed build, open Train's gear → Settings, tap Connect Apple Health,
  and inspect the
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

The creation trap calls `scripts/conductor-resource-cleanup.sh archive`; leave
it installed for the whole validation. The created UUID is written to the
pending manifest before the owned manifest so the archive mode can retry cleanup
after an interrupted setup. Archive cleanup verifies each pending or owned
manifest entry against the exact `Hang Ten Conductor $CONDUCTOR_WORKSPACE_NAME `
name prefix, shuts down the matching device if necessary, and runs
`xcrun simctl delete` on that exact UUID. Pending state is removed only after
archive cleanup succeeds; the direct delete fallback is limited to a validated
UUID whose pending record could not be written, and it must re-query that exact
UUID, parse the exact device-name field, and require the exact
`Hang Ten Conductor $CONDUCTOR_WORKSPACE_NAME ` marker before deleting. If the
lookup or ownership check fails, it does not delete and returns failure. This is
immediate workspace cleanup, while the Conductor archive hook is a failsafe for
an abandoned workspace; both manifests remain available for archive retry.

Do not delete or shut down a shared/unknown simulator. The cleanup script must
not receive an unrecorded UUID or a simulator without the exact workspace
ownership marker.
