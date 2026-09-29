"""Wide rectangular sling slots must retain their actual outer rim."""
import sys
from pathlib import Path

import pytest

pytest.importorskip("trimesh")
pytest.importorskip("shapely")
from shapely.geometry import Point, box

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from solve_threaded_rope import bearing_section


def test_wide_rectangular_through_slot_opens_only_the_selected_mouth():
    pieces = [box(-0.05, -0.045, -0.0105, 0.045),
              box(0.0155, -0.045, 0.05, 0.045)]
    section = bearing_section(pieces, [0.0025, 0.045], 0.0021, channel_profile="rectangular")
    assert section.is_valid and not section.interiors
    assert not section.covers(Point(0.0025, 0.045))
    assert section.covers(Point(0.0025, -0.045))
    assert section.covers(Point(0.03, 0.045))


def test_rectangular_bridge_rejects_tapered_or_overlapping_sections():
    with pytest.raises(ValueError, match="rectangular"):
        bearing_section([box(-.05, -.045, -.01, .045),
                         box(.015, -.04, .05, .04)],
                        [.0025, .045], .0021, channel_profile="rectangular")


@pytest.mark.parametrize("portal_id", ["central-front", "central-back"])
def test_live_mouth_is_a_sliding_region_without_an_authored_bearing(portal_id):
    # Numerical wall seating is covered by ClavelliumRopePhysicsTests. This
    # package regression prevents restoring the defect as a fixed center pin.
    import json
    root = Path(__file__).resolve().parents[3]
    data = json.loads((root / "Hangboards/clavellium-training-block/assets/primary.physics.json").read_text())
    portal = next(p for p in data["portals"] if p["id"] == portal_id)
    assert portal["center"][1] == 0.0025
    assert max(p[1] for p in portal["boundary"]) == 0.0155
    rope = data["profiles"][0]["ropes"][0]
    assert rope["radius"] == 1.75 * rope["baselineRadius"] == 0.0035
    node = next(n for n in rope["nodes"] if n.get("portalID") == portal_id)
    assert "point" not in node
    assert "cordContactPoints" not in data
