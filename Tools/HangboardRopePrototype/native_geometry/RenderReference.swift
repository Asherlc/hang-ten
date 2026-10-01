import simd

struct OriginalRopeTubeVertex {
    var position: SIMD3<Float>
    var normal: SIMD3<Float>
}

enum OriginalRopeTubeGeometry {
    static func vertices(points: [SIMD3<Float>], radialSegments: Int, radius: Float) throws -> [OriginalRopeTubeVertex] {
        guard points.count >= 2, points.count <= 50000, (3...32).contains(radialSegments),
              radius.isFinite, radius > 0,
              points.allSatisfy({ [$0.x,$0.y,$0.z].allSatisfy(\.isFinite) }) else {
            throw RopePhysicsError.invalid("Invalid dynamic tube geometry")
        }
        var vertices: [OriginalRopeTubeVertex] = []
        vertices.reserveCapacity(points.count * radialSegments)
        var previousNormal = SIMD3<Float>(1,0,0)
        for i in points.indices {
            let before = points[max(0,i-1)], after = points[min(points.count-1,i+1)]
            let delta = after-before
            let tangent = simd_length_squared(delta)>1e-16 ? simd_normalize(delta):SIMD3<Float>(0,1,0)
            var normal = previousNormal - tangent*simd_dot(previousNormal,tangent)
            if simd_length_squared(normal)<1e-10 {
                let axis = abs(tangent.x)<0.8 ? SIMD3<Float>(1,0,0):SIMD3<Float>(0,0,1)
                normal = axis-tangent*simd_dot(axis,tangent)
            }
            normal = simd_normalize(normal); previousNormal = normal
            let binormal = simd_normalize(simd_cross(tangent,normal))
            for j in 0..<radialSegments {
                let angle = Float(j)*2*Float.pi/Float(radialSegments)
                let radial = normal*cos(angle)+binormal*sin(angle)
                vertices.append(OriginalRopeTubeVertex(position:points[i]+radius*radial,normal:radial))
            }
        }
        return vertices
    }
    static func indices(pointCount: Int, radialSegments: Int) -> [UInt32] {
        guard pointCount>=2, (3...32).contains(radialSegments) else { return [] }
        var indices: [UInt32] = []
        indices.reserveCapacity((pointCount-1)*radialSegments*6+(radialSegments-2)*6)
        for i in 0..<(pointCount-1) {
            for j in 0..<radialSegments {
                let a=UInt32(i*radialSegments+j), b=UInt32(i*radialSegments+(j+1)%radialSegments)
                let c=a+UInt32(radialSegments), d=b+UInt32(radialSegments)
                indices += [a,b,c,b,d,c]
            }
        }
        for j in 1..<(radialSegments-1) {
            indices += [0,UInt32(j+1),UInt32(j)]
            let last=UInt32((pointCount-1)*radialSegments)
            indices += [last,last+UInt32(j),last+UInt32(j+1)]
        }
        return indices
    }
}

