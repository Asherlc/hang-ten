# Isolated iOS Simulator validation

Paseo can run several agents against the same Mac simultaneously. A device
addressed as `booted` is therefore shared mutable state: another agent can
install a different build under the same bundle ID while a review is in
progress. Hang Ten validation must use a dedicated device and its explicit
UUID for every command.

## Create and identify a dedicated device

Inspect available identifiers:

```sh
rtk proxy xcrun simctl list devicetypes
rtk proxy xcrun simctl list runtimes
```

Create a uniquely named device using identifiers copied from those lists. The
name must begin with the exact workspace marker `Hang Ten Paseo
$workspace_name`, and its UUID must be recorded before any boot or
build work:

```zsh
set -euo pipefail

workspace_path="${PASEO_WORKTREE_PATH:-$PWD}"
workspace_name="${workspace_path:t}"
test -n "$workspace_name"
mkdir -p "$workspace_path/.context"
manifest="$workspace_path/.context/paseo-owned-simulators"
pending_manifest="$workspace_path/.context/paseo-pending-simulators"
simulator_name="Hang Ten Paseo $workspace_name Review"
device_type_id="${DEVICE_TYPE_ID:?Set DEVICE_TYPE_ID from rtk proxy xcrun simctl list devicetypes}"
runtime_id="${RUNTIME_ID:?Set RUNTIME_ID from rtk proxy xcrun simctl list runtimes}"
uuid_regex='^[0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12}$'
pending_simulator_uuid=""
pending_recorded_simulator_uuid=""

cleanup() {
  PASEO_WORKTREE_PATH="$workspace_path" \
  "$workspace_path/scripts/paseo-resource-cleanup.sh" archive
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
  simulator_record="$(rtk proxy xcrun simctl list devices | awk -v uuid="$pending_simulator_uuid" '
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
  if [[ -z "$simulator_record" || "$simulator_name" != "Hang Ten Paseo $workspace_name "* ]]; then
    printf 'pending simulator %s failed exact UUID/name ownership check\n' "$pending_simulator_uuid" >&2
    return 1
  fi
  if ! rtk proxy xcrun simctl delete "$pending_simulator_uuid"; then
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
  if [[ -e "$workspace_path/.context/DerivedData" ||
        -e "$workspace_path/.context/workout-raw.png" ||
        -e "$workspace_path/.context/workout-landscape.png" ]]; then
    artifact_cleanup_status=1
  fi
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

pending_simulator_uuid="$(rtk proxy xcrun simctl create "$simulator_name" "$device_type_id" "$runtime_id")"
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
rtk proxy xcrun simctl boot <uuid>

simulator_ready=0
for attempt in {1..40}; do
  if rtk proxy perl -e 'alarm 4; exec @ARGV' \
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

`rtk proxy xcrun simctl bootstatus <uuid> -b` is convenient when it returns normally, but
use the bounded readiness poll when launch services are not responding.

## Build for that destination

Fetch the retained Git LFS sources and generate the runtime files before Xcode:

```sh
rtk git lfs pull
rtk proxy bash scripts/build-runtime-assets.sh
```

This produces ignored board USDZ/descriptors, optional suspension/physics
artifacts, grip hand mesh JSON, and plan JSON. Each flat
`Hangboards/<slug>.FCStd` embeds board, cord, and simulation inputs; the hand
Blender source and Swift plan definitions also remain
authoritative. CI consumers receive the same runtime files from the producer
artifact. See [generated artifacts](GENERATED_ARTIFACTS.md).

Use a workspace-specific Derived Data path and explicit destination:

```sh
rtk xcodebuild \
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
rtk proxy xcrun simctl terminate <uuid> com.hangten.training || true
rtk proxy xcrun simctl install \
  <uuid> \
  .context/DerivedData/Build/Products/Debug-iphonesimulator/HangTen.app
rtk proxy xcrun simctl launch <uuid> com.hangten.training
```

First install or launch on a fresh device can take noticeably longer. Bound a
stuck command with `perl -e 'alarm 40; exec @ARGV' ...`, then inspect device
logs before assuming it failed.

Confirm the installed container when builds from several workspaces share a
bundle ID:

```sh
rtk proxy xcrun simctl get_app_container <uuid> com.hangten.training app
```

When provenance is in doubt, compare the built and installed `HangTen` binary
hashes before capturing review evidence.

## Workout deep links

Production deep links open a plan’s workout with the same auto-start behavior as
plan-detail Start routine. Both host forms are accepted:

- `hangten://plan/<TrainingPlan.id>/workout`
- `hangten:///plan/<id>/workout`

Example:

```sh
rtk proxy xcrun simctl openurl <uuid> 'hangten://plan/<planID>/workout'
```

You can combine a deep link with DEBUG review env (below) for step preview or
orientation after launch:

```sh
rtk proxy env SIMCTL_CHILD_HANGTEN_REVIEW_STEP=2 \
SIMCTL_CHILD_HANGTEN_REVIEW_LANDSCAPE=1 \
xcrun simctl launch <uuid> com.hangten.training
rtk proxy xcrun simctl openurl <uuid> 'hangten://plan/research.max-hangs/workout'
```

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
| `HANGTEN_REVIEW_STEP=<step number>` | Preview any plan step without waiting. |
| `HANGTEN_REVIEW_HEALTH=1` | Open Settings from Train with the Apple Health card visible. |
| `HANGTEN_REVIEW_MOTHERBOARD=1` | Open Settings from Train and use the deterministic sensor transport. |
| `HANGTEN_REVIEW_LANDSCAPE=1` | Request landscape-right scene geometry. |
| `HANGTEN_REVIEW_PORTRAIT=1` | Request portrait scene geometry. |
| `HANGTEN_REVIEW_AUTOSTART=1` | Start the three-second countdown on launch. |

Example:

```sh
rtk proxy env SIMCTL_CHILD_HANGTEN_REVIEW_STEP=2 \
SIMCTL_CHILD_HANGTEN_REVIEW_LANDSCAPE=1 \
xcrun simctl launch <uuid> com.hangten.training
```

These hooks are compiled only in DEBUG and do not affect production launches.
See [Workout deep links](#workout-deep-links) to open a workout URL after launch.

For primary-navigation review, the Train gear is `train.settings`, its board
link is `train.changeBoard`, and the compact Plans board link is
`plans.changeBoard`. Both board links open the full-page picker; each choice is
`boardPicker.board.<BoardRevision.id>`, selects and persists that board, then
returns to its originating screen. Settings exposes `settings.sensor`,
`health.historySource`, and either `health.connect` or `health.settings` when
that action is available. History is the third root tab and opens directly to
the chronological saved-session list.

## Capture and orient screenshots

```sh
rtk proxy xcrun simctl io <uuid> screenshot .context/workout-raw.png
rtk proxy cp .context/workout-raw.png .context/workout-landscape.png
rtk proxy sips -r 270 .context/workout-landscape.png
```

On the simulator runtimes used during development, a landscape interface could
still be emitted in the hardware-native portrait pixel buffer. Inspect the raw
image before rotating; use 90 instead of 270 when the interface is turned the
other direction.

Review portrait and landscape separately. For a board change, capture inactive
and highlighted surface, shelf, deep-recess, and shallow-recess states. For a
routine change, preview every distinct hold target and finger cue.

## Validate changed behavior

Use the [runtime-service contract](IOS_RUNTIME_SERVICES.md) to choose the affected
checks. Common review cases are:

- Initial countdown, running/paused step selection, skip countdown cancellation,
  final-step completion and background pause.
- Spoken start/final-three/completion cues, speaker disabling and audio ducking.
- Portrait/landscape rotation with stable clock, grip and contact state.
- Stopwatch Start/Stop/Resume, pause accumulation and finalization on navigation
  or rest; never-started work must retain an omitted observed duration.
- Log session with the selected board and ordered work/rest records; End session
  must not log a completion.
- Health permission requested only by Connect Apple Health, plus authorization,
  local fallback, source and error states after Settings/scene refresh.

A local History row is not evidence of a HealthKit save or import. Use
`WorkoutHistoryServiceTests` and `AppStoreTests` for reconciliation and inspect
actual HealthKit records on a signed device. Empty readable history is ambiguous;
preserve pending local records and never infer denied read access from it.
Simulator sensor fixtures do not validate radio or force accuracy. Cross-device
Health restoration and physical-scale behavior require device review.

For HealthKit review, inspect the simulator's effective
`HangTen.app-Simulated.xcent` in workspace DerivedData and verify
`com.apple.developer.healthkit = true`. Check the installed usage descriptions:

```sh
app_path="$(rtk proxy xcrun simctl get_app_container <uuid> com.hangten.training app)"
rtk proxy /usr/libexec/PlistBuddy -c 'Print :NSHealthShareUsageDescription' "$app_path/Info.plist"
rtk proxy /usr/libexec/PlistBuddy -c 'Print :NSHealthUpdateUsageDescription' "$app_path/Info.plist"
```

Both values must be nonempty. Compile-only unsigned builds do not validate this
permission flow. Keep the exact app revision, review findings and necessary
screenshots with the change; raw commands/logs belong in workspace `.context`.

## Cleanup

The creation trap calls `scripts/paseo-resource-cleanup.sh archive`; leave
it installed for the whole validation. The created UUID is written to the
pending manifest before the owned manifest so the archive mode can retry cleanup
after an interrupted setup. Archive cleanup verifies each pending or owned
manifest entry against the exact `Hang Ten Paseo $workspace_name `
name prefix, shuts down the matching device if necessary, and runs
`rtk proxy xcrun simctl delete` on that exact UUID. Pending state is removed only after
archive cleanup succeeds; the direct delete fallback is limited to a validated
UUID whose pending record could not be written, and it must re-query that exact
UUID, parse the exact device-name field, and require the exact
`Hang Ten Paseo $workspace_name ` marker before deleting. If the
lookup or ownership check fails, it does not delete and returns failure. This is
immediate workspace cleanup, while the Paseo workspace archive hook is a failsafe for
an abandoned workspace; both manifests remain available for archive retry.

Do not delete or shut down a shared/unknown simulator. The cleanup script must
not receive an unrecorded UUID or a simulator without the exact workspace
ownership marker.
