import pytest
from hangboard_packages.cord_paths import validate_cord_paths


def test_distinct_leads_can_share_only_their_support_endpoint():
    validate_cord_paths({"left": [(0, 1, 0), (-1, 0, 0)], "right": [(0, 1, 0), (1, 0, 0)]},
                        {"left": .01, "right": .01})


def test_a_closed_loop_can_meet_at_its_support():
    validate_cord_paths({"loop": [(0, 1, 0), (-1, 0, 0), (0, -1, 0), (1, 0, 0), (0, 1, 0)]}, {"loop": .01})


@pytest.mark.parametrize("paths", [
    {"loop": [(0, 1, 0), (0, 0, 0), (0, -1, 0), (0, 0, 0), (0, 1, 0)]},
    {"first": [(0, 1, 0), (0, 0, 0)], "duplicate": [(0, 1, 0), (0, 0, 0)]},
    {"first": [(-1, 0, 0), (1, 0, 0)], "second": [(0, -1, 0), (0, 1, 0)]},
    {"first": [(-1, 0, 0), (0, 0, 0), (1, 0, 0)],
     "second": [(0, -1, 0), (0, 0, 0), (0, 1, 0)]},
    {"first": [(-1, 0, 0), (0, 0, 0), (1, 0, 0)],
     "second": [(0, 0, 0), (0, 1, 0)]},
])
def test_retraced_or_crossing_paths_are_rejected_even_with_shared_endpoints(paths):
    with pytest.raises(ValueError, match="retrace|intersect"):
        validate_cord_paths(paths)


def test_nonlocal_tubes_cannot_overlap_without_centerline_crossing():
    with pytest.raises(ValueError, match="tubes intersect"):
        validate_cord_paths({"first": [(-1, 0, 0), (1, 0, 0)],
                             "second": [(-1, .01, 0), (1, .01, 0)]}, {"first": .01, "second": .01})
