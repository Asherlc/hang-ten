import AVFoundation
import Combine
import OSLog

@MainActor
final class WorkoutAudioCoach: NSObject, ObservableObject {
    @Published private(set) var isSpeaking = false

    private let synthesizer = AVSpeechSynthesizer()
    private let logger = Logger(subsystem: "com.hangten.training", category: "WorkoutAudio")
    private var configuredAudioSession = false
    private var speechLifecycle = WorkoutAudioCoachSpeechLifecycle()
    private var activeUtterance: AVSpeechUtterance?

    override init() {
        super.init()
        synthesizer.delegate = self
    }

    func speak(_ phrase: String) {
        guard !phrase.isEmpty else { return }
        configureAudioSessionIfNeeded()

        let utterance = AVSpeechUtterance(string: phrase)
        utterance.voice = AVSpeechSynthesisVoice(language: preferredLanguageCode)
        utterance.rate = phrase.count <= 2 ? 0.50 : 0.47
        utterance.pitchMultiplier = 1.0
        utterance.volume = 1.0
        speechLifecycle.beginCue()
        activeUtterance = utterance
        synthesizer.stopSpeaking(at: .immediate)
        logger.notice("Speaking cue: \(phrase, privacy: .public)")
        synthesizer.speak(utterance)
    }

    func stop() {
        let completion = speechLifecycle.stop()
        activeUtterance = nil
        synthesizer.stopSpeaking(at: .immediate)
        isSpeaking = false
        if completion == .deactivateAudioSession {
            deactivateAudioSession()
        }
    }

    private var preferredLanguageCode: String {
        Locale.preferredLanguages.first ?? "en-US"
    }

    private func configureAudioSessionIfNeeded() {
        guard !configuredAudioSession else { return }
        configuredAudioSession = true

        let session = AVAudioSession.sharedInstance()
        try? session.setCategory(.playback, mode: .spokenAudio, options: [.duckOthers])
        try? session.setActive(true)
    }

    private func deactivateAudioSession() {
        guard configuredAudioSession else { return }
        configuredAudioSession = false
        try? AVAudioSession.sharedInstance().setActive(
            false,
            options: .notifyOthersOnDeactivation
        )
    }
}

extension WorkoutAudioCoach: AVSpeechSynthesizerDelegate {
    nonisolated func speechSynthesizer(
        _ synthesizer: AVSpeechSynthesizer,
        didStart utterance: AVSpeechUtterance
    ) {
        Task { @MainActor in
            guard self.activeUtterance === utterance else { return }
            isSpeaking = true
        }
    }

    nonisolated func speechSynthesizer(
        _ synthesizer: AVSpeechSynthesizer,
        didFinish utterance: AVSpeechUtterance
    ) {
        Task { @MainActor in
            self.finishCue(for: utterance)
        }
    }

    nonisolated func speechSynthesizer(
        _ synthesizer: AVSpeechSynthesizer,
        didCancel utterance: AVSpeechUtterance
    ) {
        Task { @MainActor in
            self.finishCue(for: utterance)
        }
    }

    private func finishCue(for utterance: AVSpeechUtterance) {
        guard activeUtterance === utterance,
              let cueID = speechLifecycle.activeCueID,
              speechLifecycle.finishCue(cueID) == .keepAudioSessionActive else { return }

        activeUtterance = nil
        isSpeaking = false
    }
}

struct WorkoutAudioCoachSpeechLifecycle {
    enum CueCompletion: Equatable {
        case ignore
        case keepAudioSessionActive
        case deactivateAudioSession
    }

    private var nextCueID = 0
    private(set) var activeCueID: Int?
    private(set) var isCueing = false

    var hasActiveCue: Bool {
        activeCueID != nil
    }

    @discardableResult
    mutating func beginCue() -> Int {
        nextCueID += 1
        activeCueID = nextCueID
        isCueing = true
        return nextCueID
    }

    mutating func finishCue(_ cueID: Int) -> CueCompletion {
        guard activeCueID == cueID else { return .ignore }
        activeCueID = nil
        return .keepAudioSessionActive
    }

    mutating func stop() -> CueCompletion {
        nextCueID += 1
        activeCueID = nil
        isCueing = false
        return .deactivateAudioSession
    }
}
