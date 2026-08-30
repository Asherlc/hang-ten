package com.hangten.android.ui

import android.app.Activity
import androidx.activity.ComponentActivity
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.junit4.createAndroidComposeRule
import androidx.compose.ui.test.onNodeWithContentDescription
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import com.hangten.android.billing.AcknowledgementResult
import com.hangten.android.billing.PurchaseClient
import com.hangten.android.billing.PurchaseManager
import com.hangten.android.billing.PurchaseProduct
import com.hangten.android.billing.PurchaseResult
import com.hangten.android.billing.PurchaseUpdate
import com.hangten.android.billing.RestoreResult
import com.hangten.android.health.CompletedHealthWorkout
import com.hangten.android.health.HangTenHealthWorkout
import com.hangten.android.health.HealthAuthorizationState
import com.hangten.android.health.HealthConnectPermissions
import com.hangten.android.health.HealthViewModel
import com.hangten.android.health.WorkoutHealthStore
import com.hangten.android.health.WorkoutHistory
import com.hangten.android.workout.CompletedSession
import java.time.Instant
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.emptyFlow
import kotlinx.coroutines.runBlocking
import org.junit.Assert.assertEquals
import org.junit.Rule
import org.junit.Test

class HealthConnectUiTest {
    @get:Rule
    val composeRule = createAndroidComposeRule<ComponentActivity>()

    @Test
    fun connectHealthIsLaunchedOnlyByTheExplicitConnectButton() {
        val healthStore = FakeWorkoutHealthStore(HealthAuthorizationState.NotDetermined)
        val healthViewModel = HealthViewModel(healthStore, InMemoryWorkoutHistory())
        val requestedPermissions = mutableListOf<Set<String>>()
        val purchases = PurchaseManager(FakePurchaseClient())

        composeRule.setContent {
            SettingsScreen(
                audioCoach = RecordingAudioCoach(),
                purchaseManager = purchases,
                healthViewModel = healthViewModel,
                contentPadding = PaddingValues(),
                onHealthPermissionRequest = requestedPermissions::add,
            )
        }

        composeRule.onNodeWithContentDescription("Connect Health").assertIsDisplayed()
        composeRule.runOnIdle {
            assertEquals(0, healthStore.authorizationRequests)
            assertEquals(emptyList<Set<String>>(), requestedPermissions)
        }
        composeRule.onNodeWithContentDescription("Connect Health").performClick()
        composeRule.runOnIdle {
            assertEquals(1, healthStore.authorizationRequests)
            assertEquals(listOf(HealthConnectPermissions.required), requestedPermissions)
        }
        purchases.close()
    }

    @Test
    fun deniedHealthConnectRendersLocalHistoryWithoutPromptingAgain() {
        val local = completedSession("local-plan")
        val healthStore = FakeWorkoutHealthStore(HealthAuthorizationState.Denied)
        val healthViewModel = HealthViewModel(healthStore, InMemoryWorkoutHistory(listOf(local)))

        composeRule.setContent {
            HistoryScreen(healthViewModel, refreshKey = 0, contentPadding = PaddingValues())
        }

        composeRule.onNodeWithText("Showing local workout history.").assertIsDisplayed()
        composeRule.onNodeWithText("local-plan", substring = true).assertIsDisplayed()
        composeRule.runOnIdle { assertEquals(0, healthStore.authorizationRequests) }
    }

    @Test
    fun healthWriteFailureKeepsTheCompletionVisibleInLocalHistory() {
        val healthStore = FakeWorkoutHealthStore(
            authorization = HealthAuthorizationState.Authorized,
            saveFailure = IllegalStateException("Fake Health Connect write failure"),
        )
        val history = InMemoryWorkoutHistory()
        val healthViewModel = HealthViewModel(healthStore, history)

        runBlocking { healthViewModel.recordCompletion(completedWorkout("write-failure")) }
        composeRule.setContent {
            HistoryScreen(healthViewModel, refreshKey = 0, contentPadding = PaddingValues())
        }

        composeRule.onNodeWithText("Fake Health Connect write failure").assertIsDisplayed()
        composeRule.onNodeWithText("write-failure", substring = true).assertIsDisplayed()
        composeRule.runOnIdle { assertEquals(1, history.sessions.size) }
    }

    @Test
    fun reconciliationShowsOneRemoteSessionForDuplicateStableIdentity() {
        val remote = HangTenHealthWorkout(
            remoteId = "remote-1",
            clientRecordId = "stable-remote-id",
            planId = "remote-plan",
            boardId = "board",
            planTitle = "Remote plan",
            startTime = Instant.ofEpochMilli(1_700_000_000_000),
            endTime = Instant.ofEpochMilli(1_700_000_030_000),
        )
        val healthStore = FakeWorkoutHealthStore(
            authorization = HealthAuthorizationState.Authorized,
            remoteWorkouts = listOf(remote, remote.copy(remoteId = "remote-duplicate")),
        )
        val healthViewModel = HealthViewModel(healthStore, InMemoryWorkoutHistory())

        composeRule.setContent {
            HistoryScreen(healthViewModel, refreshKey = 0, contentPadding = PaddingValues())
        }

        composeRule.onNodeWithText("History reconciled with Health Connect.").assertIsDisplayed()
        composeRule.waitUntil(timeoutMillis = 5_000) {
            healthViewModel.state.value.sessions.count { it.planId == "remote-plan" } == 1
        }
        composeRule.runOnIdle { assertEquals(1, healthViewModel.state.value.sessions.size) }
    }
}

private class FakeWorkoutHealthStore(
    private val authorization: HealthAuthorizationState,
    private val remoteWorkouts: List<HangTenHealthWorkout> = emptyList(),
    private val saveFailure: Throwable? = null,
) : WorkoutHealthStore {
    var authorizationRequests = 0
        private set

    override fun requestAuthorization(): Set<String> {
        authorizationRequests += 1
        return if (authorization == HealthAuthorizationState.Unavailable) emptySet() else HealthConnectPermissions.required
    }

    override suspend fun completeAuthorizationRequest(): HealthAuthorizationState = authorization

    override suspend fun refreshAuthorization(): HealthAuthorizationState = authorization

    override suspend fun saveCompletedWorkout(workout: CompletedHealthWorkout): Result<HangTenHealthWorkout> =
        saveFailure?.let { Result.failure(it) } ?: Result.success(
            HangTenHealthWorkout(
                remoteId = "saved",
                clientRecordId = "saved-${workout.session.planId}",
                planId = workout.session.planId,
                boardId = workout.session.boardId,
                planTitle = workout.session.planTitle.orEmpty(),
                startTime = Instant.ofEpochMilli(workout.session.completedAtWallClockMs - workout.session.elapsedDurationMs),
                endTime = Instant.ofEpochMilli(workout.session.completedAtWallClockMs),
            ),
        )

    override suspend fun fetchHangTenWorkouts(): Result<List<HangTenHealthWorkout>> = Result.success(remoteWorkouts)
}

private class InMemoryWorkoutHistory(
    initial: List<CompletedSession> = emptyList(),
) : WorkoutHistory {
    val sessions = initial.toMutableList()

    override suspend fun record(completedSession: CompletedSession) {
        sessions += completedSession
    }

    override suspend fun completedSessions(): List<CompletedSession> = sessions.toList()
}

private class FakePurchaseClient : PurchaseClient {
    override val updates: Flow<PurchaseUpdate> = emptyFlow()

    override suspend fun load(id: String): PurchaseProduct? = null

    override suspend fun purchase(activity: Activity?, id: String): PurchaseResult = PurchaseResult.Cancelled

    override suspend fun restore(): RestoreResult = RestoreResult.Purchases(emptyList())

    override suspend fun acknowledge(purchaseToken: String): AcknowledgementResult = AcknowledgementResult.Success
}

private fun completedSession(planId: String): CompletedSession = CompletedSession(
    planId = planId,
    completedAtWallClockMs = 1_700_000_030_000,
    elapsedDurationMs = 30_000,
    boardId = "board",
    planTitle = planId,
)

private fun completedWorkout(planId: String): CompletedHealthWorkout = CompletedHealthWorkout(
    session = completedSession(planId),
    segments = emptyList(),
)
