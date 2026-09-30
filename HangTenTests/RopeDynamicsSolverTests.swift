import XCTest
import simd
#if canImport(HangTen)
@testable import HangTen
#endif

final class RopeDynamicsSolverTests: XCTestCase {
    func testRejectsNonfiniteStateAndInvalidTimeStep() throws {
        let input=try RopeThreadedSeedTests.clavellium(),collider=try RopeTriangleCollider(input:input)
        let q=simd_quatd(angle:0,axis:SIMD3<Double>(0,0,1))
        var state=try RopeThreadedSeed.make(input:input,profileID:"front",orientation:q,collider:collider)
        var solver=try RopeDynamicsSolver(input:input,state:state,collider:collider)
        for dt in [0, -1, Double.nan, Double.infinity, 1] {
            XCTAssertThrowsError(try solver.step(dt:dt,targetOrientation:q))
        }
        var previousState=state
        previousState.ropes[0].previousPositions[20].x = .nan
        XCTAssertThrowsError(try RopeDynamicsSolver(input:input,state:previousState,collider:collider))
        state.ropes[0].positions[20].x = .nan
        XCTAssertThrowsError(try RopeDynamicsSolver(input:input,state:state,collider:collider))
    }

    func testTautAttachmentTransfersBoardLoadWithoutStretch() throws {
        let q=simd_quatd(angle:0,axis:SIMD3<Double>(0,0,1))
        let support=SIMD3<Double>(0,0.114,0),attachment=SIMD3<Double>(0,0.014,0)
        let rope=RopePhysicsRope(id:"lead",baselineRadius:0.002,radius:0.0035,restLength:0.1,linearMass:0.01,
            nodes:[RopeGraphNode(id:"support",kind:"support",point:support,portalID:nil),
                   RopeGraphNode(id:"attachment",kind:"attachment",point:attachment,portalID:nil)],
            edges:[RopeGraphEdge(from:"support",to:"attachment",kind:"free",channelID:nil,winding:nil)])
        let mesh=RopeTriangleColliderTests.box(minimum:SIMD3(-0.01,-0.01,-0.01),maximum:SIMD3(0.01,0.01,0.01))
        let input=RopePhysicsInput(modelSHA256:String(repeating:"a",count:64),sourceSHA256:String(repeating:"b",count:64),
            collision:mesh,portals:[],channels:[],profiles:[RopePhysicsProfile(id:"front",presentationID:"front",instanceID:nil,boardMass:1,ropes:[rope])])
        let chain=RopeChainState(id:"lead",radius:0.0035,linearMass:0.01,restLengths:[0.1],positions:[support,attachment],
            previousPositions:[support,attachment],velocities:[.zero,.zero],supports:[0:support],attachments:[1:attachment],portals:[:],channelSegments:[:])
        let state=RopeSimulationState(profileID:"front",boardMass:1,boardHeight:0,boardVerticalVelocity:0,orientation:q,ropes:[chain])
        var solver=try RopeDynamicsSolver(input:input,state:state,collider:RopeTriangleCollider(input:input))
        for _ in 0..<240 {
            let frame=try solver.step(dt:1.0/240,targetOrientation:q)
            XCTAssertEqual(frame.boardHeight,0,accuracy:1e-8)
            XCTAssertLessThan(frame.metrics.maximumLocalStrain,1e-7)
            XCTAssertLessThan(frame.metrics.totalLengthError,1e-8)
        }
    }

    func testPortalCrossingsMoveThroughMaterialWithoutChangingRestLengths() throws {
        let input=try RopeThreadedSeedTests.clavellium(),collider=try RopeTriangleCollider(input:input)
        let q=simd_quatd(angle:0,axis:SIMD3<Double>(0,0,1))
        var state=try RopeThreadedSeed.make(input:input,profileID:"front",orientation:q,collider:collider)
        let before=state.ropes[0].portalCrossings,rest=state.ropes[0].restLengths
        for i in state.ropes[0].positions.indices where state.ropes[0].supports[i] == nil {
            state.ropes[0].positions[i].z += 0.002
        }
        try RopePassageTopology.refresh(state:&state,input:input)
        XCTAssertEqual(state.ropes[0].restLengths,rest)
        XCTAssertEqual(state.ropes[0].portalCrossings.count,2)
        for (id,crossing) in state.ropes[0].portalCrossings {
            XCTAssertGreaterThan(crossing.materialCoordinate,try XCTUnwrap(before[id]).materialCoordinate+0.5)
            let portal=try XCTUnwrap(input.portals.first{$0.id == id})
            let point=state.boardPoint(crossing.point(in:state.ropes[0].positions))
            XCTAssertEqual(simd_dot(point-portal.center,portal.normal),0,accuracy:1e-10)
        }
    }

    func testDynamicsFeedsRopeThroughPassageUnderAsymmetricMaterialAllocation() throws {
        let input=try RopeThreadedSeedTests.clavellium(),collider=try RopeTriangleCollider(input:input)
        let q=simd_quatd(angle:0,axis:SIMD3<Double>(0,0,1))
        var state=try RopeThreadedSeed.make(input:input,profileID:"front",orientation:q,collider:collider)
        let source=state.ropes[0]
        let front=try XCTUnwrap(source.portals.first{$0.value == "central-front"}?.key)
        let back=try XCTUnwrap(source.portals.first{$0.value == "central-back"}?.key)
        var arc=[0.0]
        for length in source.restLengths {arc.append(arc.last!+length)}
        let frontBegin=try XCTUnwrap(arc.firstIndex{$0>=0.02})
        let backEnd=try XCTUnwrap(arc.lastIndex{$0<=arc.last!-0.02})
        let frontLength=source.restLengths[frontBegin..<front].reduce(0,+)
        let backLength=source.restLengths[back..<backEnd].reduce(0,+)
        // Keep the certified geometric shape and total material length. Put
        // 1 mm less material in the front leg and 1 mm more in the back leg.
        // Leave the material of the common support knot unchanged. Sliding
        // must resolve the leg asymmetry; fixed portal particles cannot.
        let rest=source.restLengths.enumerated().map{i,length in
            length*(i>=frontBegin && i<front ? 1-0.001/frontLength:(i>=back && i<backEnd ? 1+0.001/backLength:1))
        }
        var chain=RopeChainState(id:source.id,radius:source.radius,linearMass:source.linearMass,restLengths:rest,
            positions:source.positions,previousPositions:source.previousPositions,velocities:source.velocities,
            supports:source.supports,attachments:source.attachments,portals:source.portals,channelSegments:source.channelSegments)
        chain.portalCrossings=source.portalCrossings;chain.channelSpans=source.channelSpans
        state.ropes[0]=chain
        let initial=try RopeSimulationMetrics.measure(state:state,input:input,collider:collider,boardHistory:[state.boardHeight])
        XCTAssertTrue(initial.geometryAccepted,String(describing:initial))
        var solver=try RopeDynamicsSolver(input:input,state:state,collider:collider)
        let frame=try solver.settled(targetOrientation:q,maxDuration:5)
        XCTAssertTrue(frame.settled);XCTAssertTrue(frame.metrics.geometryAccepted)
        XCTAssertEqual(solver.state.ropes[0].restLengths,rest)
        for (id,before) in source.portalCrossings {
            let after=try XCTUnwrap(solver.state.ropes[0].portalCrossings[id])
            XCTAssertGreaterThan(after.materialCoordinate,before.materialCoordinate+0.2)
        }
    }

    func testUnconvergedSolutionCannotBeReportedSettled() throws {
        let input=try RopeThreadedSeedTests.clavellium(),collider=try RopeTriangleCollider(input:input)
        let q=simd_quatd(angle:0,axis:SIMD3<Double>(0,0,1))
        let state=try RopeThreadedSeed.make(input:input,profileID:"front",orientation:q,collider:collider)
        var solver=try RopeDynamicsSolver(input:input,state:state,collider:collider)
        XCTAssertThrowsError(try solver.settled(targetOrientation:simd_quatd(angle:.pi,axis:SIMD3(0,0,1)),maxDuration:0.01)) {error in
            XCTAssertEqual(error as? RopePhysicsError,.invalid("Rope did not converge within 0.01 seconds"))
        }
    }

    func testSelfContactDetectsCrossingAwayFromSharedSupport() {
        let points:[SIMD3<Double>]=[SIMD3(0,1,0),SIMD3(-1,0,0),SIMD3(1,0,0),SIMD3(1,1,0),SIMD3(0,-1,0),SIMD3(0,1,0)]
        XCTAssertFalse(RopeSimulationMetrics.selfContactValid(positions:points,radius:0.006,supports:[0:points[0],5:points[5]]))
    }

    func testRotatingBoardSweepCoversArcMissedByEndpointChord() throws {
        let angle=Double.pi/2,start=SIMD3<Double>(1,0,0),end=start
        let first=start,last=simd_quatd(angle:angle,axis:SIMD3(0,0,1)).inverse.act(end)
        let deviation=RopeMotionSweep.rotationalDeviation(start:start,end:end,angle:angle)
        for i in 0...100 {
            let t=Double(i)/100
            let actual=simd_quatd(angle:angle*t,axis:SIMD3(0,0,1)).inverse.act(start+(end-start)*t)
            XCTAssertLessThanOrEqual(simd_distance(actual,first+(last-first)*t),deviation)
        }
        let center=SIMD3<Double>(sqrt(0.5),-sqrt(0.5),0)
        let collider=try RopeTriangleCollider(mesh:RopeTriangleColliderTests.box(minimum:center-SIMD3(repeating:0.02),maximum:center+SIMD3(repeating:0.02)))
        XCTAssertNil(collider.sweptSegmentContact(previousStart:first,previousEnd:first,start:last,end:last,radius:0.0035))
        XCTAssertNotNil(collider.sweptSegmentContact(previousStart:first,previousEnd:first,start:last,end:last,radius:0.0035+deviation))
        XCTAssertEqual(RopeMotionSweep.rotationalDeviation(start:start,end:end,angle:0),0)
    }

    func testSweptSelfContactRejectsCrossingWithClearEndpointShapes() {
        let before:[SIMD3<Double>]=[SIMD3(-1,0,-0.02),SIMD3(1,0,-0.02),SIMD3(3,0,-0.02),
                                   SIMD3(3,2,0.02),SIMD3(0,-1,0.02),SIMD3(0,1,0.02)]
        let after=before.map{SIMD3($0.x,$0.y,-$0.z)}
        let rest=zip(before,before.dropFirst()).map{simd_distance($0,$1)}
        XCTAssertTrue(RopeSimulationMetrics.selfContactValid(positions:before,radius:0.0035,supports:[:]))
        XCTAssertTrue(RopeSimulationMetrics.selfContactValid(positions:after,radius:0.0035,supports:[:]))
        XCTAssertFalse(RopeMotionSweep.selfContactValid(previous:before,positions:after,radius:0.0035,supports:[:],restLengths:rest))
        XCTAssertTrue(RopeMotionSweep.selfContactValid(previous:before,positions:before.map{$0+SIMD3(0,0,0.001)},radius:0.0035,supports:[:],restLengths:rest))
    }

    func testConnectedCapsulesAroundQuarterTurnAreNotSelfCrossing() {
        let r=0.0061
        var points:[SIMD3<Double>]=stride(from:-0.01,through:0,by:0.002).map{SIMD3($0,0,0)}
        points += (1...10).map {i in
            let angle=Double(i)*Double.pi/20
            return SIMD3(r*sin(angle),r*(1-cos(angle)),0)
        }
        points += stride(from:0.002,through:0.01,by:0.002).map{SIMD3(r,r+$0,0)}
        XCTAssertTrue(RopeSimulationMetrics.selfContactValid(positions:points,radius:0.006,supports:[:]))
    }
}
