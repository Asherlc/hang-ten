import simd

struct RopeTubeVertex {
    var position: SIMD3<Float>
    var normal: SIMD3<Float>
}

enum RopeTubeGeometry {
    static func vertices(points: [SIMD3<Float>], radialSegments: Int, radius: Float) throws -> [RopeTubeVertex] {
        guard points.count >= 2, points.count <= 50000, (3...32).contains(radialSegments),
              radius.isFinite, radius > 0,
              points.allSatisfy({ [$0.x,$0.y,$0.z].allSatisfy(\.isFinite) }) else {
            throw RopePhysicsError.invalid("Invalid dynamic tube geometry")
        }
        var vertices: [RopeTubeVertex] = []
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
                vertices.append(RopeTubeVertex(position:points[i]+radius*radial,normal:radial))
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

#if canImport(UIKit)
import RealityKit
import UIKit

/// One non-pickable entity and reusable vertex/index storage per physical cord.
@MainActor
final class LiveRopeMesh {
    let entity = ModelEntity()
    private(set) var lowLevelMesh: LowLevelMesh
    private(set) var capacity: Int
    let radialSegments: Int
    let radius: Float
    private var pointCount = 0

    init(capacity: Int, radialSegments: Int, radius: Float) throws {
        guard capacity>=2, capacity<=50000, (3...32).contains(radialSegments), radius.isFinite, radius>0 else {
            throw RopePhysicsError.invalid("Invalid dynamic tube capacity")
        }
        self.capacity=capacity; self.radialSegments=radialSegments; self.radius=radius
        lowLevelMesh = try Self.makeBuffer(capacity:capacity,radialSegments:radialSegments)
        var material = PhysicallyBasedMaterial()
        material.baseColor = .init(tint:UIColor(white:0.12,alpha:1))
        material.roughness = .init(floatLiteral:0.85)
        entity.model = ModelComponent(mesh:try MeshResource(from:lowLevelMesh),materials:[material])
        entity.name = "live-rope"
    }
    private static func makeBuffer(capacity: Int, radialSegments: Int) throws -> LowLevelMesh {
        try LowLevelMesh(descriptor:.init(vertexCapacity:capacity*radialSegments,
            vertexAttributes:[.init(semantic:.position,format:.float3,offset:0),
                              .init(semantic:.normal,format:.float3,offset:MemoryLayout<SIMD3<Float>>.stride)],
            vertexLayouts:[.init(bufferIndex:0,bufferStride:MemoryLayout<RopeTubeVertex>.stride)],
            indexCapacity:(capacity-1)*radialSegments*6+(radialSegments-2)*6,indexType:.uint32))
    }
    func update(snapshot: RopeFrameSnapshot) throws {
        guard snapshot.metrics.geometryAccepted,let rope=snapshot.ropes.first,
              abs(Float(rope.radius)-radius)<1e-8 else { throw RopePhysicsError.invalid("Rejected dynamic tube frame") }
        try update(positions:rope.positions)
    }
    func update(positions: [SIMD3<Double>]) throws {
        let points=positions.map { SIMD3<Float>(Float($0.x),Float($0.y),Float($0.z)) }
        let vertices=try RopeTubeGeometry.vertices(points:points,radialSegments:radialSegments,radius:radius)
        if points.count>capacity {
            let newCapacity=min(50000,max(points.count,capacity*2))
            let buffer=try Self.makeBuffer(capacity:newCapacity,radialSegments:radialSegments)
            let resource=try MeshResource(from:buffer)
            lowLevelMesh=buffer; capacity=newCapacity; pointCount=0
            entity.model?.mesh=resource
        }
        lowLevelMesh.withUnsafeMutableBytes(bufferIndex:0) { bytes in
            vertices.withUnsafeBytes { bytes.copyMemory(from:$0) }
        }
        let indicesCount=(points.count-1)*radialSegments*6+(radialSegments-2)*6
        if pointCount != points.count {
            let indices=RopeTubeGeometry.indices(pointCount:points.count,radialSegments:radialSegments)
            lowLevelMesh.withUnsafeMutableIndices { bytes in
                indices.withUnsafeBytes { bytes.copyMemory(from:$0) }
            }
            pointCount=points.count
        }
        let minimum=points.reduce(SIMD3<Float>(repeating:.infinity),simd_min)-SIMD3(repeating:radius)
        let maximum=points.reduce(SIMD3<Float>(repeating:-.infinity),simd_max)+SIMD3(repeating:radius)
        lowLevelMesh.parts.replaceAll([.init(indexCount:indicesCount,bounds:BoundingBox(min:minimum,max:maximum))])
    }
}
#endif
