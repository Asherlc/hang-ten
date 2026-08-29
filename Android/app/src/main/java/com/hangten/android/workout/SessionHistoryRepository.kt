package com.hangten.android.workout

import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringPreferencesKey
import com.hangten.android.sensors.ForceSensorProfile
import com.hangten.android.sensors.LoadInterval
import com.hangten.android.sensors.MeasurementStatus
import com.hangten.android.sensors.MotherboardMeasurement
import com.hangten.android.sensors.SensorWorkoutActivity
import com.hangten.android.sensors.WorkoutStepMeasurement
import java.util.Base64
import kotlinx.coroutines.flow.first

class SessionHistoryRepository(
    private val dataStore: DataStore<Preferences>,
) : com.hangten.android.health.WorkoutHistory {
    override suspend fun record(completedSession: CompletedSession) {
        dataStore.edit { preferences ->
            val sessions = decode(preferences[HISTORY_KEY]).toMutableList()
            sessions += completedSession
            preferences[HISTORY_KEY] = encode(
                sessions.sortedByDescending { it.completedAtWallClockMs }.take(MAX_HISTORY_ENTRIES),
            )
        }
    }

    override suspend fun completedSessions(): List<CompletedSession> = decode(dataStore.data.first()[HISTORY_KEY])

    private fun encode(sessions: List<CompletedSession>): String = sessions.joinToString("\n") { session ->
        listOf(
            planIdEncoder.encodeToString(session.planId.toByteArray(Charsets.UTF_8)),
            session.completedAtWallClockMs.toString(),
            session.elapsedDurationMs.toString(),
            planIdEncoder.encodeToString(session.boardId.orEmpty().toByteArray(Charsets.UTF_8)),
            planIdEncoder.encodeToString(session.planTitle.orEmpty().toByteArray(Charsets.UTF_8)),
            planIdEncoder.encodeToString(session.sensorActivity?.let(::encodeSensorActivity).orEmpty().toByteArray(Charsets.UTF_8)),
        ).joinToString(",")
    }

    private fun decode(serialized: String?): List<CompletedSession> = serialized.orEmpty().lineSequence()
        .mapNotNull(::decodeSession)
        .sortedByDescending { it.completedAtWallClockMs }
        .take(MAX_HISTORY_ENTRIES)
        .toList()

    private fun decodeSession(encoded: String): CompletedSession? = runCatching {
        val fields = encoded.split(',')
        require(fields.size == 3 || fields.size == 5 || fields.size == 6)
        CompletedSession(
            planId = String(planIdDecoder.decode(fields[0]), Charsets.UTF_8),
            completedAtWallClockMs = fields[1].toLong(),
            elapsedDurationMs = fields[2].toLong().also(::requireNonNegative),
            boardId = fields.getOrNull(3)?.let { String(planIdDecoder.decode(it), Charsets.UTF_8).ifBlank { null } },
            planTitle = fields.getOrNull(4)?.let { String(planIdDecoder.decode(it), Charsets.UTF_8).ifBlank { null } },
            sensorActivity = fields.getOrNull(5)
                ?.let { String(planIdDecoder.decode(it), Charsets.UTF_8) }
                ?.takeIf(String::isNotBlank)
                ?.let(::decodeSensorActivity),
        )
    }.getOrNull()

    private fun requireNonNegative(value: Long): Long = value.also { require(it >= 0L) }

    private fun encodeSensorActivity(activity: SensorWorkoutActivity): String = listOf(
        activity.profile.name,
        activity.measurementsTruncated.toString(),
        activity.measurements.joinToString(";") { measurement -> listOf(
            measurement.timestampMs, measurement.sampleNumber, measurement.batteryValue,
            measurement.rawAdcValues.joinToString(":"), measurement.sensorLoadsKgf.joinToString(":"), measurement.aggregateLoadKgf,
        ).joinToString("|") },
        activity.steps.joinToString(";") { step -> listOf(
            planIdEncoder.encodeToString(step.stepId.toByteArray()), step.plannedActiveDurationMs,
            step.intervals.joinToString(":") { "${it.startMs}/${it.endMs}" }, step.peakLoadKgf ?: "", step.sampleCount, step.status.name,
        ).joinToString("|") },
    ).joinToString("^")

    private fun decodeSensorActivity(encoded: String): SensorWorkoutActivity? = runCatching {
        val fields = encoded.split("^", limit = 4)
        require(fields.size == 4)
        SensorWorkoutActivity(
            profile = ForceSensorProfile.valueOf(fields[0]),
            measurements = if (fields[2].isEmpty()) emptyList() else fields[2].split(";").map(::decodeMeasurement),
            measurementsTruncated = fields[1].toBooleanStrict(),
            steps = if (fields[3].isEmpty()) emptyList() else fields[3].split(";").map(::decodeStep),
        )
    }.getOrNull()

    private fun decodeMeasurement(encoded: String): MotherboardMeasurement {
        val fields = encoded.split("|")
        require(fields.size == 6)
        return MotherboardMeasurement(
            timestampMs = fields[0].toLong(), sampleNumber = fields[1].toUShort(), batteryValue = fields[2].toUShort(),
            rawAdcValues = fields[3].takeIf(String::isNotEmpty).orEmpty().split(":").filter(String::isNotEmpty).map(String::toInt),
            sensorLoadsKgf = fields[4].takeIf(String::isNotEmpty).orEmpty().split(":").filter(String::isNotEmpty).map(String::toDouble),
            aggregateLoadKgf = fields[5].toDouble(),
        )
    }

    private fun decodeStep(encoded: String): WorkoutStepMeasurement {
        val fields = encoded.split("|")
        require(fields.size == 6)
        return WorkoutStepMeasurement(
            stepId = String(planIdDecoder.decode(fields[0]), Charsets.UTF_8), plannedActiveDurationMs = fields[1].toLong(),
            intervals = fields[2].takeIf(String::isNotEmpty).orEmpty().split(":").filter(String::isNotEmpty).map { item ->
                val interval = item.split("/"); LoadInterval(interval[0].toLong(), interval[1].toLong())
            }, peakLoadKgf = fields[3].takeIf(String::isNotEmpty)?.toDouble(), sampleCount = fields[4].toInt(), status = MeasurementStatus.valueOf(fields[5]),
        )
    }

    private companion object {
        val HISTORY_KEY = stringPreferencesKey("completed_session_history")
        val planIdEncoder: Base64.Encoder = Base64.getUrlEncoder().withoutPadding()
        val planIdDecoder: Base64.Decoder = Base64.getUrlDecoder()
        const val MAX_HISTORY_ENTRIES = 20
    }
}
