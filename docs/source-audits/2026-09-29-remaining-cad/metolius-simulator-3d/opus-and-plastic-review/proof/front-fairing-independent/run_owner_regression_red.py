import sys,functools,unittest
from pathlib import Path
sys.path.insert(0,str(Path.cwd()/"Tools/HangboardCAD"))
sys.path.insert(0,str(Path.cwd()/"Tools/HangboardCAD/tests"))
import compile_board as compiler
original=compiler._surface_normals
@functools.wraps(original)
def legacy_only(*args,**kwargs):
    kwargs["uv_nodes"]=False
    return original(*args,**kwargs)
compiler._surface_normals=legacy_only
from uv_node_normal_checks import UVNodeNormalTests
r=unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite([UVNodeNormalTests("test_exact_native_facet_owner_takes_precedence_over_nearby_centroid_plane")]))
raise SystemExit(not r.wasSuccessful())
