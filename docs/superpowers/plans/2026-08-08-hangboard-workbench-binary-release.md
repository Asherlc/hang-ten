# Hangboard Workbench Binary Release Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use a fresh subagent for every implementation or configuration task, with separate implementation and review checkpoints for each task. Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the repository-backed workbench as a dependency-free Apple Silicon macOS executable and publish a verified immutable GitHub Release after every successful push to `main`.

**Architecture:** A focused packaged entrypoint reuses the existing server factory while resolving frozen static resources explicitly. A deterministic PyInstaller build script embeds the required workbench modules, one shared UI asset manifest, and source commit into one arm64 executable without collecting product or evidence resources. GitHub Actions builds and smoke-tests the real executable on pull requests and publishes checksummed release assets only for `main` pushes.

**Tech Stack:** Python 3.12, PyInstaller 6.22.0, existing Python `http.server` workbench, OpenCV/NumPy/Pillow/Requests, Node test runner, GitHub Actions on `macos-15`, GitHub CLI releases.

## Global Constraints

- The first binary target is Apple Silicon macOS (`arm64`) only.
- The released executable must require no Python, Node, OpenCV, NumPy, Pillow, Requests, or application dependency installation.
- The checkout remains the authoritative source for `Tools/HangboardOnboarding/boards/`; committed board packages must not be embedded.
- `hangboard_vectorizer.products` and `hangboard_vectorizer.evidence` resources must not be collected; only required workbench modules, shared-manifest UI assets, and build metadata are explicit application inputs.
- Drafts remain under `.context/hangboard-workbench/`, and canonical publication paths and schemas must not change.
- Visual algorithms, protected visual outputs, and the product-neutral pipeline must remain unchanged.
- Every successful push to `main` publishes one immutable release; failed verification publishes none.
- Pull requests build and smoke-test the binary without publishing.
- Signing, notarization, Intel macOS, Linux, and Windows are out of scope.

## File Structure

- Create `Tools/hold-highlight-editor/workbench_binary.py`: packaged-only startup, version reporting, browser launch, and frozen resource selection.
- Create `Tools/hold-highlight-editor/workbench_assets.py`: one explicit static route and asset manifest shared by serving, validation, packaging, tests, and CI.
- Modify `Tools/hold-highlight-editor/server.py`: accept an explicit static resource root without changing API or workflow behavior.
- Create `Tools/hold-highlight-editor/tests/test_workbench_binary.py`: unit tests for packaged startup and version/resource behavior.
- Modify `Tools/hold-highlight-editor/tests/test_server.py`: prove static assets come from the server instance's configured resource root.
- Create `Tools/hold-highlight-editor/packaging/build.py`: deterministic PyInstaller invocation and build-input validation.
- Create `Tools/hold-highlight-editor/tests/test_workbench_packaging.py`: validate the build manifest without requiring PyInstaller in the unit-test process.
- Create `Tools/hold-highlight-editor/tests/test_workbench_release_workflow.py`: parse the workflow, syntax-check extracted shell, and enforce smoke, permission, and Latest policies.
- Create `.github/workflows/hangboard-workbench-release.yml`: PR build gate and immutable `main` release publication.
- Modify `Tools/hold-highlight-editor/README.md`: binary quick start, checksum, flags, and Gatekeeper note.
- Modify `Tools/HangboardOnboarding/README.md`: point workbench users to the released binary while preserving source instructions.

---

### Task 1: Frozen resource seam and packaged entrypoint

**Files:**
- Create: `Tools/hold-highlight-editor/workbench_binary.py`
- Modify: `Tools/hold-highlight-editor/server.py:33,283-345,380,1032-1050,1080-1137`
- Create: `Tools/hold-highlight-editor/tests/test_workbench_binary.py`
- Modify: `Tools/hold-highlight-editor/tests/test_server.py`

**Interfaces:**
- Consumes: `server._server_from_cli(arguments: list[str] | None = None, *, editor_root: Path = EDITOR_ROOT) -> tuple[WorkbenchHTTPServer, EditorCatalog | None]`.
- Produces: `workbench_binary._resource_root() -> Path`, `_build_commit(root: Path) -> str`, `_packaged_arguments(arguments: list[str]) -> tuple[bool, bool, list[str]]`, and `_run(arguments: list[str], *, server_factory: Callable[..., tuple[WorkbenchHTTPServer, EditorCatalog | None]], browser_open: Callable[[str], bool]) -> int`.
- Produces: `create_server(..., editor_root: Path = EDITOR_ROOT) -> ThreadingHTTPServer`; `WorkbenchHTTPServer.editor_root: Path` is the only static-asset root used by handlers.

- [ ] **Step 1: Write failing server resource-root tests**

Add a test that creates a temporary editor root containing a unique
`index.html`, starts `create_server(..., editor_root=temporary_root)`, requests
`/`, and asserts the unique bytes are returned. Also assert a missing requested
static asset returns a safe HTTP error without exposing the absolute temporary
path.

```python
def test_server_uses_configured_editor_root(tmp_path):
    editor_root = tmp_path / "embedded-editor"
    editor_root.mkdir()
    (editor_root / "index.html").write_text("frozen editor", encoding="utf-8")
    service = FakeWorkbenchService(tmp_path / "workbench")
    with running_server(
        make_run(tmp_path / "legacy"),
        service,
        editor_root=editor_root,
    ) as base:
        status, body = request(base, "/")
    assert status == 200
    assert body == b"frozen editor"
```

- [ ] **Step 2: Run the focused server test and verify it fails**

Run:

```bash
rtk python -m pytest Tools/hold-highlight-editor/tests/test_server.py::test_server_uses_configured_editor_root -q
```

Expected: FAIL because `create_server()` and the test helper do not accept
`editor_root` and the handler still reads global `EDITOR_ROOT`.

- [ ] **Step 3: Route all static assets through the server instance**

Add the keyword-only `editor_root` parameter to `create_server`, resolve it
without requiring the path to live in the checkout, pass it to
`WorkbenchHTTPServer`, and use `self.server.editor_root / filename` in
`EditorRequestHandler.do_GET`. Thread the same root from `_server_from_cli`.
Keep `EDITOR_ROOT` as the source-mode default.

```python
def create_server(..., editor_root: Path = EDITOR_ROOT) -> ThreadingHTTPServer:
    ...
    return WorkbenchHTTPServer(
        (host, port),
        SessionHandler,
        editor_root=editor_root,
        ...,
    )

class WorkbenchHTTPServer(ThreadingHTTPServer):
    def __init__(..., editor_root: Path, ...) -> None:
        self.editor_root = Path(editor_root).resolve(strict=False)
        ...

# Handler
self._send_file(self.server.editor_root / filename)
```

Change `_create_workbench_service` to try importing the installed
`hangboard_vectorizer` package first and add the source `src` path only when the
package is unavailable. Do not derive import behavior from the frozen asset
root.

- [ ] **Step 4: Run the focused server tests**

Run:

```bash
rtk python -m pytest Tools/hold-highlight-editor/tests/test_server.py -q
```

Expected: all server tests PASS.

- [ ] **Step 5: Write failing packaged-entrypoint tests**

Create tests using a fake server factory and fake browser callable. Cover:

```python
def test_resource_root_uses_meipass(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)
    assert workbench_binary._resource_root() == tmp_path.resolve()

def test_version_reads_exact_embedded_commit(tmp_path, capsys):
    commit = "a" * 40
    (tmp_path / "build-commit.txt").write_text(commit + "\n", encoding="ascii")
    assert workbench_binary._build_commit(tmp_path) == commit

def test_run_opens_browser_and_forwards_server_arguments(tmp_path):
    server = FakeServer(("127.0.0.1", 4317))
    result = workbench_binary._run(
        ["--repository-root", str(tmp_path), "--port", "4317"],
        server_factory=recording_factory(server),
        browser_open=recording_browser,
    )
    assert result == 0
    assert forwarded == ["--repository-root", str(tmp_path), "--port", "4317"]
    assert opened == ["http://127.0.0.1:4317/"]
    assert server.served and server.closed

def test_no_open_skips_browser(): ...
def test_browser_failure_prints_url_and_keeps_serving(): ...
def test_version_rejects_missing_or_invalid_build_metadata(): ...
```

The fake server's `serve_forever()` returns immediately so the test proves
lifecycle behavior without opening a socket.

- [ ] **Step 6: Run entrypoint tests and verify they fail**

Run:

```bash
rtk python -m pytest Tools/hold-highlight-editor/tests/test_workbench_binary.py -q
```

Expected: FAIL because `workbench_binary.py` does not exist.

- [ ] **Step 7: Implement the packaged entrypoint**

Implement the private helpers and a thin `main()`:

```python
def _resource_root() -> Path:
    frozen_root = getattr(sys, "_MEIPASS", None)
    return (
        Path(frozen_root).resolve(strict=False)
        if frozen_root is not None
        else Path(__file__).resolve().parent
    )

def _build_commit(root: Path) -> str:
    path = root / "build-commit.txt"
    try:
        value = path.read_text(encoding="ascii").strip()
    except OSError as error:
        raise PackagedWorkbenchError("embedded build metadata is missing") from error
    if re.fullmatch(r"[0-9a-f]{40}", value) is None:
        raise PackagedWorkbenchError("embedded build metadata is invalid")
    return value

def _packaged_arguments(arguments: list[str]) -> tuple[bool, bool, list[str]]:
    parser = ArgumentParser(add_help=False)
    parser.add_argument("--no-open", action="store_true")
    parser.add_argument("--version", action="store_true")
    packaged, forwarded = parser.parse_known_args(arguments)
    return packaged.no_open, packaged.version, forwarded
```

`_run` passes `editor_root=_resource_root()` to the server factory, prints
`Hangboard Workbench: <url>` with `flush=True`, opens the browser unless
disabled, serves until interrupted, and always closes the server. `main()`
turns `PackagedWorkbenchError`, `EditorError`, and `OSError` into a concise
stderr message and exit status 2 without printing frozen temporary paths.

- [ ] **Step 8: Run the entrypoint and server tests**

Run:

```bash
rtk python -m pytest Tools/hold-highlight-editor/tests/test_workbench_binary.py Tools/hold-highlight-editor/tests/test_server.py -q
```

Expected: PASS.

- [ ] **Step 9: Commit Task 1**

```bash
rtk git add Tools/hold-highlight-editor/server.py Tools/hold-highlight-editor/workbench_binary.py Tools/hold-highlight-editor/tests/test_server.py Tools/hold-highlight-editor/tests/test_workbench_binary.py
rtk git commit -m "Add packaged workbench entrypoint"
```

---

### Task 2: Deterministic PyInstaller build

**Files:**
- Create: `Tools/hold-highlight-editor/packaging/build.py`
- Create: `Tools/hold-highlight-editor/tests/test_workbench_packaging.py`
- Modify: `.gitignore`

**Interfaces:**
- Consumes: `workbench_binary.py` and the static assets enumerated by `workbench_assets.py`.
- Produces: `packaging/build.py --commit <40-hex-sha> --dist-dir <path> --work-dir <path>` and `<dist-dir>/hangboard-workbench`.
- Produces: `_pyinstaller_arguments(repository_root: Path, metadata_root: Path, dist_dir: Path, work_dir: Path) -> list[str]`, which is testable without importing PyInstaller.

- [ ] **Step 1: Write failing packaging-manifest tests**

Create tests that load `packaging/build.py` with `importlib.util` and assert:

```python
def test_pyinstaller_arguments_embed_only_runtime_inputs(tmp_path):
    arguments = build._pyinstaller_arguments(REPOSITORY_ROOT, metadata, dist, work)
    joined = "\n".join(arguments)
    for asset in workbench_assets.STATIC_ASSETS:
        assert asset in joined
    assert "hangboard_vectorizer" in joined
    assert "Tools/HangboardOnboarding/boards" not in joined
    assert "/tests/" not in joined

def test_commit_must_be_exact_lowercase_sha(): ...
def test_build_metadata_contains_the_requested_commit_only(): ...
```

- [ ] **Step 2: Run packaging tests and verify they fail**

Run:

```bash
rtk python -m pytest Tools/hold-highlight-editor/tests/test_workbench_packaging.py -q
```

Expected: FAIL because the build module does not exist.

- [ ] **Step 3: Implement the deterministic build module**

The module validates the source layout and SHA, creates
`<work-dir>/metadata/build-commit.txt` atomically, then imports
`PyInstaller.__main__` only inside `_build()` and invokes it with explicit
arguments:

```python
arguments = [
    str(editor_root / "workbench_binary.py"),
    "--name", "hangboard-workbench",
    "--onefile", "--noconfirm", "--clean",
    "--target-architecture", "arm64",
    "--distpath", str(dist_dir),
    "--workpath", str(work_dir / "pyinstaller"),
    "--specpath", str(work_dir / "spec"),
    "--paths", str(onboarding_root / "src"),
    "--hidden-import", "hangboard_vectorizer.workbench",
    "--hidden-import", "hangboard_vectorizer.workbench_store",
    "--hidden-import", "hangboard_vectorizer.board_library",
]
```

Append one `--add-data`, `<source>:<destination>` pair for each asset in the
shared static manifest and for `build-commit.txt`. Do not use `--collect-data`
for `hangboard_vectorizer` and do not add product or evidence resources. Reject
a non-Darwin host or non-arm64 machine before invoking PyInstaller. After the
build, require exactly one executable at the expected output path.

Add PyInstaller `build/`, `dist/`, and generated `*.spec` paths under the editor
packaging directory to `.gitignore` without ignoring release source files.

- [ ] **Step 4: Run packaging tests**

Run:

```bash
rtk python -m pytest Tools/hold-highlight-editor/tests/test_workbench_packaging.py -q
```

Expected: PASS without PyInstaller installed because the tests exercise
validation and argument construction only.

- [ ] **Step 5: Build and smoke-test locally on Apple Silicon**

Create an isolated environment outside the repository and install the pinned
build dependencies:

```bash
rtk python -m venv /tmp/hangboard-workbench-build-venv
rtk /tmp/hangboard-workbench-build-venv/bin/python -m pip install --upgrade pip
rtk /tmp/hangboard-workbench-build-venv/bin/python -m pip install -e 'Tools/HangboardOnboarding[dev]' 'pyinstaller==6.22.0'
rtk git rev-parse HEAD
rtk /tmp/hangboard-workbench-build-venv/bin/python Tools/hold-highlight-editor/packaging/build.py --commit 9549e12f8628b63da17816cb71cafd83925a2511 --dist-dir /tmp/hangboard-workbench-dist --work-dir /tmp/hangboard-workbench-build
rtk file /tmp/hangboard-workbench-dist/hangboard-workbench
rtk /tmp/hangboard-workbench-dist/hangboard-workbench --version
```

Expected: `file` reports an arm64 Mach-O executable and `--version` prints the
exact HEAD SHA. Replace the example commit argument with the literal
40-character SHA printed by the preceding `rtk git rev-parse HEAD` command.

Launch the binary from the repository root on isolated ports, request
`/api/library`, `/`, and every shared-manifest asset, then stop separate frozen
parent/child pairs with `SIGINT` and `SIGTERM`. Require exit zero, no remaining
process, and no traceback for both.

- [ ] **Step 6: Commit Task 2**

```bash
rtk git add .gitignore Tools/hold-highlight-editor/packaging/build.py Tools/hold-highlight-editor/tests/test_workbench_packaging.py
rtk git commit -m "Package workbench as arm64 binary"
```

---

### Task 3: CI build gate and immutable releases

**Files:**
- Create: `.github/workflows/hangboard-workbench-release.yml`

**Interfaces:**
- Consumes: `packaging/build.py --commit/--dist-dir/--work-dir` and `workbench_binary.py --version/--no-open`.
- Produces: workflow artifact `hangboard-workbench-release-<run-id>` containing `hangboard-workbench-macos-arm64.tar.gz` and `hangboard-workbench-macos-arm64.sha256`.
- Produces on `main`: tag `hangboard-workbench-main-<run-number>-<short-sha>` and an immutable GitHub Release for the exact `github.sha`, marked Latest only if that SHA is still the current `refs/heads/main` tip.

- [ ] **Step 1: Add the build-and-release workflow**

Create triggers for `pull_request` targeting `main`, `push` to `main`, and
`workflow_dispatch`. Set top-level `contents: read`, serialize with
`concurrency.group: hangboard-workbench-release-${{ github.ref }}`, and do not
cancel in-progress main builds.

The `build` job uses `macos-15`, checkout pinned to
`3d3c42e5aac5ba805825da76410c181273ba90b1`, and setup-python pinned to
`ece7cb06caefa5fff74198d8649806c4678c61a1` with
`python-version: '3.12'`. It installs:

```yaml
- name: Install workbench build dependencies
  run: |
    set -euo pipefail
    python -m pip install --upgrade pip
    python -m pip install -e 'Tools/HangboardOnboarding[dev]' 'pyinstaller==6.22.0'
```

Run the full focused Python and Node suites, build with `--commit "$GITHUB_SHA"`,
check `uname -m` and `file`, and require `--version` output to contain the exact
SHA.

- [ ] **Step 2: Add the executable smoke gate and cleanup**

Run the binary from `$GITHUB_WORKSPACE` with `--no-open` on isolated ports,
redirect logs under `$RUNNER_TEMP`, and install a shell `trap` that stops and
waits for the exact owned PID on every exit. For both `SIGINT` and `SIGTERM`,
poll up to 30 seconds, request every static asset supplied by the shared
manifest, and require `/` plus `/api/library`:

```bash
curl --fail --silent --show-error http://127.0.0.1:41739/ >/dev/null
curl --fail --silent --show-error http://127.0.0.1:41739/api/library \
  | python -c 'import json,sys; payload=json.load(sys.stdin); assert payload["ok"] is True'
```

Fail if the process exits before readiness or does not exit zero after its
signal. Require that neither frozen parent nor child remains and that the
confined log contains no traceback or packaged startup error.

- [ ] **Step 3: Archive, checksum, and upload the verified assets**

Create the archive from its parent directory so the tar contains only
`hangboard-workbench`, then run `shasum -a 256` from the release directory so
the checksum contains a basename. Verify the checksum before uploading with
`actions/upload-artifact` pinned to
`ea165f8d65b6e75b540449e92b4886f43607fa02`.

- [ ] **Step 4: Publish only verified `main` pushes**

Add a separate `release` job with:

```yaml
if: github.event_name == 'push' && github.ref == 'refs/heads/main'
needs: build
permissions:
  contents: write
```

Download the artifact with `actions/download-artifact` pinned to
`634f93cb2916e3fdff6788551b99b062d0335ce0`, verify the checksum again, derive
`short_sha="${GITHUB_SHA::12}"`, and create the release:

```bash
tag="hangboard-workbench-main-${GITHUB_RUN_NUMBER}-${short_sha}"
gh release create "$tag" \
  hangboard-workbench-macos-arm64.tar.gz \
  hangboard-workbench-macos-arm64.sha256 \
  --repo "$GITHUB_REPOSITORY" \
  --target "$GITHUB_SHA" \
  --title "Hangboard Workbench ${short_sha}" \
  --notes "Dependency-free Apple Silicon workbench built from ${GITHUB_SHA}." \
  "$latest_flag"
```

Use `GH_TOKEN: ${{ github.token }}` only on this step. Before creating, fail if
the tag or release already exists at a different commit; treat an existing
release at the exact commit as an idempotent rerun only after both named assets
are present. Immediately before a new release, resolve `refs/heads/main` and
set `latest_flag` to `--latest` only when it equals `GITHUB_SHA`; otherwise pass
`--latest=false` so an older retried run cannot displace a newer release.

- [ ] **Step 5: Validate workflow syntax and policy locally**

Run:

```bash
rtk ruby -e 'require "yaml"; YAML.load_file(".github/workflows/hangboard-workbench-release.yml", aliases: true); puts "valid yaml"'
rtk rg -n 'macos-15|pyinstaller==6.22.0|contents: write|gh release create|api/library|shasum -a 256' .github/workflows/hangboard-workbench-release.yml
```

Expected: valid YAML and valid extracted build/release shell; `contents: write`
appears only in the conditional release job; the build job covers every shared
static asset, both signals, clean parent/child teardown, and traceback checks;
policy tests exercise both conditional Latest branches.

- [ ] **Step 6: Commit Task 3**

```bash
rtk git add .github/workflows/hangboard-workbench-release.yml
rtk git commit -m "Release workbench binary from CI"
```

---

### Task 4: Distribution documentation and final verification

**Files:**
- Modify: `Tools/hold-highlight-editor/README.md`
- Modify: `Tools/HangboardOnboarding/README.md`

**Interfaces:**
- Consumes: release asset names and CLI behavior from Tasks 1-3.
- Produces: exact download, checksum, launch, override, and Gatekeeper guidance for end users.

- [ ] **Step 1: Document the binary quick start**

Add a binary-first section before source-development instructions. Use exact
commands with a release directory placeholder only in the URL, not the asset
names:

```bash
shasum -a 256 -c hangboard-workbench-macos-arm64.sha256
tar -xzf hangboard-workbench-macos-arm64.tar.gz
./hangboard-workbench
```

Explain that the executable must run from a Hang Ten checkout or receive
`--repository-root`, that it opens the browser automatically, and that
`--no-open`, `--port`, `--workspace-root`, and `--version` are available.
Keep the source command as the development path.

Add a concise unsigned-download note: if Gatekeeper blocks the first launch,
use Finder's **Open** context-menu action; do not recommend disabling Gatekeeper
globally.

- [ ] **Step 2: Run documentation and whitespace checks**

Run:

```bash
rtk rg -n 'hangboard-workbench-macos-arm64|--no-open|--version|Gatekeeper' Tools/hold-highlight-editor/README.md Tools/HangboardOnboarding/README.md
rtk git diff --check
```

Expected: both READMEs point to the same artifact and CLI names; no whitespace
errors.

- [ ] **Step 3: Run all focused tests and syntax checks**

Run:

```bash
rtk python -m pytest Tools/HangboardOnboarding/tests Tools/hold-highlight-editor/tests -q
rtk node --test Tools/hold-highlight-editor/tests/*.test.js
rtk python -m compileall -q Tools/HangboardOnboarding/src Tools/hold-highlight-editor/server.py Tools/hold-highlight-editor/workbench_binary.py Tools/hold-highlight-editor/packaging/build.py
rtk node --check Tools/hold-highlight-editor/app.js
rtk node --check Tools/hold-highlight-editor/workbench-client.js
rtk node --check Tools/hold-highlight-editor/workbench-controller.js
rtk node --check Tools/hold-highlight-editor/workbench-model.js
rtk git diff --check
```

Expected: every command succeeds.

- [ ] **Step 4: Build the exact final commit and smoke-test it**

Commit documentation first so embedded build metadata can name the final
implementation commit:

```bash
rtk git add Tools/hold-highlight-editor/README.md Tools/HangboardOnboarding/README.md
rtk git commit -m "Document workbench binary releases"
rtk git rev-parse HEAD
```

Build with the literal final SHA in the isolated PyInstaller environment from
Task 2. Require arm64 architecture, exact `--version`, successful `/`,
`/api/library`, and every static asset response, clean `SIGINT` and `SIGTERM`
shutdown with no parent or child left, archive creation, checksum verification,
and absence of product/evidence resources.

- [ ] **Step 5: Verify protected visual artifacts are unchanged**

Compare the protected Stage 4 PNG and SVG hashes against the pre-packaging
baseline recorded by the workbench implementation. Packaging changes must not
modify any path under `Tools/HangboardOnboarding/boards/`.

```bash
rtk git diff --name-only 94e34b9ea14aa235fa130446ae917e1bb3b45af1..HEAD -- Tools/HangboardOnboarding/boards
```

Expected: no output.

- [ ] **Step 6: Request final internal review, push, and update PR #40**

Use `superpowers:requesting-code-review`, fix all Critical and Important
findings, rerun the affected verification, then push
`codex/local-hangboard-workbench`. Confirm PR #40 targets `main`, remains a
draft, and reports the exact final head SHA and updated binary/release
validation.
