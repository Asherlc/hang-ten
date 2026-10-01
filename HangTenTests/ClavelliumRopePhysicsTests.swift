import XCTest
import simd
#if canImport(HangTen)
@testable import HangTen
#endif

final class ClavelliumRopePhysicsTests: XCTestCase {
    private let upright = simd_quatd(angle:0,axis:SIMD3<Double>(0,0,1))

    private func solver(perturb: Bool = false) throws -> RopeDynamicsSolver {
        let input=try RopeThreadedSeedTests.clavellium(),collider=try RopeTriangleCollider(input:input)
        var state=try RopeThreadedSeed.make(input:input,profileID:"front",orientation:upright,collider:collider)
        if perturb {
            for i in state.ropes[0].positions.indices where state.ropes[0].supports[i] == nil {
                state.ropes[0].positions[i].y += 0.00005*sin(Double(i))
            }
            state.boardLinearVelocity = SIMD3(0, -0.01, 0)
        }
        return try RopeDynamicsSolver(input:input,state:state,collider:collider)
    }

    private func assertAccepted(_ frame:RopeFrameSnapshot,file:StaticString=#filePath,line:UInt=#line) {
        XCTAssertTrue(frame.settled,file:file,line:line)
        XCTAssertLessThanOrEqual(frame.metrics.totalLengthError,0.0005,file:file,line:line)
        XCTAssertLessThanOrEqual(frame.metrics.maximumLocalStrain,0.005,file:file,line:line)
        XCTAssertGreaterThanOrEqual(frame.metrics.minimumSegmentClearance,0.00345,file:file,line:line)
        XCTAssertTrue(frame.metrics.topologyValid,file:file,line:line)
        XCTAssertLessThan(frame.metrics.maximumSpeed,0.001,file:file,line:line)
        XCTAssertLessThan(frame.metrics.boardDisplacement,0.0001,file:file,line:line)
    }

    func testUprightAutomaticallyHugsUpperPassage() throws {
        var solver=try solver(perturb:true)
        let frame=try solver.settled(targetOrientation:upright,maxDuration:5)
        assertAccepted(frame)
        for (_,crossing) in solver.state.ropes[0].portalCrossings {
            let p=solver.state.boardPoint(crossing.point(in:frame.ropes[0].positions))
            XCTAssertEqual(p.y,0.0155-0.0036,accuracy:0.0002)
            XCTAssertGreaterThan(abs(p.y-0.0025),0.005)
        }
    }

    func testLoadSeatsCordStartingAwayFromBearingSurface() throws {
        let input=try RopeThreadedSeedTests.clavellium(),collider=try RopeTriangleCollider(input:input)
        let state=try RopeThreadedSeed.make(input:input,profileID:"front",orientation:upright,collider:collider,
                                           placement:.apertureCenter)
        let initial=try RopeSimulationMetrics.measure(state:state,input:input,collider:collider,boardHistory:[state.boardTranslation])
        XCTAssertTrue(initial.geometryAccepted)
        for crossing in state.ropes[0].portalCrossings.values {
            let local=state.boardPoint(crossing.point(in:state.ropes[0].positions))
            XCTAssertGreaterThan(0.0155-local.y-state.ropes[0].radius,0.003)
        }
        let rest=state.ropes[0].restLengths
        var solver=try RopeDynamicsSolver(input:input,state:state,collider:collider)
        let frame=try solver.settled(targetOrientation:upright,maxDuration:5)
        assertAccepted(frame)
        XCTAssertEqual(solver.state.ropes[0].restLengths,rest)
        for crossing in solver.state.ropes[0].portalCrossings.values {
            let local=solver.state.boardPoint(crossing.point(in:frame.ropes[0].positions))
            XCTAssertEqual(local.y,0.0155-0.0036,accuracy:0.0002)
        }
    }

    func testPhysicalRotationsAndRepeatedReversalsPreserveThreading() throws {
        var solver=try solver()
        for angle in [0.0,Double.pi/2,Double.pi,0,Double.pi/2,0] {
            let target=simd_quatd(angle:angle,axis:SIMD3<Double>(0,0,1))
            let frame=try solver.settled(targetOrientation:target,maxDuration:5)
            assertAccepted(frame)
            let up=target.inverse.act(SIMD3<Double>(0,1,0))
            for (id,crossing) in solver.state.ropes[0].portalCrossings {
                let portal=try XCTUnwrap(solver.input.portals.first{$0.id == id}, "Missing portal for crossing \(id)")
                let expected=try RopeRegionGeometry.bearing(portal,radius:solver.state.ropes[0].radius,up:up)
                let bearing=solver.state.boardPoint(crossing.point(in:frame.ropes[0].positions))
                XCTAssertEqual(simd_dot(bearing,up),simd_dot(expected,up),accuracy:0.0002)
                XCTAssertLessThanOrEqual(solver.collider.closestSurface(at:bearing).distance,solver.state.ropes[0].radius+0.0003)
            }
        }
    }

    func testXTiltAndReturnPreserveCordConstraints() throws {
        var solver = try solver()
        let supports = solver.state.ropes.map(\.supports)
        let rest = solver.state.ropes.map(\.restLengths)
        for angle in [Double.pi / 9, -Double.pi / 9, 0] {
            let target = simd_quatd(angle: angle, axis: SIMD3(1, 0, 0))
            let frame = try solver.settled(targetOrientation: target, maxDuration: 5)
            assertAccepted(frame)
            XCTAssertEqual(solver.state.ropes.map(\.restLengths), rest)
            for chain in solver.state.ropes {
                XCTAssertEqual(Set(chain.channelSpans.keys),Set(solver.input.channels.map(\.id)))
                for crossing in chain.portalCrossings.values {
                    let local=solver.state.boardPoint(crossing.point(in:chain.positions))
                    XCTAssertLessThanOrEqual(solver.collider.closestSurface(at:local).distance,chain.radius+RopeRegionGeometry.clearance+0.0002)
                }
            }
            for (chain, fixed) in zip(solver.state.ropes, supports) {
                for (index, point) in fixed {
                    XCTAssertEqual(chain.positions[index], point)
                }
            }
        }
    }

    private func settle(_ solver: inout RopeDynamicsSolver, target: simd_quatd, dt: Double = 1.0/240) throws -> RopeFrameSnapshot {
        for step in 1...Int((5/dt).rounded()) {
            let frame = try solver.step(dt: dt, targetOrientation: target)
            if frame.settled {
                print("cord settlement dt=\(dt), target=\(target.vector), duration=\(Double(step)*dt), translation=\(frame.boardTranslation)")
                return frame
            }
        }
        throw RopePhysicsError.invalid("Fixture did not settle within five simulated seconds")
    }

    func testXTiltSequenceIsDeterministicAndInvariantToHalfStep() throws {
        var first = try solver(), repeated = try solver(), half = try solver()
        for angle in [0.0, Double.pi/9, 0] {
            let target = simd_quatd(angle: angle, axis: SIMD3<Double>(1,0,0))
            let a = try settle(&first,target: target), b = try settle(&repeated,target: target)
            let c = try settle(&half,target: target,dt: 1.0/480)
            assertAccepted(a);assertAccepted(b);assertAccepted(c)
            XCTAssertEqual(a.boardTranslation,b.boardTranslation)
            XCTAssertEqual(a.ropes[0].positions,b.ropes[0].positions)
            XCTAssertLessThan(simd_distance(a.boardTranslation,c.boardTranslation),0.0002)
            for i in a.ropes[0].positions.indices {
                XCTAssertLessThan(simd_distance(a.ropes[0].positions[i],c.ropes[0].positions[i]),0.0002,"material particle \(i)")
            }
            for id in first.state.ropes[0].portalCrossings.keys {
                let aPoint = first.state.ropes[0].portalCrossings[id]!.point(in:first.state.ropes[0].positions)
                let cPoint = half.state.ropes[0].portalCrossings[id]!.point(in:half.state.ropes[0].positions)
                XCTAssertLessThan(simd_distance(aPoint,cPoint),0.0002,"bearing \(id)")
            }
        }
    }

    func testNeutralZBearingReportsSidewaysDifferenceAndPreservesHeight() throws {
        var first = try solver(), half = try solver()
        let target = simd_quatd(angle: .pi/2, axis: SIMD3<Double>(0,0,1))
        let a = try settle(&first,target:target), b = try settle(&half,target:target,dt:1.0/480)
        assertAccepted(a);assertAccepted(b)
        let difference = simd_distance(a.boardTranslation,b.boardTranslation)
        print("neutral Z90 strict-position delta=\(difference), gate=0.0002, passes=\(difference<0.0002)")
        XCTAssertEqual(first.state.worldPoint(first.input.bodyReferencePoint).y,
            half.state.worldPoint(half.input.bodyReferencePoint).y,accuracy:0.0002)
        for (i,point) in first.state.ropes[0].supports {
            XCTAssertEqual(first.state.ropes[0].positions[i],point)
            XCTAssertEqual(half.state.ropes[0].positions[i],point)
        }
        for id in first.state.ropes[0].portalCrossings.keys {
            let aPoint = first.state.ropes[0].portalCrossings[id]!.point(in:first.state.ropes[0].positions)
            let bPoint = half.state.ropes[0].portalCrossings[id]!.point(in:half.state.ropes[0].positions)
            XCTAssertEqual(aPoint.y,bPoint.y,accuracy:0.0002)
        }
    }

    func testTwoSyntheticThreadedLoopsKeepTheirOwnBudgetsThroughXTilt() throws {
        let source = try RopeThreadedSeedTests.clavellium()
        var portals: [RopePortalRegion] = [], channels: [RopeChannelRegion] = [], ropes: [RopePhysicsRope] = []
        for (index,x) in [-0.0045,0.0045].enumerated() {
            let prefix = "loop-\(index)-"
            for portal in source.portals {
                let boundary = portal.boundary.map { SIMD3<Double>(x+($0.x<0 ? -0.004:0.004),$0.y,$0.z) }
                portals.append(RopePortalRegion(id:prefix+portal.id,center:SIMD3(x,portal.center.y,portal.center.z),
                    normal:portal.normal,boundary:boundary,clearanceRadius:portal.clearanceRadius))
            }
            for channel in source.channels {
                channels.append(RopeChannelRegion(id:prefix+channel.id,portalIDs:channel.portalIDs.map {prefix+$0},
                    spine:channel.spine.map {SIMD3(x,$0.y,$0.z)},solid:channel.solid))
            }
            let rope = source.profiles[0].ropes[0]
            let nodes = rope.nodes.map { node in
                RopeGraphNode(id:prefix+node.id,kind:node.kind,
                    point:node.point.map {SIMD3(x,$0.y,$0.z)},portalID:node.portalID.map {prefix+$0})
            }
            let edges = rope.edges.map { edge in
                RopeGraphEdge(from:prefix+edge.from,to:prefix+edge.to,kind:edge.kind,
                    channelID:edge.channelID.map {prefix+$0},winding:edge.winding)
            }
            ropes.append(RopePhysicsRope(id:prefix+rope.id,baselineRadius:rope.baselineRadius,radius:rope.radius,
                restLength:rope.restLength,linearMass:rope.linearMass,nodes:nodes,edges:edges))
        }
        let profile = RopePhysicsProfile(id:"pair",presentationID:"pair",instanceID:nil,boardMass:1,ropes:ropes)
        let input = RopePhysicsInput(modelSHA256:source.modelSHA256,sourceSHA256:source.sourceSHA256,
            collision:source.collision,portals:portals,channels:channels,profiles:[profile])
        let collider = try RopeTriangleCollider(input:input)
        let seed = try RopeThreadedSeed.make(input:input,profileID:profile.id,orientation:upright,collider:collider)
        var solver = try RopeDynamicsSolver.prepareDisplay(input:input,state:seed,collider:collider).solver
        let budgets = solver.state.ropes.map(\.restLengths)
        for angle in [0.0,Double.pi/9,0] {
            let frame = try settle(&solver,target:simd_quatd(angle:angle,axis:SIMD3<Double>(1,0,0)))
            assertAccepted(frame)
            XCTAssertEqual(solver.state.ropes.map(\.restLengths),budgets)
            XCTAssertTrue(RopeCordContacts.between(solver.state.ropes[0],solver.state.ropes[1]).isEmpty)
            for chain in solver.state.ropes {
                XCTAssertEqual(chain.channelSpans.count,1)
                for (i,point) in chain.supports {XCTAssertEqual(chain.positions[i],point)}
            }
        }
    }

    func testDeterminismAndHalfTimeStep() throws {
        var first=try solver(),repeatRun=try solver(),halfStep=try solver()
        let a=try first.settled(targetOrientation:upright,maxDuration:5)
        let b=try repeatRun.settled(targetOrientation:upright,maxDuration:5)
        var c=try halfStep.step(dt:1.0/480,targetOrientation:upright)
        for _ in 0..<2399 where !c.settled { c=try halfStep.step(dt:1.0/480,targetOrientation:upright) }
        assertAccepted(a);assertAccepted(b);assertAccepted(c)
        XCTAssertEqual(a.boardTranslation,b.boardTranslation)
        XCTAssertEqual(a.ropes[0].positions,b.ropes[0].positions)
        XCTAssertLessThan(simd_distance(a.boardTranslation,c.boardTranslation),0.0002)
        for i in a.ropes[0].positions.indices {
            XCTAssertLessThan(simd_distance(a.ropes[0].positions[i],c.ropes[0].positions[i]),0.0002)
        }
    }
}
