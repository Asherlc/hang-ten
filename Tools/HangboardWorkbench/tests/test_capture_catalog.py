from __future__ import annotations

import json
import signal
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


def test_capture_targets_enumerate_every_presentation_in_api_order(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    requested: list[str] = []
    default_payload = {
        "ok": True,
        "board": {
            "boardId": "fixture.two-sided",
            "displayName": "Fixture Two Sided",
            "selectedPresentationID": "front",
            "imageUrl": "/api/boards/fixture.two-sided/image?presentationID=front",
            "presentations": [
                {
                    "presentationID": "front",
                    "displayName": "Front",
                    "imageUrl": "/api/boards/fixture.two-sided/image?presentationID=front",
                    "default": True,
                },
                {
                    "presentationID": "back-inverted",
                    "displayName": "Back (inverted)",
                    "imageUrl": "/api/boards/fixture.two-sided/image?presentationID=back-inverted",
                    "default": False,
                },
            ],
            "document": {
                "presentationID": "front",
                "regions": [{"key": "front-left"}, {"key": "front-right"}],
            },
        },
    }
    alternate_payload = {
        "ok": True,
        "board": {
            "boardId": "fixture.two-sided",
            "displayName": "Fixture Two Sided",
            "selectedPresentationID": "back-inverted",
            "imageUrl": "/api/boards/fixture.two-sided/image?presentationID=back-inverted",
            "presentations": default_payload["board"]["presentations"],
            "document": {
                "presentationID": "back-inverted",
                "regions": [{"key": "back-center"}],
            },
        },
    }

    def open_url(request: object, *, timeout: float) -> _Response:
        requested.append(request.full_url)
        return _Response(alternate_payload if "presentationID=back-inverted" in request.full_url else default_payload)

    monkeypatch.setattr(capture_catalog.urllib.request, "urlopen", open_url)

    assert capture_catalog.fetch_capture_targets(
        "http://127.0.0.1:4173",
        capture_catalog.CatalogBoard("fixture.two-sided", "Fixture Two Sided"),
    ) == (
        capture_catalog.PresentationCaptureTarget(
            board_id="fixture.two-sided",
            display_name="Fixture Two Sided",
            presentation_id="front",
            presentation_name="Front",
            image_url="http://127.0.0.1:4173/api/boards/fixture.two-sided/image?presentationID=front",
            region_keys=("front-left", "front-right"),
            is_default=True,
        ),
        capture_catalog.PresentationCaptureTarget(
            board_id="fixture.two-sided",
            display_name="Fixture Two Sided",
            presentation_id="back-inverted",
            presentation_name="Back (inverted)",
            image_url="http://127.0.0.1:4173/api/boards/fixture.two-sided/image?presentationID=back-inverted",
            region_keys=("back-center",),
            is_default=False,
        ),
    )
    assert requested == [
        "http://127.0.0.1:4173/api/boards/fixture.two-sided",
        "http://127.0.0.1:4173/api/boards/fixture.two-sided?presentationID=back-inverted",
    ]


def test_capture_readiness_requires_exact_presentation_asset_and_region_keys() -> None:
    assert not capture_catalog.capture_is_ready(
        {
            "primaryImageLoaded": False,
            "imageURL": "http://capture.test/image?presentationID=back",
            "presentationID": "back",
            "regionKeys": ["back-left", "back-right"],
        },
        expected_image_url="http://capture.test/image?presentationID=back",
        expected_presentation_id="back",
        expected_region_keys=("back-left", "back-right"),
    )
    assert not capture_catalog.capture_is_ready(
        {
            "primaryImageLoaded": True,
            "imageURL": "http://capture.test/image?presentationID=back",
            "presentationID": "front",
            "regionKeys": ["back-left", "back-right"],
        },
        expected_image_url="http://capture.test/image?presentationID=back",
        expected_presentation_id="back",
        expected_region_keys=("back-left", "back-right"),
    )
    assert not capture_catalog.capture_is_ready(
        {
            "primaryImageLoaded": True,
            "imageURL": "http://capture.test/image?presentationID=back",
            "presentationID": "back",
            "regionKeys": ["front-left", "front-right"],
        },
        expected_image_url="http://capture.test/image?presentationID=back",
        expected_presentation_id="back",
        expected_region_keys=("back-left", "back-right"),
    )
    assert capture_catalog.capture_is_ready(
        {
            "primaryImageLoaded": True,
            "imageURL": "http://capture.test/image?presentationID=back",
            "presentationID": "back",
            "regionKeys": ["back-left", "back-right"],
        },
        expected_image_url="http://capture.test/image?presentationID=back",
        expected_presentation_id="back",
        expected_region_keys=("back-left", "back-right"),
    )


def test_capture_readiness_image_probe_cannot_outlive_the_outer_deadline() -> None:
    expression = capture_catalog._readiness_expression("http://capture.test/expected.png")

    assert "AbortController" in expression
    assert "clearTimeout" in expression


def test_capture_readiness_does_not_probe_a_stale_presentation_asset() -> None:
    expression = capture_catalog._readiness_expression("http://capture.test/expected.png")

    assert 'const expectedImageURL = "http://capture.test/expected.png"' in expression
    assert "absoluteURL === expectedImageURL" in expression


def test_catalog_controls_wait_for_every_api_board_before_clicking() -> None:
    assert not capture_catalog.catalog_controls_are_ready({"boardButtonCount": 1}, expected_count=2)
    assert capture_catalog.catalog_controls_are_ready({"boardButtonCount": 2}, expected_count=2)


def test_board_selection_waits_until_the_existing_catalog_control_is_enabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    evaluations: list[str] = []
    results = iter((False, True))

    def evaluate(_connection: object, expression: str) -> bool:
        evaluations.append(expression)
        return next(results)

    monkeypatch.setattr(capture_catalog, "_evaluate", evaluate)
    monkeypatch.setattr(capture_catalog.time, "sleep", lambda _seconds: None)

    capture_catalog._select_board(object(), index=7, board_id="fixture.board")

    assert len(evaluations) == 2
    assert all("[7]" in expression and "button.disabled" in expression for expression in evaluations)


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


def test_capture_filenames_distinguish_presentations_of_the_same_board() -> None:
    front = capture_catalog.capture_filename("fixture.board", "front")
    back = capture_catalog.capture_filename("fixture.board", "back/inverted")

    assert front != back
    assert "front" in front
    assert "back-inverted" in back
    assert "/" not in back


def test_capture_identity_is_stable_and_unambiguous_for_a_package_presentation_pair() -> None:
    assert capture_catalog.capture_identity("fixture.board", "back/inverted") == (
        "fixture.board::back/inverted"
    )


def test_default_capture_keeps_legacy_one_presentation_behavior_until_all_is_requested() -> None:
    targets = (
        capture_catalog.PresentationCaptureTarget(
            "fixture.board", "Fixture", "front", "Front", "https://example.test/front", (), True
        ),
        capture_catalog.PresentationCaptureTarget(
            "fixture.board", "Fixture", "back", "Back", "https://example.test/back", (), False
        ),
    )

    assert capture_catalog.capture_targets_for_run(targets, all_presentations=False) == (targets[0],)
    assert capture_catalog.capture_targets_for_run(targets, all_presentations=True) == targets


def test_manifest_records_every_board_presentation_pair(tmp_path: Path) -> None:
    manifest = capture_catalog.CaptureManifest(
        entries=(
            capture_catalog.CaptureEntry(
                "fixture.board", "Fixture", "front", "Front", 2, "front.png"
            ),
            capture_catalog.CaptureEntry(
                "fixture.board", "Fixture", "back", "Back", 1, "back.png"
            ),
        )
    )

    path = manifest.write(tmp_path)

    assert json.loads(path.read_text(encoding="utf-8")) == {
        "boards": [
            {
                "capture_id": "fixture.board::front",
                "board_id": "fixture.board",
                "display_name": "Fixture",
                "presentation_id": "front",
                "presentation_name": "Front",
                "region_count": 2,
                "filename": "front.png",
                "variant": "normal",
            },
            {
                "capture_id": "fixture.board::back",
                "board_id": "fixture.board",
                "display_name": "Fixture",
                "presentation_id": "back",
                "presentation_name": "Back",
                "region_count": 1,
                "filename": "back.png",
                "variant": "normal",
            },
        ]
    }


def test_contact_sheet_contains_every_manifest_entry(tmp_path: Path) -> None:
    from PIL import Image

    output = tmp_path / "captures"
    output.mkdir()
    Image.new("RGB", (24, 16), "red").save(output / "first-board.png")
    Image.new("RGB", (24, 16), "blue").save(output / "second-board.png")
    manifest = capture_catalog.CaptureManifest(
        entries=(
            capture_catalog.CaptureEntry("first.board", "First", "primary", "Primary", 2, "first-board.png"),
            capture_catalog.CaptureEntry("second.board", "Second", "rotated", "Rotated", 3, "second-board.png"),
        )
    )

    sheet = capture_catalog.create_contact_sheet(output, manifest)

    assert sheet.name == "contact-sheet.png"
    assert sheet.is_file()
    assert capture_catalog.contact_sheet_entries(sheet) == (
        ("first.board", "primary"),
        ("second.board", "rotated"),
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
            "--all-presentations",
        ]
    )

    assert arguments.repository_root == Path("/checkout")
    assert arguments.output_root == Path("/captures")
    assert arguments.chrome_path.name == "Google Chrome"
    assert arguments.port == 4183
    assert arguments.all_presentations is True


def test_hold_id_labels_use_the_union_center_for_every_piece_of_one_logical_hold() -> None:
    labels = capture_catalog.hold_id_label_positions(
        (
            capture_catalog.RegionBounds("two-piece-0", "two-piece", 0, 0, 10, 10),
            capture_catalog.RegionBounds("two-piece-1", "two-piece", 20, 10, 10, 10),
        )
    )

    assert labels == (capture_catalog.HoldIDLabel("two-piece", 15, 10),)


def test_hold_id_labels_reject_a_region_without_an_editor_hold_id() -> None:
    with pytest.raises(capture_catalog.CaptureError, match="missing metadata.holdID"):
        capture_catalog.hold_id_label_positions(
            (capture_catalog.RegionBounds("unmapped-piece", None, 0, 0, 10, 10),)
        )


def test_capture_command_accepts_hold_id_labels() -> None:
    arguments = capture_catalog.argument_parser().parse_args(
        [
            "--repository-root",
            "/checkout",
            "--output-root",
            "/captures",
            "--chrome-path",
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "--hold-id-labels",
        ]
    )

    assert arguments.hold_id_labels is True


class _OwnedProcess:
    def __init__(self, pid: int) -> None:
        self.pid = pid
        self.returncode: int | None = None

    def poll(self) -> int | None:
        return self.returncode

    def wait(self, *, timeout: float) -> int:
        self.returncode = -signal.SIGTERM
        return self.returncode


@pytest.mark.parametrize("fail", (False, True), ids=("success", "capture-failure"))
def test_owned_process_group_is_stopped_exactly_on_success_and_capture_failure(
    monkeypatch: pytest.MonkeyPatch, fail: bool
) -> None:
    process = _OwnedProcess(7319)
    popen_calls: list[tuple[list[str], dict[str, object]]] = []
    signals: list[tuple[int, signal.Signals]] = []

    def popen(command: list[str], **kwargs: object) -> _OwnedProcess:
        popen_calls.append((command, kwargs))
        return process

    monkeypatch.setattr(capture_catalog.subprocess, "Popen", popen)
    monkeypatch.setattr(capture_catalog.os, "killpg", lambda pid, sig: signals.append((pid, sig)))

    if fail:
        with pytest.raises(capture_catalog.CaptureError, match="capture failed"):
            with capture_catalog._managed_process(["owned-child"], stage="chrome"):
                raise capture_catalog.CaptureError("capture", "capture failed")
    else:
        with capture_catalog._managed_process(["owned-child"], stage="chrome"):
            pass

    assert popen_calls[0][1]["start_new_session"] is True
    assert signals == [(7319, signal.SIGTERM)]
    assert process.poll() == -signal.SIGTERM


def test_signal_handler_unwinds_and_stops_the_exact_owned_process_group(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    process = _OwnedProcess(8427)
    installed: dict[signal.Signals, object] = {}
    signals: list[tuple[int, signal.Signals]] = []

    monkeypatch.setattr(capture_catalog.subprocess, "Popen", lambda *_args, **_kwargs: process)
    monkeypatch.setattr(capture_catalog.os, "killpg", lambda pid, sig: signals.append((pid, sig)))
    monkeypatch.setattr(
        capture_catalog.signal,
        "signal",
        lambda signum, handler: installed.setdefault(signum, handler),
    )

    with pytest.raises(capture_catalog.CaptureInterrupted) as caught:
        with capture_catalog._capture_signal_handlers():
            with capture_catalog._managed_process(["owned-child"], stage="server"):
                handler = installed[signal.SIGTERM]
                assert callable(handler)
                handler(signal.SIGTERM, None)

    assert caught.value.signum == signal.SIGTERM
    assert signals == [(8427, signal.SIGTERM)]
    assert process.poll() == -signal.SIGTERM


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
