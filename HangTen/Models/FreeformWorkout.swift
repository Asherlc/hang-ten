import Foundation

/// Lifecycle of an unstructured, scale-only Freeform session.
enum FreeformSessionState: Equatable {
    case idle
    case active
    case paused
    case finished
}

/// One auto-detected effort, surfaced for live display and review.
struct FreeformEffort: Equatable, Identifiable {
    let id: String
    let duration: TimeInterval
    let peakLoadKGF: Double
    let sampleCount: Int
}

/// Drives a Freeform workout: the athlete enters an edge depth, the connected
/// scale streams force, and efforts are detected automatically. The recorder is
/// the sole effort-boundary authority; this model owns session state, sensor
/// identity captured at start, statistics, and conversion into an ordinary
/// measured workout history record. No board, hand, grip, or prescription facts
/// are inferred or invented.
struct FreeformWorkout {
    static let planID = "freeform"
    static let planTitle = "Freeform"
    private static let recorderStepID = "effort"

    private let configuration: MotherboardDetectionConfiguration
    /// Maximum sample gap before closing the effort at the last observed sample.
    private let streamGapTimeout: TimeInterval
    private var recorder: MotherboardWorkoutRecorder

    private(set) var state: FreeformSessionState = .idle
    private(set) var edgeDepthMM: Double?
    private(set) var elapsed: TimeInterval = 0

    /// The most recent *accepted* scale sample, retained in full so live force
    /// and per-sensor balance come only from a sample the detector counted.
    /// Stale, repeated, nonfinite and paused-gap samples never replace it.
    private(set) var liveMeasurement: MotherboardMeasurement?

    private var startDate: Date?
    private(set) var sensorIdentifier: String?
    private var sensorBatteryValue: UInt16?
    private(set) var forceSensorProfile: ForceSensorProfile = .automatic

    private var resumeCutoff: TimeInterval?
    private var lastAcceptedSampleElapsed: TimeInterval?
    /// Advances even while paused on the same stream, without recording force.
    private var latestSampleNumber: UInt16?
    /// A gap already closed the detector; a second timer tick for the same
    /// silent period must not interrupt repeatedly.
    private var isGapInterrupted = false

    init(
        configuration: MotherboardDetectionConfiguration = .init(),
        streamGapTimeout: TimeInterval = WHC06ProtocolAdapter.advertisementLivenessTimeout
    ) {
        self.configuration = configuration
        self.streamGapTimeout = max(0, streamGapTimeout)
        self.recorder = MotherboardWorkoutRecorder(configuration: configuration)
    }

    /// App recording tolerance for a silent scale stream, selected by the
    /// profile actually connected at Start. These are app-level recording
    /// tolerances for detecting a stalled stream, not manufacturer-prescribed
    /// sample rates. Motherboard frames are streamed at 30 Hz; notification
    /// profiles arrive per BLE notification; WH-C06 advertisement profiles keep
    /// their existing connection liveness window.
    static func recordingGapTimeout(for profile: ForceSensorProfile) -> TimeInterval {
        switch profile {
        case .motherboard: return 0.5
        case .progressor, .genericProgressor, .pitchSix: return 1
        case .automatic, .whC06, .genericWHC06, .entralpi, .climbro:
            return WHC06ProtocolAdapter.advertisementLivenessTimeout
        }
    }

    /// Locale-aware depth presentation used by both the live view and the
    /// summary. Significant digits preserve every accepted positive value
    /// (including 0.004 mm) instead of rounding a small depth to zero.
    static func depthText(_ depthMM: Double, locale: Locale = .current) -> String {
        guard depthMM.isFinite, depthMM > 0 else { return "—" }
        return "\(depthMM.formatted(.number.precision(.significantDigits(1...15)).locale(locale))) mm"
    }

    /// Resume is bound to the scale captured at start. A replacement device
    /// (different UUID or profile) must not inherit this session's metadata.
    func canResume(deviceID: String?, profile: ForceSensorProfile?) -> Bool {
        guard state == .paused,
              let deviceID, let profile,
              deviceID == sensorIdentifier,
              profile == forceSensorProfile else { return false }
        return true
    }

    // MARK: - Depth validation

    /// Accepts a positive finite millimeter depth. A comma decimal separator is
    /// normalized so locale-formatted input (for example "18,5") validates.
    static func normalizedDepth(from text: String) -> Double? {
        let trimmed = text.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return nil }
        let normalized = trimmed.replacingOccurrences(of: ",", with: ".")
        guard let value = Double(normalized), value.isFinite, value > 0 else { return nil }
        return value
    }

    // MARK: - Lifecycle

    /// Sensor identity and profile are captured here and retained for the whole
    /// session, including after a disconnect.
    mutating func start(
        depthMM: Double,
        startDate: Date,
        sensorIdentifier: String?,
        sensorBatteryValue: UInt16? = nil,
        forceSensorProfile: ForceSensorProfile,
        latestSampleNumber: UInt16? = nil
    ) {
        guard state == .idle, depthMM.isFinite, depthMM > 0 else { return }
        edgeDepthMM = depthMM
        self.startDate = startDate
        self.sensorIdentifier = sensorIdentifier
        self.sensorBatteryValue = sensorBatteryValue
        self.forceSensorProfile = forceSensorProfile
        self.latestSampleNumber = latestSampleNumber
        elapsed = 0
        liveMeasurement = nil
        recorder = MotherboardWorkoutRecorder(configuration: configuration)
        state = .active
    }

    /// `elapsed` and `receiptDate` describe the same receipt. Use wall time to
    /// estimate this packet's age, then do detection on the active clock.
    mutating func consume(
        _ measurement: MotherboardMeasurement,
        elapsed: TimeInterval,
        receiptDate: Date
    ) {
        guard state == .active || state == .paused,
              Self.followsInStream(measurement.sampleNumber, latestSampleNumber) else { return }
        let age = receiptDate.timeIntervalSince(measurement.timestamp)
        guard age.isFinite, age >= 0 else { return }
        if state == .paused {
            latestSampleNumber = measurement.sampleNumber
            return
        }

        let projectedElapsed = elapsed - age
        guard measurement.aggregateLoadKGF.isFinite,
              projectedElapsed.isFinite, projectedElapsed >= 0,
              resumeCutoff.map({ projectedElapsed > $0 }) ?? true else { return }

        // Frames decoded from one notification share its receive time. Keep
        // that time even if projection introduces small differences per frame.
        let sampleElapsed = liveMeasurement?.timestamp == measurement.timestamp
            ? lastAcceptedSampleElapsed ?? projectedElapsed
            : projectedElapsed
        if let last = lastAcceptedSampleElapsed, sampleElapsed < last { return }

        // A new sample arriving after a silent stream is the post-gap boundary:
        // close the detector at the last accepted sample before counting it, so
        // a late release cannot book the gap as loaded time.
        if let last = lastAcceptedSampleElapsed, sampleElapsed - last > streamGapTimeout {
            interruptDetector(at: elapsed)
        }

        lastAcceptedSampleElapsed = sampleElapsed
        latestSampleNumber = measurement.sampleNumber
        isGapInterrupted = false
        liveMeasurement = measurement
        updateElapsed(elapsed)
        recorder.consume(
            MotherboardMeasurement(
                timestamp: Date(timeIntervalSinceReferenceDate: sampleElapsed),
                sampleNumber: measurement.sampleNumber,
                batteryValue: measurement.batteryValue,
                rawADCValues: measurement.rawADCValues,
                sensorLoadsKGF: measurement.sensorLoadsKGF,
                aggregateLoadKGF: measurement.aggregateLoadKGF
            ),
            stepID: Self.recorderStepID,
            plannedActiveDuration: 0,
            workoutElapsed: sampleElapsed,
            isActive: true
        )
    }

    /// Forward progress across a UInt16 counter, including wrap at 65535 -> 0.
    /// Equal numbers are replays; large backward jumps are stale identities.
    private static func followsInStream(_ next: UInt16, _ last: UInt16?) -> Bool {
        guard let last else { return true }
        let forward = next &- last
        return forward > 0 && forward <= UInt16.max / 2
    }

    /// Closes an open or pending effort when the timer observes a silent stream.
    mutating func interruptStreamGapIfNeeded(at elapsed: TimeInterval) -> Bool {
        guard state == .active, !isGapInterrupted,
              let last = lastAcceptedSampleElapsed,
              elapsed - last > streamGapTimeout else { return false }
        interruptDetector(at: elapsed)
        return true
    }

    private mutating func interruptDetector(at elapsed: TimeInterval) {
        recorder.interrupt(at: max(0, elapsed))
        // Keep sequence and timing so a replay cannot reopen a stalled stream.
        isGapInterrupted = true
        liveMeasurement = nil
    }

    mutating func updateElapsed(_ elapsed: TimeInterval) {
        guard state == .active else { return }
        self.elapsed = max(0, elapsed)
    }

    /// Closes the current effort at the last observed sample. Used for user
    /// pause, connection loss, and app inactivity. Recorded efforts survive so
    /// the athlete can reconnect and resume.
    mutating func pause(at elapsed: TimeInterval) {
        guard state == .active else { return }
        recorder.pause(at: elapsed)
        self.elapsed = max(0, elapsed)
        liveMeasurement = nil
        state = .paused
    }

    /// A packet must project strictly after the frozen elapsed time to record
    /// after Resume. A confirmed restart can also restart the scale's counter.
    mutating func resume(latestSampleNumber: UInt16? = nil, streamRestarted: Bool = false) {
        guard state == .paused else { return }
        resumeCutoff = elapsed
        lastAcceptedSampleElapsed = nil
        if streamRestarted {
            self.latestSampleNumber = latestSampleNumber
        } else if let latestSampleNumber,
                  Self.followsInStream(latestSampleNumber, self.latestSampleNumber) {
            self.latestSampleNumber = latestSampleNumber
        }
        isGapInterrupted = false
        state = .active
    }

    mutating func discard() {
        state = .finished
        liveMeasurement = nil
    }

    /// Closes any open effort and returns a measured session with one step per
    /// effort. Returns nil for an empty session so the caller can discard it.
    mutating func finish(
        at elapsed: TimeInterval,
        endDate: Date = Date()
    ) -> WorkoutSessionRecord? {
        guard state == .active || state == .paused, elapsed.isFinite else { return nil }
        recorder.pause(at: elapsed)
        self.elapsed = max(0, elapsed)

        let detectedEfforts = recorder.recordedEfforts(stepID: Self.recorderStepID)
        guard !detectedEfforts.isEmpty else {
            // Nothing savable yet. Leave the session where it was and keep the
            // last accepted sample so the "Keep training" action on the
            // empty-finish alert can continue the live session unchanged.
            return nil
        }

        var steps: [WorkoutStepMeasurement] = []
        var stepTitles: [String] = []
        for (index, effort) in detectedEfforts.enumerated() {
            steps.append(
                WorkoutStepMeasurement(
                    stepID: "\(Self.recorderStepID)-\(index + 1)",
                    plannedActiveDuration: 0,
                    intervals: [effort.interval],
                    peakLoadKGF: effort.peakLoadKGF,
                    sampleCount: effort.sampleCount,
                    status: .measured,
                    // Scale-only effort: no hand, grip or prescription is known.
                    isGeneralActivity: true
                )
            )
            stepTitles.append("Effort \(index + 1)")
        }

        // A wall clock rollback can leave less wall time than we observed.
        let latestStartDate = endDate.addingTimeInterval(-self.elapsed)
        let session = WorkoutSessionRecord(
            id: UUID(),
            planID: Self.planID,
            planTitle: Self.planTitle,
            recordedAt: endDate,
            startDate: min(startDate ?? endDate, latestStartDate),
            endDate: endDate,
            motherboardIdentifier: sensorIdentifier,
            batteryValue: sensorBatteryValue,
            steps: steps,
            stepTitles: stepTitles,
            forceSensorProfile: forceSensorProfile,
            initialWeight: .sensor,
            edgeDepthMM: edgeDepthMM
        )
        state = .finished
        liveMeasurement = nil
        return session
    }

    // MARK: - Live statistics

    var loadedDuration: TimeInterval { recorder.currentLoadedDuration }
    var peakLoadKGF: Double? { recorder.currentPeakLoadKGF }

    /// Includes the in-progress effort alongside released efforts so the live
    /// snapshot shows current statistics without dropping a released interval.
    var efforts: [FreeformEffort] {
        recorder.recordedEfforts(stepID: Self.recorderStepID, includeCurrent: true)
            .enumerated().map { index, effort in
                FreeformEffort(
                    id: "\(Self.recorderStepID)-\(index + 1)",
                    duration: effort.duration,
                    peakLoadKGF: effort.peakLoadKGF,
                    sampleCount: effort.sampleCount
                )
            }
    }
}
