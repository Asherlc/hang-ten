import AVFoundation
import Combine
import OSLog

@MainActor
protocol WorkoutSpeechSynthesizing: AnyObject {
    var delegate: AVSpeechSynthesizerDelegate? { get set }
    var isSpeaking: Bool { get }

    @discardableResult
    func stopSpeaking(at boundary: AVSpeechBoundary) -> Bool
    func speak(_ utterance: AVSpeechUtterance)
}

extension AVSpeechSynthesizer: WorkoutSpeechSynthesizing {}

@MainActor
protocol WorkoutAudioSessionManaging: AnyObject {
    func configureForSpokenCues() throws
    func activate() throws
    func deactivateAndNotifyOthers() throws
}

@MainActor
private final class SystemWorkoutAudioSession: WorkoutAudioSessionManaging {
    private let session: AVAudioSession

    init(session: AVAudioSession = .sharedInstance()) {
        self.session = session
    }

    func configureForSpokenCues() throws {
        try session.setCategory(.playback, mode: .spokenAudio, options: [.duckOthers])
    }

    func activate() throws {
        try session.setActive(true)
    }

    func deactivateAndNotifyOthers() throws {
        try session.setActive(false, options: .notifyOthersOnDeactivation)
    }
}

@MainActor
final class WorkoutAudioCoach: NSObject, ObservableObject {
    @Published private(set) var isSpeaking = false

    private let synthesizer: any WorkoutSpeechSynthesizing
    private let audioSession: any WorkoutAudioSessionManaging
    private let logger = Logger(subsystem: "com.hangten.training", category: "WorkoutAudio")
    private var configuredAudioSession = false
    private var deactivationRetryTask: Task<Void, Never>?
    private var remainingDeactivationRetries: Int

    private static let maximumDeactivationRetries = 1

    override convenience init() {
        self.init(
            synthesizer: AVSpeechSynthesizer(),
            audioSession: SystemWorkoutAudioSession()
        )
    }

    init(
        synthesizer: any WorkoutSpeechSynthesizing,
        audioSession: any WorkoutAudioSessionManaging
    ) {
        self.synthesizer = synthesizer
        self.audioSession = audioSession
        self.remainingDeactivationRetries = WorkoutAudioCoach.maximumDeactivationRetries
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
        deactivateAudioSessionIfSpeechStopped()
    }

    private var preferredLanguageCode: String {
        Locale.preferredLanguages.first ?? "en-US"
    }

    private func configureAudioSessionIfNeeded() {
        guard !configuredAudioSession else { return }

        do {
            try audioSession.configureForSpokenCues()
            try audioSession.activate()
            configuredAudioSession = true
            remainingDeactivationRetries = WorkoutAudioCoach.maximumDeactivationRetries
        } catch {
            logger.error("Unable to activate spoken cue audio session: \(error.localizedDescription, privacy: .public)")
        }
    }

    private func deactivateAudioSessionIfSpeechStopped() {
        guard !synthesizer.isSpeaking else { return }
        deactivateAudioSession()
    }

    private func deactivateAudioSession() {
        guard configuredAudioSession else { return }

        do {
            try audioSession.deactivateAndNotifyOthers()
            configuredAudioSession = false
            deactivationRetryTask?.cancel()
            deactivationRetryTask = nil
        } catch {
            logger.error("Unable to deactivate spoken cue audio session: \(error.localizedDescription, privacy: .public)")
            scheduleDeactivationRetryIfNeeded()
        }
    }

    private func scheduleDeactivationRetryIfNeeded() {
        guard configuredAudioSession,
              !synthesizer.isSpeaking,
              remainingDeactivationRetries > 0,
              deactivationRetryTask == nil else { return }

        remainingDeactivationRetries -= 1
        deactivationRetryTask = Task { @MainActor [weak self] in
            await Task.yield()
            guard !Task.isCancelled, let self else { return }

            deactivationRetryTask = nil
            deactivateAudioSessionIfSpeechStopped()
        }
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
            self.deactivateAudioSessionIfSpeechStopped()
        }
    }

    nonisolated func speechSynthesizer(
        _ synthesizer: AVSpeechSynthesizer,
        didCancel utterance: AVSpeechUtterance
    ) {
        Task { @MainActor in
            isSpeaking = false
            self.deactivateAudioSessionIfSpeechStopped()
        }
    }
}
