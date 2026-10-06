# iOS runtime services

This reference covers navigation, scale tracking, workout timing, audio,
orientation, recording and Apple Health. Use the
[isolated simulator guide](IOS_SIMULATOR_VALIDATION.md) for review commands.

## Navigation and reports

Train is the default tab, with the selected board and favorite plans. Both
`train.changeBoard` and `plans.changeBoard` open the full-page board picker;
`boardPicker.board.<BoardRevision.id>` persists the choice and returns to the
originating tab. `train.settings` opens Settings. History opens the chronological
list of detailed local sessions.

Board detail and active workouts expose Report a problem through
`boardDetail.reportProblem` and `workout.reportProblem`. Configured Sentry User
Feedback receives the user's message, optional typed email, and ID tags
(`report_source`, `board_id`, optional `hold_id`, `plan_id`, `step_id`). Without
Sentry configuration, submission is a no-op.

DEBUG review routes can open tabs, board detail, Settings and visual fixtures.
Release ignores those routes; see the simulator guide for supported variables.

Plans uses native focus browsing, All workouts, and My routines. Focus is
optional source-audited editorial metadata; unsupported categories and empty
compatible focus destinations are hidden. See
[the chooser classification audit](WORKOUT_CHOOSER_CLASSIFICATION_AUDIT_2026-10-05.md).
Search preserves catalog order and matches names, descriptions, and displayed
labels. Results expose actual exercise content separately from training goals.
Duration is marked approximate for variable or untimed routines.

The filter sheet stages duration, exercise, and difficulty choices until Show
workouts is tapped; Cancel discards the draft. Filter groups combine with AND,
and exercises/difficulties allow any selected value within their group. Duration
ranges are under 10 minutes, 10 to under 20 minutes, and 20 minutes or more.
Removing applied filters or clearing them leaves the current focus unchanged.
At accessibility text sizes, board names and workout titles use the full row
width, with the favorite action below the workout. The filter action uses a
shorter label and exposes its matching count to accessibility. Empty My routines
offers routine creation; a search or filter with no matches retains refinement
guidance. Difficulty choices follow Entry, Beginner, Intermediate, and Advanced,
followed by other difficulty labels in alphabetical order.

## Scale and manual tracking

On plan detail, Weight tracking defaults to Skip. Manual retains the entered
weight, unit and Add bodyweight choice. Scale permits explicit profile selection,
discovery, connection and disconnection before Start routine. Bluetooth
permission follows that user action. Start remains available when the scale is
unavailable; the workout records the Scale choice without fabricated samples.
Deep links have no plan-page setup state and default to Skip.

The tracking choice is snapshotted at Start and retained across the purchase
sheet. Skip and Manual omit scale preparation, the meter and samples; an unused
scale disconnect does not interrupt them. Scale activates tracking only when
initial preparation completes or is explicitly skipped. A scale that begins
streaming after an unprepared start is ignored for that session. Manual and
Skip persist the neutral Automatic profile, keeping configured scale state out
of those records.

The Motherboard profile scans its service, enables TX notifications, requests
four-sensor calibration and starts the 30 Hz stream after complete calibration.
Its parser handles fragmented or combined CRLF rows and 16-byte hex packets;
a 4,096-byte buffer cap clears overflow and reports an error. Calibration maps
ADC values to kgf; Tare subtracts current per-sensor values. Loaded-time recording
uses notification timestamps, threshold, release ratio, debounce and merge gap.
Rest is unmeasured, and the workout clock remains the planned-time authority.
Setup parser errors are fatal. During streaming, two consecutive parser errors
are tolerated; the third clears transient measurements/calibration and exposes
an error while leaving timer controls usable. A valid frame resets that streak.

Motherboard's UART UUIDs, calibration format and commands are reverse-engineered,
not an official SDK or certified force measurement. For compatibility with the
unofficial `hangtime-grip-connect` reference, the first three channels represent
left, center and right; center/right are negated before tare, and center is split
between the two displayed sides. The fourth channel participates in calibration
and tare but remains diagnostic-only. These wiring assumptions require physical
device validation after firmware changes. Other supported profiles use their
own adapters and capabilities.

Completed detailed sessions retain at most 20,000 eligible raw measurements and
record truncation when further samples are dropped. `WorkoutSessionStore` keeps
the 20 newest detailed sessions.

`HANGTEN_REVIEW_MOTHERBOARD=1` substitutes a deterministic DEBUG transport that
sends calibration and raw frames through the real service and recorder paths.
Combine `HANGTEN_REVIEW_SENSOR_DISCONNECTED=1` to exercise an explicit Connect
action. The fixture validates app integration, not radio permissions, GATT,
firmware, disconnect timing or measurement accuracy. Release always uses the
CoreBluetooth transport.

## Workout clock, audio and navigation

`WorkoutView` uses a monotonic system-uptime clock; `TimelineView` samples it
four times per second. Pause retains elapsed time and Resume starts from that
value. The initial three-second countdown shares the same clock. Stopwatch
start, pause, display and finalization also use uptime; absolute dates identify
the completed session interval and cannot change elapsed duration.

A visible workout disables the idle timer. Scene inactivity, lock or background
entry pauses the workout and stops audio. Returning requires explicit Resume.

`WorkoutAudioCoach` configures `.playback` / default mode / `.duckOthers` and
persists the speaker preference. Numeric 3-2-1 buffers are prepared ahead of the
monotonic boundary and scheduled together using host time. Reviewed bundled
countdown audio is preferred; unavailable bundled buffers select Apple's PCM
speech renderer during preparation. Empty voice renders have bounded prewarm
retries. Failed preparation leaves numeric cues silent rather than speaking them
late. Nonnumeric cues use normal speech synthesis.

Initial and skip countdowns wait for preparation. Fixed segments arm final-three
audio at the preceding 4 tick; a following fixed segment of three seconds or less
joins the same schedule. Stable audio-moment keys prevent repeat playback on
timeline ticks. Pause, cue disabling and dismissal cancel scheduled audio;
speech teardown waits for its delegate before deactivating the audio session.
The reviewed audio authoring process lives in
[CountdownAudio/README.md](../HangTen/Resources/CountdownAudio/README.md).

New sessions begin at step 1. Routine selection and Skip are disabled through
the initial countdown. Selecting another step rebases elapsed time to its start,
preserving running or paused state; selecting the current step is a no-op.
Skipping a nonfinal step moves to the next start and runs a five-second countdown
before that step, including when initiated while paused. During that countdown,
controls and hold/grip cues are inactive. Cancellation or scene interruption
leaves the destination paused. Skipping the final step completes immediately.
Every seek stops old speech and reanchors cues to the new elapsed position.

Official Metolius source-cycle steps keep `timedWorkDuration == nil`: speech says
“Begin minute …” and the athlete completes all listed tasks, then rests within
that minute. The generic adapted expansions instead expose guided task and rest
steps. Never derive a rest boundary from the first hang in a multi-task source
cycle. See [routine authoring](ADDING_A_ROUTINE.md).

When `fingerConfiguration` is omitted, hand cues display index, middle, ring and
pinky with `4 fingers (assumed)`. Explicit selections override this display
default. The fallback is not a sourced prescription and does not populate the
omitted routine or recorded field. See [the grip hand contract](grip-hand-model.md).

## Activity recording and local history

Completion records the exact selected `BoardRevision`. Source-backed plan
predicates resolve against its factual contacts and applicable position; catalog
plans do not contain contact IDs. Athlete-authored custom routines may select
exact contacts. Resolution failure does not substitute a hold or broaden a
predicate. Explicit self-selected work records that choice without an invented
contact snapshot.

Resolved work retains board/revision identity, optional model hash, the factual
requirement or per-hand targets, resolved contact IDs and applicable position.
Ordered source segments remain ordered records. Rest has identity and duration
but no target. Fixed work stores prescribed active duration; stopwatch work
stores observed active seconds. Never-started stopwatch and genuinely untimed
work omit duration.

Stopwatch controls begin at `00:00` and expose Start, Stop and Resume. They do
not advance the enclosing workout clock. Workout pause or scene interruption
pauses a running stopwatch. Entering rest, navigating, skipping, logging or
dismissing finalizes its value; revisiting the step retains that stopped value.

Log session creates a detailed local record through `WorkoutSessionStore` and
passes a pending record to `WorkoutHistoryService` for optional HealthKit sync.
The local detailed History list is distinct from the HealthKit-derived progress
snapshot, so a visible History row does not prove a HealthKit save or import.
End session dismisses without completion logging or a HealthKit write.

## Apple Health authorization and synchronization

Only Connect Apple Health requests workout read/write authorization. Settings
appearance and scene activation refresh sharing status without prompting.
`HangTen.healthAuthorizationRequested.v1` gates history queries and uploads;
refreshing an already-authorized sharing status also reconciles a missing flag
and enables sync. Before either event, initialization and completion use local
fallback history.

The target requires `HealthKit.framework`, the
`com.apple.developer.healthkit = true` entitlement, and nonempty
`NSHealthShareUsageDescription` / `NSHealthUpdateUsageDescription` values. The
read description explains restoration of progress on a new device.

Accepted HealthKit records must have functional-strength activity type, brand
`Hang Ten` and a nonempty `HangTen.PlanName`. New writes include the pending
UUID as `HangTen.SessionID`; this is the primary reconciliation key. Legacy
records can match normalized plan title and exact start/end dates, and the
HealthKit workout UUID is retained for retry reconciliation.

Pending/fallback records use `HangTen.pendingWorkoutHistory.v2`. They are written
locally before HealthKit upload and removed only after a readable query confirms
a matching workout. Successful uploads retain their HealthKit UUID while read
privacy hides them; failures remain retryable and do not discard local history.
An empty query is ambiguous and does not prove denied read access or no workouts.
Readable accepted HealthKit records govern the synced progress snapshot. Hang
Ten has no network history synchronization.

The Apple Health card uses sharing/write authorization for its status; Connected
does not establish readable history. The action mapping is:

| Sharing state | Status | Action |
| --- | --- | --- |
| unavailable | Unavailable | none |
| not determined | Not connected | Connect Apple Health |
| denied | Access denied | Open app settings |
| authorized | Connected | Open app settings for local fallback; otherwise none |

History source is displayed separately as synced, syncing, local fallback or
unavailable. The unavailable source alone does not create an action. Query/write
errors appear in the Health card while keeping local records. Returning from
system app settings refreshes status and enabled history without a new prompt.

Health writes use `HKWorkoutBuilder` to begin collection, add Hang Ten metadata,
end collection and finish. The workout retains its functional-strength type,
plan title, session interval, board ID/name and `HangTen.ActivitySegments.v2`
metadata. That versioned JSON rejects unknown fields and omits unsupported
values. Every builder stage reports failures. Saves require write authorization
and a positive interval; the end is capped at the earlier of planned active end
or Log session time so early completion cannot write a future end date.

## Orientation and validation

The target supports portrait and both landscape orientations on iPhone, and all
orientations on iPad. Layout follows actual view dimensions and shares workout
state, so rotation preserves time, pause state and highlights. DEBUG orientation
routes request scene geometry; production follows device/user orientation.

Use an owned simulator to review countdown, seek/skip, stopwatch, background
pause, both layouts, explicit and assumed finger cues, local logging, End
session, and Health authorization/source/error states. Run affected focused
tests rather than treating a build as behavioral validation.

Compile-only builds may disable signing; Health permission reviews require the
simulator signature and effective HealthKit entitlement. Simulator `codesign`
output can be empty while `HangTen.app-Simulated.xcent` retains the entitlement.
For a device app, inspect it with:

```sh
rtk proxy codesign -d --entitlements :- <path-to-HangTen.app>
```

Repeat radio/force checks, HealthKit writes and cross-device restoration on
signed physical devices before release. Review audible timing with audio enabled
and alongside other audio to verify ducking. Simulator fixtures and UI tests do
not establish device measurement accuracy or cross-device Health restoration.
