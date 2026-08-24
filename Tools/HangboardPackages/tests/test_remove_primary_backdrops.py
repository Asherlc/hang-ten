from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

from PIL import Image


SCRIPT_PATH = (
    Path(__file__).resolve().parents[1] / "scripts" / "remove_primary_backdrops.py"
)
CONTACT_BOUNDARY_FIXTURE = (
    Path(__file__).resolve().parent / "fixtures" / "metolius-contact-boundary.png"
)


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
        source_pixels = source.load()

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
        for y in range(output.height):
            for x in range(output.width):
                red, green, blue, _ = output.getpixel((x, y))
                assert (red, green, blue) == source_pixels[x, y]


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
