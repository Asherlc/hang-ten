"""Catch dropped clearance, pins, midpoint-only admission, and changed coupling."""
import math
import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from channel_contact import UChannel, build_rows


def channel():
    return UChannel((0, 0, 0), .006, .0037, .033, .0000164)


def test_leg_row_preserves_radius_and_clearance():
    # Dropping the 0.1 mm clearance would change this residual by 0.1 mm.
    residual, gradient = channel().row((.0061, 0, .01), .0035, .0001)
    assert residual == pytest.approx(-.0000164, abs=1e-15)
    assert gradient == pytest.approx((-1, 0, 0))


def test_u_bend_core_is_lower_semicircle_not_unused_upper_torus():
    assert channel().core((0, 0, -.0062)) == pytest.approx((0, 0, -.006))
    assert channel().core((.0059, 0, .002)) == pytest.approx((.006, 0, .002))


def test_leg_tangent_is_free_to_slide():
    _, gradient = channel().row((.0061, 0, .01), .0035, .0001)
    assert gradient[2] == 0


def test_centerline_inactive_has_no_arbitrary_normal_or_pin():
    assert channel().row((.006, 0, .01), .0035, .0001) is None


def test_bend_tightening_covers_offset_endpoints_and_strain_limit():
    # The circular interpolation bound is <= D^2/(8R), with endpoint
    # offsets included in the projected chord; direct hand bounds below.
    value = channel().tightening(.00077, .0035, .0001)
    assert .000019 < value < .000021
    assert channel().tightening(.002, .0035, .0001) is None


def test_opening_and_distant_pipe_are_fallback():
    assert channel().eligible((.006, 0, .032))
    assert not channel().eligible((.006, 0, .033))
    assert not channel().eligible((0, 0, .01))


def frozen_fixture():
    def row(contact, particles, gradients, residual=0, second=-1):
        return dict(rope=0, secondRope=second, particles=particles,
                    gradients=gradients, boardGradient=0,
                    residual=residual, contact=contact)
    return dict(orientation=[0, 0, 0, 1], boardHeight=0,
                positions=[[[.0061, 0, .01], [.0061, 0, .0105]]],
                radii=[.0035], restLengths=[[.0005]],
                rows=[row(False, [0, 1], [[0, 0, -1], [0, 0, 1]]),
                      row(True, [0], [[-1, 0, 0]], -.000001),
                      row(True, [0], [[-.99, .1, 0]], -.000001),
                      row(True, [1], [[-1, 0, 0]], -.000001),
                      row(True, [0, 1], [[-.5, 0, 0], [-.5, 0, 0]], -.000001),
                      row(True, [0, 1, 0, 1], [[0, 0, 0]]*4, -.000001)])


def test_rows_collapse_and_other_coupling_rows_remain_exact():
    source = frozen_fixture()
    result, report = build_rows(source, [channel()])
    assert len(result['rows']) == 4
    assert result['rows'][0] == source['rows'][0]
    assert source['rows'][-1] in result['rows']
    assert report['removedRows'] == 4
    assert report['tubeRows'] == 2
    assert result['positions'] == source['positions']
    assert result['restLengths'] == source['restLengths']


def test_link_with_one_endpoint_outside_keeps_whole_link_rows():
    source = frozen_fixture()
    source['positions'][0][1] = [.0061, 0, .034]
    result, _ = build_rows(source, [channel()])
    assert source['rows'][4] in result['rows']


def test_invalid_inputs_fail_instead_of_generating_certificates():
    with pytest.raises(ValueError):
        channel().row((math.nan, 0, 0), .0035, .0001)
    source = frozen_fixture()
    source['orientation'] = [0, 1, 0, 0]
    with pytest.raises(ValueError):
        build_rows(source, [channel()])
