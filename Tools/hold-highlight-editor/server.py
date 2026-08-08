#!/usr/bin/env python3
"""Local filesystem boundary for the dependency-free hold-region editor."""

from __future__ import annotations

import json
import math
import mimetypes
import os
import re
import sys
import tempfile
from argparse import ArgumentParser
from dataclasses import dataclass
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from ipaddress import ip_address
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import parse_qs, unquote, urlencode, urlsplit
from uuid import uuid4

from job_manager import (
    BoardJobManager,
    JobCapacityError,
    JobConflictError,
    JobNotFoundError,
)


MAX_REQUEST_BYTES = 10 * 1024 * 1024
EDITOR_ROOT = Path(__file__).resolve().parent
_ABSOLUTE_PATH_IN_TEXT = re.compile(
    r"(?:^|[\s(\"'\[:=])(?:/|[A-Za-z]:[\\/])"
)


def _new_board_reservation_key() -> str:
    """Give each independent pre-board operation its own exclusion key."""
    return f"workbench-board-reservation-{uuid4().hex}"


def _public_job_error_message(error: Exception) -> str:
    message = str(error)
    return (
        "repository operation failed"
        if _ABSOLUTE_PATH_IN_TEXT.search(message)
        else message
    )


class EditorError(ValueError):
    """A safe, user-facing editor session or payload error."""


class RequestError(EditorError):
    """A safe HTTP request error with an explicit response status."""

    def __init__(self, status: HTTPStatus, message: str) -> None:
        super().__init__(message)
        self.status = status


@dataclass(frozen=True)
class EditorSession:
    run_dir: Path
    image_path: Path
    regions_path: Path


@dataclass(frozen=True)
class CatalogSession:
    id: str
    label: str
    session: EditorSession


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


def catalog_from_inputs(run_dirs: Iterable[Path], catalog_path: Path | None) -> EditorCatalog:
    sessions: list[tuple[str, EditorSession]] = []
    if catalog_path is not None:
        sessions.extend((entry.label, entry.session) for entry in load_catalog(catalog_path).sessions)
    for run_dir in run_dirs:
        session = discover_session(run_dir)
        sessions.append((session.run_dir.name, session))
    return EditorCatalog.from_sessions(sessions)


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


def _workbench_view_payload(view: object) -> dict[str, Any]:
    run_root = Path(view.run_root).resolve()
    def artifact_url(path: Path | None, label: str) -> str | None:
        if path is None:
            return None
        resolved_artifact = Path(path).resolve()
        try:
            relative_artifact = resolved_artifact.relative_to(run_root)
        except ValueError as error:
            raise EditorError(
                f"{label} artifact resolves outside the selected revision"
            ) from error
        return "/api/artifact?" + urlencode(
            {
                "boardId": view.board_id,
                "revisionId": view.revision_id,
                "path": relative_artifact.as_posix(),
            }
        )

    review_url = artifact_url(view.review_path, "review")
    editor_image_url = artifact_url(
        getattr(view, "editor_image_path", None), "editor image"
    )
    return {
        "boardId": view.board_id,
        "revisionId": view.revision_id,
        "parentRevisionId": view.parent_revision_id,
        "productName": view.product_name,
        "stage": view.stage,
        "state": view.state,
        "checkpointToken": view.checkpoint_token,
        "reviewUrl": review_url,
        "editorImageUrl": editor_image_url,
        "editorMode": view.editor_mode,
        "saved": view.saved,
        "staleFromStage": view.stale_from_stage,
        "repositoryBoardId": view.repository_board_id,
        "repositoryRevisionToken": view.repository_revision_token,
    }


def create_server(
    source: EditorSession | EditorCatalog | None,
    host: str = "127.0.0.1",
    port: int = 4173,
    *,
    editor_root: Path = EDITOR_ROOT,
    workbench_service: object | None = None,
    max_workers: int = 4,
    public_job_error_types: tuple[type[Exception], ...] = (),
    job_outcome_root: Path | None = None,
) -> ThreadingHTTPServer:
    catalog = (
        source
        if isinstance(source, EditorCatalog)
        else EditorCatalog.from_sessions([(source.run_dir.name, source)])
        if source is not None
        else None
    )
    jobs = BoardJobManager(
        max_workers=max_workers,
        result_serializer=_workbench_view_payload,
        public_error_types=public_job_error_types,
        public_error_formatter=_public_job_error_message,
        outcome_root=job_outcome_root,
    )

    class SessionHandler(EditorRequestHandler):
        editor_catalog = catalog

    return WorkbenchHTTPServer(
        (host, port),
        SessionHandler,
        editor_root=editor_root,
        workbench_service=workbench_service,
        job_manager=jobs,
        public_error_types=public_job_error_types,
    )


class WorkbenchHTTPServer(ThreadingHTTPServer):
    """HTTP server owning the lifecycle of its bounded job executor."""

    def __init__(
        self,
        server_address: tuple[str, int],
        request_handler: type[BaseHTTPRequestHandler],
        *,
        editor_root: Path,
        workbench_service: object | None,
        job_manager: BoardJobManager,
        public_error_types: tuple[type[Exception], ...],
    ) -> None:
        self.editor_root = Path(editor_root).resolve(strict=False)
        self.workbench_service = workbench_service
        self.job_manager = job_manager
        self.public_error_types = public_error_types
        super().__init__(server_address, request_handler)

    def server_close(self) -> None:
        try:
            super().server_close()
        finally:
            self.job_manager.shutdown()


class EditorRequestHandler(BaseHTTPRequestHandler):
    editor_catalog: EditorCatalog | None

    def do_GET(self) -> None:  # noqa: N802
        if not self._allow_request(mutation=False):
            return
        request = urlsplit(self.path)
        path = request.path
        if path == "/api/library":
            self._get_library()
            return
        if path == "/api/boards":
            self._get_boards()
            return
        if path.startswith("/api/boards/"):
            self._get_board(unquote(path.removeprefix("/api/boards/")), request.query)
            return
        if path.startswith("/api/jobs/"):
            self._get_job(unquote(path.removeprefix("/api/jobs/")))
            return
        if path == "/api/artifact":
            self._get_workbench_artifact(request.query)
            return
        static_files = {
            "/": "index.html",
            "/index.html": "index.html",
            "/styles.css": "styles.css",
            "/editor-model.js": "editor-model.js",
            "/workbench-client.js": "workbench-client.js",
            "/workbench-controller.js": "workbench-controller.js",
            "/workbench-model.js": "workbench-model.js",
            "/vector-path-model.js": "vector-path-model.js",
            "/app.js": "app.js",
        }
        filename = static_files.get(path)
        if filename is not None:
            try:
                self._send_file(self.server.editor_root / filename)
            except OSError:
                self._send_json(
                    HTTPStatus.NOT_FOUND,
                    {"ok": False, "error": "static asset not found"},
                )
            return
        if path == "/api/sessions":
            self._send_json(
                HTTPStatus.OK,
                {
                    "ok": True,
                    "sessions": [
                        {"id": entry.id, "label": entry.label, "runName": entry.session.run_dir.name}
                        for entry in (
                            self.editor_catalog.sessions
                            if self.editor_catalog is not None
                            else ()
                        )
                    ],
                },
            )
            return
        if path not in {"/api/session", "/api/artifact/image", "/api/artifact/regions"}:
            self._send_json(HTTPStatus.NOT_FOUND, {"ok": False, "error": "not found"})
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
                    "runName": session.run_dir.name,
                    "imageUrl": self._run_url("/api/artifact/image", entry.id, include_run),
                    "regionsUrl": self._run_url("/api/artifact/regions", entry.id, include_run),
                    "saveUrl": self._run_url("/api/save", entry.id, include_run),
                    "imagePath": str(session.image_path.relative_to(session.run_dir)),
                    "regionsPath": str(session.regions_path.relative_to(session.run_dir)),
                },
            )
            return
        if path == "/api/artifact/image":
            self._send_file(session.image_path)
            return
        if path == "/api/artifact/regions":
            self._send_file(session.regions_path)
            return
        self._send_json(HTTPStatus.NOT_FOUND, {"ok": False, "error": "not found"})

    def do_POST(self) -> None:  # noqa: N802
        if not self._allow_request(mutation=True):
            return
        request = urlsplit(self.path)
        try:
            service = self._workbench_service()
            if request.path == "/api/boards/upload":
                self._post_upload(service, request.query)
                return
            payload = self._read_json_object()
            if request.path == "/api/boards":
                product_name = self._required_string(payload, "productName")
                source = self._required_string(payload, "source")
                self._submit_job(
                    _new_board_reservation_key(),
                    lambda: service.create_from_url(product_name, source),
                )
                return
            if request.path == "/api/boards/import":
                run_root = Path(self._required_string(payload, "runRoot"))
                self._submit_job(
                    _new_board_reservation_key(),
                    lambda: service.import_run(run_root),
                )
                return
            if request.path.startswith("/api/library/") and request.path.endswith("/open"):
                board_id = unquote(
                    request.path.removeprefix("/api/library/").removesuffix("/open")
                )
                self._post_library_open(service, board_id)
                return
            if request.path.startswith("/api/boards/") and request.path.endswith("/save"):
                board_id = unquote(
                    request.path.removeprefix("/api/boards/").removesuffix("/save")
                )
                if self._required_string(payload, "boardId") != board_id:
                    raise RequestError(
                        HTTPStatus.BAD_REQUEST, "boardId must match the save route"
                    )
                self._post_mutation(service, "/api/final-save", payload)
                return
            if request.path in {
                "/api/drafts",
                "/api/approve",
                "/api/revise",
                "/api/retry",
            }:
                self._post_mutation(service, request.path, payload)
                return
            raise RequestError(HTTPStatus.NOT_FOUND, "not found")
        except RequestError as error:
            self._send_json(error.status, {"ok": False, "error": str(error)})
        except JobConflictError as error:
            self._send_json(HTTPStatus.CONFLICT, {"ok": False, "error": str(error)})
        except JobCapacityError as error:
            self._send_json(
                HTTPStatus.SERVICE_UNAVAILABLE,
                {"ok": False, "error": str(error)},
            )
        except ValueError as error:
            self._send_json(HTTPStatus.BAD_REQUEST, {"ok": False, "error": str(error)})
        except Exception:
            self._send_json(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                {"ok": False, "error": "request failed"},
            )

    def do_PUT(self) -> None:  # noqa: N802
        if not self._allow_request(mutation=True):
            return
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
        except (EditorError, json.JSONDecodeError, UnicodeDecodeError) as error:
            self._send_json(HTTPStatus.BAD_REQUEST, {"ok": False, "error": str(error)})
            return
        self._send_json(HTTPStatus.OK, {"ok": True, **result})

    def _get_boards(self) -> None:
        try:
            service = self._workbench_service()
            boards = [_workbench_view_payload(view) for view in service.list_boards()]
        except RequestError as error:
            self._send_json(error.status, {"ok": False, "error": str(error)})
            return
        except self._public_error_types() as error:
            self._send_json(HTTPStatus.BAD_REQUEST, {"ok": False, "error": str(error)})
            return
        except Exception:
            self._send_json(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                {"ok": False, "error": "request failed"},
            )
            return
        self._send_json(HTTPStatus.OK, {"ok": True, "boards": boards})

    def _get_library(self) -> None:
        try:
            service = self._workbench_service()
            snapshot = service.library_snapshot()
            boards = [
                {
                    "boardId": board.board_id,
                    "displayName": board.display_name,
                    "revisionToken": board.revision_token,
                }
                for board in snapshot.boards
            ]
            diagnostics = [
                self._library_diagnostic_payload(diagnostic)
                for diagnostic in snapshot.diagnostics
            ]
        except RequestError as error:
            self._send_json(error.status, {"ok": False, "error": str(error)})
            return
        except self._public_error_types() as error:
            self._send_json(HTTPStatus.BAD_REQUEST, {"ok": False, "error": str(error)})
            return
        except Exception:
            self._send_json(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                {"ok": False, "error": "request failed"},
            )
            return
        self._send_json(
            HTTPStatus.OK,
            {"ok": True, "boards": boards, "diagnostics": diagnostics},
        )

    def _get_board(self, board_id: str, query: str) -> None:
        try:
            if not board_id:
                raise RequestError(HTTPStatus.NOT_FOUND, "not found")
            service = self._workbench_service()
            revision_values = parse_qs(query).get("revisionId", [])
            revision_id = revision_values[0] if revision_values else None
            board = _workbench_view_payload(
                service.get_board(board_id, revision_id=revision_id)
            )
        except RequestError as error:
            self._send_json(error.status, {"ok": False, "error": str(error)})
            return
        except self._public_error_types() as error:
            self._send_json(HTTPStatus.NOT_FOUND, {"ok": False, "error": str(error)})
            return
        except Exception:
            self._send_json(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                {"ok": False, "error": "request failed"},
            )
            return
        self._send_json(HTTPStatus.OK, {"ok": True, "board": board})

    def _get_job(self, job_id: str) -> None:
        try:
            job = self._job_manager().get(job_id)
        except JobNotFoundError as error:
            self._send_json(HTTPStatus.NOT_FOUND, {"ok": False, "error": str(error)})
            return
        self._send_json(HTTPStatus.OK, {"ok": True, "job": job.as_dict()})

    def _get_workbench_artifact(self, query: str) -> None:
        try:
            values = parse_qs(query)
            relative_value = self._required_query_string(values, "path")
            relative = Path(relative_value)
            if relative.is_absolute() or ".." in relative.parts:
                raise RequestError(
                    HTTPStatus.BAD_REQUEST,
                    "artifact path must stay within the selected revision",
                )
            board_id = self._required_query_string(values, "boardId")
            revision_id = self._required_query_string(values, "revisionId")
            view = self._workbench_service().get_board(
                board_id, revision_id=revision_id
            )
            root = Path(view.run_root).resolve(strict=True)
            artifact = (root / relative).resolve(strict=True)
            artifact.relative_to(root)
            if not artifact.is_file():
                raise FileNotFoundError
            body = artifact.read_bytes()
        except RequestError as error:
            self._send_json(error.status, {"ok": False, "error": str(error)})
            return
        except (FileNotFoundError, OSError, RuntimeError, ValueError):
            self._send_json(
                HTTPStatus.NOT_FOUND,
                {"ok": False, "error": "artifact not found"},
            )
            return
        self._send_file_body(artifact, body)

    def _post_upload(self, service: object, query: str) -> None:
        if not self.headers.get_content_type().startswith("image/"):
            raise RequestError(
                HTTPStatus.UNSUPPORTED_MEDIA_TYPE,
                "Content-Type must be image/*",
            )
        product_name = self._required_query_string(
            parse_qs(query), "productName"
        )
        content = self._read_body()
        if not content:
            raise RequestError(HTTPStatus.BAD_REQUEST, "upload must not be empty")
        self._submit_job(
            _new_board_reservation_key(),
            lambda: service.create_from_upload(product_name, content),
        )

    def _post_library_open(self, service: object, board_id: str) -> None:
        if not board_id:
            raise RequestError(HTTPStatus.NOT_FOUND, "not found")
        if not any(
            board.board_id == board_id for board in service.library_snapshot().boards
        ):
            raise RequestError(
                HTTPStatus.NOT_FOUND, f"board does not exist: {board_id}"
            )
        self._submit_job(
            board_id,
            lambda: service.open_library_board(board_id),
            conflict_key=service.library_open_reservation_key(board_id),
        )

    @staticmethod
    def _relative_diagnostic_path(value: object) -> str:
        if not isinstance(value, str) or not value:
            raise EditorError("repository diagnostic path must be relative")
        path = Path(value)
        if path.is_absolute() or ".." in path.parts:
            raise EditorError("repository diagnostic path must be relative")
        return path.as_posix()

    @classmethod
    def _library_diagnostic_payload(cls, diagnostic: object) -> dict[str, str]:
        path = cls._relative_diagnostic_path(diagnostic.path)
        message = diagnostic.message
        if (
            not isinstance(message, str)
            or not message
            or _ABSOLUTE_PATH_IN_TEXT.search(message)
        ):
            message = f"{path}: repository package is invalid"
        return {"path": path, "code": diagnostic.code, "message": message}

    def _post_mutation(
        self, service: object, path: str, payload: dict[str, Any]
    ) -> None:
        board_id = self._required_string(payload, "boardId")
        revision_id = self._required_string(payload, "expectedRevisionId")
        if path == "/api/final-save":
            operation = lambda: service.save(
                board_id, expected_revision_id=revision_id
            )
        else:
            stage = self._required_stage(payload, "expectedStage")
            if path == "/api/drafts":
                checkpoint_token = self._required_string(
                    payload, "expectedCheckpointToken"
                )
                if "document" not in payload:
                    raise RequestError(
                        HTTPStatus.BAD_REQUEST, "document is required"
                    )
                document = payload["document"]
                operation = lambda: service.save_draft(
                    board_id,
                    document,
                    expected_stage=stage,
                    expected_checkpoint_token=checkpoint_token,
                    expected_revision_id=revision_id,
                )
            elif path == "/api/approve":
                checkpoint_token = self._required_string(
                    payload, "expectedCheckpointToken"
                )
                operation = lambda: service.approve_and_advance(
                    board_id,
                    expected_stage=stage,
                    expected_checkpoint_token=checkpoint_token,
                    expected_revision_id=revision_id,
                )
            elif path == "/api/revise":
                operation = lambda: service.revise_stage(
                    board_id,
                    stage=stage,
                    expected_revision_id=revision_id,
                )
            else:
                operation = lambda: service.retry(
                    board_id,
                    expected_stage=stage,
                    expected_revision_id=revision_id,
                )
        self._submit_job(
            board_id,
            operation,
            conflict_key=service.mutation_reservation_key(board_id),
        )

    def _submit_job(
        self,
        board_id: str,
        operation: object,
        *,
        conflict_key: str | None = None,
    ) -> None:
        job = self._job_manager().submit(
            board_id,
            operation,
            conflict_key=conflict_key,
        )
        self._send_json(
            HTTPStatus.ACCEPTED,
            {"ok": True, "jobId": job.id},
        )

    def _read_json_object(self) -> dict[str, Any]:
        if self.headers.get_content_type() != "application/json":
            raise RequestError(
                HTTPStatus.UNSUPPORTED_MEDIA_TYPE,
                "Content-Type must be application/json",
            )
        try:
            payload = json.loads(self._read_body())
        except (json.JSONDecodeError, UnicodeDecodeError) as error:
            raise RequestError(
                HTTPStatus.BAD_REQUEST, "request body must be valid JSON"
            ) from error
        if not isinstance(payload, dict):
            raise RequestError(
                HTTPStatus.BAD_REQUEST, "request body must be a JSON object"
            )
        return payload

    def _read_body(self) -> bytes:
        try:
            length = int(self.headers.get("Content-Length", ""))
        except ValueError:
            length = -1
        if length < 0:
            raise RequestError(
                HTTPStatus.LENGTH_REQUIRED, "Content-Length is required"
            )
        if length > MAX_REQUEST_BYTES:
            raise RequestError(
                HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
                "request exceeds 10 MiB",
            )
        return self.rfile.read(length)

    @staticmethod
    def _required_string(payload: dict[str, Any], field: str) -> str:
        value = payload.get(field)
        if not isinstance(value, str) or not value.strip():
            raise RequestError(
                HTTPStatus.BAD_REQUEST, f"{field} must be a non-empty string"
            )
        return value.strip()

    @staticmethod
    def _required_stage(payload: dict[str, Any], field: str) -> int:
        value = payload.get(field)
        if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 4:
            raise RequestError(
                HTTPStatus.BAD_REQUEST,
                f"{field} must be an integer between 0 and 4",
            )
        return value

    @staticmethod
    def _required_query_string(values: dict[str, list[str]], field: str) -> str:
        selected = values.get(field, [])
        if len(selected) != 1 or not selected[0].strip():
            raise RequestError(
                HTTPStatus.BAD_REQUEST, f"{field} must be provided exactly once"
            )
        return selected[0].strip()

    def _workbench_service(self) -> Any:
        service = getattr(self.server, "workbench_service", None)
        if service is None:
            raise RequestError(
                HTTPStatus.NOT_FOUND, "workbench service is unavailable"
            )
        return service

    def _job_manager(self) -> BoardJobManager:
        return self.server.job_manager

    def _public_error_types(self) -> tuple[type[Exception], ...]:
        return self.server.public_error_types

    def _selected_entry(self, query: str) -> CatalogSession:
        if self.editor_catalog is None:
            raise EditorError("no editor sessions are configured")
        values = parse_qs(query).get("run", [])
        return self.editor_catalog.get(values[0] if values else None)

    def _allow_request(self, *, mutation: bool) -> bool:
        host_values = self.headers.get_all("Host", [])
        host = (
            _loopback_authority(host_values[0], self.server.server_port)
            if len(host_values) == 1
            else None
        )
        if host is not None and mutation:
            origin_values = self.headers.get_all("Origin", [])
            if origin_values:
                origin = (
                    _loopback_origin(origin_values[0], self.server.server_port)
                    if len(origin_values) == 1
                    else None
                )
                if origin != host:
                    host = None
            elif self.headers.get("Sec-Fetch-Site") is not None:
                host = None
        if host is not None:
            return True
        self._send_json(
            HTTPStatus.FORBIDDEN,
            {"ok": False, "error": "request origin is not allowed"},
        )
        return False

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
        self._send_file_body(path, body)

    def _send_file_body(self, path: Path, body: bytes) -> None:
        content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        return


def _finite_number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _loopback_authority(value: object, selected_port: int) -> tuple[str, int] | None:
    if not isinstance(value, str) or not value or value.strip() != value:
        return None
    try:
        parsed = urlsplit(f"//{value}")
        port = parsed.port if parsed.port is not None else 80
    except ValueError:
        return None
    if (
        not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.path
        or parsed.query
        or parsed.fragment
        or port != selected_port
    ):
        return None
    hostname = parsed.hostname.lower().rstrip(".")
    if hostname == "localhost":
        return hostname, port
    try:
        if ip_address(hostname).is_loopback:
            return hostname, port
    except ValueError:
        pass
    return None


def _loopback_origin(value: object, selected_port: int) -> tuple[str, int] | None:
    if not isinstance(value, str) or not value or value.strip() != value:
        return None
    try:
        parsed = urlsplit(value)
    except ValueError:
        return None
    if (
        parsed.scheme.lower() != "http"
        or not parsed.netloc
        or parsed.path
        or parsed.query
        or parsed.fragment
    ):
        return None
    return _loopback_authority(parsed.netloc, selected_port)


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


def _argument_parser() -> ArgumentParser:
    parser = ArgumentParser(description="Serve the hold-region editor for pipeline-generated onboarding runs")
    parser.add_argument(
        "--run-dir",
        action="append",
        default=[],
        type=Path,
        help="Onboarding run containing one Stage 1 image and Stage 2 regions file; repeat to add boards",
    )
    parser.add_argument("--catalog", type=Path, help="JSON catalog for named runs or explicit historical artifact paths")
    parser.add_argument(
        "--workspace-root",
        type=Path,
        help="Persistent workbench workspace; may be combined with legacy run inputs",
    )
    parser.add_argument(
        "--repository-root",
        type=Path,
        help="Checkout containing the repository board library",
    )
    parser.add_argument("--host", default="127.0.0.1", help="Listen address (default: 127.0.0.1)")
    parser.add_argument("--port", default=4173, type=int, help="Listen port (default: 4173)")
    return parser


def _create_workbench_service(
    workspace_root: Path,
    repository_root: Path | None,
) -> tuple[object, tuple[type[Exception], ...]]:
    try:
        from hangboard_vectorizer.workbench import WorkbenchService, WorkbenchServiceError
        from hangboard_vectorizer.workbench_store import WorkbenchStore
    except ModuleNotFoundError as error:
        if error.name not in {
            "hangboard_vectorizer",
            "hangboard_vectorizer.workbench",
            "hangboard_vectorizer.workbench_store",
        }:
            raise
        onboarding_source = EDITOR_ROOT.parent / "HangboardOnboarding" / "src"
        source_value = str(onboarding_source)
        if source_value not in sys.path:
            sys.path.insert(0, source_value)
        sys.modules.pop("hangboard_vectorizer", None)
        from hangboard_vectorizer.workbench import WorkbenchService, WorkbenchServiceError
        from hangboard_vectorizer.workbench_store import WorkbenchStore

    library = None
    public_error_types: tuple[type[Exception], ...] = (WorkbenchServiceError,)
    if repository_root is not None:
        from hangboard_vectorizer.board_library import (
            BoardLibraryError,
            RepositoryBoardLibrary,
        )

        library = RepositoryBoardLibrary(repository_root)
        public_error_types = (WorkbenchServiceError, BoardLibraryError)

    return (
        WorkbenchService(
            WorkbenchStore(workspace_root),
            library=library,
        ),
        public_error_types,
    )


def _discover_repository_root(start: Path) -> Path:
    candidate = Path(start).expanduser().resolve(strict=False)
    while True:
        if (candidate / ".git").exists():
            return candidate
        if candidate.parent == candidate:
            raise EditorError("could not find a repository root from the current directory")
        candidate = candidate.parent


def _configured_repository_root(value: Path | None) -> Path:
    if value is None:
        return _discover_repository_root(Path.cwd())
    root = Path(value).expanduser().resolve(strict=False)
    if not root.is_dir() or not (root / ".git").exists():
        raise EditorError("repository root must be a checkout containing .git")
    return root


def _server_from_cli(
    arguments: list[str] | None = None,
    *,
    editor_root: Path = EDITOR_ROOT,
) -> tuple[WorkbenchHTTPServer, EditorCatalog | None]:
    parser = _argument_parser()
    parsed = parser.parse_args(arguments)
    try:
        catalog = (
            catalog_from_inputs(parsed.run_dir, parsed.catalog)
            if parsed.run_dir or parsed.catalog is not None
            else None
        )
        use_workbench = (
            parsed.workspace_root is not None
            or parsed.repository_root is not None
            or catalog is None
        )
        workspace_root: Path | None = None
        if use_workbench:
            use_repository_library = (
                parsed.repository_root is not None
                or (catalog is None and parsed.workspace_root is None)
            )
            repository_root = (
                _configured_repository_root(parsed.repository_root)
                if use_repository_library
                else None
            )
            workspace_root = (
                parsed.workspace_root.expanduser().resolve(strict=False)
                if parsed.workspace_root is not None
                else repository_root / ".context" / "hangboard-workbench"
            )
            service, public_job_error_types = _create_workbench_service(
                workspace_root,
                repository_root,
            )
        else:
            service = None
            public_job_error_types = ()
    except (EditorError, OSError, ValueError) as error:
        parser.error(str(error))
    server = create_server(
        catalog,
        parsed.host,
        parsed.port,
        editor_root=editor_root,
        workbench_service=service,
        public_job_error_types=public_job_error_types,
        job_outcome_root=(
            workspace_root / ".workbench-job-outcomes"
            if workspace_root is not None
            else None
        ),
    )
    return server, catalog


def main() -> None:
    server, catalog = _server_from_cli()
    print(f"Hold Region Editor: http://{server.server_address[0]}:{server.server_port}")
    if catalog is not None:
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
