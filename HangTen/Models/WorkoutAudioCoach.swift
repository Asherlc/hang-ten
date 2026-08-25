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

struct WorkoutSpeechVoiceCandidate {
    let identifier: String
    let language: String
    let quality: AVSpeechSynthesisVoiceQuality
}

enum WorkoutSpeechVoiceSelector {
    static func bestCandidate(
        from candidates: [WorkoutSpeechVoiceCandidate],
        preferredLanguage: String
    ) -> WorkoutSpeechVoiceCandidate? {
        let exactLocaleCandidates = candidates.filter {
            $0.language.caseInsensitiveCompare(preferredLanguage) == .orderedSame
        }
        return exactLocaleCandidates.max { qualityRank($0.quality) < qualityRank($1.quality) }
    }

    static func bestInstalledVoice(for preferredLanguage: String) -> AVSpeechSynthesisVoice? {
        let voices = AVSpeechSynthesisVoice.speechVoices()
        let candidates = voices.map {
            WorkoutSpeechVoiceCandidate(
                identifier: $0.identifier,
                language: $0.language,
                quality: $0.quality
            )
        }
        guard let candidate = bestCandidate(
            from: candidates,
            preferredLanguage: preferredLanguage
        ) else {
            return nil
        }
        return voices.first { $0.identifier == candidate.identifier }
    }

    private static func qualityRank(_ quality: AVSpeechSynthesisVoiceQuality) -> Int {
        switch quality {
        case .premium: return 3
        case .enhanced: return 2
        default: return 1
        }
    }
}

enum CountdownAudioPreparationState: Equatable {
    case idle
    case preparing
    case ready
    case failed
}

struct WorkoutSpeechOwnership {
    private struct SpeechIdentity {
        let utterance: AVSpeechUtterance
        let generation: Int
    }

    private var generation = 0
    private var activeSpeech: SpeechIdentity?
    private var pendingStop: SpeechIdentity?

    mutating func begin(_ utterance: AVSpeechUtterance) {
        generation += 1
        activeSpeech = SpeechIdentity(utterance: utterance, generation: generation)
        pendingStop = nil
    }

    mutating func requestStop() {
        guard activeSpeech != nil else { return }
        generation += 1
        if let activeSpeech {
            pendingStop = SpeechIdentity(utterance: activeSpeech.utterance, generation: generation)
        }
        activeSpeech = nil
    }

    func ownsActive(_ utterance: AVSpeechUtterance) -> Bool {
        owns(activeSpeech, utterance: utterance)
    }

    func ownsPendingStop(_ utterance: AVSpeechUtterance) -> Bool {
        owns(pendingStop, utterance: utterance)
    }

    mutating func finishActive(_ utterance: AVSpeechUtterance) {
        guard ownsActive(utterance) else { return }
        activeSpeech = nil
    }

    mutating func finishPendingStop(_ utterance: AVSpeechUtterance) {
        guard ownsPendingStop(utterance) else { return }
        pendingStop = nil
    }

    private func owns(_ identity: SpeechIdentity?, utterance: AVSpeechUtterance) -> Bool {
        guard let identity else { return false }
        return identity.generation == generation && identity.utterance === utterance
    }
}

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
protocol WorkoutCountdownCompletionScheduling: AnyObject {
    func schedule(atUptime uptime: TimeInterval, completion: @escaping () -> Void)
    func cancel()
}

@MainActor
private final class SystemWorkoutCountdownCompletionScheduler:
    WorkoutCountdownCompletionScheduling
{
    private var task: Task<Void, Never>?

    func schedule(atUptime uptime: TimeInterval, completion: @escaping () -> Void) {
        cancel()
        let delay = max(0, uptime - ProcessInfo.processInfo.systemUptime)
        task = Task { @MainActor [weak self] in
            do {
                try await Task.sleep(for: .seconds(delay))
            } catch {
                return
            }
            guard !Task.isCancelled, let self else { return }
            task = nil
            completion()
        }
    }

    func cancel() {
        task?.cancel()
        task = nil
    }
}

@MainActor
final class WorkoutAudioCoach: NSObject, ObservableObject {
    @Published private(set) var isSpeaking = false
    @Published private(set) var countdownPreparationState: CountdownAudioPreparationState = .idle

    private let synthesizer: any WorkoutSpeechSynthesizing
    private let audioSession: any WorkoutAudioSessionManaging
    private let countdownSchedulerFactory: () -> any CountdownAudioScheduling
    private var countdownScheduler: (any CountdownAudioScheduling)?
    private let countdownCompletionScheduler: any WorkoutCountdownCompletionScheduling
    private let logger = Logger(subsystem: "com.hangten.training", category: "WorkoutAudio")
    private var configuredAudioSession = false
    private var ownsCountdownSchedule = false
    private var deactivationRetryTask: Task<Void, Never>?
    private var speechOwnership = WorkoutSpeechOwnership()

    private static let deactivationRetryDelay: Duration = .milliseconds(200)
    override convenience init() {
        self.init(
            synthesizer: AVSpeechSynthesizer(),
            audioSession: SystemWorkoutAudioSession()
        )
    }

    convenience init(
        synthesizer: any WorkoutSpeechSynthesizing,
        audioSession: any WorkoutAudioSessionManaging
    ) {
        self.init(
            synthesizer: synthesizer,
            audioSession: audioSession,
            countdownSchedulerFactory: {
                CountdownAudioScheduler(
                    preferredLanguageCode: Self.preferredLanguageCode,
                    rate: 0.50,
                    pitchMultiplier: 1.0,
                    volume: 1.0
                )
            },
            countdownCompletionScheduler: SystemWorkoutCountdownCompletionScheduler()
        )
    }

    convenience init(
        synthesizer: any WorkoutSpeechSynthesizing,
        audioSession: any WorkoutAudioSessionManaging,
        countdownScheduler: any CountdownAudioScheduling
    ) {
        self.init(
            synthesizer: synthesizer,
            audioSession: audioSession,
            countdownSchedulerFactory: { countdownScheduler },
            countdownCompletionScheduler: SystemWorkoutCountdownCompletionScheduler()
        )
    }

    convenience init(
        synthesizer: any WorkoutSpeechSynthesizing,
        audioSession: any WorkoutAudioSessionManaging,
        countdownScheduler: any CountdownAudioScheduling,
        countdownCompletionScheduler: any WorkoutCountdownCompletionScheduling
    ) {
        self.init(
            synthesizer: synthesizer,
            audioSession: audioSession,
            countdownSchedulerFactory: { countdownScheduler },
            countdownCompletionScheduler: countdownCompletionScheduler
        )
    }

    init(
        synthesizer: any WorkoutSpeechSynthesizing,
        audioSession: any WorkoutAudioSessionManaging,
        countdownSchedulerFactory: @escaping () -> any CountdownAudioScheduling,
        countdownCompletionScheduler: any WorkoutCountdownCompletionScheduling
    ) {
        self.synthesizer = synthesizer
        self.audioSession = audioSession
        self.countdownSchedulerFactory = countdownSchedulerFactory
        self.countdownCompletionScheduler = countdownCompletionScheduler
        super.init()
        synthesizer.delegate = self
    }

    func prepareCountdownAudio() {
        guard countdownPreparationState == .idle || countdownPreparationState == .failed else {
            return
        }
        beginCountdownPrewarm()
    }

    func speak(_ phrase: String) {
        guard !phrase.isEmpty else { return }
        cancelOwnedCountdownSchedule()
        deactivationRetryTask?.cancel()
        deactivationRetryTask = nil
        configureAudioSessionIfNeeded()

        let utterance = AVSpeechUtterance(string: phrase)
        utterance.voice = WorkoutSpeechVoiceSelector.bestInstalledVoice(
            for: preferredLanguageCode
        ) ?? AVSpeechSynthesisVoice(language: preferredLanguageCode)
        utterance.rate = phrase.count <= 2 ? 0.50 : 0.47
        utterance.pitchMultiplier = 1.0
        utterance.volume = 1.0
        speechOwnership.begin(utterance)
        isSpeaking = true
        logger.notice("Speaking cue: \(phrase, privacy: .public)")
        synthesizer.speak(utterance)
    }

    @discardableResult
    func startCountdown(remainingFrom phrase: String, startUptime: TimeInterval) -> Bool {
        startCountdown(
            CountdownAudioSchedule(remainingFrom: phrase),
            startUptime: startUptime
        )
    }

    @discardableResult
    func startCountdown(
        _ schedule: CountdownAudioSchedule,
        startUptime: TimeInterval
    ) -> Bool {
        guard !ownsCountdownSchedule,
              countdownPreparationState == .ready,
              let countdownScheduler else { return false }

        deactivationRetryTask?.cancel()
        deactivationRetryTask = nil
        guard configureAudioSessionIfNeeded() else { return false }

        let startHostTime = AVAudioTime.hostTime(forSeconds: startUptime)
        guard countdownScheduler.schedule(schedule, startHostTime: startHostTime) else {
            let phrases = schedule.cues.map(\.phrase).joined(separator: ",")
            logger.error("Unable to pre-schedule numeric countdown \(phrases, privacy: .public)")
            deactivateAudioSessionIfSpeechStopped()
            return false
        }

        ownsCountdownSchedule = true
        let sequenceEndUptime = startUptime + schedule.endOffset
        countdownCompletionScheduler.schedule(atUptime: sequenceEndUptime) { [weak self] in
            self?.finishOwnedCountdownSchedule()
        }
        return true
    }

    func stop() {
        countdownCompletionScheduler.cancel()
        deactivationRetryTask?.cancel()
        deactivationRetryTask = nil
        countdownScheduler?.stop()
        ownsCountdownSchedule = false
        speechOwnership.requestStop()
        isSpeaking = false
        synthesizer.stopSpeaking(at: .immediate)
        deactivateAudioSessionIfSpeechStopped()
        countdownPreparationState = .idle
    }

    private static var preferredLanguageCode: String {
        Locale.preferredLanguages.first ?? "en-US"
    }

    private var preferredLanguageCode: String {
        Self.preferredLanguageCode
    }

    @discardableResult
    private func configureAudioSessionIfNeeded() -> Bool {
        guard !configuredAudioSession else { return true }

        do {
            try audioSession.configureForSpokenCues()
            try audioSession.activate()
            configuredAudioSession = true
            return true
        } catch {
            logger.error("Unable to activate spoken cue audio session: \(error.localizedDescription, privacy: .public)")
            return false
        }
    }

    private func cancelOwnedCountdownSchedule() {
        guard ownsCountdownSchedule else { return }
        countdownCompletionScheduler.cancel()
        countdownScheduler?.stop()
        ownsCountdownSchedule = false
        countdownPreparationState = .idle
    }

    private func finishOwnedCountdownSchedule() {
        guard ownsCountdownSchedule else { return }
        countdownScheduler?.stop()
        ownsCountdownSchedule = false
        deactivateAudioSessionIfSpeechStopped()
        countdownPreparationState = .idle
    }

    private func beginCountdownPrewarm() {
        countdownPreparationState = .preparing
        let countdownScheduler = countdownSchedulerIfNeeded()
        countdownScheduler.prewarm { [weak self] succeeded in
            if Thread.isMainThread {
                MainActor.assumeIsolated {
                    guard self?.countdownPreparationState == .preparing else { return }
                    self?.countdownPreparationState = succeeded ? .ready : .failed
                }
            } else {
                Task { @MainActor in
                    guard self?.countdownPreparationState == .preparing else { return }
                    self?.countdownPreparationState = succeeded ? .ready : .failed
                }
            }
        }
    }

    private func countdownSchedulerIfNeeded() -> any CountdownAudioScheduling {
        if let countdownScheduler {
            return countdownScheduler
        }

        let countdownScheduler = countdownSchedulerFactory()
        self.countdownScheduler = countdownScheduler
        return countdownScheduler
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
              deactivationRetryTask == nil else { return }

        deactivationRetryTask = Task { @MainActor [weak self] in
            do {
                try await Task.sleep(for: WorkoutAudioCoach.deactivationRetryDelay)
            } catch {
                return
            }
            guard !Task.isCancelled, let self else { return }

            deactivationRetryTask = nil
            deactivateAudioSessionIfSpeechStopped()
        }
    }
}

extension WorkoutAudioCoach: AVSpeechSynthesizerDelegate {
    private func ownsActiveSpeech(_ utterance: AVSpeechUtterance) -> Bool {
        speechOwnership.ownsActive(utterance)
    }

    private func ownsPendingStop(_ utterance: AVSpeechUtterance) -> Bool {
        speechOwnership.ownsPendingStop(utterance)
    }

    private func handleSpeechStart(for utterance: AVSpeechUtterance) {
        guard ownsActiveSpeech(utterance) else { return }
        isSpeaking = true
    }

    private func handleSpeechEnd(for utterance: AVSpeechUtterance) {
        if ownsPendingStop(utterance) {
            speechOwnership.finishPendingStop(utterance)
            deactivateAudioSessionIfSpeechStopped()
            return
        }

        guard ownsActiveSpeech(utterance) else { return }
        speechOwnership.finishActive(utterance)
        isSpeaking = false
        deactivateAudioSessionIfSpeechStopped()
    }

    nonisolated func speechSynthesizer(
        _ synthesizer: AVSpeechSynthesizer,
        didStart utterance: AVSpeechUtterance
    ) {
        Task { @MainActor in
            handleSpeechStart(for: utterance)
        }
    }

    nonisolated func speechSynthesizer(
        _ synthesizer: AVSpeechSynthesizer,
        didFinish utterance: AVSpeechUtterance
    ) {
        Task { @MainActor in
            handleSpeechEnd(for: utterance)
        }
    }

    nonisolated func speechSynthesizer(
        _ synthesizer: AVSpeechSynthesizer,
        didCancel utterance: AVSpeechUtterance
    ) {
        Task { @MainActor in
            handleSpeechEnd(for: utterance)
        }
    }
}
