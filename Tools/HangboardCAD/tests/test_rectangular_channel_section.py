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
