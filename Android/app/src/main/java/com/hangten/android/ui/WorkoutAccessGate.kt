package com.hangten.android.ui

import android.app.Activity
import android.content.Context
import android.content.ContextWrapper
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.unit.dp
import com.hangten.android.billing.PurchaseManager
import com.hangten.android.billing.PurchaseState
import kotlinx.coroutines.launch

@Composable
fun WorkoutAccessGate(
    accessStore: WorkoutAccessStore,
    purchaseManager: PurchaseManager,
    onWorkoutAllowed: () -> Unit,
    content: @Composable (onStartWorkout: () -> Unit) -> Unit,
) {
    val hasLifetimeEntitlement by purchaseManager.hasLifetimeEntitlement.collectAsState()
    var showsPaywall by remember { mutableStateOf(false) }
    val requestWorkout = {
        when (accessStore.launchDecision(hasLifetimeEntitlement)) {
            WorkoutLaunchDecision.Allowed -> onWorkoutAllowed()
            WorkoutLaunchDecision.RequiresPurchase -> showsPaywall = true
        }
    }

    LaunchedEffect(hasLifetimeEntitlement, showsPaywall) {
        if (showsPaywall && accessStore.launchDecision(hasLifetimeEntitlement) == WorkoutLaunchDecision.Allowed) {
            showsPaywall = false
            onWorkoutAllowed()
        }
    }

    content(requestWorkout)
    if (showsPaywall) {
        LifetimeUnlockPaywall(
            purchaseManager = purchaseManager,
            onDismiss = { showsPaywall = false },
        )
    }
}

@Composable
fun LifetimeUnlockPaywall(
    purchaseManager: PurchaseManager,
    onDismiss: () -> Unit,
) {
    val product by purchaseManager.product.collectAsState()
    val state by purchaseManager.state.collectAsState()
    val scope = rememberCoroutineScope()
    val activity = LocalContext.current.findActivity()
    val isTransacting = state == PurchaseState.Loading || state == PurchaseState.Purchasing

    AlertDialog(
        onDismissRequest = { if (!isTransacting) onDismiss() },
        title = { Text("Unlock Hang Ten") },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                Text("You’ve completed your 2 free workouts. Unlock unlimited workouts for a one-time purchase.")
                if (product != null) {
                    Button(
                        onClick = { scope.launch { purchaseManager.purchase(activity) } },
                        enabled = !isTransacting,
                        modifier = Modifier.fillMaxWidth().semantics { contentDescription = "Purchase lifetime access" },
                    ) { Text("Unlock for ${product!!.displayPrice}") }
                } else {
                    Text("Purchase options are unavailable.")
                    OutlinedButton(
                        onClick = { scope.launch { purchaseManager.prepare() } },
                        enabled = !isTransacting,
                        modifier = Modifier.fillMaxWidth().semantics { contentDescription = "Retry loading purchase" },
                    ) { Text("Retry loading purchase") }
                }
                OutlinedButton(
                    onClick = { scope.launch { purchaseManager.restore() } },
                    enabled = !isTransacting,
                    modifier = Modifier.fillMaxWidth().semantics { contentDescription = "Restore purchases" },
                ) { Text("Restore purchases") }
                PurchaseStatus(state)
            }
        },
        confirmButton = {
            TextButton(
                onClick = onDismiss,
                enabled = state != PurchaseState.Purchasing,
                modifier = Modifier.semantics { contentDescription = "Close purchase access" },
            ) { Text("Close") }
        },
    )
}

@Composable
fun PurchaseStatus(state: PurchaseState) {
    val message = when (state) {
        PurchaseState.Idle -> null
        PurchaseState.Loading -> "Loading purchase options…"
        PurchaseState.Purchasing -> "Completing your purchase…"
        PurchaseState.Pending -> "Purchase pending. Your workout will unlock after Google Play approves it."
        PurchaseState.Failed -> "We couldn’t complete the purchase. Please try again or restore purchases."
        PurchaseState.ProductLoadFailed -> "We couldn’t load purchase options. Check your connection and try again."
        PurchaseState.NothingToRestore -> "Nothing to restore. No lifetime unlock purchase was found."
        PurchaseState.RestoreFailed -> "Restore failed. Please try again."
    }
    if (message != null) {
        Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
            if (state == PurchaseState.Loading || state == PurchaseState.Purchasing) CircularProgressIndicator()
            Text(message)
        }
    }
}

internal tailrec fun Context.findActivity(): Activity? = when (this) {
    is Activity -> this
    is ContextWrapper -> baseContext.findActivity()
    else -> null
}
