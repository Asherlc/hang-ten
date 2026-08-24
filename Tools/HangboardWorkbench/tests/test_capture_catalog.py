from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

WORKBENCH_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WORKBENCH_ROOT))

import capture_catalog  # noqa: E402


class _Response:
    def __init__(self, payload: object) -> None:
        self._payload = payload

    def __enter__(self) -> "_Response":
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def read(self) -> bytes:
        return json.dumps(self._payload).encode("utf-8")


def test_catalog_order_comes_from_boards_api(monkeypatch: pytest.MonkeyPatch) -> None:
    requested: list[str] = []

    def open_url(request: object, *, timeout: float) -> _Response:
        requested.append(request.full_url)
        return _Response(
            {
                "ok": True,
                "boards": [
                    {"boardId": "zeta.board", "displayName": "Zeta"},
                    {"boardId": "alpha.board", "displayName": "Alpha"},
                ],
            }
        )

    monkeypatch.setattr(capture_catalog.urllib.request, "urlopen", open_url)

    assert capture_catalog.fetch_catalog("http://127.0.0.1:4173") == (
        capture_catalog.CatalogBoard("zeta.board", "Zeta"),
        capture_catalog.CatalogBoard("alpha.board", "Alpha"),
    )
    assert requested == ["http://127.0.0.1:4173/api/boards"]


def test_capture_readiness_requires_expected_primary_image_and_exact_region_count() -> None:
    assert not capture_catalog.capture_is_ready(
        {"primaryImageLoaded": False, "imageURL": "http://capture.test/api/boards/second/image", "regionCount": 2},
        expected_image_url="http://capture.test/api/boards/second/image",
        expected_region_count=2,
    )
    assert not capture_catalog.capture_is_ready(
        {"primaryImageLoaded": True, "imageURL": "http://capture.test/api/boards/second/image", "regionCount": 1},
        expected_image_url="http://capture.test/api/boards/second/image",
        expected_region_count=2,
    )
    assert capture_catalog.capture_is_ready(
        {"primaryImageLoaded": True, "imageURL": "http://capture.test/api/boards/second/image", "regionCount": 2},
        expected_image_url="http://capture.test/api/boards/second/image",
        expected_region_count=2,
    )


def test_capture_readiness_rejects_prior_board_with_the_same_region_count() -> None:
    assert not capture_catalog.capture_is_ready(
        {"primaryImageLoaded": True, "imageURL": "http://capture.test/api/boards/first/image", "regionCount": 2},
        expected_image_url="http://capture.test/api/boards/second/image",
        expected_region_count=2,
    )


def test_catalog_controls_wait_for_every_api_board_before_clicking() -> None:
    assert not capture_catalog.catalog_controls_are_ready({"boardButtonCount": 1}, expected_count=2)
    assert capture_catalog.catalog_controls_are_ready({"boardButtonCount": 2}, expected_count=2)


def test_devtools_uses_a_page_target_not_chrome_profile_ui() -> None:
    targets = [
        {"type": "browser_ui", "webSocketDebuggerUrl": "ws://profile"},
        {"type": "page", "webSocketDebuggerUrl": "ws://capture"},
    ]

    assert capture_catalog.page_websocket_url(targets) == "ws://capture"


def test_capture_failure_identifies_its_stage_and_board() -> None:
    error = capture_catalog.CaptureError("readiness", "timed out", board_id="fixture.board")

    assert str(error) == "readiness fixture.board: timed out"


@pytest.mark.parametrize(
    ("board_id", "safe_stem"),
    [
        ("synthetic.board-alpha", "synthetic.board-alpha"),
        ("Board / Needs Review", "board-needs-review"),
        ("../../escape", "escape"),
    ],
)
def test_capture_filenames_are_derived_from_safe_board_ids(
    board_id: str, safe_stem: str
) -> None:
    filename = capture_catalog.capture_filename(board_id)

    assert filename.startswith(f"{safe_stem}--")
    assert filename.endswith(".png")
    assert "/" not in filename


def test_capture_filenames_distinguish_ids_that_normalize_to_the_same_stem() -> None:
    assert capture_catalog.capture_filename("a_b") != capture_catalog.capture_filename("a-b")


def test_contact_sheet_contains_every_manifest_entry(tmp_path: Path) -> None:
    from PIL import Image

    output = tmp_path / "captures"
    output.mkdir()
    Image.new("RGB", (24, 16), "red").save(output / "first-board.png")
    Image.new("RGB", (24, 16), "blue").save(output / "second-board.png")
    manifest = capture_catalog.CaptureManifest(
        entries=(
            capture_catalog.CaptureEntry("first.board", "First", 2, "first-board.png"),
            capture_catalog.CaptureEntry("second.board", "Second", 3, "second-board.png"),
        )
    )

    sheet = capture_catalog.create_contact_sheet(output, manifest)

    assert sheet.name == "contact-sheet.png"
    assert sheet.is_file()
    assert capture_catalog.contact_sheet_entries(sheet) == (
        "first.board",
        "second.board",
    )


def test_capture_command_accepts_explicit_repository_output_and_chrome_paths() -> None:
    arguments = capture_catalog.argument_parser().parse_args(
        [
            "--repository-root",
            "/checkout",
            "--output-root",
            "/captures",
            "--chrome-path",
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "--port",
            "4183",
        ]
    )

    assert arguments.repository_root == Path("/checkout")
    assert arguments.output_root == Path("/captures")
    assert arguments.chrome_path.name == "Google Chrome"
    assert arguments.port == 4183


def test_capture_uses_its_dedicated_local_only_server_launcher() -> None:
    repository_root = Path("/checkout")

    assert capture_catalog._capture_server_command(repository_root, 4183) == [
        "python3",
        "/checkout/Tools/HangboardWorkbench/capture_server.py",
        "--repository-root",
        "/checkout",
        "--port",
        "4183",
    ]
