package com.hangten.android.health

import com.hangten.android.workout.CompletedSession
import java.time.Instant
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.test.UnconfinedTestDispatcher
import kotlinx.coroutines.test.advanceUntilIdle
import kotlinx.coroutines.test.resetMain
import kotlinx.coroutines.test.runTest
import kotlinx.coroutines.test.setMain
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class HealthConnectServiceTest {
    @Test
    fun authorizationIsRequestedOnlyAfterAnExplicitSettingsAction() = runTest {
        val gateway = FakeHealthConnectGateway()
        val service = HealthConnectService(gateway, InMemoryHealthAuthorizationMemory())

        assertEquals(HealthAuthorizationState.NotDetermined, service.refreshAuthorization())
        assertTrue(service.requestAuthorization().contains(HealthConnectPermissions.EXERCISE_WRITE))
        assertEquals(HealthAuthorizationState.NotDetermined, service.refreshAuthorization())

        gateway.grantedPermissions = HealthConnectPermissions.required
        assertEquals(HealthAuthorizationState.Authorized, service.completeAuthorizationRequest())
    }

    @OptIn(ExperimentalCoroutinesApi::class)
    @Test
    fun authorizationRequestFailureKeepsAUserVisibleErrorAndReportsFailureToTheUi() = runTest {
        Dispatchers.setMain(UnconfinedTestDispatcher(testScheduler))
        try {
            val viewModel = HealthViewModel(FailingAuthorizationStore(), FakeSessionHistory())
            var completion: Result<HealthAuthorizationState>? = null

            viewModel.authorizationRequestFinished { completion = it }
            advanceUntilIdle()

            assertTrue(requireNotNull(completion).isFailure)
            assertEquals(HealthAuthorizationState.NotDetermined, viewModel.state.value.authorization)
            assertEquals("Health Connect provider failed", viewModel.state.value.error)
        } finally {
            Dispatchers.resetMain()
        }
    }

    @OptIn(ExperimentalCoroutinesApi::class)
    @Test
    fun authorizationRequestCancellationLeavesUiStableAndDoesNotCallTheOutcomeCallback() = runTest {
        Dispatchers.setMain(UnconfinedTestDispatcher(testScheduler))
        try {
            val viewModel = HealthViewModel(CancellingAuthorizationStore(), FakeSessionHistory())
            val initial = viewModel.state.value
            var callbackCount = 0

            viewModel.authorizationRequestFinished { callbackCount += 1 }
            advanceUntilIdle()

            assertEquals(0, callbackCount)
            assertEquals(initial, viewModel.state.value)
        } finally {
            Dispatchers.resetMain()
        }
    }

    @Test
    fun completedWorkoutUsesStableClientRecordIdAndVersionedActivityNotes() = runTest {
        val gateway = FakeHealthConnectGateway(grantedPermissions = HealthConnectPermissions.required)
        val service = HealthConnectService(gateway, InMemoryHealthAuthorizationMemory())
        val workout = fixtureWorkout()

        service.saveCompletedWorkout(workout).getOrThrow()
        service.saveCompletedWorkout(workout).getOrThrow()

        assertEquals(2, gateway.insertedRecords.size)
        val record = gateway.insertedRecords.first()
        assertEquals("3480499de0ba087c6aa9ede55aa8521612f71e09a170e2cbd989971804f40e85", record.clientRecordId)
        assertEquals(1L, record.clientRecordVersion)
        assertEquals(HealthConnectRecord.ExerciseType.StrengthTraining, record.exerciseType)
        assertEquals("Hang Ten · Repeaters", record.title)
        assertEquals(
            "{\"schema\":\"com.hangten.health.exercise-session.v1\",\"planId\":\"repeaters\",\"boardId\":\"rock-prodigy\",\"segments\":[{\"id\":\"warmup\",\"title\":\"Warm up\",\"phase\":\"warmup\",\"durationSeconds\":30.0},{\"id\":\"hang\",\"title\":\"Seven seconds\",\"phase\":\"hang\",\"durationSeconds\":7.0}]}",
            record.notes,
        )
        assertEquals(record.clientRecordId, gateway.insertedRecords.last().clientRecordId)
    }

    @Test
    fun deniedHealthConnectLeavesCompletedWorkoutInLocalFallback() = runTest {
        val gateway = FakeHealthConnectGateway()
        val history = FakeSessionHistory()
        val viewModel = HealthViewModel(
            healthStore = HealthConnectService(gateway, InMemoryHealthAuthorizationMemory(requested = true)),
            history = history,
        )

        viewModel.recordCompletion(fixtureWorkout())

        assertEquals(listOf(fixtureWorkout().session), history.recorded)
        assertTrue(gateway.insertedRecords.isEmpty())
        assertEquals(HealthAuthorizationState.Denied, viewModel.state.value.authorization)
        assertEquals(listOf(fixtureWorkout().session), viewModel.state.value.sessions)
    }

    @Test
    fun failedHealthConnectWriteRetainsLocalCompletionAndPublishesSyncError() = runTest {
        val gateway = FakeHealthConnectGateway(
            grantedPermissions = HealthConnectPermissions.required,
            insertFailure = IllegalStateException("Health Connect write failed"),
        )
        val history = FakeSessionHistory()
        val viewModel = HealthViewModel(HealthConnectService(gateway, InMemoryHealthAuthorizationMemory()), history)

        viewModel.recordCompletion(fixtureWorkout())

        assertEquals(listOf(fixtureWorkout().session), history.recorded)
        assertEquals("Health Connect write failed", viewModel.state.value.error)
        assertTrue(viewModel.state.value.isLocalFallbackOnly)
    }

    @Test
    fun reconciliationDeduplicatesOwnHealthRecordAndKeepsUnmatchedLocalCompletion() = runTest {
        val local = fixtureWorkout().session
        val otherLocal = local.copy(planId = "max-hangs", completedAtWallClockMs = 1_700_000_060_000)
        val remote = HealthConnectRecord(
            id = "remote-repeaters",
            clientRecordId = "3480499de0ba087c6aa9ede55aa8521612f71e09a170e2cbd989971804f40e85",
            clientRecordVersion = 1,
            title = "Hang Ten · Repeaters",
            notes = "{\"schema\":\"com.hangten.health.exercise-session.v1\",\"planId\":\"repeaters\",\"boardId\":\"rock-prodigy\",\"segments\":[]}",
            startTime = Instant.ofEpochMilli(1_700_000_000_000),
            endTime = Instant.ofEpochMilli(1_700_000_045_000),
            exerciseType = HealthConnectRecord.ExerciseType.StrengthTraining,
        )
        val gateway = FakeHealthConnectGateway(
            grantedPermissions = HealthConnectPermissions.required,
            records = mutableListOf(remote),
        )
        val history = FakeSessionHistory(listOf(local, otherLocal))
        val viewModel = HealthViewModel(HealthConnectService(gateway, InMemoryHealthAuthorizationMemory()), history)

        viewModel.reconcileHistory()

        assertEquals(listOf(otherLocal, local), viewModel.state.value.sessions)
        assertEquals(HealthHistorySource.HealthConnect, viewModel.state.value.historySource)
        assertFalse(viewModel.state.value.isLocalFallbackOnly)
    }

    @Test
    fun reconciliationRejectsMatchingNonStrengthRecordsAndDuplicateRemoteIdentities() = runTest {
        val remoteID = "3480499de0ba087c6aa9ede55aa8521612f71e09a170e2cbd989971804f40e85"
        val notes = "{\"schema\":\"com.hangten.health.exercise-session.v1\",\"planId\":\"repeaters\",\"boardId\":\"rock-prodigy\",\"segments\":[]}"
        val accepted = HealthConnectRecord(
            id = "accepted",
            clientRecordId = remoteID,
            clientRecordVersion = 1,
            title = "Hang Ten · Repeaters",
            notes = notes,
            startTime = Instant.ofEpochMilli(1_700_000_000_000),
            endTime = Instant.ofEpochMilli(1_700_000_045_000),
            exerciseType = HealthConnectRecord.ExerciseType.StrengthTraining,
        )
        val nonStrength = accepted.copy(id = "not-strength", clientRecordId = "non-strength", exerciseType = HealthConnectRecord.ExerciseType.Other(0))
        val duplicate = accepted.copy(id = "duplicate")
        val gateway = FakeHealthConnectGateway(
            grantedPermissions = HealthConnectPermissions.required,
            records = mutableListOf(accepted, nonStrength, duplicate),
        )
        val viewModel = HealthViewModel(
            HealthConnectService(gateway, InMemoryHealthAuthorizationMemory()),
            FakeSessionHistory(),
        )

        viewModel.reconcileHistory()

        assertEquals(listOf("repeaters"), viewModel.state.value.sessions.map { it.planId })
    }

    private fun fixtureWorkout(): CompletedHealthWorkout = CompletedHealthWorkout(
        session = CompletedSession(
            planId = "repeaters",
            completedAtWallClockMs = 1_700_000_045_000,
            elapsedDurationMs = 45_000,
            boardId = "rock-prodigy",
            planTitle = "Repeaters",
        ),
        segments = listOf(
            HealthWorkoutSegment("warmup", "Warm up", "warmup", 30f),
            HealthWorkoutSegment("hang", "Seven seconds", "hang", 7f),
        ),
    )
}

private class FakeHealthConnectGateway(
    var grantedPermissions: Set<String> = emptySet(),
    var records: MutableList<HealthConnectRecord> = mutableListOf(),
    override var available: Boolean = true,
    private val insertFailure: Throwable? = null,
) : HealthConnectGateway {
    val insertedRecords = mutableListOf<HealthConnectRecord>()

    override suspend fun insert(record: HealthConnectRecord): String {
        insertFailure?.let { throw it }
        insertedRecords += record
        records += record.copy(id = "remote-${insertedRecords.size}")
        return "remote-${insertedRecords.size}"
    }

    override suspend fun grantedPermissions(): Set<String> = grantedPermissions

    override suspend fun readRecords(): List<HealthConnectRecord> = records.toList()
}

private class FakeSessionHistory(
    initial: List<CompletedSession> = emptyList(),
) : WorkoutHistory {
    val recorded = initial.toMutableList()

    override suspend fun record(completedSession: CompletedSession) {
        recorded += completedSession
    }

    override suspend fun completedSessions(): List<CompletedSession> = recorded.sortedByDescending { it.completedAtWallClockMs }
}

private class FailingAuthorizationStore : WorkoutHealthStore {
    override fun requestAuthorization(): Set<String> = emptySet()

    override suspend fun completeAuthorizationRequest(): HealthAuthorizationState =
        throw IllegalStateException("Health Connect provider failed")

    override suspend fun refreshAuthorization(): HealthAuthorizationState = HealthAuthorizationState.NotDetermined

    override suspend fun saveCompletedWorkout(workout: CompletedHealthWorkout): Result<HangTenHealthWorkout> =
        error("Not used by this test")

    override suspend fun fetchHangTenWorkouts(): Result<List<HangTenHealthWorkout>> =
        error("Not used by this test")
}

private class CancellingAuthorizationStore : WorkoutHealthStore {
    override fun requestAuthorization(): Set<String> = emptySet()

    override suspend fun completeAuthorizationRequest(): HealthAuthorizationState =
        throw CancellationException("Permission request cancelled")

    override suspend fun refreshAuthorization(): HealthAuthorizationState = HealthAuthorizationState.NotDetermined

    override suspend fun saveCompletedWorkout(workout: CompletedHealthWorkout): Result<HangTenHealthWorkout> =
        error("Not used by this test")

    override suspend fun fetchHangTenWorkouts(): Result<List<HangTenHealthWorkout>> =
        error("Not used by this test")
}
