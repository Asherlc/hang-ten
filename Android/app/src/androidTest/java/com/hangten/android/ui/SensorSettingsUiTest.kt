package com.hangten.android.ui

import android.app.Activity
import androidx.activity.ComponentActivity
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.junit4.createAndroidComposeRule
import androidx.compose.ui.test.onNodeWithContentDescription
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import com.hangten.android.audio.WorkoutAudioCoach
import com.hangten.android.billing.*
import com.hangten.android.health.*
import com.hangten.android.sensors.*
import com.hangten.android.workout.CompletedSession
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.emptyFlow
import org.junit.Rule
import org.junit.Test

class SensorSettingsUiTest {
    @get:Rule val rule = createAndroidComposeRule<ComponentActivity>()

    @Test fun explicitConnectUsesFakeTransportAndRendersMeterAndTare() {
        val transport = FakeForceSensorTransport().apply { enqueue(ForceSensorAdvertisement(name = "Progressor 200")) }
        val controller = SensorConnectionController(transport, ForceSensorProfile.Progressor)
        rule.setContent {
            SettingsScreen(TestCoach(), PurchaseManager(TestPurchaseClient()), HealthViewModel(TestHealthStore(), TestHistory()), PaddingValues(), controller,
                onSensorPermissionRequest = { controller.connectAfterPermissionsGranted() })
        }
        rule.onNodeWithContentDescription("Connect sensor").assertIsDisplayed().performClick()
        rule.waitUntil(5_000) { controller.state.value.connection == SensorConnectionState.Streaming }
        transport.emit(byteArrayOf(1, 8, 0, 0, 72, 65, 7, 0, 0, 0))
        rule.onNodeWithText("Live force: 12.5 kgf").assertIsDisplayed()
        rule.onNodeWithContentDescription("Tare sensor").performClick()
    }
}

private class TestCoach : WorkoutAudioCoach {
    override val instructionCoachingEnabled = MutableStateFlow(false)
    override fun scheduleCountdown(startElapsedMs: Long) = Unit
    override fun cancel() = Unit
    override fun speakInstruction(instruction: String) = Unit
    override fun setInstructionCoachingEnabled(enabled: Boolean) { instructionCoachingEnabled.value = enabled }
}
private class TestPurchaseClient : PurchaseClient {
    override val updates = emptyFlow<PurchaseUpdate>()
    override suspend fun load(id: String): PurchaseProduct? = null
    override suspend fun purchase(activity: Activity?, id: String) = PurchaseResult.Cancelled
    override suspend fun restore() = RestoreResult.Purchases(emptyList())
    override suspend fun acknowledge(purchaseToken: String) = AcknowledgementResult.Success
}
private class TestHistory : WorkoutHistory { override suspend fun record(completedSession: CompletedSession) = Unit; override suspend fun completedSessions() = emptyList<CompletedSession>() }
private class TestHealthStore : WorkoutHealthStore {
    override fun requestAuthorization() = emptySet<String>()
    override suspend fun completeAuthorizationRequest() = HealthAuthorizationState.Unavailable
    override suspend fun refreshAuthorization() = HealthAuthorizationState.Unavailable
    override suspend fun saveCompletedWorkout(workout: CompletedHealthWorkout) = Result.failure<HangTenHealthWorkout>(IllegalStateException("unavailable"))
    override suspend fun fetchHangTenWorkouts() = Result.failure<List<HangTenHealthWorkout>>(IllegalStateException("unavailable"))
}
