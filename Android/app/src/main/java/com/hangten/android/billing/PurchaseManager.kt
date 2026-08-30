package com.hangten.android.billing

import android.app.Activity
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.CoroutineStart
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

data class PurchaseProduct(
    val id: String,
    val displayPrice: String,
)

data class PurchaseRecord(
    val productId: String,
    val purchaseToken: String,
    val acknowledged: Boolean,
)

sealed interface PurchaseResult {
    data class Purchased(val record: PurchaseRecord) : PurchaseResult
    data object Pending : PurchaseResult
    data object Cancelled : PurchaseResult
    data object Started : PurchaseResult
    data object Failed : PurchaseResult
}

sealed interface RestoreResult {
    data class Purchases(val updates: List<PurchaseUpdate>) : RestoreResult
    data object Failed : RestoreResult
}

sealed interface AcknowledgementResult {
    data object Success : AcknowledgementResult
    data object Failed : AcknowledgementResult
}

sealed interface PurchaseUpdate {
    data class Purchased(val record: PurchaseRecord) : PurchaseUpdate
    data class Pending(val productId: String) : PurchaseUpdate
    data class Revoked(val productId: String, val purchaseToken: String) : PurchaseUpdate
    data object Cancelled : PurchaseUpdate
    data object Failed : PurchaseUpdate
}

interface PurchaseClient {
    val updates: Flow<PurchaseUpdate>

    suspend fun load(id: String): PurchaseProduct?

    suspend fun purchase(activity: Activity?, id: String): PurchaseResult

    suspend fun restore(): RestoreResult

    suspend fun acknowledge(purchaseToken: String): AcknowledgementResult

    fun close() = Unit
}

enum class PurchaseState {
    Idle,
    Loading,
    Purchasing,
    Pending,
    Cancelled,
    Failed,
    ProductLoadFailed,
    NothingToRestore,
    RestoreFailed,
}

class PurchaseManager(
    private val client: PurchaseClient,
    scope: CoroutineScope = CoroutineScope(SupervisorJob() + Dispatchers.Main.immediate),
) {
    private val _hasLifetimeEntitlement = MutableStateFlow(false)
    private val _product = MutableStateFlow<PurchaseProduct?>(null)
    private val _state = MutableStateFlow(PurchaseState.Idle)
    private val updateJob: Job = scope.launch(start = CoroutineStart.UNDISPATCHED) {
        client.updates.collect(::apply)
    }
    private val acknowledgedTokens = mutableSetOf<String>()

    val hasLifetimeEntitlement: StateFlow<Boolean> = _hasLifetimeEntitlement.asStateFlow()
    val product: StateFlow<PurchaseProduct?> = _product.asStateFlow()
    val state: StateFlow<PurchaseState> = _state.asStateFlow()

    suspend fun prepare() {
        _state.value = PurchaseState.Loading
        _product.value = null
        refreshCurrentPurchases()
        _product.value = runCatching { client.load(LIFETIME_PRODUCT_ID) }.getOrNull()
        _state.value = if (_product.value == null) PurchaseState.ProductLoadFailed else PurchaseState.Idle
    }

    suspend fun purchase(activity: Activity?) {
        _state.value = PurchaseState.Purchasing
        when (val result = client.purchase(activity, LIFETIME_PRODUCT_ID)) {
            is PurchaseResult.Purchased -> apply(PurchaseUpdate.Purchased(result.record))
            PurchaseResult.Pending -> _state.value = PurchaseState.Pending
            PurchaseResult.Cancelled -> _state.value = PurchaseState.Cancelled
            PurchaseResult.Started -> Unit
            PurchaseResult.Failed -> _state.value = PurchaseState.Failed
        }
    }

    suspend fun restore() {
        _state.value = PurchaseState.Loading
        when (val result = client.restore()) {
            RestoreResult.Failed -> _state.value = PurchaseState.RestoreFailed
            is RestoreResult.Purchases -> {
                _hasLifetimeEntitlement.value = false
                for (update in result.updates) apply(update)
                val hasPendingLifetimePurchase = result.updates.any {
                    it is PurchaseUpdate.Pending && it.productId == LIFETIME_PRODUCT_ID
                }
                if (!_hasLifetimeEntitlement.value && !hasPendingLifetimePurchase) {
                    _state.value = PurchaseState.NothingToRestore
                }
            }
        }
    }

    fun close() {
        updateJob.cancel()
        client.close()
    }

    /**
     * Reconciles local access with Google Play's current purchase list.
     * A successful empty list is authoritative and removes a prior unlock.
     */
    suspend fun refreshCurrentPurchases() {
        when (val result = client.restore()) {
            RestoreResult.Failed -> Unit
            is RestoreResult.Purchases -> {
                _hasLifetimeEntitlement.value = false
                for (update in result.updates) apply(update)
            }
        }
    }

    private suspend fun apply(update: PurchaseUpdate) {
        when (update) {
            is PurchaseUpdate.Purchased -> applyPurchased(update.record)
            is PurchaseUpdate.Pending -> if (update.productId == LIFETIME_PRODUCT_ID) {
                _hasLifetimeEntitlement.value = false
                _state.value = PurchaseState.Pending
            }
            is PurchaseUpdate.Revoked -> if (update.productId == LIFETIME_PRODUCT_ID) {
                acknowledgedTokens.remove(update.purchaseToken)
                _hasLifetimeEntitlement.value = false
                _state.value = PurchaseState.Idle
            }
            PurchaseUpdate.Cancelled -> _state.value = PurchaseState.Cancelled
            PurchaseUpdate.Failed -> _state.value = PurchaseState.Failed
        }
    }

    private suspend fun applyPurchased(record: PurchaseRecord) {
        if (record.productId != LIFETIME_PRODUCT_ID) return
        if (!record.acknowledged && record.purchaseToken !in acknowledgedTokens) {
            if (client.acknowledge(record.purchaseToken) == AcknowledgementResult.Failed) {
                _state.value = PurchaseState.Failed
                return
            }
            acknowledgedTokens += record.purchaseToken
        }
        _hasLifetimeEntitlement.value = true
        _state.value = PurchaseState.Idle
    }

    companion object {
        const val LIFETIME_PRODUCT_ID = "com.hangten.training.lifetime"
    }
}
