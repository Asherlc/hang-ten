import XCTest
import simd
#if canImport(HangTen)
@testable import HangTen
#endif

final class LiveRopeControllerTests: XCTestCase {
    func testBusyClockAccruesBoundedWorkAndDrainsOnce() {
        var clock=LiveRopeSchedule()
        XCTAssertEqual(clock.steps(elapsed:1.0/60),4)
        clock.accrue(elapsed:1.0/60);clock.accrue(elapsed:1.0/60)
        XCTAssertEqual(clock.takeSteps(),8)
        XCTAssertEqual(clock.takeSteps(),0)
        clock.accrue(elapsed:100);clock.accrue(elapsed:100)
        XCTAssertEqual(clock.takeSteps(),8)
        XCTAssertEqual(clock.takeSteps(),0)
        clock.accrue(elapsed:1.0/60);clock.pause();clock.resume()
        XCTAssertEqual(clock.takeSteps(),0)
    }
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
        let input = try RopeThreadedSeedTests.clavellium()
        let collider = try RopeTriangleCollider(input: input)
        let orientation = simd_quatd(angle: 0, axis: SIMD3<Double>(0, 0, 1))
        let state = try RopeThreadedSeed.make(input: input, profileID: "front", orientation: orientation, collider: collider)
        return try RopeDynamicsSolver(input: input, state: state, collider: collider)
    }
    @MainActor
    func testBusyElapsedDrainsWithoutAnotherTickAndKeepsExactWorkerState() async throws {
        let solver=try Self.solverFixture.get(),q=solver.state.orientation
        let expected=try await LiveRopeWorker(solver:solver).advanceExactly(steps:2,target:q)
        let ready=expectation(description:"Both elapsed steps delivered without another tick")
        var frames:[RopeFrameSnapshot]=[]
        let controller=LiveRopeController(solver:solver,sceneID:UUID(),delivery:{ _,_,frame in
            frames.append(frame)
            if frames.count==2 {ready.fulfill()}
        },failure:{error in XCTFail(String(describing:error));ready.fulfill()},continuousScheduling:true)
        controller.advance(elapsed:1.0/240)
        controller.advance(elapsed:1.0/240)
        await fulfillment(of:[ready],timeout:30)
        controller.stop()
        XCTAssertEqual(frames.count,2)
        guard frames.count==2 else{return}
        for i in frames.indices {
            XCTAssertEqual(frames[i].boardHeight,expected[i].boardHeight)
            XCTAssertEqual(frames[i].orientation.vector,expected[i].orientation.vector)
            XCTAssertEqual(frames[i].ropes[0].positions,expected[i].ropes[0].positions)
            XCTAssertTrue(frames[i].metrics.geometryAccepted)
        }
    }

    @MainActor
    func testStaleBusyResultDrainsCurrentGenerationWithoutSleepingIt() async throws {
        let solver=try Self.solverFixture.get(),old=solver.state.orientation
        let target=simd_quatd(angle:0.1,axis:SIMD3<Double>(0,0,1))
        let worker=LiveRopeWorker(solver:solver)
        _ = try await worker.advanceExactly(steps:1,target:old)
        let expected=try await worker.advanceExactly(steps:1,target:target)[0]
        let ready=expectation(description:"Current generation delivered after stale result")
        var delivered:RopeFrameSnapshot?
        let controller=LiveRopeController(solver:solver,sceneID:UUID(),delivery:{ _,generation,frame in
            XCTAssertEqual(generation,2);delivered=frame;ready.fulfill()
        },failure:{error in XCTFail(String(describing:error));ready.fulfill()},continuousScheduling:true)
        controller.advance(elapsed:1.0/240)
        controller.setTarget(orientation:target,generation:2)
        controller.advance(elapsed:1.0/240)
        await fulfillment(of:[ready],timeout:30)
        controller.stop()
        XCTAssertEqual(delivered?.boardHeight,expected.boardHeight)
        XCTAssertEqual(delivered?.orientation.vector,expected.orientation.vector)
        XCTAssertEqual(delivered?.ropes[0].positions,expected.ropes[0].positions)
    }
    func testWorkersKeepIndependentStateAndStopIsTerminal() async throws {
        let solver = try Self.solverFixture.get()
        let q = solver.state.orientation
        let first=LiveRopeWorker(solver:solver),second=LiveRopeWorker(solver:solver)
        let a=try await first.advanceExactly(steps:2,target:q)
        let b=try await second.advanceExactly(steps:1,target:q)
        XCTAssertEqual(a.count,2);XCTAssertEqual(b.count,1)
        XCTAssertEqual(a[0].boardHeight,b[0].boardHeight)
        XCTAssertEqual(a[0].ropes[0].positions,b[0].ropes[0].positions)
        await first.stop()
        let stopped=try await first.advanceExactly(steps:1,target:q)
        let continuing=try await second.advanceExactly(steps:1,target:q)
        XCTAssertTrue(stopped.isEmpty)
        XCTAssertEqual(continuing[0].boardHeight,a[1].boardHeight)
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
