import Foundation
import simd

#if DEBUG
enum LiveRopeReviewTrace {
    static func log(_ message: @autoclosure () -> String) {
        guard ProcessInfo.processInfo.environment["HANGTEN_REVIEW_LIVE_ROPE_DIAGNOSTICS"] == "1" else { return }
        FileHandle.standardError.write(Data("[LiveRopeReview] \(message())\n".utf8))
    }
}
#endif

/// Display time never becomes unbounded simulation debt.
struct LiveRopeSchedule {
    private var remainder = 0.0
    private var paused = false
    private var stopped = false
    private var sleeping = false
    private var target = simd_quatd(angle: 0, axis: SIMD3(0,0,1))
    mutating func steps(elapsed: Double) -> Int {
        guard !paused, !stopped, !sleeping, elapsed.isFinite, elapsed > 0 else { return 0 }
        remainder += min(elapsed, 1.0/30)
        let count = min(8, Int((remainder + 1e-12) * 240))
        remainder = max(0, remainder - Double(count)/240)
        return count
    }
    mutating func setTarget(_ value: simd_quatd) {
        if abs(simd_dot(target.vector, value.vector)) < 1-1e-12 { sleeping = false }
        target = value
    }
    mutating func accept(settled: Bool) { sleeping = settled; if settled { remainder = 0 } }
    mutating func pause() { paused = true; remainder = 0 }
    mutating func resume() { paused = false; remainder = 0 }
    mutating func stop() { stopped = true; remainder = 0 }
}

struct LiveRopeDeliveryIdentity {
    let sceneID: UUID
    private(set) var token: UInt64 = 0
    private var generation: UInt64 = 0
    private var paused = false
    private var stopped = false

    init(sceneID: UUID) {
        self.sceneID = sceneID
    }

    mutating func select(generation: UInt64) {
        if generation != self.generation { token &+= 1; self.generation = generation }
    }
    mutating func invalidate() { token &+= 1 }
    mutating func pause() { paused = true; token &+= 1 }
    mutating func resume() { paused = false; token &+= 1 }
    mutating func stop() { stopped = true; token &+= 1 }
    func accepts(sceneID: UUID, token: UInt64) -> Bool {
        !paused && !stopped && self.sceneID == sceneID && self.token == token
    }
}

/// The actor owns all mutable physical state. No frame runs on the main actor.
actor LiveRopeWorker {
    private var solver: RopeDynamicsSolver?
    init(solver: RopeDynamicsSolver) { self.solver = solver }
    func advance(steps: Int, target: simd_quatd, settleImmediately: Bool) throws -> RopeFrameSnapshot? {
        try Task.checkCancellation()
        guard var candidate = solver else { return nil }
        #if DEBUG
        LiveRopeReviewTrace.log("worker begin steps=\(steps) immediate=\(settleImmediately) target=\(target.vector)")
        #endif
        var frame: RopeFrameSnapshot?
        if settleImmediately {
            frame = try candidate.settled(targetOrientation: target, maxDuration: 5)
        } else {
            guard (0...8).contains(steps) else { throw RopePhysicsError.invalid("Unbounded display step") }
            for _ in 0..<steps {
                try Task.checkCancellation()
                frame = try candidate.step(dt: 1.0/240, targetOrientation: target)
                if frame?.settled == true { break }
            }
        }
        try Task.checkCancellation()
        solver = candidate
        #if DEBUG
        LiveRopeReviewTrace.log("worker end orientation=\(String(describing: frame?.orientation.vector)) settled=\(String(describing: frame?.settled))")
        #endif
        return frame
    }
    /// Clock-independent numerical interface for lifecycle and instance tests.
    func advanceExactly(steps: Int, target: simd_quatd) throws -> [RopeFrameSnapshot] {
        guard (0...1200).contains(steps), var candidate = solver else { return [] }
        var frames: [RopeFrameSnapshot] = []
        for _ in 0..<steps { frames.append(try candidate.step(dt: 1.0/240, targetOrientation: target)) }
        solver = candidate
        return frames
    }
    func stop() { solver = nil }
}

@MainActor
final class LiveRopeController {
    typealias Delivery = @MainActor (UUID, UInt64, RopeFrameSnapshot) -> Void
    private let worker: LiveRopeWorker
    private var schedule = LiveRopeSchedule()
    private var identity: LiveRopeDeliveryIdentity
    private var target: simd_quatd
    private var generation: UInt64 = 0
    private var busy = false
    private var task: Task<Void, Never>?
    private var stopped = false
    #if DEBUG
    private var reviewAdvanceCount = 0
    #endif
    var settleImmediately = false {
        didSet { if oldValue != settleImmediately { identity.invalidate() } }
    }
    private let delivery: Delivery
    private let failure: @MainActor (Error) -> Void

    init(solver: RopeDynamicsSolver, sceneID: UUID, delivery: @escaping Delivery,
         failure: @escaping @MainActor (Error) -> Void) {
        worker = LiveRopeWorker(solver: solver)
        identity = LiveRopeDeliveryIdentity(sceneID: sceneID)
        target = solver.state.orientation
        schedule.setTarget(target)
        self.delivery = delivery; self.failure = failure
    }
    func setTarget(orientation: simd_quatd, generation: UInt64) {
        guard !stopped else { return }
        target = orientation; self.generation = generation
        identity.select(generation: generation); schedule.setTarget(orientation)
        #if DEBUG
        LiveRopeReviewTrace.log("controller target generation=\(generation) orientation=\(orientation.vector)")
        #endif
    }
    func advance(elapsed: Double) {
        #if DEBUG
        reviewAdvanceCount += 1
        if reviewAdvanceCount <= 3 || reviewAdvanceCount % 120 == 0 {
            LiveRopeReviewTrace.log("controller tick count=\(reviewAdvanceCount) busy=\(busy) stopped=\(stopped) elapsed=\(elapsed)")
        }
        #endif
        guard !busy, !stopped else { return }
        let steps = schedule.steps(elapsed: elapsed)
        guard steps > 0 else { return }
        busy = true
        let worker = worker, sceneID = identity.sceneID, token = identity.token
        let target = target, generation = generation, immediate = settleImmediately
        #if DEBUG
        let reviewStart = DispatchTime.now().uptimeNanoseconds
        LiveRopeReviewTrace.log("controller batch start steps=\(steps) token=\(token) generation=\(generation)")
        #endif
        task = Task { [weak self] in
            do {
                let frame = try await worker.advance(steps: steps, target: target, settleImmediately: immediate)
                guard let self else { return }
                self.busy = false; self.task = nil
                #if DEBUG
                LiveRopeReviewTrace.log("controller batch returned ms=\(Double(DispatchTime.now().uptimeNanoseconds-reviewStart)/1e6) deliverable=\(self.identity.accepts(sceneID:sceneID,token:token))")
                #endif
                guard !Task.isCancelled, self.identity.accepts(sceneID: sceneID, token: token), let frame else { return }
                guard frame.metrics.geometryAccepted else { throw RopePhysicsError.invalid("Rejected display geometry") }
                self.schedule.accept(settled: frame.settled)
                self.delivery(sceneID, generation, frame)
            } catch is CancellationError {
                self?.busy = false
                self?.task = nil
            } catch {
                guard let self else { return }
                self.busy = false; self.task = nil
                #if DEBUG
                LiveRopeReviewTrace.log("controller batch failed error=\(error)")
                #endif
                guard !Task.isCancelled, self.identity.accepts(sceneID: sceneID, token: token) else { return }
                self.stop(); self.failure(error)
            }
        }
    }
    func pause() {
        identity.pause(); schedule.pause()
        #if DEBUG
        LiveRopeReviewTrace.log("controller pause")
        #endif
    }
    func resume() {
        guard !stopped else { return }; identity.resume(); schedule.resume()
        #if DEBUG
        LiveRopeReviewTrace.log("controller resume")
        #endif
    }
    func stop() {
        guard !stopped else { return }
        stopped = true; identity.stop(); schedule.stop(); task?.cancel(); task = nil
        let worker = worker
        Task { await worker.stop() }
    }
    deinit {
        task?.cancel()
        let worker = worker
        Task { await worker.stop() }
    }
}
