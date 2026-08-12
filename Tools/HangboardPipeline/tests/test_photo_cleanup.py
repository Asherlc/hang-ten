from __future__ import annotations

from collections import Counter
from hashlib import sha256

import cv2
import numpy as np
import pytest

import hangboard_vectorizer.photo_cleanup as cleanup_module
from hangboard_vectorizer.display_paths import DisplayPath, flatten_display_path
from hangboard_vectorizer.photo_cleanup import clean_beastmaker_photo
from hangboard_vectorizer.templates import get_product_template


def _source_rgb() -> np.ndarray:
    template = get_product_template("beastmaker-1000")
    assert template.display_outline_path is not None
    assert template.display_front_path is not None

    canonical = np.full((259, 1000, 3), 255, dtype=np.uint8)
    body = _path_mask(template.display_outline_path)
    front = _path_mask(template.display_front_path)
    canonical[body] = (213, 190, 151)
    canonical[front] = (188, 158, 119)
    for y in range(5, 255, 7):
        canonical[y, body[y]] = (218, 196, 158)

    for region in template.regions:
        assert region.display_path is not None
        mask = _path_mask(region.display_path) & body
        if region.type == "pocket":
            canonical[mask] = (96, 67, 38)
            for y in range(0, 259, 5):
                canonical[y, mask[y]] = (115, 82, 47)
        elif region.type == "sloper":
            canonical[mask] = (206, 181, 143)
        else:
            canonical[mask] = (219, 198, 163)

    cv2.putText(
        canonical,
        "brand",
        (222, 105),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.58,
        (45, 28, 18),
        2,
        cv2.LINE_AA,
    )
    cv2.putText(
        canonical,
        "1000",
        (675, 105),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.58,
        (45, 28, 18),
        2,
        cv2.LINE_AA,
    )
    for center in _screw_centers():
        cv2.circle(canonical, center, 6, (42, 31, 22), -1)
        cv2.circle(canonical, center, 3, (250, 250, 247), -1)

    source = np.full((318, 1080, 3), 255, dtype=np.uint8)
    source[30:289, 35:1041] = cv2.resize(
        canonical, (1006, 259), interpolation=cv2.INTER_LANCZOS4
    )
    return source


def _path_mask(path: DisplayPath) -> np.ndarray:
    contour = flatten_display_path(path)
    mask = np.zeros((259, 1000), dtype=np.uint8)
    cv2.fillPoly(mask, [np.rint(contour).astype(np.int32)], 1)
    return mask.astype(bool)


def _screw_centers() -> tuple[tuple[int, int], ...]:
    return (
        (110, 75),
        (432, 75),
        (570, 75),
        (892, 74),
        (184, 211),
        (818, 211),
    )


def _register_fixture(monkeypatch: pytest.MonkeyPatch, source: np.ndarray) -> None:
    fingerprint = sha256(source.tobytes()).hexdigest()
    monkeypatch.setattr(
        cleanup_module,
        "_AUTHORITATIVE_SOURCE_RGB_SHA256",
        fingerprint,
        raising=False,
    )


def _source_with_contact_shadow() -> np.ndarray:
    source = _source_rgb()
    canonical = cv2.resize(
        source[30:289, 35:1041], (1000, 259), interpolation=cv2.INTER_LANCZOS4
    )
    canonical[256, 100:900] = (35, 34, 32)
    canonical[256, 480:520] = (80, 70, 60)
    canonical[257, 100:900] = (70, 70, 69)
    canonical[258, 100:900] = (110, 110, 109)
    source[30:289, 35:1041] = cv2.resize(
        canonical, (1006, 259), interpolation=cv2.INTER_LANCZOS4
    )
    return source


def test_photo_cleanup_rejects_wrong_dimensions_and_content(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = _source_rgb()
    _register_fixture(monkeypatch, source)

    taller = np.pad(source, ((1, 0), (0, 0), (0, 0)), constant_values=255)
    with pytest.raises(ValueError, match="registration"):
        clean_beastmaker_photo(taller)

    shifted = np.roll(source, 1, axis=1)
    with pytest.raises(ValueError, match="registration"):
        clean_beastmaker_photo(shifted)


def test_photo_cleanup_is_deterministic_and_preserves_alpha_contract(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = _source_rgb()
    _register_fixture(monkeypatch, source)

    first = clean_beastmaker_photo(source)
    second = clean_beastmaker_photo(source)

    assert first.rgba.shape == (259, 1000, 4)
    assert first.review_rgb.shape == (459, 1200, 3)
    assert first.rgba.dtype == np.uint8
    assert np.array_equal(first.rgba, second.rgba)
    assert np.array_equal(first.review_rgb, second.review_rgb)
    assert tuple(first.rgba[0, 0]) == (0, 0, 0, 0)
    assert tuple(first.review_rgb[0, 0]) == (248, 247, 244)


def test_photo_cleanup_removes_branding_and_screw_heads(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = _source_rgb()
    _register_fixture(monkeypatch, source)
    canonical = cv2.resize(
        source[30:289, 35:1041], (1000, 259), interpolation=cv2.INTER_LANCZOS4
    )
    result = clean_beastmaker_photo(source)
    before = cv2.cvtColor(canonical, cv2.COLOR_RGB2GRAY)
    after = cv2.cvtColor(result.rgba[..., :3], cv2.COLOR_RGB2GRAY)

    for x1, y1, x2, y2 in ((216, 84, 352, 113), (658, 84, 786, 113)):
        assert np.count_nonzero(before[y1:y2, x1:x2] < 120) > 100
        assert np.count_nonzero(after[y1:y2, x1:x2] < 120) == 0

    for x, y in _screw_centers():
        assert before[y, x] >= 245
        assert after[y, x] < 235


def test_photo_cleanup_alpha_matches_full_registered_silhouette(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = _source_rgb()
    _register_fixture(monkeypatch, source)
    result = clean_beastmaker_photo(source)
    template = get_product_template("beastmaker-1000")
    assert template.display_outline_path is not None
    expected = _path_mask(template.display_outline_path)
    actual = result.rgba[..., 3] >= 128

    intersection = np.count_nonzero(actual & expected)
    union = np.count_nonzero(actual | expected)
    assert intersection / union > 0.98
    assert float(np.mean(result.rgba[-3:, :, 3][expected[-3:]])) > 220.0


def test_photo_cleanup_separates_bottom_edge_from_contact_shadow(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = _source_with_contact_shadow()
    _register_fixture(monkeypatch, source)

    result = clean_beastmaker_photo(source)

    assert result.rgba[255, 500, 3] >= 128
    assert result.rgba[258, 500, 3] == 0
    assert float(np.mean(result.review_rgb[356, 600])) > 200.0
    assert tuple(result.review_rgb[358, 600]) == (248, 247, 244)


def test_photo_cleanup_preserves_exact_template_inventory_and_depth(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = _source_rgb()
    _register_fixture(monkeypatch, source)
    result = clean_beastmaker_photo(source)
    template = get_product_template("beastmaker-1000")
    counts = Counter(region.type for region in template.regions)

    assert counts == {"pocket": 17, "sloper": 3, "jug": 2}
    assert tuple(
        region.id for region in template.regions if region.type == "sloper"
    ) == ("sloper-35-left", "sloper-35-right", "sloper-center")

    assert template.display_outline_path is not None
    body = _path_mask(template.display_outline_path)
    light = cv2.cvtColor(result.rgba[..., :3], cv2.COLOR_RGB2LAB)[..., 0]
    for region in template.regions:
        assert region.display_path is not None
        mask = _path_mask(region.display_path) & body
        assert float(np.mean(result.rgba[..., 3][mask])) > 245.0
        if region.type == "pocket":
            assert float(np.mean(light[mask])) < 155.0
