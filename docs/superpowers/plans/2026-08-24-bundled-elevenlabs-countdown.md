# Bundled ElevenLabs Countdown Voice Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prefer bundled, development-generated ElevenLabs clips for the `1`, `2`, `3` countdown while retaining the current Apple renderer as an all-or-nothing fallback.

**Architecture:** A developer-only script calls ElevenLabs only when explicitly supplied local credentials and atomically writes a three-file pack plus non-secret metadata under `HangTen/Resources/CountdownAudio`. The app's countdown backend first attempts to load every required numeric clip into PCM buffers; if any clip is absent or invalid, it renders the whole countdown with its existing `AVSpeechSynthesizer` path. Dynamic `WorkoutAudioCoach.speak(_:)` is unchanged.

**Tech Stack:** Swift 5, AVFoundation, XCTest, zsh, curl, Xcode 26.

**Spec:** `docs/superpowers/specs/2026-08-24-bundled-elevenlabs-countdown-design.md`

## Global Constraints

- Do not add a backend, runtime API key, or runtime ElevenLabs request.
- Do not change dynamic spoken-cue behavior.
- Do not commit an ElevenLabs API key or any generated output outside `HangTen/Resources/CountdownAudio`.
- Preserve the existing prewarm-before-scheduling and sample-accurate countdown guarantees.
- Use `rtk` for repository shell commands and observe each new test fail before writing production code.

---

### Task 1: Add a safe, developer-only countdown-pack generator

**Files:**
- Create: `scripts/generate-elevenlabs-countdown-audio.sh`
- Create: `scripts/test-generate-elevenlabs-countdown-audio.sh`
- Create: `HangTen/Resources/CountdownAudio/README.md`
- Create: `HangTen/Resources/CountdownAudio/.gitkeep`
- Modify: `HangTen.xcodeproj/project.pbxproj`
- Modify: `README.md`

**Interfaces:**
- Consumes: `ELEVENLABS_API_KEY`, `ELEVENLABS_VOICE_ID`, optional `ELEVENLABS_MODEL_ID` (defaults to `eleven_flash_v2_5`), and optional `ELEVENLABS_OUTPUT_FORMAT` (defaults to `mp3_22050_32`) from the caller's environment.
- Produces: `HangTen/Resources/CountdownAudio/countdown-1.mp3`, `countdown-2.mp3`, `countdown-3.mp3`, and `metadata.json`, each replaced only after all three POST requests succeed.

- [ ] **Step 1: Write the failing generator-contract test.**

Create `scripts/test-generate-elevenlabs-countdown-audio.sh` with an isolated `mktemp -d` workspace and a fake `curl` placed first on `PATH`. Invoke `scripts/generate-elevenlabs-countdown-audio.sh` without `ELEVENLABS_API_KEY` and assert nonzero exit, no `curl` invocation, and an error containing `ELEVENLABS_API_KEY`. Then invoke it with `ELEVENLABS_API_KEY=test-key`, `ELEVENLABS_VOICE_ID=test-voice`, a fake curl that writes deterministic bytes to the requested output file, and `ELEVENLABS_OUTPUT_DIRECTORY` set to the temp workspace. Assert exactly `countdown-1.mp3`, `countdown-2.mp3`, `countdown-3.mp3`, and `metadata.json` exist; assert captured requests use `POST`, `xi-api-key: test-key`, `Content-Type: application/json`, and `/v1/text-to-speech/test-voice?output_format=mp3_22050_32`; assert neither log nor metadata contains `test-key`.

- [ ] **Step 2: Run the test to verify it is red.**

Run: `rtk zsh scripts/test-generate-elevenlabs-countdown-audio.sh`

Expected: FAIL because the generator script does not yet exist.

- [ ] **Step 3: Implement the minimal generator and package documentation.**

Create an executable zsh script that uses `set -euo pipefail`, validates the required nonempty key and voice ID before calling `curl`, creates a temporary sibling directory with `mktemp -d`, and installs an EXIT trap that removes only that exact temporary directory. For each phrase in `1 2 3`, post the JSON body `{"text":"<phrase>","model_id":"<model>"}` to `https://api.elevenlabs.io/v1/text-to-speech/<voice-id>?output_format=<format>` with the API key only in the `xi-api-key` header. Write response bytes to the temporary directory, create metadata without the key, validate all four temporary files are nonempty, then atomically replace the exact output directory contents. On any curl failure, preserve the previous pack and print only sanitized diagnostics. Keep the committed resource directory empty except for `.gitkeep` and its README; real generated files are deliberately created only by an authorized maintainer. Document the required command and that the generated pack must be reviewed and committed explicitly before it can ship.

Register `HangTen/Resources/CountdownAudio` as a resource folder in the app target's existing `Resources` group and Resources build phase, so generated `countdown-*.mp3` files are copied into `Bundle.main` without needing per-file project edits.

- [ ] **Step 4: Run the generator contract test to verify green.**

Run: `rtk zsh scripts/test-generate-elevenlabs-countdown-audio.sh`

Expected: PASS, including both missing-credential and successful fake-curl cases.

- [ ] **Step 5: Commit Task 1.**

Run:

```sh
rtk git add scripts/generate-elevenlabs-countdown-audio.sh scripts/test-generate-elevenlabs-countdown-audio.sh HangTen/Resources/CountdownAudio HangTen.xcodeproj/project.pbxproj README.md
rtk git commit -m "feat: add ElevenLabs countdown pack generator"
```

### Task 2: Prefer a complete bundled pack and preserve Apple fallback

**Files:**
- Modify: `HangTen/Models/CountdownAudioScheduler.swift`
- Modify: `HangTenTests/WorkoutTimelineTests.swift`

**Interfaces:**
- Consumes: a phrase-to-buffer provider that returns a complete `[String: [AVAudioPCMBuffer]]` for a supplied `CountdownAudioSchedule`, or `nil` when a bundle resource is missing, empty, unreadable, or cannot share a playback format.
- Produces: `SystemCountdownAudioSchedulingBackend` schedules bundled buffers when every requested phrase is ready; otherwise it invokes the existing `render(_:)` Apple synthesis implementation for the entire schedule.

- [ ] **Step 1: Write failing source-selection tests.**

In `HangTenTests/WorkoutTimelineTests.swift`, add a pure testable selector adjacent to existing countdown tests. Define a `CountdownAudioBufferSource` protocol with `func buffers(for phrases: Set<String>) -> [String: [AVAudioPCMBuffer]]?`. Add a recording fake source and a recording Apple-renderer factory. Test that a source returning buffers for `"1"`, `"2"`, and `"3"` is selected without invoking the Apple factory; test that a source returning `nil` invokes the Apple factory once and never mixes a source buffer into that preparation. Keep the tests independent of bundle files by injecting the source and factory.

- [ ] **Step 2: Run the focused tests to verify red.**

Run:

```sh
rtk xcodebuild test -project HangTen.xcodeproj -scheme HangTen -sdk iphonesimulator -configuration Debug -derivedDataPath .context/DerivedData-ElevenLabs -destination 'platform=iOS Simulator,name=iPhone 17 Pro' -only-testing:HangTenTests/WorkoutTimelineTests
```

Expected: FAIL because the source-selection API is absent.

- [ ] **Step 3: Implement complete-pack loading and fallback.**

Add a `BundledCountdownAudioBufferSource` that looks up `countdown-<phrase>.mp3` in `Bundle.main`, opens each with `AVAudioFile`, creates an `AVAudioPCMBuffer` of the file's processing format and frame capacity, and reads the whole file. Return `nil` unless every requested phrase has a nonempty buffer and all decoded buffers share a compatible `AVAudioFormat`. Add a small injectable selection layer that chooses this source before constructing the existing `SystemCountdownAudioSchedulingBackend`; when selection fails, instantiate the untouched Apple renderer. Ensure the selected source remains fixed for a prewarm cycle and that no schedule can combine pack and Apple buffers. Do not alter `WorkoutAudioCoach.speak(_:)`.

- [ ] **Step 4: Run the focused tests to verify green.**

Re-run the exact command from Step 2.

Expected: PASS.

- [ ] **Step 5: Run the full unit suite and Debug simulator build.**

Run:

```sh
rtk xcodebuild test -project HangTen.xcodeproj -scheme HangTen -sdk iphonesimulator -configuration Debug -derivedDataPath .context/DerivedData-ElevenLabs -destination 'platform=iOS Simulator,name=iPhone 17 Pro'
rtk xcodebuild build -project HangTen.xcodeproj -scheme HangTen -sdk iphonesimulator -configuration Debug -derivedDataPath .context/DerivedData-ElevenLabs
```

Expected: both commands exit zero.

- [ ] **Step 6: Commit Task 2.**

Run:

```sh
rtk git add HangTen/Models/CountdownAudioScheduler.swift HangTenTests/WorkoutTimelineTests.swift
rtk git commit -m "feat: prefer bundled ElevenLabs countdown audio"
```

## Plan Self-Review

- Spec coverage: Task 1 covers credential isolation, deterministic assets, metadata, atomic regeneration, and sanitized failures. Task 2 covers all-or-nothing bundled playback, Apple fallback, timing preservation, and the unchanged dynamic path.
- Placeholder scan: no TODO or deferred implementation instructions remain; the only externally supplied values are intentionally explicit developer environment variables.
- Type consistency: Task 2 introduces only `CountdownAudioBufferSource.buffers(for:)`, used by its fake and bundled implementations; the existing scheduler continues consuming `[String: [AVAudioPCMBuffer]]`.
