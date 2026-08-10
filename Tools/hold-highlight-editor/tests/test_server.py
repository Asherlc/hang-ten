from __future__ import annotations

import json
import math
import sys
import threading
from contextlib import contextmanager
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

EDITOR_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(EDITOR_ROOT))

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
def running_server(session):
    server = create_server(session, "127.0.0.1", 0)
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


def test_http_serves_curve_gesture_model_asset(tmp_path):
    session = make_run(tmp_path)

    with running_server(session) as base:
        with urlopen(base + "/curve-gesture-model.js") as response:
            assert response.status == 200
            asset = response.read()

    assert asset == (EDITOR_ROOT / "curve-gesture-model.js").read_bytes()


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
