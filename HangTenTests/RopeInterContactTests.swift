import XCTest
import simd
#if canImport(HangTen)
@testable import HangTen
#endif

final class RopeInterContactTests:XCTestCase {
    func testNearGrazingCommonAndTangentialTranslationsHaveSweepCertificates() {
        let a = SIMD3<Double>(-0.05, -0.05, 0), b = SIMD3<Double>(0.05, 0.05, 0)
        let gap = simd_normalize(SIMD3<Double>(-1, 1, 0)) * 0.006951
        let first = Self.chain("first", [a, b])
        let second = Self.chain("second", [a + gap, b + gap])
        for tangent in [SIMD3<Double>.zero, SIMD3<Double>(0.03, 0.03, 0)] {
            var movedFirst = first, movedSecond = second
            movedFirst.positions = first.positions.map { $0 + SIMD3(0, 0, 0.05) }
            movedSecond.positions = second.positions.map { $0 + SIMD3(0, 0, 0.05) + tangent }
            XCTAssertTrue(RopeCordContacts.between(first, second).isEmpty)
            XCTAssertTrue(RopeCordContacts.between(movedFirst, movedSecond).isEmpty)
            XCTAssertTrue(RopeCordContacts.sweepValid(previousFirst: first, first: movedFirst,
                previousSecond: second, second: movedSecond))
        }
    }

    static func chain(_ id:String,_ points:[SIMD3<Double>],supports:[Int:SIMD3<Double>]=[:],radius:Double=0.0035)->RopeChainState {
        RopeChainState(id:id,radius:radius,linearMass:0.01,
            restLengths:zip(points,points.dropFirst()).map{simd_distance($0,$1)},
            positions:points,previousPositions:points,velocities:points.map{_ in .zero},
            supports:supports,attachments:[:],portals:[:],channelSegments:[:])
    }

    func testIndependentKnotRaysRotateWithoutFalseSweepExhaustion() {
        let support=SIMD3<Double>.zero,u=SIMD3<Double>(0.08,-0.12,0.01),v=SIMD3<Double>(0.12,-0.04,0.07)
        let q=simd_quatd(angle:0.03,axis:SIMD3<Double>(0,0,1))
        for firstStart in [true,false] {
            for secondStart in [true,false] {
                let first=Self.chain("first",firstStart ? [support,u]:[u,support],supports:[firstStart ? 0:1:support])
                let second=Self.chain("second",secondStart ? [support,v]:[v,support],supports:[secondStart ? 0:1:support])
                var nextFirst=first,nextSecond=second
                nextFirst.positions=first.positions.map{q.act($0)}
                nextSecond.positions=second.positions.map{q.act($0)}
                XCTAssertTrue(RopeCordContacts.between(first,second).isEmpty)
                XCTAssertTrue(RopeCordContacts.between(nextFirst,nextSecond).isEmpty)
                XCTAssertTrue(RopeCordContacts.sweepValid(previousFirst:first,first:nextFirst,previousSecond:second,second:nextSecond))
            }
        }
    }

    func testIndependentKnotRaysCannotSwapThroughEachOther() {
        let support=SIMD3<Double>.zero,u=SIMD3<Double>(0.08,-0.12,0.01),v=SIMD3<Double>(0.12,-0.04,0.07)
        let first=Self.chain("first",[support,u],supports:[0:support])
        let second=Self.chain("second",[v,support],supports:[1:support])
        var nextFirst=first,nextSecond=second
        nextFirst.positions=[support,v];nextSecond.positions=[u,support]
        XCTAssertTrue(RopeCordContacts.between(first,second).isEmpty)
        XCTAssertTrue(RopeCordContacts.between(nextFirst,nextSecond).isEmpty)
        XCTAssertFalse(RopeCordContacts.sweepValid(previousFirst:first,first:nextFirst,previousSecond:second,second:nextSecond))
    }

    func testIndependentCordSweepCertifiesEndReachedOnLastIteration() {
        let first=Self.chain("first",[SIMD3(-1,0,0),SIMD3(1,0,0)],radius:0.000275)
        let second=Self.chain("second",[SIMD3(-1,0.001,0),SIMD3(1,0.001,0)],radius:0.000275)
        var nextFirst=first,nextSecond=second
        nextFirst.positions=first.positions.map{$0+SIMD3<Double>(0,0.0511,0)}
        nextSecond.positions=second.positions.map{$0+SIMD3<Double>(0,0.0511,0)}
        XCTAssertTrue(RopeCordContacts.between(first,second).isEmpty)
        XCTAssertTrue(RopeCordContacts.between(nextFirst,nextSecond).isEmpty)
        XCTAssertTrue(RopeCordContacts.sweepValid(previousFirst:first,first:nextFirst,previousSecond:second,second:nextSecond))
    }

    // Nine simultaneous unilateral contact planes, with a known feasible
    // witness. Releasing the greatest tensile multiplier cycles between
    // working sets; a dual-feasible blocking step reaches the projection.
    func testSimultaneousContactProjectionDoesNotCycle() throws {
        let baseGradients:[[Double]]=[
            [0.23417230188986185, -0.9113047611325361, -0.27170006889895276, -0.20215350089740997],
            [-0.5562543431302027, 0.3978371423832167, 0.10620831731926461, -0.7218216588752053],
            [-0.8678931152763595, -0.21789206068464254, 0.015317569667208484, -0.44615015679251546],
            [-0.7516506573002164, 0.07513644379647937, -0.5653747796588384, -0.33125090599044554],
            [0.6457370379875231, -0.4478467395336529, 0.3021393606550425, 0.5396005767260988],
            [0.9302070160629295, 0.0036088191095783933, 0.20729741649775618, -0.30286905554264015],
            [-0.40871833984744654, 0.799841473952132, -0.16735691537929545, 0.4064413833422422],
            [0.38999698992902165, -0.6071516265439675, 0.38472513184901047, 0.5755482804726973],
            [0.07877792738909307, -0.7292609659152083, -0.5103842254439367, -0.44886570838803114]
        ]
        let baseOffsets: [Double]=[1.4336093285463596, -0.6957574859673138, 0.09456007144250711, 0.39264982796391645, 0.46158804190285174, 0.047236273064659474, -0.5456594263614699, 0.6071278304165902, 1.357207251942219]
        let prediction: [Double]=[0.34320245362986124, 1.2538185483667008, -3.1790366658133844, 0.6999056305262005]
        let witness: [Double]=[-0.216053172994632, 1.0440528763494636, 0.9530748947380221, -0.12075568490079783]
        func dot(_ a:[Double],_ b:[Double])->Double {zip(a,b).reduce(0){$0+$1.0*$1.1}}
        // Both equality signs exercise unrestricted multipliers; a duplicate
        // active contact exercises the same numerical rank regularization.
        for equalitySign in [0.0,1.0,-1.0] {
            var gradients=baseGradients,offsets=baseOffsets
            let mixed=equalitySign != 0
            let metric=mixed ? [0.25,2,1.5,0.6]:[1,1,1,1]
            if mixed {
                gradients.insert([0,equalitySign,0,0],at:0)
                offsets.insert(-equalitySign*witness[1],at:0)
                gradients.append(baseGradients[1]);offsets.append(baseOffsets[1])
            }
            func contact(_ id:Int)->Bool {!mixed || id != 0}
            for i in gradients.indices {
                let residual=offsets[i]+dot(gradients[i],witness)
                if contact(i) {XCTAssertGreaterThan(residual,0)}
                else {XCTAssertEqual(residual,0,accuracy:1e-12)}
            }
            var working=RopeContactWorkingSet(activeIDs:mixed ? [0]:[]),converged=false
            var point=prediction
            for _ in 0..<32 {
                let active=working.activeIDs
                var lambda:[Double]=[]
                if !active.isEmpty {
                    var matrix=try RopeBandedSystem(size:active.count,bandwidth:active.count-1)
                    for i in active.indices {for k in 0...i {
                        try matrix.addSymmetric(row:i,column:k,value:dot(gradients[active[i]],zip(gradients[active[k]],metric).map{$0*$1})+(i == k ? 1e-8:0))
                    }}
                    lambda=try matrix.solve(rhs:active.map{offsets[$0]+dot(gradients[$0],prediction)},
                        borderColumns:[],borderMatrix:[],borderRHS:[]).base
                }
                if working.releaseTensileContact(multipliers:lambda,contacts:active.map{contact($0)}) {continue}
                point=prediction
                for i in active.indices {for axis in point.indices {point[axis] -= metric[axis]*gradients[active[i]][axis]*lambda[i]}}
                let residual=gradients.indices.map{offsets[$0]+dot(gradients[$0],point)}
                if let violated=gradients.indices.filter({contact($0) && !active.contains($0) && residual[$0] < -1e-8}).min(by:{residual[$0]<residual[$1]}) {
                    working.insert(violated);continue
                }
                for i in gradients.indices {
                    if let selected=active.firstIndex(of:i) {
                        XCTAssertEqual(residual[i],1e-8*lambda[selected],accuracy:1e-12)
                        if contact(i) {XCTAssertLessThanOrEqual(lambda[selected],1e-12)}
                    } else {XCTAssertGreaterThanOrEqual(residual[i],-1e-8)}
                }
                converged=true;break
            }
            XCTAssertTrue(converged,"Contact projection cycled despite a feasible solution")
            let expected=mixed ? [0.02417904275,1.04405286523,0.55050822355,-0.32608552715]:[0.05525928,1.00895621,0.51794086,-0.37417238]
            for axis in point.indices {XCTAssertEqual(point[axis],expected[axis],accuracy:1e-6)}
        }
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
        let state=RopeSimulationState(profileID:"fixture",boardMass:1,boardTranslation:.zero,boardLinearVelocity:.zero,
            orientation:simd_quatd(angle:0,axis:SIMD3<Double>(0,0,1)),ropes:chains)
        return (input,state,try RopeTriangleCollider(input:input))
    }

    func testCoupledInitializationSeparatesDifferentRopesAndPreservesBothBudgets() throws {
        let (input,state,collider)=try Self.fixture(
            [SIMD3(-0.1,1,-0.01),SIMD3(0,1.005,0),SIMD3(0.1,1,-0.01)],
            [SIMD3(-0.1,1,0.014),SIMD3(0,1.005,0.004),SIMD3(0.1,1,0.014)])
        let before=try RopeSimulationMetrics.measure(state:state,input:input,collider:collider,boardHistory:[.zero])
        XCTAssertFalse(before.geometryAccepted)
        var solver=try RopeDynamicsSolver(input:input,state:state,collider:collider)
        let frame=try solver.projectInitialization()
        XCTAssertTrue(frame.metrics.geometryAccepted)
        XCTAssertTrue(RopeCordContacts.between(solver.state.ropes[0],solver.state.ropes[1]).isEmpty)
        for (original,result) in zip(state.ropes,solver.state.ropes) {
            XCTAssertEqual(original.restLengths,result.restLengths)
            for (index,point) in original.supports {XCTAssertEqual(result.positions[index],point)}
        }
        // Keep checking after the collars separate: a contact that is just
        // clear must still constrain the next gravity correction.
        for _ in 0..<5 {
            let next=try solver.step(dt:1.0/240,targetOrientation:state.orientation)
            XCTAssertTrue(next.metrics.geometryAccepted)
            XCTAssertTrue(RopeCordContacts.between(solver.state.ropes[0],solver.state.ropes[1]).isEmpty)
        }
    }

    func testDisplayPreparationPublishesProjectedStateAndPreservesMaterial() throws {
        let (input,state,collider)=try Self.fixture(
            [SIMD3(-0.1,1,-0.01),SIMD3(0,1.005,0),SIMD3(0.1,1,-0.01)],
            [SIMD3(-0.1,1,0.014),SIMD3(0,1.005,0.004),SIMD3(0.1,1,0.014)])
        XCTAssertFalse(try RopeSimulationMetrics.measure(state:state,input:input,collider:collider,
            boardHistory:[.zero]).geometryAccepted)
        let prepared=try RopeDynamicsSolver.prepareDisplay(input:input,state:state,collider:collider)
        XCTAssertTrue(prepared.frame.metrics.geometryAccepted)
        XCTAssertFalse(prepared.frame.settled)
        XCTAssertEqual(prepared.frame.boardTranslation.y,prepared.solver.state.boardTranslation.y)
        for ((original,result),frame) in zip(zip(state.ropes,prepared.solver.state.ropes),prepared.frame.ropes) {
            XCTAssertEqual(result.restLengths,original.restLengths)
            XCTAssertEqual(frame.id,result.id)
            XCTAssertEqual(frame.radius,result.radius)
            XCTAssertEqual(frame.positions,result.positions)
            for (index,point) in original.supports {XCTAssertEqual(result.positions[index],point)}
        }
        XCTAssertTrue(RopeCordContacts.between(prepared.solver.state.ropes[0],prepared.solver.state.ropes[1]).isEmpty)
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
