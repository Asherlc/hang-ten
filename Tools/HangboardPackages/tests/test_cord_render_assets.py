from __future__ import annotations

import hashlib
import inspect
import json
import math
import os
import shutil
import time
from dataclasses import replace
from datetime import date, datetime
from pathlib import Path

import pytest
from PIL import Image, ImageDraw, PngImagePlugin

import hangboard_packages.cord_render_assets as cord_render_assets
from hangboard_packages.cord_render_assets import (
    ChromaConfig,
    LockedSource,
    build_lossless_atlases,
    build_lossless_atlases_with_report,
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
    return _locked(
        _png(root / f"{source_id}.png", size, {}, background=color), source_id
    )


def _small_index(tmp_path: Path, prefix: str = "tamper") -> object:
    first = _context_source(tmp_path, f"{prefix}-first", (5, 4), (10, 20, 30))
    second = _context_source(tmp_path, f"{prefix}-second", (6, 3), (80, 90, 100))
    return build_lossless_atlases(
        [first, second], _context(tmp_path, f"atlas-{prefix}") / "pages"
    )


def _refreshed_source_digest(source: LockedSource) -> str:
    payload = source.to_json()
    payload.pop("canonicalDigest")
    return hashlib.sha256(
        json.dumps(
            {
                "digestVersion": 1,
                "kind": "cordLockedSource",
                "source": payload,
            },
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
    ).hexdigest()


def _file_bytes(root: Path) -> dict[str, bytes]:
    return {
        str(path.relative_to(root)): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def test_decoded_pixel_hash_ignores_png_container_metadata(tmp_path: Path) -> None:
    first = _png(tmp_path / "first.png", (3, 2), {(1, 1): (12, 34, 56)})
    second = tmp_path / "second.png"
    with Image.open(first) as image:
        metadata = PngImagePlugin.PngInfo()
        metadata.add_text("Comment", "different container metadata")
        image.save(second, format="PNG", pnginfo=metadata)

    assert (
        hashlib.sha256(first.read_bytes()).hexdigest()
        != hashlib.sha256(second.read_bytes()).hexdigest()
    )
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
    original_read = cord_render_assets.os.read
    reads = 0

    def observed_read(descriptor: int, count: int) -> bytes:
        nonlocal reads
        reads += 1
        return original_read(descriptor, count)

    monkeypatch.setattr(cord_render_assets.os, "read", observed_read)

    locked = _locked(source, "single-snapshot")
    cache_bytes = locked.cache_path.read_bytes()

    assert reads > 0
    assert hashlib.sha256(cache_bytes).hexdigest() == locked.byte_sha256
    assert decoded_pixel_sha256(locked.cache_path) == locked.decoded_pixel_sha256
    assert (locked.width, locked.height, locked.mode) == (4, 3, "RGB")


def test_lock_source_fails_if_path_is_replaced_while_snapshot_is_open(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    monkeypatch.setenv("PASEO_WORKTREE_PATH", str(workspace))
    source = _png(
        tmp_path / "replace-during-read.png", (4, 3), {}, background=(1, 2, 3)
    )
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


def test_lock_source_parent_swap_cannot_substitute_attacker_pixels(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    monkeypatch.setenv("PASEO_WORKTREE_PATH", str(workspace))
    trusted_parent = tmp_path / "trusted-parent"
    attacker_parent = tmp_path / "attacker-parent"
    trusted_parent.mkdir()
    attacker_parent.mkdir()
    source = _png(trusted_parent / "source.png", (4, 3), {}, background=(1, 2, 3))
    attacker = _png(
        attacker_parent / "source.png", (4, 3), {}, background=(200, 201, 202)
    )
    displaced = tmp_path / "trusted-parent-displaced"
    original_open = cord_render_assets.os.open
    hook_ran = False

    def racing_open(
        path: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        flags: int,
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> int:
        nonlocal hook_ran
        if not hook_ran and Path(os.fsdecode(path)).name == "source.png":
            hook_ran = True
            trusted_parent.rename(displaced)
            trusted_parent.symlink_to(attacker_parent, target_is_directory=True)
        return original_open(path, flags, mode, dir_fd=dir_fd)

    monkeypatch.setattr(cord_render_assets.os, "open", racing_open)

    with pytest.raises(ValueError, match="changed|symlink"):
        _locked(source, "parent-race")

    assert hook_ran is True
    assert attacker.read_bytes() == (attacker_parent / "source.png").read_bytes()
    assert not (
        workspace / ".context" / "joyful-donkey-cord-assets" / "sources" / "locked"
    ).exists()


def test_owner_write_parent_swap_cannot_redirect_outside_owner(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    context = _context(tmp_path, "output-parent-race")
    approved_parent = context / "reports"
    approved_parent.mkdir()
    displaced = context / "reports-displaced"
    outside = tmp_path / "outside"
    outside.mkdir()
    target = approved_parent / "report.json"
    original_open = cord_render_assets.os.open
    hook_ran = False

    def racing_open(
        path: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        flags: int,
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> int:
        nonlocal hook_ran
        name = Path(os.fsdecode(path)).name
        if not hook_ran and flags & os.O_CREAT and ".report.json.tmp-" in name:
            hook_ran = True
            approved_parent.rename(displaced)
            approved_parent.symlink_to(outside, target_is_directory=True)
        return original_open(path, flags, mode, dir_fd=dir_fd)

    monkeypatch.setattr(cord_render_assets.os, "open", racing_open)

    with pytest.raises(ValueError, match="changed|symlink"):
        cord_render_assets.write_owner_json(target, {"safe": True})

    assert hook_ran is True
    assert not (outside / "report.json").exists()
    assert not any(outside.iterdir())


def test_freeze_manifest_rejects_replacement_after_parse_without_stale_publication(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    context = _context(tmp_path, "manifest-lifetime-race")
    source_a = _png(tmp_path / "manifest-a.png", (4, 3), {}, background=(10, 20, 30))
    source_b = _png(tmp_path / "manifest-b.png", (4, 3), {}, background=(40, 50, 60))

    def record(path: Path, source_id: str) -> dict[str, object]:
        return {
            "path": str(path),
            "sourceID": source_id,
            "url": f"https://manufacturer.example/{source_id}",
            "publisher": "Fixture Manufacturer",
            "role": "product",
            "revision": "fixture-revision",
            "reviewedAt": "2026-09-02",
        }

    manifest = context / "sources" / "index.json"
    manifest.parent.mkdir(parents=True)
    manifest_a = json.dumps({"sources": [record(source_a, "manifest-a")]}).encode()
    manifest_b = json.dumps({"sources": [record(source_b, "manifest-b")]}).encode()
    manifest.write_bytes(manifest_a)
    replacement = manifest.with_name("replacement.json")
    replacement.write_bytes(manifest_b)
    report = context / "reports" / "source-lock.json"
    report.parent.mkdir(parents=True)
    prior_report = b"prior source-lock report\n"
    report.write_bytes(prior_report)
    stale_cache = (
        context
        / "sources"
        / "locked"
        / f"manifest-a-{hashlib.sha256(source_a.read_bytes()).hexdigest()}.png"
    )
    actual_snapshot = cord_render_assets._snapshot_image
    hook_ran = False

    def replacing_manifest_before_source_snapshot(
        path: Path,
    ) -> cord_render_assets._ImageSnapshot:
        nonlocal hook_ran
        if not hook_ran:
            hook_ran = True
            os.replace(replacement, manifest)
        return actual_snapshot(path)

    monkeypatch.setattr(
        cord_render_assets,
        "_snapshot_image",
        replacing_manifest_before_source_snapshot,
    )
    failure: ValueError | None = None
    try:
        cord_render_assets.freeze_source_manifest(manifest, report_path=report)
    except ValueError as error:
        failure = error

    assert hook_ran is True
    assert failure is not None, (
        "a replaced parsed manifest must not publish successfully"
    )
    assert isinstance(failure, ValueError)
    assert "manifest" in str(failure).lower() or "changed" in str(failure).lower()
    assert manifest.read_bytes() == manifest_b
    assert report.read_bytes() == prior_report
    assert not stale_cache.exists()


def test_lock_source_rejects_datetime_instead_of_emitting_invalid_lock(
    tmp_path: Path,
) -> None:
    source = _png(
        _context(tmp_path, "datetime") / "source.png",
        (3, 3),
        {},
        background=(1, 2, 3),
    )

    with pytest.raises(ValueError, match="immutable date"):
        lock_source(
            source,
            source_id="datetime",
            url="https://manufacturer.example/datetime",
            publisher="Fixture Manufacturer",
            role="product",
            revision="fixture-revision",
            reviewed_at=datetime(2026, 9, 2, 3, 4, 5),
        )


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


def test_atlas_accepts_five_lossless_pair_pages_that_source_order_defeats(
    tmp_path: Path,
) -> None:
    sources = []
    for pair in range(5):
        sources.append(
            _context_source(
                tmp_path,
                f"{pair * 2:02d}-shorter",
                (1000, 1015),
                (10 + pair, 60, 90),
            )
        )
        sources.append(
            _context_source(
                tmp_path,
                f"{pair * 2 + 1:02d}-taller",
                (1020, 1017),
                (20 + pair, 80, 110),
            )
        )

    index = build_lossless_atlases(
        sources, _context(tmp_path, "five-pair-pages") / "pages", max_pages=5
    )

    assert len(index.pages) <= 5
    assert verify_atlas_round_trip(index).verified_panels == 10


def test_atlas_size_aware_packing_accepts_mixed_tall_and_short_set_in_four_pages(
    tmp_path: Path,
) -> None:
    sources = []
    for number in range(12):
        sources.append(
            _context_source(
                tmp_path,
                f"{number:02d}-tall",
                (1000, 1000),
                (20 + number, 40, 80),
            )
        )
        sources.append(
            _context_source(
                tmp_path,
                f"{number:02d}-short",
                (1000, 100),
                (80, 20 + number, 40),
            )
        )

    index = build_lossless_atlases(
        sources, _context(tmp_path, "four-mixed-pages") / "pages", max_pages=5
    )

    assert len(index.pages) <= 4
    assert verify_atlas_round_trip(index).verified_panels == 24


def test_atlas_preserves_native_rgb_jpeg_and_rgba_panels_on_compatible_pages(
    tmp_path: Path,
) -> None:
    source_root = _context(tmp_path, "native-mode-sources")
    rgb_path = source_root / "manufacturer.jpg"
    rgb = Image.new("RGB", (9, 7), (21, 42, 63))
    rgb.putpixel((4, 3), (190, 120, 40))
    rgb.save(rgb_path, format="JPEG", quality=95, subsampling=0)
    rgba_path = source_root / "transparent-reference.png"
    rgba = Image.new("RGBA", (8, 6), (11, 22, 33, 0))
    rgba.putpixel((3, 2), (90, 80, 70, 255))
    rgba.putpixel((4, 2), (1, 2, 3, 127))
    rgba.save(rgba_path, format="PNG")
    sources = [_locked(rgb_path, "rgb-jpeg"), _locked(rgba_path, "rgba-png")]

    index = build_lossless_atlases(
        sources, _context(tmp_path, "native-mode-atlas") / "pages"
    )

    assert len(index.pages) == 2
    assert {page.mode for page in index.pages} == {"RGB", "RGBA"}
    page_by_number = {page.number: page for page in index.pages}
    source_by_id = {source.source_id: source for source in index.sources}
    for panel in index.panels:
        page_record = page_by_number[panel.page_number]
        source = source_by_id[panel.source_id]
        assert page_record.mode == panel.mode == source.mode
        with Image.open(page_record.path) as opened_page:
            opened_page.load()
            crop = opened_page.crop(
                (panel.x, panel.y, panel.x + panel.width, panel.y + panel.height)
            )
        with Image.open(source.cache_path) as opened_source:
            opened_source.load()
            native_source = opened_source.copy()
        assert crop.mode == native_source.mode == source.mode
        assert crop.size == native_source.size
        assert crop.tobytes() == native_source.tobytes()
        assert decoded_pixel_sha256(source.cache_path) == source.decoded_pixel_sha256
    assert verify_atlas_round_trip(index).verified_panels == 2


def test_atlas_enforces_one_global_five_page_budget_across_rgb_and_rgba(
    tmp_path: Path,
) -> None:
    sources = []
    for number, mode in enumerate(("RGB", "RGBA", "RGB", "RGBA", "RGB")):
        root = _context(tmp_path, f"global-mode-{number}")
        path = root / f"source-{number}.png"
        color = (
            (20 + number, 40, 60)
            if mode == "RGB"
            else (20 + number, 40, 60, 100 + number)
        )
        Image.new(mode, (1025, 1025), color).save(path, format="PNG")
        sources.append(_locked(path, f"global-mode-{number}"))

    index = build_lossless_atlases(
        sources,
        _context(tmp_path, "global-mode-budget") / "pages",
        max_pages=5,
    )

    assert len(index.pages) == 5
    assert [page.mode for page in index.pages].count("RGB") == 3
    assert [page.mode for page in index.pages].count("RGBA") == 2
    assert verify_atlas_round_trip(index).verified_panels == 5


def test_atlas_records_source_derived_bound_and_accepts_source_over_2048(
    tmp_path: Path,
) -> None:
    sources = [
        _context_source(tmp_path, "large", (2100, 10), (1, 2, 3)),
        *[
            _context_source(tmp_path, f"small-{number}", (10, 10), (number, 4, 5))
            for number in range(5)
        ],
    ]

    index = build_lossless_atlases(
        sources, _context(tmp_path, "source-derived-bound") / "pages"
    )

    assert index.max_dimension >= 2116
    assert verify_atlas_round_trip(index).verified_panels == 6


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

    with pytest.raises(ValueError, match=r"requires more than 5.*limit.*5"):
        build_lossless_atlases(
            sources, _context(tmp_path, "sixth-page") / "pages", max_pages=5
        )
    assert not {"crop", "resize", "rotate"}.intersection(
        inspect.signature(build_lossless_atlases).parameters
    )


@pytest.mark.parametrize(("source_count", "max_pages"), [(4, 2), (7, 5)])
def test_atlas_overflow_reports_only_the_proven_nonfit_lower_bound(
    tmp_path: Path, source_count: int, max_pages: int
) -> None:
    sources = [
        _context_source(
            tmp_path,
            f"lower-bound-{source_count}-{number}",
            (1025, 1025),
            (number + 1, 100, 200),
        )
        for number in range(source_count)
    ]

    with pytest.raises(
        ValueError,
        match=rf"requires more than {max_pages} atlas pages; limit is {max_pages}",
    ):
        build_lossless_atlases(
            sources,
            _context(tmp_path, f"lower-bound-{source_count}") / "pages",
            max_pages=max_pages,
        )


def test_atlas_search_exhaustion_remains_indeterminate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    sources = [
        _context_source(
            tmp_path,
            f"search-limit-{number}",
            (1025, 1025),
            (number + 1, 100, 200),
        )
        for number in range(2)
    ]
    output = _context(tmp_path, "search-limit") / "pages"
    monkeypatch.setattr(cord_render_assets, "_ATLAS_SEARCH_NODE_LIMIT", 0)

    with pytest.raises(
        ValueError,
        match="packing feasibility search limit reached; page overflow not proven",
    ):
        build_lossless_atlases(sources, output, max_pages=1)

    assert not output.exists()


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


def test_atlas_verifier_rejects_valid_value_source_provenance_tampering(
    tmp_path: Path,
) -> None:
    index = _small_index(tmp_path, "source-provenance")
    source = index.sources[0]
    changed_url = replace(source, url="https://different.example/valid-revision")

    with pytest.raises(ValueError, match="canonical|digest|provenance"):
        verify_atlas_round_trip(
            replace(index, sources=(changed_url, *index.sources[1:]))
        )
    refreshed_url = replace(
        changed_url, canonical_digest=_refreshed_source_digest(changed_url)
    )
    with pytest.raises(ValueError, match="source lock digest"):
        verify_atlas_round_trip(
            replace(index, sources=(refreshed_url, *index.sources[1:]))
        )

    changed_id = "renamed-source"
    renamed = replace(source, source_id=changed_id)
    panels = tuple(
        replace(panel, source_id=changed_id)
        if panel.source_id == source.source_id
        else panel
        for panel in index.panels
    )
    with pytest.raises(ValueError, match="canonical|digest|provenance"):
        verify_atlas_round_trip(
            replace(index, sources=(renamed, *index.sources[1:]), panels=panels)
        )


def test_atlas_verifier_rejects_noncanonical_cache_name_with_identical_bytes(
    tmp_path: Path,
) -> None:
    index = _small_index(tmp_path, "cache-name")
    source = index.sources[0]
    renamed_cache = source.cache_path.with_name("valid-looking-renamed-cache.png")
    shutil.copyfile(source.cache_path, renamed_cache)
    changed = replace(source, cache_path=renamed_cache.resolve())
    changed = replace(changed, canonical_digest=_refreshed_source_digest(changed))

    with pytest.raises(ValueError, match="cache path|canonical|digest"):
        verify_atlas_round_trip(
            replace(
                index,
                sources=(
                    changed,
                    *index.sources[1:],
                ),
            )
        )


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
        opened.load()
        image = opened.copy()
    changed_pixel = (1, 2, 3, 4) if image.mode == "RGBA" else (1, 2, 3)
    image.putpixel((0, 0), changed_pixel)
    image.save(page.path, format="PNG")

    with pytest.raises(ValueError, match="atlas page hash"):
        verify_atlas_round_trip(index)

    fresh = _small_index(tmp_path, "page-path")
    outside = tmp_path / "outside-page.png"
    outside.write_bytes(fresh.pages[0].path.read_bytes())
    escaped = replace(fresh, pages=(replace(fresh.pages[0], path=outside.resolve()),))
    with pytest.raises(ValueError, match="owner-named .context"):
        verify_atlas_round_trip(escaped)


def test_atlas_verifier_binds_exact_output_root_and_canonical_page_path(
    tmp_path: Path,
) -> None:
    index = _small_index(tmp_path, "bound-page-path")
    page = index.pages[0]
    relocated_root = _context(tmp_path, "relocated-page") / "pages"
    relocated_root.mkdir(parents=True)
    relocated = relocated_root / page.path.name
    shutil.copyfile(page.path, relocated)

    with pytest.raises(ValueError, match="output root|page path"):
        verify_atlas_round_trip(
            replace(index, pages=(replace(page, path=relocated.resolve()),))
        )


def test_atlas_verifier_reconstructs_padding_instead_of_trusting_page_hashes(
    tmp_path: Path,
) -> None:
    index = _small_index(tmp_path, "canonical-padding")
    page = index.pages[0]
    with Image.open(page.path) as opened:
        opened.load()
        image = opened.copy()
    changed_pixel = (255, 0, 0, 255) if image.mode == "RGBA" else (255, 0, 0)
    image.putpixel((0, 0), changed_pixel)
    image.save(page.path, format="PNG", optimize=False, compress_level=9)
    changed_bytes = page.path.read_bytes()
    tampered_page = replace(
        page,
        byte_sha256=hashlib.sha256(changed_bytes).hexdigest(),
        decoded_pixel_sha256=decoded_pixel_sha256(page.path),
    )
    tampered_index = replace(index, pages=(tampered_page,))
    canonical = tampered_index.to_json()
    canonical.pop("atlasIndexSHA256")
    refreshed_index_digest = hashlib.sha256(
        json.dumps(
            canonical,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
    ).hexdigest()
    tampered_index = replace(tampered_index, atlas_index_sha256=refreshed_index_digest)

    with pytest.raises(ValueError, match="canonical page (pixels|bytes)"):
        verify_atlas_round_trip(tampered_index)


def test_atlas_rebuild_removes_only_stale_canonical_pages(tmp_path: Path) -> None:
    first = _context_source(tmp_path, "rebuild-first", (2000, 1100), (1, 2, 3))
    second = _context_source(tmp_path, "rebuild-second", (2000, 1100), (4, 5, 6))
    output = _context(tmp_path, "rebuild-pages") / "pages"

    initial = build_lossless_atlases([first, second], output)
    assert len(initial.pages) == 2
    assert (output / "page-02.png").is_file()

    rebuilt = build_lossless_atlases([first], output)

    assert len(rebuilt.pages) == 1
    assert (output / "page-01.png").is_file()
    assert not (output / "page-02.png").exists()


def test_atlas_rebuild_rejects_unknown_files_without_deleting_them(
    tmp_path: Path,
) -> None:
    source = _context_source(tmp_path, "unknown-output-file")
    output = _context(tmp_path, "unknown-output") / "pages"
    output.mkdir(parents=True)
    unknown = output / "notes.txt"
    unknown.write_text("not an atlas artifact", encoding="utf-8")

    with pytest.raises(ValueError, match="unknown atlas output"):
        build_lossless_atlases([source], output)

    assert unknown.read_text(encoding="utf-8") == "not an atlas artifact"
    assert not (output / "page-01.png").exists()


def test_atlas_publication_failure_rolls_back_prior_page_set(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    original = _context_source(tmp_path, "rollback-original", color=(1, 2, 3))
    output = _context(tmp_path, "rollback-pages") / "pages"
    build_lossless_atlases([original], output)
    original_page = (output / "page-01.png").read_bytes()
    first = _context_source(tmp_path, "rollback-first", (2000, 1100), (4, 5, 6))
    second = _context_source(tmp_path, "rollback-second", (2000, 1100), (7, 8, 9))
    original_link = cord_render_assets.os.link
    hook_ran = False

    def failing_link(
        source: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        target: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        *,
        src_dir_fd: int | None = None,
        dst_dir_fd: int | None = None,
        follow_symlinks: bool = True,
    ) -> None:
        nonlocal hook_ran
        if not hook_ran and Path(os.fsdecode(target)).name == "page-02.png":
            hook_ran = True
            raise OSError("injected second-page publication failure")
        original_link(
            source,
            target,
            src_dir_fd=src_dir_fd,
            dst_dir_fd=dst_dir_fd,
            follow_symlinks=follow_symlinks,
        )

    monkeypatch.setattr(cord_render_assets.os, "link", failing_link)

    with pytest.raises(OSError, match="injected second-page"):
        build_lossless_atlases([first, second], output)

    assert hook_ran is True
    assert (output / "page-01.png").read_bytes() == original_page
    assert not (output / "page-02.png").exists()


def test_atlas_backup_cleanup_failure_restores_every_prior_artifact(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    original = _context_source(tmp_path, "cleanup-original", color=(1, 2, 3))
    output = _context(tmp_path, "cleanup-pages") / "pages"
    build_lossless_atlases([original], output)
    original_page = (output / "page-01.png").read_bytes()
    original_index = (output / "index.json").read_bytes()
    replacement = _context_source(tmp_path, "cleanup-replacement", color=(4, 5, 6))
    original_unlink = cord_render_assets.os.unlink
    backup_unlinks = 0
    hook_ran = False

    def failing_unlink(
        path: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        *,
        dir_fd: int | None = None,
    ) -> None:
        nonlocal backup_unlinks, hook_ran
        if ".backup-" in Path(os.fsdecode(path)).name:
            backup_unlinks += 1
            if backup_unlinks == 2 and not hook_ran:
                hook_ran = True
                raise OSError("injected backup cleanup failure")
        original_unlink(path, dir_fd=dir_fd)

    monkeypatch.setattr(cord_render_assets.os, "unlink", failing_unlink)

    with pytest.raises(OSError, match="injected backup cleanup"):
        build_lossless_atlases([replacement], output)

    assert hook_ran is True
    assert (output / "page-01.png").read_bytes() == original_page
    assert (output / "index.json").read_bytes() == original_index
    assert sorted(path.name for path in output.iterdir()) == [
        "index.json",
        "page-01.png",
    ]


def test_atlas_backup_cleanup_tamper_cannot_succeed_and_restores_prior_tree(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    original = _context_source(tmp_path, "cleanup-tamper-original", color=(1, 2, 3))
    output = _context(tmp_path, "cleanup-tamper-pages") / "pages"
    build_lossless_atlases([original], output)
    prior_tree = _file_bytes(output)
    replacement = _context_source(
        tmp_path, "cleanup-tamper-replacement", color=(4, 5, 6)
    )
    original_unlink = cord_render_assets.os.unlink
    hook_ran = False

    def tampering_first_backup_cleanup(
        path: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        *,
        dir_fd: int | None = None,
    ) -> None:
        nonlocal hook_ran
        if not hook_ran and ".backup-" in Path(os.fsdecode(path)).name:
            hook_ran = True
            (output / "page-01.png").write_bytes(b"tampered after final verification")
        original_unlink(path, dir_fd=dir_fd)

    monkeypatch.setattr(cord_render_assets.os, "unlink", tampering_first_backup_cleanup)
    failure: OSError | ValueError | None = None
    try:
        build_lossless_atlases([replacement], output)
    except (OSError, ValueError) as error:
        failure = error

    assert hook_ran is True
    assert failure is not None, "backup cleanup must not open a success window"
    assert isinstance(failure, (OSError, ValueError))
    assert _file_bytes(output) == prior_tree


def test_atlas_rollback_uses_payload_fallback_after_transient_backup_restore_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    original = _context_source(tmp_path, "rollback-fallback-original", color=(1, 2, 3))
    output = _context(tmp_path, "rollback-fallback-pages") / "pages"
    build_lossless_atlases([original], output)
    prior_tree = _file_bytes(output)
    replacement = _context_source(
        tmp_path, "rollback-fallback-replacement", color=(4, 5, 6)
    )
    actual_verifier = cord_render_assets.verify_atlas_round_trip
    original_replace = cord_render_assets.os.replace
    original_unlink = cord_render_assets.os.unlink
    callback_ran = False
    rollback_active = False
    restore_hook_ran = False
    visible_unlink_attempted = False

    def failing_validation_callback(
        index: cord_render_assets.AtlasIndex,
    ) -> cord_render_assets.AtlasVerification:
        nonlocal callback_ran, rollback_active
        callback_ran = True
        verification = actual_verifier(index)
        assert verification.valid is True
        rollback_active = True
        raise ValueError("injected validation callback failure")

    def failing_first_backup_restore(
        source: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        target: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        *,
        src_dir_fd: int | None = None,
        dst_dir_fd: int | None = None,
    ) -> None:
        nonlocal restore_hook_ran
        source_name = Path(os.fsdecode(source)).name
        if rollback_active and not restore_hook_ran and ".backup-" in source_name:
            restore_hook_ran = True
            raise OSError("injected transient backup restore failure")
        original_replace(
            source,
            target,
            src_dir_fd=src_dir_fd,
            dst_dir_fd=dst_dir_fd,
        )

    def rejecting_visible_preunlink(
        path: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        *,
        dir_fd: int | None = None,
    ) -> None:
        nonlocal visible_unlink_attempted
        if rollback_active and Path(os.fsdecode(path)).name in {
            "page-01.png",
            "index.json",
        }:
            visible_unlink_attempted = True
            raise AssertionError("rollback must not pre-unlink a visible artifact")
        original_unlink(path, dir_fd=dir_fd)

    monkeypatch.setattr(
        cord_render_assets, "verify_atlas_round_trip", failing_validation_callback
    )
    monkeypatch.setattr(cord_render_assets.os, "replace", failing_first_backup_restore)
    monkeypatch.setattr(cord_render_assets.os, "unlink", rejecting_visible_preunlink)

    with pytest.raises(ValueError, match="injected validation callback failure"):
        build_lossless_atlases([replacement], output)

    assert callback_ran is True
    assert restore_hook_ran is True
    assert visible_unlink_attempted is False
    assert _file_bytes(output) == prior_tree
    assert not any(path.name.startswith(".") for path in output.iterdir())


def test_atlas_rollback_surfaces_unproven_state_when_all_restore_paths_fail(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    original = _context_source(tmp_path, "rollback-unproven-original", color=(1, 2, 3))
    output = _context(tmp_path, "rollback-unproven-pages") / "pages"
    build_lossless_atlases([original], output)
    prior_page = (output / "page-01.png").read_bytes()
    replacement = _context_source(
        tmp_path, "rollback-unproven-replacement", color=(4, 5, 6)
    )
    actual_verifier = cord_render_assets.verify_atlas_round_trip
    original_replace = cord_render_assets.os.replace
    callback_ran = False
    rollback_active = False
    backup_restore_hook_ran = False
    fallback_restore_hook_ran = False

    def failing_validation_callback(
        index: cord_render_assets.AtlasIndex,
    ) -> cord_render_assets.AtlasVerification:
        nonlocal callback_ran, rollback_active
        callback_ran = True
        verification = actual_verifier(index)
        assert verification.valid is True
        rollback_active = True
        raise ValueError("injected persistent validation callback failure")

    def failing_all_restore_replacements(
        source: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        target: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        *,
        src_dir_fd: int | None = None,
        dst_dir_fd: int | None = None,
    ) -> None:
        nonlocal backup_restore_hook_ran, fallback_restore_hook_ran
        source_name = Path(os.fsdecode(source)).name
        if rollback_active and source_name.startswith(".index.json.backup-"):
            backup_restore_hook_ran = True
            raise OSError("injected persistent backup restore failure")
        if rollback_active and source_name.startswith(".index.json.restore-"):
            fallback_restore_hook_ran = True
            raise OSError("injected persistent payload restore failure")
        original_replace(
            source,
            target,
            src_dir_fd=src_dir_fd,
            dst_dir_fd=dst_dir_fd,
        )

    monkeypatch.setattr(
        cord_render_assets, "verify_atlas_round_trip", failing_validation_callback
    )
    monkeypatch.setattr(
        cord_render_assets.os, "replace", failing_all_restore_replacements
    )

    with pytest.raises(Exception) as captured:
        build_lossless_atlases([replacement], output)

    assert callback_ran is True
    assert backup_restore_hook_ran is True
    assert fallback_restore_hook_ran is True
    message = str(captured.value).lower()
    assert "rollback" in message
    assert "unproven" in message or "not be proven" in message
    causes: list[str] = []
    cause: BaseException | None = captured.value
    while cause is not None:
        causes.append(str(cause))
        cause = cause.__cause__
    assert any("persistent validation callback failure" in text for text in causes)
    assert (output / "page-01.png").read_bytes() == prior_page


def test_atlas_final_verifier_failure_restores_prior_pages_index_report_and_stale_page(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    original_sources = [
        _context_source(
            tmp_path,
            f"postverify-original-{number}",
            (2000, 1100),
            (10 + number, 20, 30),
        )
        for number in range(2)
    ]
    context = _context(tmp_path, "postverify-rollback")
    output = context / "pages"
    external_report = context / "reports" / "atlas-report.json"
    initial = build_lossless_atlases_with_report(
        original_sources, output, report_path=external_report
    )
    assert len(initial.pages) == 2
    prior_output = _file_bytes(output)
    prior_report_tree = _file_bytes(external_report.parent)
    replacement = _context_source(
        tmp_path, "postverify-replacement", (12, 8), (200, 100, 50)
    )
    actual_verifier = cord_render_assets.verify_atlas_round_trip
    hook_ran = False

    def failing_final_verifier(
        index: cord_render_assets.AtlasIndex,
    ) -> cord_render_assets.AtlasVerification:
        nonlocal hook_ran
        hook_ran = True
        verification = actual_verifier(index)
        assert verification.valid is True
        raise ValueError("injected final verification failure")

    monkeypatch.setattr(
        cord_render_assets, "verify_atlas_round_trip", failing_final_verifier
    )

    with pytest.raises(ValueError, match="injected final verification failure"):
        build_lossless_atlases_with_report(
            [replacement], output, report_path=external_report
        )

    assert hook_ran is True
    assert _file_bytes(output) == prior_output
    assert _file_bytes(external_report.parent) == prior_report_tree
    assert "page-02.png" in prior_output


def test_atlas_final_verifier_failure_removes_initial_publication(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = _context_source(tmp_path, "postverify-new")
    context = _context(tmp_path, "postverify-new-output")
    output = context / "pages"
    external_report = context / "reports" / "report.json"
    actual_verifier = cord_render_assets.verify_atlas_round_trip
    hook_ran = False

    def failing_final_verifier(
        index: cord_render_assets.AtlasIndex,
    ) -> cord_render_assets.AtlasVerification:
        nonlocal hook_ran
        hook_ran = True
        verification = actual_verifier(index)
        assert verification.valid is True
        raise ValueError("injected first-build verification failure")

    monkeypatch.setattr(
        cord_render_assets, "verify_atlas_round_trip", failing_final_verifier
    )

    with pytest.raises(ValueError, match="injected first-build verification failure"):
        build_lossless_atlases_with_report(
            [source], output, report_path=external_report
        )

    assert hook_ran is True
    assert not output.exists()
    assert not external_report.exists()
    assert not external_report.parent.exists()


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


@pytest.mark.parametrize("mode", ["1", "L", "LA", "P"])
def test_atlas_rejects_unsupported_native_modes_before_publication(
    tmp_path: Path, mode: str
) -> None:
    root = _context(tmp_path, f"unsupported-{mode}")
    if mode == "1":
        image = Image.new(mode, (5, 4), 1)
    elif mode == "L":
        image = Image.new(mode, (5, 4), 120)
    elif mode == "LA":
        image = Image.new(mode, (5, 4), (120, 200))
    else:
        image = Image.new("P", (5, 4), 0)
        image.putpalette([255, 0, 0] + [0, 0, 0] * 255)
    source_path = root / "source.png"
    image.save(source_path, format="PNG")
    source = _locked(source_path, f"unsupported-{mode}")
    output = _context(tmp_path, f"unsupported-{mode}-output") / "pages"

    with pytest.raises(ValueError) as error:
        build_lossless_atlases([source], output)

    assert "unsupported atlas source mode" in str(error.value)
    assert mode in str(error.value)
    assert "RGB and RGBA" in str(error.value)
    assert not output.exists()


def test_atlas_rejects_high_bit_mode_before_publication(tmp_path: Path) -> None:
    root = _context(tmp_path, "high-bit-atlas-source")
    high_bit = Image.new("I;16", (5, 4))
    high_bit.putdata(range(20))
    high_bit_path = root / "high-bit.png"
    high_bit.save(high_bit_path, format="PNG")
    high_bit_source = _locked(high_bit_path, "high-bit-atlas")
    output = _context(tmp_path, "high-bit-atlas-output") / "pages"

    with pytest.raises(ValueError, match="unsupported atlas source mode"):
        build_lossless_atlases([high_bit_source], output)

    assert not output.exists()


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


@pytest.mark.parametrize("textured", [False, True])
def test_transparency_inspection_rejects_substantial_alpha_254_matte(
    tmp_path: Path, textured: bool
) -> None:
    image = Image.new("RGBA", (20, 20), (20, 30, 100, 254))
    for x in range(20):
        for y in range(20):
            if textured and (x + y) % 2:
                image.putpixel((x, y), (80, 30, 20, 254))
    for point in ((0, 0), (19, 0), (0, 19), (19, 19)):
        image.putpixel(point, (0, 0, 0, 0))
    for x in range(8, 12):
        for y in range(8, 12):
            image.putpixel((x, y), (90, 80, 70, 255))
    path = tmp_path / f"alpha-254-{'textured' if textured else 'flat'}.png"
    image.save(path, format="PNG")

    with pytest.raises(ValueError, match="boundary .*flood"):
        inspect_transparency(path, 20, 20, (0, 255, 0))


def test_transparency_inspection_rejects_one_pixel_inset_near_opaque_matte(
    tmp_path: Path,
) -> None:
    image = Image.new("RGBA", (24, 24), (0, 0, 0, 0))
    for x in range(1, 23):
        for y in range(1, 23):
            color = (20, 30, 100) if (x + y) % 2 else (70, 20, 30)
            image.putpixel((x, y), (*color, 254))
    for x in range(9, 15):
        for y in range(9, 15):
            image.putpixel((x, y), (90, 80, 70, 255))
    path = tmp_path / "inset-alpha-254-matte.png"
    image.save(path, format="PNG")

    with pytest.raises(ValueError, match="boundary .*flood"):
        inspect_transparency(path, 24, 24, (0, 255, 0))


@pytest.mark.parametrize("inset", [2, 3, 4])
@pytest.mark.parametrize("textured", [False, True])
def test_transparency_inspection_rejects_scale_enveloped_inset_alpha_254_matte(
    tmp_path: Path, inset: int, textured: bool
) -> None:
    image = Image.new("RGBA", (40, 40), (0, 0, 0, 0))
    for x in range(inset, 40 - inset):
        for y in range(inset, 40 - inset):
            color = (25, 35, 95) if not textured or (x + y) % 2 else (85, 25, 35)
            image.putpixel((x, y), (*color, 254))
    for x in range(16, 24):
        for y in range(16, 24):
            image.putpixel((x, y), (90, 80, 70, 255))
    path = tmp_path / f"inset-{inset}-{'textured' if textured else 'flat'}.png"
    image.save(path, format="PNG")

    with pytest.raises(ValueError, match="boundary .*flood"):
        inspect_transparency(path, 40, 40, (0, 255, 0))


def test_transparency_inspection_rejects_proportional_production_size_inset_matte(
    tmp_path: Path,
) -> None:
    width, height = 1536, 1024
    inset = 21
    image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    matte = Image.new(
        "RGBA",
        (width - inset * 2, height - inset * 2),
        (30, 40, 100, 254),
    )
    image.paste(matte, (inset, inset))
    for x in range(inset, width - inset, 32):
        for y in range(inset, height - inset):
            image.putpixel((x, y), (90, 30, 20, 254))
    path = tmp_path / "production-inset-alpha-254.png"
    image.save(path, format="PNG")

    with pytest.raises(ValueError, match="boundary .*flood"):
        inspect_transparency(path, width, height, (0, 255, 0))


@pytest.mark.parametrize(
    ("size", "inset", "alpha", "textured"),
    [
        ((100, 100), 5, 254, True),
        ((1536, 1024), 22, 254, True),
        ((100, 100), 0, 249, False),
    ],
    ids=["small-envelope-plus-one", "production-envelope-plus-one", "alpha-249"],
)
def test_transparency_inspection_rejects_near_full_mattes_beyond_seed_cutoffs(
    tmp_path: Path,
    size: tuple[int, int],
    inset: int,
    alpha: int,
    textured: bool,
) -> None:
    width, height = size
    image = Image.new("RGBA", size, (0, 0, 0, 0))
    matte = Image.new(
        "RGBA",
        (width - inset * 2, height - inset * 2),
        (30, 40, 100, alpha),
    )
    image.paste(matte, (inset, inset))
    if textured:
        for x in range(inset, width - inset, 16):
            for y in range(inset, height - inset):
                image.putpixel((x, y), (90, 30, 20, alpha))
    for point in ((0, 0), (width - 1, 0), (0, height - 1), (width - 1, height - 1)):
        image.putpixel(point, (0, 0, 0, 0))
    path = tmp_path / f"near-full-{width}x{height}-inset-{inset}-alpha-{alpha}.png"
    image.save(path, format="PNG")

    with pytest.raises(ValueError, match="boundary .*flood"):
        inspect_transparency(path, width, height, (0, 255, 0))


@pytest.mark.parametrize("alpha", range(249, 256))
@pytest.mark.parametrize("textured", [False, True])
@pytest.mark.parametrize("rim_fraction", [0.02, 0.05, 0.08])
def test_transparency_inspection_rejects_alpha_family_with_normalized_shallow_rims(
    tmp_path: Path,
    alpha: int,
    textured: bool,
    rim_fraction: float,
) -> None:
    width, height = 160, 100
    inset = max(1, round(min(width, height) * rim_fraction))
    image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rectangle(
        (inset, inset, width - inset - 1, height - inset - 1),
        fill=(30, 40, 100, alpha),
    )
    if textured:
        for x in range(inset, width - inset, 13):
            draw.line(
                (x, inset, x, height - inset - 1),
                fill=(90, 30, 20, alpha),
            )
    path = tmp_path / (
        f"normalized-rim-{rim_fraction}-{alpha}-"
        f"{'textured' if textured else 'flat'}.png"
    )
    image.save(path, format="PNG")

    with pytest.raises(ValueError, match="boundary .*flood"):
        inspect_transparency(path, width, height, (0, 255, 0))


def test_transparency_inspection_allows_substantial_isolated_central_product(
    tmp_path: Path,
) -> None:
    image = Image.new("RGBA", (40, 40), (0, 0, 0, 0))
    for x in range(8, 32):
        for y in range(10, 30):
            image.putpixel((x, y), (90, 80, 70, 255))
    path = tmp_path / "central-product.png"
    image.save(path, format="PNG")

    report = inspect_transparency(path, 40, 40, (0, 255, 0))

    assert report.boundary_connected_opaque_flood_count == 0


def test_transparency_inspection_allows_disconnected_units_spanning_canvas(
    tmp_path: Path,
) -> None:
    width, height = 200, 120
    image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    for box in (
        (5, 30, 45, 70),
        (155, 30, 195, 70),
        (65, 5, 95, 25),
        (105, 95, 135, 115),
    ):
        draw.rounded_rectangle(box, radius=6, fill=(90, 80, 70, 255))
    path = tmp_path / "disconnected-units-spanning-canvas.png"
    image.save(path, format="PNG")

    report = inspect_transparency(path, width, height, (0, 255, 0))

    assert report.boundary_connected_opaque_flood_count == 0


def test_transparency_inspection_allows_tall_thin_product(tmp_path: Path) -> None:
    width, height = 120, 200
    image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    ImageDraw.Draw(image).rounded_rectangle(
        (50, 8, 69, 191),
        radius=8,
        fill=(90, 80, 70, 255),
    )
    path = tmp_path / "tall-thin-product.png"
    image.save(path, format="PNG")

    report = inspect_transparency(path, width, height, (0, 255, 0))

    assert report.boundary_connected_opaque_flood_count == 0


@pytest.mark.parametrize("halo_width", [1, 2, 3])
def test_transparency_inspection_allows_narrow_antialias_halo(
    tmp_path: Path, halo_width: int
) -> None:
    width = height = 100
    image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle(
        (19, 19, 80, 80),
        radius=12,
        fill=(90, 80, 70, 72),
    )
    draw.rounded_rectangle(
        (
            19 + halo_width,
            19 + halo_width,
            80 - halo_width,
            80 - halo_width,
        ),
        radius=max(1, 12 - halo_width),
        fill=(90, 80, 70, 255),
    )
    path = tmp_path / f"antialias-halo-{halo_width}.png"
    image.save(path, format="PNG")

    report = inspect_transparency(path, width, height, (0, 255, 0))

    assert report.boundary_connected_opaque_flood_count == 0


@pytest.mark.parametrize("coverage", [0.50, 0.65])
@pytest.mark.parametrize("rounded", [False, True])
def test_transparency_inspection_allows_large_central_product_shapes(
    tmp_path: Path, coverage: float, rounded: bool
) -> None:
    width = height = 200
    side = round(math.sqrt(coverage) * width)
    inset = (width - side) // 2
    image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    box = (inset, inset, inset + side - 1, inset + side - 1)
    if rounded:
        draw.rounded_rectangle(box, radius=side // 6, fill=(90, 80, 70, 255))
    else:
        draw.rectangle(box, fill=(90, 80, 70, 255))
    path = tmp_path / f"central-{coverage}-{'rounded' if rounded else 'square'}.png"
    image.save(path, format="PNG")

    report = inspect_transparency(path, width, height, (0, 255, 0))

    assert report.boundary_connected_opaque_flood_count == 0


def test_transparency_inspection_allows_wide_board_with_tensioned_cord_contacts(
    tmp_path: Path,
) -> None:
    width, height = 160, 100
    image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    for x in range(10, 150):
        for y in range(55, 85):
            image.putpixel((x, y), (90, 80, 70, 255))
    for x in range(29, 32):
        for y in range(56):
            image.putpixel((x, y), (25, 25, 25, 254))
    for x in range(128, 131):
        for y in range(56):
            image.putpixel((x, y), (25, 25, 25, 254))
    path = tmp_path / "wide-board-and-cords.png"
    image.save(path, format="PNG")

    report = inspect_transparency(path, width, height, (0, 255, 0))

    assert report.boundary_connected_opaque_flood_count == 0


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


def test_transparency_inspection_allows_small_near_opaque_cord_contact_and_antialias(
    tmp_path: Path,
) -> None:
    image = Image.new("RGBA", (20, 20), (0, 0, 0, 0))
    for y, alpha in enumerate((254, 254, 220, 180)):
        image.putpixel((10, y), (30, 30, 30, alpha))
    for x in range(8, 13):
        for y in range(8, 13):
            image.putpixel((x, y), (90, 80, 70, 255))
    path = tmp_path / "small-near-opaque-contact.png"
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

    assert (
        inspect.signature(remove_chroma).parameters["config"].default
        is inspect.Signature.empty
    )
    with pytest.raises(ValueError, match="in place"):
        remove_chroma(raw, raw, ChromaConfig())
    with pytest.raises(ValueError, match="owner-named .context"):
        remove_chroma(raw, Path("/tmp/outside.png"), ChromaConfig())
