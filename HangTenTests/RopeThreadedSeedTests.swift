import Foundation
import XCTest
import simd
#if canImport(HangTen)
@testable import HangTen
#endif

final class RopeThreadedSeedTests: XCTestCase {
    private func attachedBoard() -> RopePhysicsInput {
        let ropes = [-0.008, 0.008].enumerated().map { index, x in
            let nodes = [
                RopeGraphNode(id: "support-\(index)", kind: "support", point: SIMD3(x, 0.12, 0.008), portalID: nil),
                RopeGraphNode(id: "attachment-\(index)", kind: "attachment", point: SIMD3(x, 0.02, 0.008), portalID: nil)
            ]
            return RopePhysicsRope(id: "lead-\(index)", baselineRadius: 0.001, radius: 0.001,
                restLength: 0.1, linearMass: 0.01, nodes: nodes,
                edges: [RopeGraphEdge(from: nodes[0].id, to: nodes[1].id, kind: "free", channelID: nil, winding: nil)])
        }
        return RopePhysicsInput(modelSHA256: "fixture", sourceSHA256: "fixture",
            collision: RopeTriangleColliderTests.box(minimum: SIMD3(-0.01, -0.01, -0.01), maximum: SIMD3(0.01, 0.01, 0.01)),
            portals: [], channels: [], profiles: [RopePhysicsProfile(id: "front", presentationID: "front",
                instanceID: nil, boardMass: 1, ropes: ropes)])
    }

    func testXTiltKeepsBoardCordAttachmentsOnTheirAxis() throws {
        let input = attachedBoard(), collider = try RopeTriangleCollider(input: input)
        var state = try RopeThreadedSeed.make(input: input, profileID: "front",
            orientation: simd_quatd(angle: 0, axis: SIMD3(1, 0, 0)), collider: collider)
        let height = state.boardHeight
        for angle in [-Double.pi / 2, -0.4, 0, 0.4, Double.pi / 2] {
            state.orientation = simd_quatd(angle: angle, axis: SIMD3(1, 0, 0))
            for x in [-0.008, 0.008] {
                let attachment = SIMD3<Double>(x, 0.02, 0.008)
                XCTAssertLessThan(simd_distance(state.worldPoint(attachment), attachment + SIMD3(0, height, 0)), 1e-10)
                XCTAssertLessThan(simd_distance(state.boardPoint(state.worldPoint(attachment)), attachment), 1e-10)
            }
        }
        // At +90 degrees the board origin moves around the cord axis.
        let origin = state.worldPoint(.zero)
        XCTAssertEqual(origin.y - height, 0.028, accuracy: 1e-10)
        XCTAssertEqual(origin.z, -0.012, accuracy: 1e-10)
    }

    func testTiltedSeedKeepsFixedSupportsAndTautAttachmentLeads() throws {
        let input = attachedBoard(), collider = try RopeTriangleCollider(input: input)
        let state = try RopeThreadedSeed.make(input: input, profileID: "front",
            orientation: simd_quatd(angle: Double.pi / 3, axis: SIMD3(1, 0, 0)), collider: collider)
        XCTAssertEqual(state.boardHeight, 0, accuracy: 1e-8)
        for (index, x) in [-0.008, 0.008].enumerated() {
            let chain = state.ropes[index]
            XCTAssertLessThan(simd_distance(try XCTUnwrap(chain.positions.first), SIMD3(x, 0.12, 0.008)), 1e-10)
            XCTAssertLessThan(simd_distance(try XCTUnwrap(chain.positions.last), SIMD3(x, 0.02, 0.008)), 1e-8)
        }
        let metrics = try RopeSimulationMetrics.measure(state: state, input: input, collider: collider, boardHistory: [state.boardHeight])
        XCTAssertTrue(metrics.geometryAccepted)
    }

    func testThreadedBoardTiltsAroundItsPassageCenter() throws {
        let input = try Self.clavellium(), collider = try RopeTriangleCollider(input: input)
        var state = try RopeThreadedSeed.make(input: input, profileID: "front",
            orientation: simd_quatd(angle: 0, axis: SIMD3(1, 0, 0)), collider: collider)
        // The front/back mouths are at y=2.5 mm, z=+/-45 mm.
        // Their central cord axis crosses (0, 2.5 mm, 0).
        let center = SIMD3<Double>(0, 0.0025, 0)
        let fixed = center + SIMD3(0, state.boardHeight, 0)
        for angle in [-0.6, 0, 0.6] {
            state.orientation = simd_quatd(angle: angle, axis: SIMD3(1, 0, 0))
            XCTAssertLessThan(simd_distance(state.worldPoint(center), fixed), 1e-10)
        }
    }

    func testSeedRejectsChannelRegionThatDoesNotContainItsTraversal() throws {
        let source = try Self.clavellium()
        let channels = source.channels.map { region in
            RopeChannelRegion(id: region.id, portalIDs: region.portalIDs, spine: region.spine,
                solid: RopeCollisionMesh(vertices: region.solid.vertices.map { $0 + SIMD3<Double>(0.1, 0, 0) },
                                         triangles: region.solid.triangles))
        }
        let input = RopePhysicsInput(modelSHA256: source.modelSHA256, sourceSHA256: source.sourceSHA256,
            collision: source.collision, portals: source.portals, channels: channels, profiles: source.profiles)
        XCTAssertThrowsError(try RopeThreadedSeed.make(input: input, profileID: "front",
            orientation: simd_quatd(angle: 0, axis: SIMD3<Double>(0, 0, 1)),
            collider: RopeTriangleCollider(input: input))) { error in
            guard case RopePhysicsError.invalid(let message) = error else {
                return XCTFail("Expected channel containment rejection, got \(error)")
            }
            XCTAssertEqual(message, "Seed traversal leaves its native channel region")
        }
    }

    func testOppositeFaceUnsupportedLowerWindingIsRejected() throws {
        let source = try Self.clavellium(), original = source.profiles[0], rope = original.ropes[0]
        let edges = rope.edges.enumerated().map { index, edge in
            RopeGraphEdge(from: edge.from, to: edge.to, kind: edge.kind, channelID: edge.channelID,
                          winding: index == 0 ? "clockwise" : edge.winding)
        }
        let altered = RopePhysicsRope(id: rope.id, baselineRadius: rope.baselineRadius, radius: rope.radius,
            restLength: 0.8, linearMass: rope.linearMass, nodes: rope.nodes, edges: edges)
        let profile = RopePhysicsProfile(id: original.id, presentationID: original.presentationID,
            instanceID: original.instanceID, boardMass: original.boardMass, ropes: [altered])
        let input = RopePhysicsInput(modelSHA256: source.modelSHA256, sourceSHA256: source.sourceSHA256,
            collision: source.collision, portals: source.portals, channels: source.channels, profiles: [profile])
        XCTAssertLessThan(simd_dot(input.portals[0].normal, input.portals[1].normal), -0.99)
        XCTAssertThrowsError(try RopeThreadedSeed.make(input: input, profileID: profile.id,
            orientation: simd_quatd(angle: 0, axis: SIMD3<Double>(0, 0, 1)), collider: RopeTriangleCollider(input: input))) { error in
            guard case RopePhysicsError.invalid(let message) = error else {
                return XCTFail("Expected unsupported winding rejection, got \(error)")
            }
            XCTAssertEqual(message, "Opposite-face lower winding requires a reviewed exterior topology adapter")
        }
    }

    func testAnchorsBelowTheGridFailWithoutIntegerOverflow() throws {
        let source = try Self.clavellium()
        let original = source.profiles[0]
        for magnitude in [1e16, 1e6] {
            let ropes = original.ropes.map { rope in
                RopePhysicsRope(
                    id: rope.id, baselineRadius: rope.baselineRadius, radius: rope.radius,
                    restLength: rope.restLength, linearMass: rope.linearMass,
                    nodes: rope.nodes.map { node in
                        node.id == "end" ? RopeGraphNode(
                            id: node.id, kind: "attachment",
                            point: SIMD3<Double>(0, -magnitude, 0), portalID: nil) : node
                    }, edges: rope.edges)
            }
            let profile = RopePhysicsProfile(
                id: original.id, presentationID: original.presentationID,
                instanceID: original.instanceID, boardMass: original.boardMass, ropes: ropes)
            let input = RopePhysicsInput(
                modelSHA256: source.modelSHA256, sourceSHA256: source.sourceSHA256,
                collision: source.collision, portals: source.portals, channels: source.channels,
                profiles: [profile])
            let collider = try RopeTriangleCollider(input: input)
            XCTAssertThrowsError(try RopeThreadedSeed.make(
                input: input, profileID: profile.id,
                orientation: simd_quatd(angle: 0, axis: SIMD3<Double>(0, 0, 1)),
                collider: collider)) { error in
                guard case .invalid(let reason) = error as? RopePhysicsError else {
                    return XCTFail("Expected invalid physics, got \(error)")
                }
                XCTAssertEqual(reason, "Seed search exceeds bounded workspace")
            }
        }
    }

    func testUnboundedCollisionCoordinatesFailWithoutIntegerOverflow() throws {
        let source = try Self.clavellium()
        for magnitude in [1e16, 3e15, 1e6] {
            let mesh = RopeCollisionMesh(
                // Unreferenced finite vertices pass mesh validation but still
                // contribute to the exterior search's projected bounds.
                vertices: source.collision.vertices + [SIMD3<Double>(0, magnitude, 0)],
                triangles: source.collision.triangles)
            let input = RopePhysicsInput(
                modelSHA256: source.modelSHA256, sourceSHA256: source.sourceSHA256,
                collision: mesh, portals: source.portals, channels: source.channels,
                profiles: source.profiles)
            let collider = try RopeTriangleCollider(input: input)
            XCTAssertThrowsError(try RopeThreadedSeed.make(
                input: input, profileID: "front",
                orientation: simd_quatd(angle: 0, axis: SIMD3<Double>(0, 0, 1)),
                collider: collider)) { error in
                guard case .invalid(let reason) = error as? RopePhysicsError else {
                    return XCTFail("Expected invalid physics, got \(error)")
                }
                XCTAssertEqual(reason, "Seed search exceeds bounded workspace")
            }
        }
    }

    static func clavellium() throws -> RopePhysicsInput {
        let root = URL(fileURLWithPath: #filePath).deletingLastPathComponent().deletingLastPathComponent()
        let url = root.appendingPathComponent("Hangboards/clavellium-training-block/assets/primary.physics.json")
        let data = try Data(contentsOf: url)
        let raw = try XCTUnwrap(JSONSerialization.jsonObject(with: data) as? [String: Any])
        let hash = try XCTUnwrap(raw["modelSHA256"] as? String)
        return try RopePhysicsDescriptor.decode(data).validated(modelSHA256: hash)
    }

    func testCachedChannelMetricsMatchUncachedGeometry() throws {
        let input = try Self.clavellium()
        let collider = try RopeTriangleCollider(input: input)
        let cache = try RopeChannelColliderCache(channels: input.channels)
        let original = try RopeThreadedSeed.make(
            input: input, profileID: "front",
            orientation: simd_quatd(angle: 0, axis: SIMD3<Double>(0, 0, 1)), collider: collider)
        var outside = original
        let span = try XCTUnwrap(outside.ropes[0].channelSpans.values.first)
        let middle = Int((span.start.materialCoordinate + span.end.materialCoordinate) / 2)
        outside.ropes[0].positions[middle].x += 0.1
        for (index, state) in [original, outside].enumerated() {
            let uncached = try RopeSimulationMetrics.measure(
                state: state, input: input, collider: collider,
                boardHistory: [state.boardHeight], includeSelfContact: false)
            let cached = try RopeSimulationMetrics.measure(
                state: state, input: input, collider: collider,
                boardHistory: [state.boardHeight], includeSelfContact: false, channelCache: cache)
            XCTAssertEqual(
                [
                    cached.totalLengthError, cached.maximumLocalStrain, cached.minimumSegmentClearance,
                    cached.minimumClearanceMargin, cached.maximumSpeed, cached.boardDisplacement,
                ],
                [
                    uncached.totalLengthError, uncached.maximumLocalStrain, uncached.minimumSegmentClearance,
                    uncached.minimumClearanceMargin, uncached.maximumSpeed, uncached.boardDisplacement,
                ])
            XCTAssertEqual(cached.topologyValid, uncached.topologyValid)
            XCTAssertEqual(cached.topologyFailure, uncached.topologyFailure)
            XCTAssertEqual(cached.geometryAccepted, index == 0)
        }
    }

    func testChannelColliderCacheRejectsDifferentGeometry() throws {
        let source = try Self.clavellium()
        let collider = try RopeTriangleCollider(input: source)
        let cache = try RopeChannelColliderCache(channels: source.channels)
        let channels = source.channels.map { region in
            RopeChannelRegion(
                id: region.id, portalIDs: region.portalIDs, spine: region.spine,
                solid: RopeCollisionMesh(
                    vertices: region.solid.vertices.map { $0 + SIMD3<Double>(0.1, 0, 0) },
                    triangles: region.solid.triangles))
        }
        let input = RopePhysicsInput(
            modelSHA256: source.modelSHA256, sourceSHA256: source.sourceSHA256,
            collision: source.collision, portals: source.portals, channels: channels,
            profiles: source.profiles)
        let state = try RopeThreadedSeed.make(
            input: source, profileID: "front",
            orientation: simd_quatd(angle: 0, axis: SIMD3<Double>(0, 0, 1)), collider: collider)
        XCTAssertFalse(
            try RopeSimulationMetrics.measure(
                state: state, input: input, collider: collider,
                boardHistory: [state.boardHeight], includeSelfContact: false
            ).geometryAccepted)
        XCTAssertThrowsError(
            try RopeSimulationMetrics.measure(
                state: state, input: input, collider: collider,
                boardHistory: [state.boardHeight], includeSelfContact: false, channelCache: cache))
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
