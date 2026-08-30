package com.hangten.android.billing

import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.test.advanceUntilIdle
import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

@OptIn(ExperimentalCoroutinesApi::class)
class PurchaseManagerTest {
    @Test
    fun purchasedLifetimeUnlockIsAcknowledgedBeforeAccessIsGranted() = runTest {
        val client = FakePurchaseClient(
            purchaseResult = PurchaseResult.Purchased(
                PurchaseRecord(PurchaseManager.LIFETIME_PRODUCT_ID, "purchase-token", acknowledged = false),
            ),
        )
        val manager = PurchaseManager(client, this)

        manager.purchase(null)

        assertTrue(manager.hasLifetimeEntitlement.value)
        assertEquals(PurchaseState.Idle, manager.state.value)
        assertEquals(listOf("purchase-token"), client.acknowledgedTokens)
        manager.close()
    }

    @Test
    fun acknowledgementFailureKeepsAccessLockedAndRetriesOnCurrentPurchaseRefresh() = runTest {
        val record = PurchaseRecord(PurchaseManager.LIFETIME_PRODUCT_ID, "purchase-token", acknowledged = false)
        val client = FakePurchaseClient(
            purchaseResult = PurchaseResult.Purchased(record),
            acknowledgementResult = AcknowledgementResult.Failed,
        )
        val manager = PurchaseManager(client, this)

        manager.purchase(null)

        assertFalse(manager.hasLifetimeEntitlement.value)
        assertEquals(PurchaseState.Failed, manager.state.value)
        assertEquals(listOf("purchase-token"), client.acknowledgedTokens)

        client.acknowledgementResult = AcknowledgementResult.Success
        client.restoreResult = RestoreResult.Purchases(listOf(PurchaseUpdate.Purchased(record)))

        manager.refreshCurrentPurchases()

        assertTrue(manager.hasLifetimeEntitlement.value)
        assertEquals(PurchaseState.Idle, manager.state.value)
        assertEquals(listOf("purchase-token", "purchase-token"), client.acknowledgedTokens)
        manager.close()
    }

    @Test
    fun pendingPurchaseDoesNotUnlockLifetimeAccess() = runTest {
        val client = FakePurchaseClient(purchaseResult = PurchaseResult.Pending)
        val manager = PurchaseManager(client, this)

        manager.purchase(null)

        assertFalse(manager.hasLifetimeEntitlement.value)
        assertEquals(PurchaseState.Pending, manager.state.value)
        assertTrue(client.acknowledgedTokens.isEmpty())
        manager.close()
    }

    @Test
    fun revokedPurchaseUpdateRemovesLifetimeAccess() = runTest {
        val updates = MutableSharedFlow<PurchaseUpdate>(replay = 1)
        val manager = PurchaseManager(
            FakePurchaseClient(updates = updates),
            this,
        )
        advanceUntilIdle()
        updates.tryEmit(PurchaseUpdate.Purchased(PurchaseRecord(PurchaseManager.LIFETIME_PRODUCT_ID, "token", true)))
        advanceUntilIdle()
        assertTrue(manager.hasLifetimeEntitlement.value)

        updates.tryEmit(PurchaseUpdate.Revoked(PurchaseManager.LIFETIME_PRODUCT_ID, "token"))
        advanceUntilIdle()

        assertFalse(manager.hasLifetimeEntitlement.value)
        assertEquals(PurchaseState.Idle, manager.state.value)
        manager.close()
    }

    @Test
    fun restoreProcessesCurrentPurchasedLifetimeAccess() = runTest {
        val client = FakePurchaseClient(
            restoreResult = RestoreResult.Purchases(
                listOf(PurchaseUpdate.Purchased(PurchaseRecord(PurchaseManager.LIFETIME_PRODUCT_ID, "restored-token", false))),
            ),
        )
        val manager = PurchaseManager(client, this)

        manager.restore()

        assertTrue(manager.hasLifetimeEntitlement.value)
        assertEquals(listOf("restored-token"), client.acknowledgedTokens)
        manager.close()
    }

    @Test
    fun restoreWithoutLifetimePurchaseRevokesPreviouslyGrantedAccess() = runTest {
        val client = FakePurchaseClient(
            purchaseResult = PurchaseResult.Purchased(
                PurchaseRecord(PurchaseManager.LIFETIME_PRODUCT_ID, "expired-token", acknowledged = true),
            ),
        )
        val manager = PurchaseManager(client, this)
        manager.purchase(null)
        assertTrue(manager.hasLifetimeEntitlement.value)
        client.restoreResult = RestoreResult.Purchases(emptyList())

        manager.restore()

        assertFalse(manager.hasLifetimeEntitlement.value)
        assertEquals(PurchaseState.NothingToRestore, manager.state.value)
        manager.close()
    }

    @Test
    fun unavailableLifetimeProductIsNotExposedForPurchase() = runTest {
        val manager = PurchaseManager(
            FakePurchaseClient(product = null),
            this,
        )

        manager.prepare()

        assertNull(manager.product.value)
        assertEquals(PurchaseState.ProductLoadFailed, manager.state.value)
        manager.close()
    }

    private class FakePurchaseClient(
        private val product: PurchaseProduct? = PurchaseProduct(PurchaseManager.LIFETIME_PRODUCT_ID, "$2.99"),
        private val purchaseResult: PurchaseResult = PurchaseResult.Cancelled,
        var restoreResult: RestoreResult = RestoreResult.Purchases(emptyList()),
        var acknowledgementResult: AcknowledgementResult = AcknowledgementResult.Success,
        override val updates: Flow<PurchaseUpdate> = MutableSharedFlow(),
    ) : PurchaseClient {
        val acknowledgedTokens = mutableListOf<String>()

        override suspend fun load(id: String): PurchaseProduct? = product

        override suspend fun purchase(activity: android.app.Activity?, id: String): PurchaseResult = purchaseResult

        override suspend fun restore(): RestoreResult = restoreResult

        override suspend fun acknowledge(purchaseToken: String): AcknowledgementResult {
            acknowledgedTokens += purchaseToken
            return acknowledgementResult
        }
    }
}
