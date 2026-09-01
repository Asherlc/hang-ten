#!/usr/bin/env python3
"""Capture the completed Hangboard Workbench catalog through its editor surface."""

from __future__ import annotations

import base64
import hashlib
import json
import os
import secrets
import signal
import socket
import struct
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from argparse import ArgumentParser
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable, Iterator


STARTUP_TIMEOUT_SECONDS = 15
READINESS_TIMEOUT_SECONDS = 20
REQUEST_TIMEOUT_SECONDS = 3
VIEWPORT_WIDTH = 1600
VIEWPORT_HEIGHT = 1200
LABEL_HEIGHT = 34
CONTACT_SHEET_COLUMNS = 3


class CaptureError(RuntimeError):
    """A structured failure from a named catalog capture stage."""

    def __init__(
        self,
        stage: str,
        message: str,
        *,
        board_id: str | None = None,
        presentation_id: str | None = None,
    ) -> None:
        self.stage = stage
        self.board_id = board_id
        self.presentation_id = presentation_id
        subject = f" {board_id}" if board_id else ""
        if presentation_id:
            subject += f"/{presentation_id}"
        super().__init__(f"{stage}{subject}: {message}")


class CaptureInterrupted(KeyboardInterrupt):
    """A termination signal converted into normal context-manager unwinding."""

    def __init__(self, signum: int) -> None:
        self.signum = signum
        super().__init__(f"catalog capture interrupted by signal {signum}")


@dataclass(frozen=True)
class CatalogBoard:
    board_id: str
    display_name: str


@dataclass(frozen=True)
class PresentationCaptureTarget:
    board_id: str
    display_name: str
    presentation_id: str
    presentation_name: str
    image_url: str
    region_keys: tuple[str, ...]
    is_default: bool


@dataclass(frozen=True)
class RegionBounds:
    """One rendered editor-region bounding box paired with its API hold identity."""

    region_key: str
    hold_id: str | None
    x: float
    y: float
    width: float
    height: float


@dataclass(frozen=True)
class HoldIDLabel:
    hold_id: str
    x: float
    y: float


@dataclass(frozen=True)
class CaptureEntry:
    board_id: str
    display_name: str
    presentation_id: str
    presentation_name: str
    region_count: int
    filename: str
    variant: str = "normal"

    @property
    def capture_id(self) -> str:
        return capture_identity(self.board_id, self.presentation_id)


@dataclass(frozen=True)
class CaptureManifest:
    entries: tuple[CaptureEntry, ...]

    def write(self, output_root: Path) -> Path:
        path = output_root / "manifest.json"
        path.write_text(
            json.dumps(
                {
                    "boards": [
                        {"capture_id": entry.capture_id, **asdict(entry)}
                        for entry in self.entries
                    ]
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        return path


def _safe_stem(identifier: str, *, subject: str, board_id: str) -> str:
    normalized = "".join(
        character.lower() if character.isalnum() or character in ".-" else "-"
        for character in identifier.strip()
    ).strip(".-")
    normalized = "-".join(piece for piece in normalized.split("-") if piece)
    if not normalized:
        raise CaptureError("catalog", f"{subject} cannot produce a safe filename", board_id=board_id)
    return normalized


def capture_filename(board_id: str, presentation_id: str | None = None) -> str:
    """Return a traversal-safe PNG name for a board or board/presentation pair."""
    board_stem = _safe_stem(board_id, subject="board ID", board_id=board_id)
    identity = board_id
    stem = board_stem
    if presentation_id is not None:
        presentation_stem = _safe_stem(
            presentation_id,
            subject="presentation ID",
            board_id=board_id,
        )
        identity = f"{board_id}\0{presentation_id}"
        stem = f"{board_stem}--{presentation_stem}"
    digest = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:12]
    return f"{stem}--{digest}.png"


def capture_identity(board_id: str, presentation_id: str) -> str:
    """Return the stable package/presentation identity used by review evidence."""
    return f"{board_id}::{presentation_id}"


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


def _absolute_url(base_url: str, url: str) -> str:
    resolved = urllib.parse.urlsplit(urllib.parse.urljoin(base_url, url))
    return urllib.parse.urlunsplit(
        (
            resolved.scheme,
            resolved.netloc,
            urllib.parse.quote(resolved.path, safe="/%"),
            resolved.query,
            resolved.fragment,
        )
    )


def _board_payload(
    base_url: str,
    board_id: str,
    presentation_id: str | None = None,
) -> dict[str, Any]:
    encoded_id = urllib.parse.quote(board_id, safe="")
    query = (
        f"?{urllib.parse.urlencode({'presentationID': presentation_id})}"
        if presentation_id is not None
        else ""
    )
    payload = _request_json(f"{base_url}/api/boards/{encoded_id}{query}")
    board = payload.get("board")
    if payload.get("ok") is not True or not isinstance(board, dict):
        raise CaptureError("board", "Workbench returned an invalid board document", board_id=board_id)
    return board


def _capture_target_from_payload(
    base_url: str,
    catalog_board: CatalogBoard,
    presentation: dict[str, Any],
    board: dict[str, Any],
) -> PresentationCaptureTarget:
    presentation_id = presentation.get("presentationID")
    presentation_name = presentation.get("displayName")
    is_default = presentation.get("default")
    selected_presentation_id = board.get("selectedPresentationID")
    document = board.get("document")
    image_url = board.get("imageUrl")
    if (
        not isinstance(presentation_id, str)
        or not presentation_id
        or not isinstance(presentation_name, str)
        or not presentation_name
        or not isinstance(is_default, bool)
    ):
        raise CaptureError("board", "Workbench returned an invalid presentation", board_id=catalog_board.board_id)
    if selected_presentation_id != presentation_id or not isinstance(document, dict):
        raise CaptureError(
            "board",
            "Workbench returned a mismatched presentation document",
            board_id=catalog_board.board_id,
            presentation_id=presentation_id,
        )
    if document.get("presentationID") != presentation_id:
        raise CaptureError(
            "board",
            "editor geometry does not match the selected presentation",
            board_id=catalog_board.board_id,
            presentation_id=presentation_id,
        )
    if not isinstance(image_url, str) or not image_url:
        raise CaptureError(
            "board",
            "board document is missing its selected presentation image",
            board_id=catalog_board.board_id,
            presentation_id=presentation_id,
        )
    regions = document.get("regions")
    if not isinstance(regions, list):
        raise CaptureError(
            "board",
            "board document is missing regions",
            board_id=catalog_board.board_id,
            presentation_id=presentation_id,
        )
    region_keys = tuple(
        region.get("key") if isinstance(region, dict) else None
        for region in regions
    )
    if not all(isinstance(key, str) and key for key in region_keys) or len(set(region_keys)) != len(region_keys):
        raise CaptureError(
            "board",
            "board document has invalid region keys",
            board_id=catalog_board.board_id,
            presentation_id=presentation_id,
        )
    return PresentationCaptureTarget(
        board_id=catalog_board.board_id,
        display_name=catalog_board.display_name,
        presentation_id=presentation_id,
        presentation_name=presentation_name,
        image_url=_absolute_url(base_url, image_url),
        region_keys=region_keys,
        is_default=is_default,
    )


def fetch_capture_targets(
    base_url: str,
    board: CatalogBoard,
) -> tuple[PresentationCaptureTarget, ...]:
    """Enumerate every API-declared presentation with its scoped capture truth."""
    initial = _board_payload(base_url, board.board_id)
    presentations = initial.get("presentations")
    if not isinstance(presentations, list) or not presentations:
        raise CaptureError("board", "board document is missing presentations", board_id=board.board_id)
    selected_id = initial.get("selectedPresentationID")
    targets: list[PresentationCaptureTarget] = []
    for presentation in presentations:
        if not isinstance(presentation, dict):
            raise CaptureError("board", "Workbench returned an invalid presentation", board_id=board.board_id)
        presentation_id = presentation.get("presentationID")
        selected = (
            initial
            if presentation_id == selected_id
            else _board_payload(base_url, board.board_id, presentation_id)
            if isinstance(presentation_id, str)
            else initial
        )
        targets.append(_capture_target_from_payload(base_url, board, presentation, selected))
    if sum(target.is_default for target in targets) != 1:
        raise CaptureError("board", "board must have exactly one default presentation", board_id=board.board_id)
    if len({target.presentation_id for target in targets}) != len(targets):
        raise CaptureError("board", "board has duplicate presentation IDs", board_id=board.board_id)
    return tuple(targets)


def capture_targets_for_run(
    targets: tuple[PresentationCaptureTarget, ...],
    *,
    all_presentations: bool,
) -> tuple[PresentationCaptureTarget, ...]:
    """Retain legacy default-only capture unless complete enumeration is requested."""
    if all_presentations:
        return targets
    return tuple(target for target in targets if target.is_default)


def _board_document(base_url: str, board_id: str, presentation_id: str) -> dict[str, Any]:
    board = _board_payload(base_url, board_id, presentation_id)
    document = board.get("document")
    if not isinstance(document, dict) or document.get("presentationID") != presentation_id:
        raise CaptureError("board", "Workbench returned an invalid board document", board_id=board_id)
    return document


def hold_id_label_positions(regions: tuple[RegionBounds, ...]) -> tuple[HoldIDLabel, ...]:
    """Place one review label at the union center of every logical editor hold."""
    bounds_by_hold: dict[str, tuple[float, float, float, float]] = {}
    for region in regions:
        if not isinstance(region.hold_id, str) or not region.hold_id:
            raise CaptureError("capture", f"region {region.region_key} is missing metadata.holdID")
        minimum_x, minimum_y = region.x, region.y
        maximum_x, maximum_y = region.x + region.width, region.y + region.height
        existing = bounds_by_hold.get(region.hold_id)
        if existing is None:
            bounds_by_hold[region.hold_id] = (minimum_x, minimum_y, maximum_x, maximum_y)
        else:
            bounds_by_hold[region.hold_id] = (
                min(existing[0], minimum_x),
                min(existing[1], minimum_y),
                max(existing[2], maximum_x),
                max(existing[3], maximum_y),
            )
    return tuple(
        HoldIDLabel(hold_id, (bounds[0] + bounds[2]) / 2, (bounds[1] + bounds[3]) / 2)
        for hold_id, bounds in bounds_by_hold.items()
    )


def capture_is_ready(
    value: object,
    *,
    expected_image_url: str,
    expected_presentation_id: str,
    expected_region_keys: tuple[str, ...],
) -> bool:
    """Validate the exact selected asset and presentation-scoped geometry signal."""
    return (
        isinstance(value, dict)
        and value.get("primaryImageLoaded") is True
        and value.get("imageURL") == expected_image_url
        and value.get("presentationID") == expected_presentation_id
        and value.get("regionKeys") == list(expected_region_keys)
    )


def catalog_controls_are_ready(value: object, *, expected_count: int) -> bool:
    return isinstance(value, dict) and value.get("boardButtonCount") == expected_count


def _readiness_expression(expected_image_url: str) -> str:
    return f"""
      (async () => {{
        const expectedImageURL = {json.dumps(expected_image_url)};
        const image = document.getElementById('board-image');
        const href = image?.href?.baseVal || image?.getAttribute('href');
        const absoluteURL = href ? new URL(href, document.baseURI).href : null;
        let primaryImageLoaded = false;
        if (absoluteURL === expectedImageURL && image?.getBoundingClientRect().width > 0) {{
          const controller = new AbortController();
          const timeout = setTimeout(() => controller.abort(), 2000);
          try {{
            primaryImageLoaded = (await fetch(absoluteURL, {{
              cache: 'no-store',
              signal: controller.signal,
            }})).ok;
          }} catch (_) {{
          }} finally {{
            clearTimeout(timeout);
          }}
        }}
        return {{
          primaryImageLoaded,
          imageURL: absoluteURL,
          presentationID: absoluteURL
            ? new URL(absoluteURL).searchParams.get('presentationID')
            : null,
          regionKeys: [...document.querySelectorAll('#hold-overlay path.region-shape')]
            .map((path) => path.dataset.holdKey),
        }};
      }})()
    """


@contextmanager
def _managed_process(
    command: list[str],
    *,
    stage: str,
    owner: str | None = None,
    resource_recorder: Callable[[dict[str, object]], None] | None = None,
) -> Iterator[subprocess.Popen[str]]:
    try:
        process = subprocess.Popen(
            command,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            text=True,
            start_new_session=True,
        )
    except OSError as error:
        raise CaptureError(stage, f"could not start {command[0]}") from error
    if owner is not None and resource_recorder is not None:
        resource_recorder(
            {
                "owner": owner,
                "resource": f"{stage}-process-group",
                "pid": process.pid,
                "state": "created",
            }
        )
    try:
        yield process
    finally:
        if process.poll() is None:
            os.killpg(process.pid, signal.SIGTERM)
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait(timeout=5)
        if owner is not None and resource_recorder is not None:
            resource_recorder(
                {
                    "owner": owner,
                    "resource": f"{stage}-process-group",
                    "pid": process.pid,
                    "state": "verified-terminated",
                }
            )


@contextmanager
def _capture_signal_handlers() -> Iterator[None]:
    """Turn termination signals into exceptions so owned resources unwind."""
    watched = (signal.SIGINT, signal.SIGTERM)
    previous = {signum: signal.getsignal(signum) for signum in watched}

    def interrupt(signum: int, _frame: object) -> None:
        raise CaptureInterrupted(signum)

    for signum in watched:
        signal.signal(signum, interrupt)
    try:
        yield
    finally:
        for signum, handler in previous.items():
            signal.signal(signum, handler)


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
    connection: _DevToolsConnection,
    *,
    target: PresentationCaptureTarget,
) -> None:
    deadline = time.monotonic() + READINESS_TIMEOUT_SECONDS
    last_observed: object = None
    while time.monotonic() < deadline:
        last_observed = _evaluate(connection, _readiness_expression(target.image_url))
        if capture_is_ready(
            last_observed,
            expected_image_url=target.image_url,
            expected_presentation_id=target.presentation_id,
            expected_region_keys=target.region_keys,
        ):
            return
        time.sleep(0.1)
    raise CaptureError(
        "readiness",
        "timed out waiting for selected presentation image and SVG regions; "
        f"last observed {json.dumps(last_observed, sort_keys=True)}",
        board_id=target.board_id,
        presentation_id=target.presentation_id,
    )


def _select_board(
    connection: _DevToolsConnection,
    *,
    index: int,
    board_id: str,
) -> None:
    deadline = time.monotonic() + READINESS_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        selected = _evaluate(
            connection,
            f"""(() => {{
              const button = document.querySelectorAll('#board-list button')[{index}];
              if (!(button instanceof HTMLButtonElement) || button.disabled) return false;
              button.click();
              return true;
            }})()""",
        )
        if selected is True:
            return
        time.sleep(0.1)
    raise CaptureError(
        "selection",
        "timed out waiting for the catalog control to become enabled",
        board_id=board_id,
    )


def _select_presentation(
    connection: _DevToolsConnection,
    *,
    board_id: str,
    presentation_id: str,
) -> None:
    selected = _evaluate(
        connection,
        f"""(() => {{
          const select = document.getElementById('presentation-select');
          if (!(select instanceof HTMLSelectElement)) return false;
          select.value = {json.dumps(presentation_id)};
          select.dispatchEvent(new Event('change', {{ bubbles: true }}));
          return true;
        }})()""",
    )
    if selected is not True:
        raise CaptureError(
            "capture",
            "presentation selector is unavailable",
            board_id=board_id,
            presentation_id=presentation_id,
        )


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


def _rendered_region_bounds(
    connection: _DevToolsConnection, document: dict[str, Any], *, board_id: str
) -> tuple[RegionBounds, ...]:
    regions = document.get("regions")
    if not isinstance(regions, list):
        raise CaptureError("board", "board document is missing regions", board_id=board_id)
    value = _evaluate(
        connection,
        f"""(() => {{
          const apiRegions = {json.dumps(regions)};
          const paths = [...document.querySelectorAll('#hold-overlay path.region-shape')];
          return apiRegions.map((region) => {{
            const path = paths.find((candidate) => candidate.dataset.holdKey === region.key);
            if (!path) return {{ regionKey: region.key, missingPath: true }};
            const bounds = path.getBBox();
            return {{
              regionKey: region.key,
              holdID: region.metadata?.holdID,
              x: bounds.x,
              y: bounds.y,
              width: bounds.width,
              height: bounds.height,
            }};
          }});
        }})()""",
    )
    if not isinstance(value, list):
        raise CaptureError("capture", "page returned invalid rendered region bounds", board_id=board_id)
    result: list[RegionBounds] = []
    for region in value:
        if not isinstance(region, dict):
            raise CaptureError("capture", "page returned invalid rendered region bounds", board_id=board_id)
        region_key = region.get("regionKey")
        if region.get("missingPath") is True or not isinstance(region_key, str):
            raise CaptureError("capture", "editor is missing a rendered region path", board_id=board_id)
        bounds = tuple(region.get(key) for key in ("x", "y", "width", "height"))
        if not all(isinstance(item, (int, float)) for item in bounds):
            raise CaptureError("capture", f"region {region_key} has invalid rendered bounds", board_id=board_id)
        x, y, width, height = bounds
        result.append(RegionBounds(region_key, region.get("holdID"), float(x), float(y), float(width), float(height)))
    return tuple(result)


def _inject_hold_id_labels(
    connection: _DevToolsConnection, labels: tuple[HoldIDLabel, ...]
) -> None:
    value = _evaluate(
        connection,
        f"""(() => {{
          const svg = document.getElementById('editor-svg');
          if (!(svg instanceof SVGSVGElement)) return false;
          for (const label of {json.dumps([asdict(label) for label in labels])}) {{
            const text = document.createElementNS('http://www.w3.org/2000/svg', 'text');
            text.setAttribute('data-audit-hold-id', label.hold_id);
            text.setAttribute('x', String(label.x));
            text.setAttribute('y', String(label.y));
            text.setAttribute('text-anchor', 'middle');
            text.setAttribute('dominant-baseline', 'middle');
            text.setAttribute('font-size', '14');
            text.setAttribute('font-weight', '700');
            text.setAttribute('fill', '#ffffff');
            text.setAttribute('stroke', '#111111');
            text.setAttribute('stroke-width', '3.5');
            text.setAttribute('paint-order', 'stroke');
            text.setAttribute('pointer-events', 'none');
            text.setAttribute('aria-hidden', 'true');
            text.textContent = label.hold_id;
            svg.appendChild(text);
          }}
          return true;
        }})()""",
    )
    if value is not True:
        raise CaptureError("capture", "editor SVG is unavailable for hold ID labels")


def _remove_hold_id_labels(connection: _DevToolsConnection) -> None:
    value = _evaluate(
        connection,
        """(() => {
          document.querySelectorAll('#editor-svg text[data-audit-hold-id]').forEach((label) => label.remove());
          return true;
        })()""",
    )
    if value is not True:
        raise CaptureError("capture", "editor SVG is unavailable while removing hold ID labels")


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
        draw.text(
            (x, y),
            f"{entry.board_id} / {entry.presentation_id}",
            fill="#f3f0e8",
            font=font,
        )
    output = output_root / "contact-sheet.png"
    metadata = PngImagePlugin.PngInfo()
    metadata.add_text(
        "hang-ten-catalog-presentations",
        json.dumps(
            [
                {"boardID": entry.board_id, "presentationID": entry.presentation_id}
                for entry in manifest.entries
            ]
        ),
    )
    sheet.save(output, pnginfo=metadata)
    return output


def contact_sheet_entries(path: Path) -> tuple[tuple[str, str], ...]:
    """Read the inventory recorded in a generated contact sheet (test/audit helper)."""
    try:
        from PIL import Image
    except ImportError as error:
        raise CaptureError("output", "Pillow is required to inspect the contact sheet") from error
    with Image.open(path) as image:
        value = image.info.get("hang-ten-catalog-presentations")
    try:
        entries = json.loads(value)
    except (TypeError, json.JSONDecodeError) as error:
        raise CaptureError("output", "contact sheet has no catalog inventory") from error
    if not isinstance(entries, list) or not all(
        isinstance(entry, dict)
        and isinstance(entry.get("boardID"), str)
        and isinstance(entry.get("presentationID"), str)
        for entry in entries
    ):
        raise CaptureError("output", "contact sheet has an invalid catalog inventory")
    return tuple((entry["boardID"], entry["presentationID"]) for entry in entries)


def _capture_server_command(repository_root: Path, port: int) -> list[str]:
    """Launch the capture-only local backend, never the hosted server CLI."""
    return [
        "python3",
        str(repository_root / "Tools" / "HangboardWorkbench" / "capture_server.py"),
        "--repository-root",
        str(repository_root),
        "--port",
        str(port),
    ]


def capture_catalog(
    repository_root: Path,
    output_root: Path,
    chrome_path: Path,
    port: int,
    *,
    hold_id_labels: bool = False,
    all_presentations: bool = False,
) -> CaptureManifest:
    """Capture all completed boards in API order through one Chrome DevTools page."""
    repository_root = Path(repository_root).resolve()
    output_root = Path(output_root).resolve()
    chrome_path = Path(chrome_path).resolve()
    if not repository_root.is_dir() or not (repository_root / "Hangboards").is_dir():
        raise CaptureError("setup", "repository root must contain Hangboards/")
    if not (repository_root / "Tools" / "HangboardWorkbench" / "app.js").is_file():
        raise CaptureError(
            "setup",
            "Workbench UI bundle is missing; run npm ci and npm run check:bundle "
            "in Tools/HangboardWorkbench",
        )
    if not chrome_path.is_file():
        raise CaptureError("setup", "Chrome executable is unavailable")
    if not 1 <= port <= 65535:
        raise CaptureError("setup", "port must be between 1 and 65535")
    output_root.mkdir(parents=True, exist_ok=True)
    context_root = repository_root / ".context"
    context_root.mkdir(parents=True, exist_ok=True)
    base_url = f"http://127.0.0.1:{port}"
    debug_port = _available_port()

    def record_resource(event: dict[str, object]) -> None:
        print(
            json.dumps({"captureResource": event}, sort_keys=True),
            file=sys.stderr,
            flush=True,
        )

    with tempfile.TemporaryDirectory(
        prefix=f"{repository_root.name}-chrome-",
        dir=context_root,
    ) as profile:
        with _managed_process(
            _capture_server_command(repository_root, port),
            stage="server",
            owner=repository_root.name,
            resource_recorder=record_resource,
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
                owner=repository_root.name,
                resource_recorder=record_resource,
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
                        targets = capture_targets_for_run(
                            fetch_capture_targets(base_url, board),
                            all_presentations=all_presentations,
                        )
                        default_target = next(target for target in targets if target.is_default)
                        _select_board(connection, index=index, board_id=board.board_id)
                        _wait_for_capture_ready(
                            connection,
                            target=default_target,
                        )
                        selected_presentation_id = default_target.presentation_id
                        for target in targets:
                            if target.presentation_id != selected_presentation_id:
                                _select_presentation(
                                    connection,
                                    board_id=board.board_id,
                                    presentation_id=target.presentation_id,
                                )
                                _wait_for_capture_ready(connection, target=target)
                                selected_presentation_id = target.presentation_id
                            labels_injected = False
                            if hold_id_labels:
                                labels = hold_id_label_positions(
                                    _rendered_region_bounds(
                                        connection,
                                        _board_document(
                                            base_url,
                                            board.board_id,
                                            target.presentation_id,
                                        ),
                                        board_id=board.board_id,
                                    )
                                )
                                _inject_hold_id_labels(connection, labels)
                                labels_injected = True
                            try:
                                screenshot = connection.call(
                                    "Page.captureScreenshot", format="png", clip=_canvas_clip(connection)
                                ).get("data")
                            finally:
                                if labels_injected:
                                    _remove_hold_id_labels(connection)
                            if not isinstance(screenshot, str):
                                raise CaptureError(
                                    "capture",
                                    "Chrome returned no PNG data",
                                    board_id=board.board_id,
                                    presentation_id=target.presentation_id,
                                )
                            filename = capture_filename(board.board_id, target.presentation_id)
                            _write_labeled_capture(
                                base64.b64decode(screenshot),
                                output_root / filename,
                                f"{board.board_id} / {target.presentation_id} — "
                                f"{board.display_name} / {target.presentation_name}",
                            )
                            entries.append(
                                CaptureEntry(
                                    board.board_id,
                                    board.display_name,
                                    target.presentation_id,
                                    target.presentation_name,
                                    len(target.region_keys),
                                    filename,
                                    "hold-ids" if hold_id_labels else "normal",
                                )
                            )
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
    parser.add_argument(
        "--all-presentations",
        action="store_true",
        help="Capture every API-declared presentation instead of only each default",
    )
    parser.add_argument(
        "--hold-id-labels",
        action="store_true",
        help="Overlay one review-only stable hold ID label per logical hold",
    )
    return parser


def main() -> None:
    arguments = argument_parser().parse_args()
    with _capture_signal_handlers():
        manifest = capture_catalog(
            arguments.repository_root,
            arguments.output_root,
            arguments.chrome_path,
            arguments.port,
            hold_id_labels=arguments.hold_id_labels,
            all_presentations=arguments.all_presentations,
        )
    print(
        json.dumps(
            {
                "boards": len({entry.board_id for entry in manifest.entries}),
                "presentations": len(manifest.entries),
                "output": str(arguments.output_root),
            },
            sort_keys=True,
        )
    )


__all__ = [
    "CaptureEntry",
    "CaptureError",
    "CaptureInterrupted",
    "CaptureManifest",
    "CatalogBoard",
    "HoldIDLabel",
    "RegionBounds",
    "PresentationCaptureTarget",
    "capture_catalog",
    "capture_filename",
    "capture_identity",
    "capture_is_ready",
    "catalog_controls_are_ready",
    "contact_sheet_entries",
    "create_contact_sheet",
    "fetch_catalog",
    "fetch_capture_targets",
    "capture_targets_for_run",
    "hold_id_label_positions",
    "argument_parser",
    "page_websocket_url",
]


if __name__ == "__main__":
    main()
