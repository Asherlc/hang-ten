package com.hangten.android.ui

import androidx.activity.ComponentActivity
import androidx.compose.material3.Button
import androidx.compose.material3.Text
import androidx.compose.runtime.mutableStateOf
import androidx.compose.ui.test.assertCountEquals
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.junit4.createAndroidComposeRule
import androidx.compose.ui.test.onNodeWithContentDescription
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.onAllNodesWithContentDescription
import androidx.compose.ui.test.performClick
import com.hangten.android.billing.AcknowledgementResult
import com.hangten.android.billing.PurchaseClient
import com.hangten.android.billing.PurchaseManager
import com.hangten.android.billing.PurchaseProduct
import com.hangten.android.billing.PurchaseResult
import com.hangten.android.billing.PurchaseUpdate
import com.hangten.android.billing.RestoreResult
import kotlinx.coroutines.flow.emptyFlow
import org.junit.Rule
import org.junit.Test

class WorkoutAccessGateTest {
    @get:Rule
    val composeRule = createAndroidComposeRule<ComponentActivity>()

    @Test
    fun exhaustedFreeWorkoutsShowUnavailablePurchaseGateWithoutStartingTheWorkout() {
        val purchaseManager = PurchaseManager(UnavailablePurchaseClient())
        val startedWorkout = mutableStateOf(false)
        composeRule.setContent {
            WorkoutAccessGate(
                accessStore = WorkoutAccessStore(FixedWorkoutAccessPreferences(2)),
                purchaseManager = purchaseManager,
                onWorkoutAllowed = { startedWorkout.value = true },
            ) { requestWorkout ->
                Button(onClick = requestWorkout) { Text("Start fixture workout") }
            }
        }

        composeRule.onNodeWithText("Start fixture workout").performClick()

        composeRule.onNodeWithText("Unlock Hang Ten").assertIsDisplayed()
        composeRule.onNodeWithText("Purchase options are unavailable.").assertIsDisplayed()
        composeRule.onAllNodesWithContentDescription("Purchase lifetime access").assertCountEquals(0)
        composeRule.runOnIdle {
            org.junit.Assert.assertFalse(startedWorkout.value)
            purchaseManager.close()
        }
    }

    private class FixedWorkoutAccessPreferences(
        private var freeWorkoutsUsed: Int,
    ) : WorkoutAccessPreferences {
        override fun readFreeWorkoutsUsed(): Int = freeWorkoutsUsed

        override fun writeFreeWorkoutsUsed(value: Int) {
            freeWorkoutsUsed = value
        }
    }

    private class UnavailablePurchaseClient : PurchaseClient {
        override val updates = emptyFlow<PurchaseUpdate>()

        override suspend fun load(id: String): PurchaseProduct? = null

        override suspend fun purchase(activity: android.app.Activity?, id: String): PurchaseResult = PurchaseResult.Failed

        override suspend fun restore(): RestoreResult = RestoreResult.Purchases(emptyList())

        override suspend fun acknowledge(purchaseToken: String): AcknowledgementResult = AcknowledgementResult.Failed
    }
}
