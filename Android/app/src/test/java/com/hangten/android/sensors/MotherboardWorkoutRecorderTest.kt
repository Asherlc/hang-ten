package com.hangten.android.sensors

import org.junit.Assert.assertEquals
import org.junit.Test

class MotherboardWorkoutRecorderTest {
    @Test
    fun debounceUsesHysteresisAndShortGapsMergeWithoutChangingPlannedDuration() {
        val recorder = MotherboardWorkoutRecorder(
            MotherboardDetectionConfiguration(thresholdKgf = 5.0, releaseRatio = 0.8, debounceMs = 1_000, mergeGapMs = 2_000),
        )
        recorder.consume(measurement(5.0), "step", 10_000, 1_000, isActive = true)
        recorder.consume(measurement(6.0), "step", 10_000, 2_000, isActive = true)
        recorder.consume(measurement(3.0), "step", 10_000, 3_000, isActive = true)
        recorder.consume(measurement(3.0), "step", 10_000, 4_000, isActive = true)
        recorder.consume(measurement(5.0), "step", 10_000, 5_000, isActive = true)
        recorder.consume(measurement(6.0), "step", 10_000, 6_000, isActive = true)
        recorder.endStep("step", 11_000)

        val result = recorder.finish(11_000).single()
        assertEquals(10_000, result.plannedActiveDurationMs)
        assertEquals(listOf(LoadInterval(1_000, 11_000)), result.intervals)
        assertEquals(6.0, result.peakLoadKgf!!, 0.0001)
        assertEquals(6, result.sampleCount)
    }

    @Test
    fun collectorCapsPersistedMeasurementsAtTwentyThousandAndMarksTruncation() {
        val collector = MeasuredWorkoutCollector()
        repeat(20_001) { index -> collector.append(measurement(index.toDouble(), index.toLong())) }

        val completed = collector.complete()
        assertEquals(20_000, completed.measurements.size)
        assertEquals(0L, completed.measurements.first().timestampMs)
        assertEquals(19_999L, completed.measurements.last().timestampMs)
        assertEquals(true, completed.truncated)
    }

    private fun measurement(load: Double, timestampMs: Long = 0) = MotherboardMeasurement(
        timestampMs = timestampMs,
        sampleNumber = 1u,
        batteryValue = 90u,
        rawAdcValues = listOf(0, 0, 0, 0),
        sensorLoadsKgf = listOf(load, 0.0, 0.0, 0.0),
        aggregateLoadKgf = load,
    )
}
