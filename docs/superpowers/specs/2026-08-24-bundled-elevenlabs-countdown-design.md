# Bundled ElevenLabs Countdown Voice Design

## Goal

Use ElevenLabs-generated audio for Hang Ten's numeric countdown without placing an ElevenLabs API key in the app, operating a server, or making a network request during a workout. Continue using Apple's speech synthesis for all dynamic workout cues.

## Scope

The feature covers only the existing countdown vocabulary: `"1"`, `"2"`, and `"3"`. These are the only phrases produced by `CountdownAudioSchedule`. Dynamic phrases passed to `WorkoutAudioCoach.speak(_:)`, including exercise names and user-authored routine content, remain Apple speech.

## Architecture

A checked-in asset pack provides three pre-rendered, app-bundled audio clips. `CountdownAudioScheduler` loads the clips, decodes them into the existing `AVAudioPCMBuffer` scheduling pipeline, and preserves the present sample-accurate scheduling behavior.

The numeric countdown never calls ElevenLabs at runtime. A developer-only generation tool, excluded from the app target and configured solely through a local `ELEVENLABS_API_KEY` environment variable, can regenerate the assets intentionally. The key is never committed, emitted to logs, or included in an Xcode configuration file.

If the bundled pack cannot be loaded or decoded, the scheduler uses the existing Apple speech-buffer renderer. This is the local fallback for a missing, corrupt, or unavailable pack; runtime ElevenLabs credit exhaustion cannot occur because the production app never holds an ElevenLabs credential or makes an ElevenLabs request.

## Audio Asset Contract

- Asset filenames are deterministic: `countdown-1`, `countdown-2`, and `countdown-3`.
- Assets use a format supported by `AVAudioFile` and decode to PCM before scheduling.
- The package metadata records the ElevenLabs voice ID, model ID, output format, and source phrases used to make the assets. It does not contain a credential.
- The generation tool sends `POST /v1/text-to-speech/{voice_id}` using the `xi-api-key` header and an explicit supported output format. It fails without an environment-supplied key or explicitly supplied voice/model values.

## Error Handling

- Missing local developer credentials: the generation tool fails before any network request and explains which environment variables are required.
- ElevenLabs failure while regenerating: the tool reports the HTTP status and sanitized API error; it does not create or replace assets.
- Bundled asset loading/decoding failure in the app: log the failure category and use Apple synthesis for the entire countdown prewarm.
- Mixed sources are forbidden within a countdown: all numeric cues use the bundled pack only when every required asset has decoded successfully; otherwise all use Apple-rendered buffers.

## Testing

Unit tests verify that the asset-backed loader supplies buffers only when every requested phrase exists and is valid, and that failure delegates to the existing Apple renderer. Scheduler timing and current countdown behavior remain covered by the existing tests. The asset-generation tool is tested with URLProtocol-based HTTP stubs for its request shape and error handling; no test calls ElevenLabs.

## Constraints

- Do not add a backend, runtime API key, or runtime ElevenLabs request.
- Do not change dynamic spoken-cue behavior.
- Do not commit an ElevenLabs API key or any generated output outside the app's explicit asset directory.
- Preserve the existing prewarm-before-scheduling and sample-accurate countdown guarantees.
