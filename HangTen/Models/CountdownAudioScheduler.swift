import AVFoundation
import Foundation
import OSLog

struct CountdownAudioSchedule: Hashable {
    struct Cue: Hashable {
        let phrase: String
        let offset: TimeInterval
    }

    let cues: [Cue]
    let endOffset: TimeInterval

    private init(cues: [Cue], endOffset: TimeInterval) {
        self.cues = cues
        self.endOffset = endOffset
    }

    init(remainingFrom phrase: String) {
        switch phrase {
        case "3":
            cues = [
                Cue(phrase: "3", offset: 0),
                Cue(phrase: "2", offset: 1),
                Cue(phrase: "1", offset: 2)
            ]
            endOffset = 3
        case "2":
            cues = [
                Cue(phrase: "2", offset: 0),
                Cue(phrase: "1", offset: 1)
            ]
            endOffset = 2
        case "1":
            cues = [Cue(phrase: "1", offset: 0)]
            endOffset = 1
        default:
            cues = []
            endOffset = 0
        }
    }

    func appendingShortIntervals(
        _ durations: [TimeInterval],
        startingAt initialOffset: TimeInterval
    ) -> CountdownAudioSchedule {
        var result = cues
        var intervalStart = initialOffset

        for duration in durations {
            guard duration > 0 && duration <= 3 else { break }
            let firstNumber = min(3, max(1, Int(ceil(duration))))
            for number in stride(from: firstNumber, through: 1, by: -1) {
                let offset = number == firstNumber
                    ? intervalStart
                    : intervalStart + duration - TimeInterval(number)
                result.append(Cue(phrase: String(number), offset: offset))
            }
            intervalStart += duration
        }

        return CountdownAudioSchedule(
            cues: result,
            endOffset: max(endOffset, intervalStart)
        )
    }
}

struct CountdownAudioRenderAttemptPolicy {
    static let maximumAttempts = 3

    static func shouldRetry(
        completedAttempts: Int,
        renderedBufferCount: Int
    ) -> Bool {
        renderedBufferCount == 0 && completedAttempts < maximumAttempts
    }

    static func shouldIgnoreCallback(phraseIsAlreadyPrepared: Bool) -> Bool {
        phraseIsAlreadyPrepared
    }
}

protocol CountdownAudioScheduling: AnyObject {
    func prewarm(completion: @escaping (Bool) -> Void)

    @discardableResult
    func schedule(_ schedule: CountdownAudioSchedule, startHostTime: UInt64) -> Bool

    func stop()
}

extension CountdownAudioScheduling {
    @discardableResult
    func schedule(remainingFrom phrase: String, startHostTime: UInt64) -> Bool {
        schedule(CountdownAudioSchedule(remainingFrom: phrase), startHostTime: startHostTime)
    }
}

protocol CountdownAudioSchedulingBackend: AnyObject {
    func prewarm(completion: @escaping (Bool) -> Void)

    @discardableResult
    func schedule(_ schedule: CountdownAudioSchedule, startHostTime: UInt64) -> Bool

    func stop()
}

protocol CountdownAudioLifecycleLogging: AnyObject {
    func prewarmCompleted(succeeded: Bool)
    func scheduleAccepted(_ schedule: CountdownAudioSchedule, startHostTime: UInt64)
    func scheduleRejected(_ schedule: CountdownAudioSchedule, startHostTime: UInt64)
}

private final class SystemCountdownAudioLifecycleLogger: CountdownAudioLifecycleLogging {
    private let logger = Logger(subsystem: "com.hangten.training", category: "CountdownAudio")

    func prewarmCompleted(succeeded: Bool) {
        if succeeded {
            logger.notice("Countdown audio prewarm ready")
        } else {
            logger.error("Countdown audio prewarm failed; numeric countdowns will remain silent")
        }
    }

    func scheduleAccepted(_ schedule: CountdownAudioSchedule, startHostTime: UInt64) {
        let phrases = schedule.cues.map(\.phrase).joined(separator: ",")
        let offsets = schedule.cues.map { String(format: "%.3f", $0.offset) }.joined(separator: ",")
        logger.notice(
            "Accepted countdown schedule phrases=\(phrases, privacy: .public) startHostTime=\(startHostTime, privacy: .public) offsets=\(offsets, privacy: .public)"
        )
    }

    func scheduleRejected(_ schedule: CountdownAudioSchedule, startHostTime: UInt64) {
        let phrases = schedule.cues.map(\.phrase).joined(separator: ",")
        logger.error(
            "Rejected countdown schedule phrases=\(phrases, privacy: .public) startHostTime=\(startHostTime, privacy: .public); no live-speech fallback"
        )
    }
}

final class CountdownAudioScheduler: CountdownAudioScheduling {
    private let backend: any CountdownAudioSchedulingBackend
    private let lifecycleLogger: any CountdownAudioLifecycleLogging
    private var hasActiveSchedule = false

    init(backend: any CountdownAudioSchedulingBackend) {
        self.backend = backend
        self.lifecycleLogger = SystemCountdownAudioLifecycleLogger()
    }

    init(
        backend: any CountdownAudioSchedulingBackend,
        lifecycleLogger: any CountdownAudioLifecycleLogging
    ) {
        self.backend = backend
        self.lifecycleLogger = lifecycleLogger
    }

    func prewarm(completion: @escaping (Bool) -> Void) {
        backend.prewarm { [lifecycleLogger] succeeded in
            lifecycleLogger.prewarmCompleted(succeeded: succeeded)
            completion(succeeded)
        }
    }

    convenience init(
        preferredLanguageCode: String,
        rate: Float,
        pitchMultiplier: Float,
        volume: Float
    ) {
        self.init(
            backend: SystemCountdownAudioSchedulingBackend(
                preferredLanguageCode: preferredLanguageCode,
                rate: rate,
                pitchMultiplier: pitchMultiplier,
                volume: volume
            )
        )
    }

    @discardableResult
    func schedule(_ schedule: CountdownAudioSchedule, startHostTime: UInt64) -> Bool {
        guard !hasActiveSchedule else {
            lifecycleLogger.scheduleRejected(schedule, startHostTime: startHostTime)
            return false
        }

        guard !schedule.cues.isEmpty,
              backend.schedule(schedule, startHostTime: startHostTime) else {
            lifecycleLogger.scheduleRejected(schedule, startHostTime: startHostTime)
            return false
        }

        hasActiveSchedule = true
        lifecycleLogger.scheduleAccepted(schedule, startHostTime: startHostTime)
        return true
    }

    func stop() {
        hasActiveSchedule = false
        backend.stop()
    }
}

protocol CountdownAudioBufferPlayback: AnyObject {
    func prepare(format: AVAudioFormat)
    func start() throws
    func schedule(_ buffer: AVAudioPCMBuffer, atHostTime hostTime: UInt64)
    func play()
    func stop()
}

final class CountdownAudioBufferSchedulingBackend: CountdownAudioSchedulingBackend {
    private struct ScheduledBuffer {
        let buffer: AVAudioPCMBuffer
        let hostTime: UInt64
    }

    private let buffersForSchedule: (CountdownAudioSchedule) -> [String: [AVAudioPCMBuffer]]?
    private let playback: any CountdownAudioBufferPlayback
    private let currentHostTime: () -> UInt64
    private var retainedPlaybackBuffers: [AVAudioPCMBuffer] = []
    private var isPrewarmed = false

    init(
        buffersForSchedule: @escaping (CountdownAudioSchedule) -> [String: [AVAudioPCMBuffer]]?,
        playback: any CountdownAudioBufferPlayback,
        currentHostTime: @escaping () -> UInt64
    ) {
        self.buffersForSchedule = buffersForSchedule
        self.playback = playback
        self.currentHostTime = currentHostTime
    }

    func prewarm(completion: @escaping (Bool) -> Void) {
        completion(prewarm(CountdownAudioSchedule(remainingFrom: "3")))
    }

    @discardableResult
    func prewarm(_ schedule: CountdownAudioSchedule) -> Bool {
        guard let buffersByPhrase = buffersForSchedule(schedule),
              let scheduledBuffers = scheduledBuffers(
                for: schedule,
                buffersByPhrase: buffersByPhrase,
                startHostTime: 0
              ),
              let format = scheduledBuffers.first?.buffer.format else {
            return false
        }

        playback.prepare(format: format)
        isPrewarmed = true
        return true
    }

    @discardableResult
    func schedule(_ schedule: CountdownAudioSchedule, startHostTime: UInt64) -> Bool {
        guard let buffersByPhrase = buffersForSchedule(schedule),
              let scheduledBuffers = scheduledBuffers(
                for: schedule,
                buffersByPhrase: buffersByPhrase,
                startHostTime: startHostTime
              ),
              currentHostTime() < startHostTime else {
            return false
        }

        guard isPrewarmed || prewarm(schedule) else { return false }
        do {
            try playback.start()
        } catch {
            stop()
            return false
        }

        guard currentHostTime() < startHostTime else {
            stop()
            return false
        }

        retainedPlaybackBuffers = scheduledBuffers.map(\.buffer)
        for scheduledBuffer in scheduledBuffers {
            playback.schedule(
                scheduledBuffer.buffer,
                atHostTime: scheduledBuffer.hostTime
            )
        }

        guard currentHostTime() < startHostTime else {
            stop()
            return false
        }

        playback.play()
        return true
    }

    func stop() {
        playback.stop()
        retainedPlaybackBuffers.removeAll()
        isPrewarmed = false
    }

    private func scheduledBuffers(
        for schedule: CountdownAudioSchedule,
        buffersByPhrase: [String: [AVAudioPCMBuffer]],
        startHostTime: UInt64
    ) -> [ScheduledBuffer]? {
        var result: [ScheduledBuffer] = []

        for (cueIndex, cue) in schedule.cues.enumerated() {
            guard let buffers = buffersByPhrase[cue.phrase] else { return nil }
            var cueBufferOffset: TimeInterval = 0

            for buffer in buffers {
                guard buffer.format.sampleRate > 0 else { return nil }
                let offsetHostTime = AVAudioTime.hostTime(
                    forSeconds: cue.offset + cueBufferOffset
                )
                let (hostTime, overflowed) = startHostTime.addingReportingOverflow(offsetHostTime)
                guard !overflowed else { return nil }

                result.append(ScheduledBuffer(buffer: buffer, hostTime: hostTime))
                cueBufferOffset += TimeInterval(buffer.frameLength) / buffer.format.sampleRate
            }

            let cueDeadline = cueIndex + 1 < schedule.cues.count
                ? schedule.cues[cueIndex + 1].offset
                : cue.offset + 1
            guard cueBufferOffset < cueDeadline - cue.offset else { return nil }
        }

        return result
    }
}

private final class SystemCountdownAudioBufferPlayback: CountdownAudioBufferPlayback {
    private let engine = AVAudioEngine()
    private let playerNode = AVAudioPlayerNode()
    private var connectedFormat: AVAudioFormat?

    init() {
        engine.attach(playerNode)
    }

    func prepare(format: AVAudioFormat) {
        if connectedFormat == nil {
            engine.connect(playerNode, to: engine.mainMixerNode, format: format)
            connectedFormat = format
        }
        engine.prepare()
    }

    func start() throws {
        if !engine.isRunning {
            try engine.start()
        }
    }

    func schedule(_ buffer: AVAudioPCMBuffer, atHostTime hostTime: UInt64) {
        playerNode.scheduleBuffer(
            buffer,
            at: AVAudioTime(hostTime: hostTime),
            options: [],
            completionHandler: nil
        )
    }

    func play() {
        playerNode.play()
    }

    func stop() {
        playerNode.stop()
        engine.stop()
    }
}

private final class SystemCountdownAudioSchedulingBackend: CountdownAudioSchedulingBackend {
    private enum PreparationState {
        case idle
        case preparingPlayback
        case ready
        case failed
    }

    private let synthesizer = AVSpeechSynthesizer()
    private let playback = SystemCountdownAudioBufferPlayback()
    private let preferredLanguageCode: String
    private let rate: Float
    private let pitchMultiplier: Float
    private let volume: Float
    private let stateLock = NSLock()
    private let logger = Logger(subsystem: "com.hangten.training", category: "CountdownAudio")
    private var pendingBuffers: [String: [AVAudioPCMBuffer]] = [:]
    private var preparedBuffers: [String: [AVAudioPCMBuffer]] = [:]
    private var failedPhrases: Set<String> = []
    private var renderAttempts: [String: Int] = [:]
    private var preparationState: PreparationState = .idle
    private var prewarmCompletions: [(Bool) -> Void] = []
    private lazy var bufferSchedulingBackend = CountdownAudioBufferSchedulingBackend(
        buffersForSchedule: { [weak self] schedule in
            self?.preparedSnapshot(for: schedule)
        },
        playback: playback,
        currentHostTime: {
            AVAudioTime.hostTime(forSeconds: ProcessInfo.processInfo.systemUptime)
        }
    )

    init(
        preferredLanguageCode: String,
        rate: Float,
        pitchMultiplier: Float,
        volume: Float
    ) {
        self.preferredLanguageCode = preferredLanguageCode
        self.rate = rate
        self.pitchMultiplier = pitchMultiplier
        self.volume = volume
        for phrase in ["3", "2", "1"] {
            pendingBuffers[phrase] = []
        }

        for phrase in ["3", "2", "1"] {
            render(phrase)
        }
    }

    private func render(_ phrase: String) {
        withStateLock {
            renderAttempts[phrase, default: 0] += 1
            pendingBuffers[phrase] = []
        }
        let utterance = AVSpeechUtterance(string: phrase)
        utterance.voice = AVSpeechSynthesisVoice(language: preferredLanguageCode)
        utterance.rate = rate
        utterance.pitchMultiplier = pitchMultiplier
        utterance.volume = volume
        synthesizer.write(utterance) { [weak self] buffer in
            self?.receive(buffer, for: phrase)
        }
    }

    func prewarm(completion: @escaping (Bool) -> Void) {
        let immediateResult: Bool? = withStateLock {
            switch preparationState {
            case .ready:
                return true
            case .failed:
                return false
            case .idle, .preparingPlayback:
                prewarmCompletions.append(completion)
                return nil
            }
        }

        if let immediateResult {
            completion(immediateResult)
            return
        }
        preparePlaybackIfBuffersResolved()
    }

    @discardableResult
    func schedule(_ schedule: CountdownAudioSchedule, startHostTime: UInt64) -> Bool {
        guard bufferSchedulingBackend.schedule(
            schedule,
            startHostTime: startHostTime
        ) else {
            logger.error("Countdown speech buffers were unavailable, overlong, or past deadline")
            return false
        }
        logger.notice(
            "Scheduled countdown cues: \(schedule.cues.map(\.phrase).joined(separator: ","), privacy: .public)"
        )
        return true
    }

    func stop() {
        bufferSchedulingBackend.stop()
        withStateLock {
            switch preparationState {
            case .ready:
                preparationState = .idle
            case .idle, .preparingPlayback, .failed:
                break
            }
        }
    }

    private func receive(_ buffer: AVAudioBuffer, for phrase: String) {
        guard let pcmBuffer = buffer as? AVAudioPCMBuffer else {
            logger.error("Countdown PCM render failed phrase=\(phrase, privacy: .public) reason=non-PCM-buffer")
            withStateLock {
                failedPhrases.insert(phrase)
                pendingBuffers.removeValue(forKey: phrase)
            }
            preparePlaybackIfBuffersResolved()
            return
        }

        guard pcmBuffer.frameLength > 0 else {
            let shouldRetry: Bool = withStateLock {
                if CountdownAudioRenderAttemptPolicy.shouldIgnoreCallback(
                    phraseIsAlreadyPrepared: preparedBuffers[phrase] != nil
                ) {
                    pendingBuffers.removeValue(forKey: phrase)
                    return false
                }
                let buffers = pendingBuffers.removeValue(forKey: phrase) ?? []
                let completedAttempts = renderAttempts[phrase, default: 0]
                if CountdownAudioRenderAttemptPolicy.shouldRetry(
                    completedAttempts: completedAttempts,
                    renderedBufferCount: buffers.count
                ) {
                    return true
                }
                guard !buffers.isEmpty else {
                    logger.error(
                        "Countdown PCM render failed phrase=\(phrase, privacy: .public) reason=empty-terminal-render attempts=\(completedAttempts, privacy: .public)"
                    )
                    failedPhrases.insert(phrase)
                    return false
                }
                preparedBuffers[phrase] = buffers
                return false
            }
            if shouldRetry {
                let nextAttempt = withStateLock { renderAttempts[phrase, default: 0] + 1 }
                logger.notice(
                    "Retrying empty countdown PCM render phrase=\(phrase, privacy: .public) attempt=\(nextAttempt, privacy: .public)"
                )
                DispatchQueue.main.asyncAfter(deadline: .now() + 0.1) { [weak self] in
                    self?.render(phrase)
                }
                return
            }
            preparePlaybackIfBuffersResolved()
            return
        }

        guard let retainedBuffer = retainedCopy(of: pcmBuffer) else {
            logger.error(
                "Countdown PCM render failed phrase=\(phrase, privacy: .public) reason=copy-failed frames=\(pcmBuffer.frameLength, privacy: .public) format=\(pcmBuffer.format.description, privacy: .public)"
            )
            withStateLock {
                failedPhrases.insert(phrase)
                pendingBuffers.removeValue(forKey: phrase)
            }
            preparePlaybackIfBuffersResolved()
            return
        }

        withStateLock {
            guard failedPhrases.contains(phrase) == false,
                  preparedBuffers[phrase] == nil else { return }
            pendingBuffers[phrase, default: []].append(retainedBuffer)
        }
    }

    private func preparePlaybackIfBuffersResolved() {
        enum Resolution {
            case wait
            case fail([(Bool) -> Void])
            case prepare
        }

        let resolution: Resolution = withStateLock {
            guard case .idle = preparationState else { return .wait }
            if !failedPhrases.isEmpty {
                preparationState = .failed
                let completions = prewarmCompletions
                prewarmCompletions.removeAll()
                return .fail(completions)
            }
            guard ["3", "2", "1"].allSatisfy({ preparedBuffers[$0]?.isEmpty == false }) else {
                return .wait
            }
            preparationState = .preparingPlayback
            return .prepare
        }

        switch resolution {
        case .wait:
            return
        case .fail(let completions):
            completions.forEach { $0(false) }
        case .prepare:
            if let buffers = preparedSnapshot(
                for: CountdownAudioSchedule(remainingFrom: "3")
            ) {
                let diagnostics = ["3", "2", "1"].compactMap { phrase -> String? in
                    guard let phraseBuffers = buffers[phrase] else { return nil }
                    let duration = phraseBuffers.reduce(0.0) { total, buffer in
                        guard buffer.format.sampleRate > 0 else { return total }
                        return total + TimeInterval(buffer.frameLength) / buffer.format.sampleRate
                    }
                    let sampleRates = Set(phraseBuffers.map { Int($0.format.sampleRate) })
                        .sorted()
                        .map(String.init)
                        .joined(separator: "/")
                    return "\(phrase):\(String(format: "%.3f", duration))s@\(sampleRates)Hz"
                }.joined(separator: ",")
                logger.notice(
                    "Prepared countdown PCM diagnostics \(diagnostics, privacy: .public)"
                )
            }
            let succeeded = bufferSchedulingBackend.prewarm(
                CountdownAudioSchedule(remainingFrom: "3")
            )
            let completions: [(Bool) -> Void] = withStateLock {
                preparationState = succeeded ? .ready : .failed
                let completions = prewarmCompletions
                prewarmCompletions.removeAll()
                return completions
            }
            completions.forEach { $0(succeeded) }
        }
    }

    private func preparedSnapshot(
        for schedule: CountdownAudioSchedule
    ) -> [String: [AVAudioPCMBuffer]]? {
        withStateLock {
            var snapshot: [String: [AVAudioPCMBuffer]] = [:]
            for cue in schedule.cues {
                guard failedPhrases.contains(cue.phrase) == false,
                      let buffers = preparedBuffers[cue.phrase],
                      !buffers.isEmpty else {
                    return nil
                }
                snapshot[cue.phrase] = buffers
            }
            return snapshot
        }
    }

    private func retainedCopy(of source: AVAudioPCMBuffer) -> AVAudioPCMBuffer? {
        guard let copy = AVAudioPCMBuffer(
            pcmFormat: source.format,
            frameCapacity: source.frameLength
        ) else {
            return nil
        }

        copy.frameLength = source.frameLength
        let sourceBuffers = UnsafeMutableAudioBufferListPointer(source.mutableAudioBufferList)
        let destinationBuffers = UnsafeMutableAudioBufferListPointer(copy.mutableAudioBufferList)
        guard sourceBuffers.count == destinationBuffers.count else { return nil }

        for index in sourceBuffers.indices {
            let sourceBuffer = sourceBuffers[index]
            guard let sourceData = sourceBuffer.mData,
                  let destinationData = destinationBuffers[index].mData,
                  destinationBuffers[index].mDataByteSize >= sourceBuffer.mDataByteSize else {
                return nil
            }
            memcpy(destinationData, sourceData, Int(sourceBuffer.mDataByteSize))
            destinationBuffers[index].mDataByteSize = sourceBuffer.mDataByteSize
        }

        return copy
    }

    private func withStateLock<T>(_ operation: () -> T) -> T {
        stateLock.lock()
        defer { stateLock.unlock() }
        return operation()
    }
}
