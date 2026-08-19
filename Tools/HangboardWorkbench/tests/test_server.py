from __future__ import annotations

import http.cookiejar
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
from collections.abc import Iterator
from contextlib import contextmanager
from http.cookies import SimpleCookie
from pathlib import Path
from types import SimpleNamespace
from typing import Self
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
WORKBENCH_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WORKBENCH_ROOT))

import board_package  # noqa: E402
import server as server_module  # noqa: E402
from board_package import BoardPackageError  # noqa: E402
from fake_github_client import FakeGitHubClient  # noqa: E402
from github_client import (  # noqa: E402
    GitHubAuthError,
    GitHubClient,
    GitHubForbiddenError,
    GitHubNotFoundError,
    GitHubRateLimitError,
    GitHubTransportError,
)
from server import (  # noqa: E402
    EditorError,
    _Session,
    create_server,
    validate_hang_ten_checkout,
)
from workbench_fixtures import PRIMARY_IMAGE, board_document  # noqa: E402

HOSTED_TOKEN = "ghp_hosted_session"
HOSTED_BRANCH = "workbench-default"


def _write_library(root: Path) -> Path:
    library = root / "Hangboards"
    package = library / "fixture-board"
    assets = package / "assets"
    assets.mkdir(parents=True)
    shutil.copyfile(PRIMARY_IMAGE, assets / "primary.png")
    board = board_document("fixture.board")
    (package / "board.json").write_text(
        json.dumps(board, indent=2) + "\n", encoding="utf-8"
    )
    return library


def _git_checkout(root: Path) -> Path:
    checkout = root / "checkout"
    (checkout / ".git").mkdir(parents=True)
    (checkout / "Hangboards").mkdir(parents=True)
    workbench = checkout / "Tools" / "HangboardWorkbench"
    workbench.mkdir(parents=True)
    shutil.copy2(
        REPOSITORY_ROOT / "Tools" / "HangboardWorkbench" / "server.py",
        workbench / "server.py",
    )
    shutil.copy2(
        REPOSITORY_ROOT / "Tools" / "HangboardWorkbench" / "board_package.py",
        workbench / "board_package.py",
    )
    shutil.copy2(
        REPOSITORY_ROOT / "Tools" / "HangboardWorkbench" / "board_geometry.py",
        workbench / "board_geometry.py",
    )
    # Isolate this fixture from the developer's own global/system git config
    # (commit.gpgsign, core.hooksPath, init.templateDir, ...), any of which
    # could make these commands fail or behave unexpectedly.
    git_environment = {
        **os.environ,
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_CONFIG_SYSTEM": os.devnull,
        "GIT_CONFIG_NOSYSTEM": "1",
    }

    def run(*args: str) -> None:
        subprocess.run(
            ["git", *args],
            cwd=checkout,
            check=True,
            text=True,
            capture_output=True,
            env=git_environment,
        )

    run("init", "-b", "main")
    run("config", "user.name", "Hangboard Workbench")
    run("config", "user.email", "workbench@example.com")
    run("add", ".")
    run("commit", "-m", "Initialize hang-ten checkout")
    return checkout


@contextmanager
def running_server(library: Path) -> Iterator[str]:
    httpd = create_server(library, port=0)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{httpd.server_port}"
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=5)


@contextmanager
def running_server_with_oauth(
    library: Path, *, fake_token: str = "ghp_test_token_123"
) -> Iterator[tuple[str, str]]:
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
        httpd.server_close()


def _github_files() -> dict[str, bytes]:
    return {
        "Hangboards/fixture-board/board.json": (
            json.dumps(board_document("fixture.board"), indent=2) + "\n"
        ).encode("utf-8"),
        "Hangboards/fixture-board/assets/primary.png": PRIMARY_IMAGE.read_bytes(),
    }


class _HostedSaveIdentityRaceClient(FakeGitHubClient):
    """Replace a slug after PUT resolves its ID but before the save reload."""

    def __init__(self, files: dict[str, bytes]) -> None:
        super().__init__(
            {"main": files, HOSTED_BRANCH: files, "feature": files},
            default_branch=HOSTED_BRANCH,
        )
        self._head_reads = 0

    def get_branch_head_sha(self, token: str, branch: str) -> str:
        self._head_reads += 1
        if self._head_reads == 3:
            path = "Hangboards/fixture-board/board.json"
            content = (
                json.dumps(board_document("different.board"), indent=2) + "\n"
            ).encode("utf-8")
            current_sha = self._branches[branch][path][1]
            super().put_file(
                token,
                path,
                branch,
                content,
                "Concurrent board replacement",
                current_sha,
            )
        return super().get_branch_head_sha(token, branch)


class _ConcurrentHostedBlobClient(FakeGitHubClient):
    """Tracks the aggregate upstream blob concurrency of hosted requests."""

    def __init__(self, files: dict[str, bytes]) -> None:
        super().__init__({"main": files, HOSTED_BRANCH: files, "feature": files})
        self._lock = threading.Lock()
        self._active_blob_reads = 0
        self.max_active_blob_reads = 0

    def get_blob(self, token: str, sha: str) -> bytes:
        with self._lock:
            self._active_blob_reads += 1
            self.max_active_blob_reads = max(
                self.max_active_blob_reads, self._active_blob_reads
            )
        try:
            time.sleep(0.04)
            return super().get_blob(token, sha)
        finally:
            with self._lock:
                self._active_blob_reads -= 1


@contextmanager
def running_server_with_github_backend(
    files: dict[str, bytes],
    *,
    github_client: FakeGitHubClient | None = None,
) -> Iterator[tuple[str, FakeGitHubClient, str]]:
    """Run hosted storage entirely against an authenticated in-memory GitHub fake."""
    with tempfile.TemporaryDirectory() as directory:
        library = Path(directory) / "Hangboards"
        library.mkdir()
        github_client = github_client or FakeGitHubClient(
            {"main": files, HOSTED_BRANCH: files, "feature": files},
            default_branch=HOSTED_BRANCH,
        )
        httpd = create_server(
            library,
            port=0,
            allow_remote=True,
            github_client_id="test-client-id",
            github_client_secret="test-client-secret",
            session_secret="test-session-secret",
            github_owner="fixture-owner",
            github_repo="fixture-repo",
            github_client=github_client,
        )
        session_value = server_module._encode_session(
            httpd.session_secret,
            _Session(
                token=HOSTED_TOKEN,
                username="climber",
                branch=HOSTED_BRANCH,
            ),
        )
        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()
        try:
            yield (
                f"http://127.0.0.1:{httpd.server_port}",
                github_client,
                session_value,
            )
        finally:
            httpd.shutdown()
            thread.join(timeout=5)
            httpd.server_close()


def request_json(
    base: str, method: str, path: str, value: object | None = None
) -> tuple[int, dict[str, object]]:
    data = None if value is None else json.dumps(value).encode("utf-8")
    request = Request(
        base + path,
        data=data,
        method=method,
        headers={"Content-Type": "application/json"} if data is not None else {},
    )
    try:
        with urlopen(request) as response:
            return response.status, json.loads(response.read())
    except HTTPError as error:
        return error.code, json.loads(error.read())


def hosted_request(
    base: str,
    session_value: str,
    method: str,
    path: str,
    value: object | None = None,
) -> tuple[int, bytes, object]:
    data = None if value is None else json.dumps(value).encode("utf-8")
    headers = {"Cookie": f"wb_session={session_value}"}
    if data is not None:
        headers["Content-Type"] = "application/json"
    request = Request(base + path, data=data, method=method, headers=headers)
    try:
        with urlopen(request) as response:
            return response.status, response.read(), response.headers
    except HTTPError as error:
        return error.code, error.read(), error.headers


def hosted_request_json(
    base: str,
    session_value: str,
    method: str,
    path: str,
    value: object | None = None,
) -> tuple[int, dict[str, object], object]:
    status, body, headers = hosted_request(base, session_value, method, path, value)
    return status, json.loads(body), headers


def test_lists_and_opens_direct_packages_with_independent_piece_regions(
    tmp_path: Path,
) -> None:
    library = _write_library(tmp_path)

    with running_server(library) as base:
        status, listed = request_json(base, "GET", "/api/boards")
        assert status == 200
        assert listed == {
            "ok": True,
            "boards": [
                {
                    "boardId": "fixture.board",
                    "displayName": "Fixture Maker Fixture Board",
                    "holdCount": 1,
                    "href": "/api/boards/fixture.board",
                }
            ],
        }

        status, opened = request_json(base, "GET", "/api/boards/fixture.board")
        assert status == 200
        board = opened["board"]
        assert board["imageUrl"] == "/api/boards/fixture.board/image"
        assert board["saveUrl"] == "/api/boards/fixture.board"
        assert [region["key"] for region in board["document"]["regions"]] == [
            "hold-left-piece-0",
            "hold-left-piece-1",
        ]

        with urlopen(base + board["imageUrl"]) as response:
            assert response.status == 200
            assert response.headers["Content-Type"] == "image/png"
            assert response.read(8) == b"\x89PNG\r\n\x1a\n"


def test_save_keeps_geometry_inside_board_json_and_creates_no_registry_or_sidecar(
    tmp_path: Path,
) -> None:
    library = _write_library(tmp_path)
    package = library / "fixture-board"
    with running_server(library) as base:
        _status, opened = request_json(base, "GET", "/api/boards/fixture.board")
        document = opened["board"]["document"]
        document["regions"][0]["displayPath"] = (
            "M 177.4 45.7 L 354.8 45.7 L 354.8 137.1 L 177.4 137.1 Z"
        )

        status, saved = request_json(
            base, "PUT", "/api/boards/fixture.board", document
        )

    assert status == 200
    assert saved["board"]["document"]["regions"][0]["displayPath"] == (
        document["regions"][0]["displayPath"]
    )
    board = json.loads((package / "board.json").read_text(encoding="utf-8"))
    assert board["holds"][0]["geometry"][0]["frame"] == {
        "x": 0.1,
        "y": 0.1,
        "width": 0.1,
        "height": 0.2,
    }
    assert {path.name for path in package.iterdir()} == {"board.json", "assets"}
    assert not (library / "catalog.json").exists()


def test_invalid_save_leaves_board_json_and_inventory_unchanged(tmp_path: Path) -> None:
    library = _write_library(tmp_path)
    package = library / "fixture-board"
    before = {
        path.relative_to(package).as_posix(): path.read_bytes()
        for path in package.rglob("*")
        if path.is_file()
    }
    with running_server(library) as base:
        _status, opened = request_json(base, "GET", "/api/boards/fixture.board")
        document = opened["board"]["document"]
        document["regions"][0]["displayPath"] = (
            "M 10 10 L 90 90 L 10 90 L 90 10 Z"
        )
        status, result = request_json(
            base, "PUT", "/api/boards/fixture.board", document
        )

    assert status == 400
    assert result == {"ok": False, "error": "hold hold-left-piece-0 must not self-intersect"}
    after = {
        path.relative_to(package).as_posix(): path.read_bytes()
        for path in package.rglob("*")
        if path.is_file()
    }
    assert after == before
    assert not (library / "catalog.json").exists()


def test_load_failures_do_not_expose_library_paths(tmp_path: Path) -> None:
    library = _write_library(tmp_path)
    (library / "fixture-board" / "assets" / "primary.png").unlink()
    with running_server(library) as base:
        status, result = request_json(base, "GET", "/api/boards/fixture.board")

    assert status == 400
    assert result == {"ok": False, "error": "could not load board"}
    assert str(library) not in json.dumps(result)


def test_get_board_routes_not_available_errors_by_type(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    library = _write_library(tmp_path)
    unavailable_error = getattr(
        board_package, "BoardNotAvailableError", BoardPackageError
    )

    def raise_unavailable(*_args: object) -> object:
        raise unavailable_error("unavailable details changed")

    monkeypatch.setattr(server_module, "open_package", raise_unavailable)

    with running_server(library) as base:
        status, result = request_json(base, "GET", "/api/boards/fixture.board")

    assert status == 404
    assert result == {"ok": False, "error": "board is not available"}


def test_get_board_keeps_base_package_error_with_old_sentinel_at_generic_400(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    library = _write_library(tmp_path)

    def raise_base_error(*_args: object) -> object:
        raise BoardPackageError("board is not available")

    monkeypatch.setattr(server_module, "open_package", raise_base_error)

    with running_server(library) as base:
        status, result = request_json(base, "GET", "/api/boards/fixture.board")

    assert status == 400
    assert result == {"ok": False, "error": "could not load board"}


def test_save_routes_not_available_errors_to_404(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    library = _write_library(tmp_path)

    def raise_unavailable(*_args: object) -> object:
        raise board_package.BoardNotAvailableError("unavailable details changed")

    monkeypatch.setattr(server_module, "open_package", raise_unavailable)

    with running_server(library) as base:
        status, result = request_json(base, "PUT", "/api/boards/fixture.board", {})

    assert status == 404
    assert result == {"ok": False, "error": "board is not available"}


def test_checkout_lists_every_completed_package_and_opens_reference_compact_ii(
    tmp_path: Path,
) -> None:
    checkout = tmp_path / "checkout"
    library = checkout / "Hangboards"
    editor_root = checkout / "Tools" / "HangboardWorkbench"
    shutil.copytree(REPOSITORY_ROOT / "Hangboards", library)
    second_package = library / "fixture-second-completed"
    shutil.copytree(
        library / "metolius-wood-grips-compact-ii",
        second_package,
    )
    second_board_path = second_package / "board.json"
    second_board = json.loads(second_board_path.read_text(encoding="utf-8"))
    second_board.update(
        id="fixture.second-completed",
        manufacturer="Fixture Maker",
        name="Second Completed Board",
    )
    second_board_path.write_text(
        json.dumps(second_board, indent=2) + "\n",
        encoding="utf-8",
    )
    shutil.copytree(
        WORKBENCH_ROOT,
        editor_root,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "tests"),
    )
    code = """
import json
import sys
import threading
from pathlib import Path
from urllib.request import urlopen

root = Path(sys.argv[1])
sys.path.insert(0, str(root / 'Tools' / 'HangboardWorkbench'))
from server import create_server

httpd = create_server(root / 'Hangboards', port=0)
thread = threading.Thread(target=httpd.serve_forever, daemon=True)
thread.start()
base = f'http://{httpd.server_address[0]}:{httpd.server_address[1]}'
try:
    listed = json.loads(urlopen(base + '/api/boards').read())
    completed_packages = [
        child
        for child in (root / 'Hangboards').iterdir()
        if child.is_dir() and (child / 'board.json').is_file()
    ]
    expected_ids = sorted(
        json.loads((package / 'board.json').read_text())['id']
        for package in completed_packages
    )
    assert sorted(board['boardId'] for board in listed['boards']) == expected_ids
    compact_ii = next(
        board
        for board in listed['boards']
        if board['boardId'] == 'metolius.wood-grips-compact-ii'
    )
    opened = json.loads(urlopen(base + compact_ii['href']).read())
    assert len(opened['board']['document']['regions']) == 19
finally:
    httpd.shutdown()
    thread.join(timeout=5)
    httpd.server_close()
"""
    completed = subprocess.run(
        [sys.executable, "-c", code, str(checkout)],
        cwd=checkout,
        env=os.environ | {"PYTHONPATH": str(editor_root)},
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr


def test_server_imports_with_only_the_workbench_on_pythonpath(tmp_path: Path) -> None:
    completed = subprocess.run(
        [sys.executable, "-c", "import server; print(server.__name__)"],
        cwd=tmp_path,
        env=os.environ | {"PYTHONPATH": str(WORKBENCH_ROOT)},
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.strip() == "server"


def test_checkout_validation_requires_only_the_direct_workbench_layout(
    tmp_path: Path,
) -> None:
    checkout = tmp_path / "checkout"
    (checkout / ".git").mkdir(parents=True)
    (checkout / "Hangboards").mkdir()
    workbench = checkout / "Tools" / "HangboardWorkbench"
    workbench.mkdir(parents=True)
    (workbench / "server.py").touch()
    (workbench / "board_package.py").touch()
    (workbench / "board_geometry.py").touch()

    assert validate_hang_ten_checkout(checkout) == checkout.resolve()
    (workbench / "board_geometry.py").unlink()

    with pytest.raises(EditorError, match="Hang Ten checkout"):
        validate_hang_ten_checkout(checkout)


def test_server_rejects_a_symlinked_library_before_resolving_it(
    tmp_path: Path,
) -> None:
    real_library = _write_library(tmp_path / "real")
    linked_library = tmp_path / "linked-hangboards"
    linked_library.symlink_to(real_library, target_is_directory=True)
    httpd = None
    try:
        with pytest.raises(EditorError, match="symlink"):
            httpd = create_server(linked_library, port=0)
    finally:
        if httpd is not None:
            httpd.server_close()


def test_checkout_rejects_a_hangboards_symlink_that_escapes_the_checkout(
    tmp_path: Path,
) -> None:
    checkout = tmp_path / "checkout"
    (checkout / ".git").mkdir(parents=True)
    outside_library = _write_library(tmp_path / "outside")
    (checkout / "Hangboards").symlink_to(
        outside_library,
        target_is_directory=True,
    )
    workbench = checkout / "Tools" / "HangboardWorkbench"
    workbench.mkdir(parents=True)
    (workbench / "server.py").touch()
    (workbench / "board_package.py").touch()
    (workbench / "board_geometry.py").touch()

    with pytest.raises(EditorError, match="Hang Ten checkout"):
        validate_hang_ten_checkout(checkout)


def test_git_status_reports_branch_and_worktree_state(tmp_path: Path) -> None:
    checkout = _git_checkout(tmp_path)
    (checkout / "workbench-note.txt").write_text("working tree", encoding="utf-8")

    with running_server(checkout / "Hangboards") as base:
        status, payload = request_json(base, "GET", "/api/git/status")

    assert status == 200
    assert payload == {
        "ok": True,
        "currentBranch": "main",
        "dirty": True,
        "statusLines": ["?? workbench-note.txt"],
        "branches": ["main"],
    }


def test_git_status_reports_null_branch_in_detached_head_state(tmp_path: Path) -> None:
    checkout = _git_checkout(tmp_path)
    subprocess.run(
        ["git", "checkout", "--detach", "HEAD"],
        cwd=checkout,
        check=True,
        text=True,
        capture_output=True,
    )

    with running_server(checkout / "Hangboards") as base:
        status, payload = request_json(base, "GET", "/api/git/status")

    assert status == 200
    assert payload == {
        "ok": True,
        "currentBranch": None,
        "dirty": False,
        "statusLines": [],
        "branches": ["main"],
    }


def test_git_checkout_switches_branch(tmp_path: Path) -> None:
    checkout = _git_checkout(tmp_path)
    subprocess.run([
        "git",
        "switch",
        "-c",
        "feature",
    ], cwd=checkout, check=True, text=True, capture_output=True)

    with running_server(checkout / "Hangboards") as base:
        status, payload = request_json(
            base,
            "POST",
            "/api/git/checkout",
            {"branch": "main"},
        )

    assert status == 200
    assert payload == {
        "ok": True,
        "branch": "main",
    }


def test_git_checkout_creates_and_switches_to_a_new_branch(tmp_path: Path) -> None:
    checkout = _git_checkout(tmp_path)

    with running_server(checkout / "Hangboards") as base:
        status, payload = request_json(
            base,
            "POST",
            "/api/git/checkout",
            {"branch": "feature", "create": True},
        )

    assert status == 200
    assert payload == {
        "ok": True,
        "branch": "feature",
    }
    branch = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        cwd=checkout,
        check=True,
        text=True,
        capture_output=True,
    ).stdout.strip()
    assert branch == "feature"


def test_git_checkout_create_rejects_an_existing_branch_name(tmp_path: Path) -> None:
    checkout = _git_checkout(tmp_path)

    with running_server(checkout / "Hangboards") as base:
        status, payload = request_json(
            base,
            "POST",
            "/api/git/checkout",
            {"branch": "main", "create": True},
        )

    assert status == 400
    assert payload["ok"] is False


def test_git_commit_refuses_when_nothing_to_commit(tmp_path: Path) -> None:
    checkout = _git_checkout(tmp_path)

    with running_server(checkout / "Hangboards") as base:
        status, payload = request_json(
            base,
            "POST",
            "/api/git/commit",
            {"message": "No-op"},
        )

    assert status == 409
    assert payload == {
        "ok": False,
        "error": "no changes to commit",
    }


def test_git_checkout_rejects_branch_starting_with_dash(tmp_path: Path) -> None:
    checkout = _git_checkout(tmp_path)

    with running_server(checkout / "Hangboards") as base:
        status, payload = request_json(
            base,
            "POST",
            "/api/git/checkout",
            {"branch": "--exec=rm -rf /"},
        )

    assert status == 400
    assert "branch" in payload["error"]


def test_git_commit_rejects_message_starting_with_dash(tmp_path: Path) -> None:
    checkout = _git_checkout(tmp_path)
    (checkout / "new-file.txt").write_text("hello", encoding="utf-8")
    subprocess.run(
        ["git", "add", "new-file.txt"],
        cwd=checkout,
        check=True,
        text=True,
        capture_output=True,
    )

    with running_server(checkout / "Hangboards") as base:
        status, payload = request_json(
            base,
            "POST",
            "/api/git/commit",
            {"message": "--allow-empty"},
        )

    assert status == 400
    assert "message" in payload["error"]


def test_git_push_rejects_remote_starting_with_dash(tmp_path: Path) -> None:
    checkout = _git_checkout(tmp_path)
    (checkout / "push-me.txt").write_text("data", encoding="utf-8")
    subprocess.run(
        ["git", "add", "push-me.txt"],
        cwd=checkout,
        check=True,
        text=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "commit", "-m", "add file"],
        cwd=checkout,
        check=True,
        text=True,
        capture_output=True,
    )

    with running_server(checkout / "Hangboards") as base:
        status, payload = request_json(
            base,
            "POST",
            "/api/git/push",
            {"remote": "--all"},
        )

    assert status == 400
    assert "remote" in payload["error"]


def test_git_checkout_rejects_branch_with_null_byte(tmp_path: Path) -> None:
    checkout = _git_checkout(tmp_path)

    with running_server(checkout / "Hangboards") as base:
        status, payload = request_json(
            base,
            "POST",
            "/api/git/checkout",
            {"branch": "main\x00evil"},
        )

    assert status == 400
    assert "branch" in payload["error"]


def test_remote_request_without_session_returns_401(tmp_path: Path) -> None:
    checkout = _git_checkout(tmp_path)

    with running_server_with_oauth(checkout / "Hangboards") as (base, _token):
        status, payload = request_json(base, "GET", "/api/git/status")

    assert status == 401
    assert payload["error"] == "authentication required"
    assert payload["login_url"] == "/auth/login"


def test_signed_session_round_trip_preserves_authenticated_identity() -> None:
    """Fails if a cookie loses any GitHub identity needed by a request."""
    session = _Session(token="ghp_token", username="octocat", branch="main")

    cookie_value = server_module._encode_session(b"test-session-secret", session)

    assert server_module._decode_session(b"test-session-secret", cookie_value) == session


@pytest.mark.parametrize(
    "cookie_value", ["", ".", "not-base64.not-a-signature", "a.b.c"]
)
def test_signed_session_rejects_malformed_cookie_values(cookie_value: str) -> None:
    """Fails if malformed cookie input reaches an authenticated request."""
    assert server_module._decode_session(b"test-session-secret", cookie_value) is None


def test_signed_session_rejects_tampering_and_a_different_secret() -> None:
    """Fails if a modified or cross-deployment cookie is accepted."""
    session = _Session(token="ghp_token", username="octocat", branch="main")
    cookie_value = server_module._encode_session(b"first-session-secret", session)
    tampered = cookie_value[:-1] + ("0" if cookie_value[-1] != "0" else "1")

    assert server_module._decode_session(b"first-session-secret", tampered) is None
    assert server_module._decode_session(b"second-session-secret", cookie_value) is None


def test_remote_cli_requires_a_session_secret(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Fails if remote mode can start without a stable signing secret."""
    checkout = Path.cwd()
    monkeypatch.setattr(server_module, "create_server", lambda *_args, **_kwargs: object())

    with pytest.raises(SystemExit) as error:
        server_module._server_from_cli(
            [
                "--repository-root", str(checkout),
                "--port", "0",
                "--allow-remote",
                "--github-client-id", "test-client-id",
                "--github-client-secret", "test-client-secret",
            ]
        )

    assert error.value.code == 2
    assert "--session-secret" in capsys.readouterr().err


def test_root_without_session_redirects_to_login(tmp_path: Path) -> None:
    checkout = _git_checkout(tmp_path)

    with running_server_with_oauth(checkout / "Hangboards") as (base, _token):
        request = urllib.request.Request(f"{base}/")
        opener = urllib.request.build_opener(_NoRedirectHandler)
        try:
            opener.open(request)
            pytest.fail("expected a redirect to raise HTTPError")
        except urllib.error.HTTPError as error:
            assert error.code == 302
            assert error.headers.get("Location") == "/auth/login"


def test_health_check_without_session_returns_200(tmp_path: Path) -> None:
    checkout = _git_checkout(tmp_path)

    with running_server_with_oauth(checkout / "Hangboards") as (base, _token):
        status, payload = request_json(base, "GET", "/api/health")

    assert status == 200
    assert payload["ok"] is True


def test_local_mode_health_check_still_enforces_loopback_origin(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    library = _write_library(tmp_path)
    monkeypatch.setattr(server_module, "_loopback_peer", lambda _value: False)

    with running_server(library) as base:
        status, payload = request_json(base, "GET", "/api/health")

    assert status == 403
    assert payload["error"] == "request origin is not allowed"


def test_auth_status_returns_unauthenticated_by_default(tmp_path: Path) -> None:
    checkout = _git_checkout(tmp_path)

    with running_server_with_oauth(checkout / "Hangboards") as (base, _token):
        status, payload = request_json(base, "GET", "/api/auth/status")

    assert status == 200
    assert payload["authenticated"] is False


def test_auth_status_returns_username_with_valid_session(tmp_path: Path) -> None:
    checkout = _git_checkout(tmp_path)

    httpd = create_server(
        checkout / "Hangboards",
        port=0,
        allow_remote=True,
        github_client_id="test-client-id",
        github_client_secret="test-client-secret",
    )
    session_value = server_module._encode_session(
        httpd.session_secret,
        _Session(token="ghp_fake", username="testuser", branch="main"),
    )
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        base = f"http://127.0.0.1:{httpd.server_port}"
        cookie_jar = http.cookiejar.CookieJar()
        opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(cookie_jar)
        )
        cookie = http.cookiejar.Cookie(
            version=0,
            name="wb_session",
            value=session_value,
            port=None,
            port_specified=False,
            domain="127.0.0.1",
            domain_specified=True,
            domain_initial_dot=False,
            path="/",
            path_specified=True,
            secure=False,
            expires=int(time.time()) + 3600,
            discard=False,
            comment=None,
            comment_url=None,
            rest={},
            rfc2109=False,
        )
        cookie_jar.set_cookie(cookie)
        request = urllib.request.Request(f"{base}/api/auth/status")
        with opener.open(request) as response:
            payload = json.loads(response.read())
        assert payload["authenticated"] is True
        assert payload["username"] == "testuser"
    finally:
        httpd.shutdown()
        thread.join(timeout=5)
        httpd.server_close()


class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Raise HTTPError instead of following redirects, so tests can inspect
    the redirect response without making an outbound network call."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: D102, N802
        raise urllib.error.HTTPError(req.full_url, code, msg, headers, fp)


def test_login_redirects_to_github(tmp_path: Path) -> None:
    checkout = _git_checkout(tmp_path)

    with running_server_with_oauth(checkout / "Hangboards") as (base, _token):
        request = urllib.request.Request(f"{base}/auth/login")
        opener = urllib.request.build_opener(_NoRedirectHandler)
        try:
            opener.open(request)
            pytest.fail("expected a redirect to raise HTTPError")
        except urllib.error.HTTPError as error:
            assert error.code == 302
            location = error.headers.get("Location", "")
            assert "github.com/login/oauth/authorize" in location
            assert "client_id=test-client-id" in location
            assert "scope=repo,read:org" in location


def test_login_without_oauth_configured_returns_404(tmp_path: Path) -> None:
    checkout = _git_checkout(tmp_path)

    with running_server(checkout / "Hangboards") as base:
        status, _payload = request_json(base, "GET", "/auth/login")

    assert status == 404


def test_hosted_board_routes_read_packages_and_images_from_github() -> None:
    """Fails if hosted reads accidentally use the empty local board library."""
    with running_server_with_github_backend(_github_files()) as (
        base,
        client,
        session,
    ):
        status, listed, _headers = hosted_request_json(
            base, session, "GET", "/api/boards"
        )
        assert status == 200
        assert listed == {
            "ok": True,
            "boards": [
                {
                    "boardId": "fixture.board",
                    "displayName": "Fixture Maker Fixture Board",
                    "holdCount": 1,
                    "href": "/api/boards/fixture.board",
                }
            ],
        }

        status, opened, _headers = hosted_request_json(
            base, session, "GET", "/api/boards/fixture.board"
        )
        assert status == 200
        board = opened["board"]
        assert board["document"]["regions"][0]["key"] == "hold-left-piece-0"

        status, image, headers = hosted_request(
            base, session, "GET", board["imageUrl"]
        )
        assert status == 200
        assert headers["Content-Type"] == "image/png"
        assert image == PRIMARY_IMAGE.read_bytes()

    assert len(client.calls_named("get_tree")) == 1
    assert {call.args[0] for call in client.calls_named("get_tree")} == {HOSTED_TOKEN}
    assert {
        call.args[0] for call in client.calls_named("get_blob")
    } == {HOSTED_TOKEN}


def test_hosted_board_reads_reuse_an_unchanged_commit_snapshot() -> None:
    """Fails if list, open, and image repeatedly fetch the same GitHub tree/blobs."""
    with running_server_with_github_backend(_github_files()) as (
        base,
        client,
        session,
    ):
        listed_status, listed, _headers = hosted_request_json(
            base, session, "GET", "/api/boards"
        )
        opened_status, opened, _headers = hosted_request_json(
            base, session, "GET", "/api/boards/fixture.board"
        )
        image_status, image, _headers = hosted_request(
            base, session, "GET", "/api/boards/fixture.board/image"
        )

    assert (listed_status, opened_status, image_status) == (200, 200, 200)
    assert listed["boards"][0]["boardId"] == "fixture.board"
    assert opened["board"]["boardId"] == "fixture.board"
    assert image == PRIMARY_IMAGE.read_bytes()
    assert len(client.calls_named("get_branch_head_sha")) == 3
    assert len(client.calls_named("get_tree")) == 1
    assert len(client.calls_named("get_blob")) == 4


def test_hosted_board_reads_refresh_when_the_branch_head_changes() -> None:
    """Fails if a cached remote snapshot hides a board committed after a prior read."""
    with running_server_with_github_backend(_github_files()) as (
        base,
        client,
        session,
    ):
        first_status, first, _headers = hosted_request_json(
            base, session, "GET", "/api/boards"
        )
        board_path = "Hangboards/fixture-board/board.json"
        current_sha = next(
            entry.sha
            for entry in client.get_tree(HOSTED_TOKEN, HOSTED_BRANCH)
            if entry.path == board_path
        )
        replacement = board_document("fixture.board")
        replacement["name"] = "Replacement Board"
        client.put_file(
            HOSTED_TOKEN,
            board_path,
            HOSTED_BRANCH,
            (json.dumps(replacement, indent=2) + "\n").encode("utf-8"),
            "Replace fixture board",
            current_sha,
        )
        second_status, second, _headers = hosted_request_json(
            base, session, "GET", "/api/boards"
        )

    assert first_status == second_status == 200
    assert first["boards"][0]["displayName"] == "Fixture Maker Fixture Board"
    assert second["boards"][0]["displayName"] == "Fixture Maker Replacement Board"
    assert len(client.calls_named("get_branch_head_sha")) == 2
    assert len(client.calls_named("get_tree")) == 3


def test_simultaneous_hosted_catalog_reads_share_one_bounded_upstream_load() -> None:
    """Fails if concurrent cold routes duplicate catalog reads or worker pools."""
    files: dict[str, bytes] = {}
    for slug in ("alpha", "bravo", "charlie", "delta", "echo", "foxtrot"):
        board = board_document(f"{slug}.board")
        board["name"] = slug.title()
        files.update(
            {
                f"Hangboards/{slug}/board.json": (
                    json.dumps(board, indent=2) + "\n"
                ).encode("utf-8"),
                f"Hangboards/{slug}/assets/primary.png": (
                    PRIMARY_IMAGE.read_bytes() + slug.encode("utf-8")
                ),
            }
        )
    client = _ConcurrentHostedBlobClient(files)
    with running_server_with_github_backend(files, github_client=client) as (
        base,
        _client,
        session,
    ):
        start = threading.Barrier(3)
        results: list[tuple[int, dict[str, object], object]] = []

        def request_catalog() -> None:
            start.wait()
            results.append(hosted_request_json(base, session, "GET", "/api/boards"))

        first = threading.Thread(target=request_catalog)
        second = threading.Thread(target=request_catalog)
        first.start()
        second.start()
        start.wait()
        first.join(timeout=5)
        second.join(timeout=5)

    assert [status for status, _body, _headers in results] == [200, 200]
    assert len(client.calls_named("get_tree")) == 1
    assert len(client.calls_named("get_blob")) == 12
    assert client.max_active_blob_reads <= 4


def test_server_close_waits_for_a_paused_hosted_catalog_request(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Fails if closing the store executor races an accepted catalog request."""
    library = tmp_path / "Hangboards"
    library.mkdir()
    client = FakeGitHubClient({HOSTED_BRANCH: _github_files()})
    httpd = create_server(
        library,
        port=0,
        allow_remote=True,
        github_client_id="test-client-id",
        github_client_secret="test-client-secret",
        session_secret="test-session-secret",
        github_owner="fixture-owner",
        github_repo="fixture-repo",
        github_client=client,
    )
    session = server_module._encode_session(
        httpd.session_secret,
        _Session(token=HOSTED_TOKEN, username="climber", branch=HOSTED_BRANCH),
    )
    entered = threading.Event()
    release = threading.Event()
    original_catalog = server_module.github_board_store.GitHubBoardStore._catalog

    def pause_catalog(store, *args):
        entered.set()
        assert release.wait(timeout=5)
        return original_catalog(store, *args)

    monkeypatch.setattr(
        server_module.github_board_store.GitHubBoardStore,
        "_catalog",
        pause_catalog,
    )
    server_thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    server_thread.start()
    result: list[tuple[int, dict[str, object], object]] = []

    def request_catalog() -> None:
        result.append(hosted_request_json(
            f"http://127.0.0.1:{httpd.server_port}",
            session,
            "GET",
            "/api/boards",
        ))

    request_thread = threading.Thread(target=request_catalog)
    request_thread.start()
    close_thread: threading.Thread | None = None
    try:
        assert entered.wait(timeout=5)
        httpd.shutdown()
        close_thread = threading.Thread(target=httpd.server_close)
        close_thread.start()
        close_thread.join(timeout=1)
        assert close_thread.is_alive()
    finally:
        release.set()
        httpd.shutdown()
        request_thread.join(timeout=5)
        if close_thread is not None:
            close_thread.join(timeout=5)
        server_thread.join(timeout=5)
        httpd.server_close()

    assert result[0][0] == 200
    assert not request_thread.is_alive()
    assert close_thread is not None and not close_thread.is_alive()
    assert not server_thread.is_alive()


def test_server_close_does_not_wait_for_an_incomplete_request_before_store_work(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Fails if shutdown waits for a handler blocked before a store operation."""
    library = tmp_path / "Hangboards"
    library.mkdir()
    httpd = create_server(
        library,
        port=0,
        allow_remote=True,
        github_client_id="test-client-id",
        github_client_secret="test-client-secret",
        session_secret="test-session-secret",
        github_owner="fixture-owner",
        github_repo="fixture-repo",
        github_client=FakeGitHubClient({HOSTED_BRANCH: _github_files()}),
    )
    session = server_module._encode_session(
        httpd.session_secret,
        _Session(token=HOSTED_TOKEN, username="climber", branch=HOSTED_BRANCH),
    )
    entered_body_read = threading.Event()
    original_read_body = server_module.EditorRequestHandler._read_body

    def observe_read_body(handler):
        entered_body_read.set()
        return original_read_body(handler)

    monkeypatch.setattr(
        server_module.EditorRequestHandler, "_read_body", observe_read_body
    )
    server_thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    server_thread.start()
    client_socket = socket.create_connection(("127.0.0.1", httpd.server_port))
    try:
        client_socket.sendall(
            (
                "PUT /api/boards/fixture.board HTTP/1.1\r\n"
                f"Host: 127.0.0.1:{httpd.server_port}\r\n"
                f"Cookie: wb_session={session}\r\n"
                "Content-Type: application/json\r\n"
                "Content-Length: 10\r\n\r\n"
            ).encode("ascii")
        )
        assert entered_body_read.wait(timeout=5)
        httpd.shutdown()
        close_thread = threading.Thread(target=httpd.server_close)
        close_thread.start()
        close_thread.join(timeout=1)

        assert not close_thread.is_alive()
        assert not server_thread.is_alive()
    finally:
        client_socket.sendall(b"{}        ")
        client_socket.shutdown(socket.SHUT_WR)
        client_socket.close()
        httpd.server_close()
        server_thread.join(timeout=5)


def test_hosted_save_writes_github_and_returns_the_commit_sha() -> None:
    """Fails if a hosted save writes locally or drops GitHub's commit identity."""
    with running_server_with_github_backend(_github_files()) as (
        base,
        client,
        session,
    ):
        _status, opened, _headers = hosted_request_json(
            base, session, "GET", "/api/boards/fixture.board"
        )
        document = opened["board"]["document"]
        document["regions"][0]["displayPath"] = (
            "M 177.4 45.7 L 354.8 45.7 L 354.8 137.1 L 177.4 137.1 Z"
        )

        status, saved, _headers = hosted_request_json(
            base, session, "PUT", "/api/boards/fixture.board", document
        )

        assert status == 200
        assert saved["ok"] is True
        assert isinstance(saved["commit"], str)
        assert len(saved["commit"]) == 64
        stored = json.loads(
            client.file_bytes(
                HOSTED_BRANCH, "Hangboards/fixture-board/board.json"
            )
        )
        assert stored["holds"][0]["geometry"][0]["frame"] == {
            "x": 0.1,
            "y": 0.1,
            "width": 0.1,
            "height": 0.2,
        }
        put_call = client.calls_named("put_file")[-1]
        assert put_call.args[0] == HOSTED_TOKEN
        assert put_call.args[2] == HOSTED_BRANCH


def test_hosted_save_rejects_slug_identity_changed_after_route_resolution() -> None:
    """Fails if a PUT can write a board whose ID no longer matches its URL."""
    files = _github_files()
    client = _HostedSaveIdentityRaceClient(files)
    with running_server_with_github_backend(
        files, github_client=client
    ) as (base, client, session):
        _status, opened, _headers = hosted_request_json(
            base, session, "GET", "/api/boards/fixture.board"
        )
        document = opened["board"]["document"]
        document["regions"][0]["displayPath"] = (
            "M 177.4 45.7 L 354.8 45.7 L 354.8 137.1 L 177.4 137.1 Z"
        )

        status, payload, _headers = hosted_request_json(
            base, session, "PUT", "/api/boards/fixture.board", document
        )

    assert status == 409
    assert payload["ok"] is False
    assert [call.args[4] for call in client.calls_named("put_file")] == [
        "Concurrent board replacement"
    ]


def test_hosted_git_status_uses_session_branch_and_remote_branches() -> None:
    """Fails if hosted status shells out to the local checkout."""
    with running_server_with_github_backend(_github_files()) as (
        base,
        client,
        session,
    ):
        status, payload, _headers = hosted_request_json(
            base, session, "GET", "/api/git/status"
        )

    assert status == 200
    assert payload == {
        "ok": True,
        "currentBranch": HOSTED_BRANCH,
        "dirty": False,
        "statusLines": [],
        "branches": ["feature", "main", HOSTED_BRANCH],
    }
    assert client.calls_named("list_branches")[-1].args == (HOSTED_TOKEN,)


def test_hosted_checkout_switches_branch_and_reissues_the_session_cookie() -> None:
    """Fails if switching a hosted branch does not persist in the signed session."""
    with running_server_with_github_backend(_github_files()) as (
        base,
        client,
        session,
    ):
        status, payload, headers = hosted_request_json(
            base,
            session,
            "POST",
            "/api/git/checkout",
            {"branch": "feature"},
        )
        cookie = SimpleCookie()
        cookie.load(headers["Set-Cookie"])
        decoded = server_module._decode_session(
            b"test-session-secret", cookie["wb_session"].value
        )

    assert status == 200
    assert payload == {"ok": True, "branch": "feature"}
    assert decoded == _Session(HOSTED_TOKEN, "climber", "feature")
    assert client.calls_named("get_branch_head_sha")[-1].args == (
        HOSTED_TOKEN,
        "feature",
    )


def test_hosted_checkout_creates_from_the_current_head_and_switches() -> None:
    """Fails if hosted branch creation does not fork the current session branch."""
    with running_server_with_github_backend(_github_files()) as (
        base,
        client,
        session,
    ):
        expected_head = client.get_branch_head_sha("setup", HOSTED_BRANCH)

        status, payload, headers = hosted_request_json(
            base,
            session,
            "POST",
            "/api/git/checkout",
            {"branch": "new-feature", "create": True},
        )
        cookie = SimpleCookie()
        cookie.load(headers["Set-Cookie"])
        decoded = server_module._decode_session(
            b"test-session-secret", cookie["wb_session"].value
        )

    assert status == 200
    assert payload == {"ok": True, "branch": "new-feature"}
    assert client.get_branch_head_sha("verify", "new-feature") == expected_head
    assert decoded == _Session(HOSTED_TOKEN, "climber", "new-feature")
    assert (
        HOSTED_TOKEN,
        HOSTED_BRANCH,
    ) in tuple(call.args for call in client.calls_named("get_branch_head_sha"))
    assert client.calls_named("create_branch")[-1].args == (
        HOSTED_TOKEN,
        "new-feature",
        expected_head,
    )


@pytest.mark.parametrize("path", ["/api/git/commit", "/api/git/push"])
def test_hosted_commit_and_push_return_not_found_for_stale_tabs(path: str) -> None:
    """Fails if a stale hosted tab can invoke local repository mutations."""
    with running_server_with_github_backend(_github_files()) as (
        base,
        _client,
        session,
    ):
        status, payload, _headers = hosted_request_json(
            base, session, "POST", path
        )

    assert status == 404
    assert payload == {"ok": False, "error": "not found"}


def test_hosted_open_pull_request_uses_the_session_branch_and_defaults() -> None:
    """Fails if hosted PR creation uses the local gh process or loses defaults."""
    with running_server_with_github_backend(_github_files()) as (
        base,
        client,
        session,
    ):
        status, payload, _headers = hosted_request_json(
            base,
            session,
            "POST",
            "/api/git/open-pr",
            {"title": "Update fixture", "body": "Precise holds"},
        )

    assert status == 200
    assert payload == {
        "ok": True,
        "branch": HOSTED_BRANCH,
        "url": "https://example.test/pull/1",
    }
    assert client.calls_named("create_pull_request")[-1].args == (
        HOSTED_TOKEN,
        "Update fixture",
        HOSTED_BRANCH,
        "main",
        "Precise holds",
    )


@pytest.mark.parametrize(
    ("github_error", "expected_status", "expected_message"),
    [
        (GitHubNotFoundError("remote branch missing"), 404, "remote branch missing"),
        (GitHubRateLimitError("rate limit exhausted"), 429, "rate limit exhausted"),
        (GitHubForbiddenError("permission denied"), 403, "permission denied"),
        (
            GitHubAuthError("token leaked detail"),
            401,
            "GitHub authentication expired or insufficient permissions",
        ),
        (
            GitHubTransportError("socket leaked detail"),
            502,
            "could not reach GitHub",
        ),
    ],
)
def test_hosted_routes_map_typed_github_errors(
    github_error: Exception,
    expected_status: int,
    expected_message: str,
) -> None:
    """Fails if typed GitHub failures collapse into a generic server error."""
    with running_server_with_github_backend(_github_files()) as (
        base,
        client,
        session,
    ):
        def fail_list_branches(_token: str) -> list[str]:
            raise github_error

        client.list_branches = fail_list_branches  # type: ignore[method-assign]
        status, payload, _headers = hosted_request_json(
            base, session, "GET", "/api/git/status"
        )

    assert status == expected_status
    assert payload == {"ok": False, "error": expected_message}


def test_hosted_save_conflict_maps_to_conflict_status() -> None:
    """Fails if an optimistic GitHub save conflict is reported as a bad request."""
    with running_server_with_github_backend(_github_files()) as (
        base,
        client,
        session,
    ):
        _status, opened, _headers = hosted_request_json(
            base, session, "GET", "/api/boards/fixture.board"
        )
        document = opened["board"]["document"]
        document["regions"][0]["displayPath"] = (
            "M 177.4 45.7 L 354.8 45.7 L 354.8 137.1 L 177.4 137.1 Z"
        )
        original_put_file = client.put_file

        def conflicting_put_file(*args: object, **kwargs: object) -> str:
            path = "Hangboards/fixture-board/board.json"
            current = json.loads(client.file_bytes(HOSTED_BRANCH, path))
            current["subtitle"] = "Concurrent change"
            original_put_file(
                "other-token",
                path,
                HOSTED_BRANCH,
                (json.dumps(current, indent=2) + "\n").encode("utf-8"),
                "Concurrent update",
                args[-1],
            )
            return original_put_file(*args, **kwargs)

        client.put_file = conflicting_put_file  # type: ignore[method-assign]
        status, payload, _headers = hosted_request_json(
            base, session, "PUT", "/api/boards/fixture.board", document
        )

    assert status == 409
    assert payload["ok"] is False


def test_auth_status_identifies_hosted_storage() -> None:
    """Fails if the frontend cannot distinguish hosted from local storage."""
    with running_server_with_github_backend(_github_files()) as (
        base,
        _client,
        session,
    ):
        status, payload, _headers = hosted_request_json(
            base, session, "GET", "/api/auth/status"
        )

    assert status == 200
    assert payload == {
        "ok": True,
        "authenticated": True,
        "username": "climber",
        "hostedStorage": True,
    }


def test_oauth_callback_uses_github_client_identity_and_default_branch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Fails if callback identity or branch still come from direct API assumptions."""
    with running_server_with_github_backend(_github_files()) as (
        base,
        client,
        _session,
    ):
        opener = urllib.request.build_opener(_NoRedirectHandler)
        with pytest.raises(HTTPError) as login_redirect:
            opener.open(f"{base}/auth/login")
        oauth_cookie = SimpleCookie()
        oauth_cookie.load(login_redirect.value.headers["Set-Cookie"])
        oauth_state = oauth_cookie["oauth_state"].value

        class TokenResponse:
            def __enter__(self) -> Self:
                return self

            def __exit__(self, *_args: object) -> None:
                return None

            def read(self) -> bytes:
                return b'{"access_token":"ghp_from_callback"}'

        def exchange_token(request: urllib.request.Request) -> TokenResponse:
            assert request.full_url.endswith("/login/oauth/access_token")
            return TokenResponse()

        monkeypatch.setattr(server_module.urllib.request, "urlopen", exchange_token)
        callback = Request(
            f"{base}/auth/callback?code=fixture-code&state={oauth_state}",
            headers={"Cookie": f"oauth_state={oauth_state}"},
        )
        with pytest.raises(HTTPError) as callback_redirect:
            opener.open(callback)
        session_cookie = SimpleCookie()
        session_cookie.load(callback_redirect.value.headers["Set-Cookie"])
        decoded = server_module._decode_session(
            b"test-session-secret", session_cookie["wb_session"].value
        )

    assert decoded == _Session(
        "ghp_from_callback", "climber", HOSTED_BRANCH
    )
    assert client.calls_named("get_authenticated_user")[-1].args == (
        "ghp_from_callback",
    )
    assert client.calls_named("get_default_branch")[-1].args == (
        "ghp_from_callback",
    )


def test_local_oauth_callback_retains_direct_user_lookup_and_main_branch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Fails if hosted GitHub-client callback behavior leaks into local mode."""
    library = _write_library(tmp_path)
    client = FakeGitHubClient(
        {"client-default": {}},
        default_branch="client-default",
        username="client-user",
    )
    httpd = create_server(
        library,
        port=0,
        github_client_id="test-client-id",
        github_client_secret="test-client-secret",
        session_secret="test-session-secret",
        github_client=client,
    )
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        base = f"http://127.0.0.1:{httpd.server_port}"
        opener = urllib.request.build_opener(_NoRedirectHandler)
        with pytest.raises(HTTPError) as login_redirect:
            opener.open(f"{base}/auth/login")
        oauth_cookie = SimpleCookie()
        oauth_cookie.load(login_redirect.value.headers["Set-Cookie"])
        oauth_state = oauth_cookie["oauth_state"].value

        class OAuthResponse:
            def __init__(self, body: bytes) -> None:
                self._body = body

            def __enter__(self) -> Self:
                return self

            def __exit__(self, *_args: object) -> None:
                return None

            def read(self) -> bytes:
                return self._body

        def oauth_request(request: urllib.request.Request) -> OAuthResponse:
            if request.full_url.endswith("/login/oauth/access_token"):
                return OAuthResponse(b'{"access_token":"ghp_local_callback"}')
            assert request.full_url == "https://api.github.com/user"
            return OAuthResponse(b'{"login":"legacy-user"}')

        monkeypatch.setattr(server_module.urllib.request, "urlopen", oauth_request)
        callback = Request(
            f"{base}/auth/callback?code=fixture-code&state={oauth_state}",
            headers={"Cookie": f"oauth_state={oauth_state}"},
        )
        with pytest.raises(HTTPError) as callback_redirect:
            opener.open(callback)
        session_cookie = SimpleCookie()
        session_cookie.load(callback_redirect.value.headers["Set-Cookie"])
        decoded = server_module._decode_session(
            b"test-session-secret", session_cookie["wb_session"].value
        )
    finally:
        httpd.shutdown()
        thread.join(timeout=5)
        httpd.server_close()

    assert decoded == _Session("ghp_local_callback", "legacy-user", "main")
    assert client.calls == []


def test_remote_server_constructs_a_real_github_client_without_an_injected_fake(
    tmp_path: Path,
) -> None:
    """Fails if production hosted construction lacks a GitHub client."""
    library = _write_library(tmp_path)
    httpd = create_server(
        library,
        port=0,
        allow_remote=True,
        github_owner="fixture-owner",
        github_repo="fixture-repo",
    )
    try:
        assert isinstance(httpd.github_client, GitHubClient)
    finally:
        httpd.server_close()


@pytest.mark.parametrize(
    "remote_url",
    [
        "https://github.com/Asherlc/hang-ten.git",
        "git@github.com:Asherlc/hang-ten.git",
        "ssh://git@github.com/Asherlc/hang-ten.git",
    ],
)
def test_remote_cli_autodetects_github_owner_and_repo_with_one_git_query(
    remote_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Fails if hosted CLI startup cannot infer standard GitHub remotes."""
    monkeypatch.delenv("GITHUB_OWNER", raising=False)
    monkeypatch.delenv("GITHUB_REPO", raising=False)
    calls: list[list[str]] = []
    captured: dict[str, object] = {}

    def fake_run(args: list[str], **_kwargs: object) -> SimpleNamespace:
        calls.append(args)
        return SimpleNamespace(returncode=0, stdout=f"{remote_url}\n")

    def fake_create_server(*_args: object, **kwargs: object) -> object:
        captured.update(kwargs)
        return object()

    monkeypatch.setattr(server_module.subprocess, "run", fake_run)
    monkeypatch.setattr(server_module, "create_server", fake_create_server)

    server_module._server_from_cli(
        [
            "--repository-root",
            str(REPOSITORY_ROOT),
            "--port",
            "0",
            "--allow-remote",
            "--github-client-id",
            "test-client-id",
            "--github-client-secret",
            "test-client-secret",
            "--session-secret",
            "test-session-secret",
        ]
    )

    assert calls == [["git", "config", "--get", "remote.origin.url"]]
    assert captured["github_owner"] == "Asherlc"
    assert captured["github_repo"] == "hang-ten"


def test_remote_cli_uses_explicit_owner_and_repo_without_git_autodetection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Fails if explicit repository identity is ignored or triggers git discovery."""
    captured: dict[str, object] = {}

    def unexpected_git(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("git autodetection must not run for explicit values")

    def fake_create_server(*_args: object, **kwargs: object) -> object:
        captured.update(kwargs)
        return object()

    monkeypatch.setattr(server_module.subprocess, "run", unexpected_git)
    monkeypatch.setattr(server_module, "create_server", fake_create_server)

    server_module._server_from_cli(
        [
            "--repository-root",
            str(REPOSITORY_ROOT),
            "--port",
            "0",
            "--allow-remote",
            "--github-client-id",
            "test-client-id",
            "--github-client-secret",
            "test-client-secret",
            "--session-secret",
            "test-session-secret",
            "--github-owner",
            "ExplicitOwner",
            "--github-repo",
            "explicit-repo",
        ]
    )

    assert captured["github_owner"] == "ExplicitOwner"
    assert captured["github_repo"] == "explicit-repo"


def test_remote_cli_uses_environment_owner_and_repo_without_git_autodetection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Fails if the documented owner/repository environment fallbacks are lost."""
    captured: dict[str, object] = {}

    def unexpected_git(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("git autodetection must not run for environment values")

    def fake_create_server(*_args: object, **kwargs: object) -> object:
        captured.update(kwargs)
        return object()

    monkeypatch.setenv("GITHUB_OWNER", "EnvironmentOwner")
    monkeypatch.setenv("GITHUB_REPO", "environment-repo")
    monkeypatch.setattr(server_module.subprocess, "run", unexpected_git)
    monkeypatch.setattr(server_module, "create_server", fake_create_server)

    server_module._server_from_cli(
        [
            "--repository-root",
            str(REPOSITORY_ROOT),
            "--port",
            "0",
            "--allow-remote",
            "--github-client-id",
            "test-client-id",
            "--github-client-secret",
            "test-client-secret",
            "--session-secret",
            "test-session-secret",
        ]
    )

    assert captured["github_owner"] == "EnvironmentOwner"
    assert captured["github_repo"] == "environment-repo"


@pytest.mark.parametrize(
    ("returncode", "remote_url"),
    [
        (1, ""),
        (0, "https://gitlab.com/Elsewhere/not-hang-ten.git"),
    ],
    ids=["git-config-failed", "unsupported-remote"],
)
def test_remote_cli_rejects_failed_or_unsupported_repository_autodetection(
    returncode: int,
    remote_url: str,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Fails if hosted startup proceeds without an unambiguous GitHub target."""
    monkeypatch.delenv("GITHUB_OWNER", raising=False)
    monkeypatch.delenv("GITHUB_REPO", raising=False)
    calls: list[list[str]] = []

    def fake_run(args: list[str], **_kwargs: object) -> SimpleNamespace:
        calls.append(args)
        return SimpleNamespace(returncode=returncode, stdout=f"{remote_url}\n")

    def unexpected_create_server(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("server must not start without repository identity")

    monkeypatch.setattr(server_module.subprocess, "run", fake_run)
    monkeypatch.setattr(server_module, "create_server", unexpected_create_server)

    with pytest.raises(SystemExit) as error:
        server_module._server_from_cli(
            [
                "--repository-root",
                str(REPOSITORY_ROOT),
                "--port",
                "0",
                "--allow-remote",
                "--github-client-id",
                "test-client-id",
                "--github-client-secret",
                "test-client-secret",
                "--session-secret",
                "test-session-secret",
            ]
        )

    assert error.value.code == 2
    assert calls == [["git", "config", "--get", "remote.origin.url"]]
    error_text = capsys.readouterr().err
    assert "--github-owner" in error_text
    assert "--github-repo" in error_text
