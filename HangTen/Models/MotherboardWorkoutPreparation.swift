import Foundation

enum MotherboardWorkoutPreparationStep: Equatable {
    case tare
    case bodyweight
    case ready
}

enum MotherboardWorkoutPreparationResult: Equatable {
    case inProgress
    case completed(bodyweightKGF: Double?)
    case skipped
}

enum MotherboardWorkoutPreparationFailure: Equatable {
    case tareInterrupted
    case bodyweightCaptureInterrupted
    case invalidBodyweightCapture
}

struct MotherboardWorkoutPreparation: Equatable {
    private(set) var step: MotherboardWorkoutPreparationStep = .tare
    private(set) var bodyweightKGF: Double?
    private(set) var result: MotherboardWorkoutPreparationResult = .inProgress
    private(set) var failure: MotherboardWorkoutPreparationFailure?
    private(set) var isTareInProgress = false
    private(set) var isBodyweightCaptureInProgress = false

    var isAwaitingBodyweightCapture: Bool {
        result == .inProgress && step == .bodyweight && !isBodyweightCaptureInProgress && failure == nil
    }

    func canContinue(isStreaming: Bool) -> Bool {
        guard isStreaming,
              step == .ready,
              case let .completed(bodyweightKGF: capturedBodyweight) = result,
              let capturedBodyweight,
              capturedBodyweight.isFinite,
              capturedBodyweight > 0 else { return false }
        return true
    }

    static func requiresPreparation(isInitialStart: Bool, isStreaming: Bool) -> Bool {
        isInitialStart && isStreaming
    }

    @discardableResult
    mutating func startTare() -> Bool {
        guard result == .inProgress, step == .tare, !isTareInProgress else { return false }
        failure = nil
        isTareInProgress = true
        return true
    }

    @discardableResult
    mutating func startBodyweightCapture() -> Bool {
        guard isAwaitingBodyweightCapture else { return false }
        isBodyweightCaptureInProgress = true
        return true
    }

    mutating func completeTare(isStreaming: Bool) {
        guard result == .inProgress, step == .tare, isTareInProgress else { return }
        isTareInProgress = false
        guard isStreaming else {
            failure = .tareInterrupted
            return
        }
        failure = nil
        step = .bodyweight
    }

    mutating func completeBodyweight(with bodyweightKGF: Double?, isStreaming: Bool) {
        guard result == .inProgress, step == .bodyweight, isBodyweightCaptureInProgress else { return }
        isBodyweightCaptureInProgress = false
        guard isStreaming else {
            self.bodyweightKGF = nil
            failure = .bodyweightCaptureInterrupted
            return
        }
        guard let bodyweightKGF, bodyweightKGF.isFinite, bodyweightKGF > 0 else {
            self.bodyweightKGF = nil
            failure = .invalidBodyweightCapture
            return
        }

        let capturedBodyweight = bodyweightKGF
        self.bodyweightKGF = capturedBodyweight
        failure = nil
        step = .ready
        result = .completed(bodyweightKGF: capturedBodyweight)
    }

    mutating func retryTare() {
        guard result == .inProgress, step == .tare else { return }
        failure = nil
        isTareInProgress = false
    }

    mutating func retryBodyweight() {
        guard result != .skipped, step == .bodyweight || step == .ready else { return }
        bodyweightKGF = nil
        failure = nil
        step = .bodyweight
        result = .inProgress
        isBodyweightCaptureInProgress = false
    }

    mutating func invalidateForStreamingLoss() {
        guard result != .skipped else { return }
        isTareInProgress = false
        isBodyweightCaptureInProgress = false

        switch step {
        case .tare:
            failure = .tareInterrupted
        case .bodyweight, .ready:
            bodyweightKGF = nil
            failure = .bodyweightCaptureInterrupted
            step = .bodyweight
            result = .inProgress
        }
    }

    mutating func skip() {
        guard result != .skipped else { return }
        bodyweightKGF = nil
        failure = nil
        result = .skipped
        isTareInProgress = false
        isBodyweightCaptureInProgress = false
    }
}
