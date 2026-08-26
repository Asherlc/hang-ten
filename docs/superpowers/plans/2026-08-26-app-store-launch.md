# Hang Ten Training App Store Launch Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Submit Hang Ten Training 1.0.0 build 242001 for App Review with a truthful public listing and complete App Store Connect readiness.

**Architecture:** The repository hosts the policy and canonical listing copy; App Store Connect holds the review-version, compliance, privacy, availability, screenshot, and submission state. Each task must dry-run or inspect before its remote mutation and re-run `asc validate` before handoff.

**Tech Stack:** SwiftUI/Xcode Simulator; GitHub; App Store Connect CLI (`asc`).

**Spec:** `docs/superpowers/specs/2026-08-26-app-store-launch-design.md`

## Global Constraints

- Target app `6797141761`, version `1.0.0` (`84220a9c-0bc5-4ce0-a8dc-dc63e53e24ec`), build `242001` (`cf43f160-bfa2-4f92-96e5-626af4a3a55a`) only.
- Use review contact Asher Cohen, `asherlc@asherlc.com`, `+1 510-759-6248`; no demo account is required.
- Use only the source-backed listing copy in the approved spec and state the app’s third-party content truthfully.
- Data processed solely on the device is not a collected App Privacy data type; disclose any actual off-device telemetry, GitHub sync, or diagnostics according to the release binary.
- Store generated screenshots and release evidence under `.context/app-store-launch/`; never commit secrets or generated assets.
- Push every repository commit to `origin/submit-app-store`.

---

### Task 1: Publish the public policy and canonical listing metadata

**Files:**
- Create: `PRIVACY.md`, `metadata/`
- Modify: `README.md`
- Test: `asc metadata validate --dir metadata --output table`

**Interfaces:**
- Consumes: verified source behavior and the approved listing copy.
- Produces: public privacy/support URLs and validated en-US metadata.

- [ ] Pull current metadata into `metadata/` and preserve it as the canonical source.
- [ ] Create `PRIVACY.md` identifying Asher Cohen and `asherlc@asherlc.com`, with accurate disclosures for on-device workout history, opt-in Apple Health, optional Bluetooth, optional GitHub Device Flow, and conditional PostHog/Sentry telemetry. Link it from `README.md`.
- [ ] Write the approved en-US description, promotional text, keywords, support URL `https://github.com/Asherlc/hang-ten/issues`, and copyright `© 2026 Hang Ten` into canonical metadata.
- [ ] Validate and dry-run `asc metadata push`; apply only the inspected diff. Commit/push the policy and metadata.

### Task 2: Complete App Store Connect compliance, review setup, and screenshots

**Files:**
- Create: `.context/app-store-launch/screenshots/`
- Modify: App Store Connect app/version records only
- Test: `asc validate --app 6797141761 --version 1.0.0 --platform IOS --output table`

**Interfaces:**
- Consumes: Task 1 public policy URL and canonical metadata.
- Produces: a fully prepared version with validated iPhone screenshots.

- [ ] Inspect build settings and App Privacy JSON; declare no collection for data confined to device/HealthKit, and declare only the off-device data practices confirmed by the binary and current PostHog/Sentry configuration. Dry-run web privacy plan, apply, then publish.
- [ ] Set Health & Fitness primary category, use `USES_THIRD_PARTY_CONTENT`, set the complete age-rating questionnaire (`healthOrWellnessTopics` and user-generated-content capabilities included; all unsupported objectionable-content categories none/false), set free availability for all territories, and configure the approved review contact/notes.
- [ ] Use an isolated simulator and release-visible UI states to capture five 6.5-inch iPhone screenshots: guided routine/holds, grip/step cue, board picker, Apple Health option, and optional Bluetooth sensor option. Validate locally, dry-run upload, then upload.
- [ ] Attach no build until the next validation report has no non-build blockers. Re-run the report and resolve any newly surfaced problem.

### Task 3: Attach the release build and submit once

**Files:**
- Modify: App Store Connect review submission only
- Test: `asc review status --app 6797141761 --version 1.0.0 --platform IOS --output table`

**Interfaces:**
- Consumes: zero-blocker validation and the exact valid build.
- Produces: one App Review submission ID and status.

- [ ] Dry-run `asc review submit` for version ID `84220a9c-0bc5-4ce0-a8dc-dc63e53e24ec` and build ID `cf43f160-bfa2-4f92-96e5-626af4a3a55a`.
- [ ] Confirm the dry-run creates no duplicate submission and names only the target app/version/build; execute with `--confirm`.
- [ ] Record the submission ID and final status. Do not monitor, cancel, or retry it in this task.
