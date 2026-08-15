#!/usr/bin/env python3
"""Local HTTP boundary for direct Hangboard Workbench board packages."""

from __future__ import annotations

import json
import mimetypes
import re
from argparse import ArgumentParser
from contextlib import contextmanager
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from ipaddress import ip_address
from pathlib import Path
from typing import Any, Iterator
from urllib.parse import unquote, urlsplit

from board_package import (
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
) -> "WorkbenchHTTPServer":
    """Create a direct board-package server with no workspace lifecycle state."""
    resolved_editor_root = Path(editor_root).resolve(strict=False)
    for asset in dict.fromkeys(asset for _route, asset in STATIC_ASSET_ROUTES):
        if not (resolved_editor_root / asset).is_file():
            raise StaticAssetError(f"required static asset is missing: {asset}")
    try:
        resolved_library_root = Path(library_root).resolve(strict=True)
    except OSError as error:
        raise EditorError("board library is unavailable") from error
    if not resolved_library_root.is_dir():
        raise EditorError("board library is unavailable")
    return WorkbenchHTTPServer(
        (host, port),
        EditorRequestHandler,
        editor_root=resolved_editor_root,
        library_root=resolved_library_root,
        allow_remote=allow_remote,
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
    ) -> None:
        self.editor_root = editor_root
        self.library_root = library_root
        self.allow_remote = allow_remote
        super().__init__(server_address, request_handler)


class EditorRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        if not self._allow_request(mutation=False):
            return
        request = urlsplit(self.path)
        path = request.path
        if path == "/api/health":
            self._send_json(HTTPStatus.OK, {"ok": True})
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
        except BoardPackageError as error:
            message = _safe_message(error, "could not load board")
            status = HTTPStatus.NOT_FOUND if message == "board is not available" else HTTPStatus.BAD_REQUEST
            self._send_json(status, {"ok": False, "error": message if status == HTTPStatus.NOT_FOUND else "could not load board"})
            return
        except OSError:
            self._send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"ok": False, "error": "could not load board"})
            return
        self._send_json(HTTPStatus.OK, {"ok": True, "board": payload})

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
        try:
            yield
        except RequestError as error:
            self._send_json(error.status, {"ok": False, "error": str(error)})
        except BoardPackageError as error:
            self._send_json(HTTPStatus.BAD_REQUEST, {"ok": False, "error": _safe_message(error, "could not save board")})
        except OSError:
            self._send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"ok": False, "error": "could not save board"})
        except Exception:
            self._send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"ok": False, "error": "could not save board"})

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

    def _allow_request(self, *, mutation: bool) -> bool:
        if self.server.allow_remote:
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
    resolved_root = Path(root).expanduser().resolve(strict=False)
    markers = (
        resolved_root / ".git",
        resolved_root / "Hangboards",
        resolved_root / "Tools" / "HangboardWorkbench" / "server.py",
        resolved_root / "Tools" / "HangboardWorkbench" / "board_package.py",
        resolved_root / "Tools" / "HangboardWorkbench" / "board_geometry.py",
    )
    if (
        not resolved_root.is_dir()
        or not markers[0].exists()
        or not markers[1].is_dir()
        or any(not marker.is_file() for marker in markers[2:])
    ):
        raise EditorError("repository root must be a Hang Ten checkout")
    return resolved_root


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
    return parser


def _server_from_cli(arguments: list[str] | None = None, *, editor_root: Path = EDITOR_ROOT) -> tuple[WorkbenchHTTPServer, None]:
    parser = _argument_parser()
    parsed = parser.parse_args(arguments)
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
