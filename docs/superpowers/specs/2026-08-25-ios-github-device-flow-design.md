# iOS GitHub Device Flow for Board Editor

## Problem

The iOS board editor currently asks a user to create and paste a GitHub
personal access token (PAT). The hosted Hangboard Workbench already uses the
project's GitHub OAuth App for browser authentication. Mobile editing should
use that OAuth App too, without exposing its client secret or requiring a PAT.

## Goal

The iOS board editor signs a user into GitHub through GitHub OAuth Device Flow.
After the user approves the app in a browser, the editor stores the resulting
OAuth access token in the existing device-only Keychain entry and uses it for
the existing board pull, commit, and pull-request requests.

## Scope

- Reuse the GitHub OAuth App used by the hosted Workbench.
- Use its public client ID in the iOS target; never include its client secret
  in source, build settings, or the app bundle.
- Request the same `repo read:org` scopes used by the hosted Workbench.
- Replace the PAT form with an approval-code screen that can open GitHub.
- Preserve the existing Keychain storage and GitHub REST sync operations.
- Provide a clear retry path for denial, expiry, polling throttling, and
  malformed GitHub responses.

## Non-goals

- Changing the hosted Workbench's browser OAuth flow or session cookies.
- Changing repository ownership, board package paths, branch behavior, or PR
  behavior.
- Supporting GitHub Enterprise Server in this change.
- Refresh-token support. A later OAuth App configuration that enables
  expiring tokens will require a separate refresh-token design.

## Configuration and deployment

GitHub Device Flow must be enabled on the existing OAuth App. The iOS target
receives that app's public client ID through a build configuration value exposed
in the app bundle. The value is public by design; an absent or blank value
disables sign-in with a configuration error rather than falling back to a PAT.

The hosted Workbench continues to receive the same client ID plus its private
client secret through its existing deployment environment. No new hosted
endpoint is needed.

## Components

### GitHub device authorization client

`GitHubBoardSyncService` gains a focused device-flow interface, backed by the
same injectable `URLSession` used by the existing REST client. It will:

1. POST `client_id` and `scope=repo read:org` to
   `https://github.com/login/device/code` with `Accept: application/json`.
2. Parse and validate the device code, user code, verification URI, expiry,
   and minimum polling interval.
3. Poll `https://github.com/login/oauth/access_token` no faster than the
   returned interval using the device-code grant type.
4. Continue only for `authorization_pending`; add five seconds after each
   `slow_down`; stop on approval, denial, expiry, malformed input, or network
   failure.
5. Validate the authenticated user through the existing `/user` request before
   allowing the session to persist.

The service exposes typed outcomes so the view layer never parses OAuth JSON or
handles raw tokens. The access token remains in memory only until the validated
session saves it through `GitHubTokenStore`.

### GitHub sync session

`GitHubSyncSession` owns the device-flow lifecycle. It starts a sign-in from
the configured client ID, publishes the verification challenge for the UI,
observes cancellation, and persists only a successfully validated token. Its
existing restore and sign-out behavior stays intact.

### Board editor sign-in UI

`GitHubSignInView` no longer contains a secure text field or PAT guidance. It
starts the device flow, displays GitHub's user code, provides an action to open
the verification URI, and shows progress while waiting for approval. The user
can cancel and return to the editor. Success dismisses the sheet; recoverable
errors remain visible with a new Connect action.

## Data flow

1. The user chooses Connect GitHub in the mobile board editor.
2. The app obtains a device challenge from GitHub using the configured public
   client ID and displays its user code.
3. The user approves the code in GitHub's browser page.
4. The app polls GitHub according to the received interval.
5. On approval, the app validates `/user`, writes the OAuth token to the
   existing Keychain item, publishes the username, and dismisses the sheet.
6. Existing pull, commit, and PR actions retrieve that token from Keychain and
   continue to call GitHub exactly as they do today.

## Error handling

- Missing client ID: show a configuration error and do not send a request.
- `authorization_pending`: remain in the waiting state without showing an
  error.
- `slow_down`: increase the following polling delay by five seconds.
- `access_denied` or expired device code: stop polling and show a retryable
  error.
- Transport or invalid JSON: stop polling and show the existing safe GitHub
  error text.
- User cancellation: stop polling, retain no new token, and leave any prior
  signed-in session unchanged.
- Token validation failure: retain no new token and surface the mapped GitHub
  error.

## Security

- The app bundle contains only the OAuth App client ID. The client secret stays
  in the hosted Workbench deployment.
- The device code is not persisted and expires per GitHub's response.
- The OAuth access token is never placed in a URL, view text, logs, or user
  defaults. After validation it is kept only in the existing
  `kSecAttrAccessibleAfterFirstUnlockThisDeviceOnly` Keychain entry.
- Sign-out deletes the existing Keychain token.

## Testing

Add focused URL-protocol tests to `GitHubBoardSyncServiceTests` covering the
form-encoded device-code request, validated challenge parsing, polling
intervals, approval, pending authorization, slow-down handling, denial,
expiry, and malformed responses. Add session tests that prove only validated
tokens reach the token store. Update the UI test contract to assert the PAT
field and PAT instructions are absent and that the device-flow controls are
discoverable.

## Acceptance criteria

- A mobile editor user never creates or pastes a GitHub PAT.
- A user can authenticate through GitHub approval using the configured OAuth
  App client ID.
- The OAuth client secret is absent from the iOS target and repository.
- Successful authentication persists a validated OAuth token in the existing
  device-only Keychain store and shows the GitHub username.
- Existing pull, push, and PR behavior works with that token.
- Device-flow errors are actionable, do not leak tokens, and permit retry.
