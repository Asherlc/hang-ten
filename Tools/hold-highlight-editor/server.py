#!/usr/bin/env python3
"""Local filesystem boundary for the dependency-free hold-region editor."""

from __future__ import annotations

import json
import hashlib
import math
import mimetypes
import os
import re
import tempfile
from argparse import ArgumentParser
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import parse_qs, urlencode, urlsplit


MAX_REQUEST_BYTES = 10 * 1024 * 1024
EDITOR_ROOT = Path(__file__).resolve().parent
CUBIC_SEGMENTS = 12
HOLD_IDENTIFIER = re.compile(r"hold-(\d+)$")


class EditorError(ValueError):
    """A safe, user-facing editor session or payload error."""


@dataclass(frozen=True)
class EditorSession:
    run_dir: Path
    image_path: Path
    regions_path: Path
    catalog_outline_path: Path | None = None
    catalog_source_dir: Path | None = None
    catalog_outline_dir: Path | None = None


@dataclass(frozen=True)
class CatalogSession:
    id: str
    label: str
    session: EditorSession

    @property
    def run_name(self) -> str:
        if self.session.catalog_outline_path is not None:
            return self.session.catalog_outline_path.stem
        return self.session.run_dir.name


@dataclass(frozen=True)
class EditorCatalog:
    sessions: tuple[CatalogSession, ...]

    @classmethod
    def from_sessions(cls, sessions: Iterable[tuple[str, EditorSession]]) -> EditorCatalog:
        entries: list[CatalogSession] = []
        for index, (label, session) in enumerate(sessions, start=1):
            clean_label = str(label).strip()
            if not clean_label:
                raise EditorError("run label must not be empty")
            entries.append(CatalogSession(id=f"run-{index}", label=clean_label, session=session))
        if not entries:
            raise EditorError("catalog must contain at least one run")
        return cls(tuple(entries))

    def get(self, run_id: str | None) -> CatalogSession:
        if run_id is None:
            return self.sessions[0]
        for entry in self.sessions:
            if entry.id == run_id:
                return entry
        raise EditorError(f"unknown run: {run_id}")


def discover_session(run_dir: Path) -> EditorSession:
    root = Path(run_dir).expanduser().resolve()
    if not root.is_dir():
        raise EditorError(f"run directory does not exist: {root}")

    region_candidates = sorted(root.rglob("stage-2-regions.json"))
    if len(region_candidates) != 1:
        raise EditorError(
            "run directory must contain exactly one stage-2-regions.json "
            f"(found {len(region_candidates)})"
        )

    image_candidates = sorted(root.rglob("stage-1-auto-rgba.png"))
    if len(image_candidates) != 1:
        raise EditorError(
            "run directory must contain exactly one stage-1-auto-rgba.png "
            f"(found {len(image_candidates)})"
        )

    regions_path = _confined_file(root, region_candidates[0])
    image_path = _confined_file(root, image_candidates[0])
    return EditorSession(run_dir=root, image_path=image_path, regions_path=regions_path)


def load_catalog(catalog_path: Path) -> EditorCatalog:
    path = Path(catalog_path).expanduser().resolve()
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise EditorError(f"could not read catalog: {error}") from error
    if not isinstance(document, dict) or not isinstance(document.get("runs"), list):
        raise EditorError("catalog must be an object containing a runs array")

    sessions: list[tuple[str, EditorSession]] = []
    for index, entry in enumerate(document["runs"]):
        if not isinstance(entry, dict):
            raise EditorError(f"catalog runs[{index}] must be an object")
        label = entry.get("label")
        run_dir_value = entry.get("runDir")
        if not isinstance(label, str) or not label.strip():
            raise EditorError(f"catalog runs[{index}].label must be a non-empty string")
        if not isinstance(run_dir_value, str) or not run_dir_value.strip():
            raise EditorError(f"catalog runs[{index}].runDir must be a non-empty string")
        run_dir = Path(run_dir_value).expanduser()
        if not run_dir.is_absolute():
            run_dir = path.parent / run_dir
        root = run_dir.resolve()
        if not root.is_dir():
            raise EditorError(f"run directory does not exist: {root}")

        image_value = entry.get("image")
        regions_value = entry.get("regions")
        if image_value is None and regions_value is None:
            session = discover_session(root)
        elif isinstance(image_value, str) and isinstance(regions_value, str):
            image_path = _catalog_artifact(root, image_value, f"catalog runs[{index}].image")
            regions_path = _catalog_artifact(root, regions_value, f"catalog runs[{index}].regions")
            session = EditorSession(run_dir=root, image_path=image_path, regions_path=regions_path)
        else:
            raise EditorError(f"catalog runs[{index}] must provide both image and regions")
        sessions.append((label, session))
    return EditorCatalog.from_sessions(sessions)


def discover_catalog_outline_sessions(source_dir: Path, outline_dir: Path) -> list[CatalogSession]:
    source_root = _require_directory(source_dir, "catalog source directory")
    outline_root = _require_directory(outline_dir, "catalog outline directory")
    run_root = _common_parent(source_root, outline_root)
    sessions: list[CatalogSession] = []
    for outline_path in sorted(outline_root.glob("*.json")):
        image_path = source_root / f"{outline_path.stem}.png"
        if not image_path.is_file():
            raise EditorError(
                f"catalog outline {outline_path.name} has no matching PNG in the catalog source directory"
            )
        session = EditorSession(
            run_dir=run_root,
            image_path=_confined_file(source_root, image_path),
            regions_path=_confined_file(outline_root, outline_path),
            catalog_outline_path=_confined_file(outline_root, outline_path),
            catalog_source_dir=source_root,
            catalog_outline_dir=outline_root,
        )
        sessions.append(CatalogSession(id=f"catalog-{outline_path.stem}", label=outline_path.stem, session=session))
    if not sessions:
        raise EditorError("catalog outline directory must contain at least one JSON outline")
    return sessions


def catalog_from_inputs(
    run_dirs: Iterable[Path],
    catalog_path: Path | None,
    catalog_source_dir: Path | None = None,
    catalog_outline_dir: Path | None = None,
) -> EditorCatalog:
    sessions: list[tuple[str, EditorSession]] = []
    if catalog_path is not None:
        sessions.extend((entry.label, entry.session) for entry in load_catalog(catalog_path).sessions)
    if (catalog_source_dir is None) != (catalog_outline_dir is None):
        raise EditorError("--catalog-source-dir and --catalog-outline-dir must be supplied together")
    if catalog_source_dir is not None and catalog_outline_dir is not None:
        sessions.extend(
            (entry.label, entry.session)
            for entry in discover_catalog_outline_sessions(catalog_source_dir, catalog_outline_dir)
        )
    for run_dir in run_dirs:
        session = discover_session(run_dir)
        sessions.append((session.run_dir.name, session))
    return EditorCatalog.from_sessions(sessions)


def catalog_regions_document(session: EditorSession) -> dict[str, Any]:
    document = _load_catalog_outline(session)
    canvas = document["canvas"]
    outlines = document["outlines"]
    editor_ids = _editor_ids_for_outlines(outlines)
    regions = []
    for outline in outlines:
        source_id = outline["id"]
        outline_type = outline.get("kind", "edge")
        editor_type = outline_type
        regions.append(
            {
                "id": editor_ids[source_id],
                "key": source_id,
                "type": editor_type,
                "contour": [
                    [point[0] * canvas["width"], point[1] * canvas["height"]]
                    for point in _flatten_outline(outline["path"].get("commands", []))
                ],
                "metadata": {
                    "sourceRegionId": source_id,
                    "mode": "aperture" if outline_type == "pocket" else "surface",
                    "shapeKind": "freeform",
                    "pathStyle": "straight",
                    "curveTension": 0.8,
                },
            }
        )
    return {"canvas": deepcopy(canvas), "regions": regions}


def save_catalog_outline(session: EditorSession, regions: object) -> dict[str, str]:
    region_document = validate_regions_document(regions)
    source_document = _load_catalog_outline(session)
    outlines = source_document["outlines"]
    existing_by_id = {outline["id"]: outline for outline in outlines}
    editor_ids = _editor_ids_for_outlines(outlines)
    source_by_editor_id = {editor_id: source_id for source_id, editor_id in editor_ids.items()}
    incoming_ids: set[str] = set()
    updated_outlines: list[dict[str, Any]] = []
    next_hold_number = _next_hold_number(existing_by_id)

    for region in region_document["regions"]:
        source_id = region.get("metadata", {}).get("sourceRegionId")
        if not isinstance(source_id, str) or source_id not in existing_by_id:
            source_id = source_by_editor_id.get(region["id"])
        if not isinstance(source_id, str) or source_id not in existing_by_id:
            key = region.get("key")
            source_id = key if isinstance(key, str) and key in existing_by_id else None

        if source_id is None:
            source_id = _next_hold_id(existing_by_id, next_hold_number)
            next_hold_number = int(source_id.removeprefix("hold-")) + 1
            outline = _new_catalog_outline(region, source_id)
            existing_by_id[source_id] = outline
        else:
            if source_id in incoming_ids:
                raise EditorError(f"catalog region {source_id} appears more than once")
            outline = deepcopy(existing_by_id[source_id])
        incoming_ids.add(source_id)
        outline["path"] = _closed_line_path(region_document["canvas"], region["contour"])
        outline["bounds"] = _normalized_bounds(region_document["canvas"], region["contour"])
        updated_outlines.append(outline)

    source_document["outlines"] = updated_outlines
    outline_dir = session.catalog_outline_dir or session.regions_path.parent
    outline_path = _confined_file(outline_dir, session.catalog_outline_path or session.regions_path)
    _atomic_write_json(outline_path, source_document)
    return {
        "catalogPath": str(outline_path.relative_to(outline_dir)),
        "savedAt": datetime.now(timezone.utc).isoformat(),
    }


def validate_regions_document(value: object) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise EditorError("regions document must be a JSON object")
    canvas = value.get("canvas")
    if not isinstance(canvas, dict):
        raise EditorError("regions document must include canvas")
    for key in ("width", "height"):
        dimension = canvas.get(key)
        if not _finite_number(dimension) or dimension <= 0:
            raise EditorError(f"canvas.{key} must be a positive finite number")

    regions = value.get("regions")
    if not isinstance(regions, list):
        raise EditorError("regions must be an array")
    ids: set[int] = set()
    for index, region in enumerate(regions):
        if not isinstance(region, dict):
            raise EditorError(f"regions[{index}] must be an object")
        region_id = region.get("id")
        if not isinstance(region_id, int) or isinstance(region_id, bool):
            raise EditorError(f"regions[{index}].id must be an integer")
        if region_id in ids:
            raise EditorError("region ids must be unique")
        ids.add(region_id)
        contour = region.get("contour")
        if not isinstance(contour, list) or len(contour) < 3:
            raise EditorError(f"regions[{index}].contour must contain at least three points")
        for point_index, point in enumerate(contour):
            if not isinstance(point, list) or len(point) != 2:
                raise EditorError(f"regions[{index}].contour[{point_index}] must be an [x, y] pair")
            if not all(_finite_number(coordinate) for coordinate in point):
                raise EditorError(f"regions[{index}].contour[{point_index}] coordinates must be finite")
    return value


def validate_corrections_document(value: object) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise EditorError("corrections document must be a JSON object")
    for key in ("added", "modified", "deleted"):
        if not isinstance(value.get(key), list):
            raise EditorError(f"corrections.{key} must be an array")
    return value


def save_review(
    session: EditorSession,
    regions: object,
    corrections: object,
) -> dict[str, str]:
    if session.catalog_outline_path is not None:
        return save_catalog_outline(session, regions)
    region_document = validate_regions_document(regions)
    correction_document = validate_corrections_document(corrections)
    destination = _confined_directory(session.run_dir, session.regions_path.parent)
    regions_path = destination / "stage-2-regions.edited.json"
    corrections_path = destination / "stage-2-human-corrections.json"
    _atomic_write_json(regions_path, region_document)
    _atomic_write_json(corrections_path, correction_document)
    return {
        "regionsPath": str(regions_path.relative_to(session.run_dir)),
        "correctionsPath": str(corrections_path.relative_to(session.run_dir)),
        "savedAt": datetime.now(timezone.utc).isoformat(),
    }


def create_server(
    source: EditorSession | EditorCatalog,
    host: str = "127.0.0.1",
    port: int = 4173,
) -> ThreadingHTTPServer:
    catalog = source if isinstance(source, EditorCatalog) else EditorCatalog.from_sessions([(source.run_dir.name, source)])

    class SessionHandler(EditorRequestHandler):
        editor_catalog = catalog

    return ThreadingHTTPServer((host, port), SessionHandler)


class EditorRequestHandler(BaseHTTPRequestHandler):
    editor_catalog: EditorCatalog

    def do_GET(self) -> None:  # noqa: N802
        request = urlsplit(self.path)
        path = request.path
        if path == "/api/sessions":
            self._send_json(
                HTTPStatus.OK,
                {
                    "ok": True,
                    "sessions": [
                        {"id": entry.id, "label": entry.label, "runName": entry.run_name}
                        for entry in self.editor_catalog.sessions
                    ],
                },
            )
            return
        try:
            entry = self._selected_entry(request.query)
        except EditorError as error:
            self._send_json(HTTPStatus.NOT_FOUND, {"ok": False, "error": str(error)})
            return
        session = entry.session
        if path == "/api/session":
            include_run = len(self.editor_catalog.sessions) > 1 or bool(parse_qs(request.query).get("run"))
            self._send_json(
                HTTPStatus.OK,
                {
                    "ok": True,
                    "id": entry.id,
                    "label": entry.label,
                    "runName": entry.run_name,
                    "imageUrl": self._run_url("/api/artifact/image", entry.id, include_run),
                    "regionsUrl": self._run_url("/api/artifact/regions", entry.id, include_run),
                    "saveUrl": self._run_url("/api/save", entry.id, include_run),
                    "imagePath": _relative_display_path(session.run_dir, session.image_path),
                    "regionsPath": _relative_display_path(session.run_dir, session.regions_path),
                },
            )
            return
        if path == "/api/artifact/image":
            self._send_file(session.image_path)
            return
        if path == "/api/artifact/regions":
            if session.catalog_outline_path is not None:
                self._send_json(HTTPStatus.OK, catalog_regions_document(session))
            else:
                self._send_file(session.regions_path)
            return
        static_files = {
            "/": "index.html",
            "/index.html": "index.html",
            "/styles.css": "styles.css",
            "/editor-model.js": "editor-model.js",
            "/app.js": "app.js",
        }
        filename = static_files.get(path)
        if filename is not None:
            self._send_file(EDITOR_ROOT / filename)
            return
        self._send_json(HTTPStatus.NOT_FOUND, {"ok": False, "error": "not found"})

    def do_PUT(self) -> None:  # noqa: N802
        request = urlsplit(self.path)
        if request.path != "/api/save":
            self._send_json(HTTPStatus.NOT_FOUND, {"ok": False, "error": "not found"})
            return
        try:
            session = self._selected_entry(request.query).session
        except EditorError as error:
            self._send_json(HTTPStatus.NOT_FOUND, {"ok": False, "error": str(error)})
            return
        if self.headers.get_content_type() != "application/json":
            self._send_json(HTTPStatus.UNSUPPORTED_MEDIA_TYPE, {"ok": False, "error": "Content-Type must be application/json"})
            return
        try:
            length = int(self.headers.get("Content-Length", ""))
        except ValueError:
            length = -1
        if length < 0:
            self._send_json(HTTPStatus.LENGTH_REQUIRED, {"ok": False, "error": "Content-Length is required"})
            return
        if length > MAX_REQUEST_BYTES:
            self._send_json(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, {"ok": False, "error": "request exceeds 10 MiB"})
            return
        try:
            payload = json.loads(self.rfile.read(length))
            if not isinstance(payload, dict):
                raise EditorError("save payload must be a JSON object")
            result = save_review(session, payload.get("regions"), payload.get("corrections"))
        except (EditorError, OSError, json.JSONDecodeError, UnicodeDecodeError) as error:
            self._send_json(HTTPStatus.BAD_REQUEST, {"ok": False, "error": str(error)})
            return
        self._send_json(HTTPStatus.OK, {"ok": True, **result})

    def _selected_entry(self, query: str) -> CatalogSession:
        values = parse_qs(query).get("run", [])
        return self.editor_catalog.get(values[0] if values else None)

    @staticmethod
    def _run_url(path: str, run_id: str, include_run: bool) -> str:
        return f"{path}?{urlencode({'run': run_id})}" if include_run else path

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
        content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        return


def _require_directory(value: Path, description: str) -> Path:
    path = Path(value).expanduser().resolve()
    if not path.is_dir():
        raise EditorError(f"{description} does not exist: {path}")
    return path


def _common_parent(*paths: Path) -> Path:
    return Path(os.path.commonpath([str(path) for path in paths]))


def _relative_display_path(root: Path, path: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return path.name


def _load_catalog_outline(session: EditorSession) -> dict[str, Any]:
    path = session.catalog_outline_path or session.regions_path
    if session.catalog_outline_dir is not None:
        path = _confined_file(session.catalog_outline_dir, path)
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise EditorError(f"could not read catalog outline: {error}") from error
    if not isinstance(document, dict):
        raise EditorError("catalog outline must be a JSON object")
    canvas = document.get("canvas")
    if not isinstance(canvas, dict):
        raise EditorError("catalog outline must include canvas")
    for key in ("width", "height"):
        if not _finite_number(canvas.get(key)) or canvas[key] <= 0:
            raise EditorError(f"catalog canvas.{key} must be a positive finite number")
    outlines = document.get("outlines")
    if not isinstance(outlines, list):
        raise EditorError("catalog outline must include an outlines array")
    for index, outline in enumerate(outlines):
        if not isinstance(outline, dict) or not isinstance(outline.get("id"), str) or not outline["id"]:
            raise EditorError(f"catalog outlines[{index}] must have a string id")
        path_document = outline.get("path")
        if not isinstance(path_document, dict) or not isinstance(path_document.get("commands"), list):
            raise EditorError(f"catalog outlines[{index}] must include path commands")
    return document


def _editor_ids_for_outlines(outlines: list[dict[str, Any]]) -> dict[str, int]:
    source_ids = [outline["id"] for outline in outlines]
    if len(set(source_ids)) != len(source_ids):
        raise EditorError("catalog outline ids must be unique")
    result: dict[str, int] = {}
    used: set[int] = set()
    for source_id in sorted(source_ids):
        match = HOLD_IDENTIFIER.fullmatch(source_id)
        if match is not None:
            candidate = int(match.group(1))
        else:
            digest = hashlib.sha256(source_id.encode("utf-8")).digest()
            candidate = int.from_bytes(digest[:4], "big") & 0x7FFFFFFF
            candidate = max(candidate, 1)
        while candidate in used or candidate <= 0:
            candidate = candidate + 1 if candidate < 0x7FFFFFFF else 1
        result[source_id] = candidate
        used.add(candidate)
    return result


def _flatten_outline(commands: list[dict[str, Any]]) -> list[list[float]]:
    points: list[list[float]] = []
    current: list[float] | None = None
    start: list[float] | None = None
    for index, command in enumerate(commands):
        if not isinstance(command, dict) or not isinstance(command.get("command"), str):
            raise EditorError(f"catalog path command {index} is invalid")
        operation = command["command"].upper()
        if operation in {"M", "L"}:
            target = _path_point(command.get("to"), index)
            if operation == "M":
                if points and start is not None and points[-1] == start:
                    points.pop()
                start = target
            elif current is None:
                raise EditorError("catalog path must begin with M")
            points.append(target)
            current = target
        elif operation == "C":
            if current is None:
                raise EditorError("catalog path must begin with M")
            controls = command.get("controls")
            if not isinstance(controls, list) or len(controls) != 2:
                raise EditorError(f"catalog cubic command {index} must have two controls")
            control_one = _path_point(controls[0], index)
            control_two = _path_point(controls[1], index)
            target = _path_point(command.get("to"), index)
            for segment in range(1, CUBIC_SEGMENTS + 1):
                t = segment / CUBIC_SEGMENTS
                inverse = 1 - t
                points.append([
                    inverse**3 * current[0]
                    + 3 * inverse**2 * t * control_one[0]
                    + 3 * inverse * t**2 * control_two[0]
                    + t**3 * target[0],
                    inverse**3 * current[1]
                    + 3 * inverse**2 * t * control_one[1]
                    + 3 * inverse * t**2 * control_two[1]
                    + t**3 * target[1],
                ])
            current = target
        elif operation == "Z":
            if current is None or start is None:
                raise EditorError("catalog path must begin with M")
            current = start
        else:
            raise EditorError(f"unsupported catalog path command: {operation}")
    if len(points) > 1 and start is not None:
        while len(points) > 1 and points[-1] == start:
            points.pop()
    if len(points) < 3:
        raise EditorError("catalog path must contain at least three points")
    return points


def _path_point(value: object, index: int) -> list[float]:
    if not isinstance(value, list) or len(value) != 2 or not all(_finite_number(item) for item in value):
        raise EditorError(f"catalog path command {index} has an invalid point")
    return [float(value[0]), float(value[1])]


def _next_hold_number(existing_by_id: dict[str, Any]) -> int:
    numbers = [
        int(match.group(1))
        for source_id in existing_by_id
        if (match := HOLD_IDENTIFIER.fullmatch(source_id)) is not None
    ]
    candidate = 1
    while candidate in numbers:
        candidate += 1
    return candidate


def _next_hold_id(existing_by_id: dict[str, Any], candidate: int) -> str:
    existing_numbers = {
        int(match.group(1))
        for source_id in existing_by_id
        if (match := HOLD_IDENTIFIER.fullmatch(source_id)) is not None
    }
    while candidate in existing_numbers:
        candidate += 1
    return f"hold-{candidate:02d}"


def _normalized_contour(canvas: dict[str, Any], contour: list[list[object]]) -> list[list[float]]:
    points = [
        [_normalized_number(float(point[0]) / canvas["width"]), _normalized_number(float(point[1]) / canvas["height"])]
        for point in contour
    ]
    while len(points) > 1 and points[-1] == points[0]:
        points.pop()
    if len(points) < 3:
        raise EditorError("catalog region contour must contain at least three distinct points")
    return points


def _normalized_number(value: float) -> float:
    return round(value, 12)


def _closed_line_path(canvas: dict[str, Any], contour: list[list[object]]) -> dict[str, Any]:
    points = _normalized_contour(canvas, contour)
    return {
        "closed": True,
        "commands": [
            {"command": "M" if index == 0 else "L", "to": point}
            for index, point in enumerate(points)
        ],
    }


def _normalized_bounds(canvas: dict[str, Any], contour: list[list[object]]) -> dict[str, float]:
    points = _normalized_contour(canvas, contour)
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    minimum_x, maximum_x = min(xs), max(xs)
    minimum_y, maximum_y = min(ys), max(ys)
    return {
        "x": _normalized_number(minimum_x),
        "y": _normalized_number(minimum_y),
        "width": _normalized_number(maximum_x - minimum_x),
        "height": _normalized_number(maximum_y - minimum_y),
    }


def _new_catalog_outline(region: dict[str, Any], source_id: str) -> dict[str, Any]:
    outline_type = region.get("type") if isinstance(region.get("type"), str) else "edge"
    outline = {
        "id": source_id,
        "label": region.get("key") or f"Manual {outline_type} {source_id}",
        "kind": outline_type,
        "confidence": "approximate",
    }
    notes = region.get("metadata", {}).get("humanNotes") if isinstance(region.get("metadata"), dict) else None
    if isinstance(notes, str) and notes:
        outline["notes"] = notes
    return outline


def _finite_number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _catalog_artifact(root: Path, value: str, field: str) -> Path:
    relative_path = Path(value).expanduser()
    if relative_path.is_absolute():
        raise EditorError(f"{field} must be relative to runDir")
    return _confined_file(root, root / relative_path)


def _confined_file(root: Path, candidate: Path) -> Path:
    path = candidate.resolve()
    try:
        path.relative_to(root)
    except ValueError as error:
        raise EditorError("artifact resolves outside the configured run directory") from error
    if not path.is_file():
        raise EditorError(f"artifact is not a file: {path.name}")
    return path


def _confined_directory(root: Path, candidate: Path) -> Path:
    path = candidate.resolve()
    try:
        path.relative_to(root)
    except ValueError as error:
        raise EditorError("destination resolves outside the configured run directory") from error
    if not path.is_dir():
        raise EditorError("save destination is not a directory")
    return path


def _atomic_write_json(path: Path, value: object) -> None:
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_path, path)
    except Exception:
        temporary_path.unlink(missing_ok=True)
        raise


def main() -> None:
    parser = ArgumentParser(description="Serve the hold-region editor for pipeline-generated onboarding runs")
    parser.add_argument(
        "--run-dir",
        action="append",
        default=[],
        type=Path,
        help="Onboarding run containing one Stage 1 image and Stage 2 regions file; repeat to add boards",
    )
    parser.add_argument("--catalog", type=Path, help="JSON catalog for named runs or explicit historical artifact paths")
    parser.add_argument("--catalog-source-dir", type=Path, help="Directory containing root catalog PNGs")
    parser.add_argument("--catalog-outline-dir", type=Path, help="Directory containing catalog outline JSONs")
    parser.add_argument("--host", default="127.0.0.1", help="Listen address (default: 127.0.0.1)")
    parser.add_argument("--port", default=4173, type=int, help="Listen port (default: 4173)")
    arguments = parser.parse_args()
    try:
        catalog = catalog_from_inputs(
            arguments.run_dir,
            arguments.catalog,
            arguments.catalog_source_dir,
            arguments.catalog_outline_dir,
        )
    except EditorError as error:
        parser.error(str(error))
    server = create_server(catalog, arguments.host, arguments.port)
    print(f"Hold Region Editor: http://{arguments.host}:{server.server_port}")
    for entry in catalog.sessions:
        print(f"Run [{entry.id}] {entry.label}: {entry.session.run_dir}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
