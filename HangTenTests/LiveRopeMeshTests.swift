import XCTest
import simd
#if canImport(HangTen)
@testable import HangTen
#endif
#if canImport(UIKit)
import RealityKit
#endif

final class LiveRopeMeshTests: XCTestCase {
    func testTubeUsesConfirmedRadiusAndFiniteNormalsAroundCollinearSpans() throws {
        let points: [SIMD3<Float>] = [.zero, SIMD3(0,0.002,0), SIMD3(1e-10,0.004,0), SIMD3(0,0.006,1e-10)]
        let vertices = try RopeTubeGeometry.vertices(points: points, radialSegments: 8, radius: 0.0035)
        XCTAssertEqual(vertices.count, 32)
        for (i, vertex) in vertices.enumerated() {
            XCTAssertEqual(simd_distance(vertex.position, points[i/8]), 0.0035, accuracy: 1e-7)
            XCTAssertEqual(simd_length(vertex.normal), 1, accuracy: 1e-6)
            XCTAssertTrue([vertex.normal.x,vertex.normal.y,vertex.normal.z].allSatisfy(\.isFinite))
        }
    }
    func testTubeRejectsInvalidInputAndKeepsIndexWinding() throws {
        XCTAssertThrowsError(try RopeTubeGeometry.vertices(points: [.zero], radialSegments: 8, radius: 0.0035))
        XCTAssertThrowsError(try RopeTubeGeometry.vertices(points: [.zero, SIMD3(.nan,0,0)], radialSegments: 8, radius: 0.0035))
        XCTAssertThrowsError(try RopeTubeGeometry.vertices(points: [.zero, SIMD3(0,1,0)], radialSegments: 8, radius: -1))
        let vertices = try RopeTubeGeometry.vertices(points: [.zero, SIMD3(0,1,0)], radialSegments: 8, radius: 0.0035)
        let indices = RopeTubeGeometry.indices(pointCount: 2, radialSegments: 8)
        for i in stride(from: 0, to: 48, by: 3) {
            let a=vertices[Int(indices[i])], b=vertices[Int(indices[i+1])], c=vertices[Int(indices[i+2])]
            XCTAssertGreaterThan(simd_dot(simd_cross(b.position-a.position,c.position-a.position),a.normal),0)
        }
    }
    #if canImport(UIKit)
    @MainActor
    func testBuffersAndEntityRemainStableAcrossThousandUpdatesAndGrowSafely() throws {
        let mesh = try LiveRopeMesh(capacity: 4, radialSegments: 8, radius: 0.0035)
        let entity = mesh.entity, original = mesh.lowLevelMesh
        let points: [SIMD3<Double>] = [.zero, SIMD3(0,0.002,0), SIMD3(0,0.004,0)]
        for _ in 0..<1000 { try mesh.update(positions: points) }
        XCTAssertTrue(mesh.entity === entity); XCTAssertTrue(mesh.lowLevelMesh === original)
        XCTAssertNil(entity.components[CollisionComponent.self])
        XCTAssertNil(entity.components[InputTargetComponent.self])
        try mesh.update(positions: (0..<10).map { SIMD3(0,Double($0)*0.002,0) })
        XCTAssertTrue(mesh.entity === entity); XCTAssertGreaterThanOrEqual(mesh.capacity,10)
        XCTAssertFalse(mesh.lowLevelMesh === original)
    }
    #endif
}
