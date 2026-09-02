from __future__ import annotations

import hashlib
import inspect
import json
import math
import os
import shutil
import subprocess
import sys
import threading
import time
from dataclasses import replace
from datetime import date, datetime
from pathlib import Path

import hangboard_packages.cord_render_assets as cord_render_assets
import pytest
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
from PIL import Image, ImageDraw, PngImagePlugin


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


def _path_identity(path: Path) -> tuple[int, int]:
    metadata = path.stat(follow_symlinks=False)
    return metadata.st_dev, metadata.st_ino


def _retained_paths_with_identity(
    root: Path,
    *,
    identity: tuple[int, int],
    payload: bytes,
    excluding: Path,
) -> list[Path]:
    return [
        candidate
        for candidate in root.rglob("*")
        if candidate != excluding
        and candidate.is_file()
        and _path_identity(candidate) == identity
        and candidate.read_bytes() == payload
    ]


def _exception_chain_messages(error: BaseException) -> list[str]:
    messages: list[str] = []
    seen: set[int] = set()
    current: BaseException | None = error
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        messages.append(str(current))
        current = current.__cause__
    return messages


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
    failure: Exception | None = None
    try:
        cord_render_assets.freeze_source_manifest(manifest, report_path=report)
    except Exception as error:  # noqa: BLE001 - inspect the complete failure chain
        failure = error

    assert hook_ran is True
    assert failure is not None, (
        "a replaced parsed manifest must not publish successfully"
    )
    assert isinstance(failure, RuntimeError)
    assert "rollback" in str(failure).lower()
    assert "unproven" in str(failure).lower()
    assert any(
        "manifest" in message.lower() or "changed" in message.lower()
        for message in _exception_chain_messages(failure)
    )
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


def test_same_owner_atlas_writers_serialize_planning_before_stale_page_selection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    initial = _context_source(tmp_path, "serialized-atlas-initial")
    output = _context(tmp_path, "serialized-atlas-output") / "pages"
    build_lossless_atlases([initial], output)
    two_page_sources = [
        _context_source(
            tmp_path,
            f"serialized-atlas-two-page-{number}",
            (2000, 1100),
            (20 + number, 40, 60),
        )
        for number in range(2)
    ]
    one_page_source = _context_source(tmp_path, "serialized-atlas-one-page")
    original_prepare = cord_render_assets._prepare_atlas
    first_prepared = threading.Event()
    second_prepared = threading.Event()
    release_first = threading.Event()
    release_second = threading.Event()
    results: dict[str, cord_render_assets.AtlasIndex] = {}
    failures: dict[str, Exception] = {}

    def pause_after_planning(
        sources: list[cord_render_assets.LockedSource]
        | tuple[cord_render_assets.LockedSource, ...],
        output_dir: Path,
        max_pages: int,
    ) -> tuple[
        cord_render_assets.AtlasIndex,
        list[tuple[Path, bytes]],
        tuple[Path, ...],
    ]:
        prepared = original_prepare(sources, output_dir, max_pages)
        if threading.current_thread().name == "two-page-atlas-writer":
            first_prepared.set()
            if not release_first.wait(timeout=5):
                raise TimeoutError("timed out releasing two-page atlas writer")
        else:
            second_prepared.set()
            if not release_second.wait(timeout=5):
                raise TimeoutError("timed out releasing one-page atlas writer")
        return prepared

    monkeypatch.setattr(cord_render_assets, "_prepare_atlas", pause_after_planning)

    def build(writer: str) -> None:
        sources = two_page_sources if writer == "two-page" else [one_page_source]
        try:
            results[writer] = build_lossless_atlases(sources, output)
        except Exception as error:  # noqa: BLE001 - assert thread failures below
            failures[writer] = error

    first_thread = threading.Thread(
        target=build,
        args=("two-page",),
        name="two-page-atlas-writer",
    )
    second_thread = threading.Thread(
        target=build,
        args=("one-page",),
        name="one-page-atlas-writer",
    )
    first_thread.start()
    assert first_prepared.wait(timeout=5)
    second_thread.start()
    second_planned_while_first_paused = second_prepared.wait(timeout=0.25)
    release_first.set()
    first_thread.join(timeout=5)
    assert first_thread.is_alive() is False
    assert second_prepared.wait(timeout=5)
    release_second.set()
    second_thread.join(timeout=5)

    assert second_planned_while_first_paused is False
    assert second_thread.is_alive() is False
    assert failures == {}
    assert set(results) == {"two-page", "one-page"}
    assert len(results["two-page"].pages) == 2
    assert len(results["one-page"].pages) == 1
    assert sorted(path.name for path in output.iterdir()) == [
        "index.json",
        "page-01.png",
    ]
    assert verify_atlas_round_trip(results["one-page"]).valid is True


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


def test_atlas_backup_cleanup_failure_keeps_every_committed_artifact(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    original = _context_source(tmp_path, "cleanup-original", color=(1, 2, 3))
    output = _context(tmp_path, "cleanup-pages") / "pages"
    build_lossless_atlases([original], output)
    replacement = _context_source(tmp_path, "cleanup-replacement", color=(4, 5, 6))
    build_lossless_atlases([replacement], output)
    expected_page = (output / "page-01.png").read_bytes()
    expected_index = (output / "index.json").read_bytes()
    build_lossless_atlases([original], output)
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

    with pytest.raises(RuntimeError) as captured:
        build_lossless_atlases([replacement], output)

    assert hook_ran is True
    assert (output / "page-01.png").read_bytes() == expected_page
    assert (output / "index.json").read_bytes() == expected_index
    assert "publication committed" in str(captured.value).lower()
    assert "cleanup state is unproven" in str(captured.value).lower()
    assert any(
        "injected backup cleanup failure" in message
        for message in _exception_chain_messages(captured.value)
    )


def test_atlas_backup_cleanup_tamper_is_preserved_after_commit_and_disclosed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    original = _context_source(tmp_path, "cleanup-tamper-original", color=(1, 2, 3))
    output = _context(tmp_path, "cleanup-tamper-pages") / "pages"
    build_lossless_atlases([original], output)
    replacement = _context_source(
        tmp_path, "cleanup-tamper-replacement", color=(4, 5, 6)
    )
    build_lossless_atlases([replacement], output)
    expected_index = (output / "index.json").read_bytes()
    build_lossless_atlases([original], output)
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
    failure: Exception | None = None
    try:
        build_lossless_atlases([replacement], output)
    except Exception as error:  # noqa: BLE001 - inspect the complete failure chain
        failure = error

    assert hook_ran is True
    assert failure is not None, "backup cleanup must not open a success window"
    assert isinstance(failure, RuntimeError)
    assert "publication committed" in str(failure).lower()
    assert "cleanup state is unproven" in str(failure).lower()
    assert (output / "page-01.png").read_bytes() == (
        b"tampered after final verification"
    )
    assert (output / "index.json").read_bytes() == expected_index


def test_delete_cleanup_concurrent_create_survives_with_unproven_committed_cleanup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    context = _context(tmp_path, "delete-cleanup-concurrent-create")
    target = context / "stale-report.json"
    target.write_bytes(b"prior-stale-report")
    concurrent_payload = b"concurrent-operator-create-after-delete"
    original_unlink = cord_render_assets.os.unlink
    hook_ran = False

    def create_visible_during_prior_cleanup(
        path: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        *,
        dir_fd: int | None = None,
    ) -> None:
        nonlocal hook_ran
        if not hook_ran and ".backup-" in Path(os.fsdecode(path)).name:
            hook_ran = True
            target.write_bytes(concurrent_payload)
        original_unlink(path, dir_fd=dir_fd)

    monkeypatch.setattr(
        cord_render_assets.os,
        "unlink",
        create_visible_during_prior_cleanup,
    )

    with pytest.raises(Exception) as captured:
        cord_render_assets._publish_artifacts(
            [cord_render_assets._Publication(target, None, "stale report")]
        )

    assert hook_ran is True
    assert target.read_bytes() == concurrent_payload
    assert concurrent_payload in _file_bytes(context).values()
    assert isinstance(captured.value, RuntimeError)
    assert "publication committed" in str(captured.value).lower()
    assert "cleanup state is unproven" in str(captured.value).lower()
    assert captured.value.__cause__ is not None
    assert any(
        "deleted artifact remains visible" in message
        for message in _exception_chain_messages(captured.value)
    )


def test_scratch_mkdir_post_create_failure_retains_first_name_without_retry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    context = _context(tmp_path, "scratch-mkdir-post-create-failure")
    target = context / "report.json"
    original_mkdir = cord_render_assets.os.mkdir
    scratch_mkdir_names: list[str] = []

    def failing_after_first_scratch_mkdir(
        path: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> None:
        name = Path(os.fsdecode(path)).name
        if name.startswith(f".{target.name}.txn-"):
            scratch_mkdir_names.append(name)
            if len(scratch_mkdir_names) == 1:
                original_mkdir(path, mode, dir_fd=dir_fd)
                raise OSError("injected after real scratch mkdir")
        original_mkdir(path, mode, dir_fd=dir_fd)

    monkeypatch.setattr(
        cord_render_assets.os, "mkdir", failing_after_first_scratch_mkdir
    )

    with pytest.raises(Exception) as captured:
        cord_render_assets.write_owner_json(target, {"new": True})

    assert len(scratch_mkdir_names) == 1
    retained_scratch_name = scratch_mkdir_names[0]
    retained_scratch_names = sorted(
        path.name
        for path in context.iterdir()
        if path.name.startswith(f".{target.name}.txn-")
    )
    assert retained_scratch_names == [retained_scratch_name]
    assert not target.exists()
    assert isinstance(captured.value, RuntimeError)
    error_message = str(captured.value)
    assert "rollback" in error_message.lower()
    assert "unproven" in error_message.lower()
    assert "debris" in error_message.lower()
    assert retained_scratch_name in error_message
    assert captured.value.__cause__ is not None
    assert any(
        "injected after real scratch mkdir" in message
        for message in _exception_chain_messages(captured.value)
    )


@pytest.mark.parametrize(
    ("failing_component", "expected_retained_directories"),
    [
        ("created-a", ("created-a",)),
        ("created-b", ("created-a", "created-a/created-b")),
    ],
    ids=("first-missing-parent", "later-missing-parent"),
)
def test_nested_parent_mkdir_post_create_failure_retains_and_discloses_uncertainty(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failing_component: str,
    expected_retained_directories: tuple[str, ...],
) -> None:
    context = _context(tmp_path, f"parent-mkdir-post-create-{failing_component}")
    target = context / "created-a" / "created-b" / "report.json"
    uncertain_path = (
        context / "created-a"
        if failing_component == "created-a"
        else context / "created-a" / "created-b"
    )
    original_dup = cord_render_assets.os.dup
    original_close = cord_render_assets.os.close
    original_mkdir = cord_render_assets.os.mkdir
    creation_ledger_fds: list[int] = []
    closed_fds: list[int] = []
    parent_mkdir_names: list[str] = []
    uncertain_identity: tuple[int, int] | None = None

    def tracking_dup(descriptor: int) -> int:
        duplicate = original_dup(descriptor)
        creation_ledger_fds.append(duplicate)
        return duplicate

    def tracking_close(descriptor: int) -> None:
        closed_fds.append(descriptor)
        original_close(descriptor)

    def failing_after_real_parent_mkdir(
        path: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> None:
        nonlocal uncertain_identity
        name = Path(os.fsdecode(path)).name
        if name in {"created-a", "created-b"}:
            parent_mkdir_names.append(name)
        if name == failing_component:
            assert parent_mkdir_names.count(name) == 1
            assert dir_fd is not None
            original_mkdir(path, mode, dir_fd=dir_fd)
            metadata = os.stat(path, dir_fd=dir_fd, follow_symlinks=False)
            uncertain_identity = (metadata.st_dev, metadata.st_ino)
            raise OSError(f"injected after real parent mkdir: {name}")
        original_mkdir(path, mode, dir_fd=dir_fd)

    monkeypatch.setattr(cord_render_assets.os, "dup", tracking_dup)
    monkeypatch.setattr(cord_render_assets.os, "close", tracking_close)
    monkeypatch.setattr(
        cord_render_assets.os,
        "mkdir",
        failing_after_real_parent_mkdir,
    )

    with pytest.raises(Exception) as captured:
        cord_render_assets.write_owner_json(target, {"new": True})

    expected_mkdir_names = (
        ["created-a"]
        if failing_component == "created-a"
        else ["created-a", "created-b"]
    )
    retained_directories = sorted(
        path.relative_to(context).as_posix()
        for path in context.rglob("*")
        if path.is_dir()
    )
    assert parent_mkdir_names == expected_mkdir_names
    assert uncertain_identity is not None
    uncertain_metadata = uncertain_path.stat()
    assert (uncertain_metadata.st_dev, uncertain_metadata.st_ino) == uncertain_identity
    assert retained_directories == list(expected_retained_directories)
    assert _file_bytes(context) == {}
    assert not target.exists()
    assert creation_ledger_fds
    assert set(creation_ledger_fds) <= set(closed_fds)
    for descriptor in creation_ledger_fds:
        with pytest.raises(OSError):
            os.fstat(descriptor)
    assert isinstance(captured.value, RuntimeError)
    error_message = str(captured.value)
    assert "rollback" in error_message.lower()
    assert "unproven" in error_message.lower()
    assert str(uncertain_path) in error_message
    assert captured.value.__cause__ is not None
    assert any(
        f"injected after real parent mkdir: {failing_component}" in message
        for message in _exception_chain_messages(captured.value)
    )


def test_same_payload_foreign_inode_at_rollback_capture_is_preserved_as_unproven(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    context = _context(tmp_path, "same-payload-foreign-inode")
    target = context / "report.json"
    prior_payload = b"identical-prior-payload"
    transaction_payload = b"transaction-publication"
    target.write_bytes(prior_payload)
    prior_identity = _path_identity(target)
    callback_failure = ValueError("injected same-payload callback failure")
    original_rename = cord_render_assets.os.rename
    original_replace = cord_render_assets.os.replace
    rollback_active = False
    capture_hook_count = 0
    transaction_identity: tuple[int, int] | None = None
    foreign_identity: tuple[int, int] | None = None
    payload_seen_at_capture: bytes | None = None

    def fail_validation() -> None:
        nonlocal rollback_active
        rollback_active = True
        raise callback_failure

    def replace_at_real_rollback_capture(
        source: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        destination: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        *,
        src_dir_fd: int | None = None,
        dst_dir_fd: int | None = None,
    ) -> None:
        nonlocal capture_hook_count, foreign_identity
        nonlocal payload_seen_at_capture, transaction_identity
        source_name = Path(os.fsdecode(source)).name
        destination_name = Path(os.fsdecode(destination)).name
        if (
            rollback_active
            and source_name == target.name
            and destination_name.startswith(f".{target.name}.rollback-")
        ):
            assert src_dir_fd is not None
            capture_hook_count += 1
            payload_seen_at_capture = target.read_bytes()
            transaction_metadata = cord_render_assets.os.stat(
                source_name,
                dir_fd=src_dir_fd,
                follow_symlinks=False,
            )
            transaction_identity = (
                transaction_metadata.st_dev,
                transaction_metadata.st_ino,
            )
            foreign_name = ".same-payload-foreign-inode"
            descriptor = cord_render_assets.os.open(
                foreign_name,
                cord_render_assets._CREATE_FLAGS,
                0o600,
                dir_fd=src_dir_fd,
            )
            try:
                cord_render_assets._write_all(descriptor, prior_payload)
            finally:
                cord_render_assets.os.close(descriptor)
            original_replace(
                foreign_name,
                source_name,
                src_dir_fd=src_dir_fd,
                dst_dir_fd=src_dir_fd,
            )
            foreign_metadata = cord_render_assets.os.stat(
                source_name,
                dir_fd=src_dir_fd,
                follow_symlinks=False,
            )
            foreign_identity = foreign_metadata.st_dev, foreign_metadata.st_ino
        original_rename(
            source,
            destination,
            src_dir_fd=src_dir_fd,
            dst_dir_fd=dst_dir_fd,
        )

    monkeypatch.setattr(
        cord_render_assets.os,
        "rename",
        replace_at_real_rollback_capture,
    )

    with pytest.raises(Exception) as captured:
        cord_render_assets._publish_artifacts(
            [
                cord_render_assets._Publication(
                    target,
                    transaction_payload,
                    "same-payload foreign report",
                )
            ],
            validate_before_commit=fail_validation,
        )

    assert capture_hook_count == 1
    assert payload_seen_at_capture == transaction_payload
    assert transaction_identity is not None
    assert foreign_identity is not None
    assert foreign_identity not in {prior_identity, transaction_identity}
    assert target.read_bytes() == prior_payload
    assert _path_identity(target) == foreign_identity
    assert _retained_paths_with_identity(
        context,
        identity=prior_identity,
        payload=prior_payload,
        excluding=target,
    ), "the original-prior inode must remain as recovery evidence"
    assert isinstance(captured.value, RuntimeError)
    assert "rollback" in str(captured.value).lower()
    assert "unproven" in str(captured.value).lower()
    assert captured.value.__cause__ is callback_failure


@pytest.mark.parametrize("prior_present", [True, False], ids=["prior", "absent"])
def test_callback_deletion_of_new_visible_preserves_absence_as_unproven(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    prior_present: bool,
) -> None:
    context = _context(
        tmp_path,
        f"callback-delete-{'prior' if prior_present else 'absent'}",
    )
    target = context / "report.json"
    prior_payload = b"stale-prior-payload"
    prior_identity: tuple[int, int] | None = None
    if prior_present:
        target.write_bytes(prior_payload)
        prior_identity = _path_identity(target)
    transaction_payload = b"transaction-publication"
    callback_failure = ValueError("injected callback deletion failure")
    original_unlink = cord_render_assets.os.unlink
    validation_active = False
    unlink_hook_count = 0
    payload_seen_at_unlink: bytes | None = None
    transaction_identity: tuple[int, int] | None = None

    def track_real_visible_unlink(
        path: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        *,
        dir_fd: int | None = None,
    ) -> None:
        nonlocal payload_seen_at_unlink, transaction_identity, unlink_hook_count
        name = Path(os.fsdecode(path)).name
        if validation_active and name == target.name:
            unlink_hook_count += 1
            payload_seen_at_unlink = target.read_bytes()
            transaction_identity = _path_identity(target)
        original_unlink(path, dir_fd=dir_fd)

    def delete_new_visible_then_fail() -> None:
        nonlocal validation_active
        validation_active = True
        try:
            target.unlink()
        finally:
            validation_active = False
        raise callback_failure

    monkeypatch.setattr(
        cord_render_assets.os,
        "unlink",
        track_real_visible_unlink,
    )

    with pytest.raises(Exception) as captured:
        cord_render_assets._publish_artifacts(
            [
                cord_render_assets._Publication(
                    target,
                    transaction_payload,
                    "callback-deleted report",
                )
            ],
            validate_before_commit=delete_new_visible_then_fail,
        )

    assert unlink_hook_count == 1
    assert payload_seen_at_unlink == transaction_payload
    assert transaction_identity is not None
    assert not target.exists(), "callback-observed absence must remain visible"
    if prior_identity is not None:
        assert _retained_paths_with_identity(
            context,
            identity=prior_identity,
            payload=prior_payload,
            excluding=target,
        ), "the stale original prior must be retained only as recovery evidence"
    assert isinstance(captured.value, RuntimeError)
    assert "rollback" in str(captured.value).lower()
    assert "unproven" in str(captured.value).lower()
    assert captured.value.__cause__ is callback_failure


def test_untouched_rollback_never_captures_or_mutates_observed_leaf(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    context = _context(tmp_path, "untouched-leaf")
    target = context / "report.json"
    prior_payload = b"observed-prior"
    target.write_bytes(prior_payload)
    prior_identity = _path_identity(target)
    original_rename = cord_render_assets.os.rename
    visible_capture_attempts = 0

    def reject_visible_capture(
        source: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        destination: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        *,
        src_dir_fd: int | None = None,
        dst_dir_fd: int | None = None,
    ) -> None:
        nonlocal visible_capture_attempts
        if Path(os.fsdecode(source)).name == target.name:
            visible_capture_attempts += 1
            raise AssertionError("UNTOUCHED rollback must not capture the leaf")
        original_rename(
            source,
            destination,
            src_dir_fd=src_dir_fd,
            dst_dir_fd=dst_dir_fd,
        )

    monkeypatch.setattr(cord_render_assets.os, "rename", reject_visible_capture)
    incorrect_payload = b"incorrect expected prior"
    expectation = cord_render_assets._LeafExpectation(
        prior_identity,
        incorrect_payload,
        hashlib.sha256(incorrect_payload).hexdigest(),
    )

    with pytest.raises(ValueError, match="changed during operation"):
        cord_render_assets._publish_artifacts(
            [
                cord_render_assets._Publication(
                    target,
                    b"new publication",
                    "untouched report",
                    expectation,
                )
            ]
        )

    assert visible_capture_attempts == 0
    assert _path_identity(target) == prior_identity
    assert target.read_bytes() == prior_payload
    assert sorted(path.name for path in context.iterdir()) == [target.name]


@pytest.mark.parametrize(
    "post_link_change",
    ["delete", "same-payload-foreign"],
    ids=["deleted", "same-payload-foreign"],
)
def test_successful_backup_link_then_external_change_never_uses_fallback(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    post_link_change: str,
) -> None:
    context = _context(tmp_path, f"post-link-{post_link_change}")
    target = context / "report.json"
    prior_payload = b"original-prior"
    target.write_bytes(prior_payload)
    prior_identity = _path_identity(target)
    callback_failure = ValueError("injected post-link callback failure")
    original_link = cord_render_assets.os.link
    original_replace = cord_render_assets.os.replace
    original_unlink = cord_render_assets.os.unlink
    rollback_active = False
    backup_link_count = 0
    fallback_link_count = 0
    foreign_identity: tuple[int, int] | None = None

    def fail_validation() -> None:
        nonlocal rollback_active
        rollback_active = True
        raise callback_failure

    def change_visible_after_successful_backup_link(
        source: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        destination: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        *,
        src_dir_fd: int | None = None,
        dst_dir_fd: int | None = None,
        follow_symlinks: bool = True,
    ) -> None:
        nonlocal backup_link_count, fallback_link_count, foreign_identity
        source_name = Path(os.fsdecode(source)).name
        if rollback_active and ".restore-" in source_name:
            fallback_link_count += 1
        original_link(
            source,
            destination,
            src_dir_fd=src_dir_fd,
            dst_dir_fd=dst_dir_fd,
            follow_symlinks=follow_symlinks,
        )
        if rollback_active and ".backup-" in source_name:
            assert dst_dir_fd is not None
            backup_link_count += 1
            if post_link_change == "delete":
                original_unlink(destination, dir_fd=dst_dir_fd)
            else:
                foreign_name = ".post-link-same-payload-foreign"
                descriptor = cord_render_assets.os.open(
                    foreign_name,
                    cord_render_assets._CREATE_FLAGS,
                    0o600,
                    dir_fd=dst_dir_fd,
                )
                try:
                    cord_render_assets._write_all(descriptor, prior_payload)
                finally:
                    cord_render_assets.os.close(descriptor)
                original_replace(
                    foreign_name,
                    destination,
                    src_dir_fd=dst_dir_fd,
                    dst_dir_fd=dst_dir_fd,
                )
                foreign_identity = _path_identity(target)

    monkeypatch.setattr(
        cord_render_assets.os,
        "link",
        change_visible_after_successful_backup_link,
    )

    with pytest.raises(Exception) as captured:
        cord_render_assets._publish_artifacts(
            [
                cord_render_assets._Publication(
                    target,
                    b"transaction-publication",
                    "post-link report",
                )
            ],
            validate_before_commit=fail_validation,
        )

    assert backup_link_count == 1
    assert fallback_link_count == 0
    if post_link_change == "delete":
        assert not target.exists()
    else:
        assert foreign_identity is not None
        assert foreign_identity != prior_identity
        assert _path_identity(target) == foreign_identity
        assert target.read_bytes() == prior_payload
    assert _retained_paths_with_identity(
        context,
        identity=prior_identity,
        payload=prior_payload,
        excluding=target,
    ), "the exact original-prior inode must remain as recovery evidence"
    assert isinstance(captured.value, RuntimeError)
    assert "rollback" in str(captured.value).lower()
    assert "unproven" in str(captured.value).lower()
    assert captured.value.__cause__ is callback_failure


def test_final_rollback_verifier_rejects_same_payload_foreign_inode(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    context = _context(tmp_path, "final-same-payload-foreign")
    target = context / "report.json"
    prior_payload = b"final-original-prior"
    target.write_bytes(prior_payload)
    prior_identity = _path_identity(target)
    callback_failure = ValueError("injected final-verifier callback failure")
    original_verifier = cord_render_assets._rollback_visible_matches
    rollback_active = False
    replacement_count = 0
    foreign_identity: tuple[int, int] | None = None

    def fail_validation() -> None:
        nonlocal rollback_active
        rollback_active = True
        raise callback_failure

    def replace_during_sole_final_rollback_verification(
        item: cord_render_assets._StagedPublication,
    ) -> bool:
        nonlocal replacement_count, foreign_identity
        if rollback_active and replacement_count == 0:
            replacement_count += 1
            foreign_name = ".final-same-payload-foreign"
            descriptor = cord_render_assets.os.open(
                foreign_name,
                cord_render_assets._CREATE_FLAGS,
                0o600,
                dir_fd=item.anchor.parent_fd,
            )
            try:
                cord_render_assets._write_all(descriptor, prior_payload)
            finally:
                cord_render_assets.os.close(descriptor)
            cord_render_assets.os.replace(
                foreign_name,
                item.anchor.leaf,
                src_dir_fd=item.anchor.parent_fd,
                dst_dir_fd=item.anchor.parent_fd,
            )
            foreign_identity = _path_identity(target)
        return original_verifier(item)

    monkeypatch.setattr(
        cord_render_assets,
        "_rollback_visible_matches",
        replace_during_sole_final_rollback_verification,
    )

    with pytest.raises(Exception) as captured:
        cord_render_assets._publish_artifacts(
            [
                cord_render_assets._Publication(
                    target,
                    b"transaction-publication",
                    "final-verifier report",
                )
            ],
            validate_before_commit=fail_validation,
        )

    assert replacement_count == 1
    assert foreign_identity is not None
    assert foreign_identity != prior_identity
    assert _path_identity(target) == foreign_identity
    assert target.read_bytes() == prior_payload
    assert _retained_paths_with_identity(
        context,
        identity=prior_identity,
        payload=prior_payload,
        excluding=target,
    ), "final verification must retain the original-prior inode"
    assert isinstance(captured.value, RuntimeError)
    assert "rollback" in str(captured.value).lower()
    assert "unproven" in str(captured.value).lower()
    assert captured.value.__cause__ is callback_failure


def test_transient_scratch_directory_cleanup_failure_keeps_committed_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    context = _context(tmp_path, "scratch-directory-cleanup")
    target = context / "report.json"
    prior_payload = b"prior-report"
    target.write_bytes(prior_payload)
    original_rmdir = cord_render_assets.os.rmdir
    hook_ran = False

    def fail_first_scratch_directory_cleanup(
        path: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        *,
        dir_fd: int | None = None,
    ) -> None:
        nonlocal hook_ran
        name = Path(os.fsdecode(path)).name
        if not hook_ran and ".txn-" in name and ".cleanup-" in name:
            hook_ran = True
            raise OSError("injected scratch directory cleanup failure")
        original_rmdir(path, dir_fd=dir_fd)

    monkeypatch.setattr(
        cord_render_assets.os,
        "rmdir",
        fail_first_scratch_directory_cleanup,
    )

    with pytest.raises(RuntimeError) as captured:
        cord_render_assets._publish_artifacts(
            [
                cord_render_assets._Publication(
                    target,
                    b"replacement-report",
                    "scratch cleanup report",
                )
            ]
        )

    assert hook_ran is True
    assert target.read_bytes() == b"replacement-report"
    assert "publication committed" in str(captured.value).lower()
    assert "cleanup state is unproven" in str(captured.value).lower()
    assert any(
        "injected scratch directory cleanup failure" in message
        for message in _exception_chain_messages(captured.value)
    )


def test_scratch_directory_quarantine_post_rename_failure_reconciles_both_names(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    context = _context(tmp_path, "scratch-directory-post-rename")
    target = context / "report.json"
    prior_payload = b"prior-report"
    publication_payload = b"committed-report"
    target.write_bytes(prior_payload)
    original_rename = cord_render_assets.os.rename
    hook_count = 0
    attempted_names: tuple[str, str] | None = None

    def rename_scratch_directory_then_raise(
        source: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        destination: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        *,
        src_dir_fd: int | None = None,
        dst_dir_fd: int | None = None,
    ) -> None:
        nonlocal attempted_names, hook_count
        source_name = Path(os.fsdecode(source)).name
        destination_name = Path(os.fsdecode(destination)).name
        if (
            hook_count == 0
            and source_name.startswith(f".{target.name}.txn-")
            and ".cleanup-" in destination_name
        ):
            assert src_dir_fd is not None
            assert src_dir_fd == dst_dir_fd
            original_rename(
                source,
                destination,
                src_dir_fd=src_dir_fd,
                dst_dir_fd=dst_dir_fd,
            )
            hook_count += 1
            attempted_names = source_name, destination_name
            raise OSError("injected after real scratch-directory quarantine rename")
        original_rename(
            source,
            destination,
            src_dir_fd=src_dir_fd,
            dst_dir_fd=dst_dir_fd,
        )

    monkeypatch.setattr(
        cord_render_assets.os,
        "rename",
        rename_scratch_directory_then_raise,
    )

    failure: Exception | None = None
    try:
        cord_render_assets._publish_artifacts(
            [
                cord_render_assets._Publication(
                    target,
                    publication_payload,
                    "post-commit cleanup report",
                )
            ]
        )
    except Exception as error:  # noqa: BLE001 - inspect the complete failure chain
        failure = error

    assert hook_count == 1
    assert attempted_names is not None
    assert failure is not None
    assert target.read_bytes() == publication_payload
    source_name, quarantine_name = attempted_names
    surviving_attempted_names = [
        name for name in attempted_names if (context / name).exists()
    ]
    hidden_transaction_names = sorted(
        path.name
        for path in context.iterdir()
        if path.name.startswith(f".{target.name}.txn-")
    )
    assert hidden_transaction_names == sorted(surviving_attempted_names)
    assert isinstance(failure, RuntimeError)
    assert "publication committed" in str(failure).lower()
    assert "cleanup state is unproven" in str(failure).lower()
    for surviving_name in surviving_attempted_names:
        assert surviving_name in str(failure)
    assert not (context / source_name).exists() or source_name in str(failure)
    assert not (context / quarantine_name).exists() or quarantine_name in str(failure)
    assert any(
        "injected after real scratch-directory quarantine rename" in message
        for message in _exception_chain_messages(failure)
    )


def test_in_place_mutation_after_scratch_leaf_cleanup_is_preserved_as_external(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    context = _context(tmp_path, "in-place-after-scratch-leaf-cleanup")
    target = context / "report.json"
    prior_payload = b"prior-report-bytes"
    transaction_payload = b"transaction-publication"
    concurrent_payload = b"concurrent-in-place-update"
    target.write_bytes(prior_payload)
    prior_identity = _path_identity(target)
    original_verifier = cord_render_assets._verify_published_artifacts
    verifier_calls = 0
    mutation_count = 0
    transaction_identity: tuple[int, int] | None = None

    def mutate_before_post_cleanup_verification(
        staged: list[cord_render_assets._StagedPublication]
        | tuple[cord_render_assets._StagedPublication, ...],
    ) -> None:
        nonlocal mutation_count, transaction_identity, verifier_calls
        verifier_calls += 1
        if verifier_calls == 2:
            mutation_count += 1
            transaction_identity = _path_identity(target)
            target.write_bytes(concurrent_payload)
            assert _path_identity(target) == transaction_identity
        original_verifier(staged)

    monkeypatch.setattr(
        cord_render_assets,
        "_verify_published_artifacts",
        mutate_before_post_cleanup_verification,
    )

    failure: Exception | None = None
    try:
        cord_render_assets._publish_artifacts(
            [
                cord_render_assets._Publication(
                    target,
                    transaction_payload,
                    "in-place mutation report",
                )
            ]
        )
    except Exception as error:  # noqa: BLE001 - inspect the complete failure chain
        failure = error

    assert verifier_calls == 2
    assert mutation_count == 1
    assert transaction_identity is not None
    assert failure is not None
    assert _path_identity(target) == transaction_identity
    assert target.read_bytes() == concurrent_payload
    assert _retained_paths_with_identity(
        context,
        identity=prior_identity,
        payload=prior_payload,
        excluding=target,
    ), "the original-prior inode must remain as recovery evidence"
    assert isinstance(failure, RuntimeError)
    assert "rollback" in str(failure).lower()
    assert "unproven" in str(failure).lower()
    assert failure.__cause__ is not None
    assert any(
        "published artifact verification failed" in message
        for message in _exception_chain_messages(failure)
    )


def test_two_item_later_scratch_removal_failure_never_leaves_partial_new_state(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    context = _context(tmp_path, "two-item-later-scratch-removal")
    first = context / "first.json"
    second = context / "second.json"
    first_prior = b"first-prior"
    second_prior = b"second-prior"
    first_new = b"first-new"
    second_new = b"second-new"
    first.write_bytes(first_prior)
    second.write_bytes(second_prior)
    original_rmdir = cord_render_assets.os.rmdir
    scratch_rmdir_names: list[str] = []
    injected_count = 0
    failed_scratch_name = ""

    def fail_second_real_scratch_rmdir(
        path: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        *,
        dir_fd: int | None = None,
    ) -> None:
        nonlocal failed_scratch_name, injected_count
        name = Path(os.fsdecode(path)).name
        if ".txn-" in name and ".cleanup-" in name:
            scratch_rmdir_names.append(name)
            if len(scratch_rmdir_names) == 2 and injected_count == 0:
                injected_count += 1
                failed_scratch_name = name
                raise OSError("injected later scratch-directory removal failure")
        original_rmdir(path, dir_fd=dir_fd)

    monkeypatch.setattr(
        cord_render_assets.os,
        "rmdir",
        fail_second_real_scratch_rmdir,
    )

    failure: Exception | None = None
    try:
        cord_render_assets._publish_artifacts(
            [
                cord_render_assets._Publication(first, first_new, "first report"),
                cord_render_assets._Publication(second, second_new, "second report"),
            ]
        )
    except Exception as error:  # noqa: BLE001 - inspect the complete failure chain
        failure = error

    assert injected_count == 1
    assert len(scratch_rmdir_names) >= 2
    assert scratch_rmdir_names[0] != scratch_rmdir_names[1]
    assert failed_scratch_name == scratch_rmdir_names[1]
    assert failure is not None
    assert first.read_bytes() == first_new
    assert second.read_bytes() == second_new
    assert isinstance(failure, RuntimeError)
    assert "publication committed" in str(failure).lower()
    assert "cleanup state is unproven" in str(failure).lower()
    assert failed_scratch_name in str(failure)
    assert any(
        "injected later scratch-directory removal failure" in message
        for message in _exception_chain_messages(failure)
    )


@pytest.mark.parametrize(
    "verification_boundary",
    ["fstat", "visible-stat"],
    ids=["fstat", "visible-stat"],
)
def test_created_parent_post_open_verification_error_closes_new_descriptor(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    verification_boundary: str,
) -> None:
    context = _context(tmp_path, f"parent-post-open-{verification_boundary}")
    created_parent = context / "created-parent"
    target = created_parent / "report.json"
    original_close = cord_render_assets.os.close
    original_fstat = cord_render_assets.os.fstat
    original_open = cord_render_assets.os.open
    original_stat = cord_render_assets.os.stat
    opened_parent_fds: list[int] = []
    hook_count = 0

    def track_created_parent_open(
        path: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        flags: int,
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> int:
        descriptor = original_open(path, flags, mode, dir_fd=dir_fd)
        if (
            dir_fd is not None
            and Path(os.fsdecode(path)).name == created_parent.name
            and not opened_parent_fds
        ):
            opened_parent_fds.append(descriptor)
        return descriptor

    def fstat_then_raise(descriptor: int) -> os.stat_result:
        nonlocal hook_count
        metadata = original_fstat(descriptor)
        if (
            verification_boundary == "fstat"
            and descriptor in opened_parent_fds
            and hook_count == 0
        ):
            hook_count += 1
            raise OSError("injected after real created-parent fstat")
        return metadata

    def visible_stat_then_raise(
        path: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        *,
        dir_fd: int | None = None,
        follow_symlinks: bool = True,
    ) -> os.stat_result:
        nonlocal hook_count
        metadata = original_stat(
            path,
            dir_fd=dir_fd,
            follow_symlinks=follow_symlinks,
        )
        if (
            verification_boundary == "visible-stat"
            and opened_parent_fds
            and Path(os.fsdecode(path)).name == created_parent.name
            and dir_fd is not None
            and hook_count == 0
        ):
            hook_count += 1
            raise OSError("injected after real created-parent visible stat")
        return metadata

    monkeypatch.setattr(cord_render_assets.os, "open", track_created_parent_open)
    monkeypatch.setattr(cord_render_assets.os, "fstat", fstat_then_raise)
    monkeypatch.setattr(cord_render_assets.os, "stat", visible_stat_then_raise)

    failure: Exception | None = None
    try:
        cord_render_assets.write_owner_json(target, {"new": True})
    except Exception as error:  # noqa: BLE001 - inspect the complete failure chain
        failure = error

    still_open: list[int] = []
    for descriptor in opened_parent_fds:
        try:
            original_fstat(descriptor)
        except OSError:
            continue
        still_open.append(descriptor)
    for descriptor in still_open:
        original_close(descriptor)

    assert opened_parent_fds
    assert hook_count == 1
    assert failure is not None
    assert not still_open, f"created-parent descriptors leaked: {still_open}"
    expected_message = (
        "injected after real created-parent fstat"
        if verification_boundary == "fstat"
        else "injected after real created-parent visible stat"
    )
    assert any(
        expected_message in message for message in _exception_chain_messages(failure)
    )


def test_revalidate_anchor_post_open_fstat_error_closes_new_descriptor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    context = _context(tmp_path, "revalidate-post-open-fstat")
    target = context / "report.json"
    target.write_bytes(b"report")
    anchor = cord_render_assets._open_parent(target)
    original_close = cord_render_assets.os.close
    original_fstat = cord_render_assets.os.fstat
    original_open = cord_render_assets.os.open
    opened_context_fds: list[int] = []
    hook_count = 0

    def track_context_open(
        path: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        flags: int,
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> int:
        descriptor = original_open(path, flags, mode, dir_fd=dir_fd)
        if (
            dir_fd is not None
            and Path(os.fsdecode(path)).name == context.name
            and not opened_context_fds
        ):
            opened_context_fds.append(descriptor)
        return descriptor

    def fstat_then_raise(descriptor: int) -> os.stat_result:
        nonlocal hook_count
        metadata = original_fstat(descriptor)
        if descriptor in opened_context_fds and hook_count == 0:
            hook_count += 1
            raise OSError("injected after real revalidation fstat")
        return metadata

    monkeypatch.setattr(cord_render_assets.os, "open", track_context_open)
    monkeypatch.setattr(cord_render_assets.os, "fstat", fstat_then_raise)

    try:
        with pytest.raises(OSError, match="injected after real revalidation fstat"):
            cord_render_assets._revalidate_anchor(anchor)
    finally:
        anchor.close()

    still_open: list[int] = []
    for descriptor in opened_context_fds:
        try:
            original_fstat(descriptor)
        except OSError:
            continue
        still_open.append(descriptor)
    for descriptor in still_open:
        original_close(descriptor)

    assert opened_context_fds
    assert hook_count == 1
    assert not still_open, f"revalidation descriptors leaked: {still_open}"


def test_open_parent_post_real_component_close_failure_is_not_retried(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    context = _context(tmp_path, "open-parent-post-real-close")
    target = context / "report.json"
    original_close = cord_render_assets.os.close
    hook_count = 0

    def close_first_component_then_raise(descriptor: int) -> None:
        nonlocal hook_count
        original_close(descriptor)
        if hook_count == 0:
            hook_count += 1
            raise OSError("injected after real open-parent component close")

    monkeypatch.setattr(
        cord_render_assets.os,
        "close",
        close_first_component_then_raise,
    )

    with pytest.raises(
        OSError,
        match="injected after real open-parent component close",
    ):
        cord_render_assets._open_parent(target)

    assert hook_count == 1


def test_revalidate_anchor_post_real_component_close_failure_is_not_retried(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    context = _context(tmp_path, "revalidate-post-real-close")
    target = context / "report.json"
    target.write_bytes(b"report")
    anchor = cord_render_assets._open_parent(target)
    original_close = cord_render_assets.os.close
    hook_count = 0

    def close_first_component_then_raise(descriptor: int) -> None:
        nonlocal hook_count
        original_close(descriptor)
        if hook_count == 0:
            hook_count += 1
            raise OSError("injected after real revalidation component close")

    monkeypatch.setattr(
        cord_render_assets.os,
        "close",
        close_first_component_then_raise,
    )

    try:
        with pytest.raises(
            OSError,
            match="injected after real revalidation component close",
        ):
            cord_render_assets._revalidate_anchor(anchor)
    finally:
        anchor.close()

    assert hook_count == 1


def _assert_same_owner_writers_serialize_at_boundary(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    boundary: str,
) -> None:
    context = _context(tmp_path, f"serialized-writers-{boundary}")
    target = context / "report.json"
    original_mkdir = cord_render_assets.os.mkdir
    original_rmdir = cord_render_assets.os.rmdir
    original_unlink = cord_render_assets.os.unlink
    first_reached_boundary = threading.Event()
    release_first = threading.Event()
    second_started = threading.Event()
    second_finished = threading.Event()
    completion_order: list[str] = []
    failures: dict[str, Exception] = {}
    hook_count = 0
    first_thread: threading.Thread | None = None

    def pause_first_writer() -> None:
        nonlocal hook_count
        if threading.current_thread() is not first_thread or hook_count != 0:
            return
        hook_count += 1
        first_reached_boundary.set()
        if not release_first.wait(timeout=5):
            raise TimeoutError(f"timed out releasing first writer at {boundary}")

    def pause_after_real_scratch_mkdir(
        path: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> None:
        original_mkdir(path, mode, dir_fd=dir_fd)
        name = Path(os.fsdecode(path)).name
        if boundary == "post-scratch-mkdir" and ".txn-" in name:
            pause_first_writer()

    def pause_before_real_scratch_leaf_unlink(
        path: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        *,
        dir_fd: int | None = None,
    ) -> None:
        name = Path(os.fsdecode(path)).name
        if boundary == "pre-scratch-leaf-unlink" and all(
            marker in name for marker in (".tmp-", ".cleanup-")
        ):
            pause_first_writer()
        original_unlink(path, dir_fd=dir_fd)

    def pause_before_real_scratch_directory_rmdir(
        path: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        *,
        dir_fd: int | None = None,
    ) -> None:
        name = Path(os.fsdecode(path)).name
        if boundary == "pre-scratch-directory-rmdir" and all(
            marker in name for marker in (".txn-", ".cleanup-")
        ):
            pause_first_writer()
        original_rmdir(path, dir_fd=dir_fd)

    monkeypatch.setattr(
        cord_render_assets.os,
        "mkdir",
        pause_after_real_scratch_mkdir,
    )
    monkeypatch.setattr(
        cord_render_assets.os,
        "unlink",
        pause_before_real_scratch_leaf_unlink,
    )
    monkeypatch.setattr(
        cord_render_assets.os,
        "rmdir",
        pause_before_real_scratch_directory_rmdir,
    )

    def write_payload(writer: str) -> None:
        if writer == "second":
            second_started.set()
        try:
            cord_render_assets.write_owner_json(target, {"writer": writer})
        except Exception as error:  # noqa: BLE001 - assert thread failures below
            failures[writer] = error
        else:
            completion_order.append(writer)
        finally:
            if writer == "second":
                second_finished.set()

    first_thread = threading.Thread(
        target=write_payload,
        args=("first",),
        name=f"first-{boundary}",
    )
    second_thread = threading.Thread(
        target=write_payload,
        args=("second",),
        name=f"second-{boundary}",
    )
    first_thread.start()
    reached_boundary = first_reached_boundary.wait(timeout=5)
    if reached_boundary:
        second_thread.start()
        observed_second_start = second_started.wait(timeout=5)
        second_finished_while_first_paused = second_finished.wait(timeout=0.25)
    else:
        observed_second_start = False
        second_finished_while_first_paused = False
    release_first.set()
    first_thread.join(timeout=5)
    if second_thread.ident is not None:
        second_thread.join(timeout=5)

    assert reached_boundary is True
    assert observed_second_start is True
    assert hook_count == 1
    assert second_finished_while_first_paused is False
    assert first_thread.is_alive() is False
    assert second_thread.is_alive() is False
    assert failures == {}
    assert completion_order == ["first", "second"]
    assert json.loads(target.read_text(encoding="utf-8")) == {"writer": "second"}


def test_same_owner_writers_serialize_after_real_scratch_mkdir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _assert_same_owner_writers_serialize_at_boundary(
        tmp_path,
        monkeypatch,
        "post-scratch-mkdir",
    )


def test_same_owner_writers_serialize_before_scratch_leaf_unlink(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _assert_same_owner_writers_serialize_at_boundary(
        tmp_path,
        monkeypatch,
        "pre-scratch-leaf-unlink",
    )


def test_same_owner_writers_serialize_before_scratch_directory_rmdir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _assert_same_owner_writers_serialize_at_boundary(
        tmp_path,
        monkeypatch,
        "pre-scratch-directory-rmdir",
    )


def test_publication_transaction_lock_serializes_same_owner_across_processes(
    tmp_path: Path,
) -> None:
    context = _context(tmp_path, "cross-process-publication-lock")
    held_target = context / "held.json"
    child_target = context / "child.json"
    child_started = context / "child-started"
    source_root = Path(cord_render_assets.__file__).resolve().parents[1]
    child_environment = os.environ.copy()
    child_environment["PYTHONPATH"] = os.pathsep.join(
        filter(
            None,
            (str(source_root), child_environment.get("PYTHONPATH", "")),
        )
    )
    child_script = """
import sys
from pathlib import Path

from hangboard_packages.cord_render_assets import write_owner_json

target = Path(sys.argv[1])
Path(sys.argv[2]).write_text("started", encoding="utf-8")
write_owner_json(target, {"writer": "child"})
"""
    child: subprocess.Popen[str] | None = None
    child_stdout = ""
    child_stderr = ""
    try:
        with cord_render_assets._publication_transaction_lock((held_target,)):
            child = subprocess.Popen(
                [
                    sys.executable,
                    "-c",
                    child_script,
                    os.fspath(child_target),
                    os.fspath(child_started),
                ],
                env=child_environment,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            deadline = time.monotonic() + 5
            while (
                not child_started.exists()
                and child.poll() is None
                and time.monotonic() < deadline
            ):
                time.sleep(0.01)

            assert child_started.read_text(encoding="utf-8") == "started"
            with pytest.raises(subprocess.TimeoutExpired):
                child.wait(timeout=0.25)
            assert not child_target.exists()

        child_stdout, child_stderr = child.communicate(timeout=5)
    finally:
        if child is not None and child.poll() is None:
            child.kill()
            child_stdout, child_stderr = child.communicate(timeout=5)

    assert child.returncode == 0, (
        f"child stdout: {child_stdout!r}; child stderr: {child_stderr!r}"
    )
    assert json.loads(child_target.read_text(encoding="utf-8")) == {"writer": "child"}


def test_nested_same_owner_writer_reuses_outer_lock_without_premature_unlock(
    tmp_path: Path,
) -> None:
    context = _context(tmp_path, "nested-cross-process-publication-lock")
    held_target = context / "held.json"
    nested_target = context / "nested.json"
    child_target = context / "child.json"
    child_started = context / "child-started"
    source_root = Path(cord_render_assets.__file__).resolve().parents[1]
    child_environment = os.environ.copy()
    child_environment["PYTHONPATH"] = os.pathsep.join(
        filter(
            None,
            (str(source_root), child_environment.get("PYTHONPATH", "")),
        )
    )
    child_script = """
import sys
from pathlib import Path

from hangboard_packages.cord_render_assets import write_owner_json

target = Path(sys.argv[1])
Path(sys.argv[2]).write_text("started", encoding="utf-8")
write_owner_json(target, {"writer": "child"})
"""
    child: subprocess.Popen[str] | None = None
    child_stdout = ""
    child_stderr = ""
    try:
        with cord_render_assets._publication_transaction_lock((held_target,)):
            cord_render_assets.write_owner_json(nested_target, {"writer": "nested"})
            child = subprocess.Popen(
                [
                    sys.executable,
                    "-c",
                    child_script,
                    os.fspath(child_target),
                    os.fspath(child_started),
                ],
                env=child_environment,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            deadline = time.monotonic() + 5
            while (
                not child_started.exists()
                and child.poll() is None
                and time.monotonic() < deadline
            ):
                time.sleep(0.01)

            assert json.loads(nested_target.read_text(encoding="utf-8")) == {
                "writer": "nested"
            }
            assert child_started.read_text(encoding="utf-8") == "started"
            with pytest.raises(subprocess.TimeoutExpired):
                child.wait(timeout=0.25)
            assert not child_target.exists()

        child_stdout, child_stderr = child.communicate(timeout=5)
    finally:
        if child is not None and child.poll() is None:
            child.kill()
            child_stdout, child_stderr = child.communicate(timeout=5)

    assert child.returncode == 0, (
        f"child stdout: {child_stdout!r}; child stderr: {child_stderr!r}"
    )
    assert json.loads(child_target.read_text(encoding="utf-8")) == {"writer": "child"}


def test_lock_release_failure_after_commit_preserves_committed_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    context = _context(tmp_path, "postcommit-lock-release")
    target = context / "report.json"
    original_flock = cord_render_assets.fcntl.flock
    unlock_count = 0

    def unlock_then_raise(descriptor: int, operation: int) -> None:
        nonlocal unlock_count
        original_flock(descriptor, operation)
        if operation & cord_render_assets.fcntl.LOCK_UN:
            unlock_count += 1
            raise OSError("injected after real publication unlock")

    monkeypatch.setattr(cord_render_assets.fcntl, "flock", unlock_then_raise)

    with pytest.raises(RuntimeError) as captured:
        cord_render_assets.write_owner_json(target, {"committed": True})

    assert unlock_count == 1
    assert json.loads(target.read_text(encoding="utf-8")) == {"committed": True}
    assert "publication committed" in str(captured.value).lower()
    assert "cleanup state is unproven" in str(captured.value).lower()
    assert any(
        "injected after real publication unlock" in message
        for message in _exception_chain_messages(captured.value)
    )


def test_partial_multi_owner_flock_failure_releases_and_closes_every_descriptor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    first = _context(tmp_path, "partial-flock-first") / "first.json"
    second = _context(tmp_path, "partial-flock-second") / "second.json"
    original_flock = cord_render_assets.fcntl.flock
    exclusive_fds: list[int] = []
    unlocked_fds: list[int] = []

    def fail_second_exclusive_flock(descriptor: int, operation: int) -> None:
        if operation & cord_render_assets.fcntl.LOCK_EX:
            exclusive_fds.append(descriptor)
            if len(exclusive_fds) == 2:
                raise OSError("injected second owner flock failure")
        if operation & cord_render_assets.fcntl.LOCK_UN:
            unlocked_fds.append(descriptor)
        original_flock(descriptor, operation)

    monkeypatch.setattr(
        cord_render_assets.fcntl,
        "flock",
        fail_second_exclusive_flock,
    )

    with pytest.raises(OSError, match="injected second owner flock failure"):
        with cord_render_assets._publication_transaction_lock((first, second)):
            raise AssertionError("lock acquisition must fail before yielding")

    assert len(exclusive_fds) == 2
    assert unlocked_fds == [exclusive_fds[0]]
    for descriptor in exclusive_fds:
        with pytest.raises(OSError):
            os.fstat(descriptor)
    assert not first.exists()
    assert not second.exists()


def test_postcommit_first_item_cleanup_failure_still_cleans_later_item(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    context = _context(tmp_path, "continued-postcommit-cleanup")
    first = context / "first.json"
    second = context / "second.json"
    first.write_bytes(b"first-prior")
    second.write_bytes(b"second-prior")
    original_unlink = cord_render_assets.os.unlink
    hook_count = 0

    def fail_first_backup_unlink(
        path: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        *,
        dir_fd: int | None = None,
    ) -> None:
        nonlocal hook_count
        name = Path(os.fsdecode(path)).name
        if hook_count == 0 and ".backup-" in name:
            hook_count += 1
            raise OSError("injected first-item backup cleanup failure")
        original_unlink(path, dir_fd=dir_fd)

    monkeypatch.setattr(cord_render_assets.os, "unlink", fail_first_backup_unlink)

    with pytest.raises(RuntimeError) as captured:
        cord_render_assets._publish_artifacts(
            [
                cord_render_assets._Publication(first, b"first-new", "first report"),
                cord_render_assets._Publication(
                    second,
                    b"second-new",
                    "second report",
                ),
            ]
        )

    assert hook_count == 1
    assert first.read_bytes() == b"first-new"
    assert second.read_bytes() == b"second-new"
    assert any(
        path.name.startswith(f".{first.name}.txn-") for path in context.iterdir()
    )
    assert not any(
        path.name.startswith(f".{second.name}.txn-") for path in context.iterdir()
    )
    assert "publication committed" in str(captured.value).lower()
    assert "cleanup state is unproven" in str(captured.value).lower()
    assert any(
        "injected first-item backup cleanup failure" in message
        for message in _exception_chain_messages(captured.value)
    )


def test_committed_close_failure_still_closes_later_items_and_preserves_primary_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    context = _context(tmp_path, "continued-resource-close")
    first = context / "first.json"
    second = context / "second.json"
    first.write_bytes(b"first-prior")
    second.write_bytes(b"second-prior")
    original_cleanup = cord_render_assets._cleanup_committed_artifacts
    original_close = cord_render_assets.os.close
    original_fstat = cord_render_assets.os.fstat
    original_rmdir = cord_render_assets.os.rmdir
    tracked_scratch_fd: int | None = None
    tracked_anchor_fds: list[int] = []
    close_calls: list[int] = []
    rmdir_hook_count = 0
    close_hook_count = 0

    def fail_first_scratch_rmdir(
        path: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        *,
        dir_fd: int | None = None,
    ) -> None:
        nonlocal rmdir_hook_count
        name = Path(os.fsdecode(path)).name
        if rmdir_hook_count == 0 and ".txn-" in name and ".cleanup-" in name:
            rmdir_hook_count += 1
            raise OSError("injected primary scratch-directory cleanup failure")
        original_rmdir(path, dir_fd=dir_fd)

    def record_staged_descriptors(
        staged: list[cord_render_assets._StagedPublication]
        | tuple[cord_render_assets._StagedPublication, ...],
    ) -> tuple[list[str], BaseException | None]:
        nonlocal tracked_scratch_fd
        tracked_scratch_fd = staged[0].scratch_fd
        tracked_anchor_fds.extend(item.anchor.parent_fd for item in staged)
        return original_cleanup(staged)

    def close_first_scratch_then_raise(descriptor: int) -> None:
        nonlocal close_hook_count
        close_calls.append(descriptor)
        original_close(descriptor)
        if descriptor == tracked_scratch_fd and close_hook_count == 0:
            close_hook_count += 1
            raise OSError("injected after real first scratch descriptor close")

    monkeypatch.setattr(cord_render_assets.os, "rmdir", fail_first_scratch_rmdir)
    monkeypatch.setattr(
        cord_render_assets,
        "_cleanup_committed_artifacts",
        record_staged_descriptors,
    )
    monkeypatch.setattr(cord_render_assets.os, "close", close_first_scratch_then_raise)

    with pytest.raises(Exception) as captured:
        cord_render_assets._publish_artifacts(
            [
                cord_render_assets._Publication(first, b"first-new", "first report"),
                cord_render_assets._Publication(
                    second,
                    b"second-new",
                    "second report",
                ),
            ]
        )

    still_open: list[int] = []
    for descriptor in tracked_anchor_fds:
        try:
            original_fstat(descriptor)
        except OSError:
            continue
        still_open.append(descriptor)
    for descriptor in still_open:
        original_close(descriptor)

    assert rmdir_hook_count == 1
    assert close_hook_count == 1
    assert tracked_scratch_fd is not None
    assert tracked_scratch_fd in close_calls
    assert set(tracked_anchor_fds) <= set(close_calls)
    assert not still_open, f"later publication descriptors leaked: {still_open}"
    assert first.read_bytes() == b"first-new"
    assert second.read_bytes() == b"second-new"
    assert isinstance(captured.value, RuntimeError)
    assert "publication committed" in str(captured.value).lower()
    assert "cleanup state is unproven" in str(captured.value).lower()
    assert "descriptor" in str(captured.value).lower()
    chain = _exception_chain_messages(captured.value)
    assert any(
        "injected primary scratch-directory cleanup failure" in message
        for message in chain
    )
    assert "injected after real first scratch descriptor close" in str(captured.value)


def test_unexpected_postcommit_cleanup_exception_is_phase_wrapped_without_rollback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    context = _context(tmp_path, "unexpected-postcommit-cleanup")
    target = context / "report.json"
    prior_payload = b"prior-report"
    committed_payload = b"committed-report"
    target.write_bytes(prior_payload)
    cleanup_failure = OSError("injected top-level postcommit cleanup crash")

    def fail_cleanup_executor(
        staged: list[cord_render_assets._StagedPublication]
        | tuple[cord_render_assets._StagedPublication, ...],
    ) -> tuple[list[str], BaseException | None]:
        assert len(staged) == 1
        raise cleanup_failure

    monkeypatch.setattr(
        cord_render_assets,
        "_cleanup_committed_artifacts",
        fail_cleanup_executor,
    )

    with pytest.raises(RuntimeError) as captured:
        cord_render_assets._publish_artifacts(
            [
                cord_render_assets._Publication(
                    target,
                    committed_payload,
                    "unexpected cleanup report",
                )
            ]
        )

    assert target.read_bytes() == committed_payload
    assert "publication committed" in str(captured.value).lower()
    assert "cleanup state is unproven" in str(captured.value).lower()
    assert captured.value.__cause__ is cleanup_failure
    assert any(
        path.name.startswith(f".{target.name}.txn-") for path in context.iterdir()
    ), "unreleased prior recovery state must remain disclosed on cleanup crash"


def test_post_real_scratch_descriptor_close_failure_is_never_reclosed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    context = _context(tmp_path, "post-real-scratch-close")
    target = context / "report.json"
    target.write_bytes(b"prior-report")
    original_close = cord_render_assets.os.close
    original_remove = cord_render_assets._remove_scratch_directory
    scratch_fd: int | None = None
    scratch_fd_after_remove: int | None = None
    hook_count = 0

    def record_scratch_descriptor(
        item: cord_render_assets._StagedPublication,
    ) -> None:
        nonlocal scratch_fd, scratch_fd_after_remove
        scratch_fd = item.scratch_fd
        try:
            original_remove(item)
        finally:
            scratch_fd_after_remove = item.scratch_fd

    def close_scratch_then_raise(descriptor: int) -> None:
        nonlocal hook_count
        original_close(descriptor)
        if descriptor == scratch_fd and hook_count == 0:
            hook_count += 1
            raise OSError("injected after real scratch descriptor close")

    monkeypatch.setattr(
        cord_render_assets,
        "_remove_scratch_directory",
        record_scratch_descriptor,
    )
    monkeypatch.setattr(cord_render_assets.os, "close", close_scratch_then_raise)

    with pytest.raises(RuntimeError) as captured:
        cord_render_assets._publish_artifacts(
            [
                cord_render_assets._Publication(
                    target,
                    b"committed-report",
                    "post-real close report",
                )
            ]
        )

    assert scratch_fd is not None
    assert hook_count == 1
    assert scratch_fd_after_remove == -1
    assert target.read_bytes() == b"committed-report"
    assert not any(
        path.name.startswith(f".{target.name}.txn-") for path in context.iterdir()
    )
    assert "publication committed" in str(captured.value).lower()
    assert "cleanup state is unproven" in str(captured.value).lower()
    assert any(
        "injected after real scratch descriptor close" in message
        for message in _exception_chain_messages(captured.value)
    )


def test_unexpected_rollback_executor_exception_is_wrapped_with_both_failures(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    context = _context(tmp_path, "unexpected-rollback-executor")
    target = context / "report.json"
    target.write_bytes(b"prior-report")
    callback_failure = ValueError("injected precommit validation failure")
    rollback_failure = OSError("injected rollback executor crash")

    def fail_validation() -> None:
        raise callback_failure

    def fail_rollback_executor(
        staged: list[cord_render_assets._StagedPublication]
        | tuple[cord_render_assets._StagedPublication, ...],
        created_directories: list[cord_render_assets._CreatedDirectory]
        | tuple[cord_render_assets._CreatedDirectory, ...],
    ) -> list[str]:
        assert len(staged) == 1
        assert created_directories == []
        raise rollback_failure

    monkeypatch.setattr(
        cord_render_assets,
        "_rollback_artifacts",
        fail_rollback_executor,
    )

    with pytest.raises(RuntimeError) as captured:
        cord_render_assets._publish_artifacts(
            [
                cord_render_assets._Publication(
                    target,
                    b"new-report",
                    "unexpected rollback report",
                )
            ],
            validate_before_commit=fail_validation,
        )

    assert "rollback state is unproven" in str(captured.value).lower()
    assert "injected rollback executor crash" in str(captured.value)
    assert "injected precommit validation failure" in str(captured.value)
    assert captured.value.__cause__ is rollback_failure


def test_scratch_leaf_quarantine_post_rename_failure_reconciles_both_names(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    context = _context(tmp_path, "scratch-leaf-post-rename")
    target = context / "report.json"
    target.write_bytes(b"prior-report")
    original_rename = cord_render_assets.os.rename
    attempted_names: tuple[str, str] | None = None

    def rename_backup_then_raise(
        source: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        destination: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        *,
        src_dir_fd: int | None = None,
        dst_dir_fd: int | None = None,
    ) -> None:
        nonlocal attempted_names
        source_name = Path(os.fsdecode(source)).name
        destination_name = Path(os.fsdecode(destination)).name
        if (
            attempted_names is None
            and ".backup-" in source_name
            and ".cleanup-" in destination_name
        ):
            assert src_dir_fd is not None
            assert src_dir_fd == dst_dir_fd
            original_rename(
                source,
                destination,
                src_dir_fd=src_dir_fd,
                dst_dir_fd=dst_dir_fd,
            )
            attempted_names = source_name, destination_name
            raise OSError("injected after real scratch-leaf quarantine rename")
        original_rename(
            source,
            destination,
            src_dir_fd=src_dir_fd,
            dst_dir_fd=dst_dir_fd,
        )

    monkeypatch.setattr(cord_render_assets.os, "rename", rename_backup_then_raise)

    with pytest.raises(RuntimeError) as captured:
        cord_render_assets._publish_artifacts(
            [
                cord_render_assets._Publication(
                    target,
                    b"committed-report",
                    "scratch leaf report",
                )
            ]
        )

    assert attempted_names is not None
    source_name, quarantine_name = attempted_names
    retained_names = {path.name for path in context.rglob("*")}
    assert source_name not in retained_names
    assert quarantine_name in retained_names
    assert target.read_bytes() == b"committed-report"
    assert quarantine_name in str(captured.value)
    assert "publication committed" in str(captured.value).lower()
    assert "cleanup state is unproven" in str(captured.value).lower()
    assert any(
        "injected after real scratch-leaf quarantine rename" in message
        for message in _exception_chain_messages(captured.value)
    )


def test_precommit_nested_parent_failure_retains_monotonic_directories(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    context = _context(tmp_path, "monotonic-created-parents")
    created_a = context / "created-a"
    created_b = created_a / "created-b"
    target = created_b / "report.json"
    original_mkdir = cord_render_assets.os.mkdir
    original_rmdir = cord_render_assets.os.rmdir
    created_parent_mkdir_names: list[str] = []
    created_parent_rmdir_names: list[str] = []

    def track_created_parent_mkdir(
        path: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> None:
        name = Path(os.fsdecode(path)).name
        if name in {created_a.name, created_b.name}:
            created_parent_mkdir_names.append(name)
        original_mkdir(path, mode, dir_fd=dir_fd)

    def reject_created_parent_rmdir(
        path: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        *,
        dir_fd: int | None = None,
    ) -> None:
        name = Path(os.fsdecode(path)).name
        if name in {created_a.name, created_b.name}:
            created_parent_rmdir_names.append(name)
        original_rmdir(path, dir_fd=dir_fd)

    monkeypatch.setattr(
        cord_render_assets.os,
        "mkdir",
        track_created_parent_mkdir,
    )
    monkeypatch.setattr(
        cord_render_assets.os,
        "rmdir",
        reject_created_parent_rmdir,
    )
    unexpected_prior = b"unexpected-prior"
    expectation = cord_render_assets._LeafExpectation(
        (0, 0),
        unexpected_prior,
        hashlib.sha256(unexpected_prior).hexdigest(),
    )

    failure: Exception | None = None
    try:
        cord_render_assets._publish_artifacts(
            [
                cord_render_assets._Publication(
                    target,
                    b"new-publication",
                    "monotonic parent report",
                    expectation,
                )
            ]
        )
    except Exception as error:  # noqa: BLE001 - inspect the complete failure chain
        failure = error

    assert created_parent_mkdir_names == [created_a.name, created_b.name]
    assert created_parent_rmdir_names == []
    assert created_a.is_dir()
    assert created_b.is_dir()
    assert target.exists() is False
    assert _file_bytes(context) == {}
    assert failure is not None
    assert isinstance(failure, RuntimeError)
    assert "rollback" in str(failure).lower()
    assert "unproven" in str(failure).lower()
    assert str(created_a) in str(failure)
    assert str(created_b) in str(failure)
    assert failure.__cause__ is not None
    assert any(
        "changed during operation" in message
        for message in _exception_chain_messages(failure)
    )


def test_final_precommit_verifier_preserves_same_byte_foreign_and_prior_recovery(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    context = _context(tmp_path, "final-precommit-verifier")
    target = context / "report.json"
    prior_payload = b"original-prior-payload"
    transaction_payload = b"transaction-publication"
    target.write_bytes(prior_payload)
    prior_identity = _path_identity(target)
    original_verifier = cord_render_assets._verify_published_artifacts
    validation_returned = False
    verifier_calls = 0
    post_validation_verifier_calls = 0
    replacement_count = 0
    foreign_identity: tuple[int, int] | None = None

    def complete_validation() -> None:
        nonlocal validation_returned
        validation_returned = True

    def replace_before_sole_final_precommit_verifier(
        staged: list[cord_render_assets._StagedPublication]
        | tuple[cord_render_assets._StagedPublication, ...],
    ) -> None:
        nonlocal foreign_identity, post_validation_verifier_calls
        nonlocal replacement_count, verifier_calls
        verifier_calls += 1
        if validation_returned:
            post_validation_verifier_calls += 1
            if post_validation_verifier_calls == 1:
                replacement_count += 1
                item = staged[0]
                foreign_name = ".final-precommit-same-byte-foreign"
                descriptor = cord_render_assets.os.open(
                    foreign_name,
                    cord_render_assets._CREATE_FLAGS,
                    0o600,
                    dir_fd=item.anchor.parent_fd,
                )
                try:
                    cord_render_assets._write_all(descriptor, transaction_payload)
                finally:
                    cord_render_assets.os.close(descriptor)
                cord_render_assets.os.replace(
                    foreign_name,
                    item.anchor.leaf,
                    src_dir_fd=item.anchor.parent_fd,
                    dst_dir_fd=item.anchor.parent_fd,
                )
                foreign_identity = _path_identity(target)
        original_verifier(staged)

    monkeypatch.setattr(
        cord_render_assets,
        "_verify_published_artifacts",
        replace_before_sole_final_precommit_verifier,
    )

    failure: Exception | None = None
    try:
        cord_render_assets._publish_artifacts(
            [
                cord_render_assets._Publication(
                    target,
                    transaction_payload,
                    "final precommit report",
                )
            ],
            validate_before_commit=complete_validation,
        )
    except Exception as error:  # noqa: BLE001 - inspect the complete failure chain
        failure = error

    assert validation_returned is True
    assert verifier_calls == 2
    assert post_validation_verifier_calls == 1
    assert replacement_count == 1
    assert foreign_identity is not None
    assert foreign_identity != prior_identity
    assert _path_identity(target) == foreign_identity
    assert target.read_bytes() == transaction_payload
    assert _retained_paths_with_identity(
        context,
        identity=prior_identity,
        payload=prior_payload,
        excluding=target,
    ), "precommit failure must retain the exact prior recovery inode"
    assert failure is not None
    assert isinstance(failure, RuntimeError)
    assert "rollback" in str(failure).lower()
    assert "unproven" in str(failure).lower()
    assert failure.__cause__ is not None
    assert any(
        "published artifact verification failed" in message
        for message in _exception_chain_messages(failure)
    )


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
    original_link = cord_render_assets.os.link
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
        follow_symlinks: bool = True,
    ) -> None:
        nonlocal restore_hook_ran
        source_name = Path(os.fsdecode(source)).name
        if rollback_active and not restore_hook_ran and ".backup-" in source_name:
            restore_hook_ran = True
            raise OSError("injected transient backup restore failure")
        original_link(
            source,
            target,
            src_dir_fd=src_dir_fd,
            dst_dir_fd=dst_dir_fd,
            follow_symlinks=follow_symlinks,
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
    monkeypatch.setattr(cord_render_assets.os, "link", failing_first_backup_restore)
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
    original_link = cord_render_assets.os.link
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

    def failing_all_restore_links(
        source: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        target: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        *,
        src_dir_fd: int | None = None,
        dst_dir_fd: int | None = None,
        follow_symlinks: bool = True,
    ) -> None:
        nonlocal backup_restore_hook_ran, fallback_restore_hook_ran
        source_name = Path(os.fsdecode(source)).name
        if rollback_active and source_name.startswith(".index.json.backup-"):
            backup_restore_hook_ran = True
            raise OSError("injected persistent backup restore failure")
        if rollback_active and source_name.startswith(".index.json.restore-"):
            fallback_restore_hook_ran = True
            raise OSError("injected persistent payload restore failure")
        original_link(
            source,
            target,
            src_dir_fd=src_dir_fd,
            dst_dir_fd=dst_dir_fd,
            follow_symlinks=follow_symlinks,
        )

    monkeypatch.setattr(
        cord_render_assets, "verify_atlas_round_trip", failing_validation_callback
    )
    monkeypatch.setattr(cord_render_assets.os, "link", failing_all_restore_links)

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


def test_absent_prior_rollback_preserves_concurrent_create_at_atomic_capture(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    context = _context(tmp_path, "rollback-absent-prior-concurrent-create")
    target = context / "new-report.json"
    transaction_payload = b"transaction-publication"
    concurrent_payload = b"concurrent-operator-create"
    original_rename = cord_render_assets.os.rename
    original_replace = cord_render_assets.os.replace
    original_unlink = cord_render_assets.os.unlink
    rollback_active = False
    capture_hook_count = 0
    payload_seen_at_capture: bytes | None = None
    unsafe_visible_mutations: list[str] = []

    def fail_validation() -> None:
        nonlocal rollback_active
        rollback_active = True
        raise ValueError("injected absent-prior validation failure")

    def racing_visible_capture(
        source: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        destination: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        *,
        src_dir_fd: int | None = None,
        dst_dir_fd: int | None = None,
    ) -> None:
        nonlocal capture_hook_count, payload_seen_at_capture
        source_name = Path(os.fsdecode(source)).name
        destination_name = Path(os.fsdecode(destination)).name
        if (
            rollback_active
            and source_name == target.name
            and ".rollback-" in destination_name
            and capture_hook_count == 0
        ):
            assert src_dir_fd is not None
            payload_seen_at_capture = target.read_bytes()
            capture_hook_count += 1
            concurrent_name = ".concurrent-operator-create"
            descriptor = cord_render_assets.os.open(
                concurrent_name,
                cord_render_assets._CREATE_FLAGS,
                0o600,
                dir_fd=src_dir_fd,
            )
            try:
                cord_render_assets._write_all(descriptor, concurrent_payload)
            finally:
                cord_render_assets.os.close(descriptor)
            original_replace(
                concurrent_name,
                source_name,
                src_dir_fd=src_dir_fd,
                dst_dir_fd=src_dir_fd,
            )
        original_rename(
            source,
            destination,
            src_dir_fd=src_dir_fd,
            dst_dir_fd=dst_dir_fd,
        )

    def reject_visible_unlink(
        path: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        *,
        dir_fd: int | None = None,
    ) -> None:
        if rollback_active and Path(os.fsdecode(path)).name == target.name:
            unsafe_visible_mutations.append("unlink")
            raise AssertionError("rollback must not unlink a visible leaf")
        original_unlink(path, dir_fd=dir_fd)

    monkeypatch.setattr(cord_render_assets.os, "rename", racing_visible_capture)
    monkeypatch.setattr(cord_render_assets.os, "unlink", reject_visible_unlink)

    with pytest.raises(Exception) as captured:
        cord_render_assets._publish_artifacts(
            [
                cord_render_assets._Publication(
                    target,
                    transaction_payload,
                    "concurrent-create report",
                )
            ],
            validate_before_commit=fail_validation,
        )

    assert capture_hook_count == 1
    assert payload_seen_at_capture == transaction_payload
    assert target.read_bytes() == concurrent_payload
    assert concurrent_payload in _file_bytes(context).values()
    assert unsafe_visible_mutations == []
    assert isinstance(captured.value, RuntimeError)
    assert "rollback" in str(captured.value).lower()
    assert "unproven" in str(captured.value).lower()
    assert captured.value.__cause__ is not None
    assert any(
        "injected absent-prior validation failure" in message
        for message in _exception_chain_messages(captured.value)
    )


def test_retained_byte_rollback_preserves_concurrent_update_at_atomic_capture(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    context = _context(tmp_path, "rollback-retained-concurrent-update")
    target = context / "report.json"
    prior_payload = b"prior-operator-payload"
    transaction_payload = b"transaction-publication"
    concurrent_payload = b"concurrent-operator-update"
    target.write_bytes(prior_payload)
    original_rename = cord_render_assets.os.rename
    original_replace = cord_render_assets.os.replace
    original_unlink = cord_render_assets.os.unlink
    rollback_active = False
    capture_hook_count = 0
    payload_seen_at_capture: bytes | None = None
    unsafe_visible_mutations: list[str] = []

    def fail_validation() -> None:
        nonlocal rollback_active
        rollback_active = True
        raise ValueError("injected retained-byte validation failure")

    def racing_visible_capture(
        source: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        destination: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        *,
        src_dir_fd: int | None = None,
        dst_dir_fd: int | None = None,
    ) -> None:
        nonlocal capture_hook_count, payload_seen_at_capture
        source_name = Path(os.fsdecode(source)).name
        destination_name = Path(os.fsdecode(destination)).name
        if (
            rollback_active
            and source_name == target.name
            and ".rollback-" in destination_name
            and capture_hook_count == 0
        ):
            assert src_dir_fd is not None
            payload_seen_at_capture = target.read_bytes()
            capture_hook_count += 1
            concurrent_name = ".concurrent-operator-update"
            descriptor = cord_render_assets.os.open(
                concurrent_name,
                cord_render_assets._CREATE_FLAGS,
                0o600,
                dir_fd=src_dir_fd,
            )
            try:
                cord_render_assets._write_all(descriptor, concurrent_payload)
            finally:
                cord_render_assets.os.close(descriptor)
            original_replace(
                concurrent_name,
                source_name,
                src_dir_fd=src_dir_fd,
                dst_dir_fd=src_dir_fd,
            )
        original_rename(
            source,
            destination,
            src_dir_fd=src_dir_fd,
            dst_dir_fd=dst_dir_fd,
        )

    def reject_visible_unlink(
        path: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        *,
        dir_fd: int | None = None,
    ) -> None:
        if rollback_active and Path(os.fsdecode(path)).name == target.name:
            unsafe_visible_mutations.append("unlink")
            raise AssertionError("rollback must not unlink a visible leaf")
        original_unlink(path, dir_fd=dir_fd)

    monkeypatch.setattr(cord_render_assets.os, "rename", racing_visible_capture)
    monkeypatch.setattr(cord_render_assets.os, "unlink", reject_visible_unlink)

    with pytest.raises(Exception) as captured:
        cord_render_assets._publish_artifacts(
            [
                cord_render_assets._Publication(
                    target,
                    transaction_payload,
                    "concurrent-update report",
                )
            ],
            validate_before_commit=fail_validation,
        )

    assert capture_hook_count == 1
    assert payload_seen_at_capture == transaction_payload
    assert target.read_bytes() == concurrent_payload
    assert prior_payload in _file_bytes(context).values()
    assert unsafe_visible_mutations == []
    assert isinstance(captured.value, RuntimeError)
    assert "rollback" in str(captured.value).lower()
    assert "unproven" in str(captured.value).lower()
    assert captured.value.__cause__ is not None
    assert any(
        "injected retained-byte validation failure" in message
        for message in _exception_chain_messages(captured.value)
    )


def test_staging_verification_and_cleanup_failure_discloses_debris_and_closes_anchor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    context = _context(tmp_path, "staging-double-failure")
    target = context / "report.json"
    original_open_parent = cord_render_assets._open_parent
    original_read_from_fd = cord_render_assets._read_from_fd
    original_unlink = cord_render_assets.os.unlink
    staged_anchors: list[cord_render_assets._HeldParent] = []
    staged_parent_fds: list[int] = []
    verification_hook_count = 0
    cleanup_hook_count = 0
    cleanup_dir_fds: list[int | None] = []

    def tracking_open_parent(
        path: Path,
        *,
        create: bool = False,
        creation_ledger: list[cord_render_assets._CreatedDirectory] | None = None,
    ) -> cord_render_assets._HeldParent:
        anchor = original_open_parent(
            path,
            create=create,
            creation_ledger=creation_ledger,
        )
        if create and anchor.path == target.absolute():
            staged_anchors.append(anchor)
            staged_parent_fds.append(anchor.parent_fd)
        return anchor

    def failing_staged_verification(
        parent_fd: int,
        name: str,
        *,
        label: str = "artifact",
    ) -> tuple[bytes, os.stat_result]:
        nonlocal verification_hook_count
        if (
            name.startswith(f".{target.name}.tmp-")
            and label.startswith("staged artifact")
            and verification_hook_count == 0
        ):
            verification_hook_count += 1
            raise OSError("injected staged verification failure")
        return original_read_from_fd(parent_fd, name, label=label)

    def failing_staged_cleanup(
        path: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        *,
        dir_fd: int | None = None,
    ) -> None:
        nonlocal cleanup_hook_count
        name = Path(os.fsdecode(path)).name
        if name.startswith(f".{target.name}.tmp-"):
            cleanup_hook_count += 1
            cleanup_dir_fds.append(dir_fd)
            raise OSError("injected staging cleanup failure")
        original_unlink(path, dir_fd=dir_fd)

    monkeypatch.setattr(cord_render_assets, "_open_parent", tracking_open_parent)
    monkeypatch.setattr(
        cord_render_assets, "_read_from_fd", failing_staged_verification
    )
    monkeypatch.setattr(cord_render_assets.os, "unlink", failing_staged_cleanup)

    with pytest.raises(Exception) as captured:
        cord_render_assets.write_owner_json(target, {"new": True})

    hidden_temporaries = sorted(
        path.name
        for path in context.rglob("*")
        if path.name.startswith(f".{target.name}.tmp-")
    )
    anchors_were_closed = all(anchor.parent_fd == -1 for anchor in staged_anchors)
    for anchor in staged_anchors:
        if anchor.parent_fd >= 0:
            anchor.close()
    assert verification_hook_count == 1
    assert cleanup_hook_count >= 1
    assert staged_anchors
    assert all(directory_fd is not None for directory_fd in cleanup_dir_fds)
    assert anchors_were_closed
    assert not target.exists()
    assert isinstance(captured.value, RuntimeError)
    assert "rollback" in str(captured.value).lower()
    assert "unproven" in str(captured.value).lower()
    assert captured.value.__cause__ is not None
    assert any(
        "injected staged verification failure" in message
        for message in _exception_chain_messages(captured.value)
    )
    if hidden_temporaries:
        assert any(
            term in str(captured.value).lower() for term in ("temporary", "debris")
        )


def test_staging_cleanup_quarantines_but_never_deletes_replaced_foreign_temp(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    context = _context(tmp_path, "staging-foreign-temp")
    target = context / "report.json"
    foreign_payload = b"concurrent-foreign-scratch-payload"
    original_read_from_fd = cord_render_assets._read_from_fd
    original_rename = cord_render_assets.os.rename
    original_replace = cord_render_assets.os.replace
    original_unlink = cord_render_assets.os.unlink
    verification_hook_count = 0
    replacement_hook_count = 0
    temp_unlink_count = 0

    def failing_staged_verification(
        parent_fd: int,
        name: str,
        *,
        label: str = "artifact",
    ) -> tuple[bytes, os.stat_result]:
        nonlocal verification_hook_count
        if (
            name.startswith(f".{target.name}.tmp-")
            and label.startswith("staged artifact")
            and verification_hook_count == 0
        ):
            verification_hook_count += 1
            raise OSError("injected staged verification failure")
        return original_read_from_fd(parent_fd, name, label=label)

    def replacing_temp_at_cleanup_capture(
        source: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        destination: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        *,
        src_dir_fd: int | None = None,
        dst_dir_fd: int | None = None,
    ) -> None:
        nonlocal replacement_hook_count
        source_name = Path(os.fsdecode(source)).name
        destination_name = Path(os.fsdecode(destination)).name
        if (
            source_name.startswith(f".{target.name}.tmp-")
            and ".cleanup-" in destination_name
            and replacement_hook_count == 0
        ):
            assert src_dir_fd is not None
            replacement_hook_count += 1
            foreign_name = ".concurrent-foreign-temp"
            descriptor = cord_render_assets.os.open(
                foreign_name,
                cord_render_assets._CREATE_FLAGS,
                0o600,
                dir_fd=src_dir_fd,
            )
            try:
                cord_render_assets._write_all(descriptor, foreign_payload)
            finally:
                cord_render_assets.os.close(descriptor)
            original_replace(
                foreign_name,
                source_name,
                src_dir_fd=src_dir_fd,
                dst_dir_fd=src_dir_fd,
            )
        original_rename(
            source,
            destination,
            src_dir_fd=src_dir_fd,
            dst_dir_fd=dst_dir_fd,
        )

    def tracking_unlink(
        path: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        *,
        dir_fd: int | None = None,
    ) -> None:
        nonlocal temp_unlink_count
        if Path(os.fsdecode(path)).name.startswith(f".{target.name}.tmp-"):
            temp_unlink_count += 1
        original_unlink(path, dir_fd=dir_fd)

    monkeypatch.setattr(
        cord_render_assets,
        "_read_from_fd",
        failing_staged_verification,
    )
    monkeypatch.setattr(
        cord_render_assets.os, "rename", replacing_temp_at_cleanup_capture
    )
    monkeypatch.setattr(cord_render_assets.os, "unlink", tracking_unlink)

    with pytest.raises(Exception) as captured:
        cord_render_assets.write_owner_json(target, {"new": True})

    assert verification_hook_count == 1
    assert replacement_hook_count == 1
    assert temp_unlink_count == 0
    assert not target.exists()
    assert foreign_payload in _file_bytes(context).values()
    assert isinstance(captured.value, RuntimeError)
    assert "rollback" in str(captured.value).lower()
    assert "unproven" in str(captured.value).lower()
    assert any(
        "injected staged verification failure" in message
        for message in _exception_chain_messages(captured.value)
    )


def test_partial_nested_parent_failure_cleans_or_discloses_and_closes_descriptors(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    context = _context(tmp_path, "partial-nested-parent")
    created_a = context / "created-a"
    target = created_a / "created-b" / "report.json"
    original_open = cord_render_assets.os.open
    original_close = cord_render_assets.os.close
    original_mkdir = cord_render_assets.os.mkdir
    opened_created_parent_fds: list[int] = []
    closed_fds: list[int] = []
    failing_mkdir_dir_fd: int | None = None
    mkdir_hook_count = 0
    created_parent_seen_at_failure = False

    def tracking_open(
        path: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        flags: int,
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> int:
        descriptor = original_open(path, flags, mode, dir_fd=dir_fd)
        if Path(os.fsdecode(path)).name == created_a.name and dir_fd is not None:
            opened_created_parent_fds.append(descriptor)
        return descriptor

    def tracking_close(descriptor: int) -> None:
        closed_fds.append(descriptor)
        original_close(descriptor)

    def failing_second_parent_mkdir(
        path: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> None:
        nonlocal failing_mkdir_dir_fd, mkdir_hook_count
        nonlocal created_parent_seen_at_failure
        if Path(os.fsdecode(path)).name == "created-b" and mkdir_hook_count == 0:
            mkdir_hook_count += 1
            failing_mkdir_dir_fd = dir_fd
            created_parent_seen_at_failure = created_a.is_dir()
            raise OSError("injected nested parent creation failure")
        original_mkdir(path, mode, dir_fd=dir_fd)

    monkeypatch.setattr(cord_render_assets.os, "open", tracking_open)
    monkeypatch.setattr(cord_render_assets.os, "close", tracking_close)
    monkeypatch.setattr(cord_render_assets.os, "mkdir", failing_second_parent_mkdir)

    with pytest.raises(Exception) as captured:
        cord_render_assets.write_owner_json(target, {"new": True})

    chain = _exception_chain_messages(captured.value)
    unclosed_created_parent_fds = set(opened_created_parent_fds) - set(closed_fds)
    for descriptor in unclosed_created_parent_fds:
        try:
            original_close(descriptor)
        except OSError:
            pass
    assert mkdir_hook_count == 1
    assert created_parent_seen_at_failure is True
    assert opened_created_parent_fds
    assert failing_mkdir_dir_fd in opened_created_parent_fds
    assert not unclosed_created_parent_fds
    assert not target.exists()
    assert _file_bytes(context) == {}
    assert created_a.is_dir()
    assert any(
        "injected nested parent creation failure" in message for message in chain
    )
    assert isinstance(captured.value, RuntimeError)
    assert "rollback" in str(captured.value).lower()
    assert "unproven" in str(captured.value).lower()
    assert str(created_a) in str(captured.value)
    assert captured.value.__cause__ is not None


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

    with pytest.raises(RuntimeError) as captured:
        build_lossless_atlases_with_report(
            [source], output, report_path=external_report
        )

    assert hook_ran is True
    assert output.is_dir()
    assert not external_report.exists()
    assert external_report.parent.is_dir()
    assert _file_bytes(output) == {}
    assert _file_bytes(external_report.parent) == {}
    assert "rollback" in str(captured.value).lower()
    assert "unproven" in str(captured.value).lower()
    assert str(output) in str(captured.value)
    assert str(external_report.parent) in str(captured.value)
    assert any(
        "injected first-build verification failure" in message
        for message in _exception_chain_messages(captured.value)
    )


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


@pytest.mark.parametrize("alpha", range(249, 256))
@pytest.mark.parametrize("textured", [False, True], ids=["flat", "textured"])
@pytest.mark.parametrize("seam", ["horizontal", "cross"])
def test_transparency_inspection_rejects_fragmented_near_full_matte_alpha_family(
    tmp_path: Path,
    alpha: int,
    textured: bool,
    seam: str,
) -> None:
    width, height = 160, 100
    inset = 5
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
    draw.line(
        (inset, height // 2, width - inset - 1, height // 2),
        fill=(0, 0, 0, 0),
    )
    if seam == "cross":
        draw.line(
            (width // 2, inset, width // 2, height - inset - 1),
            fill=(0, 0, 0, 0),
        )
    path = (
        tmp_path / f"fragmented-{seam}-{alpha}-{'textured' if textured else 'flat'}.png"
    )
    image.save(path, format="PNG")

    with pytest.raises(ValueError, match="boundary .*flood"):
        inspect_transparency(path, width, height, (0, 255, 0))


def test_transparency_inspection_rejects_production_scale_fragmented_matte(
    tmp_path: Path,
) -> None:
    width, height = 1536, 1024
    inset = 22
    alpha = 249
    image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rectangle(
        (inset, inset, width - inset - 1, height - inset - 1),
        fill=(30, 40, 100, alpha),
    )
    for x in range(inset, width - inset, 37):
        draw.line(
            (x, inset, x, height - inset - 1),
            fill=(90, 30, 20, alpha),
        )
    draw.line(
        (inset, height // 2, width - inset - 1, height // 2),
        fill=(0, 0, 0, 0),
    )
    draw.line(
        (width // 2, inset, width // 2, height - inset - 1),
        fill=(0, 0, 0, 0),
    )
    path = tmp_path / "production-fragmented-cross-alpha-249-textured.png"
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


def test_transparency_inspection_allows_large_central_product_with_antialias_perimeter(
    tmp_path: Path,
) -> None:
    width = height = 200
    side = round(math.sqrt(0.65) * width)
    inset = (width - side) // 2
    image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    box = (inset, inset, inset + side - 1, inset + side - 1)
    draw.rectangle(box, fill=(90, 80, 70, 96))
    draw.rectangle(
        (inset + 1, inset + 1, inset + side - 2, inset + side - 2),
        fill=(90, 80, 70, 255),
    )
    path = tmp_path / "central-65-percent-one-pixel-antialias.png"
    image.save(path, format="PNG")

    report = inspect_transparency(path, width, height, (0, 255, 0))

    assert side * side == 25_921
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
