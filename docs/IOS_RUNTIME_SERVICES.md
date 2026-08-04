# iOS runtime services

This document records the runtime behavior that spans the workout UI, audio,
orientation, and Apple Health. Use it with the isolated simulator guide when
changing any of those systems.

## Workout clock and spoken cues

`WorkoutView` uses one elapsed session clock. `TimelineView` samples it four
times per second, while each `WorkoutStep.duration` determines the active step.
Pause stores elapsed time; resume starts from that value. A new routine starts
three seconds in the future, which makes the initial 3-2-1 countdown part of
the same clock instead of a second timer.

While a workout is visible, Hang Ten disables the idle timer. If the scene
becomes inactive because the device locks or the athlete switches apps, the
routine pauses and stops speech instead of letting the clock cross silent cue
boundaries while iOS suspends the app. Returning to the app requires an
explicit resume.

`WorkoutAudioCoach` wraps `AVSpeechSynthesizer` and configures
`AVAudioSession` as `.playback` with `.spokenAudio` and `.duckOthers`. The
speaker preference is persisted with `@AppStorage`. When an utterance ends or
the routine pauses/exits, the audio session deactivates with
`.notifyOthersOnDeactivation` so other audio is no longer ducked.

Audio moments are derived from clock state:

- initial 3, 2, 1;
- the current minute/task start;
- the final 3, 2, 1 of a fixed segment;
- an explicit rest transition for routines with a fixed rest segment;
- session complete.

Metolius task-cycle steps intentionally have `timedWorkDuration == nil`.
Speech says “Begin minute …” and the full minute remains visible because the
athlete completes all listed tasks, then rests for the remainder. The app must
not announce a fabricated rest boundary after the first numeric hang.

When adding audio, make the audio moment `Hashable` and stable for its whole
window so SwiftUI's `onChange` speaks once rather than on every timeline tick.
Stop speech on view dismissal and when the user disables cues.
For a three-second segment, speak the short start command and the complete
3-2-1 as one utterance; do not let periodic view updates interrupt or skip a
count in such a short interval.

## Workout step navigation

A new workout session starts at step 1. Step selection and Skip step are
disabled until the initial three-second countdown has finished, and remain
disabled while that countdown is running.

The Routine sheet lets the athlete select any other step directly. A running
seek rebases the elapsed clock at the selected step's start and stays running;
a paused seek replaces the paused elapsed position and stays paused. Selecting
the current step is a no-op. Skip step seeks to the end of the current
`WorkoutStep`, including its timed rest interval, so it advances to the next
step's start; skipping the final step reaches the existing completion state.

Every seek stops the active audio utterance and re-anchors audio to the new
elapsed position. The normal cue for the selected step can therefore play once
without a stale cue continuing from the prior step.

## Completed activity recording

The completion handoff records the exact `TrainingBoard` selected for the
session. `WorkoutView` passes that board together with the plan and finalized
stopwatch values to `AppStore`; the recorder does not substitute a default
board or infer one from the plan. Each work target is resolved against that
board through the same semantic, ID, and fallback mapping used by the board
highlights. Recorded work therefore carries the resolved physical hold IDs,
the hold kind (`edge`, `pocket`, `sloper`, or `jug`), and the board's explicit
`sizeMillimeters` value when present. Physical size is never parsed from a
display name. Matching left/right holds are grouped only within their source
segment; separate repetitions remain separate records.

The recorder preserves the routine's ordered `RecordedActivitySegment` values.
Work and rest are separate segments: rest carries its step identity and
duration but no hold metadata. A fixed work duration is the prescribed active
duration and excludes rest. A stopwatch work duration is the athlete's
observed active seconds, including any start/stop and pause/resume accumulation.
If a stopwatch was never started, its duration is omitted. Genuinely untimed
work also omits duration; the app never invents one from the surrounding cycle.

Stopwatch activities expose a count-up control in both portrait and landscape.
The control shows `00:00` before start, has explicit Start, Stop, and Resume
states, and does not alter the enclosing workout clock. A normal workout pause
or scene/background interruption pauses a running stopwatch without finalizing
it. The current stopwatch is finalized when the athlete crosses into rest,
navigates to another step, skips a step, completes/logs the session, or
dismisses the workout. A stopped value remains stable when revisiting the step.

The completed `HKWorkout` keeps the existing title, functional-strength
activity type, and session date interval. Its custom metadata includes
`HangTen.PlanName`, `HangTen.BoardID`, `HangTen.BoardName`, and
`HangTen.ActivitySegments`. The last value is versioned JSON with
`{"version":1,"segments":[...]}`; optional fields are omitted rather than
encoded as fabricated values. The metadata is attached during the existing
`HKWorkoutBuilder` sequence. There is no local activity database: the
completed HealthKit workout metadata is the activity source of record. A
metadata or HealthKit write failure keeps the local completion and surfaces the
existing Health error state.

The completed “Log session” path records the activity. The destructive “End
session” path still dismisses without marking the routine complete and without
writing an Apple Health workout.

## Portrait and landscape

The target supports portrait, landscape-left, and landscape-right on iPhone,
and all orientations on iPad through generated Info.plist settings in
`HangTen.xcodeproj/project.pbxproj`.

`WorkoutView` switches layouts from actual `GeometryReader` dimensions. The
landscape layout keeps the board centered, mirrors the left/right hand cue
cards around it, and moves the timer and cue text into available horizontal
space. It does not keep a separate workout state, so rotation must not reset
the timer, current minute, pause state, or highlights.

`HANGTEN_REVIEW_LANDSCAPE` requests scene geometry only in DEBUG. Production
orientation remains user/device controlled.

## Apple Health authorization

Hang Ten uses `HKObjectType.workoutType()` for both HealthKit sharing (write)
and reading. Authorization is requested only by the visible Connect Apple
Health action. Progress appearance and scene-activation refreshes may update
the sharing status without presenting an authorization sheet or prompting;
they query HealthKit history only after the persisted request flag is enabled.

`HangTen.healthAuthorizationRequested.v1` gates history synchronization. Until
the user taps Connect Apple Health and that flag is persisted, initialization,
Progress appearance, scene activation, and completion logging use only the
local `UserDefaults` history fallback. No HealthKit workout-history query,
workout save, or migration occurs on that path. The app may still read the
HealthKit sharing status for the authorization pill. Connect enables HealthKit
sync as it persists the flag, before requesting authorization. Once the flag is
true, refresh and completion reconciliation may query HealthKit, upload pending
records, and migrate matching history.

Required configuration:

- `HealthKit.framework` linked by the target;
- `HangTen/HangTen.entitlements` with
  `com.apple.developer.healthkit = true`;
- `NSHealthShareUsageDescription` in generated Info.plist settings with the
  value `Hang Ten reads your Apple Health workout history to restore your
  progress on a new device.`;
- `NSHealthUpdateUsageDescription` in generated Info.plist settings;
- a user-initiated Connect Apple Health button.

`HealthKitService.requestAuthorization` requests both read and write
permission for the workout type. HealthKit query results are filtered before
they become history. Hang Ten imports only records that have all of the
following:

- activity type `.functionalStrengthTraining`;
- the exact `HKMetadataKeyWorkoutBrandName` value `Hang Ten`;
- a non-empty `HangTen.PlanName` metadata value.

New records include the plan title and a `HangTen.SessionID` metadata value
equal to the UUID of the local pending record created for that session. This
stable ID is the primary reconciliation key. Older Hang Ten records without
`HangTen.SessionID` remain importable when their normalized plan titles match
(surrounding whitespace trimmed) and their start and end dates match exactly.
A HealthKit workout UUID is also kept for retry reconciliation. Matching
records are deduplicated so a migrated local session and its HealthKit workout
count as one session.

HealthKit-derived history is authoritative whenever an accepted Hang Ten
workout is readable. Local `UserDefaults` records under
`HangTen.pendingWorkoutHistory.v1` are pending/fallback records, not a
permanent mirror. Hang Ten writes the local record before attempting the
HealthKit save. After Connect Apple Health grants authorization, pending
records are uploaded and retained until a later HealthKit query confirms them;
unmatched local records remain visible while they are pending. A successful
upload that is still hidden by read privacy remains marked as attempted, so a
later refresh does not save a duplicate. There is no network history sync.

An empty HealthKit query result is ambiguous because Apple hides denied read
access in the same way as a genuinely empty readable result. The app must not
interpret an empty result as proof that no workouts exist or that access was
denied. It retains local pending records and uses them as fallback until a
readable HealthKit result can reconcile them.

`HealthAuthorizationState` drives the authorization portion of the Progress
card. Its current status copy is:

| State | Label | Detail | Action |
| --- | --- | --- | --- |
| unavailable | `Unavailable` | `Apple Health is not available on this device.` | none |
| not determined | `Not connected` | `Connect once to save completed routines as functional strength workouts.` | `Connect Apple Health` |
| denied | `Access denied` | `Workout access is off. You can enable it for Hang Ten in Settings.` | `Open app settings` |
| authorized | `Connected` | `Completed routines will be saved automatically to Apple Health.` | `Connect Apple Health` when `hasRequestedHealthAuthorization == false` or a successful refresh yields an empty `.healthKit` snapshot; `Open app settings` for `.localFallback`; none when accepted HealthKit history is visible |

The authorization state reflects the workout sharing/write state exposed by
HealthKit; `Connected` does not prove that workout reads are visible, and
HealthKit does not expose a separate readable-history authorization state. The
Progress action combines this state with the persisted
`hasRequestedHealthAuthorization` flag and the history source. Before the
request flag is true it offers Connect Apple Health. After a request, local
fallback maps to Open app settings, a successful empty `.healthKit` snapshot
keeps Connect Apple Health available as a conservative recovery action, and
visible accepted HealthKit history has no action. Denied and unavailable
behavior remains as shown in the table.

The `.unavailable` history source does not create an action by itself. In
`RootView.healthAction`, any Connect or Settings action shown alongside that
source comes from the current authorization state or persisted request state;
an unavailable history source alone has no action.

The history source copy is:

- `.healthKit`: `History synced from Apple Health.`
- `.localFallback`: `History stored on this device until Apple Health is connected.`
- `.syncing`: `Syncing Hang Ten history with Apple Health…`
- `.unavailable`: `Apple Health history is unavailable; completed sessions stay on this device.`

If a completion cannot sync, the Progress card reports
`Session was saved locally and will retry Apple Health sync.` If a refresh
cannot sync, it reports `Apple Health history could not sync. Local history
remains available.` A request error supplied by HealthKit is shown using its
localized description. These errors do not discard the local record.

`saveCompletedWorkout` uses `HKWorkoutBuilder`: begin collection, attach Hang
Ten brand, plan, and session metadata, end collection, then finish the
workout. It runs only when write authorization is granted and the end date is
later than the start date.
Every builder stage reports failure back to `AppStore`; the local session stays
logged, while the Progress card explains that the Health write failed. The
saved interval keeps the session's original start date and ends at the earlier
of the planned active-duration end or the athlete's Log session time. This
prevents an early completion from writing a future HealthKit end date.

The denied-state button is labeled Open app settings because iOS does not
provide a public deep link to the exact Health permission row. Authorization
status refreshes whenever Progress appears or its scene becomes active again.
History refreshes at those lifecycle points only after the request flag is
true; before then, the app reloads the local fallback. Returning from Settings
therefore refreshes status and, when enabled, history without prompting.

Do not trigger Health authorization at launch. Apple permission sheets must
follow a clear user action. Do not mark a routine complete or save a workout
when the user confirms “End session”; only the completed “Log session” path
records it.

## Validation notes

- Compile-only simulator builds can disable signing; Health permission tests
  cannot.
- Inspect the built app entitlement when HealthKit behaves as unavailable or
  fails silently. A device archive can be inspected with:

  ```sh
  codesign -d --entitlements :- <path-to-HangTen.app>
  ```

  For an iOS Simulator build, Xcode can emit the effective entitlement as an
  intermediate `HangTen.app-Simulated.xcent` while the final simulator app's
  `codesign` output remains empty. Locate that file under the target's Derived
  Data intermediates and verify it contains
  `com.apple.developer.healthkit = true`.

- Exercise permission states and completion on a dedicated simulator, then
  repeat HealthKit writes on a physical device before release. A simulator can
  validate the permission flow and entitlement, but cross-device HealthKit
  restoration must be tested on physical devices using the same HealthKit
  account; Hang Ten does not provide network synchronization.
- Verify audio with the simulator unmuted and once while other audio is playing
  to confirm ducking behavior.
- Rotate during countdown, running, and paused states.
- Lock the simulator or background the app during a session; verify that it
  pauses and does not skip an audio transition.
- For a stopwatch step, verify the `workout.stopwatch` value is `00:00` before
  start, `workout.stopwatch.toggle` is labeled “Start stopwatch,” the control
  changes to “Stop stopwatch” while running, and the stopped observed value is
  retained.
