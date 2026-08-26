# Hang Ten Training App Store Launch Design

## Goal

Prepare the first public iOS release of Hang Ten Training for App Store Review
without representing unavailable facts as completed App Store Connect metadata.
The approved launch posture is conservative: a free Health & Fitness app,
available worldwide, with a public privacy policy and GitHub Issues support.

This is a release specification only. It makes no App Store Connect, source,
hosting, or external-account changes.

## Product facts that may be used in the listing

The listing must describe only functionality present in the shipped release
candidate:

- Hang Ten is a SwiftUI hangboard coach that shows the athlete the exact holds,
  intended grip/fingers, and current task for a selected board.
- It includes source-linked guided hangboard routines, including marked adapted
  routines, and board maps with directly authored hold paths/highlights.
- With the user's authorization, completed sessions save to Apple Health as
  functional-strength workouts and the app reads Health workout history to
  restore progress.
- An optional Bluetooth force-sensor connection provides live force,
  calibration, tare, and threshold-based loaded-time recording. The app
  requests Bluetooth only after the user explicitly chooses to connect a
  sensor; force readings are not a certified measurement.

The public description must not say that a sensor is required, that every
board/routine is manufacturer-authored, or that force data is medically or
scientifically certified. Adapted routine timing and mapping are app guidance,
not manufacturer prescriptions. The app is not medical advice.

### English (U.S.) listing copy to stage

**Name:** Hang Ten Training

**Subtitle:** Guided hangboard workouts

**Promotional text:** Train with clear hold maps, guided routines, and optional
Apple Health workout saving.

**Description:**

Hang Ten Training is a guided hangboard coach for climbers. Choose your board,
follow the current task, and see the intended holds, grip, and fingers as you
train.

Use source-linked routines and a clear board map instead of translating a
paper plan mid-session. Pause, resume, select steps directly, and use spoken
countdown cues while you work.

Optional connections let you save completed sessions as functional-strength
workouts in Apple Health and receive live force readings from a compatible
Bluetooth force sensor. Sensor features are optional and are not certified
measurements.

Hangboard training can injure fingers, arms, and shoulders. Warm up, use a
securely installed board, and stop if you feel pain. Hang Ten is a training
timer and visual cue, not medical advice.

**Keywords:** hangboard,climbing,training,workout,grip,strength,bouldering

The operator must validate all character limits in App Store Connect before
staging; no fabricated ratings, performance claims, or manufacturer
endorsements may be added.

## Store setup decisions

| App Store Connect field | Decision | Constraint |
| --- | --- | --- |
| Primary category | Health & Fitness | Approved first-release category. |
| Price | Free | No monetization decision is included in this release. |
| Availability | Worldwide | This is an explicit territory decision; select every territory only after the account holder confirms it has distribution rights and can meet local obligations. |
| Copyright | © 2026 Hang Ten | Use exactly this approved value. |
| Support URL | `https://github.com/Asherlc/hang-ten/issues` | GitHub Issues is the approved support channel. Confirm the repository remains publicly reachable before submission. |
| Privacy Policy URL | Public policy in this repository | The final URL must be a public, stable rendered page (for example the repository's public policy file), not an unpublished branch or local path. |

## Rights and content declaration

Do **not** declare that the app contains no third-party content. The repository
documents source-linked Metolius training material and board references, and
`THIRD_PARTY_NOTICES.md` identifies adapted Phosphor hand-cue assets under the
MIT License. This release needs an account-holder/legal verification of the
rights declaration that applies to the final binary and listing assets.

Before answering App Store Connect's content-rights question, verify all of
the following:

1. The shipped board images and geometry may be distributed in the selected
   territories.
2. The source-linked and adapted routine content may be distributed as used.
3. The Phosphor license notice remains included where required.
4. All screenshots, app icon, listing copy, and any submitted preview media
   are owned or licensed for worldwide App Store use.

If the answer is not affirmative for every item, stop the launch and obtain
the applicable rights or remove the affected content. This specification does
not choose a content-rights answer on the owner's behalf.

## Privacy and App Privacy analysis

The public Privacy Policy and App Privacy answers must match the release
configuration that is actually shipped. They cannot be made accurate until the
data controller's contact details, the production analytics configuration, and
any data-storage/retention terms are identified.

| Capability | What the code/repository establishes | App Privacy work required before submission |
| --- | --- | --- |
| Local sessions and settings | Workout history is stored locally; `WorkoutSessionStore` writes session records in Application Support and retains up to 20. Local workout history also uses `UserDefaults`. | Confirm the exact locally stored fields, deletion behavior, backups/sync behavior, and whether any are transmitted. Do not claim collection if they remain on-device. |
| Apple Health | With opt-in authorization, the app reads and writes HealthKit workout data. A completed workout can include plan, board, and activity-segment metadata. | Declare Health & Fitness data exactly as required by Apple's current questionnaire, including whether it is linked to the user or used for tracking. State that Health data is used only for the disclosed workout/history function if that remains true. |
| Bluetooth force sensor | The optional CoreBluetooth service receives sensor data, including force measurements; completed session measurements can be persisted locally. | Determine the exact data category and whether peripheral identifiers/names are retained or transmitted in the release. Do not describe force data as anonymous or not collected without verifying the binary and the questionnaire definitions. |
| GitHub Device Flow | Optional board-editor sign-in requests GitHub Device Flow approval. The OAuth access token is stored in a device-only Keychain item; authenticated calls reach GitHub's OAuth/API endpoints and may read/write board content and create pull requests. | Identify GitHub as a separate service in the policy; disclose account/authentication and user content handling as applicable. Confirm the exact scope and all network operations in the release. |
| PostHog | Telemetry is a no-op without a configured `phc_` client token. If configured, the app sends an allow-listed set of anonymous product events and uses masked session replay; it does not call `identify`. | The release manager must determine whether build 242001 includes a working PostHog token/host. If yes, complete Analytics and any applicable diagnostics/session-replay disclosures based on the actual SDK behavior, PostHog project configuration, retention, recipients, and Apple's definitions. If no, verify telemetry is genuinely disabled in the archived app before making no-collection answers. |

`SENTRY_DSN` is also present as a build setting in the project. Treat it as an
additional release-configuration question: inspect the archived app and its
runtime behavior before asserting that crash/diagnostic data is or is not
collected.

### Minimum public-policy content, after owner inputs are supplied

The policy must identify the legal controller and a real contact method; list
each data practice above that ships; distinguish on-device storage from data
sent to Apple, GitHub, PostHog, or another processor; state purposes,
recipients, retention/deletion, security measures, and how users can exercise
available privacy rights. It must explain how to disconnect Apple Health,
Bluetooth, GitHub, and analytics functionality where those controls exist.

Do not publish a generic or contactless policy. Missing controller identity,
contact information, storage/retention facts, or production telemetry status
is a release blocker for a truthful privacy policy.

## Age rating

Complete the current App Store Connect age-rating questionnaire from the
release candidate's actual capabilities. The repository supports training,
HealthKit, Bluetooth, optional GitHub sign-in, and user-created board/routine
content; it does not by itself establish every questionnaire answer.

Do not infer answers about user-generated content, web access, messaging,
advertising, purchases, or medical/health content from absence in this
specification. Record the chosen answers and evidence for each question, then
use the resulting Apple-generated rating. Escalate any question whose answer
cannot be verified from the final binary and approved product policy.

## App Review information

App Review contact details must be the actual developer or authorized review
contact's name, email address, and phone number. Do not invent a person or use
placeholder data. Obtain the real values from the account holder and enter
them only in App Store Connect.

Review notes should explain:

- The core guided routine and board-map experience works without an account,
  Apple Health permission, Bluetooth hardware, GitHub, or telemetry.
- Apple Health is optional and only requested from the in-app connection flow.
- Bluetooth is optional and requires a compatible physical force sensor;
  reviewers can assess the rest of the app without one.
- GitHub Device Flow is an optional board-editor feature. It requires the
  reviewer to use their own GitHub account and is not needed for core training.
- No medical claims are made; the app is a training timer and visual cue.

Do not provide test credentials unless the final binary actually requires
them. If a review route, demo account, or hardware workflow is required,
document its real steps and verify them in the release candidate.

## Screenshots

Create required iPhone screenshots from the release candidate, not from design
mockups or DEBUG-only review routes. Use an isolated simulator or device and
the current App Store Connect screenshot-size requirements. Capture a focused
set that truthfully shows:

1. A guided routine with hold map and current task.
2. A second routine/task state showing grip/finger cues or step guidance.
3. The board picker or board map selection experience.
4. The Apple Health option, without implying authorization or an outcome that
   has not occurred.
5. The optional Bluetooth force-sensor option, clearly labeled optional.

Remove any debug UI, fixture-only state, personal information, access tokens,
or unsupported performance claims. Validate resolution, device framing, and
localization in App Store Connect before upload.

## Submission sequence

1. Resolve all owner-provided blockers: data controller/contact, policy URL,
   rights declaration, age-rating answers, App Review contact, confirmed
   territory rights, and whether PostHog/Sentry ship in the release archive.
2. Publish the accurate Privacy Policy at the confirmed public repository URL.
3. Stage the English (U.S.) metadata, category, copyright, free pricing, and
   worldwide availability; upload approved screenshots and complete content
   rights, age rating, App Privacy, and review information.
4. Locate build **242001** for the intended version and platform. Attach it
   only after its status is **VALID** and its embedded configuration matches
   the privacy analysis.
5. Run App Store Connect validation against the staged version. Resolve every
   blocking validation result; do not treat an invalid or processing build as
   submission-ready.
6. Dry-run the review submission, confirm the exact app/version/build and
   metadata plan, then submit once. Record the submission identifier and the
   monitoring command/status.

The approved build number alone is not evidence that build 242001 is valid or
that it contains the intended settings. A successful final validation gate is
required before submission.

## Evidence

- `README.md` — product scope, routines, board maps, Apple Health, Bluetooth,
  GitHub Device Flow release setup, optional PostHog configuration, safety,
  source links, and licenses.
- `THIRD_PARTY_NOTICES.md` — adapted Phosphor icon assets and MIT notice.
- `HangTen/Models/HealthKitService.swift` and `docs/IOS_RUNTIME_SERVICES.md`
  — Apple Health read/write behavior and workout metadata.
- `HangTen/Models/MotherboardBluetoothService.swift` and
  `docs/IOS_RUNTIME_SERVICES.md` — optional Bluetooth force-sensor behavior
  and its limitations.
- `HangTen/Models/GitHubBoardSyncService.swift` and
  `HangTen/Views/BoardEditor/GitHubEditorSyncViews.swift` — optional GitHub
  Device Flow, Keychain token storage, and GitHub API operations.
- `HangTen/Models/PostHogTelemetry.swift` and `HangTen/Models/Telemetry.swift`
  — conditional telemetry configuration, allow-listed event data, and replay
  settings.
- `HangTen/Models/WorkoutSessionStore.swift` and
  `HangTen/Models/LocalWorkoutHistoryStore.swift` — local session persistence.
