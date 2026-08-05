import AVFoundation
import Combine
import OSLog

@MainActor
final class WorkoutAudioCoach: NSObject, ObservableObject {
    @Published private(set) var isSpeaking = false

    private let synthesizer = AVSpeechSynthesizer()
    private let logger = Logger(subsystem: "com.hangten.training", category: "WorkoutAudio")
    private var configuredAudioSession = false

    override init() {
        super.init()
        synthesizer.delegate = self
    }

    func speak(_ phrase: String) {
        guard !phrase.isEmpty else { return }
        configureAudioSessionIfNeeded()

        synthesizer.stopSpeaking(at: .immediate)

        let utterance = AVSpeechUtterance(string: phrase)
        utterance.voice = AVSpeechSynthesisVoice(language: preferredLanguageCode)
        utterance.rate = phrase.count <= 2 ? 0.50 : 0.47
        utterance.pitchMultiplier = 1.0
        utterance.volume = 1.0
        logger.notice("Speaking cue: \(phrase, privacy: .public)")
        synthesizer.speak(utterance)
    }

    func stop() {
        synthesizer.stopSpeaking(at: .immediate)
        isSpeaking = false
        deactivateAudioSession()
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
            isSpeaking = true
        }
    }

    nonisolated func speechSynthesizer(
        _ synthesizer: AVSpeechSynthesizer,
        didFinish utterance: AVSpeechUtterance
    ) {
        Task { @MainActor in
            isSpeaking = false
            if !self.synthesizer.isSpeaking {
                self.deactivateAudioSession()
            }
        }
    }

    nonisolated func speechSynthesizer(
        _ synthesizer: AVSpeechSynthesizer,
        didCancel utterance: AVSpeechUtterance
    ) {
        Task { @MainActor in
            isSpeaking = false
            if !self.synthesizer.isSpeaking {
                self.deactivateAudioSession()
            }
        }
    }
}
