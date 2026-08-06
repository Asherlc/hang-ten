"""Post-override validation for product-backed exported regions."""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence

from .models import ConversionError
from .regions import GripRegion
from .templates import ProductTemplate


BEASTMAKER_1000_REGION_IDS = (
    "jug-left",
    "jug-right",
    "sloper-35-left",
    "sloper-35-right",
    "sloper-center",
    "pocket-top-outer-left",
    "pocket-top-outer-right",
    "pocket-top-left",
    "pocket-top-right",
    "pocket-middle-outer-left",
    "pocket-middle-mid-left",
    "pocket-middle-inner-left",
    "pocket-middle-center",
    "pocket-middle-inner-right",
    "pocket-middle-mid-right",
    "pocket-middle-outer-right",
    "pocket-bottom-outer-left",
    "pocket-bottom-mid-left",
    "pocket-bottom-inner-left",
    "pocket-bottom-inner-right",
    "pocket-bottom-mid-right",
    "pocket-bottom-outer-right",
)

_BEASTMAKER_1000_TYPE_COUNTS = Counter({"pocket": 17, "sloper": 3, "jug": 2})
_BEASTMAKER_1000_TYPES = {
    region_id: (
        "jug"
        if region_id.startswith("jug-")
        else "sloper"
        if region_id.startswith("sloper-")
        else "pocket"
    )
    for region_id in BEASTMAKER_1000_REGION_IDS
}
BEASTMAKER_1000_FORBIDDEN_SPLIT_CENTER_IDS = frozenset(
    {
        "sloper-20-left",
        "sloper-20-right",
        "sloper-center-left",
        "sloper-center-right",
    }
)
BEASTMAKER_1000_SLOPER_IDS = (
    "sloper-35-left",
    "sloper-35-right",
    "sloper-center",
)


def validate_product_output(
    product: ProductTemplate,
    regions: Sequence[GripRegion],
) -> None:
    """Validate final enabled topology and native display geometry before export."""
    region_ids = tuple(region.id for region in regions)
    if len(set(region_ids)) != len(region_ids):
        raise ConversionError("product output region IDs must be unique")

    enabled = tuple(region for region in regions if not region.disabled)
    if product.product_id == "beastmaker-1000":
        _validate_beastmaker_1000_output(regions, enabled)

    if product.render_asset is not None:
        _validate_native_display_geometry(product, enabled)


def _validate_beastmaker_1000_output(
    regions: Sequence[GripRegion],
    enabled: Sequence[GripRegion],
) -> None:
    all_ids = {region.id for region in regions}
    if all_ids.intersection(BEASTMAKER_1000_FORBIDDEN_SPLIT_CENTER_IDS):
        raise ConversionError(
            "beastmaker-1000 output requires canonical unsplit center topology"
        )

    enabled_ids = tuple(region.id for region in enabled)
    if enabled_ids != BEASTMAKER_1000_REGION_IDS:
        raise ConversionError(
            "beastmaker-1000 output requires canonical enabled region IDs and order"
        )

    type_counts = Counter(region.type for region in enabled)
    has_canonical_types = all(
        region.type == _BEASTMAKER_1000_TYPES[region.id] for region in enabled
    )
    if type_counts != _BEASTMAKER_1000_TYPE_COUNTS or not has_canonical_types:
        raise ConversionError(
            "beastmaker-1000 output requires canonical 17-pocket, 3-sloper, "
            "2-jug topology"
        )

    if any(region.template_region_id != region.id for region in enabled):
        raise ConversionError(
            "beastmaker-1000 output requires canonical native region identity"
        )

    center_regions = tuple(
        region
        for region in enabled
        if region.id == "sloper-center" and region.type == "sloper"
    )
    if len(center_regions) != 1:
        raise ConversionError(
            "beastmaker-1000 output requires one canonical uninterrupted sloper-center"
        )


def _validate_native_display_geometry(
    product: ProductTemplate,
    enabled: Sequence[GripRegion],
) -> None:
    template_regions = {region.id: region for region in product.regions}
    if len(template_regions) != len(product.regions):
        raise ConversionError("product template region IDs must be unique")

    seen_origins: set[str] = set()
    for region in enabled:
        origin_id = region.template_region_id
        template_region = template_regions.get(origin_id or "")
        if (
            origin_id is None
            or region.display_path is None
            or template_region is None
            or template_region.display_path is None
            or region.display_path != template_region.display_path
            or origin_id in seen_origins
        ):
            raise ConversionError(
                f"asset-backed region {region.id!r} requires valid native "
                "display geometry"
            )
        seen_origins.add(origin_id)
