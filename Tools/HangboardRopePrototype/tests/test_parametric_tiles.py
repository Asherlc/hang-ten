"""Catch incorrect trig rounding, seam spanning, and missing curvature/residuals."""
import math
from decimal import Decimal, getcontext
import unittest
import importlib.util
from pathlib import Path

_test_directory = Path(__file__).resolve().parent
_module_path = _test_directory/'parametric_tiles.py'
if not _module_path.exists():
    _module_path = _test_directory.parent/'parametric_tiles.py'
_spec = importlib.util.spec_from_file_location('tested_parametric_tiles', _module_path)
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)
trig_enclosure, unwrap_triangle, tile_envelope = _module.trig_enclosure, _module.unwrap_triangle, _module.tile_envelope


class ParametricTileTests(unittest.TestCase):
    def setUp(self):
        previous = getcontext().prec
        getcontext().prec = 80
        self.addCleanup(setattr, getcontext(), 'prec', previous)

    def test_trig_encloses_high_precision_reference(self):
        # Reference decimal digits are independent of Python's binary64 libm.
        for angle, cosine, reference in [
            (0.5, False, '0.47942553860420300027328793521557138808180336794060'),
            (0.5, True, '0.87758256189037271611628158260382965199164519710974'),
            (6.0, False, '-0.27941549819892587281155544661189475962799486431820'),
        ]:
            bound = trig_enclosure(angle, cosine)
            self.assertLessEqual(bound.lo, Decimal(reference) + Decimal('1e-50'))
            self.assertGreaterEqual(bound.hi, Decimal(reference) - Decimal('1e-50'))
            self.assertLess(bound.hi - bound.lo, Decimal('1e-55'))

    def test_periodic_seam_retains_a_small_tile(self):
        chart = unwrap_triangle([math.pi - .01, -math.pi + .01, math.pi - .02])
        self.assertLess(max(chart) - min(chart), .031)
        # Shifting a parameter must still be measured against its 3D vertex;
        # this chart does not presume binary64 2*pi equals the exact period.
        self.assertEqual(chart[0], math.pi - .01)

    def test_cylinder_curvature_encloses_chord_midpoint(self):
        patch = dict(kind='Cylinder', axis=2, center=[0., 0., 0.], radius=1.)
        bound = tile_envelope(patch, [(0., 0.), (math.pi/2, 0.), (0., 1.)],
                              [(1., 0., 0.), (0., 1., 0.), (1., 0., 1.)])
        # At edge midpoint the circle/chord gap is 1-sqrt(.5) = .292893...
        self.assertGreaterEqual(bound, Decimal('.2928932188134524'))
        self.assertLess(bound, Decimal('.412'))

    def test_plane_vertex_residual_cannot_be_discarded(self):
        patch = dict(kind='Plane', axis=2, center=[0., 0., 0.])
        bound = tile_envelope(patch, [(0., 0.), (1., 0.), (0., 1.)],
                              [(0., 0., .001), (1., 0., 0.), (0., 1., 0.)])
        self.assertGreaterEqual(bound, Decimal.from_float(.001))
        self.assertLess(bound, Decimal('.001000000001'))

    def test_torus_mixed_curvature_cannot_be_discarded(self):
        patch = dict(kind='Toroid', axis=2, center=[0., 0., 0.],
                     majorRadius=2., minorRadius=1.)
        uv = [(0., 0.), (math.pi/2, 0.), (0., math.pi/2)]
        bound = tile_envelope(patch, uv, [(3., 0., 0.), (0., 3., 0.), (2., 0., 1.)])
        # Three parameter diameters give (3+2+1)*(pi/2)^2/6 = pi^2/4.
        self.assertGreaterEqual(bound, Decimal('2.467401100272339'))
        self.assertLess(bound, Decimal('2.467401100273'))

    def test_nonfinite_or_unbounded_chart_is_rejected(self):
        for angle in [math.nan, math.inf, 11.]:
            with self.assertRaises(ValueError):
                trig_enclosure(angle)

    def test_caller_decimal_precision_cannot_change_certificate(self):
        getcontext().prec = 6
        angle = .123456789
        bound = trig_enclosure(angle)
        getcontext().prec = 80
        # Independent libm witness, with a conservative binary64 ulp allowance.
        reference = Decimal.from_float(math.sin(angle))
        self.assertLessEqual(bound.lo, reference + Decimal('1e-17'))
        self.assertGreaterEqual(bound.hi, reference - Decimal('1e-17'))
        self.assertLess(bound.hi - bound.lo, Decimal('1e-55'))


if __name__ == '__main__':
    unittest.main()
