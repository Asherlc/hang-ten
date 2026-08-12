# Native Hangboard Workbench Design

**Date:** 2026-08-11

## Goal

Ship Hangboard Workbench as a self-contained, Developer ID-signed and
notarized macOS application that opens in its own native window. The user
selects a Hang Ten checkout when the app launches; the workbench reads and
writes that checkout directly.

The editor must remain portable: the same browser UI speaks to an HTTP API that
can later be hosted remotely. This release provides only the local macOS mode;
it does not introduce accounts, a hosted service, or remote repository access.

## User Experience

1. The user double-clicks `Hangboard Workbench.app`.
2. On first launch, or if the remembered checkout is no longer valid, the app
   opens a native macOS folder picker.
3. The picker accepts only a folder that validates as a Hang Ten checkout.
   Cancellation quits without starting a server or making files.
4. The native app starts its packaged local backend for that checkout, waits
   for it to become healthy, then displays the existing editor inside its own
   macOS window.
5. The app remembers the last valid checkout and uses it automatically on the
   next launch. A menu command lets the user choose another checkout.
6. Final Save continues to write only to the selected checkout. It does not
   invoke Git; users review and commit those changes themselves.
7. Closing the window observes the existing unsaved-work contract and asks
   before discarding unsaved work. It then stops the local backend cleanly.

The app never opens the default web browser. It uses normal macOS application
menus and a native `NSOpenPanel` folder picker, while retaining the existing
editor visual interface within the window.

## Scope

### Included

- A native Apple Silicon macOS app shell, with a standard application window,
  menus, and folder picker.
- A bundled local workbench backend and static editor assets; Python, Node, and
  other development dependencies are not required on the user’s machine.
- Launch-time checkout selection, validation, and last-valid-checkout recall.
- Direct read/write access to the selected checkout through the existing
  repository-backed persistence and publication contracts.
- Developer ID signing, notarization, stapling, and final-app launch testing
  in the release workflow.
- A stable HTTP boundary between the editor UI and its workspace backend.

### Excluded

- Rewriting the editor UI in SwiftUI or AppKit.
- A hosted backend, authentication, synchronization, multi-user editing, or
  remote Git provider integration.
- Changing board schemas, pipeline behavior, save semantics, or Git workflow.
- Intel macOS and non-macOS packaging targets.

## Architecture

### Native shell

Create a small Swift macOS application as the user-facing executable. It owns
application lifecycle, `NSOpenPanel`, the last-checkout preference, native menu
commands, startup error presentation, and clean process shutdown. It hosts a
`WKWebView` in the main window.

The shell launches the bundled local backend with an explicit validated
`--repository-root`, loopback host, dynamically selected local port, and
`--no-open`. It polls a narrow health endpoint before navigating the web view
to the loopback editor URL. A launch failure remains visible in the native
window with a retry/choose-folder action and useful diagnostics; it must not
fail silently.

The shell is not App-Sandboxed in this release, because it must deliberately
modify the checkout the user chose. It requests no broad filesystem access and
uses the folder picker only to identify the target. If sandboxing is adopted
later, this boundary can use a security-scoped bookmark without changing the
editor API.

### Local backend runtime

The Python server remains the authority for repository discovery (after the
shell passes the explicit root), pipeline operations, file writes, and job
lifecycle. It must expose a deterministic health endpoint and must not call
`webbrowser.open` when launched by the native shell.

Package the backend and assets as an embedded, signed runtime rather than a
post-signed PyInstaller one-file executable. The packaging build supplies the
Developer ID signing identity to PyInstaller, so its embedded native
dependencies are signed before the hardened final app is assembled. The final
bundle signs all nested code and resources, then is notarized and stapled.

The app is self-contained in its runtime dependencies, not in user content:
the selected Hang Ten checkout remains the source of canonical board data and
the destination for edits.

### Editor/API boundary and future hosting

The editor accesses workspace operations only through versioned HTTP API
endpoints. No browser JavaScript may depend on local absolute paths or invoke
filesystem APIs directly. The native shell similarly does not implement
workbench routes or write board files itself.

For the native release, the API base URL is the loopback backend started by
the app. The editor obtains that base URL from one runtime configuration point,
not hard-coded localhost references spread through the UI. A later hosted
deployment can supply a remote base URL and a server-side workspace adapter
while reusing the same editor surface and API contracts. Authentication and
authorization belong at that future hosted boundary, not in this local-only
release.

## Data, Selection, and Failure Handling

- A valid checkout is identified by the repository markers already required by
  the workbench; validation reports the missing marker and allows another
  selection.
- Store only the normalized last-valid checkout path in application
  preferences. Revalidate it on every launch; do not trust a stale path.
- The app creates no parallel persistent workspace outside the selected
  checkout beyond standard application preferences and ephemeral runtime/log
  files.
- A second app launch activates the existing instance rather than starting an
  independent writer for the same checkout.
- If the backend exits, the window presents a recoverable error and lets the
  user retry or choose another checkout. It does not leave a blank web view.
- Closing, quitting, or switching checkouts shuts down the exact backend child
  process and confirms that it exited before replacement.

## Packaging and Release

The release artifact remains a notarized `.app` ZIP for Apple Silicon. The
bundle contains the Swift shell, the signed local backend runtime, static
assets, and build metadata identifying the source commit. It does not contain
private keys, certificates, a Hang Ten checkout, committed board packages, or
user workspaces.

CI must test the exact final app layout, not merely an intermediate frozen
executable. The noninteractive app launcher supports a test-only/headless
startup mode that accepts an explicit checkout and port, starts the embedded
backend, verifies the health endpoint and representative editor routes, then
shuts down cleanly. The signed release job additionally verifies nested code
signatures, notarization, stapling, Gatekeeper assessment, and final launch
behavior before publishing a release.

## Acceptance Criteria

- Double-clicking the released app opens a native Hangboard Workbench window;
  no browser window or tab is opened.
- First launch requires the user to select a valid Hang Ten checkout, and a
  later launch reuses the last still-valid selection.
- The workbench operates against the selected checkout without Python, Node,
  or a development environment installed.
- The app can switch to another validated checkout through a native command.
- Save writes only to the selected checkout and leaves Git commits to the user.
- The editor has a single configurable HTTP API base and contains no direct
  local-filesystem dependency, preserving a later remote-server deployment.
- CI catches a failure to start the final packaged app before a GitHub Release
  is published.
- The published application is Developer ID-signed, notarized, stapled, and
  accepted by Gatekeeper.
