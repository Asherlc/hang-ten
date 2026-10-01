import XCTest
import simd
#if canImport(HangTen)
@testable import HangTen
#endif

final class LiveRopeControllerTests: XCTestCase {
    func testFixedClockCapsCatchupAndDiscardsPausedTime() {
        var clock = LiveRopeSchedule()
        XCTAssertEqual(clock.steps(elapsed: 100), 8)
        XCTAssertEqual(clock.steps(elapsed: 1.0/480), 0)
        clock.pause()
        XCTAssertEqual(clock.steps(elapsed: 100), 0)
        clock.resume()
        XCTAssertEqual(clock.steps(elapsed: 1.0/480), 0)
        XCTAssertEqual(clock.steps(elapsed: 1.0/480), 1)
    }

    func testSleepingWakesOnlyForPhysicalTargetAndStopIsTerminal() {
        var clock = LiveRopeSchedule()
        let a = simd_quatd(angle: 0, axis: SIMD3(0,0,1))
        let b = simd_quatd(angle: .pi/2, axis: SIMD3(0,0,1))
        clock.setTarget(a)
        clock.accept(settled: true)
        clock.setTarget(a)
        XCTAssertEqual(clock.steps(elapsed: 1), 0)
        clock.setTarget(b)
        XCTAssertEqual(clock.steps(elapsed: 1), 8)
        clock.setTarget(a)
        XCTAssertEqual(clock.steps(elapsed: 1), 8)
        clock.stop()
        clock.resume(); clock.setTarget(b)
        XCTAssertEqual(clock.steps(elapsed: 1), 0)
    }

    func testIndependentInstanceClocksAndRejectedElapsed() {
        var first = LiveRopeSchedule(), second = LiveRopeSchedule()
        first.accept(settled: true)
        XCTAssertEqual(first.steps(elapsed: 1), 0)
        XCTAssertEqual(second.steps(elapsed: 1), 8)
        XCTAssertEqual(second.steps(elapsed: .nan), 0)
        XCTAssertEqual(second.steps(elapsed: -.infinity), 0)
        XCTAssertEqual(second.steps(elapsed: -1), 0)
    }

    func testDeliveryIdentityRejectsOldScenePoseAndPausedResults() {
        var identity = LiveRopeDeliveryIdentity(sceneID: UUID())
        let scene = identity.sceneID
        identity.select(generation: 1)
        let old = identity.token
        identity.select(generation: 2)
        identity.select(generation: 3)
        XCTAssertFalse(identity.accepts(sceneID: scene, token: old))
        XCTAssertFalse(identity.accepts(sceneID: UUID(), token: identity.token))
        XCTAssertTrue(identity.accepts(sceneID: scene, token: identity.token))
        let current = identity.token
        identity.pause()
        XCTAssertFalse(identity.accepts(sceneID: scene, token: current))
        identity.resume()
        XCTAssertFalse(identity.accepts(sceneID: scene, token: current))
        identity.stop(); identity.resume()
        XCTAssertFalse(identity.accepts(sceneID: scene, token: identity.token))
    }
    #if canImport(HangTen)
    private static let solverFixture: Result<RopeDynamicsSolver, Error> = Result {
        let original = try RopeThreadedSeedTests.clavellium()
        let offset = SIMD3<Double>(0.01,0,0.03)
        let profiles = original.profiles.map {p in
            RopePhysicsProfile(id:p.id,presentationID:p.presentationID,instanceID:p.instanceID,boardMass:p.boardMass,
                ropes:p.ropes.map {r in RopePhysicsRope(id:r.id,baselineRadius:r.baselineRadius,radius:r.radius,
                    restLength:r.restLength,linearMass:r.linearMass,nodes:r.nodes.map {n in
                        RopeGraphNode(id:n.id,kind:n.kind,point:n.point.map {n.kind == "support" ? $0+offset:$0},portalID:n.portalID)
                    },edges:r.edges)})
        }
        let input = RopePhysicsInput(modelSHA256:original.modelSHA256,sourceSHA256:original.sourceSHA256,
            collision:original.collision,portals:original.portals,channels:original.channels,profiles:profiles)
        let collider = try RopeTriangleCollider(input: input)
        let orientation = simd_quatd(angle: 0, axis: SIMD3<Double>(0, 0, 1))
        let state = try RopeThreadedSeed.make(input: input, profileID: "front", orientation: orientation, collider: collider)
        return try RopeDynamicsSolver(input: input, state: state, collider: collider)
    }
    func testWorkersKeepIndependentStateAndStopIsTerminal() async throws {
        let solver = try Self.solverFixture.get()
        let q = solver.state.orientation
        let first=LiveRopeWorker(solver:solver),second=LiveRopeWorker(solver:solver)
        let a=try await first.advanceExactly(steps:2,target:q)
        let b=try await second.advanceExactly(steps:1,target:q)
        XCTAssertEqual(a.count,2);XCTAssertEqual(b.count,1)
        XCTAssertEqual(a[0].boardTranslation,b[0].boardTranslation)
        XCTAssertEqual(a[0].ropes[0].positions,b[0].ropes[0].positions)
        await first.stop()
        let stopped=try await first.advanceExactly(steps:1,target:q)
        let continuing=try await second.advanceExactly(steps:1,target:q)
        XCTAssertTrue(stopped.isEmpty)
        XCTAssertEqual(continuing[0].boardTranslation,a[1].boardTranslation)
    }

    @MainActor
    func testReduceMotionDeliversOnlyAcceptedSettledFrame() async throws {
        let solver = try Self.solverFixture.get()
        let q = solver.state.orientation
        let ready=expectation(description:"Accepted settled frame")
        var count=0
        let controller=LiveRopeController(solver:solver,sceneID:UUID(),delivery:{ _,_,frame in
            count += 1
            XCTAssertTrue(frame.settled);XCTAssertTrue(frame.metrics.geometryAccepted)
            XCTAssertEqual(frame.boardTranslation.x,0.01,accuracy:0.0002)
            XCTAssertEqual(frame.boardTranslation.z,0.03,accuracy:0.0002)
            ready.fulfill()
        },failure:{ error in XCTFail(String(describing:error));ready.fulfill() })
        controller.settleImmediately=true
        controller.advance(elapsed:1.0/60)
        await fulfillment(of:[ready],timeout:30)
        XCTAssertEqual(count,1)
        controller.advance(elapsed:100)
        XCTAssertEqual(count,1)
        controller.stop()
    }

    @MainActor
    func testSupersededAndPausedWorkCannotDeliverStaleLateralFrames() async throws {
        let solver = try Self.solverFixture.get(), sceneID = UUID()
        let ready = expectation(description:"Only current generation delivered")
        var deliveries = 0
        let controller = LiveRopeController(solver:solver,sceneID:sceneID,delivery:{ scene,generation,frame in
            XCTAssertEqual(scene,sceneID);XCTAssertEqual(generation,2)
            XCTAssertEqual(frame.boardTranslation.x,0.01,accuracy:0.0002)
            XCTAssertGreaterThan(frame.boardTranslation.z,0.02)
            deliveries += 1
            if deliveries == 1 {ready.fulfill()}
        },failure:{error in XCTFail(String(describing:error));ready.fulfill()})
        controller.setTarget(orientation:simd_quatd(angle:0.2,axis:SIMD3<Double>(1,0,0)),generation:1)
        controller.advance(elapsed:1.0/60)
        controller.pause()
        controller.setTarget(orientation:simd_quatd(angle:-0.2,axis:SIMD3<Double>(1,0,0)),generation:2)
        controller.resume()
        let pump = Task { @MainActor in
            while !Task.isCancelled && deliveries == 0 {
                controller.advance(elapsed:1.0/60)
                try await Task.sleep(for:.milliseconds(10))
            }
        }
        await fulfillment(of:[ready],timeout:30)
        pump.cancel();controller.stop()
        let acceptedCount = deliveries
        controller.advance(elapsed:100)
        try await Task.sleep(for:.milliseconds(100))
        XCTAssertEqual(deliveries,acceptedCount)
    }

    @MainActor
    func testControllerDeallocatesWhileWorkerHasPendingWork() async throws {
        let solver = try Self.solverFixture.get()
        let callback=expectation(description:"No delivery after release")
        callback.isInverted=true
        var controller:LiveRopeController?=LiveRopeController(solver:solver,sceneID:UUID(),
            delivery:{ _,_,_ in callback.fulfill() },failure:{ _ in callback.fulfill() })
        weak var weakController=controller
        controller?.advance(elapsed:1.0/30)
        controller=nil
        XCTAssertNil(weakController)
        await fulfillment(of:[callback],timeout:0.2)
    }
    #endif

}
