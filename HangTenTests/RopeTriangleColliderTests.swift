import XCTest
import simd
#if canImport(HangTen)
@testable import HangTen
#endif

final class RopeTriangleColliderTests: XCTestCase {
    static func box(minimum: SIMD3<Double> = SIMD3(-1,-1,-1), maximum: SIMD3<Double> = SIMD3(1,1,1)) -> RopeCollisionMesh {
        let a = minimum, b = maximum
        let vertices = [SIMD3(a.x,a.y,a.z),SIMD3(b.x,a.y,a.z),SIMD3(b.x,b.y,a.z),SIMD3(a.x,b.y,a.z),
                        SIMD3(a.x,a.y,b.z),SIMD3(b.x,a.y,b.z),SIMD3(b.x,b.y,b.z),SIMD3(a.x,b.y,b.z)]
        return RopeCollisionMesh(vertices: vertices, triangles: [SIMD3(0,2,1),SIMD3(0,3,2),SIMD3(4,5,6),SIMD3(4,6,7),
            SIMD3(0,1,5),SIMD3(0,5,4),SIMD3(1,2,6),SIMD3(1,6,5),SIMD3(2,3,7),SIMD3(2,7,6),SIMD3(3,0,4),SIMD3(3,4,7)])
    }

    func testSignedDistanceAndClosestSurface() throws {
        let collider = try RopeTriangleCollider(mesh: Self.box())
        XCTAssertEqual(collider.signedDistance(at: SIMD3(0,0,0)), -1, accuracy: 1e-9)
        XCTAssertEqual(collider.signedDistance(at: SIMD3(0,2,0)), 1, accuracy: 1e-9)
        XCTAssertEqual(collider.signedDistance(at: SIMD3(1,0,0)), 0, accuracy: 1e-9)
        let hit = collider.closestSurface(at: SIMD3(0,2,0))
        XCTAssertEqual(hit.point, SIMD3(0,1,0))
        XCTAssertEqual(hit.normal, SIMD3(0,1,0))
    }

    func testSegmentCannotCrossWoodWithClearEndpoints() throws {
        let collider = try RopeTriangleCollider(mesh: Self.box())
        let start = SIMD3<Double>(-2,0,0), end = SIMD3<Double>(2,0,0)
        XCTAssertGreaterThan(collider.signedDistance(at:start), 0)
        XCTAssertGreaterThan(collider.signedDistance(at:end), 0)
        XCTAssertNotNil(collider.segmentContact(from:start, to:end, radius:0.006))
        XCTAssertNil(collider.segmentContact(from:SIMD3(-2,2,0), to:SIMD3(2,2,0), radius:0.006))
    }

    func testFiniteRadiusAndSweptMotion() throws {
        let collider = try RopeTriangleCollider(mesh: Self.box())
        XCTAssertNotNil(collider.segmentContact(from:SIMD3(-0.5,1.004,0), to:SIMD3(0.5,1.004,0), radius:0.006))
        XCTAssertNil(collider.segmentContact(from:SIMD3(-0.5,1.007,0), to:SIMD3(0.5,1.007,0), radius:0.006))
        XCTAssertNotNil(collider.sweptSegmentContact(previousStart:SIMD3(-0.5,2,0), previousEnd:SIMD3(0.5,2,0),
            start:SIMD3(-0.5,-2,0), end:SIMD3(0.5,-2,0), radius:0.006))
    }

    func testInsideEndpointsReportDeepestPenetrationInEitherDirection() throws {
        let collider=try RopeTriangleCollider(mesh:Self.box())
        let shallow=SIMD3<Double>(0.9,0,0),deep=SIMD3<Double>(0.2,0.4,0.3)
        for (start,end,fraction) in [(shallow,deep,1.0),(deep,shallow,0.0)] {
            let hit=try XCTUnwrap(collider.segmentContact(from:start,to:end,radius:0.006))
            XCTAssertEqual(hit.penetrationDepth,0.606,accuracy:1e-12)
            XCTAssertEqual(hit.centerlinePoint,deep)
            XCTAssertLessThan(simd_distance(hit.surfacePoint,SIMD3(0.2,1,0.3)),1e-12)
            XCTAssertLessThan(simd_distance(hit.normal,SIMD3(0,1,0)),1e-12)
            XCTAssertEqual(hit.fraction,fraction)
            let manifold=try XCTUnwrap(collider.segmentContacts(from:start,to:end,radius:0.006).first)
            XCTAssertEqual(manifold.penetrationDepth,hit.penetrationDepth)
            XCTAssertEqual(manifold.centerlinePoint,deep)
        }
    }

    func testVoidStaysOpenAndTransformDoesNotFillIt() throws {
        // Four independent closed rails make a square through-passage. A hull
        // would incorrectly fill it; exact triangles must keep it empty.
        let rails = [Self.box(minimum: SIMD3(-1,-1,-1), maximum:SIMD3(-0.2,1,1)),
                     Self.box(minimum: SIMD3(0.2,-1,-1), maximum:SIMD3(1,1,1)),
                     Self.box(minimum: SIMD3(-0.2,-1,-1), maximum:SIMD3(0.2,-0.2,1)),
                     Self.box(minimum: SIMD3(-0.2,0.2,-1), maximum:SIMD3(0.2,1,1))]
        var vertices: [SIMD3<Double>] = [], faces: [SIMD3<Int>] = []
        let rotation = simd_quatd(angle: .pi/3, axis: simd_normalize(SIMD3(1,2,3)))
        for rail in rails {
            let offset = vertices.count
            vertices += rail.vertices.map { rotation.act($0) }
            faces += rail.triangles.map { $0 &+ SIMD3(repeating:offset) }
        }
        let collider = try RopeTriangleCollider(mesh:RopeCollisionMesh(vertices:vertices,triangles:faces))
        XCTAssertEqual(collider.signedDistance(at: .zero), 0.2, accuracy: 1e-8)
        XCTAssertNil(collider.segmentContact(from:rotation.act(SIMD3(0,0,-2)), to:rotation.act(SIMD3(0,0,2)), radius:0.006))
        XCTAssertLessThan(collider.signedDistance(at:rotation.act(SIMD3(0.5,0,0))), 0)
    }

    func testMalformedCollisionMeshIsRejected() {
        let mesh = Self.box()
        XCTAssertThrowsError(try RopeTriangleCollider(mesh:RopeCollisionMesh(vertices:mesh.vertices,triangles:Array(mesh.triangles.dropLast()))))
        var faces = mesh.triangles
        faces[0] = SIMD3(0,0,1)
        XCTAssertThrowsError(try RopeTriangleCollider(mesh:RopeCollisionMesh(vertices:mesh.vertices,triangles:faces)))
        faces = mesh.triangles
        faces[0] = SIMD3(faces[0].x, faces[0].z, faces[0].y)
        XCTAssertThrowsError(try RopeTriangleCollider(mesh:RopeCollisionMesh(vertices:mesh.vertices,triangles:faces)))
    }

    func testCornerContactRetainsBothBearingNormals() throws {
        let walls=[Self.box(minimum:SIMD3(0.012,-0.02,-0.01),maximum:SIMD3(0.02,0.03,0.01)),
                   Self.box(minimum:SIMD3(-0.012,0.0155,-0.01),maximum:SIMD3(0.012,0.025,0.01))]
        var vertices:[SIMD3<Double>]=[],triangles:[SIMD3<Int>]=[]
        for wall in walls {
            let offset=vertices.count
            vertices += wall.vertices
            triangles += wall.triangles.map{$0 &+ SIMD3(repeating:offset)}
        }
        let collider=try RopeTriangleCollider(mesh:RopeCollisionMesh(vertices:vertices,triangles:triangles))
        let point=SIMD3<Double>(0.0084,0.0119,0)
        let hits=collider.segmentContacts(from:point,to:point,radius:0.00365)
        XCTAssertTrue(hits.contains{simd_dot($0.normal,SIMD3(-1,0,0))>0.999})
        XCTAssertTrue(hits.contains{simd_dot($0.normal,SIMD3(0,-1,0))>0.999})
        for hit in hits {XCTAssertEqual(hit.penetrationDepth,0.00005,accuracy:1e-9)}
        XCTAssertTrue(collider.segmentContacts(from:SIMD3(0,0,0),to:SIMD3(0,0,0),radius:0.00365).isEmpty)
    }
}
