"""Real FreeCAD geometry regressions for optional UV-node analytic normals."""
import inspect
import math
import sys
import unittest
from pathlib import Path

import FreeCAD as App
import Part

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import compile_board as compiler


class SurfaceProbe:
    def __init__(self, surface, calls):
        self.surface, self.calls = surface, calls

    def __getattr__(self, name):
        return getattr(self.surface, name)

    def parameter(self, point):
        self.calls.append(point)
        return self.surface.parameter(point)


class FaceProbe:
    def __init__(self, face, calls, uv_mode="normal", uv_reads=None):
        self.face = face
        self.Surface = SurfaceProbe(face.Surface, calls)
        self.uv_mode = uv_mode
        self.uv_reads = uv_reads

    def __getattr__(self, name):
        return getattr(self.face, name)

    def getUVNodes(self):
        if self.uv_reads is not None:
            self.uv_reads.append(self.face)
        if self.uv_mode == "unavailable":
            raise AttributeError("native UV API unavailable")
        if self.uv_mode == "unmatched":
            return []
        if self.uv_mode == "ambiguous":
            return list(self.face.getUVNodes()) * 2
        if self.uv_mode == "invalid-duplicate":
            nodes = list(self.face.getUVNodes())
            return nodes + [(u + 2 * math.pi, v) for u, v in nodes]
        return self.face.getUVNodes()

    def normalAt(self, u, v):
        if self.uv_mode == "invalid-duplicate" and u > 2 * math.pi:
            return App.Vector()
        return self.face.normalAt(u, v)


class ShapeProbe:
    def __init__(self, faces, calls, uv_mode="normal"):
        self.uv_reads = []
        self.Faces = [FaceProbe(face, calls, uv_mode, self.uv_reads) for face in faces]


def serialized(result):
    points, triangles, normals = result
    return (
        [(p.x, p.y, p.z) for p in points], triangles,
        [(n.x, n.y, n.z) for n in normals],
    )


class UVNodeNormalTests(unittest.TestCase):
    def setUp(self):
        self.shape = Part.makeCylinder(20, 10)
        self.points, self.triangles = self.shape.tessellate(0.28)

    def accelerated(self, shape, points, triangles):
        self.assertIn(
            "uv_nodes", inspect.signature(compiler._surface_normals).parameters,
            "Compiler lacks opt-in native UV-node normal evaluation",
        )
        return compiler._surface_normals(shape, points, triangles, 0.28, uv_nodes=True)

    def test_curved_normals_preserve_geometry_winding_and_avoid_inverse_queries(self):
        # Fails if optimization still projects every vertex/centroid, chooses a
        # neighboring face, flattens cylindrical normals, or changes geometry.
        for reverse in [False, True]:
            triangles = [tuple(reversed(t)) for t in self.triangles] if reverse else self.triangles
            old_calls, new_calls = [], []
            old = compiler._surface_normals(
                ShapeProbe(self.shape.Faces, old_calls), self.points, triangles, 0.28,
            )
            new = self.accelerated(ShapeProbe(self.shape.Faces, new_calls), self.points, triangles)
            self.assertEqual(serialized(old)[:2], serialized(new)[:2])
            self.assertLess(len(new_calls), len(old_calls) // 2)
            for point, actual, expected in zip(new[0], new[2], old[2]):
                self.assertLess((actual - expected).Length, 1e-6)
                self.assertAlmostEqual(actual.Length, 1, places=10)
                if abs(actual.z) < 0.5:
                    radial = App.Vector(point.x, point.y, 0)
                    radial.normalize()
                    if reverse:
                        radial = -radial
                    self.assertGreater(actual.dot(radial), 1 - 1e-9)

    def test_ambiguous_exact_face_ownership_uses_legacy_evaluator(self):
        face = self.shape.Faces[0]
        points, triangles = face.tessellate(0.28)
        faces = [face, face.copy()]
        old = compiler._surface_normals(ShapeProbe(faces, []), points, triangles, 0.28)
        calls = []
        new = self.accelerated(ShapeProbe(faces, calls), points, triangles)
        self.assertTrue(calls, "Ambiguous coincident faces must use the legacy evaluator")
        self.assertEqual(serialized(old), serialized(new))

    def test_missing_uv_api_and_unmatched_uv_nodes_preserve_exact_fallback(self):
        for mode in ["unavailable", "unmatched", "ambiguous"]:
            calls = []
            old = compiler._surface_normals(self.shape, self.points, self.triangles, 0.28)
            new = self.accelerated(ShapeProbe(self.shape.Faces, calls, mode), self.points, self.triangles)
            self.assertTrue(calls)
            self.assertEqual(serialized(old), serialized(new))

    def test_shared_face_vertices_do_not_claim_an_unrelated_triangle(self):
        face = Part.makePlane(10, 10)
        points, triangles = face.tessellate(0.28)
        # The opposite diagonal also connects three on-face UV nodes, but it
        # is not a cached facet and therefore has no proven tessellation owner.
        from itertools import combinations
        signatures = {tuple(sorted(t)) for t in triangles}
        triangle = next(t for t in combinations(range(len(points)), 3) if t not in signatures)
        calls = []
        old = compiler._surface_normals(face, points, [triangle], 0.28)
        new = self.accelerated(ShapeProbe(face.Faces, calls), points, [triangle])
        self.assertTrue(calls, "On-face vertices alone must not bypass legacy ownership")
        self.assertEqual(serialized(old), serialized(new))

    def test_internal_c0_knot_vertices_keep_the_legacy_derivative_side(self):
        # One native surface folds 90 degrees at its interior U knot. Its
        # position is unique there, but its analytic normal has two sides.
        surface = Part.BSplineSurface()
        surface.buildFromPolesMultsKnots(
            [[App.Vector(x, y, z) for z in [0, 10]] for x, y in [(0, 0), (10, 0), (10, 10)]],
            [2, 1, 2], [2, 2], [0, 1, 2], [0, 1], False, False, 1, 1,
        )
        # Degree elevation preserves the folded surface exactly and makes
        # OCCT's cached triangulation include interior points on the knot.
        surface.increaseDegree(8, 3)
        face = surface.toShape()
        self.assertAlmostEqual(face.normalAt(1 - 1e-7, 0.5).dot(face.normalAt(1 + 1e-7, 0.5)), 0)
        points, triangles = face.tessellate(0.28)
        cache = compiler._uv_node_normal_cache(face, points, triangles, 0.28)
        crease_triangles = [
            i for i, triangle in enumerate(triangles)
            if any(abs(points[j].x - 10) < 1e-9 and abs(points[j].y) < 1e-9 for j in triangle)
        ]
        self.assertTrue(crease_triangles)
        self.assertTrue(all(i not in cache for i in crease_triangles), "C0-knot normals are ambiguous")
        old = compiler._surface_normals(face, points, triangles, 0.28)
        new = self.accelerated(face, points, triangles)
        self.assertEqual(serialized(old), serialized(new))

    def test_invalid_coincident_uv_candidate_cannot_create_false_uniqueness(self):
        face = self.shape.Faces[0]  # Native periodic cylindrical surface.
        points, triangles = face.tessellate(0.28)
        ambiguous = ShapeProbe([face], [], "invalid-duplicate")
        self.assertFalse(
            compiler._uv_node_normal_cache(ambiguous, points, triangles, 0.28),
            "An invalid second UV witness must not turn a position into a unique match",
        )
        old = compiler._surface_normals(face, points, triangles, 0.28)
        self.assertEqual(serialized(old), serialized(self.accelerated(ambiguous, points, triangles)))

    def test_opt_in_requires_true_analytic_normal_policy_and_boolean_property(self):
        doc = App.newDocument("UVNormalsContract")
        try:
            for name in compiler.DOCUMENT_PROPERTIES:
                doc.addProperty("App::PropertyString", name)
                setattr(doc, name, "unused")
            doc.addProperty("App::PropertyBool", "HangTenUVNodeSurfaceNormals")
            compiler._document_properties(doc)  # Explicit false is still legacy.
            doc.HangTenUVNodeSurfaceNormals = True
            with self.assertRaises(compiler.BuildError):
                compiler._document_properties(doc)
            doc.addProperty("App::PropertyBool", "HangTenSurfaceNormals")
            with self.assertRaises(compiler.BuildError):
                compiler._document_properties(doc)
            doc.HangTenSurfaceNormals = True
            compiler._document_properties(doc)
            doc.removeProperty("HangTenUVNodeSurfaceNormals")
            doc.addProperty("App::PropertyString", "HangTenUVNodeSurfaceNormals")
            doc.HangTenUVNodeSurfaceNormals = "true"
            with self.assertRaises(compiler.BuildError):
                compiler._document_properties(doc)
        finally:
            App.closeDocument(doc.Name)

    def test_default_mesh_path_does_not_read_uv_api(self):
        # The legacy branch must neither require nor consult the new API.
        old = compiler._build_mesh(
            "curved", self.points, self.triangles, None, [-20, -20, 0, 20, 20, 10],
            surface=self.shape, deflection=0.28,
        )
        unavailable = ShapeProbe(self.shape.Faces, [], "unavailable")
        legacy = compiler._build_mesh(
            "curved", self.points, self.triangles, None, [-20, -20, 0, 20, 20, 10],
            surface=unavailable, deflection=0.28,
        )
        self.assertEqual(unavailable.uv_reads, [])
        self.assertEqual(old, legacy)

    def test_mesh_builder_dispatches_the_explicit_opt_in(self):
        calls = []
        self.assertIn("uv_node_surface_normals", inspect.signature(compiler._build_mesh).parameters)
        mesh = compiler._build_mesh(
            "curved", self.points, self.triangles, None, [-20, -20, 0, 20, 20, 10],
            surface=ShapeProbe(self.shape.Faces, calls), deflection=0.28,
            uv_node_surface_normals=True,
        )
        self.assertLess(len(calls), len(self.triangles))
        self.assertEqual(mesh.node_id, "curved")
        self.assertIsNone(mesh.material)
        self.assertEqual(len(mesh.triangles), len(self.triangles))


if __name__ == "__main__":
    result = unittest.TextTestRunner(verbosity=2).run(
        unittest.defaultTestLoader.loadTestsFromTestCase(UVNodeNormalTests)
    )
    raise SystemExit(not result.wasSuccessful())
