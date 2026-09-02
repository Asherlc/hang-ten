from __future__ import annotations

import hashlib
import inspect
import json
from datetime import date
from pathlib import Path

import pytest
from PIL import Image, PngImagePlugin

from hangboard_packages.cord_render_assets import (
    ChromaConfig,
    build_lossless_atlases,
    decoded_pixel_sha256,
    inspect_transparency,
    lock_source,
    remove_chroma,
    verify_atlas_round_trip,
)


def _context(tmp_path: Path) -> Path:
    root = tmp_path / ".context" / "joyful-donkey-cord-assets"
    root.mkdir(parents=True)
    return root


def _png(path: Path, size: tuple[int, int], pixels: dict[tuple[int, int], tuple[int, ...]], mode: str = "RGB") -> Path:
    image = Image.new(mode, size, (0, 255, 0) if mode == "RGB" else (0, 255, 0, 255))
    for position, value in pixels.items():
        image.putpixel(position, value)
    image.save(path, format="PNG")
    return path


def _locked(path: Path, source_id: str) -> object:
    return lock_source(
        path,
        source_id=source_id,
        url=f"https://manufacturer.example/{source_id}",
        publisher="Fixture Manufacturer",
        role="product",
        revision="fixture-revision",
        reviewed_at=date(2026, 9, 2),
    )


def test_decoded_pixel_hash_ignores_png_container_metadata(tmp_path: Path) -> None:
    first = _png(tmp_path / "first.png", (3, 2), {(1, 1): (12, 34, 56)})
    second = tmp_path / "second.png"
    image = Image.open(first)
    metadata = PngImagePlugin.PngInfo()
    metadata.add_text("Comment", "different container metadata")
    image.save(second, format="PNG", pnginfo=metadata)

    assert hashlib.sha256(first.read_bytes()).hexdigest() != hashlib.sha256(second.read_bytes()).hexdigest()
    assert decoded_pixel_sha256(first) == decoded_pixel_sha256(second)


def test_lock_source_freezes_metadata_and_rejects_unsafe_sources(tmp_path: Path) -> None:
    source = _png(tmp_path / "source.png", (4, 3), {})
    lock = _locked(source, "source-a")

    assert lock.source_id == "source-a"
    assert lock.byte_sha256 == hashlib.sha256(source.read_bytes()).hexdigest()
    assert lock.decoded_pixel_sha256 == decoded_pixel_sha256(source)
    assert lock.mode == "RGB" and lock.width == 4 and lock.height == 3
    assert lock.cache_path.is_absolute() and lock.cache_path != source.resolve()
    assert lock.cache_path.read_bytes() == source.read_bytes()
    with pytest.raises(ValueError, match="duplicate source ID"):
        _locked(source, "source-a")
    missing_url = tmp_path / "missing-url.png"
    missing_url.write_bytes(source.read_bytes())
    with pytest.raises(ValueError, match="url"):
        lock_source(missing_url, source_id="missing", url="", publisher="x", role="x", revision="x", reviewed_at=date.today())
    not_image = tmp_path / "not-image.txt"
    not_image.write_text("not an image", encoding="utf-8")
    with pytest.raises(ValueError, match="image"):
        _locked(not_image, "not-image")
    symlink = tmp_path / "source-link.png"
    symlink.symlink_to(source)
    with pytest.raises(ValueError, match="symlink"):
        _locked(symlink, "symlink")


def test_atlas_is_lossless_deterministic_and_rejects_tampering(tmp_path: Path) -> None:
    context = _context(tmp_path)
    sources = [
        _locked(_png(tmp_path / f"{name}.png", size, {(0, 0): color}), name)
        for name, size, color in (
            ("six", (7, 3), (1, 2, 3)), ("one", (3, 4), (4, 5, 6)),
            ("five", (4, 2), (7, 8, 9)), ("two", (5, 5), (10, 11, 12)),
            ("four", (2, 6), (13, 14, 15)), ("three", (6, 2), (16, 17, 18)),
        )
    ]
    source_bytes = {source.source_id: source.cache_path.read_bytes() for source in sources}
    first = build_lossless_atlases(sources, context / "atlases-a")
    second = build_lossless_atlases(list(reversed(sources)), context / "atlases-b")

    assert 1 <= len(first.pages) <= 5
    assert [page.byte_sha256 for page in first.pages] == [page.byte_sha256 for page in second.pages]
    assert [panel.source_id for panel in first.panels] == sorted(source_bytes)
    assert all(source.cache_path.read_bytes() == source_bytes[source.source_id] for source in sources)
    assert verify_atlas_round_trip(first).valid is True
    for page in first.pages:
        panels = [panel for panel in first.panels if panel.page_number == page.number]
        for index, panel in enumerate(panels):
            assert panel.x >= 0 and panel.y >= 0 and panel.x + panel.width <= page.width and panel.y + panel.height <= page.height
            assert all(
                panel.x + panel.width <= other.x or other.x + other.width <= panel.x or panel.y + panel.height <= other.y or other.y + other.height <= panel.y
                for other in panels[index + 1 :]
            )
    tampered = first.pages[0].path
    tampered.write_bytes(b"tampered")
    with pytest.raises(ValueError, match="atlas page hash"):
        verify_atlas_round_trip(first)


def test_atlas_refuses_a_sixth_required_page_and_has_no_transform_parameters(tmp_path: Path) -> None:
    context = _context(tmp_path)
    sources = [_locked(_png(tmp_path / f"{number}.png", (2000, 1100), {}), str(number)) for number in range(6)]
    with pytest.raises(ValueError, match="five atlas pages"):
        build_lossless_atlases(sources, context / "atlases", max_pages=5)
    assert not {"crop", "resize", "rotate"}.intersection(inspect.signature(build_lossless_atlases).parameters)


def test_remove_chroma_preserves_product_pixels_and_existing_alpha(tmp_path: Path) -> None:
    context = _context(tmp_path)
    raw = _png(
        tmp_path / "raw.png", (5, 5),
        {(2, 2): (0, 255, 0, 255), (1, 1): (91, 92, 93, 255), (2, 1): (91, 92, 93, 255), (3, 2): (91, 92, 93, 255), (2, 3): (91, 92, 93, 255), (1, 2): (91, 92, 93, 255), (3, 3): (1, 2, 3, 77)},
        "RGBA",
    )
    output = context / "keyed.png"
    report = remove_chroma(raw, output, ChromaConfig(key_rgb=(0, 255, 0), distance_threshold=45, edge_distance_threshold=90))
    image = Image.open(output).convert("RGBA")

    assert image.size == (5, 5)
    assert image.getpixel((2, 2)) == (0, 255, 0, 255)  # isolated green product pixel survives
    assert image.getpixel((1, 1)) == (91, 92, 93, 255)
    assert image.getpixel((3, 3)) == (1, 2, 3, 77)
    assert image.getpixel((0, 0))[3] == 0
    assert report.minimum_alpha == 0 and report.maximum_alpha == 255
    assert report.config.key_rgb == (0, 255, 0)


def test_transparency_inspection_rejects_background_fringe_and_wrong_output(tmp_path: Path) -> None:
    opaque = _png(tmp_path / "opaque.png", (4, 4), {(1, 1): (250, 250, 245, 255)}, "RGBA")
    with pytest.raises(ValueError, match="all opaque"):
        inspect_transparency(opaque, 4, 4, (0, 255, 0))
    flood = tmp_path / "flood.png"
    flood_image = Image.new("RGBA", (4, 4), (0, 0, 0, 0))
    flood_image.putpixel((1, 0), (250, 250, 245, 255))
    flood_image.save(flood, format="PNG")
    with pytest.raises(ValueError, match="boundary.*flood"):
        inspect_transparency(flood, 4, 4, (0, 255, 0))
    fringe = _png(tmp_path / "fringe.png", (4, 4), {(0, 0): (0, 0, 0, 0), (3, 0): (0, 0, 0, 0), (0, 3): (0, 0, 0, 0), (3, 3): (0, 0, 0, 0), (1, 0): (0, 230, 0, 255)}, "RGBA")
    with pytest.raises(ValueError, match="key fringe"):
        inspect_transparency(fringe, 4, 4, (0, 255, 0))
    valid = tmp_path / "valid.png"
    valid_image = Image.new("RGBA", (4, 4), (0, 0, 0, 0))
    valid_image.putpixel((1, 1), (90, 80, 70, 255))
    valid_image.save(valid, format="PNG")
    report = inspect_transparency(valid, 4, 4, (0, 255, 0))
    assert report.corner_alpha == (0, 0, 0, 0)
    with pytest.raises(ValueError, match="dimensions"):
        inspect_transparency(valid, 5, 4, (0, 255, 0))


def test_remove_chroma_refuses_in_place_or_context_escape(tmp_path: Path) -> None:
    raw = _png(tmp_path / "raw.png", (3, 3), {})
    with pytest.raises(ValueError, match="in place"):
        remove_chroma(raw, raw, ChromaConfig())
    with pytest.raises(ValueError, match="owner-named .context"):
        remove_chroma(raw, Path("/tmp/outside.png"), ChromaConfig())
