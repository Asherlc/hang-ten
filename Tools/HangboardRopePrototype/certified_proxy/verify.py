#!/usr/bin/env python3
"""Independent rational coverage/bound replay; no generator functions imported."""
import argparse,collections,hashlib,json
from fractions import Fraction as Q
from pathlib import Path


def area(a,b,c):return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])


def overlap(a,b):
    for tri in (a,b):
        for i in range(3):
            p,q=tri[i],tri[(i+1)%3];axis=(p[1]-q[1],q[0]-p[0])
            u=[x[0]*axis[0]+x[1]*axis[1] for x in a];v=[x[0]*axis[0]+x[1]*axis[1] for x in b]
            if max(min(u),min(v))>=min(max(u),max(v)):return False
    return True


def edges(triangles):
    counts=collections.Counter((t[i],t[(i+1)%3]) for t in triangles for i in range(3))
    return collections.Counter({edge:count-counts[edge[::-1]] for edge,count in counts.items() if count>counts[edge[::-1]]})


def replay(descriptor,proxy,records):
    mesh=descriptor['collision'];vertices=[tuple(Q.from_float(x) for x in p) for p in mesh['vertices']]
    faces={i:tuple(t) for i,t in enumerate(mesh['triangles'])};bounds={i:Q(0) for i in faces}
    last_round=0;used=set();limit=Q(1,100000)
    for record in records:
        if record['round']!=last_round:
            assert record['round']>last_round;last_round=record['round'];used=set()
        ids=record['oldFaces'];assert set(ids).isdisjoint(used);used.update(ids)
        center=record['center'];assert set(ids)=={i for i,t in faces.items() if center in t},'complete current one-ring'
        old=[faces[i] for i in ids];new=[tuple(t) for t in record['triangles']];loop=record['boundary']
        assert edges(old)==edges(new)==collections.Counter((loop[i],loop[(i+1)%len(loop)]) for i in range(len(loop))), 'exact 3D boundary identity'
        axis=record['axis'];assert axis in range(3);other=[i for i in range(3) if i!=axis]
        xy={i:tuple(vertices[i][k] for k in other) for t in old for i in t}
        polygon_area=sum(xy[loop[i]][0]*xy[loop[(i+1)%len(loop)]][1]-xy[loop[i]][1]*xy[loop[(i+1)%len(loop)]][0] for i in range(len(loop)))
        assert polygon_area!=0;sign=1 if polygon_area>0 else -1
        for i,start in enumerate(loop):
            end=loop[(i+1)%len(loop)]
            assert all(sign*area(xy[start],xy[end],p)>=0 for p in xy.values()),'all patch points inside convex polygon'
        for triangulation in (old,new):
            projected=[[xy[i] for i in t] for t in triangulation]
            signed=[area(*t) for t in projected]
            assert all(sign*x>0 for x in signed),'single-valued graph orientation'
            assert sum(signed)==polygon_area,'full area coverage'
            for i,t in enumerate(projected):
                for u in projected[i+1:]:assert not overlap(t,u),'disjoint interiors'
        # Exact equation from three plane points, independent determinant form.
        p,q,r=[vertices[i] for i in faces[record['planeFace']]]
        u=[q[i]-p[i] for i in range(3)];v=[r[i]-p[i] for i in range(3)]
        normal=[u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]]
        assert normal[axis]!=0
        residuals=[sum(normal[k]*(vertices[i][k]-p[k]) for k in range(3))/normal[axis] for i in xy]
        local=max(residuals)-min(residuals);inherited=max(bounds[i] for i in ids);bound=local+inherited
        assert local==Q(*record['localBound']) and inherited==Q(*record['inheritedBound'])
        assert bound==Q(*record['bound']) and bound<=limit
        assert len(record['newFaces'])==len(new) and all(i not in faces for i in record['newFaces'])
        for i in ids:del faces[i];del bounds[i]
        for i,t in zip(record['newFaces'],new):faces[i]=t;bounds[i]=bound
    assert proxy['vertices']==mesh['vertices'] and proxy['triangles']==[list(t) for _,t in sorted(faces.items())],'final mesh identity'
    assert not edges(list(faces.values())),'closed outward edge pairing'
    return {'records':len(records),'rounds':last_round,'maximumComposedBoundMeters':float(max(bounds.values())),
        'exactGraphCoveragePass':True,'closedOrientationPass':True,'limits':['Abstract continuous graph-map composition supplies two-sided metric proximity.','Does not prove global embedding, signedness, CAD accuracy, normals or dynamics.']}


def main():
    parser=argparse.ArgumentParser();parser.add_argument('descriptor',type=Path);parser.add_argument('proxy',type=Path);parser.add_argument('certificates',type=Path);parser.add_argument('output',type=Path);args=parser.parse_args()
    root=Path(__file__).resolve().parents[3];assert args.output.resolve().is_relative_to(root/'.context')
    result=replay(json.loads(args.descriptor.read_text()),json.loads(args.proxy.read_text()),json.loads(args.certificates.read_text()))
    result.update(owner=root.name,adopted=False,hashes={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [args.descriptor,args.proxy,args.certificates,Path(__file__)]})
    args.output.write_text(json.dumps(result,indent=2)+'\n');print(result)


if __name__=='__main__':main()
