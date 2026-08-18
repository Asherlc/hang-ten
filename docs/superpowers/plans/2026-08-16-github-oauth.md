# GitHub OAuth for Hosted Workbench Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add GitHub OAuth login so a single user can authenticate to a hosted Workbench server and have `git push` and `gh pr create` use their GitHub token.

**Architecture:** Server-side sessions hold the GitHub token (in-memory, lost on restart). OAuth flow uses standard GitHub redirect. `_run_git` injects the token via `GIT_CONFIG` env vars for push and `GH_TOKEN` for gh CLI. Browser only gets an HttpOnly session cookie.

**Tech Stack:** Python 3.11+, `urllib.request` for token exchange, `http.cookies` for session cookie, standard library only (no new dependencies).

---

## File Structure

| File | Action | Responsibility |
|---|---|---|
| `Tools/HangboardWorkbench/server.py` | Modify | OAuth endpoints, session store, `_allow_request` extension, `_run_git` auth, new CLI flags |
| `Tools/HangboardWorkbench/workbench-client.js` | Modify | `getAuthStatus()` method |
| `Tools/HangboardWorkbench/app.js` | Modify | Auth state display, login link |
| `Tools/HangboardWorkbench/index.html` | Modify | Auth status element in toolbar |
| `Tools/HangboardWorkbench/tests/test_server.py` | Modify | Tests for OAuth, sessions, auth-gated endpoints |

---

### Task 1: Add session store and CLI flags

**Files:**
- Modify: `Tools/HangboardWorkbench/server.py:4-18` (imports)
- Modify: `Tools/HangboardWorkbench/server.py:125-142` (WorkbenchHTTPServer)
- Modify: `Tools/HangboardWorkbench/server.py:650-660` (_argument_parser)
- Modify: `Tools/HangboardWorkbench/server.py:663-680` (_server_from_cli)

- [ ] **Step 1: Add imports**

Add these imports to the top of `server.py`, after the existing `from __future__ import annotations` block:

```python
import hashlib
import os
import secrets
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from http.cookies import SimpleCookie
```

- [ ] **Step 2: Add Session dataclass**

Add after the `_validate_git_arg` function (around line 71):

```python
@dataclass
class _Session:
    token: str
    username: str
    created_at: float = field(default_factory=time.time)
```

- [ ] **Step 3: Add session store to WorkbenchHTTPServer**

Extend `WorkbenchHTTPServer.__init__` to accept and store OAuth config and a session dict. The class currently lives at lines 125-142. Add new attributes:

```python
class WorkbenchHTTPServer(ThreadingHTTPServer):
    """HTTP server containing one selected direct board library."""

    def __init__(
        self,
        server_address: tuple[str, int],
        request_handler: type[BaseHTTPRequestHandler],
        *,
        editor_root: Path,
        library_root: Path,
        allow_remote: bool,
        repository_root: Path,
        github_client_id: str = "",
        github_client_secret: str = "",
    ) -> None:
        self.editor_root = editor_root
        self.library_root = library_root
        self.allow_remote = allow_remote
        self.repository_root = repository_root
        self.github_client_id = github_client_id
        self.github_client_secret = github_client_secret
        self.sessions: dict[str, _Session] = {}
        super().__init__(server_address, request_handler)
```

- [ ] **Step 4: Add CLI flags**

Extend `_argument_parser()` (currently at lines 650-660) with two new flags:

```python
    parser.add_argument(
        "--github-client-id",
        default="",
        help="GitHub OAuth App client ID (required for --allow-remote auth)",
    )
    parser.add_argument(
        "--github-client-secret",
        default="",
        help="GitHub OAuth App client secret (required for --allow-remote auth)",
    )
```

- [ ] **Step 5: Thread new flags through create_server and _server_from_cli**

In `create_server()` (lines 97-122), add `github_client_id` and `github_client_secret` parameters and pass them to `WorkbenchHTTPServer`:

```python
def create_server(
    library_root: Path,
    host: str = "127.0.0.1",
    port: int = 4173,
    *,
    allow_remote: bool = False,
    editor_root: Path = EDITOR_ROOT,
    github_client_id: str = "",
    github_client_secret: str = "",
) -> "WorkbenchHTTPServer":
    # ... existing validation ...
    return WorkbenchHTTPServer(
        (host, port),
        EditorRequestHandler,
        editor_root=resolved_editor_root,
        library_root=resolved_library_root,
        allow_remote=allow_remote,
        repository_root=resolved_library_root.parent,
        github_client_id=github_client_id,
        github_client_secret=github_client_secret,
    )
```

In `_server_from_cli()` (lines 663-680), pass the new args through. Also add validation that `--allow-remote` requires both `--github-client-id` and `--github-client-secret`:

```python
def _server_from_cli() -> "WorkbenchHTTPServer":
    args = _argument_parser().parse_args()
    if args.allow_remote and (not args.github_client_id or not args.github_client_secret):
        _argument_parser().error("--allow-remote requires --github-client-id and --github-client-secret")
    # ... rest unchanged, passing new args to create_server ...
```

- [ ] **Step 6: Commit**

```bash
git add Tools/HangboardWorkbench/server.py
git commit -m "Add session store and GitHub OAuth CLI flags to Workbench server"
```

---

### Task 2: Implement OAuth endpoints

**Files:**
- Modify: `Tools/HangboardWorkbench/server.py` (add _get_cookie, _get_session, _handle_login, _handle_callback, _handle_auth_status methods, and do_GET routing)

- [ ] **Step 1: Add cookie/session helper methods**

Add these methods to `EditorRequestHandler`, after `_allow_request` (around line 510):

```python
    def _get_cookie(self, name: str) -> str | None:
        cookie_header = self.headers.get("Cookie", "")
        cookie = SimpleCookie()
        cookie.load(cookie_header)
        morsel = cookie.get(name)
        return morsel.value if morsel else None

    def _get_session(self) -> _Session | None:
        session_id = self._get_cookie("wb_session")
        if not session_id:
            return None
        return self.server.sessions.get(session_id)

    def _set_session_cookie(self, session_id: str) -> None:
        cookie = SimpleCookie()
        cookie["wb_session"] = session_id
        cookie["wb_session"]["path"] = "/"
        cookie["wb_session"]["httponly"] = True
        cookie["wb_session"]["samesite"] = "Lax"
        self.send_header("Set-Cookie", cookie["wb_session"].OutputString())
```

- [ ] **Step 2: Add _handle_login method**

```python
    def _handle_login(self) -> None:
        if not self.server.github_client_id:
            self._send_json(HTTPStatus.NOT_FOUND, {"ok": False, "error": "GitHub OAuth is not configured"})
            return
        state = secrets.token_hex(32)
        redirect_url = (
            f"https://github.com/login/oauth/authorize"
            f"?client_id={self.server.github_client_id}"
            f"&scope=repo,read:org"
            f"&state={state}"
        )
        self.send_response(HTTPStatus.FOUND)
        self.send_header("Location", redirect_url)
        cookie = SimpleCookie()
        cookie["oauth_state"] = state
        cookie["oauth_state"]["path"] = "/"
        cookie["oauth_state"]["httponly"] = True
        cookie["oauth_state"]["samesite"] = "Lax"
        cookie["oauth_state"]["max_age"] = "600"
        self.send_header("Set-Cookie", cookie["oauth_state"].OutputString())
        self.end_headers()
```

- [ ] **Step 3: Add _handle_callback method**

```python
    def _handle_callback(self) -> None:
        request = urlsplit(self.path)
        params = dict(part.split("=", 1) for part in request.query.split("&") if "=" in part)
        code = params.get("code", "")
        state = params.get("state", "")
        if not code or not state:
            self._send_json(HTTPStatus.BAD_REQUEST, {"ok": False, "error": "Missing code or state"})
            return
        stored_state = self._get_cookie("oauth_state")
        if not stored_state or not secrets.compare_digest(stored_state, state):
            self._send_json(HTTPStatus.BAD_REQUEST, {"ok": False, "error": "Invalid or expired OAuth state"})
            return
        token_data = json.dumps({
            "client_id": self.server.github_client_id,
            "client_secret": self.server.github_client_secret,
            "code": code,
        }).encode("utf-8")
        token_request = urllib.request.Request(
            "https://github.com/login/oauth/access_token",
            data=token_data,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(token_request) as response:
                token_payload = json.loads(response.read())
        except (urllib.error.URLError, json.JSONDecodeError) as error:
            self._send_json(HTTPStatus.BAD_GATEWAY, {"ok": False, "error": "Failed to exchange OAuth code"})
            return
        access_token = token_payload.get("access_token", "")
        if not access_token:
            error_desc = token_payload.get("error_description", "GitHub did not return an access token")
            self._send_json(HTTPStatus.BAD_GATEWAY, {"ok": False, "error": error_desc})
            return
        user_request = urllib.request.Request(
            "https://api.github.com/user",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(user_request) as response:
                user_payload = json.loads(response.read())
        except (urllib.error.URLError, json.JSONDecodeError):
            self._send_json(HTTPStatus.BAD_GATEWAY, {"ok": False, "error": "Failed to fetch GitHub user info"})
            return
        username = user_payload.get("login", "unknown")
        session_id = secrets.token_hex(32)
        self.server.sessions[session_id] = _Session(token=access_token, username=username)
        self.send_response(HTTPStatus.FOUND)
        self.send_header("Location", "/")
        self._set_session_cookie(session_id)
        self.end_headers()
```

- [ ] **Step 4: Add _handle_auth_status method**

```python
    def _handle_auth_status(self) -> None:
        session = self._get_session()
        if session:
            self._send_json(HTTPStatus.OK, {"ok": True, "authenticated": True, "username": session.username})
        else:
            self._send_json(HTTPStatus.OK, {"ok": True, "authenticated": False})
```

- [ ] **Step 5: Add routing for /auth/login, /auth/callback, /api/auth/status in do_GET**

Extend the `do_GET` method (currently at lines 146-175). Add these routes before the existing `/api/health` route:

```python
    def do_GET(self) -> None:
        request = urlsplit(self.path)
        path = request.path
        if path == "/auth/login":
            self._handle_login()
            return
        if path == "/auth/callback":
            self._handle_callback()
            return
        if path == "/api/auth/status":
            if not self._allow_request(mutation=False):
                return
            self._handle_auth_status()
            return
        if not self._allow_request(mutation=False):
            return
        # ... existing routes unchanged ...
```

Note: `/auth/login` and `/auth/callback` must be routed BEFORE the `_allow_request` check since they are the entry points for unauthenticated users.

- [ ] **Step 6: Commit**

```bash
git add Tools/HangboardWorkbench/server.py
git commit -m "Add GitHub OAuth login, callback, and auth status endpoints"
```

---

### Task 3: Extend _allow_request for session auth

**Files:**
- Modify: `Tools/HangboardWorkbench/server.py:491-510` (_allow_request)

- [ ] **Step 1: Modify _allow_request to check session**

Replace the current `_allow_request` method (lines 491-510) with:

```python
    def _allow_request(self, *, mutation: bool) -> bool:
        if self.server.allow_remote:
            if self.server.github_client_id:
                session = self._get_session()
                if session is None:
                    self._send_json(
                        HTTPStatus.UNAUTHORIZED,
                        {"ok": False, "error": "authentication required", "login_url": "/auth/login"},
                    )
                    return False
            return True
        if not _loopback_peer(self.client_address):
            self._send_json(HTTPStatus.FORBIDDEN, {"ok": False, "error": "request origin is not allowed"})
            return False
        host_values = self.headers.get_all("Host", [])
        host = _loopback_authority(host_values[0], self.server.server_port) if len(host_values) == 1 else None
        if host is not None and mutation:
            origin_values = self.headers.get_all("Origin", [])
            if origin_values:
                origin = _loopback_origin(origin_values[0], self.server.server_port) if len(origin_values) == 1 else None
                if origin != host:
                    host = None
            elif self.headers.get("Sec-Fetch-Site") is not None:
                host = None
        if host is not None:
            return True
        self._send_json(HTTPStatus.FORBIDDEN, {"ok": False, "error": "request origin is not allowed"})
        return False
```

Key changes:
- When `allow_remote` is on and `github_client_id` is set, require a valid session cookie.
- When `allow_remote` is on but no OAuth is configured, allow all requests (backwards compatible).
- Loopback requests always bypass auth (existing behavior preserved).

- [ ] **Step 2: Commit**

```bash
git add Tools/HangboardWorkbench/server.py
git commit -m "Gate remote requests on GitHub session when OAuth is configured"
```

---

### Task 4: Inject auth token into git operations

**Files:**
- Modify: `Tools/HangboardWorkbench/server.py:473-489` (_run_git)
- Modify: `Tools/HangboardWorkbench/server.py:310-321` (_post_push)
- Modify: `Tools/HangboardWorkbench/server.py:323-366` (_post_open_pull_request)

- [ ] **Step 1: Extend _run_git with auth_token parameter**

Replace the `_run_git` method (lines 473-489) with:

```python
    def _run_git(
        self,
        args: list[str],
        *,
        fallback: str = "command failed",
        auth_token: str | None = None,
    ) -> subprocess.CompletedProcess[str]:
        env = None
        if auth_token:
            env = os.environ.copy()
            if args[0] == "git" and len(args) > 1 and args[1] == "push":
                env["GIT_CONFIG_COUNT"] = "1"
                env["GIT_CONFIG_KEY_0"] = "http.extraHeader"
                env["GIT_CONFIG_VALUE_0"] = f"Authorization: Bearer {auth_token}"
            elif args[0] == "gh":
                env["GH_TOKEN"] = auth_token
        try:
            process = subprocess.run(
                args,
                cwd=self.server.repository_root,
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                env=env,
            )
        except OSError as error:
            raise RequestError(HTTPStatus.INTERNAL_SERVER_ERROR, fallback) from error
        if process.returncode != 0:
            message = process.stderr.strip() or process.stdout.strip() or fallback
            if auth_token and ("Authentication failed" in message or "401" in message):
                raise RequestError(HTTPStatus.UNAUTHORIZED, "GitHub authentication expired or insufficient permissions")
            raise RequestError(HTTPStatus.BAD_REQUEST, _safe_message(RuntimeError(message), fallback))
        return process
```

- [ ] **Step 2: Add _get_auth_token helper**

Add this method to `EditorRequestHandler`, after `_get_session`:

```python
    def _get_auth_token(self) -> str | None:
        session = self._get_session()
        return session.token if session else None
```

- [ ] **Step 3: Pass auth token in _post_push**

Update `_post_push` (lines 310-321) to pass the token:

```python
    def _post_push(self, body: dict[str, Any]) -> None:
        remote = body.get("remote", "origin")
        if not isinstance(remote, str):
            raise RequestError(HTTPStatus.BAD_REQUEST, "remote must be a string")
        remote = remote.strip() or "origin"
        _validate_git_arg(remote, "remote")
        branch = self._git_current_branch()
        self._run_git(
            ["git", "push", "--set-upstream", remote, branch],
            fallback="could not push branch",
            auth_token=self._get_auth_token(),
        )
        self._send_json(HTTPStatus.OK, {"ok": True, "branch": branch, "remote": remote})
```

- [ ] **Step 4: Pass auth token in _post_open_pull_request**

Update `_post_open_pull_request` (lines 323-366) to pass the token to the `gh pr create` call. Only the `_run_git` call for `gh pr create` needs the token — add `auth_token=self._get_auth_token()` to that call.

- [ ] **Step 5: Commit**

```bash
git add Tools/HangboardWorkbench/server.py
git commit -m "Inject GitHub token into git push and gh pr create via env vars"
```

---

### Task 5: Add client-side auth support

**Files:**
- Modify: `Tools/HangboardWorkbench/workbench-client.js` (add getAuthStatus)

- [ ] **Step 1: Add getAuthStatus method**

Add this method in `workbench-client.js`, after the existing `getGitStatus` method (around line 75):

```javascript
  async function getAuthStatus() {
    try {
      const payload = await request("/api/auth/status");
      return payload;
    } catch {
      return { ok: true, authenticated: false };
    }
  }
```

- [ ] **Step 2: Export getAuthStatus**

Add `getAuthStatus` to the `Object.freeze` export (around line 135):

```javascript
  return Object.freeze({
    getBoard, listBoards, saveBoard,
    getGitStatus, listBranches, switchBranch,
    commitBoardChanges, pushBranch, openPullRequest,
    getAuthStatus,
  });
```

- [ ] **Step 3: Commit**

```bash
git add Tools/HangboardWorkbench/workbench-client.js
git commit -m "Add getAuthStatus to workbench client library"
```

---

### Task 6: Update UI for auth state

**Files:**
- Modify: `Tools/HangboardWorkbench/index.html:25-34` (git toolbar)
- Modify: `Tools/HangboardWorkbench/app.js` (auth state, login link)

- [ ] **Step 1: Add auth status element to index.html**

Add an auth status element at the start of the git toolbar div in `index.html` (before line 26):

```html
        <div class="toolbar git-toolbar" aria-label="Repository tools">
          <span class="eyebrow" id="git-auth-status"></span>
          <span class="eyebrow" id="git-status">Repository status</span>
          <!-- ... rest unchanged ... -->
```

- [ ] **Step 2: Add auth state to app.js**

In `app.js`, add auth state to the `state` object (find where `state` is initialized, around line 45):

```javascript
  const state = {
    board: null,
    currentBranch: null,
    branches: [],
    hasUncommittedChanges: false,
    authenticated: false,
    username: null,
  };
```

- [ ] **Step 3: Add refreshAuthState function in app.js**

Add this function after `refreshGitState` (around line 262):

```javascript
  async function refreshAuthState() {
    try {
      const status = await client.getAuthStatus();
      state.authenticated = Boolean(status.authenticated);
      state.username = status.username || null;
    } catch {
      state.authenticated = false;
      state.username = null;
    }
    renderAuthState();
  }

  function renderAuthState() {
    const el = document;
    if (state.authenticated && state.username) {
      el.getElementById("git-auth-status").textContent = `Logged in as ${state.username}`;
      el.getElementById("git-auth-status").onclick = null;
    } else {
      el.getElementById("git-auth-status").innerHTML = '<a href="/auth/login">Log in with GitHub</a>';
    }
  }
```

- [ ] **Step 4: Call refreshAuthState on load**

In the IIFE at the bottom of `app.js` (around line 451), add `refreshAuthState()` before `refreshGitState()`:

```javascript
  void (async () => {
    await refreshAuthState();
    await gitOperations.perform(async () => {
      await refreshGitState();
    });
    await refreshBoards();
  })();
```

- [ ] **Step 5: Commit**

```bash
git add Tools/HangboardWorkbench/index.html Tools/HangboardWorkbench/app.js
git commit -m "Show GitHub auth state and login link in Workbench toolbar"
```

---

### Task 7: Add tests

**Files:**
- Modify: `Tools/HangboardWorkbench/tests/test_server.py`

- [ ] **Step 1: Add a running_server variant with OAuth configured**

Add this helper near the existing `running_server` function (around line 112):

```python
@contextmanager
def running_server_with_oauth(library: Path, *, fake_token: str = "ghp_test_token_123") -> Iterator[tuple[str, str]]:
    """Start a server with OAuth configured. Yields (base_url, fake_token)."""
    httpd = create_server(
        library,
        port=0,
        allow_remote=True,
        github_client_id="test-client-id",
        github_client_secret="test-client-secret",
    )
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{httpd.server_port}", fake_token
    finally:
        httpd.shutdown()
        thread.join(timeout=5)
        httpd.close()
```

- [ ] **Step 2: Add test for unauthenticated remote request returns 401**

```python
def test_remote_request_without_session_returns_401(tmp_path: Path) -> None:
    checkout = _git_checkout(tmp_path)

    with running_server_with_oauth(checkout / "Hangboards") as (base, _token):
        status, payload = request_json(base, "GET", "/api/git/status")

    assert status == 401
    assert payload["error"] == "authentication required"
    assert payload["login_url"] == "/auth/login"
```

- [ ] **Step 3: Add test for auth status endpoint**

```python
def test_auth_status_returns_unauthenticated_by_default(tmp_path: Path) -> None:
    checkout = _git_checkout(tmp_path)

    with running_server_with_oauth(checkout / "Hangboards") as (base, _token):
        status, payload = request_json(base, "GET", "/api/auth/status")

    assert status == 200
    assert payload["authenticated"] is False
```

- [ ] **Step 4: Add test for auth status with valid session**

```python
def test_auth_status_returns_username_with_valid_session(tmp_path: Path) -> None:
    checkout = _git_checkout(tmp_path)

    with running_server_with_oauth(checkout / "Hangboards") as (base, _token):
        httpd = create_server(
            checkout / "Hangboards",
            port=0,
            allow_remote=True,
            github_client_id="test-client-id",
            github_client_secret="test-client-secret",
        )
        session_id = secrets.token_hex(32)
        httpd.sessions[session_id] = _Session(token="ghp_fake", username="testuser")
        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()
        try:
            real_base = f"http://127.0.0.1:{httpd.server_port}"
            import http.cookiejar
            cookie_jar = http.cookiejar.CookieJar()
            opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookie_jar))
            cookie = http.cookiejar.Cookie(
                version=0, name="wb_session", value=session_id,
                port=None, port_specified=False,
                domain=f"127.0.0.1:{httpd.server_port}", domain_specified=True, domain_initial_dot=False,
                path="/", path_specified=True,
                secure=False, expires=int(time.time()) + 3600,
                discard=False, comment=None, comment_url=None,
                rest={}, rfc2109=False,
            )
            cookie_jar.set_cookie(cookie)
            request = urllib.request.Request(f"{real_base}/api/auth/status")
            with opener.open(request) as response:
                payload = json.loads(response.read())
            assert payload["authenticated"] is True
            assert payload["username"] == "testuser"
        finally:
            httpd.shutdown()
            thread.join(timeout=5)
            httpd.close()
```

- [ ] **Step 5: Add test for login redirect**

```python
def test_login_redirects_to_github(tmp_path: Path) -> None:
    checkout = _git_checkout(tmp_path)

    with running_server_with_oauth(checkout / "Hangboards") as (base, _token):
        request = urllib.request.Request(f"{base}/auth/login")
        try:
            opener = urllib.request.build_opener(urllib.request.HTTPRedirectHandler())
            opener.open(request)
        except urllib.error.HTTPError as error:
            assert error.code == 302
            location = error.headers.get("Location", "")
            assert "github.com/login/oauth/authorize" in location
            assert "client_id=test-client-id" in location
            assert "scope=repo,read:org" in location
```

- [ ] **Step 6: Add test for login without OAuth configured returns 404**

```python
def test_login_without_oauth_configured_returns_404(tmp_path: Path) -> None:
    checkout = _git_checkout(tmp_path)

    with running_server(checkout / "Hangboards") as base:
        status, payload = request_json(base, "GET", "/auth/login")

    assert status == 404
```

- [ ] **Step 7: Commit**

```bash
git add Tools/HangboardWorkbench/tests/test_server.py
git commit -m "Add tests for GitHub OAuth flow and session auth gating"
```

---

### Task 8: Update README

**Files:**
- Modify: `Tools/HangboardWorkbench/README.md`

- [ ] **Step 1: Update README to document OAuth setup**

Replace the security note section (around lines 51-58) with:

```markdown
The PR action expects `gh` to be available in the server environment and logged
into GitHub with permission to create pull requests. Alternatively, start the
server with `--github-client-id` and `--github-client-secret` (from a GitHub
OAuth App) to enable browser-based login. Once logged in, `git push` and
`gh pr create` use the authenticated user's token automatically.

To set up a GitHub OAuth App:
1. Go to https://github.com/settings/developers
2. Create a new OAuth App with the callback URL set to `http://<your-host>/auth/callback`
3. Start the server with `--allow-remote --github-client-id <id> --github-client-secret <secret>`
```

- [ ] **Step 2: Commit**

```bash
git add Tools/HangboardWorkbench/README.md
git commit -m "Document GitHub OAuth setup in Workbench README"
```
