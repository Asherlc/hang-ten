"""Fail-closed raster simplification profiles for Stage 1 onboarding."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import numpy as np

from .photo_cleanup import clean_beastmaker_photo


@dataclass(frozen=True, slots=True)
class SimplifiedRaster:
    """Canonical cleanup output owned by a Stage 1 profile."""

    rgba: np.ndarray
    review_rgb: np.ndarray
    repair_mask: np.ndarray

    def __post_init__(self) -> None:
        for field_name in ("rgba", "review_rgb", "repair_mask"):
            value = getattr(self, field_name)
            if not isinstance(value, np.ndarray) or value.dtype != np.uint8:
                raise ValueError("simplified raster arrays must be uint8 numpy arrays")
            frozen = np.frombuffer(value.tobytes(), dtype=np.uint8).reshape(value.shape)
            object.__setattr__(self, field_name, frozen)


class CleanupProfile(Protocol):
    """A product/material-specific cleanup implementation."""

    profile_id: str
    product_id: str
    material: str
    piece_count: int

    def simplify(self, source_rgb: np.ndarray) -> SimplifiedRaster: ...


@dataclass(frozen=True, slots=True)
class BeastmakerTulipwoodCleanupProfile:
    """The approved one-piece Beastmaker 1000 Tulipwood cleanup profile."""

    profile_id: str = "beastmaker-1000-tulipwood-v1"
    product_id: str = "beastmaker-1000"
    material: str = "Tulipwood"
    piece_count: int = 1

    def simplify(self, source_rgb: np.ndarray) -> SimplifiedRaster:
        cleaned = clean_beastmaker_photo(source_rgb)
        return SimplifiedRaster(
            rgba=cleaned.rgba,
            review_rgb=cleaned.review_rgb,
            repair_mask=cleaned.repair_mask,
        )
