from __future__ import annotations

from contextlib import contextmanager
import json
import os
import shutil
import subprocess
import sys
import threading
from pathlib import Path
from typing import Iterator
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
WORKBENCH_ROOT = Path(__file__).resolve().parents[1]
PRIMARY_IMAGE = (
    REPOSITORY_ROOT
    / "Hangboards"
    / "metolius-wood-grips-compact-ii"
    / "assets"
    / "primary.png"
)
sys.path.insert(0, str(WORKBENCH_ROOT))

import board_package  # noqa: E402
import server as server_module  # noqa: E402
from board_package import BoardPackageError  # noqa: E402
from server import EditorError, create_server, validate_hang_ten_checkout  # noqa: E402


def _write_library(root: Path) -> Path:
    library = root / "Hangboards"
    package = library / "fixture-board"
    assets = package / "assets"
    assets.mkdir(parents=True)
    shutil.copyfile(PRIMARY_IMAGE, assets / "primary.png")
    board = {
        "schemaVersion": 1,
        "id": "fixture.board",
        "manufacturer": "Fixture Maker",
        "name": "Fixture Board",
        "subtitle": "A physical fixture board.",
        "productURL": "https://example.com/fixture.board",
        "dimensions": "20 × 10 cm",
        "aspectRatio": 1774 / 457,
        "presentation": {"assetPath": "assets/primary.png"},
        "holds": [
            {
                "id": "hold-left",
                "name": "Left hold",
                "kind": "jug",
                "geometry": [
                    {
                        "frame": {"x": 0.05, "y": 0.2, "width": 0.1, "height": 0.3},
                        "shape": {"type": "roundedRect", "cornerRadiusFraction": 0.2},
                    },
                    {
                        "frame": {"x": 0.35, "y": 0.1, "width": 0.1, "height": 0.2},
                        "shape": {"type": "roundedRect", "cornerRadiusFraction": 0.1},
                        "treatment": {"type": "surface"},
                    },
                ],
            }
        ],
    }
    (package / "board.json").write_text(
        json.dumps(board, indent=2) + "\n", encoding="utf-8"
    )
    return library


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


def test_a_clean_checkout_lists_and_opens_the_migrated_compact_ii_package(
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
    assert [board['boardId'] for board in listed['boards']] == ['metolius.wood-grips-compact-ii']
    opened = json.loads(urlopen(base + listed['boards'][0]['href']).read())
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
