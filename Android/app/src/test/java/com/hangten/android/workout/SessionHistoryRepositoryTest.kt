package com.hangten.android.workout

import androidx.datastore.preferences.core.PreferenceDataStoreFactory
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringPreferencesKey
import com.hangten.android.sensors.ForceSensorProfile
import com.hangten.android.sensors.MotherboardMeasurement
import com.hangten.android.sensors.SensorWorkoutActivity
import java.io.File
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancelAndJoin
import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertEquals
import org.junit.Test

class SessionHistoryRepositoryTest {
    @Test
    fun completedSessionIsRestoredFromDataStore() = runTest {
        val file = File.createTempFile("session-history", ".preferences_pb").also(File::delete)
        val completed = CompletedSession(
            planId = "max-hangs",
            completedAtWallClockMs = 1_725_000_000_000,
            elapsedDurationMs = 900_000,
        )
        val writerScope = CoroutineScope(SupervisorJob() + Dispatchers.IO)
        val readerScope = CoroutineScope(SupervisorJob() + Dispatchers.IO)

        try {
            SessionHistoryRepository(
                PreferenceDataStoreFactory.create(scope = writerScope, produceFile = { file }),
            ).record(completed)
            writerScope.coroutineContext[Job]?.cancelAndJoin()

            assertEquals(
                listOf(completed),
                SessionHistoryRepository(
                    PreferenceDataStoreFactory.create(scope = readerScope, produceFile = { file }),
                ).completedSessions(),
            )
        } finally {
            writerScope.coroutineContext[Job]?.cancelAndJoin()
            readerScope.coroutineContext[Job]?.cancelAndJoin()
            file.delete()
        }
    }

    @Test
    fun measuredSensorActivityIsPersistedWithTheCompletedSession() = runTest {
        val file = File.createTempFile("sensor-session-history", ".preferences_pb").also(File::delete)
        val expected = CompletedSession(
            planId = "max-hangs", completedAtWallClockMs = 1, elapsedDurationMs = 2,
            sensorActivity = SensorWorkoutActivity(
                ForceSensorProfile.Progressor,
                listOf(MotherboardMeasurement(3, 1u, 0u, emptyList(), emptyList(), 12.5)),
                measurementsTruncated = false,
                steps = emptyList(),
            ),
        )
        val scope = CoroutineScope(SupervisorJob() + Dispatchers.IO)
        try {
            SessionHistoryRepository(PreferenceDataStoreFactory.create(scope = scope, produceFile = { file })).record(expected)
            scope.coroutineContext[Job]?.cancelAndJoin()
            val readerScope = CoroutineScope(SupervisorJob() + Dispatchers.IO)
            try {
                val restored = SessionHistoryRepository(PreferenceDataStoreFactory.create(scope = readerScope, produceFile = { file })).completedSessions()
                assertEquals(listOf(expected), restored)
            } finally { readerScope.coroutineContext[Job]?.cancelAndJoin() }
        } finally { scope.coroutineContext[Job]?.cancelAndJoin(); file.delete() }
    }

    @Test
    fun recordKeepsOnlyTheTwentyNewestCompletedSessions() = runTest {
        val file = File.createTempFile("session-history", ".preferences_pb").also(File::delete)
        val dataStore = PreferenceDataStoreFactory.create(
            scope = backgroundScope,
            produceFile = { file },
        )
        val repository = SessionHistoryRepository(dataStore)

        (1L..21L).forEach { completedAt ->
            repository.record(
                CompletedSession(
                    planId = "plan-$completedAt",
                    completedAtWallClockMs = completedAt,
                    elapsedDurationMs = completedAt * 1_000,
                ),
            )
        }

        assertEquals((21L downTo 2L).toList(), repository.completedSessions().map { it.completedAtWallClockMs })
        file.delete()
    }

    @Test
    fun malformedPersistedEntriesAreIgnoredWhileValidHistoryIsSortedNewestFirst() = runTest {
        val file = File.createTempFile("session-history", ".preferences_pb").also(File::delete)
        val dataStore = PreferenceDataStoreFactory.create(
            scope = backgroundScope,
            produceFile = { file },
        )
        dataStore.edit { preferences ->
            preferences[stringPreferencesKey("completed_session_history")] = listOf(
                "ZWFybHk,10,100",
                "not-a-record",
                "bGF0ZXI,20,200",
                "dGhyZWU,not-a-clock,300",
                "bmVnYXRpdmU,30,-1",
            ).joinToString("\n")
        }

        assertEquals(
            listOf(
                CompletedSession(planId = "later", completedAtWallClockMs = 20, elapsedDurationMs = 200),
                CompletedSession(planId = "early", completedAtWallClockMs = 10, elapsedDurationMs = 100),
            ),
            SessionHistoryRepository(dataStore).completedSessions(),
        )
        file.delete()
    }
}
