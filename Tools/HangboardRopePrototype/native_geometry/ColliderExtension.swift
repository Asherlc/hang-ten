// Same-file diagnostic access; no production collider changes.
extension RopeTriangleCollider {
    func screenTree() throws -> ([BVHNode], [UInt32], [IntegerBounds]) {
        var faces: [UInt32] = []
        let nodes = try tree.map { n -> BVHNode in
            let offset = faces.count
            faces += n.faces.map(UInt32.init)
            return BVHNode(bounds: try IntegerBounds([n.minimum, n.maximum]),
                links: SIMD4(Int32(n.left), Int32(n.right), Int32(offset), Int32(n.faces.count)))
        }
        let triangles = try mesh.triangles.map { f in
            try IntegerBounds([mesh.vertices[f.x], mesh.vertices[f.y], mesh.vertices[f.z]])
        }
        return (nodes, faces, triangles)
    }
}
