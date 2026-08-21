import Foundation

struct CountdownAudioSchedule: Equatable {
    struct Cue: Equatable {
        let phrase: String
        let offset: TimeInterval
    }

    let cues: [Cue]

    init(remainingFrom phrase: String) {
        switch phrase {
        case "3":
            cues = [
                Cue(phrase: "3", offset: 0),
                Cue(phrase: "2", offset: 1),
                Cue(phrase: "1", offset: 2)
            ]
        case "2":
            cues = [
                Cue(phrase: "2", offset: 0),
                Cue(phrase: "1", offset: 1)
            ]
        case "1":
            cues = [Cue(phrase: "1", offset: 0)]
        default:
            cues = []
        }
    }
}

protocol CountdownAudioScheduling: AnyObject {
    @discardableResult
    func schedule(remainingFrom: String, startHostTime: UInt64) -> Bool

    func stop()
}

protocol CountdownAudioSchedulingBackend: AnyObject {
    @discardableResult
    func schedule(_ schedule: CountdownAudioSchedule, startHostTime: UInt64) -> Bool

    func stop()
}

final class CountdownAudioScheduler: CountdownAudioScheduling {
    private let backend: any CountdownAudioSchedulingBackend
    private var hasActiveSchedule = false

    init(backend: any CountdownAudioSchedulingBackend) {
        self.backend = backend
    }

    @discardableResult
    func schedule(remainingFrom phrase: String, startHostTime: UInt64) -> Bool {
        guard !hasActiveSchedule else { return false }

        let schedule = CountdownAudioSchedule(remainingFrom: phrase)
        guard !schedule.cues.isEmpty,
              backend.schedule(schedule, startHostTime: startHostTime) else {
            return false
        }

        hasActiveSchedule = true
        return true
    }

    func stop() {
        hasActiveSchedule = false
        backend.stop()
    }
}
