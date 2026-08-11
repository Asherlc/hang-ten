# Hangboard Workbench macOS Trust Release Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the Hangboard Workbench release pass macOS Gatekeeper without a Finder override by packaging the PyInstaller executable as a Developer ID-signed, notarized, stapled macOS app bundle in CI.

**Architecture:** Pull requests keep building and smoke-testing the raw arm64 executable without secrets. The protected release job wraps that exact executable in a minimal `.app`, signs it with a Developer ID Application certificate and hardened runtime, submits a ZIP to Apple’s notary service using the existing App Store Connect API key, staples the ticket, validates Gatekeeper acceptance, and publishes the notarized app ZIP plus checksum.

**Tech Stack:** GitHub Actions, macOS `codesign`, `xcrun notarytool`, `xcrun stapler`, `spctl`, PyInstaller, Python workflow tests.

## Global Constraints

- Pull requests must remain runnable without Apple signing or notarization secrets.
- The release must sign the exact executable produced and smoke-tested by the build job.
- The signing identity must be a `Developer ID Application` certificate with hardened runtime enabled.
- Notarization must use `xcrun notarytool` and the existing App Store Connect API key variables/secrets.
- The published artifact must contain a stapled `.app` bundle, not only a standalone executable.
- CI must fail before publication if signing, notarization, stapling, checksum, or `spctl` validation fails.
- Existing workbench runtime behavior, repository discovery, and source-development commands must remain unchanged.
- Do not commit certificates, private keys, or generated release artifacts.

## File Structure

- Create `Tools/hold-highlight-editor/packaging/macos_app.py`: source-controlled app-bundle metadata and deterministic wrapping of the already-built executable.
- Create `Tools/hold-highlight-editor/tests/test_macos_app.py`: verify bundle layout, Info.plist metadata, version propagation, and safe replacement behavior.
- Modify `.github/workflows/hangboard-workbench-release.yml`: invoke the source-controlled bundler, import Developer ID credentials, sign, notarize, staple, validate, archive, and publish the trusted app ZIP.
- Modify `Tools/hold-highlight-editor/tests/test_workbench_release_workflow.py`: enforce the signing/notarization/stapling steps, narrow secret use, and exact trusted artifact names.
- Modify `Tools/hold-highlight-editor/README.md`: document the signed app ZIP launch flow and remove the unsigned Gatekeeper workaround.
- Modify `Tools/HangboardOnboarding/README.md`: keep the release quick start aligned with the signed app bundle and source fallback.

---

### Task 1: Sign, notarize, staple, and publish the workbench app

**Files:**
- Create: `Tools/hold-highlight-editor/packaging/macos_app.py`
- Create: `Tools/hold-highlight-editor/tests/test_macos_app.py`
- Modify: `.github/workflows/hangboard-workbench-release.yml`
- Modify: `Tools/hold-highlight-editor/tests/test_workbench_release_workflow.py`
- Modify: `Tools/hold-highlight-editor/README.md`
- Modify: `Tools/HangboardOnboarding/README.md`

**Interfaces:**
- Consumes: the existing build job’s `hangboard-workbench-macos-arm64.tar.gz` and checksum artifact, plus `APPSTORE_ISSUER_ID`, `APPSTORE_API_KEY_ID`, `APPSTORE_API_PRIVATE_KEY`, `APPLE_TEAM_ID`, `DEVELOPER_ID_CERTIFICATE_FILE_BASE64`, and `DEVELOPER_ID_CERTIFICATE_PASSWORD` CI credentials.
- Produces: `hangboard-workbench-macos-arm64.zip` containing `hangboard-workbench.app`, and `hangboard-workbench-macos-arm64.sha256` for that ZIP.

- [ ] **Step 1: Add failing workflow assertions**

Extend the workflow test to require the release job to import the Developer ID certificate, create an app bundle with `CFBundleExecutable=hangboard-workbench`, sign with `--options runtime`, submit with `xcrun notarytool`, staple with `xcrun stapler`, validate with `spctl`, and publish the ZIP/checksum pair. Require the test to reject the old tarball-only asset names and reject signing/notary credentials in the pull-request build job.

- [ ] **Step 2: Run the workflow test and verify it fails**

Run:

```bash
rtk python -m pytest Tools/hold-highlight-editor/tests/test_workbench_release_workflow.py -q
```

Expected: FAIL because the release workflow currently publishes an unsigned tarball and has no signing or notarization steps.

- [ ] **Step 3: Add the source-controlled app bundler**

Create `packaging/macos_app.py` with a CLI that takes `--executable`, `--output`, and `--version`, validates that the input is a regular arm64 executable, creates `Contents/MacOS`, writes the committed Info.plist contract, copies the executable with its mode preserved, and fails without deleting an existing output until all inputs are validated. The script must not sign, notarize, or read secrets. Unit-test it with temporary files and `plistlib`.

- [ ] **Step 4: Add protected release signing and notarization**

In the release job, extract the verified executable from the build artifact, invoke the source-controlled `packaging/macos_app.py`, import the Developer ID certificate with `Apple-Actions/import-codesign-certs`, and extract the exact `Developer ID Application` identity from the temporary keychain. The source script creates:

```text
hangboard-workbench.app/
  Contents/
    Info.plist
    MacOS/hangboard-workbench
```

Use bundle identifier `com.hangten.hangboard-workbench`, package type `APPL`, the executable name `hangboard-workbench`, and the current GitHub run number as the bundle version. Sign the inner executable and the app bundle with `codesign --force --options runtime --timestamp`, verify with `codesign --verify --deep --strict --verbose=2`, and submit a ZIP made with `ditto --keepParent` to `xcrun notarytool submit --wait`. Write the existing App Store Connect private key only to a runner-temporary `.p8` file, then staple and validate the app with `xcrun stapler` and `spctl --assess --type execute --verbose=4`.

Replace the release assets with the notarized app ZIP and its checksum. Keep the existing immutable tag/release checks, updating the exact required asset names and release notes.

- [ ] **Step 5: Update documentation**

Change both workbench quick starts to download `hangboard-workbench-macos-arm64.zip`, verify its checksum, extract it, and launch `hangboard-workbench.app` with Finder or `open`. State that the release is Developer ID signed and notarized; retain source-development instructions separately. Do not tell users to remove quarantine or disable Gatekeeper.

- [ ] **Step 6: Run focused validation**

Run:

```bash
rtk python -m pytest Tools/hold-highlight-editor/tests/test_workbench_release_workflow.py -q
rtk python -m pytest Tools/hold-highlight-editor/tests/test_macos_app.py -q
rtk python -m pytest Tools/hold-highlight-editor/tests/test_workbench_packaging.py Tools/hold-highlight-editor/tests/test_workbench_binary.py -q
```

Expected: all tests PASS. On a macOS runner with the required secrets, the release job must additionally pass `codesign`, `notarytool`, `stapler`, `spctl`, and checksum validation.

- [ ] **Step 7: Commit**

```bash
git add .github/workflows/hangboard-workbench-release.yml \
  Tools/hold-highlight-editor/packaging/macos_app.py \
  Tools/hold-highlight-editor/tests/test_macos_app.py \
  Tools/hold-highlight-editor/tests/test_workbench_release_workflow.py \
  Tools/hold-highlight-editor/README.md \
  Tools/HangboardOnboarding/README.md \
  docs/superpowers/plans/2026-08-10-hangboard-workbench-notarization.md
git commit -m "Sign and notarize workbench releases"
```
