from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import threading
from contextlib import contextmanager
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest


WORKBENCH_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = WORKBENCH_ROOT.parents[1]
sys.path.insert(0, str(WORKBENCH_ROOT))

from server import create_server, validate_hang_ten_checkout  # noqa: E402


BOARD_ID = "metolius.wood-grips-compact-ii"
SLUG = "metolius-wood-grips-compact-ii"


def _library(tmp_path: Path) -> Path:
    destination = tmp_path / "Hangboards"
    shutil.copytree(
        REPOSITORY_ROOT / "Hangboards",
        destination,
        ignore=shutil.ignore_patterns(".workbench.lock"),
    )
    return destination


@contextmanager
def running_server(library: Path):
    httpd = create_server(library, port=0)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    host, port = httpd.server_address[:2]
    try:
        yield f"http://{host}:{port}"
    finally:
        httpd.shutdown()
        thread.join(timeout=5)
        httpd.server_close()


def request_json(base: str, method: str, path: str, payload: object | None = None):
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    request = Request(
        base + path,
        data=body,
        method=method,
        headers={"Content-Type": "application/json"} if body else {},
    )
    try:
        with urlopen(request) as response:
            return response.status, json.loads(response.read())
    except HTTPError as error:
        return error.code, json.loads(error.read())


def test_lists_and_opens_registered_packages_with_full_editor_document(tmp_path: Path) -> None:
    library = _library(tmp_path)
    with running_server(library) as base:
        status, listed = request_json(base, "GET", "/api/boards")
        assert status == 200
        assert listed["boards"] == [
            {
                "boardId": BOARD_ID,
                "displayName": "Metolius Wood Grips Compact II",
                "holdCount": 19,
                "href": f"/api/boards/{BOARD_ID}",
            }
        ]

        status, opened = request_json(base, "GET", f"/api/boards/{BOARD_ID}")
        assert status == 200
        board = opened["board"]
        assert board["boardId"] == BOARD_ID
        assert board["imageUrl"] == f"/api/boards/{BOARD_ID}/image"
        assert board["saveUrl"] == f"/api/boards/{BOARD_ID}"
        assert board["document"]["canvas"]["width"] > 0
        assert len(board["document"]["regions"]) == 19
        assert all(region["displayPath"].endswith(" Z") for region in board["document"]["regions"])

        with urlopen(base + board["imageUrl"]) as response:
            assert response.status == 200
            assert response.headers["Content-Type"] == "image/png"
            assert response.read(8) == b"\x89PNG\r\n\x1a\n"


def test_save_updates_the_direct_package_and_returns_its_fresh_document(tmp_path: Path) -> None:
    library = _library(tmp_path)
    with running_server(library) as base:
        _status, opened = request_json(base, "GET", f"/api/boards/{BOARD_ID}")
        document = opened["board"]["document"]
        document["regions"][0]["displayPath"] = "M 10 10 L 80 10 L 80 50 L 10 50 Z"

        status, saved = request_json(base, "PUT", f"/api/boards/{BOARD_ID}", document)
        assert status == 200
        assert saved["board"]["document"]["regions"][0]["displayPath"] == document["regions"][0]["displayPath"]

        _status, reloaded = request_json(base, "GET", f"/api/boards/{BOARD_ID}")
        assert reloaded["board"]["document"]["regions"][0]["displayPath"] == document["regions"][0]["displayPath"]


def test_invalid_save_leaves_the_package_and_catalog_unchanged(tmp_path: Path) -> None:
    library = _library(tmp_path)
    package = library / SLUG
    before = {path.relative_to(library): path.read_bytes() for path in [library / "catalog.json", *sorted(package.rglob("*"))] if path.is_file()}
    with running_server(library) as base:
        _status, opened = request_json(base, "GET", f"/api/boards/{BOARD_ID}")
        document = opened["board"]["document"]
        document["regions"][0]["displayPath"] = "M 10 10 L 90 90 L 10 90 L 90 10 Z"
        status, result = request_json(base, "PUT", f"/api/boards/{BOARD_ID}", document)

    assert status == 400
    assert result == {"ok": False, "error": "hold jug-left must not self-intersect"}
    after = {path.relative_to(library): path.read_bytes() for path in [library / "catalog.json", *sorted(package.rglob("*"))] if path.is_file()}
    assert after == before


def test_load_failures_do_not_expose_library_paths(tmp_path: Path) -> None:
    library = _library(tmp_path)
    (library / SLUG / "assets" / "primary.png").unlink()
    with running_server(library) as base:
        status, result = request_json(base, "GET", f"/api/boards/{BOARD_ID}")

    assert status == 400
    assert result == {"ok": False, "error": "could not load board"}
    assert str(library) not in json.dumps(result)


def test_server_imports_without_the_pipeline_path(tmp_path: Path) -> None:
    code = "import server; print(server.__name__)"
    environment = os.environ | {"PYTHONPATH": str(WORKBENCH_ROOT)}
    completed = subprocess.run(
        [sys.executable, "-c", code],
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.strip() == "server"


def test_checkout_validation_requires_only_the_direct_workbench_layout(tmp_path: Path) -> None:
    checkout = tmp_path / "checkout"
    (checkout / ".git").mkdir(parents=True)
    (checkout / "Hangboards").mkdir()
    workbench = checkout / "Tools" / "HangboardWorkbench"
    workbench.mkdir(parents=True)
    (workbench / "server.py").touch()

    assert validate_hang_ten_checkout(checkout) == checkout.resolve()
