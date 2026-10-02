"""Experimental immutable storage transform; query arithmetic/order stay unchanged."""

def packed_source(source):
    old = "    private let tree: [Node]"
    assert source.count(old) == 1
    source = source.replace(old, """    private struct PackedNode: Sendable {
        let minimum: SIMD3<Double>
        let maximum: SIMD3<Double>
        let left: Int
        let right: Int
        let faceStart: Int
        let faceCount: Int
    }
    private struct Triangle: Sendable {
        let a: SIMD3<Double>
        let b: SIMD3<Double>
        let c: SIMD3<Double>
        let normal: SIMD3<Double>
    }
    private let packedTree: [PackedNode]
    private let packedTriangles: [Triangle]
    private let packedFaces: [Int]""")
    old = "        self.mesh=mesh; self.tree=nodes"
    assert source.count(old) == 1
    source = source.replace(old, """        var faceIDs: [Int] = []
        let packed = nodes.map { node in
            let start = faceIDs.count
            faceIDs.append(contentsOf: node.faces)
            return PackedNode(minimum: node.minimum, maximum: node.maximum,
                left: node.left, right: node.right, faceStart: start, faceCount: node.faces.count)
        }
        self.mesh=mesh; self.packedTree=packed; self.packedFaces=faceIDs
        self.packedTriangles=mesh.triangles.map { face in
            let a=mesh.vertices[face.x],b=mesh.vertices[face.y],c=mesh.vertices[face.z]
            return Triangle(a:a,b:b,c:c,normal:simd_normalize(simd_cross(b-a,c-a)))
        }""")
    methods = ['closestSurface', 'segmentContacts', 'boundaryTubeContainsSegment', 'contains', 'closestSegment']
    for name in methods:
        import re
        match = re.search(r'func '+name+r'\([^\{]+\{\n', source)
        assert match, name
        begin = match.end()
        depth = 1
        end = begin
        while depth:
            depth += (source[end] == '{') - (source[end] == '}')
            end += 1
        body = source[begin:end-1]
        body = body.replace('for i in node.faces {', 'for offset in node.faceStart..<(node.faceStart+node.faceCount) {\n                let i=leafFaces[offset]')
        body = body.replace('for id in node.faces {', 'for offset in node.faceStart..<(node.faceStart+node.faceCount) {\n                let id=leafFaces[offset]')
        body = body.replace('faces += node.faces', 'faces.append(contentsOf:leafFaces[node.faceStart..<(node.faceStart+node.faceCount)])')
        body = body.replace('let f=mesh.triangles[i], a=mesh.vertices[f.x], b=mesh.vertices[f.y], c=mesh.vertices[f.z]', 'let triangle=triangles[i], a=triangle.a, b=triangle.b, c=triangle.c')
        body = body.replace('let face=mesh.triangles[index],a=mesh.vertices[face.x],b=mesh.vertices[face.y],c=mesh.vertices[face.z]', 'let triangle=triangles[index],a=triangle.a,b=triangle.b,c=triangle.c')
        body = body.replace('let face=mesh.triangles[id],a=mesh.vertices[face.x],b=mesh.vertices[face.y],c=mesh.vertices[face.z]', 'let triangle=triangles[id],a=triangle.a,b=triangle.b,c=triangle.c')
        body = body.replace('let f=mesh.triangles[i]\n                if let t=Self.rayTriangle(point,direction,mesh.vertices[f.x],mesh.vertices[f.y],mesh.vertices[f.z])', 'let triangle=triangles[i]\n                if let t=Self.rayTriangle(point,direction,triangle.a,triangle.b,triangle.c)')
        body = body.replace('simd_normalize(simd_cross(b-a,c-a))', 'triangle.normal')
        assert 'mesh.' not in body and 'node.faces' not in body, name
        wrapped = """        return packedTree.withUnsafeBufferPointer { tree in
            packedTriangles.withUnsafeBufferPointer { triangles in
                packedFaces.withUnsafeBufferPointer { leafFaces in
""" + body + """                }
            }
        }
    """
        source = source[:begin] + wrapped + source[end-1:]
    return source
