import Foundation
import XCTest
import simd
#if canImport(HangTen)
@testable import HangTen
#endif

final class RopeThreadedSeedTests: XCTestCase {
    static func clavellium() throws -> RopePhysicsInput {
        let root = URL(fileURLWithPath: #filePath).deletingLastPathComponent().deletingLastPathComponent()
        let url = root.appendingPathComponent("Hangboards/clavellium-training-block/assets/primary.physics.json")
        let data = try Data(contentsOf: url)
        let raw = try JSONSerialization.jsonObject(with: data) as! [String: Any]
        return try RopePhysicsDescriptor.decode(data).validated(modelSHA256: raw["modelSHA256"] as! String)
    }

    func testCentralLoopIsContinuousCollisionFreeAndFullLength() throws {
        let input = try Self.clavellium(), collider = try RopeTriangleCollider(input: input)
        let state = try RopeThreadedSeed.make(input: input, profileID: "front",
                                             orientation: simd_quatd(angle: 0, axis: SIMD3(1,0,0)), collider: collider)
        XCTAssertEqual(state.ropes.count, 1)
        let rope = state.ropes[0]
        XCTAssertEqual(rope.radius, 0.0035, accuracy: 1e-12)
        XCTAssertEqual(rope.restLengths.reduce(0,+), 0.55, accuracy: 1e-9)
        XCTAssertLessThanOrEqual(rope.restLengths.max()!, 0.002000001)
        XCTAssertEqual(rope.positions.first, rope.positions.last)
        XCTAssertEqual(rope.supports.count, 2)
        XCTAssertEqual(rope.portals.count, 2)
        XCTAssertGreaterThan(rope.channelSegments.count, 40)
        for i in rope.restLengths.indices {
            let a = state.boardPoint(rope.positions[i]), b = state.boardPoint(rope.positions[i+1])
            XCTAssertNil(collider.segmentContact(from:a, to:b, radius:rope.radius + 0.00009))
            XCTAssertEqual(simd_distance(rope.positions[i],rope.positions[i+1]),rope.restLengths[i],accuracy:1e-9)
            if rope.channelSegments[i] != nil {
                XCTAssertLessThanOrEqual(abs(a.x), 0.012-rope.radius-RopeRegionGeometry.clearance+1e-9)
                XCTAssertLessThanOrEqual(abs(a.z), 0.045000001)
            }
        }
        // The input centers are facts about aperture regions, never pins.
        XCTAssertEqual(input.portals[0].center.y, 0.0025, accuracy:1e-12)
        for index in rope.portals.keys {
            XCTAssertGreaterThan(state.boardPoint(rope.positions[index]).y,0.009)
        }
    }

    func testImpossibleLengthAndErodedApertureFail() throws {
        let input = try Self.clavellium(), collider = try RopeTriangleCollider(input:input)
        let source = input.profiles[0].ropes[0]
        func altered(radius: Double, length: Double) -> RopePhysicsInput {
            let rope = RopePhysicsRope(id:source.id,baselineRadius:source.baselineRadius,radius:radius,
                restLength:length,linearMass:source.linearMass,nodes:source.nodes,edges:source.edges)
            let p=input.profiles[0]
            let profile=RopePhysicsProfile(id:p.id,presentationID:p.presentationID,instanceID:p.instanceID,boardMass:p.boardMass,ropes:[rope])
            return RopePhysicsInput(modelSHA256:input.modelSHA256,sourceSHA256:input.sourceSHA256,collision:input.collision,
                                    portals:input.portals,channels:input.channels,profiles:[profile])
        }
        let upright=simd_quatd(angle:0,axis:SIMD3(1,0,0))
        XCTAssertThrowsError(try RopeThreadedSeed.make(input:altered(radius:0.0035,length:0.02),profileID:"front",orientation:upright,collider:collider))
        XCTAssertThrowsError(try RopeThreadedSeed.make(input:altered(radius:0.02,length:0.55),profileID:"front",orientation:upright,collider:collider))
    }

    func testSharedHeightPreservesEachRopesDeclaredMaterialBudget() throws {
        let original=try Self.clavellium(),source=original.profiles[0].ropes[0]
        // A small difference in two synthetic loop lengths exercises shared
        // height initialization without pretending it is a product setup.
        let other=RopePhysicsRope(id:"second",baselineRadius:source.baselineRadius,radius:source.radius,
            restLength:source.restLength+0.00001,linearMass:source.linearMass,nodes:source.nodes,edges:source.edges)
        let profile=RopePhysicsProfile(id:"front",presentationID:"front",instanceID:nil,boardMass:1,ropes:[source,other])
        let input=RopePhysicsInput(modelSHA256:original.modelSHA256,sourceSHA256:original.sourceSHA256,
            collision:original.collision,portals:original.portals,channels:original.channels,profiles:[profile])
        let state=try RopeThreadedSeed.make(input:input,profileID:"front",
            orientation:simd_quatd(angle:0,axis:SIMD3<Double>(0,0,1)),collider:RopeTriangleCollider(input:input))
        for (rope,declared) in zip(state.ropes,profile.ropes) {
            XCTAssertEqual(rope.restLengths.reduce(0,+),declared.restLength,accuracy:1e-10)
            XCTAssertLessThanOrEqual(rope.restLengths.indices.map {abs(simd_distance(rope.positions[$0],rope.positions[$0+1])/rope.restLengths[$0]-1)}.max()!,0.005)
        }
    }
}
