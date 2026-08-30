package com.hangten.android.ui

import androidx.activity.ComponentActivity
import androidx.compose.ui.test.junit4.createAndroidComposeRule
import androidx.datastore.preferences.core.PreferenceDataStoreFactory
import androidx.lifecycle.Lifecycle
import com.hangten.android.billing.AcknowledgementResult
import com.hangten.android.billing.PurchaseClient
import com.hangten.android.billing.PurchaseManager
import com.hangten.android.billing.PurchaseProduct
import com.hangten.android.billing.PurchaseRecord
import com.hangten.android.billing.PurchaseResult
import com.hangten.android.billing.PurchaseUpdate
import com.hangten.android.billing.RestoreResult
import com.hangten.android.workout.SessionHistoryRepository
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.emptyFlow
import org.junit.Rule
import org.junit.Test

class ForegroundPurchaseRefreshTest {
    @get:Rule
    val composeRule = createAndroidComposeRule<ComponentActivity>()

    @Test
    fun returningToForegroundClearsLifetimeAccessWhenCurrentPurchasesAreEmpty() {
        val client = ForegroundPurchaseClient(
            RestoreResult.Purchases(
                listOf(
                    PurchaseUpdate.Purchased(
                        PurchaseRecord(PurchaseManager.LIFETIME_PRODUCT_ID, "lifetime-token", acknowledged = true),
                    ),
                ),
            ),
        )
        val purchaseManager = PurchaseManager(client)
        val history = SessionHistoryRepository(
            PreferenceDataStoreFactory.create {
                composeRule.activity.cacheDir.resolve("foreground-purchase-refresh.preferences_pb")
            },
        )

        composeRule.setContent {
            HangTenApp(
                boards = listOf(fixtureBoard()),
                plans = listOf(fixturePlan()),
                historyRepository = history,
                audioCoach = RecordingAudioCoach(),
                purchaseManager = purchaseManager,
                accessStore = WorkoutAccessStore(FixedWorkoutAccessPreferences(2)),
            )
        }

        composeRule.waitUntil(timeoutMillis = 5_000) { purchaseManager.hasLifetimeEntitlement.value }
        client.restoreResult = RestoreResult.Purchases(emptyList())

        composeRule.activityRule.scenario.moveToState(Lifecycle.State.CREATED)
        composeRule.activityRule.scenario.moveToState(Lifecycle.State.RESUMED)

        composeRule.waitUntil(timeoutMillis = 5_000) { !purchaseManager.hasLifetimeEntitlement.value }
        purchaseManager.close()
    }

    private class ForegroundPurchaseClient(
        var restoreResult: RestoreResult,
    ) : PurchaseClient {
        override val updates: Flow<PurchaseUpdate> = emptyFlow()

        override suspend fun load(id: String): PurchaseProduct? = PurchaseProduct(id, "$2.99")

        override suspend fun purchase(activity: android.app.Activity?, id: String): PurchaseResult = PurchaseResult.Cancelled

        override suspend fun restore(): RestoreResult = restoreResult

        override suspend fun acknowledge(purchaseToken: String): AcknowledgementResult = AcknowledgementResult.Success
    }

    private class FixedWorkoutAccessPreferences(
        private var freeWorkoutsUsed: Int,
    ) : WorkoutAccessPreferences {
        override fun readFreeWorkoutsUsed(): Int = freeWorkoutsUsed

        override fun writeFreeWorkoutsUsed(value: Int) {
            freeWorkoutsUsed = value
        }
    }
}
