import unittest
from census import basis,project

class MaterialBasisFixtures(unittest.TestCase):
    def rope(self,values,weights=None):
        return {'positions':[[i*.01,0.,0.] for i in range(5)],
            'displacements':[[0.,v,0.] for v in values],
            'weights':weights or [0,1,1,1,0],'restLengths':[.01]*4,
            'supports':[0,4],'attachments':[]}

    def test_unrepresentable_motion_is_rejected(self):
        report,_=project(self.rope([0,0,.001,0,0]),{0,4})
        self.assertGreater(report['maxUndampedDisplacementError'],50e-6)

    def test_consistent_mass_matches_independent_closed_form(self):
        rope=self.rope([0,.0001,.0005,.0009,0],[0,.5,1/3,1/7,0])
        expected=(2*.5*.0001+3*.0005+7*.5*.0009)/(2*.25+3+7*.25)
        report,fitted=project(rope,{0,2,4})
        self.assertAlmostEqual(fitted[2][1],expected,places=15)
        self.assertLess(report['projectionStationarity'],1e-15)
        self.assertGreater(abs(rope['displacements'][2][1]-expected),50e-6)

    def test_exact_material_hat_and_fixed_height(self):
        rope=self.rope([0,.0005,.001,.0005,0]);rope['attachments']=[2];rope['weights'][2]=0
        report,fitted=project(rope,{0,2,4})
        self.assertLess(report['maxUndampedDisplacementError'],1e-15)
        self.assertEqual(fitted[2],[0,.001,0])

    def test_input_curvature_and_material_interpolation(self):
        rope=self.rope([0,0,0,0,0]);rope['positions'][2][1]=20e-6
        knots,P=basis(rope['positions'],rope['restLengths'],{0,4})
        self.assertIn(2,knots)
        self.assertTrue(all(abs(sum(row.values())-1)<1e-15 for row in P))
        rest=[.01,.02,.03,.04]
        straight=[[v,0,0] for v in [0,.01,.03,.06,.10]]
        knots,P=basis(straight,rest,{0,4})
        self.assertEqual(knots,[0,4]);self.assertAlmostEqual(P[2][1],.3)

if __name__=='__main__':unittest.main()
