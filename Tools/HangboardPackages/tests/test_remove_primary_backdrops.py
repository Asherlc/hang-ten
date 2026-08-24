from __future__ import annotations

import importlib.util
import os
import stat
import sys
from pathlib import Path
from types import ModuleType
from types import SimpleNamespace

from PIL import Image
import pytest


SCRIPT_PATH = (
    Path(__file__).resolve().parents[1] / "scripts" / "remove_primary_backdrops.py"
)
CONTACT_BOUNDARY_FIXTURE = (
    Path(__file__).resolve().parent / "fixtures" / "metolius-contact-boundary.png"
)
HANGBOARDS_ROOT = Path(__file__).resolve().parents[3] / "Hangboards"


@pytest.mark.parametrize(
    ("package", "hole", "preserved"),
    [
        ("beastmaker-1000", (215, 10), (500, 20)),
        ("beastmaker-1000", (785, 10), (500, 20)),
        ("soill-iron-palm-2", (768, 425), (768, 475)),
        ("soill-iron-palm-2", (768, 530), (768, 580)),
        ("soill-iron-palm-2", (768, 635), (768, 690)),
        ("soill-training-tiles", (500, 450), (500, 350)),
        ("tension-grindstone", (887, 443), (887, 360)),
        ("trango-rock-prodigy-pivot", (590, 310), (590, 400)),
        ("trango-rock-prodigy-pivot", (710, 310), (710, 400)),
        ("trango-rock-prodigy-pivot", (1055, 310), (1055, 400)),
        ("trango-rock-prodigy-pivot", (1180, 310), (1180, 400)),
        ("yy-travelboard", (190, 625), (768, 512)),
        ("yy-travelboard", (1348, 625), (768, 512)),
        ("yy-verticalboard-evo", (887, 500), (887, 443)),
        ("yy-verticalboard-one", (887, 500), (887, 443)),
        ("yy-penta-evo", (145, 595), (768, 900)),
        ("yy-penta-evo", (1385, 595), (768, 900)),
        ("yy-penta-evo", (180, 720), (768, 900)),
        ("yy-penta-evo", (1355, 720), (768, 900)),
    ],
)
def test_known_enclosed_background_fixtures_clear_only_the_named_through_holes(
    package: str, hole: tuple[int, int], preserved: tuple[int, int]
) -> None:
    """Regression fixtures for the white through-holes rembg leaves opaque."""
    module = _load_script()
    path = HANGBOARDS_ROOT / package / "assets" / "primary.png"
    with Image.open(path) as source_image:
        source = source_image.convert("RGBA")
    opaque_mask = Image.new("L", source.size, color=255)

    corrected = module._clear_known_enclosed_backgrounds(
        source, opaque_mask, package
    )

    assert corrected.getpixel(hole) == 0
    assert corrected.getpixel(preserved) == 255


def _load_script() -> ModuleType:
    assert SCRIPT_PATH.is_file(), "the maintained backdrop-removal script is missing"
    spec = importlib.util.spec_from_file_location("remove_primary_backdrops", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_process_png_uses_rembg_mask_and_preserves_source_rgb(
    tmp_path: Path, monkeypatch
) -> None:
    """Catch regressions to color-keying or RGB-rewriting backdrop removal."""
    module = _load_script()
    path = tmp_path / "primary.png"
    path.write_bytes(CONTACT_BOUNDARY_FIXTURE.read_bytes())

    with Image.open(path) as source_image:
        source = source_image.convert("RGB")
        source_size = source.size
        source_rgb = source.tobytes()

    calls = []

    def create_session(model_name: str, model_root: Path) -> object:
        calls.append((model_name, model_root))
        return object()

    def remove_background(source: Image.Image, *, session: object) -> Image.Image:
        assert session is not None
        mask = Image.new("L", source.size, color=255)
        mask.putpixel((0, 0), 0)
        return mask

    monkeypatch.setattr(module, "_rembg_session", create_session)
    monkeypatch.setattr(module, "_remove_background", remove_background)

    model_root = tmp_path / "rembg-models"
    result = module.process_png(path, model_root=model_root)

    assert result.model_identifier == "rembg.u2net"
    assert calls == [("u2net", model_root)]
    assert result.transparent_pixels > 0
    assert result.opaque_pixels > 0
    with Image.open(path) as output_image:
        output = output_image.convert("RGBA")
        assert output.size == source_size
        assert output.getchannel("A").getextrema()[0] == 0
        assert output.convert("RGB").tobytes() == source_rgb


def test_process_png_preserves_primary_file_mode(tmp_path: Path, monkeypatch) -> None:
    module = _load_script()
    path = tmp_path / "primary.png"
    path.write_bytes(CONTACT_BOUNDARY_FIXTURE.read_bytes())
    path.chmod(0o640)

    def remove_background(source: Image.Image, *, session: object) -> Image.Image:
        mask = Image.new("L", source.size, color=255)
        mask.putpixel((0, 0), 0)
        return mask

    monkeypatch.setattr(module, "_remove_background", remove_background)

    module.process_png(path, model_root=tmp_path / "models", session=object())

    assert stat.S_IMODE(path.stat().st_mode) == 0o640


def test_process_png_resegments_an_existing_alpha_source(
    tmp_path: Path, monkeypatch
) -> None:
    """Every primary, including one with alpha, must use the maintained model."""
    module = _load_script()
    path = tmp_path / "primary.png"
    image = Image.new("RGBA", (5, 3), color=(120, 80, 40, 255))
    for x in range(image.width):
        image.putpixel((x, 0), (255, 255, 255, 0))
    image.save(path, format="PNG")

    calls = []

    def create_session(model_name: str, model_root: Path) -> object:
        calls.append((model_name, model_root))
        return object()

    def remove_background(source: Image.Image, *, session: object) -> Image.Image:
        assert session is not None
        mask = Image.new("L", (5, 3), color=255)
        mask.putpixel((0, 0), 0)
        return mask

    monkeypatch.setattr(module, "_rembg_session", create_session)
    monkeypatch.setattr(module, "_remove_background", remove_background)

    model_root = tmp_path / "rembg-models"
    result = module.process_png(path, model_root=model_root)

    assert result.model_identifier == "rembg.u2net"
    assert calls == [("u2net", model_root)]
    with Image.open(path) as output:
        assert output.convert("RGBA").getchannel("A").getextrema() == (0, 255)


def test_process_png_keeps_onnx_session_artifacts_out_of_the_repository_root(
    tmp_path: Path, monkeypatch
) -> None:
    module = _load_script()
    path = tmp_path / "package" / "assets" / "primary.png"
    path.parent.mkdir(parents=True)
    Image.new("RGB", (3, 2), color=(120, 100, 80)).save(path, format="PNG")
    model_root = tmp_path / "model-cache"

    def remove_background(source: Image.Image, *, session: object) -> Image.Image:
        assert Path.cwd().resolve() == model_root.resolve()
        (model_root / ":memory:.ses").write_text("session", encoding="utf-8")
        (tmp_path / ":memory:.ses").write_text("late-session", encoding="utf-8")
        mask = Image.new("L", source.size, color=255)
        mask.putpixel((0, 0), 0)
        return mask

    monkeypatch.setattr(module, "_remove_background", remove_background)
    monkeypatch.chdir(tmp_path)

    module.process_png(path, model_root=model_root, session=object())

    assert not (tmp_path / ":memory:.ses").exists()
    assert not (model_root / ":memory:.ses").exists()


def test_rembg_session_disables_onnx_telemetry_before_initialization(
    tmp_path: Path, monkeypatch
) -> None:
    module = _load_script()
    seen = []

    def new_session(model_name: str) -> object:
        seen.append((model_name, os.environ.get("ORT_DISABLE_TELEMETRY")))
        return object()

    monkeypatch.delenv("ORT_DISABLE_TELEMETRY", raising=False)
    monkeypatch.setitem(sys.modules, "rembg", SimpleNamespace(new_session=new_session))

    module._rembg_session("u2net", tmp_path / "model-cache")

    assert seen == [("u2net", "1")]


def test_main_rejects_seed_packages_missing_from_the_invocation(
    tmp_path: Path, monkeypatch, capsys: pytest.CaptureFixture[str]
) -> None:
    module = _load_script()
    root = tmp_path / "Hangboards"
    primary = root / "included" / "assets" / "primary.png"
    primary.parent.mkdir(parents=True)
    Image.new("RGB", (2, 2), color="white").save(primary, format="PNG")
    monkeypatch.setattr(
        module,
        "_ENCLOSED_BACKGROUND_SEEDS",
        {"included": ((0, 0),), "omitted": ((0, 0),)},
    )

    def reject_session_creation(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("seed coverage must be checked before model initialization")

    monkeypatch.setattr(module, "_rembg_session", reject_session_creation)

    with pytest.raises(SystemExit, match="2"):
        module.main(["--root", str(root)])

    assert "seed packages not processed by this invocation: omitted" in capsys.readouterr().err
