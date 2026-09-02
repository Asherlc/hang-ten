from __future__ import annotations

import hashlib
import inspect
import os
import time
from dataclasses import replace
from datetime import date
from pathlib import Path

import pytest
from PIL import Image, PngImagePlugin

import hangboard_packages.cord_render_assets as cord_render_assets
from hangboard_packages.cord_render_assets import (
    ChromaConfig,
    build_lossless_atlases,
    decoded_pixel_sha256,
    inspect_transparency,
    lock_source,
    remove_chroma,
    verify_atlas_round_trip,
)


def _context(tmp_path: Path, name: str = "cord-assets") -> Path:
    root = tmp_path / ".context" / f"joyful-donkey-{name}"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _png(
    path: Path,
    size: tuple[int, int],
    pixels: dict[tuple[int, int], tuple[int, ...]],
    mode: str = "RGB",
    *,
    background: tuple[int, ...] | None = None,
) -> Path:
    if background is None:
        background = (0, 255, 0) if mode == "RGB" else (0, 255, 0, 255)
    image = Image.new(mode, size, background)
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


def _context_source(
    tmp_path: Path,
    source_id: str,
    size: tuple[int, int] = (8, 6),
    color: tuple[int, int, int] = (40, 50, 60),
) -> object:
    root = _context(tmp_path, f"source-{source_id}")
    return _locked(_png(root / f"{source_id}.png", size, {}, background=color), source_id)


def _small_index(tmp_path: Path, prefix: str = "tamper") -> object:
    first = _context_source(tmp_path, f"{prefix}-first", (5, 4), (10, 20, 30))
    second = _context_source(tmp_path, f"{prefix}-second", (6, 3), (80, 90, 100))
    return build_lossless_atlases(
        [first, second], _context(tmp_path, f"atlas-{prefix}") / "pages"
    )


def test_decoded_pixel_hash_ignores_png_container_metadata(tmp_path: Path) -> None:
    first = _png(tmp_path / "first.png", (3, 2), {(1, 1): (12, 34, 56)})
    second = tmp_path / "second.png"
    with Image.open(first) as image:
        metadata = PngImagePlugin.PngInfo()
        metadata.add_text("Comment", "different container metadata")
        image.save(second, format="PNG", pnginfo=metadata)

    assert hashlib.sha256(first.read_bytes()).hexdigest() != hashlib.sha256(
        second.read_bytes()
    ).hexdigest()
    assert decoded_pixel_sha256(first) == decoded_pixel_sha256(second)


def test_decoded_pixel_hash_includes_palette_and_palette_transparency(
    tmp_path: Path,
) -> None:
    red = Image.new("P", (2, 2), 0)
    red.putpalette([255, 0, 0] + [0, 0, 0] * 255)
    red_path = tmp_path / "red-palette.png"
    red.save(red_path, format="PNG")
    blue = Image.new("P", (2, 2), 0)
    blue.putpalette([0, 0, 255] + [0, 0, 0] * 255)
    blue_path = tmp_path / "blue-palette.png"
    blue.save(blue_path, format="PNG")
    transparent_path = tmp_path / "transparent-palette.png"
    red.save(transparent_path, format="PNG", transparency=0)

    assert decoded_pixel_sha256(red_path) != decoded_pixel_sha256(blue_path)
    assert decoded_pixel_sha256(red_path) != decoded_pixel_sha256(transparent_path)


def test_decoded_pixel_hash_distinguishes_high_bit_depth_pixels(tmp_path: Path) -> None:
    first = Image.new("I;16", (2, 2))
    first.putdata([0, 256, 1024, 65535])
    first_path = tmp_path / "first-16.png"
    first.save(first_path, format="PNG")
    second = Image.new("I;16", (2, 2))
    second.putdata([0, 257, 1024, 65535])
    second_path = tmp_path / "second-16.png"
    second.save(second_path, format="PNG")

    assert decoded_pixel_sha256(first_path) != decoded_pixel_sha256(second_path)


def test_lock_source_accepts_external_input_and_uses_workspace_owner_cache(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    monkeypatch.setenv("PASEO_WORKTREE_PATH", str(workspace))
    source = _png(tmp_path / "external.png", (4, 3), {}, background=(4, 5, 6))

    locked = _locked(source, "external-source")

    expected_root = (
        workspace / ".context" / "joyful-donkey-cord-assets" / "sources" / "locked"
    ).resolve()
    assert locked.cache_path.parent == expected_root
    assert locked.cache_path.read_bytes() == source.read_bytes()


def test_lock_source_uses_one_consistent_snapshot(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    monkeypatch.setenv("PASEO_WORKTREE_PATH", str(workspace))
    source = _png(tmp_path / "snapshot.png", (4, 3), {}, background=(1, 2, 3))
    replacement = _png(
        tmp_path / "replacement.png", (4, 3), {}, background=(200, 201, 202)
    ).read_bytes()
    original_read_bytes = Path.read_bytes
    source_resolved = source.resolve()
    reads = 0

    def alternating_read_bytes(path: Path) -> bytes:
        nonlocal reads
        if path.resolve() == source_resolved:
            reads += 1
            if reads % 2 == 0:
                return replacement
        return original_read_bytes(path)

    monkeypatch.setattr(Path, "read_bytes", alternating_read_bytes)

    locked = _locked(source, "single-snapshot")
    cache_bytes = original_read_bytes(locked.cache_path)

    assert hashlib.sha256(cache_bytes).hexdigest() == locked.byte_sha256
    assert decoded_pixel_sha256(locked.cache_path) == locked.decoded_pixel_sha256
    assert (locked.width, locked.height, locked.mode) == (4, 3, "RGB")


def test_lock_source_fails_if_path_is_replaced_while_snapshot_is_open(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    monkeypatch.setenv("PASEO_WORKTREE_PATH", str(workspace))
    source = _png(tmp_path / "replace-during-read.png", (4, 3), {}, background=(1, 2, 3))
    replacement = _png(
        tmp_path / "replacement-during-read.png",
        (4, 3),
        {},
        background=(200, 201, 202),
    )
    original_read = cord_render_assets.os.read
    replaced = False

    def replacing_read(descriptor: int, count: int) -> bytes:
        nonlocal replaced
        chunk = original_read(descriptor, count)
        if not chunk and not replaced:
            replaced = True
            os.replace(replacement, source)
        return chunk

    monkeypatch.setattr(cord_render_assets.os, "read", replacing_read)

    with pytest.raises(ValueError, match="changed while it was being locked"):
        _locked(source, "replaced-snapshot")


@pytest.mark.parametrize(
    "source_id",
    ["../escape", "folder/escape", "/absolute/escape", ".", "..", "bad\\name"],
)
def test_lock_source_rejects_non_component_source_ids(
    tmp_path: Path, source_id: str
) -> None:
    source = _png(
        _context(tmp_path, "unsafe-id") / "source.png",
        (3, 3),
        {},
        background=(1, 2, 3),
    )

    with pytest.raises(ValueError, match="source_id"):
        _locked(source, source_id)


def test_lock_source_rejects_symlink_in_any_input_component(tmp_path: Path) -> None:
    real = tmp_path / "real"
    real.mkdir()
    source = _png(real / "source.png", (3, 3), {}, background=(1, 2, 3))
    linked_parent = tmp_path / "linked-parent"
    linked_parent.symlink_to(real, target_is_directory=True)

    with pytest.raises(ValueError, match="symlink"):
        _locked(linked_parent / source.name, "symlink-component")


def test_duplicate_source_ids_are_scoped_to_one_collection(tmp_path: Path) -> None:
    first = _context_source(tmp_path, "independent-id", color=(1, 2, 3))
    second_root = _context(tmp_path, "second-independent")
    second = _locked(
        _png(
            second_root / "source.png",
            (8, 6),
            {},
            background=(7, 8, 9),
        ),
        "independent-id",
    )

    assert first.source_id == second.source_id
    with pytest.raises(ValueError, match="duplicate source ID"):
        build_lossless_atlases(
            [first, second], _context(tmp_path, "duplicate-atlas") / "pages"
        )


def test_atlas_uses_deterministic_two_dimensional_packing(tmp_path: Path) -> None:
    sources = [
        _context_source(
            tmp_path,
            f"fit-{number}",
            (900, 1100),
            (number + 1, 100, 200),
        )
        for number in range(6)
    ]

    first = build_lossless_atlases(
        sources, _context(tmp_path, "two-dimensional-a") / "pages"
    )
    second = build_lossless_atlases(
        list(reversed(sources)),
        _context(tmp_path, "two-dimensional-b") / "pages",
    )

    assert len(first.pages) == 3
    assert [page.byte_sha256 for page in first.pages] == [
        page.byte_sha256 for page in second.pages
    ]
    assert verify_atlas_round_trip(first).verified_panels == 6


def test_atlas_refuses_a_genuine_sixth_page_and_reports_the_limit(
    tmp_path: Path,
) -> None:
    sources = [
        _context_source(
            tmp_path,
            f"overflow-{number}",
            (2000, 1100),
            (number + 1, 120, 210),
        )
        for number in range(6)
    ]

    with pytest.raises(ValueError, match=r"requires 6.*limit.*5"):
        build_lossless_atlases(
            sources, _context(tmp_path, "sixth-page") / "pages", max_pages=5
        )
    assert not {"crop", "resize", "rotate"}.intersection(
        inspect.signature(build_lossless_atlases).parameters
    )


def test_atlas_rejects_preexisting_page_symlink(tmp_path: Path) -> None:
    source = _context_source(tmp_path, "page-symlink-source")
    output = _context(tmp_path, "page-symlink-output") / "pages"
    output.mkdir()
    unrelated = tmp_path / "unrelated.png"
    unrelated.write_bytes(b"unrelated")
    (output / "page-01.png").symlink_to(unrelated)

    with pytest.raises(ValueError, match="symlink"):
        build_lossless_atlases([source], output)
    assert unrelated.read_bytes() == b"unrelated"


def test_owner_context_requires_real_path_components(tmp_path: Path) -> None:
    source = _context_source(tmp_path, "pseudo-context-source")
    pseudo = tmp_path / "not.context" / "joyful-donkey-pseudo" / "pages"

    with pytest.raises(ValueError, match="owner-named .context"):
        build_lossless_atlases([source], pseudo)


def test_atlas_verifier_rejects_tampered_locked_source(tmp_path: Path) -> None:
    index = _small_index(tmp_path, "source-record")
    source = index.sources[0]
    _png(
        source.cache_path,
        (source.width, source.height),
        {},
        background=(201, 202, 203),
    )

    with pytest.raises(ValueError, match="locked source"):
        verify_atlas_round_trip(index)


def test_atlas_verifier_rejects_tampered_source_record(tmp_path: Path) -> None:
    index = _small_index(tmp_path, "source-metadata-record")
    source = index.sources[0]
    tampered_sources = (replace(source, byte_sha256="0" * 64), *index.sources[1:])

    with pytest.raises(ValueError, match="original source hash"):
        verify_atlas_round_trip(replace(index, sources=tampered_sources))
    missing_metadata = (replace(source, url=""), *index.sources[1:])
    with pytest.raises(ValueError, match="url"):
        verify_atlas_round_trip(replace(index, sources=missing_metadata))


def test_atlas_verifier_rejects_tampered_page_record(tmp_path: Path) -> None:
    index = _small_index(tmp_path, "page-record")
    page = index.pages[0]
    tampered = replace(index, pages=(replace(page, width=page.width + 100),))

    with pytest.raises(ValueError, match="page.*dimensions"):
        verify_atlas_round_trip(tampered)


def test_atlas_verifier_rejects_tampered_page_pixels_and_path(tmp_path: Path) -> None:
    index = _small_index(tmp_path, "page-bytes")
    page = index.pages[0]
    with Image.open(page.path) as opened:
        image = opened.convert("RGBA")
    image.putpixel((0, 0), (1, 2, 3, 4))
    image.save(page.path, format="PNG")

    with pytest.raises(ValueError, match="atlas page hash"):
        verify_atlas_round_trip(index)

    fresh = _small_index(tmp_path, "page-path")
    outside = tmp_path / "outside-page.png"
    outside.write_bytes(fresh.pages[0].path.read_bytes())
    escaped = replace(
        fresh, pages=(replace(fresh.pages[0], path=outside.resolve()),)
    )
    with pytest.raises(ValueError, match="owner-named .context"):
        verify_atlas_round_trip(escaped)


def test_atlas_verifier_rejects_tampered_index_constants(tmp_path: Path) -> None:
    index = _small_index(tmp_path, "index-record")

    with pytest.raises(ValueError, match="packing constants"):
        verify_atlas_round_trip(replace(index, padding=index.padding + 1))


def test_atlas_verifier_rejects_overlapping_panel_records(tmp_path: Path) -> None:
    index = _small_index(tmp_path, "panel-record")
    first, second = index.panels
    overlapping = replace(
        second,
        page_number=first.page_number,
        x=first.x,
        y=first.y,
    )
    tampered = replace(index, panels=(first, overlapping))

    with pytest.raises(ValueError, match="overlap"):
        verify_atlas_round_trip(tampered)


def test_atlas_verifier_requires_every_page_to_be_used(tmp_path: Path) -> None:
    index = _small_index(tmp_path, "unused-page")
    page = index.pages[0]
    extra_path = page.path.parent / "page-02.png"
    extra_path.write_bytes(page.path.read_bytes())
    extra = replace(page, number=2, path=extra_path.resolve())
    tampered = replace(index, pages=(page, extra))

    with pytest.raises(ValueError, match="unused atlas page"):
        verify_atlas_round_trip(tampered)


def test_palette_source_round_trips_visibly_and_high_bit_atlas_is_rejected(
    tmp_path: Path,
) -> None:
    root = _context(tmp_path, "palette-atlas-source")
    palette = Image.new("P", (5, 4), 0)
    palette.putpalette([255, 0, 0] + [0, 0, 0] * 255)
    palette_path = root / "palette.png"
    palette.save(palette_path, format="PNG")
    palette_source = _locked(palette_path, "palette-atlas")
    index = build_lossless_atlases(
        [palette_source], _context(tmp_path, "palette-atlas-output") / "pages"
    )
    assert verify_atlas_round_trip(index).valid is True

    high_bit = Image.new("I;16", (5, 4))
    high_bit.putdata(range(20))
    high_bit_path = root / "high-bit.png"
    high_bit.save(high_bit_path, format="PNG")
    high_bit_source = _locked(high_bit_path, "high-bit-atlas")
    with pytest.raises(ValueError, match="cannot round-trip"):
        build_lossless_atlases(
            [high_bit_source], _context(tmp_path, "high-bit-atlas-output") / "pages"
        )


def test_chroma_boundary_walk_is_linear_for_representative_matte(
    tmp_path: Path,
) -> None:
    raw = _png(tmp_path / "flat-256.png", (256, 256), {})
    output = _context(tmp_path, "performance") / "keyed.png"

    started = time.monotonic()
    report = remove_chroma(raw, output, ChromaConfig())
    elapsed = time.monotonic() - started

    assert report.transparent_fraction == 1.0
    assert elapsed < 2.0


def test_remove_chroma_decontaminates_unique_antialiased_frontier_for_inspection(
    tmp_path: Path,
) -> None:
    raw = _png(
        tmp_path / "antialiased.png",
        (9, 9),
        {
            (3, 3): (80, 70, 60, 255),
            (4, 3): (80, 70, 60, 255),
            (5, 3): (80, 70, 60, 255),
            (3, 4): (20, 195, 20, 255),
            (4, 4): (80, 70, 60, 255),
            (5, 4): (80, 70, 60, 255),
            (3, 5): (80, 70, 60, 255),
            (4, 5): (80, 70, 60, 255),
            (5, 5): (80, 70, 60, 255),
            (2, 4): (0, 200, 0, 255),
        },
        "RGBA",
    )
    output = _context(tmp_path, "antialiased") / "keyed.png"
    config = ChromaConfig(
        key_rgb=(0, 255, 0), distance_threshold=36, edge_distance_threshold=72
    )

    remove_chroma(raw, output, config)
    report = inspect_transparency(output, 9, 9, config.key_rgb)
    keyed = Image.open(output).convert("RGBA")

    assert report.remaining_key_fringe_count == 0
    assert keyed.getpixel((2, 4))[3] < 255
    assert keyed.getpixel((2, 4))[:3] != (0, 200, 0)
    assert keyed.getpixel((3, 4)) != (20, 195, 20, 255)
    assert keyed.getpixel((4, 4)) == (80, 70, 60, 255)


def test_remove_chroma_preserves_product_pixels_and_existing_alpha(
    tmp_path: Path,
) -> None:
    raw = _png(
        tmp_path / "raw.png",
        (5, 5),
        {
            (2, 2): (0, 255, 0, 255),
            (1, 1): (91, 92, 93, 255),
            (2, 1): (91, 92, 93, 255),
            (3, 2): (91, 92, 93, 255),
            (2, 3): (91, 92, 93, 255),
            (1, 2): (91, 92, 93, 255),
            (3, 3): (1, 2, 3, 77),
        },
        "RGBA",
    )
    output = _context(tmp_path, "preservation") / "keyed.png"
    config = ChromaConfig(
        key_rgb=(0, 255, 0), distance_threshold=45, edge_distance_threshold=90
    )

    report = remove_chroma(raw, output, config)
    image = Image.open(output).convert("RGBA")

    assert image.size == (5, 5)
    assert image.getpixel((2, 2)) == (0, 255, 0, 255)
    assert image.getpixel((1, 1)) == (91, 92, 93, 255)
    assert image.getpixel((3, 3)) == (1, 2, 3, 77)
    assert image.getpixel((0, 0))[3] == 0
    assert report.minimum_alpha == 0 and report.maximum_alpha == 255
    assert report.config == config


def test_remove_chroma_supports_recorded_alternative_key(tmp_path: Path) -> None:
    raw = _png(
        tmp_path / "alternative-key.png",
        (7, 7),
        {(3, 3): (0, 255, 0, 255)},
        "RGBA",
        background=(255, 0, 255, 255),
    )
    output = _context(tmp_path, "alternative-key") / "keyed.png"
    config = ChromaConfig(
        key_rgb=(255, 0, 255), distance_threshold=36, edge_distance_threshold=72
    )

    remove_chroma(raw, output, config)
    report = inspect_transparency(output, 7, 7, config.key_rgb)

    assert report.config.key_rgb == (255, 0, 255)
    assert Image.open(output).convert("RGBA").getpixel((3, 3)) == (0, 255, 0, 255)


@pytest.mark.parametrize("matte", [(0, 0, 0), (20, 90, 220), (250, 250, 245)])
def test_transparency_inspection_rejects_substantial_opaque_mattes(
    tmp_path: Path, matte: tuple[int, int, int]
) -> None:
    image = Image.new("RGBA", (20, 20), (*matte, 255))
    for point in ((0, 0), (19, 0), (0, 19), (19, 19)):
        image.putpixel(point, (0, 0, 0, 0))
    path = tmp_path / f"matte-{matte[0]}-{matte[1]}-{matte[2]}.png"
    image.save(path, format="PNG")

    with pytest.raises(ValueError, match="boundary opaque flood"):
        inspect_transparency(path, 20, 20, (0, 255, 0))


def test_transparency_inspection_rejects_textured_boundary_matte(
    tmp_path: Path,
) -> None:
    image = Image.new("RGBA", (20, 20), (0, 0, 0, 0))
    for x in range(20):
        for y in range(20):
            if (x, y) not in {(0, 0), (19, 0), (0, 19), (19, 19)}:
                color = (10, 20, 80) if (x + y) % 2 else (90, 20, 10)
                image.putpixel((x, y), (*color, 255))
    path = tmp_path / "textured-matte.png"
    image.save(path, format="PNG")

    with pytest.raises(ValueError, match="boundary opaque flood"):
        inspect_transparency(path, 20, 20, (0, 255, 0))


def test_transparency_inspection_allows_small_documented_boundary_contact(
    tmp_path: Path,
) -> None:
    image = Image.new("RGBA", (20, 20), (0, 0, 0, 0))
    for y in range(4):
        image.putpixel((10, y), (30, 30, 30, 255))
    for x in range(8, 13):
        for y in range(8, 13):
            image.putpixel((x, y), (90, 80, 70, 255))
    path = tmp_path / "small-contact.png"
    image.save(path, format="PNG")

    report = inspect_transparency(path, 20, 20, (0, 255, 0))

    assert report.boundary_connected_opaque_flood_count == 0


def test_inspection_report_has_complete_nonempty_hash_contract(tmp_path: Path) -> None:
    image = Image.new("RGBA", (8, 8), (0, 0, 0, 0))
    image.putpixel((4, 4), (90, 80, 70, 255))
    path = tmp_path / "valid.png"
    image.save(path, format="PNG")

    report = inspect_transparency(path, 8, 8, (0, 255, 0))
    payload = report.to_json()

    assert report.input_byte_sha256 == report.output_byte_sha256
    assert len(report.input_byte_sha256) == 64
    assert len(report.decoded_pixel_sha256) == 64
    assert set(payload) == {
        "schemaVersion",
        "toolVersion",
        "config",
        "inputByteSHA256",
        "outputByteSHA256",
        "decodedPixelSHA256",
        "width",
        "height",
        "mode",
        "minimumAlpha",
        "maximumAlpha",
        "cornerAlpha",
        "transparentFraction",
        "boundaryConnectedOpaqueFloodCount",
        "remainingKeyFringeCount",
    }


def test_transparency_inspection_rejects_fringe_wrong_dimensions_and_opaque(
    tmp_path: Path,
) -> None:
    opaque = _png(
        tmp_path / "opaque.png",
        (4, 4),
        {},
        "RGBA",
        background=(20, 30, 40, 255),
    )
    with pytest.raises(ValueError, match="all opaque"):
        inspect_transparency(opaque, 4, 4, (0, 255, 0))
    fringe = Image.new("RGBA", (4, 4), (0, 0, 0, 0))
    fringe.putpixel((1, 0), (0, 230, 0, 255))
    fringe_path = tmp_path / "fringe.png"
    fringe.save(fringe_path, format="PNG")
    with pytest.raises(ValueError, match="key fringe"):
        inspect_transparency(fringe_path, 4, 4, (0, 255, 0))
    valid = Image.new("RGBA", (4, 4), (0, 0, 0, 0))
    valid.putpixel((1, 1), (90, 80, 70, 255))
    valid_path = tmp_path / "wrong-dimensions.png"
    valid.save(valid_path, format="PNG")
    with pytest.raises(ValueError, match="dimensions"):
        inspect_transparency(valid_path, 5, 4, (0, 255, 0))


def test_remove_chroma_requires_explicit_config_and_confined_distinct_output(
    tmp_path: Path,
) -> None:
    raw = _png(tmp_path / "raw.png", (3, 3), {})

    assert inspect.signature(remove_chroma).parameters["config"].default is inspect.Signature.empty
    with pytest.raises(ValueError, match="in place"):
        remove_chroma(raw, raw, ChromaConfig())
    with pytest.raises(ValueError, match="owner-named .context"):
        remove_chroma(raw, Path("/tmp/outside.png"), ChromaConfig())
