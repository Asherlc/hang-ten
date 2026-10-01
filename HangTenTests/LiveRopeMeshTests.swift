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
        XCTAssertEqual(vertices.count, 48)
        for (i, vertex) in vertices.prefix(points.count * 8).enumerated() {
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
        XCTAssertEqual(indices.count, 84)
        for i in stride(from: 0, to: indices.count, by: 3) {
            let a=vertices[Int(indices[i])], b=vertices[Int(indices[i+1])], c=vertices[Int(indices[i+2])]
            XCTAssertGreaterThan(simd_dot(simd_cross(b.position-a.position,c.position-a.position),a.normal),0)
        }
    }
    func testCoincidentAndReversedSpansKeepFiniteNormals() throws {
        // Coincident endpoints force the zero-delta fallback. An x-axis span
        // forces rebuilding the initial normal parallel to the tangent.
        for points: [SIMD3<Float>] in [
            [.zero, .zero, SIMD3(0, 0.002, 0), .zero],
            [.zero, SIMD3(0.002, 0, 0), .zero]
        ] {
            let vertices = try RopeTubeGeometry.vertices(points: points, radialSegments: 8, radius: 0.0035)
            for vertex in vertices {
                XCTAssertTrue([vertex.position.x, vertex.position.y, vertex.position.z,
                               vertex.normal.x, vertex.normal.y, vertex.normal.z].allSatisfy(\.isFinite))
                XCTAssertEqual(simd_length(vertex.normal), 1, accuracy: 1e-6)
            }
        }
    }

    func testCapsUseDistinctVerticesAndFlatEndNormals() throws {
        let points: [SIMD3<Float>] = [.zero, SIMD3(0, 1, 0)]
        let vertices = try RopeTubeGeometry.vertices(points: points, radialSegments: 8, radius: 0.0035)
        for j in 0..<8 {
            XCTAssertEqual(vertices[16 + j].position, vertices[j].position)
            XCTAssertEqual(vertices[24 + j].position, vertices[8 + j].position)
            XCTAssertEqual(vertices[16 + j].normal, SIMD3<Float>(0, -1, 0))
            XCTAssertEqual(vertices[24 + j].normal, SIMD3<Float>(0, 1, 0))
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
