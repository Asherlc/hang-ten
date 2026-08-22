# Sample-accurate countdown audio

## Goal

Make each spoken countdown number begin on its planned one-second boundary. A late number is incorrect; audio must never queue behind an earlier countdown number.

## Decision

Replace live `AVSpeechSynthesizer.speak(_:)` playback for numeric countdown cues with a countdown-specific audio player. It prepares the three numeric voice cues before a countdown begins, retains one audio session for the entire sequence, and schedules the prepared PCM buffers against one `AVAudioEngine` host-time timeline.

The existing monotonic workout clock remains the source of the visual deadline. The player receives the same start instant and schedules the complete remaining sequence before the first cue is due. It must not schedule individual numbers from SwiftUI timeline ticks or audio completion callbacks.

## Scope

- Countdown numbers `3`, `2`, and `1`, including initial, skip, and final segment countdowns.
- Preserve the user's current preferred-language voice, rate, pitch, and volume when rendering the numeric buffers.
- Keep the existing spoken-audio AVAudioSession category, mode, ducking behavior, explicit stop behavior, and notification-aware deactivation.
- Cancel all scheduled countdown buffers immediately when the workout pauses, exits, or audio cues are disabled.
- Remove the deferred-deactivation workaround; it is neither the timing authority nor required once one countdown session owns the complete sequence.

## Non-goals

- Do not change workout timing, the visual timer, cue phrases, board state, or other workout audio behavior.
- Do not queue a live speech utterance as a fallback after a scheduled cue deadline has passed.
- Do not use completion handlers as a mechanism to schedule the following cue.

## Acceptance criteria

1. Starting a countdown schedules every remaining numeric cue before playback begins, with exactly one-second host-time spacing.
2. Repeated SwiftUI updates for the later `2` and `1` values do not enqueue duplicate audio.
3. Cancellation clears scheduled audio and restores other-app audio through the existing notification-aware path.
4. A focused unit test fails if only one cue is scheduled, if inter-cue spacing is not one second, or if a late SwiftUI update schedules a duplicate cue.
5. An isolated iOS Simulator DEBUG autostart run logs/schedules `3`, `2`, and `1` at one-second cadence; physical-device listening remains the final check for output-route latency.
