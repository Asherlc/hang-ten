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
    /// Record display time while the worker is occupied, with at most eight
    /// pending fixed steps. This is separate from consuming a batch.
    mutating func accrue(elapsed: Double) {
        guard !paused, !stopped, !sleeping, elapsed.isFinite, elapsed > 0 else { return }
        remainder = min(1.0/30, remainder + min(elapsed, 1.0/30))
    }
    mutating func takeSteps() -> Int {
        guard !paused, !stopped, !sleeping else { return 0 }
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
    func advance(steps: Int, target: simd_quatd, settleImmediately: Bool, batchID: UInt64 = 0) throws -> RopeFrameSnapshot? {
        try Task.checkCancellation()
        guard var candidate = solver else { return nil }
        #if DEBUG
        let reviewWorkerStart = DispatchTime.now().uptimeNanoseconds
        LiveRopeReviewTrace.log("worker begin steps=\(steps) immediate=\(settleImmediately) target=\(target.vector)")
        #endif
        var frame: RopeFrameSnapshot?
        #if DEBUG
        var reviewAcceptedSteps = 0
        var reviewMaximumStrain = 0.0
        var reviewMinimumClearanceMargin = Double.infinity
        var reviewCorrections = 0, reviewCaps = 0, reviewRetries = 0
        var reviewStepMilliseconds: [Double] = []
        #endif
        if settleImmediately {
            frame = try candidate.settled(targetOrientation: target, maxDuration: 5)
        } else {
            guard (0...8).contains(steps) else { throw RopePhysicsError.invalid("Unbounded display step") }
            for _ in 0..<steps {
                try Task.checkCancellation()
                #if DEBUG
                let reviewStepStart = DispatchTime.now().uptimeNanoseconds
                #endif
                frame = try candidate.step(dt: 1.0/240, targetOrientation: target)
                #if DEBUG
                reviewStepMilliseconds.append(Double(DispatchTime.now().uptimeNanoseconds-reviewStepStart)/1e6)
                reviewAcceptedSteps += 1
                reviewCorrections += candidate.reviewStepCorrections
                reviewCaps += candidate.reviewStepCaps
                reviewRetries += candidate.reviewStepRetries
                if let frame {
                    reviewMaximumStrain = max(reviewMaximumStrain, frame.metrics.maximumLocalStrain)
                    reviewMinimumClearanceMargin = min(reviewMinimumClearanceMargin, frame.metrics.minimumClearanceMargin)
                }
                #endif
                if frame?.settled == true { break }
            }
        }
        try Task.checkCancellation()
        solver = candidate
        #if DEBUG
        LiveRopeReviewTrace.log("engine batch=\(batchID) startNanos=\(reviewWorkerStart) endNanos=\(DispatchTime.now().uptimeNanoseconds) stepMs=\(reviewStepMilliseconds)")
        LiveRopeReviewTrace.log("worker end orientation=\(String(describing: frame?.orientation.vector)) settled=\(String(describing: frame?.settled))")
        LiveRopeReviewTrace.log("worker metrics acceptedSteps=\(reviewAcceptedSteps) corrections=\(reviewCorrections) caps=\(reviewCaps) retries=\(reviewRetries) maximumStrain=\(reviewMaximumStrain) minimumClearanceMargin=\(reviewMinimumClearanceMargin) speed=\(frame?.metrics.maximumSpeed ?? .infinity) displacement=\(frame?.metrics.boardDisplacement ?? .infinity)")
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
    private let continuousScheduling: Bool
    private var batchID: UInt64 = 0
    #if DEBUG
    private var reviewAdvanceCount = 0
    #endif
    var settleImmediately = false {
        didSet { if oldValue != settleImmediately { identity.invalidate() } }
    }
    private let delivery: Delivery
    private let failure: @MainActor (Error) -> Void

    init(solver: RopeDynamicsSolver, sceneID: UUID, delivery: @escaping Delivery,
         failure: @escaping @MainActor (Error) -> Void, continuousScheduling: Bool? = nil) {
        worker = LiveRopeWorker(solver: solver)
        identity = LiveRopeDeliveryIdentity(sceneID: sceneID)
        target = solver.state.orientation
        #if DEBUG
        self.continuousScheduling = continuousScheduling ??
            (ProcessInfo.processInfo.environment["HANGTEN_REVIEW_CONTINUOUS_ROPE_SCHEDULE"] == "1")
        #else
        self.continuousScheduling = false
        #endif
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
        if continuousScheduling {
            guard !stopped else { return }
            schedule.accrue(elapsed: elapsed)
            dispatchPending()
            return
        }
        guard !busy, !stopped else { return }
        let steps = schedule.steps(elapsed: elapsed)
        dispatch(steps: steps)
    }
    private func dispatchPending() {
        guard !busy, !stopped else { return }
        dispatch(steps: schedule.takeSteps())
    }
    private func dispatch(steps: Int) {
        guard steps > 0 else { return }
        busy = true
        batchID &+= 1
        let batchID = batchID
        let worker = worker, sceneID = identity.sceneID, token = identity.token
        let target = target, generation = generation, immediate = settleImmediately
        #if DEBUG
        let reviewStart = DispatchTime.now().uptimeNanoseconds
        LiveRopeReviewTrace.log("controller batch start steps=\(steps) token=\(token) generation=\(generation) batch=\(batchID) startNanos=\(reviewStart) continuous=\(continuousScheduling)")
        #endif
        task = Task { [weak self] in
            do {
                let frame = try await worker.advance(steps: steps, target: target, settleImmediately: immediate, batchID: batchID)
                guard let self else { return }
                self.busy = false; self.task = nil
                #if DEBUG
                LiveRopeReviewTrace.log("controller batch returned ms=\(Double(DispatchTime.now().uptimeNanoseconds-reviewStart)/1e6) deliverable=\(self.identity.accepts(sceneID:sceneID,token:token)) batch=\(batchID) endNanos=\(DispatchTime.now().uptimeNanoseconds)")
                #endif
                guard !Task.isCancelled, self.identity.accepts(sceneID: sceneID, token: token), let frame else {
                    if self.continuousScheduling { self.dispatchPending() }
                    return
                }
                guard frame.metrics.geometryAccepted else { throw RopePhysicsError.invalid("Rejected display geometry") }
                self.schedule.accept(settled: frame.settled)
                self.delivery(sceneID, generation, frame)
                if self.continuousScheduling { self.dispatchPending() }
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
