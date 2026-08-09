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
    private var speechLifecycle = WorkoutAudioCoachSpeechLifecycle()
    private var activeUtterance: AVSpeechUtterance?
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
            deactivateAudioSessionIfSpeechStopped()
        }
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
