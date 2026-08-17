#!/usr/bin/env python3
"""Local HTTP boundary for direct Hangboard Workbench board packages."""

from __future__ import annotations

import hashlib
import json
import mimetypes
import os
import re
import secrets
import stat
import subprocess
import urllib.error
import urllib.request
from argparse import ArgumentParser
from contextlib import contextmanager
from dataclasses import dataclass
from http import HTTPStatus
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from ipaddress import ip_address
from pathlib import Path
from typing import Any, Iterator
from urllib.parse import unquote, urlsplit

from board_package import (
    BoardNotAvailableError,
    BoardPackage,
    BoardPackageError,
    discover_packages,
    editor_document,
    open_package,
    primary_image_path,
    save_editor_document,
)
from workbench_assets import STATIC_ASSET_ROUTES


MAX_REQUEST_BYTES = 10 * 1024 * 1024
EDITOR_ROOT = Path(__file__).resolve().parent
_ABSOLUTE_PATH_IN_TEXT = re.compile(r"(?:(?<![A-Za-z0-9/])/(?!/)[^\s/]|[A-Za-z]:[\\/])")


class EditorError(ValueError):
    """A safe, user-facing direct Workbench error."""


class RequestError(EditorError):
    """A safe request error with its intended HTTP status."""

    def __init__(self, status: HTTPStatus, message: str) -> None:
        super().__init__(message)
        self.status = status


class StaticAssetError(EditorError):
    """A required UI asset is unavailable."""


class ServerBindError(EditorError):
    """The local listener could not bind."""


def _safe_message(error: Exception, fallback: str) -> str:
    message = str(error)
    return fallback if not message or _ABSOLUTE_PATH_IN_TEXT.search(message) else message


def _validate_git_arg(value: str, name: str) -> str:
    """Reject user-provided values that could be interpreted as flags."""
    if not value:
        raise RequestError(HTTPStatus.BAD_REQUEST, f"{name} is required")
    if value.startswith("-"):
        raise RequestError(HTTPStatus.BAD_REQUEST, f"{name} must not start with a dash")
    if "\0" in value:
        raise RequestError(HTTPStatus.BAD_REQUEST, f"{name} contains invalid characters")
    return value


@dataclass
class _Session:
    token: str
    username: str


def _display_name(package: BoardPackage) -> str:
    manufacturer = package.board["manufacturer"]
    name = package.board["name"]
    return f"{manufacturer} {name}".strip()


def _board_payload(package: BoardPackage, *, include_document: bool) -> dict[str, object]:
    board_id = package.board_id
    payload: dict[str, object] = {
        "boardId": board_id,
        "displayName": _display_name(package),
        "holdCount": len(package.hold_ids),
        "href": f"/api/boards/{board_id}",
    }
    if include_document:
        payload.update(
            imageUrl=f"/api/boards/{board_id}/image",
            saveUrl=f"/api/boards/{board_id}",
            document=editor_document(package),
        )
    return payload


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
    """Create a direct board-package server with no workspace lifecycle state."""
    resolved_editor_root = Path(editor_root).resolve(strict=False)
    for asset in dict.fromkeys(asset for _route, asset in STATIC_ASSET_ROUTES):
        if not (resolved_editor_root / asset).is_file():
            raise StaticAssetError(f"required static asset is missing: {asset}")
    resolved_library_root = _resolved_lexical_directory(
        library_root,
        unavailable_message="board library is unavailable",
        symlink_message="board library must not be a symlink",
    )
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


class EditorRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        request = urlsplit(self.path)
        path = request.path
        if path == "/auth/login":
            self._handle_login()
            return
        if path == "/auth/callback":
            self._handle_callback()
            return
        if path == "/api/auth/status":
            self._handle_auth_status()
            return
        if path == "/api/health":
            self._send_json(HTTPStatus.OK, {"ok": True})
            return
        if not self._allow_request(mutation=False):
            return
        if path == "/api/git/status":
            self._get_git_status()
            return
        if path == "/api/boards":
            self._get_boards()
            return
        if path.startswith("/api/boards/"):
            board_path = path.removeprefix("/api/boards/")
            if board_path.endswith("/image") and "/" not in board_path.removesuffix("/image"):
                self._get_image(unquote(board_path.removesuffix("/image")))
                return
            if "/" not in board_path:
                self._get_board(unquote(board_path))
                return
        filename = next((asset for route, asset in STATIC_ASSET_ROUTES if route == path), None)
        if filename is not None:
            try:
                self._send_file(self.server.editor_root / filename)
            except OSError:
                self._send_json(HTTPStatus.NOT_FOUND, {"ok": False, "error": "static asset not found"})
            return
        self._send_json(HTTPStatus.NOT_FOUND, {"ok": False, "error": "not found"})

    def do_PUT(self) -> None:  # noqa: N802
        if not self._allow_request(mutation=True):
            return
        request = urlsplit(self.path)
        board_path = request.path.removeprefix("/api/boards/")
        if not request.path.startswith("/api/boards/") or not board_path or "/" in board_path:
            self._send_json(HTTPStatus.NOT_FOUND, {"ok": False, "error": "not found"})
            return
        with self._mutation_error_response():
            document = self._read_json_object()
            package = open_package(self.server.library_root, unquote(board_path))
            saved = save_editor_document(self.server.library_root, package.root.name, document)
            self._send_json(HTTPStatus.OK, {"ok": True, "board": _board_payload(saved, include_document=True)})

    def do_POST(self) -> None:  # noqa: N802
        if not self._allow_request(mutation=True):
            return
        request = urlsplit(self.path)
        if request.path == "/api/git/checkout":
            with self._mutation_error_response():
                body = self._read_json_object()
                self._post_checkout(body)
            return
        if request.path == "/api/git/commit":
            with self._mutation_error_response():
                body = self._read_json_object()
                self._post_commit(body)
            return
        if request.path == "/api/git/push":
            with self._mutation_error_response():
                body = self._read_json_object()
                self._post_push(body)
            return
        if request.path == "/api/git/open-pr":
            with self._mutation_error_response():
                body = self._read_json_object()
                self._post_open_pull_request(body)
            return
        if request.path == "/api/boards":
            self._send_json(HTTPStatus.NOT_FOUND, {"ok": False, "error": "not found"})
            return
        self._send_json(HTTPStatus.NOT_FOUND, {"ok": False, "error": "not found"})

    def do_PATCH(self) -> None:  # noqa: N802
        if not self._allow_request(mutation=True):
            return
        self._send_json(HTTPStatus.NOT_FOUND, {"ok": False, "error": "not found"})

    def _get_boards(self) -> None:
        try:
            boards = [
                _board_payload(package, include_document=False)
                for package in discover_packages(self.server.library_root)
            ]
        except BoardPackageError:
            self._send_json(HTTPStatus.BAD_REQUEST, {"ok": False, "error": "could not load boards"})
            return
        except OSError:
            self._send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"ok": False, "error": "board library is unavailable"})
            return
        self._send_json(HTTPStatus.OK, {"ok": True, "boards": boards})

    def _get_board(self, board_id: str) -> None:
        if not board_id:
            self._send_json(HTTPStatus.NOT_FOUND, {"ok": False, "error": "not found"})
            return
        try:
            package = open_package(self.server.library_root, board_id)
            payload = _board_payload(package, include_document=True)
        except BoardNotAvailableError:
            self._send_json(
                HTTPStatus.NOT_FOUND,
                {"ok": False, "error": "board is not available"},
            )
            return
        except BoardPackageError:
            self._send_json(
                HTTPStatus.BAD_REQUEST,
                {"ok": False, "error": "could not load board"},
            )
            return
        except OSError:
            self._send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"ok": False, "error": "could not load board"})
            return
        self._send_json(HTTPStatus.OK, {"ok": True, "board": payload})

    def _get_git_status(self) -> None:
        branch = self._git_current_branch()
        status_lines = self._git_status_lines()
        branches = self._git_branches()
        self._send_json(
            HTTPStatus.OK,
            {
                "ok": True,
                "currentBranch": branch,
                "dirty": bool(status_lines),
                "statusLines": status_lines,
                "branches": branches,
            },
        )

    def _post_checkout(self, body: dict[str, Any]) -> None:
        branch = body.get("branch")
        if not isinstance(branch, str):
            raise RequestError(HTTPStatus.BAD_REQUEST, "branch must be a string")
        sanitized_branch = _validate_git_arg(branch.strip(), "branch")
        self._run_git(["git", "check-ref-format", "--branch", sanitized_branch])
        self._run_git(["git", "switch", "--", sanitized_branch])
        self._send_json(HTTPStatus.OK, {"ok": True, "branch": sanitized_branch})

    def _post_commit(self, body: dict[str, Any]) -> None:
        message = body.get("message")
        if not isinstance(message, str):
            raise RequestError(HTTPStatus.BAD_REQUEST, "message must be a string")
        message = _validate_git_arg(message.strip(), "message")
        if not self._git_status_lines():
            raise RequestError(HTTPStatus.CONFLICT, "no changes to commit")
        self._run_git(["git", "add", "-A"])
        self._run_git(
            ["git", "commit", "--message", message],
            fallback="could not create commit",
        )
        commit = self._run_git(["git", "rev-parse", "HEAD"]).stdout.strip()
        self._send_json(
            HTTPStatus.OK,
            {
                "ok": True,
                "branch": self._git_current_branch(),
                "commit": commit,
                "message": message,
            },
        )

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

    def _post_open_pull_request(self, body: dict[str, Any]) -> None:
        branch = body.get("branch")
        if branch is None:
            branch = self._git_current_branch()
        if not isinstance(branch, str):
            raise RequestError(HTTPStatus.BAD_REQUEST, "branch must be a string")
        branch = branch.strip() or self._git_current_branch()
        _validate_git_arg(branch, "branch")
        title = body.get("title")
        if not isinstance(title, str):
            raise RequestError(HTTPStatus.BAD_REQUEST, "title must be a string")
        title = _validate_git_arg(title.strip(), "title")
        body_text = body.get("body", "")
        base = body.get("base", "main")
        if not isinstance(body_text, str):
            raise RequestError(HTTPStatus.BAD_REQUEST, "body must be a string")
        if not isinstance(base, str):
            raise RequestError(HTTPStatus.BAD_REQUEST, "base must be a string")
        base = _validate_git_arg(base.strip() or "main", "base")
        command = [
            "gh",
            "pr",
            "create",
            "--title",
            title,
            "--head",
            branch,
            "--base",
            base,
        ]
        if body_text:
            command.extend(["--body", body_text])
        pr_url = self._run_git(
            command,
            fallback="could not create pull request",
            auth_token=self._get_auth_token(),
        ).stdout.strip()
        self._send_json(
            HTTPStatus.OK,
            {
                "ok": True,
                "branch": branch,
                "url": pr_url,
            },
        )

    def _get_image(self, board_id: str) -> None:
        try:
            package = open_package(self.server.library_root, board_id)
            image = primary_image_path(package)
            self._send_file(image)
        except BoardPackageError:
            self._send_json(HTTPStatus.NOT_FOUND, {"ok": False, "error": "board image is unavailable"})
        except OSError:
            self._send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"ok": False, "error": "board image is unavailable"})

    @contextmanager
    def _mutation_error_response(self) -> Iterator[None]:
        scope = self._mutation_scope()
        board_error_message = "could not save board"
        operation_error_message = (
            "could not perform repository operation" if scope == "git" else "could not save board"
        )
        try:
            yield
        except RequestError as error:
            self._send_json(error.status, {"ok": False, "error": str(error)})
        except BoardNotAvailableError:
            self._send_json(
                HTTPStatus.NOT_FOUND,
                {"ok": False, "error": "board is not available"},
            )
        except BoardPackageError as error:
            self._send_json(
                HTTPStatus.BAD_REQUEST,
                {
                    "ok": False,
                    "error": _safe_message(
                        error,
                        operation_error_message if scope == "git" else board_error_message,
                    ),
                },
            )
        except OSError:
            self._send_json(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                {"ok": False, "error": operation_error_message if scope == "git" else board_error_message},
            )
        except Exception:
            self._send_json(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                {"ok": False, "error": operation_error_message if scope == "git" else board_error_message},
            )

    def _mutation_scope(self) -> str:
        if self.path.startswith("/api/git/"):
            return "git"
        if self.path.startswith("/api/boards"):
            return "board"
        return "other"

    def _read_json_object(self) -> dict[str, Any]:
        if self.headers.get_content_type() != "application/json":
            raise RequestError(HTTPStatus.UNSUPPORTED_MEDIA_TYPE, "Content-Type must be application/json")
        try:
            payload = json.loads(self._read_body())
        except (json.JSONDecodeError, UnicodeDecodeError) as error:
            raise RequestError(HTTPStatus.BAD_REQUEST, "request body must be valid JSON") from error
        if not isinstance(payload, dict):
            raise RequestError(HTTPStatus.BAD_REQUEST, "request body must be a JSON object")
        return payload

    def _read_body(self) -> bytes:
        try:
            length = int(self.headers.get("Content-Length", ""))
        except ValueError:
            length = -1
        if length < 0:
            raise RequestError(HTTPStatus.LENGTH_REQUIRED, "Content-Length is required")
        if length > MAX_REQUEST_BYTES:
            raise RequestError(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, "request exceeds 10 MiB")
        return self.rfile.read(length)

    def _git_current_branch(self) -> str:
        branch = self._run_git([
            "git",
            "rev-parse",
            "--abbrev-ref",
            "HEAD",
        ], fallback="could not detect current branch").stdout.strip()
        if branch == "HEAD":
            raise RequestError(HTTPStatus.CONFLICT, "repository is in detached HEAD state")
        if not branch:
            raise RequestError(HTTPStatus.CONFLICT, "repository branch is unknown")
        return branch

    def _git_status_lines(self) -> list[str]:
        output = self._run_git([
            "git",
            "status",
            "--short",
        ], fallback="could not read git status").stdout
        return [line for line in output.splitlines() if line.strip()]

    def _git_branches(self) -> list[str]:
        output = self._run_git(
            ["git", "branch", "--format=%(refname:short)"],
            fallback="could not list branches",
        ).stdout
        return [line for line in output.splitlines() if line.strip()]

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
                # codeql[py/command-line-injection] -- callers validate user-supplied values via _validate_git_arg before they reach args
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
            if auth_token and (
                "Authentication failed" in message or "401" in message or "403" in message
            ):
                raise RequestError(HTTPStatus.UNAUTHORIZED, "GitHub authentication expired or insufficient permissions")
            raise RequestError(HTTPStatus.BAD_REQUEST, _safe_message(RuntimeError(message), fallback))
        return process

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

    def _get_auth_token(self) -> str | None:
        session = self._get_session()
        return session.token if session else None

    def _set_session_cookie(self, session_id: str) -> None:
        cookie = SimpleCookie()
        cookie["wb_session"] = session_id
        cookie["wb_session"]["path"] = "/"
        cookie["wb_session"]["httponly"] = True
        cookie["wb_session"]["samesite"] = "Lax"
        if self.server.allow_remote:
            cookie["wb_session"]["secure"] = True
        self.send_header("Set-Cookie", cookie["wb_session"].OutputString())

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
        if self.server.allow_remote:
            cookie["oauth_state"]["secure"] = True
        cookie["oauth_state"]["max-age"] = "600"
        self.send_header("Set-Cookie", cookie["oauth_state"].OutputString())
        self.end_headers()

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
        except (urllib.error.URLError, json.JSONDecodeError):
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

    def _handle_auth_status(self) -> None:
        session = self._get_session()
        if session:
            self._send_json(HTTPStatus.OK, {"ok": True, "authenticated": True, "username": session.username})
        else:
            self._send_json(HTTPStatus.OK, {"ok": True, "authenticated": False})

    def _send_json(self, status: HTTPStatus, value: object) -> None:
        body = json.dumps(value, separators=(",", ":"), allow_nan=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, path: Path) -> None:
        body = path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", mimetypes.guess_type(path.name)[0] or "application/octet-stream")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        return


def _loopback_peer(value: object) -> bool:
    if not isinstance(value, tuple) or not value or not isinstance(value[0], str):
        return False
    try:
        return ip_address(value[0]).is_loopback
    except ValueError:
        return False


def _loopback_authority(value: object, selected_port: int) -> tuple[str, int] | None:
    if not isinstance(value, str) or not value or value.strip() != value:
        return None
    try:
        parsed = urlsplit(f"//{value}")
        port = parsed.port if parsed.port is not None else 80
    except ValueError:
        return None
    if not parsed.hostname or parsed.username or parsed.password or parsed.path or parsed.query or parsed.fragment or port != selected_port:
        return None
    hostname = parsed.hostname.lower().rstrip(".")
    if hostname == "localhost":
        return hostname, port
    try:
        return (hostname, port) if ip_address(hostname).is_loopback else None
    except ValueError:
        return None


def _loopback_origin(value: object, selected_port: int) -> tuple[str, int] | None:
    if not isinstance(value, str) or not value or value.strip() != value:
        return None
    parsed = urlsplit(value)
    if parsed.scheme.lower() != "http" or not parsed.netloc or parsed.path or parsed.query or parsed.fragment:
        return None
    return _loopback_authority(parsed.netloc, selected_port)


def validate_hang_ten_checkout(root: Path) -> Path:
    """Accept a checkout containing the direct Workbench and board library."""
    resolved_root = _resolved_lexical_directory(
        root,
        unavailable_message="repository root must be a Hang Ten checkout",
        symlink_message="repository root must be a Hang Ten checkout",
    )
    git_marker = resolved_root / ".git"
    hangboards = resolved_root / "Hangboards"
    workbench = resolved_root / "Tools" / "HangboardWorkbench"
    source_files = (
        workbench / "server.py",
        workbench / "board_package.py",
        workbench / "board_geometry.py",
    )
    if (
        not _is_lexical_file_or_directory(git_marker)
        or not _is_lexical_directory(hangboards)
        or not _is_lexical_directory(workbench)
        or any(not _is_lexical_file(source_file) for source_file in source_files)
    ):
        raise EditorError("repository root must be a Hang Ten checkout")
    return resolved_root


def _resolved_lexical_directory(
    path: Path,
    *,
    unavailable_message: str,
    symlink_message: str,
) -> Path:
    lexical = Path(path).expanduser()
    try:
        mode = lexical.lstat().st_mode
    except OSError as error:
        raise EditorError(unavailable_message) from error
    if stat.S_ISLNK(mode):
        raise EditorError(symlink_message)
    if not stat.S_ISDIR(mode):
        raise EditorError(unavailable_message)
    try:
        return lexical.resolve(strict=True)
    except OSError as error:
        raise EditorError(unavailable_message) from error


def _is_lexical_directory(path: Path) -> bool:
    try:
        return stat.S_ISDIR(path.lstat().st_mode)
    except OSError:
        return False


def _is_lexical_file(path: Path) -> bool:
    try:
        return stat.S_ISREG(path.lstat().st_mode)
    except OSError:
        return False


def _is_lexical_file_or_directory(path: Path) -> bool:
    try:
        mode = path.lstat().st_mode
    except OSError:
        return False
    return stat.S_ISREG(mode) or stat.S_ISDIR(mode)


def _discover_repository_root(start: Path) -> Path:
    candidate = Path(start).expanduser().resolve(strict=False)
    while True:
        try:
            return validate_hang_ten_checkout(candidate)
        except EditorError:
            if candidate.parent == candidate:
                raise EditorError("could not find a repository root from the current directory")
            candidate = candidate.parent


def _argument_parser() -> ArgumentParser:
    parser = ArgumentParser(description="Serve the direct Hangboard Workbench tools")
    parser.add_argument("--repository-root", type=Path, help="Checkout containing Hangboards/")
    parser.add_argument("--host", default="127.0.0.1", help="Listen address (default: 127.0.0.1)")
    parser.add_argument("--port", default=4173, type=int, help="Listen port (default: 4173)")
    parser.add_argument(
        "--allow-remote",
        action="store_true",
        help="Allow non-loopback web clients (for hosted deployment only)",
    )
    parser.add_argument(
        "--github-client-id",
        default=os.environ.get("GITHUB_CLIENT_ID", ""),
        help="GitHub OAuth App client ID (required for --allow-remote auth; "
        "falls back to the GITHUB_CLIENT_ID environment variable)",
    )
    parser.add_argument(
        "--github-client-secret",
        default=os.environ.get("GITHUB_CLIENT_SECRET", ""),
        help="GitHub OAuth App client secret (required for --allow-remote auth; "
        "falls back to the GITHUB_CLIENT_SECRET environment variable)",
    )
    return parser


def _server_from_cli(arguments: list[str] | None = None, *, editor_root: Path = EDITOR_ROOT) -> tuple[WorkbenchHTTPServer, None]:
    parser = _argument_parser()
    parsed = parser.parse_args(arguments)
    if parsed.allow_remote and (not parsed.github_client_id or not parsed.github_client_secret):
        parser.error("--allow-remote requires --github-client-id and --github-client-secret")
    try:
        root = validate_hang_ten_checkout(parsed.repository_root) if parsed.repository_root is not None else _discover_repository_root(Path.cwd())
    except EditorError as error:
        parser.error(str(error))
    try:
        httpd = create_server(
            root / "Hangboards",
            parsed.host,
            parsed.port,
            allow_remote=parsed.allow_remote,
            editor_root=editor_root,
            github_client_id=parsed.github_client_id,
            github_client_secret=parsed.github_client_secret,
        )
    except OSError as error:
        raise ServerBindError(f"could not bind to {parsed.host}:{parsed.port}") from error
    return httpd, None


def main() -> None:
    httpd, _ = _server_from_cli()
    print(f"Hangboard Workbench: http://{httpd.server_address[0]}:{httpd.server_address[1]}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()


if __name__ == "__main__":
    main()
