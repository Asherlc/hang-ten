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
            for (chain, fixed) in zip(solver.state.ropes, supports) {
                for (index, point) in fixed {
                    XCTAssertEqual(chain.positions[index], point)
                }
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
