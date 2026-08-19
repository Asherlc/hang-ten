#!/usr/bin/env python3
"""Capture the completed Hangboard Workbench catalog through its editor surface."""

from __future__ import annotations

import base64
import hashlib
import json
import os
import secrets
import socket
import struct
import subprocess
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from argparse import ArgumentParser
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterator


STARTUP_TIMEOUT_SECONDS = 15
READINESS_TIMEOUT_SECONDS = 20
REQUEST_TIMEOUT_SECONDS = 3
VIEWPORT_WIDTH = 1600
VIEWPORT_HEIGHT = 1200
LABEL_HEIGHT = 34
CONTACT_SHEET_COLUMNS = 3


class CaptureError(RuntimeError):
    """A structured failure from a named catalog capture stage."""

    def __init__(self, stage: str, message: str, *, board_id: str | None = None) -> None:
        self.stage = stage
        self.board_id = board_id
        subject = f" {board_id}" if board_id else ""
        super().__init__(f"{stage}{subject}: {message}")


@dataclass(frozen=True)
class CatalogBoard:
    board_id: str
    display_name: str


@dataclass(frozen=True)
class CaptureEntry:
    board_id: str
    display_name: str
    region_count: int
    filename: str


@dataclass(frozen=True)
class CaptureManifest:
    entries: tuple[CaptureEntry, ...]

    def write(self, output_root: Path) -> Path:
        path = output_root / "manifest.json"
        path.write_text(
            json.dumps({"boards": [asdict(entry) for entry in self.entries]}, indent=2)
            + "\n",
            encoding="utf-8",
        )
        return path


def capture_filename(board_id: str) -> str:
    """Return a traversal-safe PNG name derived only from a board ID."""
    normalized = "".join(
        character.lower() if character.isalnum() or character in ".-" else "-"
        for character in board_id.strip()
    ).strip(".-")
    normalized = "-".join(piece for piece in normalized.split("-") if piece)
    if not normalized:
        raise CaptureError("catalog", "board ID cannot produce a safe filename", board_id=board_id)
    return f"{normalized}.png"


def _request_json(url: str) -> dict[str, Any]:
    request = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            value = json.loads(response.read())
    except (OSError, urllib.error.URLError, json.JSONDecodeError) as error:
        raise CaptureError("api", f"could not read {url}") from error
    if not isinstance(value, dict):
        raise CaptureError("api", f"{url} returned an invalid JSON object")
    return value


def fetch_catalog(base_url: str) -> tuple[CatalogBoard, ...]:
    """Read completed board order directly from the Workbench catalog endpoint."""
    payload = _request_json(f"{base_url}/api/boards")
    boards = payload.get("boards")
    if payload.get("ok") is not True or not isinstance(boards, list):
        raise CaptureError("catalog", "Workbench returned an invalid board catalog")
    result: list[CatalogBoard] = []
    for board in boards:
        if not isinstance(board, dict):
            raise CaptureError("catalog", "Workbench returned an invalid board entry")
        board_id = board.get("boardId")
        display_name = board.get("displayName")
        if not isinstance(board_id, str) or not board_id or not isinstance(display_name, str):
            raise CaptureError("catalog", "Workbench returned an invalid board entry")
        result.append(CatalogBoard(board_id, display_name))
    return tuple(result)


def _board_region_count(base_url: str, board_id: str) -> int:
    encoded_id = urllib.parse.quote(board_id, safe="")
    payload = _request_json(f"{base_url}/api/boards/{encoded_id}")
    board = payload.get("board")
    if payload.get("ok") is not True or not isinstance(board, dict):
        raise CaptureError("board", "Workbench returned an invalid board document", board_id=board_id)
    document = board.get("document")
    image_url = board.get("imageUrl")
    if not isinstance(document, dict) or not isinstance(image_url, str) or not image_url:
        raise CaptureError("board", "board document is missing its primary image", board_id=board_id)
    regions = document.get("regions")
    if not isinstance(regions, list):
        raise CaptureError("board", "board document is missing regions", board_id=board_id)
    return len(regions)


def capture_is_ready(value: object, *, expected_region_count: int) -> bool:
    """Validate the editor's image and complete region inventory readiness signal."""
    return (
        isinstance(value, dict)
        and value.get("primaryImageLoaded") is True
        and value.get("regionCount") == expected_region_count
    )


def catalog_controls_are_ready(value: object, *, expected_count: int) -> bool:
    return isinstance(value, dict) and value.get("boardButtonCount") == expected_count


def _readiness_expression() -> str:
    return """
      (async () => {
        const image = document.getElementById('board-image');
        const href = image?.href?.baseVal || image?.getAttribute('href');
        let primaryImageLoaded = false;
        if (href && image?.getBoundingClientRect().width > 0) {
          try { primaryImageLoaded = (await fetch(href, { cache: 'no-store' })).ok; } catch (_) {}
        }
        return {
          primaryImageLoaded,
          regionCount: document.querySelectorAll('#hold-overlay path.region-shape').length,
        };
      })()
    """


@contextmanager
def _managed_process(command: list[str], *, stage: str) -> Iterator[subprocess.Popen[str]]:
    try:
        process = subprocess.Popen(
            command,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            text=True,
        )
    except OSError as error:
        raise CaptureError(stage, f"could not start {command[0]}") from error
    try:
        yield process
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)


def _wait_for_server(base_url: str, process: subprocess.Popen[str]) -> None:
    deadline = time.monotonic() + STARTUP_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise CaptureError("server", "Workbench server exited during startup")
        try:
            if _request_json(f"{base_url}/api/health").get("ok") is True:
                return
        except CaptureError:
            pass
        time.sleep(0.1)
    raise CaptureError("server", "timed out waiting for Workbench server")


def _available_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(("127.0.0.1", 0))
        return int(listener.getsockname()[1])


class _DevToolsConnection:
    def __init__(self, websocket_url: str) -> None:
        parsed = urllib.parse.urlsplit(websocket_url)
        if parsed.scheme != "ws" or not parsed.hostname or not parsed.port:
            raise CaptureError("devtools", "Chrome returned an invalid DevTools websocket URL")
        self._socket = socket.create_connection((parsed.hostname, parsed.port), timeout=REQUEST_TIMEOUT_SECONDS)
        self._socket.settimeout(READINESS_TIMEOUT_SECONDS)
        resource = parsed.path + (f"?{parsed.query}" if parsed.query else "")
        key = base64.b64encode(os.urandom(16)).decode("ascii")
        request = (
            f"GET {resource} HTTP/1.1\r\nHost: {parsed.hostname}:{parsed.port}\r\n"
            "Upgrade: websocket\r\nConnection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n"
        )
        self._socket.sendall(request.encode("ascii"))
        response = self._receive_http_headers()
        accept = base64.b64encode(
            hashlib.sha1((key + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11").encode("ascii")).digest()
        ).decode("ascii")
        if not response.startswith("http/1.1 101") or f"sec-websocket-accept: {accept.lower()}" not in response:
            self.close()
            raise CaptureError("devtools", "Chrome rejected the DevTools websocket connection")
        self._next_id = 1

    def _receive_http_headers(self) -> str:
        data = bytearray()
        while b"\r\n\r\n" not in data:
            chunk = self._socket.recv(4096)
            if not chunk:
                break
            data.extend(chunk)
        return data.decode("ascii", "replace").lower()

    def _receive_exactly(self, length: int) -> bytes:
        data = bytearray()
        while len(data) < length:
            chunk = self._socket.recv(length - len(data))
            if not chunk:
                raise CaptureError("devtools", "DevTools websocket closed unexpectedly")
            data.extend(chunk)
        return bytes(data)

    def _send(self, value: dict[str, Any]) -> None:
        payload = json.dumps(value, separators=(",", ":")).encode("utf-8")
        mask = secrets.token_bytes(4)
        length = len(payload)
        if length < 126:
            header = bytes((0x81, 0x80 | length))
        elif length <= 0xFFFF:
            header = bytes((0x81, 0x80 | 126)) + struct.pack("!H", length)
        else:
            header = bytes((0x81, 0x80 | 127)) + struct.pack("!Q", length)
        masked = bytes(byte ^ mask[index % 4] for index, byte in enumerate(payload))
        self._socket.sendall(header + mask + masked)

    def _receive(self) -> dict[str, Any]:
        first, second = self._receive_exactly(2)
        opcode = first & 0x0F
        length = second & 0x7F
        if length == 126:
            length = struct.unpack("!H", self._receive_exactly(2))[0]
        elif length == 127:
            length = struct.unpack("!Q", self._receive_exactly(8))[0]
        masked = bool(second & 0x80)
        mask = self._receive_exactly(4) if masked else b""
        payload = self._receive_exactly(length)
        if masked:
            payload = bytes(byte ^ mask[index % 4] for index, byte in enumerate(payload))
        if opcode == 8:
            raise CaptureError("devtools", "DevTools websocket closed unexpectedly")
        if opcode == 9:
            self._socket.sendall(b"\x8a\x00")
            return self._receive()
        if opcode != 1:
            raise CaptureError("devtools", "DevTools returned an unsupported websocket frame")
        try:
            value = json.loads(payload)
        except json.JSONDecodeError as error:
            raise CaptureError("devtools", "DevTools returned invalid JSON") from error
        if not isinstance(value, dict):
            raise CaptureError("devtools", "DevTools returned an invalid message")
        return value

    def call(self, method: str, **params: Any) -> dict[str, Any]:
        call_id = self._next_id
        self._next_id += 1
        self._send({"id": call_id, "method": method, "params": params})
        while True:
            response = self._receive()
            if response.get("id") != call_id:
                continue
            if "error" in response:
                raise CaptureError("devtools", f"{method} failed: {response['error']}")
            result = response.get("result")
            if not isinstance(result, dict):
                raise CaptureError("devtools", f"{method} returned an invalid result")
            return result

    def close(self) -> None:
        try:
            self._socket.close()
        except OSError:
            pass


def page_websocket_url(targets: object) -> str | None:
    if not isinstance(targets, list):
        return None
    for target in targets:
        if isinstance(target, dict) and target.get("type") == "page":
            websocket_url = target.get("webSocketDebuggerUrl")
            if isinstance(websocket_url, str):
                return websocket_url
    return None


def _devtools_targets(endpoint: str) -> list[object]:
    try:
        with urllib.request.urlopen(endpoint, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            targets = json.loads(response.read())
    except (OSError, urllib.error.URLError, json.JSONDecodeError) as error:
        raise CaptureError("chrome", "could not read Chrome DevTools targets") from error
    if not isinstance(targets, list):
        raise CaptureError("chrome", "Chrome returned invalid DevTools targets")
    return targets


def _create_devtools_page(endpoint: str) -> str | None:
    request = urllib.request.Request(f"{endpoint}/new?about:blank", data=b"", method="PUT")
    try:
        with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            target = json.loads(response.read())
    except (OSError, urllib.error.URLError, json.JSONDecodeError) as error:
        raise CaptureError("chrome", "could not create a Chrome DevTools page") from error
    return target.get("webSocketDebuggerUrl") if isinstance(target, dict) and target.get("type") == "page" and isinstance(target.get("webSocketDebuggerUrl"), str) else None


def _devtools_page(debug_port: int) -> _DevToolsConnection:
    deadline = time.monotonic() + STARTUP_TIMEOUT_SECONDS
    endpoint = f"http://127.0.0.1:{debug_port}/json"
    while time.monotonic() < deadline:
        try:
            targets = _devtools_targets(endpoint)
        except CaptureError:
            time.sleep(0.1)
            continue
        break
    else:
        raise CaptureError("chrome", "timed out waiting for Chrome DevTools")
    websocket_url = page_websocket_url(targets) or _create_devtools_page(endpoint)
    if websocket_url is None:
        raise CaptureError("chrome", "Chrome did not expose a page DevTools target")
    return _DevToolsConnection(websocket_url)


def _evaluate(connection: _DevToolsConnection, expression: str) -> Any:
    result = connection.call("Runtime.evaluate", expression=expression, awaitPromise=True, returnByValue=True)
    value = result.get("result")
    if not isinstance(value, dict) or value.get("type") == "undefined":
        raise CaptureError("devtools", "page evaluation returned no value")
    return value.get("value")


def _wait_for_capture_ready(
    connection: _DevToolsConnection, *, expected_region_count: int, board_id: str
) -> None:
    deadline = time.monotonic() + READINESS_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        if capture_is_ready(_evaluate(connection, _readiness_expression()), expected_region_count=expected_region_count):
            return
        time.sleep(0.1)
    raise CaptureError("readiness", "timed out waiting for primary image and SVG regions", board_id=board_id)


def _wait_for_catalog_controls(connection: _DevToolsConnection, *, expected_count: int) -> None:
    deadline = time.monotonic() + READINESS_TIMEOUT_SECONDS
    expression = "({ boardButtonCount: document.querySelectorAll('#board-list button').length })"
    while time.monotonic() < deadline:
        if catalog_controls_are_ready(_evaluate(connection, expression), expected_count=expected_count):
            return
        time.sleep(0.1)
    raise CaptureError("readiness", "timed out waiting for Workbench catalog controls")


def _canvas_clip(connection: _DevToolsConnection) -> dict[str, float]:
    value = _evaluate(
        connection,
        """(() => {
          const canvas = document.getElementById('editor-svg');
          canvas?.scrollIntoView({ block: 'center', inline: 'center' });
          const rect = canvas?.getBoundingClientRect();
          return rect && rect.width > 0 && rect.height > 0
            ? { x: rect.x, y: rect.y, width: rect.width, height: rect.height, scale: 1 }
            : null;
        })()""",
    )
    if not isinstance(value, dict) or not all(isinstance(value.get(key), (int, float)) for key in ("x", "y", "width", "height")):
        raise CaptureError("capture", "editor SVG has no visible bounds")
    return {key: float(value[key]) for key in ("x", "y", "width", "height")} | {"scale": 1.0}


def _write_labeled_capture(raw_png: bytes, output_path: Path, label: str) -> None:
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError as error:
        raise CaptureError("output", "Pillow is required to label captures") from error
    from io import BytesIO

    with Image.open(BytesIO(raw_png)) as source:
        image = source.convert("RGB")
    labeled = Image.new("RGB", (image.width, image.height + LABEL_HEIGHT), "#171916")
    labeled.paste(image, (0, LABEL_HEIGHT))
    ImageDraw.Draw(labeled).text((10, 9), label, fill="#f3f0e8", font=ImageFont.load_default())
    labeled.save(output_path)


def create_contact_sheet(output_root: Path, manifest: CaptureManifest) -> Path:
    """Tile every manifest capture and record the exact inventory in PNG metadata."""
    try:
        from PIL import Image, ImageDraw, ImageFont, PngImagePlugin
    except ImportError as error:
        raise CaptureError("output", "Pillow is required to build the contact sheet") from error
    if not manifest.entries:
        raise CaptureError("output", "cannot create a contact sheet for an empty catalog")
    images = []
    for entry in manifest.entries:
        path = output_root / entry.filename
        if not path.is_file():
            raise CaptureError("output", f"capture is missing: {entry.filename}", board_id=entry.board_id)
        with Image.open(path) as image:
            images.append(image.convert("RGB"))
    tile_width = max(image.width for image in images)
    tile_height = max(image.height for image in images)
    rows = (len(images) + CONTACT_SHEET_COLUMNS - 1) // CONTACT_SHEET_COLUMNS
    sheet = Image.new("RGB", (tile_width * CONTACT_SHEET_COLUMNS, tile_height * rows), "#121311")
    for index, image in enumerate(images):
        x = (index % CONTACT_SHEET_COLUMNS) * tile_width
        y = (index // CONTACT_SHEET_COLUMNS) * tile_height
        sheet.paste(image, (x, y))
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default()
    for index, entry in enumerate(manifest.entries):
        x = (index % CONTACT_SHEET_COLUMNS) * tile_width + 10
        y = (index // CONTACT_SHEET_COLUMNS) * tile_height + 9
        draw.text((x, y), entry.board_id, fill="#f3f0e8", font=font)
    output = output_root / "contact-sheet.png"
    metadata = PngImagePlugin.PngInfo()
    metadata.add_text("hang-ten-catalog-board-ids", json.dumps([entry.board_id for entry in manifest.entries]))
    sheet.save(output, pnginfo=metadata)
    return output


def contact_sheet_entries(path: Path) -> tuple[str, ...]:
    """Read the inventory recorded in a generated contact sheet (test/audit helper)."""
    try:
        from PIL import Image
    except ImportError as error:
        raise CaptureError("output", "Pillow is required to inspect the contact sheet") from error
    with Image.open(path) as image:
        value = image.info.get("hang-ten-catalog-board-ids")
    try:
        entries = json.loads(value)
    except (TypeError, json.JSONDecodeError) as error:
        raise CaptureError("output", "contact sheet has no catalog inventory") from error
    if not isinstance(entries, list) or not all(isinstance(entry, str) for entry in entries):
        raise CaptureError("output", "contact sheet has an invalid catalog inventory")
    return tuple(entries)


def capture_catalog(
    repository_root: Path, output_root: Path, chrome_path: Path, port: int
) -> CaptureManifest:
    """Capture all completed boards in API order through one Chrome DevTools page."""
    repository_root = Path(repository_root).resolve()
    output_root = Path(output_root).resolve()
    chrome_path = Path(chrome_path).resolve()
    if not repository_root.is_dir() or not (repository_root / "Hangboards").is_dir():
        raise CaptureError("setup", "repository root must contain Hangboards/")
    if not chrome_path.is_file():
        raise CaptureError("setup", "Chrome executable is unavailable")
    if not 1 <= port <= 65535:
        raise CaptureError("setup", "port must be between 1 and 65535")
    output_root.mkdir(parents=True, exist_ok=True)
    base_url = f"http://127.0.0.1:{port}"
    debug_port = _available_port()
    server_path = repository_root / "Tools" / "HangboardWorkbench" / "server.py"
    with tempfile.TemporaryDirectory(prefix="hang-ten-capture-") as profile:
        with _managed_process(
            ["python3", str(server_path), "--repository-root", str(repository_root), "--port", str(port)],
            stage="server",
        ) as server_process:
            _wait_for_server(base_url, server_process)
            with _managed_process(
                [
                    str(chrome_path),
                    "--headless=new",
                    "--disable-gpu",
                    "--hide-scrollbars",
                    f"--remote-debugging-port={debug_port}",
                    f"--user-data-dir={profile}",
                    f"--window-size={VIEWPORT_WIDTH},{VIEWPORT_HEIGHT}",
                    "about:blank",
                ],
                stage="chrome",
            ) as chrome_process:
                connection = _devtools_page(debug_port)
                try:
                    connection.call("Page.enable")
                    connection.call("Runtime.enable")
                    connection.call(
                        "Emulation.setDeviceMetricsOverride",
                        width=VIEWPORT_WIDTH,
                        height=VIEWPORT_HEIGHT,
                        deviceScaleFactor=1,
                        mobile=False,
                    )
                    connection.call("Page.navigate", url=base_url)
                    catalog = fetch_catalog(base_url)
                    _wait_for_catalog_controls(connection, expected_count=len(catalog))
                    entries: list[CaptureEntry] = []
                    for index, board in enumerate(catalog):
                        regions = _board_region_count(base_url, board.board_id)
                        _evaluate(
                            connection,
                            f"(() => {{ document.querySelectorAll('#board-list button')[{index}].click(); return true; }})()",
                        )
                        _wait_for_capture_ready(
                            connection, expected_region_count=regions, board_id=board.board_id
                        )
                        screenshot = connection.call(
                            "Page.captureScreenshot", format="png", clip=_canvas_clip(connection)
                        ).get("data")
                        if not isinstance(screenshot, str):
                            raise CaptureError("capture", "Chrome returned no PNG data", board_id=board.board_id)
                        filename = capture_filename(board.board_id)
                        _write_labeled_capture(
                            base64.b64decode(screenshot), output_root / filename,
                            f"{board.board_id} — {board.display_name}",
                        )
                        entries.append(CaptureEntry(board.board_id, board.display_name, regions, filename))
                    manifest = CaptureManifest(tuple(entries))
                    manifest.write(output_root)
                    create_contact_sheet(output_root, manifest)
                    return manifest
                finally:
                    connection.close()
                    if chrome_process.poll() is not None:
                        raise CaptureError("chrome", "Chrome exited during catalog capture")


def argument_parser() -> ArgumentParser:
    parser = ArgumentParser(description="Capture completed boards through Hangboard Workbench")
    parser.add_argument("--repository-root", type=Path, required=True, help="Checkout containing Hangboards/")
    parser.add_argument("--output-root", type=Path, required=True, help="Directory for labeled PNG evidence")
    parser.add_argument("--chrome-path", type=Path, required=True, help="Google Chrome executable")
    parser.add_argument("--port", type=int, default=4173, help="Loopback Workbench server port (default: 4173)")
    return parser


def main() -> None:
    arguments = argument_parser().parse_args()
    manifest = capture_catalog(
        arguments.repository_root, arguments.output_root, arguments.chrome_path, arguments.port
    )
    print(json.dumps({"boards": len(manifest.entries), "output": str(arguments.output_root)}, sort_keys=True))


__all__ = [
    "CaptureEntry",
    "CaptureError",
    "CaptureManifest",
    "CatalogBoard",
    "capture_catalog",
    "capture_filename",
    "capture_is_ready",
    "catalog_controls_are_ready",
    "contact_sheet_entries",
    "create_contact_sheet",
    "fetch_catalog",
    "argument_parser",
    "page_websocket_url",
]


if __name__ == "__main__":
    main()
