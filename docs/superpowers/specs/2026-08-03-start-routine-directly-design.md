# Start Routine Directly from Plan Detail

## Context

The plan-detail screen currently labels a navigation link as “Start routine,”
but the link only opens `WorkoutView`. The newly opened workout still waits for
another tap on its own “Start routine” control before beginning the existing
three-second countdown. This makes the primary call to action require two taps.

## Goal

Make the plan-detail “Start routine” action open the workout screen and begin
the existing three-second countdown immediately. The countdown must remain part
of the existing session clock, so step 1, audio cues, hold highlights, pause,
and completion continue to use the same timing behavior.

## Non-goals

- Do not remove or rename the workout screen’s manual start/resume control.
- Do not change the countdown duration or audio phrases.
- Do not alter routine definitions, board mapping, persistence, or HealthKit
  behavior.
- Do not make every route into `WorkoutView` auto-start; debug review and any
  future manual-entry route should retain the current idle state unless they
  explicitly opt in.

## Recommended approach

Add an opt-in start intent to `WorkoutView`:

```swift
WorkoutView(plan: plan, startsImmediately: true)
```

The parameter defaults to `false`, preserving existing call sites. The
plan-detail navigation link is the only production caller that opts in. On the
workout’s first appearance, a one-shot guard checks the opt-in flag and the
current unstarted state before calling the existing `toggleRunning()` method.
That method remains the single owner of starting the session and assigning the
three-second-future start date.

The guard must also prevent repeated SwiftUI `onAppear` events from resetting
the countdown. A pure session-start policy helper will express and test the
decision, using the opt-in flag, the one-shot guard, and the current
`startedAt`/session state.

## Data flow

1. The user taps “Start routine” in `PlanDetailView`.
2. The existing navigation transition presents `WorkoutView` with
   `startsImmediately == true`.
3. `WorkoutView` performs its normal review-route/setup work, then evaluates
   the one-shot auto-start policy.
4. The policy permits the first auto-start because the session has not started.
5. `toggleRunning()` sets the same `routineStartedAt` and `startedAt` values it
   uses for a manual start, with `startedAt` three seconds in the future.
6. `TimelineView` observes the shared elapsed clock. During the countdown,
   step navigation and “Skip step” remain disabled; after it reaches zero,
   normal workout controls and audio cues proceed unchanged.

All other `WorkoutView(plan:)` call sites use the default `false` value. The
existing DEBUG `HANGTEN_REVIEW_AUTOSTART` route remains supported and must not
cause a second start when the explicit start intent has already run.

## Error and lifecycle handling

- If the workout is already started when `onAppear` runs, the auto-start path is
  a no-op.
- If SwiftUI invokes `onAppear` more than once, the one-shot guard makes later
  invocations a no-op.
- Manual pause, resume, cancellation of the countdown, interruption handling,
  completion, and destructive ending continue through their existing paths.
- No new timer or independent countdown is introduced.

## Testing and validation

Before the production change, add a failing XCTest for the pure auto-start
decision. It must cover the opt-in first appearance, repeated appearance,
already-started state, and the default non-auto-start route. Implement the
smallest production change that makes the test pass, then run the full XCTest
suite.

On a dedicated iOS Simulator, launch the DEBUG plan-detail review route and
tap the visible “Start routine” action. Verify that one tap reaches the workout
screen and immediately shows the existing countdown state (including the
“Cancel countdown” control), without requiring a second tap. Also verify that
the direct workout review route still opens idle, and that the existing
countdown, pause/resume, audio, portrait, and landscape behavior is unchanged.
