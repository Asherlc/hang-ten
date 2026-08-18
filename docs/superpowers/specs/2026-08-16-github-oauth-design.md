# GitHub OAuth for Hosted Workbench

## Problem

When `--allow-remote` is enabled, the server has no authentication. Anyone who
can reach the URL can read boards, commit, push, and open PRs. The `gh` CLI
and `git push` rely on whatever credentials exist on the server machine, which
may be none in a hosted environment.

## Goal

Add a GitHub OAuth login flow so a single user can authenticate, and the server
uses their GitHub token for `git push` and `gh pr create`. Tokens are
session-only (in-memory, lost on restart) and never exposed to browser JS.

## Scope

- Single-user deployment (one person logs in with their GitHub account)
- `repo` + `read:org` OAuth scopes
- Session-only tokens (no disk persistence)
- Token invisible to browser JavaScript

## Design

### 1. OAuth Flow

Two new endpoints:

- `GET /auth/login` — Generates a random `state` token, stores it in a short-lived
  cookie, redirects to `https://github.com/login/oauth/authorize` with the
  configured `client_id`, scopes `repo,read:org`, and the state parameter.

- `GET /auth/callback` — Validates that the `state` cookie matches the `state`
  query parameter. Exchanges the authorization `code` for a GitHub access token
  via `POST https://github.com/login/oauth/access_token` (with `client_id`,
  `client_secret`, `code`, `Accept: application/json`). Stores the token in a
  server-side session. Sets an HttpOnly session cookie. Redirects to `/`.

New CLI flags:

- `--github-client-id` — GitHub OAuth App client ID (required for auth)
- `--github-client-secret` — GitHub OAuth App client secret (required for auth)

The server refuses to start in `--allow-remote` mode without both flags.

### 2. Session Management

- Server holds sessions in an in-memory `dict[str, Session]` where `Session`
  contains `token: str`, `username: str`, and `created_at: float`.
- Session ID is a 32-byte random hex string, sent as an `HttpOnly`,
  `SameSite=Lax` cookie named `wb_session`.
- `_allow_request` is extended: when `--allow-remote` is on and GitHub OAuth
  is configured, unauthenticated requests (no valid session cookie) receive a
  401 with `{"ok": false, "error": "authentication required", "login_url": "/auth/login"}`.
  Authenticated requests pass through. Loopback requests are always allowed
  regardless of session state.
- No session expiry beyond server restart.
- `GET /api/auth/status` returns `{"authenticated": true, "username": "..."}` or
  `{"authenticated": false}` so the UI can show login state.

### 3. Git Auth Injection

When a session has a GitHub token, `_run_git` receives it via environment
variables on a per-call basis:

- **`git push`** — Runs with `GIT_CONFIG_COUNT=1`, `GIT_CONFIG_KEY_0=http.extraHeader`,
  `GIT_CONFIG_VALUE_0=Authorization: Bearer <token>`. This makes git use the
  token for HTTPS authentication without embedding it in the remote URL.

- **`gh pr create`** — Runs with `GH_TOKEN=<token>` in the subprocess environment.
  The `gh` CLI uses this for GitHub API authentication.

- **`git checkout`, `git commit`, `git branch`, `git status`, `git rev-parse`**
  — No auth needed, run as before.

The `_run_git` method gains an optional `auth_token: str | None` keyword
argument. Callers that need auth (`_post_push`, `_post_open_pull_request`) pass
the session's token. Callers that don't need auth (`_post_checkout`,
`_post_commit`, `_get_git_status`, `_get_git_branches`) omit it.

Git auth failures are detected when `_run_git` raises `RequestError` and
the error message contains "fatal: Authentication failed" or the gh CLI
returns a non-zero exit with "401" or "authentication" in its output.
These are surfaced as
`{"ok": false, "error": "GitHub authentication expired or insufficient permissions"}`.

### 4. UI Changes

- The git toolbar shows the logged-in GitHub username when authenticated, or a
  "Log in with GitHub" link when not.
- Clicking the link navigates to `/auth/login`.
- The client calls `GET /api/auth/status` on load to determine auth state.
- No changes to board save or local git operations — those don't need auth.

### 5. Security Notes

- Tokens are never stored in localStorage, sessionStorage, or cookies visible
  to JavaScript. The session cookie is HttpOnly.
- The `state` parameter prevents CSRF on the OAuth callback.
- `SameSite=Lax` on the session cookie prevents cross-origin requests from
  carrying it.
- Loopback requests bypass auth (existing behavior preserved).
- The README security note is updated to reflect that the server now handles
  auth natively when `--allow-remote` is used with GitHub OAuth flags.

## Files Changed

- `Tools/HangboardWorkbench/server.py` — OAuth endpoints, session management,
  `_allow_request` extension, `_run_git` auth injection, new CLI flags
- `Tools/HangboardWorkbench/workbench-client.js` — `getAuthStatus()` method,
  login link rendering
- `Tools/HangboardWorkbench/app.js` — Auth state display in git toolbar
- `Tools/HangboardWorkbench/app.html` — Auth status element in toolbar
- `Tools/HangboardWorkbench/tests/test_server.py` — Tests for OAuth flow,
  session management, auth-gated endpoints, git auth injection

## Out of Scope

- Multi-user support
- Token refresh (GitHub tokens don't expire for web apps, but OAuth tokens do;
  re-login is the expected flow)
- Persistent sessions across restarts
- Rate limiting or brute-force protection on auth endpoints
