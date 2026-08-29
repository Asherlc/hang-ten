package com.hangten.android.sensors

data class MotherboardDetectionConfiguration(
    val thresholdKgf: Double = 2.5,
    val releaseRatio: Double = 0.8,
    val debounceMs: Long = 100,
    val mergeGapMs: Long = 150,
)

data class LoadInterval(val startMs: Long, val endMs: Long) {
    val durationMs: Long get() = (endMs - startMs).coerceAtLeast(0)
}

enum class MeasurementStatus { Measured, Unmeasured, Interrupted }

data class WorkoutStepMeasurement(
    val stepId: String,
    val plannedActiveDurationMs: Long,
    val intervals: List<LoadInterval>,
    val peakLoadKgf: Double?,
    val sampleCount: Int,
    val status: MeasurementStatus,
)

data class RecordedMeasurements(
    val measurements: List<MotherboardMeasurement>,
    val truncated: Boolean,
)

data class SensorWorkoutActivity(
    val profile: ForceSensorProfile,
    val measurements: List<MotherboardMeasurement>,
    val measurementsTruncated: Boolean,
    val steps: List<WorkoutStepMeasurement>,
)

class MeasuredWorkoutCollector {
    private val measurements = ArrayList<MotherboardMeasurement>(MAXIMUM_MEASUREMENT_COUNT)
    private var truncated = false

    fun append(measurement: MotherboardMeasurement) {
        if (measurements.size < MAXIMUM_MEASUREMENT_COUNT) measurements += measurement else truncated = true
    }

    fun complete(): RecordedMeasurements = RecordedMeasurements(measurements.toList(), truncated)

    companion object { const val MAXIMUM_MEASUREMENT_COUNT = 20_000 }
}

class MotherboardWorkoutRecorder(
    private val configuration: MotherboardDetectionConfiguration = MotherboardDetectionConfiguration(),
) {
    private data class State(
        val plannedDurationMs: Long,
        val stepStartMs: Long,
        val intervals: MutableList<LoadInterval> = mutableListOf(),
        var openStartMs: Long? = null,
        var pendingStartMs: Long? = null,
        var pendingReleaseMs: Long? = null,
        var peakLoadKgf: Double? = null,
        var sampleCount: Int = 0,
        var status: MeasurementStatus = MeasurementStatus.Unmeasured,
        var permitsMerge: Boolean = true,
    ) {
        fun clipped(timeMs: Long): Long = timeMs.coerceAtMost(stepStartMs + plannedDurationMs)
    }

    private val states = linkedMapOf<String, State>()
    private var currentStepId: String? = null

    fun consume(
        measurement: MotherboardMeasurement,
        stepId: String,
        plannedActiveDurationMs: Long,
        workoutElapsedMs: Long,
        stepStartElapsedMs: Long = workoutElapsedMs,
        isActive: Boolean,
    ) {
        currentStepId = stepId
        val state = state(stepId, plannedActiveDurationMs, stepStartElapsedMs)
        if (!isActive) return
        state.sampleCount += 1
        state.peakLoadKgf = maxOf(state.peakLoadKgf ?: measurement.aggregateLoadKgf, measurement.aggregateLoadKgf)
        val time = state.clipped(workoutElapsedMs)
        val qualifying = measurement.aggregateLoadKgf >= configuration.thresholdKgf
        val released = measurement.aggregateLoadKgf < configuration.thresholdKgf * configuration.releaseRatio
        if (state.openStartMs == null) {
            if (qualifying) {
                val pending = state.pendingStartMs
                if (pending != null && time - pending >= configuration.debounceMs) open(state, pending)
                else if (pending == null) {
                    state.pendingStartMs = time
                    if (configuration.debounceMs == 0L) open(state, time)
                }
            } else state.pendingStartMs = null
        } else if (released) {
            val pending = state.pendingReleaseMs
            if (pending != null && time - pending >= configuration.debounceMs) close(state, pending)
            else if (pending == null) {
                state.pendingReleaseMs = time
                if (configuration.debounceMs == 0L) close(state, time)
            }
        } else state.pendingReleaseMs = null
    }

    fun pause(atMs: Long) {
        currentStepId?.let(states::get)?.let { state ->
            close(state, atMs)
            state.pendingStartMs = null
            state.pendingReleaseMs = null
            state.permitsMerge = false
        }
    }

    fun endStep(stepId: String, atMs: Long, status: MeasurementStatus = MeasurementStatus.Measured) {
        states[stepId]?.let { state ->
            close(state, atMs)
            state.pendingStartMs = null
            state.pendingReleaseMs = null
            state.status = status
        }
    }

    fun interrupt(stepId: String, plannedActiveDurationMs: Long, stepStartElapsedMs: Long, atMs: Long) {
        val state = state(stepId, plannedActiveDurationMs, stepStartElapsedMs)
        close(state, atMs)
        state.pendingStartMs = null
        state.pendingReleaseMs = null
        state.permitsMerge = false
        state.status = MeasurementStatus.Interrupted
    }

    fun finish(atMs: Long): List<WorkoutStepMeasurement> = states.map { (stepId, state) ->
        close(state, atMs)
        state.pendingStartMs = null
        state.pendingReleaseMs = null
        if (state.sampleCount > 0 && state.status == MeasurementStatus.Unmeasured) state.status = MeasurementStatus.Measured
        WorkoutStepMeasurement(stepId, state.plannedDurationMs, state.intervals.toList(), state.peakLoadKgf, state.sampleCount, state.status)
    }

    private fun state(stepId: String, durationMs: Long, startMs: Long): State = states.getOrPut(stepId) {
        State(durationMs.coerceAtLeast(0), startMs)
    }

    private fun open(state: State, atMs: Long) {
        val start = state.clipped(atMs)
        state.pendingStartMs = null
        state.pendingReleaseMs = null
        val previous = state.intervals.lastOrNull()
        if (state.permitsMerge && previous != null && start - previous.endMs <= configuration.mergeGapMs) {
            state.intervals.removeAt(state.intervals.lastIndex)
            state.openStartMs = previous.startMs
        } else state.openStartMs = start
        state.permitsMerge = true
    }

    private fun close(state: State, atMs: Long) {
        val start = state.openStartMs ?: return
        state.intervals += LoadInterval(start, maxOf(start, state.clipped(atMs)))
        state.openStartMs = null
        state.pendingReleaseMs = null
    }
}

class SensorWorkoutRecorder(
    private val profile: ForceSensorProfile,
    configuration: MotherboardDetectionConfiguration = MotherboardDetectionConfiguration(),
) {
    private val samples = MeasuredWorkoutCollector()
    private val intervals = MotherboardWorkoutRecorder(configuration)

    fun consume(measurement: MotherboardMeasurement, stepId: String, plannedActiveDurationMs: Long, elapsedMs: Long, stepStartMs: Long, isActive: Boolean) {
        samples.append(measurement)
        intervals.consume(measurement, stepId, plannedActiveDurationMs, elapsedMs, stepStartMs, isActive)
    }

    fun pause(elapsedMs: Long) = intervals.pause(elapsedMs)

    fun complete(elapsedMs: Long): SensorWorkoutActivity {
        val recorded = samples.complete()
        return SensorWorkoutActivity(profile, recorded.measurements, recorded.truncated, intervals.finish(elapsedMs))
    }
}
