package com.hangten.android.health

import java.time.Instant
import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertEquals
import org.junit.Test

class AndroidHealthConnectGatewayTest {
    @Test
    fun readsOnlyThisAppsDataOriginAcrossEveryPageAndPreservesExerciseType() = runTest {
        val client = RecordingSdkClient(
            pages = mapOf(
                null to ExerciseSessionPage(
                    records = listOf(record("first", HealthConnectRecord.ExerciseType.StrengthTraining)),
                    nextPageToken = "page-2",
                ),
                "page-2" to ExerciseSessionPage(
                    records = listOf(record("second", HealthConnectRecord.ExerciseType.Other(0))),
                    nextPageToken = null,
                ),
            ),
        )
        val gateway = AndroidHealthConnectGateway("com.hangten.training", client)

        val records = gateway.readRecords()

        assertEquals(listOf("first", "second"), records.map { it.id })
        assertEquals(
            listOf(
                ExerciseSessionReadRequest("com.hangten.training", null),
                ExerciseSessionReadRequest("com.hangten.training", "page-2"),
            ),
            client.readRequests,
        )
        assertEquals(HealthConnectRecord.ExerciseType.Other(0), records.last().exerciseType)
    }

    private fun record(id: String, type: HealthConnectRecord.ExerciseType) = HealthConnectRecord(
        id = id,
        clientRecordId = id,
        clientRecordVersion = 1,
        title = "Hang Ten · Fixture",
        notes = "{\"schema\":\"com.hangten.health.exercise-session.v1\",\"planId\":\"fixture\",\"boardId\":\"fixture\",\"segments\":[]}",
        startTime = Instant.ofEpochMilli(1_700_000_000_000),
        endTime = Instant.ofEpochMilli(1_700_000_030_000),
        exerciseType = type,
    )
}

private class RecordingSdkClient(
    private val pages: Map<String?, ExerciseSessionPage>,
) : HealthConnectSdkClient {
    val readRequests = mutableListOf<ExerciseSessionReadRequest>()

    override val available: Boolean = true

    override suspend fun grantedPermissions(): Set<String> = HealthConnectPermissions.required

    override suspend fun insert(record: HealthConnectRecord): String = record.id

    override suspend fun readExerciseSessions(request: ExerciseSessionReadRequest): ExerciseSessionPage {
        readRequests += request
        return requireNotNull(pages[request.pageToken])
    }
}
