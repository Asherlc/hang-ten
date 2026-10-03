"""Exact Double supporting-plane grouping; never merges triangle witnesses."""
import hashlib,json,math


def generate(path):
    mesh=json.loads(path.read_text())['collision']
    ratios=[[float(x).as_integer_ratio() for x in p] for p in mesh['vertices']]
    denominator=max(d for p in ratios for _,d in p)
    vertices=[[n*(denominator//d) for n,d in p] for p in ratios]
    groups={};ids=[]
    for face in mesh['triangles']:
        a,b,c=[vertices[i] for i in face]
        u=[b[i]-a[i] for i in range(3)];v=[c[i]-a[i] for i in range(3)]
        n=[u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]]
        assert any(n)
        plane=[*n,sum(n[i]*a[i] for i in range(3))]
        divisor=math.gcd(*plane);plane=[x//divisor for x in plane]
        if next(x for x in plane[:3] if x)<0:plane=[-x for x in plane]
        key=tuple(plane)
        if key not in groups:groups[key]=len(groups)
        ids.append(groups[key])
    sha=hashlib.sha256(path.read_bytes()).hexdigest()
    source='// Exact grouping of descriptor SHA256 '+sha+'\nstruct RopePlaneAtlas {static let faceIDs:[Int]='+json.dumps(ids)+'}\n'
    return source,{'owner':'strong-owl-live-physics','descriptorSHA256':sha,'facePlaneIDs':ids,'planes':len(groups),'denominator':str(denominator)}
