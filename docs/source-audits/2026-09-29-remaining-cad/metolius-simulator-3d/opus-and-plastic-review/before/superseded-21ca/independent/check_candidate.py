"""Read-only metadata/USD inspection. Native physical checks are separate."""
from pathlib import Path
import argparse, hashlib, json, math, zipfile
import xml.etree.ElementTree as ET
from pxr import Usd, UsdGeom

p = argparse.ArgumentParser()
p.add_argument('source', type=Path)
p.add_argument('asset', type=Path)
p.add_argument('descriptor', type=Path)
p.add_argument('--report', type=Path, required=True)
a = p.parse_args()
here = Path(__file__).resolve().parent
baseline = json.loads((here/'baseline.json').read_text())
sha = lambda x: hashlib.sha256(x.read_bytes()).hexdigest()
failures = []
def check(label, condition):
    if not condition: failures.append(label)

with zipfile.ZipFile(a.source) as archive:
    xml = ET.fromstring(archive.read('Document.xml'))
    prop = next(x for x in xml.iter('Property') if x.get('name') == 'HangTenBoardManifest')
    raw = prop.find('String').get('value')
manifest = json.loads(raw)
check('exact raw embedded manifest preserved', raw == (here/'before-manifest-raw.txt').read_text())
check('30 contacts and facts preserved in order', manifest['contacts'] == baseline['contacts'])
descriptor = json.loads(a.descriptor.read_text())
check('descriptor model hash binds actual bytes', descriptor['modelSHA256'] == sha(a.asset))
check('descriptor contact IDs preserved', set(descriptor['contacts']) == {x['id'] for x in baseline['contacts']})
check('descriptor node IDs unique', len({x['nodeID'] for x in descriptor['nodes']}) == len(descriptor['nodes']))
bindings = {}
for node in descriptor['nodes']:
    if node['role'] == 'contact':
        for contact in [node['contactID']] + node.get('additionalContactIDs', []):
            bindings.setdefault(contact, []).append(node['nodeID'])
check('derived contact node inventory exact', all(sorted(bindings.get(k, [])) == v['nodeIDs'] for k, v in descriptor['contacts'].items()))
stage = Usd.Stage.Open(str(a.asset))
meshes, forbidden, rows = [], [], []
for prim in stage.Traverse():
    if prim.GetTypeName() in {'Material', 'Shader'}:
        forbidden.append(str(prim.GetPath()))
    if any(rel.GetName().startswith('material:binding') and rel.GetTargets() for rel in prim.GetRelationships()):
        forbidden.append(str(prim.GetPath()) + ':material binding')
    if not prim.IsA(UsdGeom.Mesh): continue
    mesh = UsdGeom.Mesh(prim)
    points = mesh.GetPointsAttr().Get()
    counts = mesh.GetFaceVertexCountsAttr().Get()
    indices = mesh.GetFaceVertexIndicesAttr().Get()
    normals = mesh.GetNormalsAttr().Get() or []
    check(str(prim.GetPath())+' finite points/normals', all(math.isfinite(float(c)) for v in list(points)+list(normals) for c in v))
    check(str(prim.GetPath())+' triangle topology', all(n == 3 for n in counts) and sum(counts) == len(indices))
    check(str(prim.GetPath())+' valid point indices', all(0 <= i < len(points) for i in indices))
    check(str(prim.GetPath())+' authored normals present', len(normals) == len(points) and str(mesh.GetNormalsInterpolation()) == 'vertex')
    check(str(prim.GetPath())+' unit normals', all(abs(sum(float(c)**2 for c in v)-1)<1e-4 for v in normals))
    check(str(prim.GetPath())+' nondegenerate triangles', all(len(set(indices[j:j+3])) == 3 for j in range(0,len(indices),3)))
    meshes.append(prim.GetName())
    rows.append({'name': prim.GetName(), 'triangles': len(counts), 'points': len(points), 'normalCount': len(normals)})
check('no materials/shaders/bindings', not forbidden)
check('USD meshes exactly descriptor node inventory', sorted(meshes) == sorted(n['nodeID'] for n in descriptor['nodes']))
tree = json.loads((here/'all-hangboards-baseline.json').read_text())['files']
current = {str(f): {'sha256': sha(f), 'bytes': f.stat().st_size} for f in Path('Hangboards').rglob('*') if f.is_file()}
outside = sorted(k for k in set(tree)|set(current) if not k.startswith('Hangboards/metolius-simulator-3d/') and tree.get(k) != current.get(k))
check('all unrelated package files unchanged', not outside)
report = {'status': 'pass' if not failures else 'fail', 'blockingFindings': failures,
          'candidateSHA256': {str(f): sha(f) for f in [a.source, a.asset, a.descriptor]},
          'rawManifestSHA256': hashlib.sha256(raw.encode()).hexdigest(), 'contactCount': len(manifest['contacts']),
          'meshes': rows, 'forbiddenMaterialPrimsOrBindings': forbidden,
          'unrelatedPackageChanges': outside, 'unrelatedFilesExpectedUnchanged': baseline['otherPackageFiles'],
          'limits': 'Metadata and USD topology inspection only; no factory shape judgment or native physical clearance certification.'}
a.report.write_text(json.dumps(report, indent=2)+'\n')
print(json.dumps(report, indent=2))
raise SystemExit(bool(failures))
