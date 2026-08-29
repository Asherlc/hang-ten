package com.hangten.android.health

import android.content.Context
import android.content.SharedPreferences
import androidx.health.connect.client.HealthConnectClient
import androidx.health.connect.client.records.ExerciseSessionRecord
import androidx.health.connect.client.records.metadata.DataOrigin
import androidx.health.connect.client.records.metadata.Metadata
import androidx.health.connect.client.request.ReadRecordsRequest
import androidx.health.connect.client.time.TimeRangeFilter
import com.hangten.android.workout.CompletedSession
import java.security.MessageDigest
import java.time.Instant
import java.time.ZoneOffset

enum class HealthAuthorizationState {
    Unavailable,
    NotDetermined,
    Denied,
    Authorized,
}

object HealthConnectPermissions {
    const val EXERCISE_READ = "android.permission.health.READ_EXERCISE"
    const val EXERCISE_WRITE = "android.permission.health.WRITE_EXERCISE"
    val required: Set<String> = setOf(EXERCISE_READ, EXERCISE_WRITE)
}

data class HealthWorkoutSegment(
    val id: String,
    val title: String,
    val phase: String,
    val durationSeconds: Float,
)

data class CompletedHealthWorkout(
    val session: CompletedSession,
    val segments: List<HealthWorkoutSegment>,
)

data class HangTenHealthWorkout(
    val remoteId: String,
    val clientRecordId: String,
    val planId: String,
    val boardId: String?,
    val planTitle: String,
    val startTime: Instant,
    val endTime: Instant,
)

data class HealthConnectRecord(
    val id: String = "",
    val clientRecordId: String,
    val clientRecordVersion: Long,
    val title: String?,
    val notes: String?,
    val startTime: Instant,
    val endTime: Instant,
    val exerciseType: ExerciseType,
) {
    sealed interface ExerciseType {
        data object StrengthTraining : ExerciseType
        data class Other(val sdkValue: Int) : ExerciseType
    }
}

/** SDK-independent read request used to make origin scoping and paging testable. */
data class ExerciseSessionReadRequest(
    val dataOriginPackageName: String,
    val pageToken: String?,
)

data class ExerciseSessionPage(
    val records: List<HealthConnectRecord>,
    val nextPageToken: String?,
)

interface HealthConnectSdkClient {
    val available: Boolean
    suspend fun grantedPermissions(): Set<String>
    suspend fun insert(record: HealthConnectRecord): String
    suspend fun readExerciseSessions(request: ExerciseSessionReadRequest): ExerciseSessionPage
}

interface HealthAuthorizationMemory {
    val requested: Boolean
    fun markRequested()
}

class InMemoryHealthAuthorizationMemory(
    requested: Boolean = false,
) : HealthAuthorizationMemory {
    override var requested: Boolean = requested
        private set

    override fun markRequested() {
        requested = true
    }
}

class SharedPreferencesHealthAuthorizationMemory(
    context: Context,
) : HealthAuthorizationMemory {
    private val preferences: SharedPreferences = context.getSharedPreferences(PREFERENCES_NAME, Context.MODE_PRIVATE)

    override val requested: Boolean
        get() = preferences.getBoolean(REQUESTED_KEY, false)

    override fun markRequested() {
        preferences.edit().putBoolean(REQUESTED_KEY, true).apply()
    }

    private companion object {
        const val PREFERENCES_NAME = "hang_ten_health_connect"
        const val REQUESTED_KEY = "health_connect_authorization_requested.v1"
    }
}

/**
 * A small portable boundary around the Health Connect SDK. The actual SDK client is isolated here
 * so the app's permission, write, and history behavior can be exercised with deterministic fakes.
 */
interface HealthConnectGateway {
    val available: Boolean
    suspend fun grantedPermissions(): Set<String>
    suspend fun insert(record: HealthConnectRecord): String
    suspend fun readRecords(): List<HealthConnectRecord>
}

interface WorkoutHealthStore {
    fun requestAuthorization(): Set<String>
    suspend fun completeAuthorizationRequest(): HealthAuthorizationState
    suspend fun refreshAuthorization(): HealthAuthorizationState
    suspend fun saveCompletedWorkout(workout: CompletedHealthWorkout): Result<HangTenHealthWorkout>
    suspend fun fetchHangTenWorkouts(): Result<List<HangTenHealthWorkout>>
}

class HealthConnectService(
    private val gateway: HealthConnectGateway,
    private val authorizationMemory: HealthAuthorizationMemory,
) : WorkoutHealthStore {
    override fun requestAuthorization(): Set<String> {
        if (!gateway.available) return emptySet()
        return HealthConnectPermissions.required
    }

    override suspend fun completeAuthorizationRequest(): HealthAuthorizationState {
        authorizationMemory.markRequested()
        return refreshAuthorization()
    }

    override suspend fun refreshAuthorization(): HealthAuthorizationState = when {
        !gateway.available -> HealthAuthorizationState.Unavailable
        gateway.grantedPermissions().containsAll(HealthConnectPermissions.required) -> HealthAuthorizationState.Authorized
        authorizationMemory.requested -> HealthAuthorizationState.Denied
        else -> HealthAuthorizationState.NotDetermined
    }

    override suspend fun saveCompletedWorkout(workout: CompletedHealthWorkout): Result<HangTenHealthWorkout> = runCatching {
        check(refreshAuthorization() == HealthAuthorizationState.Authorized) {
            "Health Connect exercise permission is not authorized"
        }
        val record = workout.toHealthConnectRecord()
        val remoteId = gateway.insert(record)
        record.toHangTenHealthWorkout(remoteId)
    }

    override suspend fun fetchHangTenWorkouts(): Result<List<HangTenHealthWorkout>> = runCatching {
        check(refreshAuthorization() == HealthAuthorizationState.Authorized) {
            "Health Connect exercise permission is not authorized"
        }
        gateway.readRecords().mapNotNull { record -> record.toHangTenHealthWorkoutOrNull() }
            .sortedByDescending { it.endTime }
    }
}

class AndroidHealthConnectGateway internal constructor(
    private val appPackageName: String,
    private val sdkClient: HealthConnectSdkClient,
) : HealthConnectGateway {
    constructor(context: Context) : this(
        appPackageName = context.applicationContext.packageName,
        sdkClient = AndroidXHealthConnectSdkClient(context.applicationContext),
    )

    override val available: Boolean
        get() = sdkClient.available

    override suspend fun grantedPermissions(): Set<String> = sdkClient.grantedPermissions()

    override suspend fun insert(record: HealthConnectRecord): String = sdkClient.insert(record)

    override suspend fun readRecords(): List<HealthConnectRecord> {
        val allRecords = mutableListOf<HealthConnectRecord>()
        var pageToken: String? = null
        do {
            val page = sdkClient.readExerciseSessions(
                ExerciseSessionReadRequest(
                    dataOriginPackageName = appPackageName,
                    pageToken = pageToken,
                ),
            )
            allRecords += page.records
            pageToken = page.nextPageToken
        } while (pageToken != null)
        return allRecords
    }
}

private class AndroidXHealthConnectSdkClient(
    private val appContext: Context,
) : HealthConnectSdkClient {
    private val client: HealthConnectClient by lazy { HealthConnectClient.getOrCreate(appContext) }

    override val available: Boolean
        get() = HealthConnectClient.getSdkStatus(appContext) == HealthConnectClient.SDK_AVAILABLE

    override suspend fun grantedPermissions(): Set<String> = client.permissionController.getGrantedPermissions()

    override suspend fun insert(record: HealthConnectRecord): String =
        client.insertRecords(listOf(record.toExerciseSessionRecord())).recordIdsList.single()

    override suspend fun readExerciseSessions(request: ExerciseSessionReadRequest): ExerciseSessionPage {
        val response = client.readRecords(
            ReadRecordsRequest<ExerciseSessionRecord>(
                timeRangeFilter = TimeRangeFilter.after(Instant.EPOCH),
                dataOriginFilter = setOf(DataOrigin(request.dataOriginPackageName)),
                pageToken = request.pageToken,
            ),
        )
        return ExerciseSessionPage(
            records = response.records.map(::fromExerciseSessionRecord),
            nextPageToken = response.pageToken,
        )
    }

    private fun HealthConnectRecord.toExerciseSessionRecord(): ExerciseSessionRecord = ExerciseSessionRecord(
        startTime = startTime,
        startZoneOffset = ZoneOffset.UTC,
        endTime = endTime,
        endZoneOffset = ZoneOffset.UTC,
        metadata = Metadata.manualEntry(clientRecordId, clientRecordVersion),
        exerciseType = when (val type = exerciseType) {
            HealthConnectRecord.ExerciseType.StrengthTraining -> ExerciseSessionRecord.EXERCISE_TYPE_STRENGTH_TRAINING
            is HealthConnectRecord.ExerciseType.Other -> type.sdkValue
        },
        title = title,
        notes = notes,
    )

    private fun fromExerciseSessionRecord(record: ExerciseSessionRecord): HealthConnectRecord = HealthConnectRecord(
        id = record.metadata.id,
        clientRecordId = record.metadata.clientRecordId.orEmpty(),
        clientRecordVersion = record.metadata.clientRecordVersion,
        title = record.title,
        notes = record.notes,
        startTime = record.startTime,
        endTime = record.endTime,
        exerciseType = record.exerciseType.toHealthConnectExerciseType(),
    )

    private fun Int.toHealthConnectExerciseType(): HealthConnectRecord.ExerciseType =
        if (this == ExerciseSessionRecord.EXERCISE_TYPE_STRENGTH_TRAINING) {
            HealthConnectRecord.ExerciseType.StrengthTraining
        } else {
            HealthConnectRecord.ExerciseType.Other(this)
        }
}

private fun CompletedHealthWorkout.toHealthConnectRecord(): HealthConnectRecord {
    val end = Instant.ofEpochMilli(session.completedAtWallClockMs)
    val start = end.minusMillis(session.elapsedDurationMs)
    return HealthConnectRecord(
        clientRecordId = stableClientRecordId(session),
        clientRecordVersion = CLIENT_RECORD_VERSION,
        title = "Hang Ten · ${session.planTitle ?: session.planId}",
        notes = versionedNotes(session, segments),
        startTime = start,
        endTime = end,
        exerciseType = HealthConnectRecord.ExerciseType.StrengthTraining,
    )
}

fun stableClientRecordId(session: CompletedSession): String = MessageDigest.getInstance("SHA-256")
    .digest("hangten.health.v1|${session.planId}|${session.boardId.orEmpty()}|${session.completedAtWallClockMs}".toByteArray())
    .joinToString(separator = "") { "%02x".format(it) }

private fun versionedNotes(session: CompletedSession, segments: List<HealthWorkoutSegment>): String = buildString {
    append("{\"schema\":\"")
    append(NOTES_SCHEMA)
    append("\",\"planId\":\"")
    append(jsonString(session.planId))
    append("\",\"boardId\":\"")
    append(jsonString(session.boardId.orEmpty()))
    append("\",\"segments\":[")
    segments.forEachIndexed { index, segment ->
        if (index > 0) append(',')
        append("{\"id\":\"")
        append(jsonString(segment.id))
        append("\",\"title\":\"")
        append(jsonString(segment.title))
        append("\",\"phase\":\"")
        append(jsonString(segment.phase))
        append("\",\"durationSeconds\":")
        append(segment.durationSeconds)
        append('}')
    }
    append("]}")
}

private fun jsonString(value: String): String = buildString(value.length) {
    value.forEach { character ->
        when (character) {
            '\\' -> append("\\\\")
            '"' -> append("\\\"")
            '\n' -> append("\\n")
            '\r' -> append("\\r")
            '\t' -> append("\\t")
            else -> append(character)
        }
    }
}

private fun HealthConnectRecord.toHangTenHealthWorkout(remoteId: String): HangTenHealthWorkout = HangTenHealthWorkout(
    remoteId = remoteId,
    clientRecordId = clientRecordId,
    planId = noteField("planId") ?: error("A Hang Ten record must have a plan id"),
    boardId = noteField("boardId")?.ifBlank { null },
    planTitle = title?.removePrefix("Hang Ten · ").orEmpty(),
    startTime = startTime,
    endTime = endTime,
)

private fun HealthConnectRecord.toHangTenHealthWorkoutOrNull(): HangTenHealthWorkout? {
    if (exerciseType != HealthConnectRecord.ExerciseType.StrengthTraining) return null
    if (title?.startsWith("Hang Ten · ") != true) return null
    if (noteField("schema") != NOTES_SCHEMA || clientRecordId.isBlank()) return null
    return toHangTenHealthWorkout(id)
}

private fun HealthConnectRecord.noteField(name: String): String? = notes
    ?.let { Regex("\\\"$name\\\":\\\"((?:\\\\.|[^\\\"])*)\\\"").find(it)?.groupValues?.get(1) }
    ?.replace("\\\"", "\"")
    ?.replace("\\\\", "\\")

private const val NOTES_SCHEMA = "com.hangten.health.exercise-session.v1"
private const val CLIENT_RECORD_VERSION = 1L
