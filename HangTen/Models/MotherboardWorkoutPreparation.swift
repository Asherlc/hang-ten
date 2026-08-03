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

struct MotherboardWorkoutPreparation: Equatable {
    private(set) var step: MotherboardWorkoutPreparationStep = .tare
    private(set) var bodyweightKGF: Double?
    private(set) var result: MotherboardWorkoutPreparationResult = .inProgress

    static func requiresPreparation(isInitialStart: Bool, isStreaming: Bool) -> Bool {
        isInitialStart && isStreaming
    }

    mutating func completeTare() {
        guard step == .tare else { return }
        step = .bodyweight
    }

    mutating func completeBodyweight(with bodyweightKGF: Double?) {
        guard step == .bodyweight else { return }
        let capturedBodyweight = bodyweightKGF.flatMap { $0.isFinite && $0 > 0 ? $0 : nil }
        self.bodyweightKGF = capturedBodyweight
        step = .ready
        result = .completed(bodyweightKGF: capturedBodyweight)
    }

    mutating func retryBodyweight() {
        guard step == .ready else { return }
        bodyweightKGF = nil
        step = .bodyweight
        result = .inProgress
    }

    mutating func skip() {
        bodyweightKGF = nil
        result = .skipped
    }
}
