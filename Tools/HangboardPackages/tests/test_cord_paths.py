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


@pytest.mark.parametrize("reverse_lead,reverse_bore", [(False, False), (True, False), (False, True)])
def test_native_lead_and_bore_keep_the_continuous_bend_neighborhood(reverse_lead, reverse_bore):
    # Actual native Block route: the 2.7 mm exterior collar is an ordinary
    # bend in one continuous cord, even though its bore has another strand ID.
    lead = [(0.176893881, .08, -.07), (.078446941, .04, -.04735),
            (-.02, 0, -.0247), (-.02, 0, -.022)]
    bore = [(-.02, 0, -.022), (-.02, 0, 0), (-.02, 0, .022)]
    if reverse_lead:
        lead.reverse()
    if reverse_bore:
        bore.reverse()
    validate_cord_paths({"lead": lead, "bore": bore}, {"lead": .0025, "bore": .0025})


def test_a_closed_cord_keeps_the_bend_neighborhood_across_its_closure():
    validate_cord_paths({"loop": [(0, 0, 0), (.0027, 0, 0), (.02, 0, 0),
                                  (.02, .02, 0), (0, .02, 0), (0, 0, 0)]},
                        {"loop": .0025})


def test_a_closed_cord_keeps_its_closure_with_another_strand_at_the_support():
    paths = {
        "loop": [(0, 0, 0), (.0027, 0, 0), (.02, 0, 0),
                 (.02, .02, 0), (0, .02, 0), (0, 0, 0)],
        "other": [(0, 0, 0), (-.02, 0, 0)],
    }
    validate_cord_paths(paths, {"loop": .0025, "other": .0001})


def test_a_strand_at_a_closed_cord_support_has_no_inferred_continuation():
    paths = {
        "loop": [(0, 0, 0), (.02, 0, 0),
                 (.02, .02, 0), (0, .02, 0), (0, 0, 0)],
        "other": [(0, 0, 0), (-.001, 0, 0), (-.001, -.02, 0)],
    }
    with pytest.raises(ValueError, match=r"tubes intersect: loop/\d+, other/\d+"):
        validate_cord_paths(paths, {"loop": .0025, "other": .0001})


def test_three_endpoint_ports_do_not_define_a_continuous_bend():
    paths = {
        "lead": [(.02, .02, 0), (.0027, 0, 0), (0, 0, 0)],
        "bore": [(0, 0, 0), (0, -.02, 0)],
        "other": [(0, 0, 0), (0, 0, .02)],
    }
    with pytest.raises(ValueError, match="tubes intersect"):
        validate_cord_paths(paths, {key: .0025 for key in paths})


def test_joined_cords_still_reject_nonlocal_parallel_tubes():
    paths = {
        "first": [(0, 0, 0), (.02, 0, 0), (.02, .02, 0)],
        "second": [(.02, .02, 0), (0, .02, 0), (0, .003, 0), (.02, .003, 0)],
    }
    with pytest.raises(ValueError, match="tubes intersect"):
        validate_cord_paths(paths, {key: .0025 for key in paths})


def test_joined_cords_still_reject_an_interior_crossing_near_the_join():
    paths = {
        "first": [(-.002, 0, 0), (.002, 0, 0), (.002, .002, 0)],
        "second": [(.002, .002, 0), (0, .002, 0), (0, -.002, 0)],
    }
    with pytest.raises(ValueError, match="intersect"):
        validate_cord_paths(paths, {key: .0025 for key in paths})


def test_bend_neighborhood_crosses_multiple_unambiguous_endpoint_joins():
    paths = {
        "lead": [(.078446941, .04, -.04735), (-.02, 0, -.0247), (-.02, 0, -.022)],
        "short-bore-entry": [(-.02, 0, -.022), (-.02, 0, -.020)],
        "remaining-bore": [(-.02, 0, -.020), (-.02, 0, 0), (-.02, 0, .022)],
    }
    validate_cord_paths(paths, {key: .0025 for key in paths})


def test_nearby_unjoined_endpoints_do_not_get_the_bend_exclusion():
    paths = {
        "lead": [(.02, .02, 0), (.0027, 0, 0), (0, 0, 0)],
        "bore": [(0, -.000002, 0), (0, -.02, 0)],
    }
    with pytest.raises(ValueError, match="tubes intersect"):
        validate_cord_paths(paths, {key: .0025 for key in paths})
