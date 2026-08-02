# iOS runtime services

This document records the runtime behavior that spans the workout UI, audio,
orientation, and Apple Health. Use it with the isolated simulator guide when
changing any of those systems.

## Motherboard Bluetooth sensor

The optional Motherboard sensor is a live force input, not a workout timer.
The user explicitly taps Connect sensor in Progress; the app then scans for
the Bluetooth service, connects, enables TX notifications, requests the
device's calibration rows, and starts its 30 Hz stream only after complete
four-sensor calibration. iOS Bluetooth permission therefore follows a clear
user action on physical devices rather than an automatic production launch.

Notifications may be fragmented or contain more than one line. The service
buffers them until CRLF-delimited calibration rows, stream acknowledgements,
or 16-byte hex raw packets can be parsed. Calibration maps each sensor's ADC
values to kgf, and Tare subtracts the current per-sensor reading. The workout
recorder uses the notification timestamp and the configured kgf threshold,
release ratio, debounce, and merge gap to calculate loaded intervals; the
workout clock remains the authority for planned time. Rest steps stay
unmeasured. A disconnect or parser error clears the transient measurement and
calibration state, records the unavailable/error state, and leaves the workout
timer controls usable. Completed summaries can therefore include both measured
and unmeasured steps.

The UART-style service UUIDs, calibration-row format, stream commands, and raw
packet layout are reverse-engineered from observed Motherboard behavior. They
are not an official manufacturer SDK or protocol guarantee. Do not treat the
displayed load as a certified measurement, and revalidate against the physical
device after firmware changes.

`HANGTEN_REVIEW_MOTHERBOARD=1` is a DEBUG-only simulator review route. It
selects Progress and replaces the CoreBluetooth transport with a deterministic
fixture that sends real calibration and raw notification frames through
`MotherboardBluetoothService`. Its deterministic unloaded, loaded, peak, and
released pattern repeats while streaming, but every raw notification is stamped
when it is delivered so a routine started after launch can be recorded. The
same service, meter, settings, threshold, and recorder paths are exercised
without system Bluetooth. Release builds always construct
`CoreBluetoothMotherboardTransport` regardless of that environment variable.
The fixture does not validate radio
permissions, discovery, GATT behavior, device calibration accuracy, firmware
compatibility, disconnect timing, or force accuracy; all of those require a
physical Motherboard before release.

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
saved interval is the plan's active duration from its actual start, excluding
manual pause time and any delay before the athlete taps Log session.

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
