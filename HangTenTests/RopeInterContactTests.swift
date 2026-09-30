import XCTest
import simd
#if canImport(HangTen)
@testable import HangTen
#endif

final class RopeInterContactTests:XCTestCase {
    static func chain(_ id:String,_ points:[SIMD3<Double>],supports:[Int:SIMD3<Double>]=[:])->RopeChainState {
        RopeChainState(id:id,radius:0.0035,linearMass:0.01,
            restLengths:zip(points,points.dropFirst()).map{simd_distance($0,$1)},
            positions:points,previousPositions:points,velocities:points.map{_ in .zero},
            supports:supports,attachments:[:],portals:[:],channelSegments:[:])
    }

    func testSeparateRopesHaveFiniteRadiusContact() {
        let first=Self.chain("a",[SIMD3(-0.05,1,0),SIMD3(0.05,1,0)])
        let second=Self.chain("b",[SIMD3(-0.05,1,0.004),SIMD3(0.05,1,0.004)])
        let contacts=RopeCordContacts.between(first,second)
        XCTAssertEqual(contacts.count,1)
        XCTAssertEqual(contacts[0].distance,0.004,accuracy:1e-12)
        XCTAssertEqual(contacts[0].targetDistance,0.00705,accuracy:1e-12)
        let clear=Self.chain("clear",second.positions.map{$0+SIMD3(0,0,0.005)})
        XCTAssertTrue(RopeCordContacts.between(first,clear).isEmpty)
    }

    func testSharedSupportExcludesOnlyTheJoinedMaterialNeighborhood() {
        let support=SIMD3<Double>.zero
        let first=Self.chain("a",[support,SIMD3(0,0.012,0),SIMD3(0,0.03,0)],supports:[0:support])
        let second=Self.chain("b",[support,SIMD3(0.004,0.012,0),SIMD3(0.004,0.03,0)],supports:[0:support])
        let contacts=RopeCordContacts.between(first,second)
        XCTAssertTrue(contacts.contains{$0.firstSegment==1 && $0.secondSegment==1 && $0.targetDistance>0.007})
        let shortA=Self.chain("a",[support,SIMD3(-0.004,0.008,0)],supports:[0:support])
        let shortB=Self.chain("b",[support,SIMD3(0.004,0.008,0)],supports:[0:support])
        XCTAssertTrue(RopeCordContacts.between(shortA,shortB).isEmpty)
    }

    func testSharedSupportCannotHideCenterlineCrossingInsideKnotNeighborhood() {
        let support=SIMD3<Double>.zero
        let first=Self.chain("a",[support,SIMD3(-0.003,0.005,0),SIMD3(0.003,0.006,0)],supports:[0:support])
        let second=Self.chain("b",[support,SIMD3(0.003,0.005,0),SIMD3(-0.003,0.006,0)],supports:[0:support])
        XCTAssertTrue(RopeCordContacts.between(first,second).contains{$0.firstSegment==1 && $0.secondSegment==1})
    }

    func testDifferentRopesCannotPassThroughEachOtherBetweenClearFrames() {
        let a=Self.chain("a",[SIMD3(-0.05,1,-0.02),SIMD3(0.05,1,-0.02)])
        let b=Self.chain("b",[SIMD3(0,0.95,0.02),SIMD3(0,1.05,0.02)])
        let nextA=Self.chain("a",a.positions.map{SIMD3($0.x,$0.y,-$0.z)})
        let nextB=Self.chain("b",b.positions.map{SIMD3($0.x,$0.y,-$0.z)})
        XCTAssertTrue(RopeCordContacts.between(a,b).isEmpty)
        XCTAssertTrue(RopeCordContacts.between(nextA,nextB).isEmpty)
        XCTAssertFalse(RopeCordContacts.sweepValid(previousFirst:a,first:nextA,previousSecond:b,second:nextB))
        XCTAssertTrue(RopeCordContacts.sweepValid(previousFirst:a,first:a,previousSecond:b,second:b))
    }
    func testSharedSupportCannotHideCoincidentCenterlinesAwayFromEndpoint() {
        let support=SIMD3<Double>.zero
        let first=Self.chain("a",[support,SIMD3(0,0.01,0)],supports:[0:support])
        let second=Self.chain("b",[support,SIMD3(0,0.01,0)],supports:[0:support])
        XCTAssertFalse(RopeCordContacts.between(first,second).isEmpty)
        XCTAssertFalse(RopeCordContacts.sweepValid(previousFirst:first,first:first,previousSecond:second,second:second))
    }

    private static func fixture(_ a:[SIMD3<Double>],_ b:[SIMD3<Double>]) throws -> (RopePhysicsInput,RopeSimulationState,RopeTriangleCollider) {
        let chains=zip(["a","b"],[a,b]).map{id,points in chain(id,points,supports:[0:points[0],points.count-1:points.last!])}
        let sources=chains.map {rope in RopePhysicsRope(id:rope.id,baselineRadius:0.002,radius:rope.radius,
            restLength:rope.restLengths.reduce(0,+),linearMass:rope.linearMass,
            nodes:[RopeGraphNode(id:"start",kind:"support",point:rope.positions[0],portalID:nil),
                   RopeGraphNode(id:"end",kind:"support",point:rope.positions.last!,portalID:nil)],
            edges:[RopeGraphEdge(from:"start",to:"end",kind:"free",channelID:nil,winding:nil)])}
        let input=RopePhysicsInput(modelSHA256:String(repeating:"a",count:64),sourceSHA256:String(repeating:"b",count:64),
            collision:RopeTriangleColliderTests.box(minimum:SIMD3(repeating:-0.01),maximum:SIMD3(repeating:0.01)),
            portals:[],channels:[],profiles:[RopePhysicsProfile(id:"fixture",presentationID:"fixture",instanceID:nil,boardMass:1,ropes:sources)])
        let state=RopeSimulationState(profileID:"fixture",boardMass:1,boardHeight:0,boardVerticalVelocity:0,
            orientation:simd_quatd(angle:0,axis:SIMD3<Double>(0,0,1)),ropes:chains)
        return (input,state,try RopeTriangleCollider(input:input))
    }

    func testCoupledInitializationSeparatesDifferentRopesAndPreservesBothBudgets() throws {
        let (input,state,collider)=try Self.fixture(
            [SIMD3(-0.1,1,-0.01),SIMD3(0,1.005,0),SIMD3(0.1,1,-0.01)],
            [SIMD3(-0.1,1,0.014),SIMD3(0,1.005,0.004),SIMD3(0.1,1,0.014)])
        let before=try RopeSimulationMetrics.measure(state:state,input:input,collider:collider,boardHistory:[0])
        XCTAssertFalse(before.geometryAccepted)
        var solver=try RopeDynamicsSolver(input:input,state:state,collider:collider)
        let frame=try solver.projectInitialization()
        XCTAssertTrue(frame.metrics.geometryAccepted)
        XCTAssertTrue(RopeCordContacts.between(solver.state.ropes[0],solver.state.ropes[1]).isEmpty)
        for (original,result) in zip(state.ropes,solver.state.ropes) {
            XCTAssertEqual(original.restLengths,result.restLengths)
            for (index,point) in original.supports {XCTAssertEqual(result.positions[index],point)}
        }
    }

    func testInitializationRejectsCrossingBetweenRopesTransactionally() throws {
        let (input,state,collider)=try Self.fixture([SIMD3(-0.05,1,0),SIMD3(0.05,1,0)],
                                                  [SIMD3(0,0.95,0),SIMD3(0,1.05,0)])
        var solver=try RopeDynamicsSolver(input:input,state:state,collider:collider)
        XCTAssertThrowsError(try solver.projectInitialization()) {error in
            XCTAssertEqual(error as? RopePhysicsError,.invalid("Initial rope centerlines cross each other"))
        }
        for (original,result) in zip(state.ropes,solver.state.ropes) {XCTAssertEqual(original.positions,result.positions)}
    }

}
