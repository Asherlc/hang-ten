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

    var canContinue: Bool {
        guard step == .ready,
              case let .completed(bodyweightKGF: capturedBodyweight) = result,
              let capturedBodyweight,
              capturedBodyweight.isFinite,
              capturedBodyweight > 0 else { return false }
        return true
    }

    static func requiresPreparation(isInitialStart: Bool, isStreaming: Bool) -> Bool {
        isInitialStart && isStreaming
    }

    mutating func completeTare(isStreaming: Bool) {
        guard result == .inProgress, step == .tare else { return }
        guard isStreaming else {
            failure = .tareInterrupted
            return
        }
        failure = nil
        step = .bodyweight
    }

    mutating func completeBodyweight(with bodyweightKGF: Double?, isStreaming: Bool) {
        guard result == .inProgress, step == .bodyweight else { return }
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
    }

    mutating func retryBodyweight() {
        guard result != .skipped, step == .bodyweight || step == .ready else { return }
        bodyweightKGF = nil
        failure = nil
        step = .bodyweight
        result = .inProgress
    }

    mutating func skip() {
        guard result != .skipped else { return }
        bodyweightKGF = nil
        failure = nil
        result = .skipped
    }
}
