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


def test_process_png_uses_vision_foreground_segmentation_and_preserves_source_rgb(
    tmp_path: Path,
) -> None:
    """Catch regressions to color-keying or RGB-rewriting backdrop removal."""
    module = _load_script()
    path = tmp_path / "primary.png"
    path.write_bytes(CONTACT_BOUNDARY_FIXTURE.read_bytes())

    with Image.open(path) as source_image:
        source = source_image.convert("RGB")
        source_size = source.size
        source_pixels = source.load()

    result = module.process_png(path, build_root=tmp_path / "vision-build")

    assert result.model_identifier == "Vision.VNGenerateForegroundInstanceMaskRequest"
    assert result.transparent_pixels > 0
    assert result.opaque_pixels > 0
    with Image.open(path) as output_image:
        output = output_image.convert("RGBA")
        assert output.size == source_size
        assert output.getchannel("A").getextrema()[0] == 0
        for y in range(output.height):
            for x in range(output.width):
                red, green, blue, alpha = output.getpixel((x, y))
                if alpha:
                    assert (red, green, blue) == source_pixels[x, y]


def test_process_png_preserves_an_existing_transparent_silhouette(
    tmp_path: Path,
) -> None:
    """Catch needless model replacement of an already-authored alpha matte."""
    module = _load_script()
    path = tmp_path / "primary.png"
    image = Image.new("RGBA", (5, 3), color=(120, 80, 40, 255))
    for x in range(image.width):
        image.putpixel((x, 0), (255, 255, 255, 0))
    image.save(path, format="PNG")
    original = path.read_bytes()

    result = module.process_png(path, build_root=tmp_path / "unused-build")

    assert result.model_identifier == "existing-alpha"
    assert path.read_bytes() == original
    assert not (tmp_path / "unused-build").exists()
