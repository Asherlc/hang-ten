from pathlib import Path

def separated_source(source):
    source=source.replace('    private let tree: [Node]', '    private let tree: [Node]\n    private let projections:[RopeTriangleProjection]')
    old='        self.mesh=mesh; self.tree=nodes'
    assert source.count(old)==1
    source=source.replace(old,old+"""
        self.projections=mesh.triangles.flatMap { face in
            let a=mesh.vertices[face.x],b=mesh.vertices[face.y],c=mesh.vertices[face.z]
            let n=simd_normalize(simd_cross(b-a,c-a))
            return [n,simd_normalize(simd_cross(b-a,n)),simd_normalize(simd_cross(c-b,n)),simd_normalize(simd_cross(a-c,n))].map {
                RopeTriangleProjection($0,a,b,c)
            }
        }""")
    old='        for index in faces.sorted() {\n'
    assert source.count(old)==1
    source=source.replace(old,old+"""            var separated=false
            for axis in 0..<4 where projections[index*4+axis].separates(start,end,radius) {separated=true;break}
            if separated {continue}
""")
    return source+'\n'+Path(__file__).with_name('Projection.swift').read_text()
