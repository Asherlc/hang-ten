from __future__ import annotations

import json
import math
import sys
import threading
from contextlib import contextmanager
from dataclasses import dataclass, replace
from http.client import HTTPConnection
from pathlib import Path
from threading import Event, Lock
from urllib.error import HTTPError
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen

import pytest

EDITOR_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(EDITOR_ROOT))

import server as server_module  # noqa: E402
from server import (  # noqa: E402
    EditorCatalog,
    EditorError,
    catalog_from_inputs,
    create_server,
    discover_session,
    load_catalog,
    save_review,
    validate_regions_document,
)


REGIONS = {
    "canvas": {"width": 1000, "height": 358},
    "regions": [
        {
            "id": 1,
            "key": "grip-001",
            "type": "edge",
            "contour": [[10, 10], [40, 10], [40, 30], [10, 30]],
            "metadata": {"mode": "surface"},
        }
    ],
}

CORRECTIONS = {
    "schemaVersion": 1,
    "summary": {"added": 0, "modified": 1, "deleted": 0},
    "added": [],
    "modified": REGIONS["regions"],
    "deleted": [],
}


@dataclass(frozen=True)
class FakeWorkbenchView:
    board_id: str
    revision_id: str
    parent_revision_id: str | None
    run_root: Path
    product_name: str
    stage: int
    state: str
    review_path: Path | None
    editor_image_path: Path | None
    editor_mode: str | None
    saved: bool
    stale_from_stage: int | None
    checkpoint_token: str | None
    repository_board_id: str | None = None
    repository_version_id: str | None = None


@dataclass(frozen=True)
class FakeLibraryBoard:
    board_id: str
    display_name: str
    current_version_id: str


class FakeWorkbenchError(ValueError):
    """Explicitly safe public error contract for deterministic API tests."""


class FakeWorkbenchService:
    def __init__(self, root: Path):
        self._root = root
        self._boards: dict[str, FakeWorkbenchView] = {}
        self._drafts: dict[str, object] = {}
        self._counter = 0
        self._lock = Lock()
        self.approve_started = Event()
        self.approve_gate: Event | None = None
        self.library_boards: tuple[FakeLibraryBoard, ...] = (
            FakeLibraryBoard(
                board_id="example-board",
                display_name="Example Board",
                current_version_id="revision-0001",
            ),
        )
        self.library_error: FakeWorkbenchError | None = None

    def create_from_url(self, product_name: str, source_url: str) -> FakeWorkbenchView:
        if not source_url.startswith(("http://", "https://")):
            raise FakeWorkbenchError("source URL must use HTTP(S)")
        return self._create(product_name, source_url.encode())

    def create_from_upload(self, product_name: str, content: bytes) -> FakeWorkbenchView:
        if not content:
            raise FakeWorkbenchError("upload content must not be empty")
        return self._create(product_name, content)

    def import_run(self, run_root: Path) -> FakeWorkbenchView:
        return self._create(run_root.name, b"imported")

    def list_boards(self) -> tuple[FakeWorkbenchView, ...]:
        with self._lock:
            return tuple(self._boards.values())

    def list_library_boards(self) -> tuple[FakeLibraryBoard, ...]:
        if self.library_error is not None:
            raise self.library_error
        return self.library_boards

    def open_library_board(self, board_id: str) -> FakeWorkbenchView:
        if self.library_error is not None:
            raise self.library_error
        board = next(
            (entry for entry in self.library_boards if entry.board_id == board_id),
            None,
        )
        if board is None:
            raise FakeWorkbenchError(f"board does not exist: {board_id}")
        return self._update(
            self._create(board.display_name, b"repository-board"),
            repository_board_id=board.board_id,
            repository_version_id=board.current_version_id,
        )

    def get_board(
        self, board_id: str, *, revision_id: str | None = None
    ) -> FakeWorkbenchView:
        with self._lock:
            try:
                view = self._boards[board_id]
            except KeyError as error:
                raise FakeWorkbenchError(f"unknown board: {board_id}") from error
        if revision_id is not None and revision_id != view.revision_id:
            raise FakeWorkbenchError(f"unknown revision: {revision_id}")
        return view

    def save_draft(
        self,
        board_id: str,
        document: object,
        *,
        expected_stage: int,
        expected_checkpoint_token: str,
        expected_revision_id: str | None = None,
    ) -> FakeWorkbenchView:
        view = self._expected(
            board_id,
            expected_revision_id,
            expected_stage,
            expected_checkpoint_token,
        )
        self._drafts[board_id] = document
        return view

    def approve_and_advance(
        self,
        board_id: str,
        *,
        expected_stage: int,
        expected_checkpoint_token: str,
        expected_revision_id: str | None = None,
    ) -> FakeWorkbenchView:
        view = self._expected(
            board_id,
            expected_revision_id,
            expected_stage,
            expected_checkpoint_token,
        )
        self.approve_started.set()
        if self.approve_gate is not None:
            self.approve_gate.wait(1)
        next_stage = min(4, view.stage + 1)
        state = "complete" if view.stage == 4 else "awaiting_review"
        return self._update(view, stage=next_stage, state=state)

    def revise_stage(
        self,
        board_id: str,
        *,
        stage: int,
        expected_revision_id: str | None = None,
    ) -> FakeWorkbenchView:
        view = self.get_board(board_id)
        if expected_revision_id != view.revision_id:
            raise FakeWorkbenchError("expected revision does not match")
        return self._update(
            view,
            revision_id=f"{view.revision_id}-revised",
            parent_revision_id=view.revision_id,
            stage=stage,
            saved=False,
        )

    def retry(
        self,
        board_id: str,
        *,
        expected_stage: int,
        expected_revision_id: str | None = None,
    ) -> FakeWorkbenchView:
        view = self._expected(board_id, expected_revision_id, expected_stage)
        return self._update(
            view,
            checkpoint_token=f"{view.checkpoint_token}-retry",
        )

    def save(
        self, board_id: str, *, expected_revision_id: str | None = None
    ) -> FakeWorkbenchView:
        view = self.get_board(board_id)
        if expected_revision_id != view.revision_id:
            raise FakeWorkbenchError("expected revision does not match")
        return self._update(view, saved=True)

    def _create(self, product_name: str, content: bytes) -> FakeWorkbenchView:
        with self._lock:
            self._counter += 1
            board_id = f"board-{self._counter}"
            revision_id = "revision-1"
            run_root = self._root / board_id / revision_id / "run"
            review_path = run_root / "stages/00/stage-0-review.png"
            review_path.parent.mkdir(parents=True)
            review_path.write_bytes(content)
            view = FakeWorkbenchView(
                board_id=board_id,
                revision_id=revision_id,
                parent_revision_id=None,
                run_root=run_root,
                product_name=product_name,
                stage=0,
                state="awaiting_review",
                review_path=review_path,
                editor_image_path=None,
                editor_mode=None,
                saved=False,
                stale_from_stage=None,
                checkpoint_token="checkpoint-0-attempt-1",
            )
            self._boards[board_id] = view
            return view

    def _expected(
        self,
        board_id: str,
        revision_id: str | None,
        stage: int,
        checkpoint_token: str | None = None,
    ) -> FakeWorkbenchView:
        view = self.get_board(board_id)
        if revision_id != view.revision_id:
            raise FakeWorkbenchError("expected revision does not match")
        if stage != view.stage:
            raise FakeWorkbenchError("expected stage does not match")
        if checkpoint_token is not None and checkpoint_token != view.checkpoint_token:
            raise FakeWorkbenchError("expected checkpoint does not match")
        return view

    def _update(self, view: FakeWorkbenchView, **changes) -> FakeWorkbenchView:
        stage = changes.get("stage", view.stage)
        state = changes.get("state", view.state)
        if "checkpoint_token" not in changes:
            changes["checkpoint_token"] = (
                f"checkpoint-{stage}-attempt-1"
                if state == "awaiting_review"
                else None
            )
        if stage in (2, 3) and "editor_image_path" not in changes:
            editor_image = view.run_root / "stages/01/stage-1-auto-rgba.png"
            editor_image.parent.mkdir(parents=True, exist_ok=True)
            editor_image.write_bytes(b"clean-canvas-image")
            changes["editor_image_path"] = editor_image
            changes.setdefault("editor_mode", "contour" if stage == 2 else "vector")
        updated = replace(view, **changes)
        with self._lock:
            self._boards[view.board_id] = updated
        return updated


class RaceRevealingCreationService(FakeWorkbenchService):
    """Detect concurrent allocation without preventing it in the fake itself."""

    def __init__(self, root: Path):
        super().__init__(root)
        self.creation_started = Event()
        self.creation_release = Event()
        self.overlapped = False
        self._active_creations = 0
        self._creation_observer = Lock()

    def create_from_url(self, product_name: str, source_url: str) -> FakeWorkbenchView:
        self._begin_creation()
        try:
            self.creation_release.wait(1)
            return super().create_from_url(product_name, source_url)
        finally:
            self._end_creation()

    def create_from_upload(self, product_name: str, content: bytes) -> FakeWorkbenchView:
        self._begin_creation()
        try:
            self.creation_release.wait(1)
            return super().create_from_upload(product_name, content)
        finally:
            self._end_creation()

    def import_run(self, run_root: Path) -> FakeWorkbenchView:
        self._begin_creation()
        try:
            self.creation_release.wait(1)
            return super().import_run(run_root)
        finally:
            self._end_creation()

    def _begin_creation(self) -> None:
        with self._creation_observer:
            self._active_creations += 1
            if self._active_creations > 1:
                self.overlapped = True
        self.creation_started.set()

    def _end_creation(self) -> None:
        with self._creation_observer:
            self._active_creations -= 1


class PathLeakingWorkbenchService(FakeWorkbenchService):
    def approve_and_advance(
        self,
        board_id: str,
        *,
        expected_stage: int,
        expected_checkpoint_token: str,
        expected_revision_id: str | None = None,
    ) -> FakeWorkbenchView:
        raise ValueError(f"could not open {self._root.resolve() / 'private.txt'}")


class PathLeakingGetService(FakeWorkbenchService):
    def list_boards(self) -> tuple[FakeWorkbenchView, ...]:
        raise ValueError(f"could not scan {self._root.resolve() / 'private'}")


class GeometryFailWorkbenchService(FakeWorkbenchService):
    def approve_and_advance(
        self,
        board_id: str,
        *,
        expected_stage: int,
        expected_checkpoint_token: str,
        expected_revision_id: str | None = None,
    ) -> FakeWorkbenchView:
        raise FakeWorkbenchError("Stage 2 region 17: contour is invalid")


def make_run(root: Path):
    image = root / "stages/01/attempt-0001/stage-1-auto-rgba.png"
    regions = root / "stages/02/attempt-0001/stage-2-regions.json"
    image.parent.mkdir(parents=True)
    regions.parent.mkdir(parents=True)
    image.write_bytes(b"fake-png")
    regions.write_text(json.dumps(REGIONS))
    return discover_session(root)


def test_discover_session_finds_stage_artifacts(tmp_path):
    session = make_run(tmp_path)

    assert session.run_dir == tmp_path.resolve()
    assert session.image_path.name == "stage-1-auto-rgba.png"
    assert session.regions_path.name == "stage-2-regions.json"


def test_discover_session_rejects_ambiguous_regions(tmp_path):
    make_run(tmp_path)
    duplicate = tmp_path / "stages/02/attempt-0002/stage-2-regions.json"
    duplicate.parent.mkdir(parents=True)
    duplicate.write_text(json.dumps(REGIONS))

    with pytest.raises(EditorError, match="exactly one stage-2-regions.json"):
        discover_session(tmp_path)


def test_catalog_assigns_distinct_ids_and_preserves_labels(tmp_path):
    first = make_run(tmp_path / "first")
    second = make_run(tmp_path / "second")

    catalog = EditorCatalog.from_sessions([
        ("Beastmaker 1000", first),
        ("Simulator 3D", second),
    ])

    assert [entry.id for entry in catalog.sessions] == ["run-1", "run-2"]
    assert [entry.label for entry in catalog.sessions] == ["Beastmaker 1000", "Simulator 3D"]
    assert catalog.get("run-2").session == second
    assert catalog.get(None).session == first


def test_load_catalog_supports_explicit_pipeline_artifacts(tmp_path):
    run_root = tmp_path / "pipeline-run"
    image = run_root / "stage-one/stage-1-auto-rgba.png"
    regions = run_root / "stage-two/stage-2-auto-regions.json"
    image.parent.mkdir(parents=True)
    regions.parent.mkdir(parents=True)
    image.write_bytes(b"pipeline-image")
    regions.write_text(json.dumps(REGIONS))
    catalog_path = tmp_path / "catalog.json"
    catalog_path.write_text(json.dumps({
        "runs": [{
            "label": "Generated board",
            "runDir": "pipeline-run",
            "image": "stage-one/stage-1-auto-rgba.png",
            "regions": "stage-two/stage-2-auto-regions.json",
        }]
    }))

    catalog = load_catalog(catalog_path)

    entry = catalog.sessions[0]
    assert entry.label == "Generated board"
    assert entry.session.image_path == image.resolve()
    assert entry.session.regions_path == regions.resolve()


def test_load_catalog_rejects_artifact_outside_run(tmp_path):
    run_root = tmp_path / "pipeline-run"
    run_root.mkdir()
    outside = tmp_path / "outside.png"
    outside.write_bytes(b"secret")
    catalog_path = tmp_path / "catalog.json"
    catalog_path.write_text(json.dumps({
        "runs": [{
            "label": "Invalid board",
            "runDir": "pipeline-run",
            "image": "../outside.png",
            "regions": "../outside.png",
        }]
    }))

    with pytest.raises(EditorError, match="outside the configured run directory"):
        load_catalog(catalog_path)


def test_catalog_rejects_unknown_run_id(tmp_path):
    catalog = EditorCatalog.from_sessions([("Board", make_run(tmp_path))])

    with pytest.raises(EditorError, match="unknown run"):
        catalog.get("run-99")


def test_catalog_from_inputs_combines_catalog_and_run_directories(tmp_path):
    catalog_run = tmp_path / "catalog-run"
    direct_run = tmp_path / "direct-run"
    make_run(catalog_run)
    make_run(direct_run)
    catalog_path = tmp_path / "catalog.json"
    catalog_path.write_text(json.dumps({"runs": [{"label": "Named board", "runDir": "catalog-run"}]}))

    catalog = catalog_from_inputs([direct_run], catalog_path)

    assert [entry.label for entry in catalog.sessions] == ["Named board", "direct-run"]


def test_catalog_from_inputs_requires_at_least_one_run():
    with pytest.raises(EditorError, match="at least one"):
        catalog_from_inputs([], None)


@pytest.mark.parametrize(
    "mutation, message",
    [
        (lambda document: document["canvas"].update(width=0), "canvas.width"),
        (lambda document: document["regions"][0].update(contour=[[1, 2], [3, 4]]), "at least three"),
        (lambda document: document["regions"][0].update(contour=[[1, 2], [3, 4], [math.inf, 6]]), "finite"),
        (lambda document: document["regions"].append({**document["regions"][0]}), "unique"),
    ],
)
def test_validate_regions_document_rejects_invalid_geometry(mutation, message):
    document = json.loads(json.dumps(REGIONS))
    mutation(document)

    with pytest.raises(EditorError, match=message):
        validate_regions_document(document)


def test_save_review_preserves_proposal_and_writes_review_artifacts(tmp_path):
    session = make_run(tmp_path)
    original = session.regions_path.read_bytes()

    result = save_review(session, REGIONS, CORRECTIONS)

    assert session.regions_path.read_bytes() == original
    edited_path = session.regions_path.parent / "stage-2-regions.edited.json"
    corrections_path = session.regions_path.parent / "stage-2-human-corrections.json"
    assert json.loads(edited_path.read_text()) == REGIONS
    assert json.loads(corrections_path.read_text()) == CORRECTIONS
    assert result["regionsPath"].endswith("stage-2-regions.edited.json")
    assert result["correctionsPath"].endswith("stage-2-human-corrections.json")


@contextmanager
def running_server(session, workbench_service=None, job_outcome_root=None):
    server = create_server(
        session,
        "127.0.0.1",
        0,
        workbench_service=workbench_service,
        job_outcome_root=job_outcome_root,
        public_job_error_types=(FakeWorkbenchError,)
        if workbench_service is not None
        else (),
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def read_json(url: str):
    with urlopen(url) as response:
        return response.status, json.load(response)


def _post_json(url: str, payload: object):
    request = Request(
        url,
        data=json.dumps(payload).encode(),
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    with urlopen(request) as response:
        return response.status, json.load(response)


def _raw_request(
    base: str,
    method: str,
    path: str,
    *,
    body: bytes | None = None,
    headers: dict[str, str] | None = None,
) -> tuple[int, dict[str, object]]:
    target = urlsplit(base)
    connection = HTTPConnection(target.hostname, target.port)
    try:
        connection.request(method, path, body=body, headers=headers or {})
        response = connection.getresponse()
        return response.status, json.loads(response.read())
    finally:
        connection.close()


def _poll_job(base: str, job_id: str):
    for _ in range(100):
        _status, payload = read_json(base + f"/api/jobs/{job_id}")
        job = payload["job"]
        if job["state"] in {"succeeded", "failed"}:
            return job
    pytest.fail("fake deterministic job did not finish within bounded polls")


def _create_board(base: str):
    status, created = _post_json(
        base + "/api/boards",
        {
            "productName": "Example Board",
            "source": "https://example.test/board.png",
        },
    )
    assert status == 202
    final = _poll_job(base, created["jobId"])
    assert final["state"] == "succeeded"
    return final["result"]


def _post_mutation(base: str, route: str, view: dict, **extra):
    checkpoint = (
        {"expectedCheckpointToken": view["checkpointToken"]}
        if view.get("checkpointToken") is not None
        else {}
    )
    status, submitted = _post_json(
        base + route,
        {
            "boardId": view["boardId"],
            "expectedRevisionId": view["revisionId"],
            "expectedStage": view["stage"],
            **checkpoint,
            **extra,
        },
    )
    assert status == 202
    final = _poll_job(base, submitted["jobId"])
    assert final["state"] == "succeeded"
    return final["result"]


@pytest.fixture
def running_workbench_server(tmp_path):
    service = FakeWorkbenchService(tmp_path / "workbench")
    with running_server(make_run(tmp_path / "legacy"), service) as base:
        yield base


@pytest.mark.parametrize(
    "asset",
    ["workbench-client.js", "workbench-controller.js", "workbench-model.js", "vector-path-model.js"],
)
def test_server_serves_guided_browser_modules(running_workbench_server, asset):
    with urlopen(running_workbench_server + f"/{asset}") as response:
        assert response.status == 200
        assert response.headers.get_content_type() == "text/javascript"
        assert response.read()


def test_reads_reject_foreign_or_wrong_port_hosts_and_accept_loopback_authorities(
    running_workbench_server,
):
    port = urlsplit(running_workbench_server).port
    assert port is not None

    for host in (f"127.0.0.1:{port}", f"localhost:{port}", f"[::1]:{port}"):
        status, payload = _raw_request(
            running_workbench_server,
            "GET",
            "/api/boards",
            headers={"Host": host},
        )
        assert status == 200
        assert payload["ok"] is True

    for host in ("attacker.example", f"127.0.0.1:{port + 1}"):
        status, payload = _raw_request(
            running_workbench_server,
            "GET",
            "/api/boards",
            headers={"Host": host},
        )
        assert status == 403
        assert payload == {"ok": False, "error": "request origin is not allowed"}


def test_mutations_reject_foreign_or_missing_browser_origins_but_allow_local_ui_and_cli(
    running_workbench_server,
):
    body = json.dumps({
        "productName": "Origin Board",
        "source": "https://example.test/board.png",
    }).encode()
    common = {"Content-Type": "application/json"}

    for headers in (
        {**common, "Origin": "https://attacker.example"},
        {**common, "Origin": "null"},
        {**common, "Sec-Fetch-Site": "same-origin"},
    ):
        status, payload = _raw_request(
            running_workbench_server,
            "POST",
            "/api/boards",
            body=body,
            headers=headers,
        )
        assert status == 403
        assert payload == {"ok": False, "error": "request origin is not allowed"}

    browser_status, browser_payload = _raw_request(
        running_workbench_server,
        "POST",
        "/api/boards",
        body=body,
        headers={**common, "Origin": running_workbench_server},
    )
    cli_status, cli_payload = _raw_request(
        running_workbench_server,
        "POST",
        "/api/boards",
        body=body,
        headers=common,
    )

    assert browser_status == cli_status == 202
    assert browser_payload["ok"] is cli_payload["ok"] is True


def test_create_url_run_returns_job_and_can_be_polled(running_workbench_server):
    status, created = _post_json(
        running_workbench_server + "/api/boards",
        {
            "productName": "Example Board",
            "source": "https://example.test/board.png",
        },
    )

    assert status == 202
    first_status, first_poll = read_json(
        running_workbench_server + f"/api/jobs/{created['jobId']}"
    )
    final = _poll_job(running_workbench_server, created["jobId"])

    assert first_status == 200
    assert first_poll["job"]["id"] == created["jobId"]
    assert final["state"] == "succeeded"
    assert final["result"]["productName"] == "Example Board"
    assert "runRoot" not in final["result"]


def test_completed_creation_job_reconciles_after_server_restart(tmp_path):
    service = FakeWorkbenchService(tmp_path / "workbench")
    session = make_run(tmp_path / "legacy")
    outcome_root = tmp_path / "job-outcomes"
    with running_server(session, service, outcome_root) as base:
        status, submitted = _post_json(
            base + "/api/boards",
            {
                "productName": "Restarted Board",
                "source": "https://example.test/restarted.png",
            },
        )
        completed = _poll_job(base, submitted["jobId"])

    with running_server(session, service, outcome_root) as restarted:
        recovered_status, recovered = read_json(
            restarted + f"/api/jobs/{submitted['jobId']}"
        )

    assert status == 202
    assert recovered_status == 200
    assert recovered["job"] == completed
    assert recovered["job"]["result"]["boardId"] == "board-1"


def test_create_upload_accepts_only_bounded_images(running_workbench_server):
    query = urlencode({"productName": "Uploaded Board"})
    request = Request(
        running_workbench_server + f"/api/boards/upload?{query}",
        data=b"uploaded-image",
        method="POST",
        headers={"Content-Type": "image/png"},
    )

    with urlopen(request) as response:
        status = response.status
        submitted = json.load(response)
    final = _poll_job(running_workbench_server, submitted["jobId"])

    assert status == 202
    assert final["result"]["productName"] == "Uploaded Board"

    invalid = Request(
        running_workbench_server + f"/api/boards/upload?{query}",
        data=b"not-an-image",
        method="POST",
        headers={"Content-Type": "application/octet-stream"},
    )
    with pytest.raises(HTTPError) as error:
        urlopen(invalid)
    assert error.value.code == 415
    assert json.load(error.value) == {
        "ok": False,
        "error": "Content-Type must be image/*",
    }


def test_import_run_returns_a_pollable_job(tmp_path):
    service = FakeWorkbenchService(tmp_path / "workbench")
    imported_run = tmp_path / "CLI Imported Board"
    imported_run.mkdir()
    with running_server(make_run(tmp_path / "legacy"), service) as base:
        status, submitted = _post_json(
            base + "/api/boards/import",
            {"runRoot": str(imported_run)},
        )
        final = _poll_job(base, submitted["jobId"])

    assert status == 202
    assert final["state"] == "succeeded"
    assert final["result"]["productName"] == "CLI Imported Board"


def test_get_library_lists_validated_repository_boards(tmp_path):
    service = FakeWorkbenchService(tmp_path / "workbench")
    with running_server(make_run(tmp_path / "legacy"), service) as base:
        status, payload = _raw_request(base, "GET", "/api/library")

    assert status == 200
    assert payload == {
        "ok": True,
        "boards": [
            {
                "boardId": "example-board",
                "displayName": "Example Board",
                "currentVersionId": "revision-0001",
            }
        ],
    }


def test_post_library_open_is_a_tracked_board_job(tmp_path):
    service = FakeWorkbenchService(tmp_path / "workbench")
    with running_server(make_run(tmp_path / "legacy"), service) as base:
        status, accepted = _raw_request(
            base,
            "POST",
            "/api/library/example-board/open",
            body=b"{}",
            headers={"Content-Type": "application/json"},
        )
        terminal = _poll_job(base, accepted["jobId"])

    assert status == 202
    assert terminal["state"] == "succeeded"
    assert terminal["result"]["repositoryBoardId"] == "example-board"
    assert terminal["result"]["repositoryVersionId"] == "revision-0001"


def test_library_unknown_board_returns_not_found(tmp_path):
    service = FakeWorkbenchService(tmp_path / "workbench")
    with running_server(make_run(tmp_path / "legacy"), service) as base:
        status, payload = _raw_request(
            base,
            "POST",
            "/api/library/missing-board/open",
            body=b"{}",
            headers={"Content-Type": "application/json"},
        )

    assert status == 404
    assert payload == {"ok": False, "error": "board does not exist: missing-board"}


def test_library_rejects_invalid_catalog_data(tmp_path):
    service = FakeWorkbenchService(tmp_path / "workbench")
    service.library_error = FakeWorkbenchError("catalog board is malformed")
    with running_server(make_run(tmp_path / "legacy"), service) as base:
        status, payload = _raw_request(base, "GET", "/api/library")

    assert status == 400
    assert payload == {"ok": False, "error": "catalog board is malformed"}


def test_library_open_retains_loopback_origin_protection(tmp_path):
    service = FakeWorkbenchService(tmp_path / "workbench")
    with running_server(make_run(tmp_path / "legacy"), service) as base:
        for headers in (
            {
                "Content-Type": "application/json",
                "Origin": "https://attacker.example",
            },
            {"Content-Type": "application/json", "Host": "attacker.example"},
        ):
            status, payload = _raw_request(
                base,
                "POST",
                "/api/library/example-board/open",
                body=b"{}",
                headers=headers,
            )

            assert status == 403
            assert payload == {"ok": False, "error": "request origin is not allowed"}


def test_list_and_get_workbench_boards_return_safe_views(running_workbench_server):
    created = _create_board(running_workbench_server)

    list_status, listed = read_json(running_workbench_server + "/api/boards")
    get_status, selected = read_json(
        running_workbench_server + f"/api/boards/{created['boardId']}"
    )

    assert list_status == get_status == 200
    assert listed["boards"] == [created]
    assert selected["board"] == created
    assert str(Path.home()) not in json.dumps(listed)


def test_editable_board_api_exposes_clean_and_annotated_artifacts_separately(
    running_workbench_server,
):
    view = _create_board(running_workbench_server)
    view = _post_mutation(running_workbench_server, "/api/approve", view)
    view = _post_mutation(running_workbench_server, "/api/approve", view)

    assert view["stage"] == 2
    assert view["editorImageUrl"] != view["reviewUrl"]
    with urlopen(running_workbench_server + view["editorImageUrl"]) as response:
        assert response.read() == b"clean-canvas-image"


def test_draft_approve_retry_and_revise_routes_preserve_optimistic_context(
    running_workbench_server,
):
    view = _create_board(running_workbench_server)
    view = _post_mutation(running_workbench_server, "/api/approve", view)
    view = _post_mutation(running_workbench_server, "/api/approve", view)
    drafted = _post_mutation(
        running_workbench_server,
        "/api/drafts",
        view,
        document={"regions": []},
    )
    retried = _post_mutation(running_workbench_server, "/api/retry", drafted)
    revised = _post_mutation(running_workbench_server, "/api/revise", retried)

    assert drafted["stage"] == 2
    assert retried["revisionId"] == drafted["revisionId"]
    assert revised["parentRevisionId"] == retried["revisionId"]
    assert revised["revisionId"].endswith("-revised")


def test_final_save_returns_saved_revision(running_workbench_server):
    view = _create_board(running_workbench_server)
    for _ in range(5):
        view = _post_mutation(running_workbench_server, "/api/approve", view)

    saved = _post_mutation(
        running_workbench_server, "/api/final-save", view
    )

    assert view["state"] == "complete"
    assert saved["saved"] is True


@pytest.mark.parametrize(
    "route, extra",
    [
        ("/api/drafts", {"document": {}}),
        ("/api/approve", {}),
        ("/api/revise", {}),
        ("/api/retry", {}),
    ],
)
def test_workbench_mutations_require_optimistic_fields(
    running_workbench_server, route, extra
):
    for omitted in ("expectedRevisionId", "expectedStage"):
        payload = {
            "boardId": "board-1",
            "expectedRevisionId": "revision-1",
            "expectedStage": 0,
            "expectedCheckpointToken": "checkpoint-0-attempt-1",
            **extra,
        }
        payload.pop(omitted)

        with pytest.raises(HTTPError) as error:
            _post_json(running_workbench_server + route, payload)

        assert error.value.code == 400
        body = json.load(error.value)
        assert body["ok"] is False
        assert omitted in body["error"]


@pytest.mark.parametrize("route", ["/api/drafts", "/api/approve"])
def test_draft_and_approval_mutations_require_checkpoint_identity(
    running_workbench_server, route
):
    payload = {
        "boardId": "board-1",
        "expectedRevisionId": "revision-1",
        "expectedStage": 2,
    }
    if route == "/api/drafts":
        payload["document"] = {"regions": []}

    with pytest.raises(HTTPError) as error:
        _post_json(running_workbench_server + route, payload)

    assert error.value.code == 400
    body = json.load(error.value)
    assert body["ok"] is False
    assert "expectedCheckpointToken" in body["error"]


def test_final_save_requires_expected_revision(running_workbench_server):
    with pytest.raises(HTTPError) as error:
        _post_json(
            running_workbench_server + "/api/final-save",
            {"boardId": "board-1", "expectedStage": 4},
        )

    assert error.value.code == 400
    assert "expectedRevisionId" in json.load(error.value)["error"]


def test_second_http_mutation_for_same_board_returns_conflict(tmp_path):
    service = FakeWorkbenchService(tmp_path / "workbench")
    service.approve_gate = Event()
    with running_server(make_run(tmp_path / "legacy"), service) as base:
        view = _create_board(base)
        status, first = _post_json(
            base + "/api/approve",
            {
                "boardId": view["boardId"],
                "expectedRevisionId": view["revisionId"],
                "expectedStage": view["stage"],
                "expectedCheckpointToken": view["checkpointToken"],
            },
        )
        assert status == 202
        assert service.approve_started.wait(1)

        with pytest.raises(HTTPError) as conflict:
            _post_json(
                base + "/api/retry",
                {
                    "boardId": view["boardId"],
                    "expectedRevisionId": view["revisionId"],
                    "expectedStage": view["stage"],
                },
            )
        service.approve_gate.set()
        assert _poll_job(base, first["jobId"])["state"] == "succeeded"

    assert conflict.value.code == 409
    assert json.load(conflict.value)["ok"] is False


def test_independent_board_creation_jobs_run_concurrently(tmp_path):
    service = RaceRevealingCreationService(tmp_path / "workbench")
    imported_run = tmp_path / "imported-run"
    imported_run.mkdir()
    with running_server(make_run(tmp_path / "legacy"), service) as base:
        status, first = _post_json(
            base + "/api/boards",
            {
                "productName": "First Board",
                "source": "https://example.test/first.png",
            },
        )
        assert status == 202
        assert service.creation_started.wait(1)
        upload = Request(
            base
            + "/api/boards/upload?"
            + urlencode({"productName": "Second Board"}),
            data=b"second-image",
            method="POST",
            headers={"Content-Type": "image/png"},
        )
        with urlopen(upload) as response:
            assert response.status == 202
            second = json.load(response)
        third_status, third = _post_json(
            base + "/api/boards/import",
            {"runRoot": str(imported_run)},
        )
        assert third_status == 202
        service.creation_release.set()
        finals = [
            _poll_job(base, job_id)["state"]
            for job_id in (first["jobId"], second["jobId"], third["jobId"])
        ]

    assert finals == ["succeeded", "succeeded", "succeeded"]
    assert service.overlapped is True


def test_failed_job_poll_exposes_safe_error_without_traceback(
    running_workbench_server,
):
    view = _create_board(running_workbench_server)
    status, submitted = _post_json(
        running_workbench_server + "/api/approve",
        {
            "boardId": view["boardId"],
            "expectedRevisionId": "revision-stale",
            "expectedStage": view["stage"],
            "expectedCheckpointToken": view["checkpointToken"],
        },
    )

    final = _poll_job(running_workbench_server, submitted["jobId"])

    assert status == 202
    assert final["state"] == "failed"
    assert final["error"] == "expected revision does not match"
    assert "Traceback" not in json.dumps(final)


def test_geometry_job_error_retains_actionable_region_without_paths(tmp_path):
    service = GeometryFailWorkbenchService(tmp_path / "workbench")
    with running_server(make_run(tmp_path / "legacy"), service) as base:
        view = _create_board(base)
        _status, submitted = _post_json(
            base + "/api/approve",
            {
                "boardId": view["boardId"],
                "expectedRevisionId": view["revisionId"],
                "expectedStage": view["stage"],
                "expectedCheckpointToken": view["checkpointToken"],
            },
        )
        final = _poll_job(base, submitted["jobId"])

    assert final["state"] == "failed"
    assert final["error"] == "Stage 2 region 17: contour is invalid"
    assert str(tmp_path) not in json.dumps(final)


def test_synchronous_board_gets_redact_untrusted_value_errors(tmp_path):
    service = PathLeakingGetService(tmp_path / "workbench-private")
    with running_server(make_run(tmp_path / "legacy"), service) as base:
        with pytest.raises(HTTPError) as error:
            urlopen(base + "/api/boards")

    assert error.value.code == 500
    assert json.load(error.value) == {"ok": False, "error": "request failed"}
    assert str(tmp_path) not in str(error.value)


def test_job_poll_redacts_path_from_untrusted_value_error(tmp_path):
    service = PathLeakingWorkbenchService(tmp_path / "workbench-private")
    with running_server(make_run(tmp_path / "legacy"), service) as base:
        view = _create_board(base)
        status, submitted = _post_json(
            base + "/api/approve",
            {
                "boardId": view["boardId"],
                "expectedRevisionId": view["revisionId"],
                "expectedStage": view["stage"],
                "expectedCheckpointToken": view["checkpointToken"],
            },
        )
        final = _poll_job(base, submitted["jobId"])

    assert status == 202
    assert final["state"] == "failed"
    assert final["error"] == "job failed"
    assert str(tmp_path) not in json.dumps(final)


def test_workbench_request_limits_are_enforced(running_workbench_server):
    oversized = Request(
        running_workbench_server + "/api/boards",
        data=b"{}",
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Content-Length": str(10 * 1024 * 1024 + 1),
        },
    )
    with pytest.raises(HTTPError) as too_large:
        urlopen(oversized)

    oversized_upload = Request(
        running_workbench_server
        + "/api/boards/upload?"
        + urlencode({"productName": "Too Large"}),
        data=b"x",
        method="POST",
        headers={
            "Content-Type": "image/png",
            "Content-Length": str(10 * 1024 * 1024 + 1),
        },
    )
    with pytest.raises(HTTPError) as upload_too_large:
        urlopen(oversized_upload)

    wrong_type = Request(
        running_workbench_server + "/api/boards",
        data=b"{}",
        method="POST",
        headers={"Content-Type": "text/plain"},
    )
    with pytest.raises(HTTPError) as unsupported:
        urlopen(wrong_type)

    assert too_large.value.code == 413
    assert upload_too_large.value.code == 413
    assert unsupported.value.code == 415
    assert json.load(too_large.value)["ok"] is False
    assert json.load(upload_too_large.value)["ok"] is False
    assert json.load(unsupported.value)["ok"] is False


def test_artifact_endpoint_serves_only_selected_revision(
    running_workbench_server,
):
    view = _create_board(running_workbench_server)

    with urlopen(running_workbench_server + view["reviewUrl"]) as response:
        content = response.read()

    assert content == b"https://example.test/board.png"


def test_artifact_endpoint_rejects_paths_outside_revision(
    running_workbench_server,
):
    with pytest.raises(HTTPError) as error:
        urlopen(running_workbench_server + "/api/artifact?path=../../secret")

    assert error.value.code == 400
    assert json.load(error.value)["ok"] is False


def test_artifact_endpoint_returns_safe_json_for_a_cyclic_symlink(tmp_path):
    service = FakeWorkbenchService(tmp_path / "workbench")
    with running_server(make_run(tmp_path / "legacy"), service) as base:
        view = _create_board(base)
        run_root = service.get_board(view["boardId"]).run_root
        (run_root / "loop").symlink_to("loop")
        query = urlencode(
            {
                "boardId": view["boardId"],
                "revisionId": view["revisionId"],
                "path": "loop",
            }
        )
        with pytest.raises(HTTPError) as error:
            urlopen(base + f"/api/artifact?{query}")

    assert error.value.code == 404
    assert json.load(error.value) == {"ok": False, "error": "artifact not found"}


def test_unknown_job_returns_consistent_json_error(running_workbench_server):
    with pytest.raises(HTTPError) as error:
        urlopen(running_workbench_server + "/api/jobs/missing")

    assert error.value.code == 404
    assert json.load(error.value) == {"ok": False, "error": "unknown job: missing"}


@pytest.mark.filterwarnings(
    "ignore:urllib3 .* doesn't match a supported version!"
)
def test_workspace_root_startup_constructs_real_empty_workbench(tmp_path):
    workspace = tmp_path / "workspace"
    server, catalog = server_module._server_from_cli(
        ["--workspace-root", str(workspace), "--port", "0"]
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        status, payload = read_json(
            f"http://127.0.0.1:{server.server_port}/api/boards"
        )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

    assert catalog is None
    assert server.server_address[0] == "127.0.0.1"
    assert status == 200
    assert payload == {"ok": True, "boards": []}
    assert (workspace / "boards").is_dir()
    assert (workspace / ".workbench-job-outcomes").is_dir()


@pytest.mark.filterwarnings(
    "ignore:urllib3 .* doesn't match a supported version!"
)
def test_repository_root_constructs_library_backed_workbench(tmp_path):
    repository = tmp_path / "repository"
    (repository / ".git").mkdir(parents=True)
    library = repository / "Tools" / "HangboardOnboarding" / "board-library"
    library.mkdir(parents=True)
    (library / "catalog.json").write_text('{"schemaVersion":1,"boards":[]}')
    workspace = tmp_path / "workspace"

    server, catalog = server_module._server_from_cli(
        [
            "--repository-root",
            str(repository),
            "--workspace-root",
            str(workspace),
            "--port",
            "0",
        ]
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        status, payload = read_json(
            f"http://127.0.0.1:{server.server_port}/api/library"
        )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

    assert catalog is None
    assert status == 200
    assert payload == {"ok": True, "boards": []}
    assert (workspace / "boards").is_dir()


@pytest.mark.filterwarnings(
    "ignore:urllib3 .* doesn't match a supported version!"
)
def test_repository_catalog_validation_errors_are_safe_bad_requests(tmp_path):
    repository = tmp_path / "repository"
    (repository / ".git").mkdir(parents=True)
    library = repository / "Tools" / "HangboardOnboarding" / "board-library"
    library.mkdir(parents=True)
    (library / "catalog.json").write_text('{"schemaVersion":99,"boards":[]}')

    server, _catalog = server_module._server_from_cli(
        ["--repository-root", str(repository), "--workspace-root", str(tmp_path / "workspace"), "--port", "0"]
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        status, payload = _raw_request(
            f"http://127.0.0.1:{server.server_port}", "GET", "/api/library"
        )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

    assert status == 400
    assert payload == {"ok": False, "error": "unsupported catalog schema version"}


@pytest.mark.filterwarnings(
    "ignore:urllib3 .* doesn't match a supported version!"
)
def test_checkout_launch_discovers_nearest_repository_and_default_workspace(
    tmp_path, monkeypatch
):
    repository = tmp_path / "repository"
    (repository / ".git").mkdir(parents=True)
    library = repository / "Tools" / "HangboardOnboarding" / "board-library"
    library.mkdir(parents=True)
    (library / "catalog.json").write_text('{"schemaVersion":1,"boards":[]}')
    launch_directory = repository / "nested" / "checkout"
    launch_directory.mkdir(parents=True)
    monkeypatch.chdir(launch_directory)

    server, catalog = server_module._server_from_cli(["--port", "0"])
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        status, payload = read_json(
            f"http://127.0.0.1:{server.server_port}/api/library"
        )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

    assert catalog is None
    assert status == 200
    assert payload == {"ok": True, "boards": []}
    assert (repository / ".context" / "hangboard-workbench" / "boards").is_dir()


def test_default_launch_fails_clearly_without_a_repository(tmp_path, monkeypatch, capsys):
    launch_directory = tmp_path / "not-a-checkout"
    launch_directory.mkdir()
    monkeypatch.chdir(launch_directory)

    with pytest.raises(SystemExit) as error:
        server_module._server_from_cli(["--port", "0"])

    assert error.value.code == 2
    assert "could not find a repository root" in capsys.readouterr().err


def test_http_session_loads_only_explicit_artifacts(tmp_path):
    session = make_run(tmp_path)
    (tmp_path / "secret.txt").write_text("not served")

    with running_server(session) as base:
        status, payload = read_json(base + "/api/session")
        assert status == 200
        assert payload["imageUrl"] == "/api/artifact/image"
        assert payload["regionsUrl"] == "/api/artifact/regions"
        with urlopen(base + payload["regionsUrl"]) as response:
            assert json.load(response) == REGIONS
        with pytest.raises(HTTPError) as unknown:
            urlopen(base + "/api/artifact/../../secret.txt")
        assert unknown.value.code == 404


def test_http_sessions_lists_catalog_without_filesystem_paths(tmp_path):
    first = make_run(tmp_path / "first")
    second = make_run(tmp_path / "second")
    catalog = EditorCatalog.from_sessions([("Beastmaker", first), ("Simulator 3D", second)])

    with running_server(catalog) as base:
        status, payload = read_json(base + "/api/sessions")

    assert status == 200
    assert payload == {
        "ok": True,
        "sessions": [
            {"id": "run-1", "label": "Beastmaker", "runName": "first"},
            {"id": "run-2", "label": "Simulator 3D", "runName": "second"},
        ],
    }
    assert str(tmp_path) not in json.dumps(payload)


def test_http_artifacts_are_selected_by_run_id(tmp_path):
    first = make_run(tmp_path / "first")
    second = make_run(tmp_path / "second")
    first.image_path.write_bytes(b"first-image")
    second.image_path.write_bytes(b"second-image")
    catalog = EditorCatalog.from_sessions([("First", first), ("Second", second)])

    with running_server(catalog) as base:
        status, session = read_json(base + "/api/session?run=run-2")
        with urlopen(base + session["imageUrl"]) as response:
            image = response.read()

    assert status == 200
    assert session["id"] == "run-2"
    assert session["label"] == "Second"
    assert session["saveUrl"] == "/api/save?run=run-2"
    assert image == b"second-image"


def test_http_unknown_run_returns_404(tmp_path):
    catalog = EditorCatalog.from_sessions([("Board", make_run(tmp_path))])

    with running_server(catalog) as base:
        with pytest.raises(HTTPError) as error:
            urlopen(base + "/api/session?run=run-99")

    assert error.value.code == 404
    assert "unknown run" in json.load(error.value)["error"]


def test_http_save_writes_both_review_documents(tmp_path):
    session = make_run(tmp_path)
    with running_server(session) as base:
        request = Request(
            base + "/api/save",
            data=json.dumps({"regions": REGIONS, "corrections": CORRECTIONS}).encode(),
            method="PUT",
            headers={"Content-Type": "application/json"},
        )
        with urlopen(request) as response:
            result = json.load(response)

    assert result["ok"] is True
    assert (session.regions_path.parent / "stage-2-regions.edited.json").exists()
    assert (session.regions_path.parent / "stage-2-human-corrections.json").exists()


def test_http_save_routes_to_selected_run(tmp_path):
    first = make_run(tmp_path / "first")
    second = make_run(tmp_path / "second")
    catalog = EditorCatalog.from_sessions([("First", first), ("Second", second)])
    with running_server(catalog) as base:
        request = Request(
            base + "/api/save?run=run-2",
            data=json.dumps({"regions": REGIONS, "corrections": CORRECTIONS}).encode(),
            method="PUT",
            headers={"Content-Type": "application/json"},
        )
        with urlopen(request) as response:
            assert json.load(response)["ok"] is True

    assert not (first.regions_path.parent / "stage-2-regions.edited.json").exists()
    assert (second.regions_path.parent / "stage-2-regions.edited.json").exists()


@pytest.mark.parametrize(
    "body, headers, expected",
    [
        (b"not-json", {"Content-Type": "application/json"}, 400),
        (b"{}", {"Content-Type": "text/plain"}, 415),
        (b"{}", {"Content-Type": "application/json", "Content-Length": str(10 * 1024 * 1024 + 1)}, 413),
    ],
)
def test_http_save_rejects_invalid_requests(tmp_path, body, headers, expected):
    session = make_run(tmp_path)
    with running_server(session) as base:
        request = Request(base + "/api/save", data=body, method="PUT", headers=headers)
        with pytest.raises(HTTPError) as error:
            urlopen(request)
        assert error.value.code == expected


def test_http_unknown_route_returns_json_404(tmp_path):
    session = make_run(tmp_path)
    with running_server(session) as base:
        with pytest.raises(HTTPError) as error:
            urlopen(base + "/api/nope")
        assert error.value.code == 404
        assert json.load(error.value)["ok"] is False
