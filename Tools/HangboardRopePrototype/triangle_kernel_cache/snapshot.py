"""Isolated cache of immutable triangle edges and fixed parity-ray terms."""
from pathlib import Path

def collider_source(source):
    assert source.count('    private let tree: [Node]') == 1
    source = source.replace('    private let tree: [Node]', '    private let tree: [Node]\n    private let kernels:[TriangleKernel]')
    source = source.replace('        self.mesh=mesh; self.tree=nodes', '        self.mesh=mesh; self.tree=nodes\n        kernels=mesh.triangles.map {f in TriangleKernel(a:mesh.vertices[f.x],b:mesh.vertices[f.y],c:mesh.vertices[f.z])}')
    parity = '                if let t=Self.rayTriangle(point,direction,mesh.vertices[f.x],mesh.vertices[f.y],mesh.vertices[f.z]), t > 1e-10 { distances.append(t) }'
    assert source.count(parity) == 1
    source = source.replace('                let f=mesh.triangles[i]\n' + parity, '                if let t=kernels[i].parityRay(point),t>1e-10 {distances.append(t)}')
    fused_start = source.index('    func fusedContactEvaluation(')
    fused_end = source.index('    private struct FusedWitness', fused_start)
    fused = source[fused_start:fused_end]
    geometry = '            let face=mesh.triangles[index],a=mesh.vertices[face.x],b=mesh.vertices[face.y],c=mesh.vertices[face.z]\n            let normal=simd_normalize(simd_cross(b-a,c-a))'
    assert fused.count(geometry) == 1
    fused = fused.replace(geometry, '            let kernel=kernels[index],a=kernel.a,b=kernel.b,c=kernel.c,normal=kernel.normal')
    fused = fused.replace('Self.triangleClosest(start,a,b,c)', 'Self.cachedTriangleClosest(start,kernel)')
    fused = fused.replace('Self.triangleClosest(end,a,b,c)', 'Self.cachedTriangleClosest(end,kernel)')
    fused = fused.replace('Self.rayTriangle(start,end-start,a,b,c)', 'Self.cachedRayTriangle(start,end-start,kernel)')
    source = source[:fused_start]+fused+source[fused_end:]
    start = source.index('    private static func triangleClosest(')
    end = source.index('    static func segmentPair(', start)
    closest = source[start:end]
    closest = closest.replace('private static func triangleClosest(_ p: SIMD3<Double>, _ a: SIMD3<Double>, _ b: SIMD3<Double>, _ c: SIMD3<Double>)', 'private static func cachedTriangleClosest(_ p:SIMD3<Double>,_ g:TriangleKernel)')
    closest = closest.replace('        let ab=b-a, ac=c-a, ap=p-a,', '        let a=g.a,b=g.b,c=g.c,ab=g.ab,ac=g.ac,ap=p-a,')
    start = source.index('    private static func rayTriangle(')
    end = source.index('    private static func triangleClosest(', start)
    ray = source[start:end]
    ray = ray.replace('private static func rayTriangle(_ p: SIMD3<Double>, _ direction: SIMD3<Double>, _ a: SIMD3<Double>, _ b: SIMD3<Double>, _ c: SIMD3<Double>)', 'private static func cachedRayTriangle(_ p:SIMD3<Double>,_ direction:SIMD3<Double>,_ g:TriangleKernel)')
    ray = ray.replace('        let e1=b-a, e2=c-a,', '        let a=g.a,e1=g.ab,e2=g.ac,')
    kernel = (Path(__file__).parent / 'Kernel.swift').read_text()
    return source + '\nextension RopeTriangleCollider {\n' + kernel + closest + ray + '\n}\n'
