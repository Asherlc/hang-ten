import AVFoundation
import Foundation
import OSLog

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

private final class SystemCountdownAudioSchedulingBackend: CountdownAudioSchedulingBackend {
    private struct ScheduledBuffer {
        let buffer: AVAudioPCMBuffer
        let hostTime: UInt64
    }

    private let engine = AVAudioEngine()
    private let playerNode = AVAudioPlayerNode()
    private let synthesizer = AVSpeechSynthesizer()
    private let stateLock = NSLock()
    private let logger = Logger(subsystem: "com.hangten.training", category: "CountdownAudio")
    private var pendingBuffers: [String: [AVAudioPCMBuffer]] = [:]
    private var preparedBuffers: [String: [AVAudioPCMBuffer]] = [:]
    private var failedPhrases: Set<String> = []
    private var retainedPlaybackBuffers: [AVAudioPCMBuffer] = []
    private var connectedFormat: AVAudioFormat?

    init(
        preferredLanguageCode: String,
        rate: Float,
        pitchMultiplier: Float,
        volume: Float
    ) {
        engine.attach(playerNode)

        for phrase in ["3", "2", "1"] {
            pendingBuffers[phrase] = []
        }

        for phrase in ["3", "2", "1"] {
            let utterance = AVSpeechUtterance(string: phrase)
            utterance.voice = AVSpeechSynthesisVoice(language: preferredLanguageCode)
            utterance.rate = rate
            utterance.pitchMultiplier = pitchMultiplier
            utterance.volume = volume
            synthesizer.write(utterance) { [weak self] buffer in
                self?.receive(buffer, for: phrase)
            }
        }
    }

    @discardableResult
    func schedule(_ schedule: CountdownAudioSchedule, startHostTime: UInt64) -> Bool {
        guard let buffersByPhrase = preparedSnapshot(for: schedule) else {
            logger.error("Countdown speech buffers were not ready before the start deadline")
            return false
        }

        let nowHostTime = AVAudioTime.hostTime(forSeconds: ProcessInfo.processInfo.systemUptime)
        guard nowHostTime < startHostTime,
              let scheduledBuffers = scheduledBuffers(
                for: schedule,
                buffersByPhrase: buffersByPhrase,
                startHostTime: startHostTime
              ),
              let format = scheduledBuffers.first?.buffer.format else {
            logger.error("Countdown start deadline passed before audio could be scheduled")
            return false
        }

        connectPlayerIfNeeded(format: format)
        engine.prepare()

        do {
            if !engine.isRunning {
                try engine.start()
            }
        } catch {
            logger.error("Unable to start countdown audio engine: \(error.localizedDescription, privacy: .public)")
            return false
        }

        let hostTimeAfterEngineStart = AVAudioTime.hostTime(
            forSeconds: ProcessInfo.processInfo.systemUptime
        )
        guard hostTimeAfterEngineStart < startHostTime else {
            engine.stop()
            logger.error("Countdown audio engine missed the start deadline")
            return false
        }

        retainedPlaybackBuffers = scheduledBuffers.map(\.buffer)
        for scheduledBuffer in scheduledBuffers {
            playerNode.scheduleBuffer(
                scheduledBuffer.buffer,
                at: AVAudioTime(hostTime: scheduledBuffer.hostTime),
                options: [],
                completionHandler: nil
            )
        }
        playerNode.play()
        logger.notice(
            "Scheduled countdown cues: \(schedule.cues.map(\.phrase).joined(separator: ","), privacy: .public)"
        )
        return true
    }

    func stop() {
        playerNode.stop()
        engine.stop()
        retainedPlaybackBuffers.removeAll()
    }

    private func receive(_ buffer: AVAudioBuffer, for phrase: String) {
        guard let pcmBuffer = buffer as? AVAudioPCMBuffer else {
            withStateLock {
                failedPhrases.insert(phrase)
                pendingBuffers.removeValue(forKey: phrase)
            }
            return
        }

        guard pcmBuffer.frameLength > 0 else {
            withStateLock {
                guard let buffers = pendingBuffers.removeValue(forKey: phrase),
                      !buffers.isEmpty else {
                    failedPhrases.insert(phrase)
                    return
                }
                preparedBuffers[phrase] = buffers
            }
            return
        }

        guard let retainedBuffer = retainedCopy(of: pcmBuffer) else {
            withStateLock {
                failedPhrases.insert(phrase)
                pendingBuffers.removeValue(forKey: phrase)
            }
            return
        }

        withStateLock {
            guard failedPhrases.contains(phrase) == false else { return }
            pendingBuffers[phrase, default: []].append(retainedBuffer)
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

    private func scheduledBuffers(
        for schedule: CountdownAudioSchedule,
        buffersByPhrase: [String: [AVAudioPCMBuffer]],
        startHostTime: UInt64
    ) -> [ScheduledBuffer]? {
        var result: [ScheduledBuffer] = []

        for cue in schedule.cues {
            guard let buffers = buffersByPhrase[cue.phrase] else { return nil }
            var cueBufferOffset: TimeInterval = 0

            for buffer in buffers {
                let offsetHostTime = AVAudioTime.hostTime(
                    forSeconds: cue.offset + cueBufferOffset
                )
                let (hostTime, overflowed) = startHostTime.addingReportingOverflow(offsetHostTime)
                guard !overflowed else { return nil }

                result.append(ScheduledBuffer(buffer: buffer, hostTime: hostTime))
                cueBufferOffset += TimeInterval(buffer.frameLength) / buffer.format.sampleRate
            }
        }

        return result
    }

    private func connectPlayerIfNeeded(format: AVAudioFormat) {
        guard connectedFormat == nil else { return }
        engine.connect(playerNode, to: engine.mainMixerNode, format: format)
        connectedFormat = format
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
