# iOS runtime services

This document records the runtime behavior that spans the workout UI, audio,
orientation, and Apple Health. Use it with the isolated simulator guide when
changing any of those systems.

## Workout clock and spoken cues

`WorkoutView` uses one elapsed session clock backed by monotonic system uptime.
`TimelineView` samples it four times per second but is not the time source,
while each `WorkoutStep.duration` determines the active step. Pause stores
elapsed time; resume starts from that value. A new routine starts three seconds
in the future, which makes the initial 3-2-1 countdown part of the same clock
instead of a second timer.

Stopwatch start, pause, display, and finalization use that same monotonic uptime
source. `Date` remains only the absolute start timestamp and is paired with the
monotonic elapsed duration to derive the completed HealthKit interval, so wall
clock adjustments cannot change observed activity durations.

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
- skip countdown 5, 4, 3, 2, 1;
- the current minute/task start;
- the final 3, 2, 1 of a fixed segment;
- an explicit rest transition for routines with a fixed rest segment;
- session complete.

Skip countdown keys are stable and speak each number once before the
destination step's start cue.

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
step's start. Skipping a non-final step seeks to the next step's start, then
schedules a five-second 5-4-3-2-1 countdown before that step begins
automatically. This happens from both running and paused sessions; the session
is running after the countdown. During the countdown, Routine and Skip step
are disabled and board/grip cues remain inactive. Cancelling or interrupting
the countdown leaves the destination step paused and preserves the original
session start. Skipping the final step still reaches completion immediately
without a countdown.

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

The app writes completed routines as `HKWorkout` records with activity type
`.functionalStrengthTraining`. It does not request read access.

Required configuration:

- `HealthKit.framework` linked by the target;
- `HangTen/HangTen.entitlements` with
  `com.apple.developer.healthkit = true`;
- `NSHealthUpdateUsageDescription` in generated Info.plist settings;
- a user-initiated Connect Apple Health button.

`HealthKitService.requestAuthorization` requests sharing permission for the
workout type. `HealthAuthorizationState` drives the Progress card:

- unavailable: Health data is not available;
- not determined: show Connect Apple Health;
- denied: explain the state and open app settings;
- authorized: completed routines save automatically.

`saveCompletedWorkout` uses `HKWorkoutBuilder`: begin collection, attach Hang
Ten plan metadata, end collection, then finish the workout. It runs only when
authorization is granted and the end date is later than the start date.
Every builder stage reports failure back to `AppStore`; the local session stays
logged, while the Progress card explains that the Health write failed. The
saved interval keeps the session's original start date and ends at the earlier
of the planned active-duration end or the athlete's Log session time. This
prevents an early completion from writing a future HealthKit end date.

The denied-state button is labeled Open app settings because iOS does not
provide a public deep link to the exact Health permission row. Authorization
state refreshes whenever the Progress scene becomes active again.

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
  repeat HealthKit writes on a physical device before release.
- Verify audio with the simulator unmuted and once while other audio is playing
  to confirm ducking behavior.
- Rotate during countdown, running, and paused states.
- Lock the simulator or background the app during a session; verify that it
  pauses and does not skip an audio transition.
- For a stopwatch step, verify the `workout.stopwatch` value is `00:00` before
  start, `workout.stopwatch.toggle` is labeled “Start stopwatch,” the control
  changes to “Stop stopwatch” while running, and the stopped observed value is
  retained.
