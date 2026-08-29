package com.hangten.android.billing

import android.app.Activity
import android.content.Context
import com.android.billingclient.api.AcknowledgePurchaseParams
import com.android.billingclient.api.BillingClient
import com.android.billingclient.api.BillingClientStateListener
import com.android.billingclient.api.BillingFlowParams
import com.android.billingclient.api.BillingResult
import com.android.billingclient.api.ProductDetails
import com.android.billingclient.api.Purchase
import com.android.billingclient.api.PurchasesUpdatedListener
import com.android.billingclient.api.QueryProductDetailsParams
import com.android.billingclient.api.QueryPurchasesParams
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.suspendCancellableCoroutine
import kotlin.coroutines.resume

class PlayBillingClient(context: Context) : PurchaseClient {
    private val productDetails = mutableMapOf<String, ProductDetails>()
    private val _updates = MutableSharedFlow<PurchaseUpdate>(extraBufferCapacity = 16)
    private val purchaseListener = PurchasesUpdatedListener { result, purchases ->
        if (result.responseCode == BillingClient.BillingResponseCode.OK && purchases != null) {
            purchases.forEach { purchase -> updatesFor(purchase).forEach(_updates::tryEmit) }
        } else {
            _updates.tryEmit(
                if (result.responseCode == BillingClient.BillingResponseCode.USER_CANCELED) {
                    PurchaseUpdate.Cancelled
                } else {
                    PurchaseUpdate.Failed
                },
            )
        }
    }
    private val billingClient = BillingClient.newBuilder(context.applicationContext)
        .setListener(purchaseListener)
        .enablePendingPurchases(
            com.android.billingclient.api.PendingPurchasesParams.newBuilder()
                .enableOneTimeProducts()
                .build(),
        )
        .enableAutoServiceReconnection()
        .build()

    override val updates: Flow<PurchaseUpdate> = _updates

    override suspend fun load(id: String): PurchaseProduct? {
        if (!connect()) return null
        val query = QueryProductDetailsParams.newBuilder()
            .setProductList(
                listOf(
                    QueryProductDetailsParams.Product.newBuilder()
                        .setProductId(id)
                        .setProductType(BillingClient.ProductType.INAPP)
                        .build(),
                ),
            )
            .build()
        return suspendCancellableCoroutine { continuation ->
            billingClient.queryProductDetailsAsync(query) { result, detailsResult ->
                val detail = detailsResult.productDetailsList.firstOrNull { it.productId == id }
                if (result.responseCode != BillingClient.BillingResponseCode.OK || detail == null) {
                    continuation.resume(null)
                    return@queryProductDetailsAsync
                }
                val offer = detail.oneTimePurchaseOfferDetailsList?.firstOrNull()
                if (offer == null) {
                    continuation.resume(null)
                    return@queryProductDetailsAsync
                }
                productDetails[id] = detail
                continuation.resume(PurchaseProduct(id, offer.formattedPrice))
            }
        }
    }

    override suspend fun purchase(activity: Activity?, id: String): PurchaseResult {
        val detail = productDetails[id] ?: return PurchaseResult.Failed
        val offer = detail.oneTimePurchaseOfferDetailsList?.firstOrNull() ?: return PurchaseResult.Failed
        val offerToken = offer.offerToken ?: return PurchaseResult.Failed
        val host = activity ?: return PurchaseResult.Failed
        val params = BillingFlowParams.newBuilder()
            .setProductDetailsParamsList(
                listOf(
                    BillingFlowParams.ProductDetailsParams.newBuilder()
                        .setProductDetails(detail)
                        .setOfferToken(offerToken)
                        .build(),
                ),
            )
            .build()
        return when (billingClient.launchBillingFlow(host, params).responseCode) {
            BillingClient.BillingResponseCode.OK -> PurchaseResult.Started
            BillingClient.BillingResponseCode.USER_CANCELED -> PurchaseResult.Cancelled
            else -> PurchaseResult.Failed
        }
    }

    override suspend fun restore(): RestoreResult {
        if (!connect()) return RestoreResult.Failed
        val params = QueryPurchasesParams.newBuilder()
            .setProductType(BillingClient.ProductType.INAPP)
            .build()
        return suspendCancellableCoroutine { continuation ->
            billingClient.queryPurchasesAsync(params) { result, purchases ->
                if (result.responseCode != BillingClient.BillingResponseCode.OK) {
                    continuation.resume(RestoreResult.Failed)
                } else {
                    continuation.resume(RestoreResult.Purchases(purchases.flatMap(::updatesFor)))
                }
            }
        }
    }

    override suspend fun acknowledge(purchaseToken: String): AcknowledgementResult {
        if (!connect()) return AcknowledgementResult.Failed
        val params = AcknowledgePurchaseParams.newBuilder().setPurchaseToken(purchaseToken).build()
        return suspendCancellableCoroutine { continuation ->
            billingClient.acknowledgePurchase(params) { result ->
                continuation.resume(
                    if (result.responseCode == BillingClient.BillingResponseCode.OK) {
                        AcknowledgementResult.Success
                    } else {
                        AcknowledgementResult.Failed
                    },
                )
            }
        }
    }

    override fun close() {
        billingClient.endConnection()
    }

    private suspend fun connect(): Boolean {
        if (billingClient.isReady) return true
        return suspendCancellableCoroutine { continuation ->
            billingClient.startConnection(object : BillingClientStateListener {
                override fun onBillingSetupFinished(result: BillingResult) {
                    continuation.resume(result.responseCode == BillingClient.BillingResponseCode.OK)
                }

                override fun onBillingServiceDisconnected() = Unit
            })
        }
    }

    private fun updatesFor(purchase: Purchase): List<PurchaseUpdate> = purchase.products.mapNotNull { productId ->
        when (purchase.purchaseState) {
            Purchase.PurchaseState.PURCHASED -> PurchaseUpdate.Purchased(
                PurchaseRecord(productId, purchase.purchaseToken, purchase.isAcknowledged),
            )
            Purchase.PurchaseState.PENDING -> PurchaseUpdate.Pending(productId)
            else -> PurchaseUpdate.Failed
        }
    }
}
