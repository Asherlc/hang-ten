# Audio Session Launch Containment Design

## Goal

Hang Ten must not create or prewarm countdown audio playback when its root view
is constructed. Background audio must be affected only after the athlete starts
a countdown with audio cues enabled.

## Root-cause evidence

`RootView` owns a long-lived `WorkoutAudioCoach`. The coach initializer calls
`beginCountdownPrewarm()`. With the bundled countdown pack, that prewarm
synchronously prepares `SystemCountdownAudioBufferPlayback`, which owns an
`AVAudioEngine`. The work happens during ordinary app launch, before a workout
or countdown exists. `stop()`, cancellation, and countdown completion then
prewarm again after stopping playback, recreating the same unnecessary audio
work while other-app audio should be restored.

## Required behavior

- A new `WorkoutAudioCoach` begins in an idle countdown-preparation state and
  does not invoke its countdown scheduler.
- `WorkoutView` requests preparation only after an athlete initiates an
  audio-enabled initial or skip countdown.
- A requested countdown waits for preparation to resolve; a failed preparation
  still starts the visual countdown without live numeric-speech fallback.
- Stopping, cancelling, or completing countdown playback returns the coach to
  idle without automatically prewarming the audio engine.
- Existing scheduled countdown, speech-session activation, and
  `notifyOthersOnDeactivation` behavior remains unchanged.
