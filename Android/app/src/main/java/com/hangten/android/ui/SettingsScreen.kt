package com.hangten.android.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.material3.Button
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.rememberCoroutineScope
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.health.connect.client.PermissionController
import androidx.compose.ui.Modifier
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.unit.dp
import com.hangten.android.audio.WorkoutAudioCoach
import com.hangten.android.billing.PurchaseManager
import com.hangten.android.billing.PurchaseState
import com.hangten.android.health.HealthAuthorizationState
import com.hangten.android.health.HealthViewModel
import kotlinx.coroutines.launch

@Composable
fun SettingsScreen(
    audioCoach: WorkoutAudioCoach,
    purchaseManager: PurchaseManager,
    healthViewModel: HealthViewModel,
    contentPadding: PaddingValues,
) {
    val instructionCoachingEnabled by audioCoach.instructionCoachingEnabled.collectAsState()
    val hasLifetimeEntitlement by purchaseManager.hasLifetimeEntitlement.collectAsState()
    val product by purchaseManager.product.collectAsState()
    val state by purchaseManager.state.collectAsState()
    val healthState by healthViewModel.state.collectAsState()
    val scope = rememberCoroutineScope()
    val activity = androidx.compose.ui.platform.LocalContext.current.findActivity()
    val isTransacting = state == PurchaseState.Loading || state == PurchaseState.Purchasing
    val healthPermissionLauncher = rememberLauncherForActivityResult(
        contract = PermissionController.createRequestPermissionResultContract(),
        onResult = { healthViewModel.authorizationRequestFinished() },
    )
    LaunchedEffect(healthViewModel) { healthViewModel.refreshHistory() }
    Column(
        modifier = Modifier.fillMaxSize().padding(contentPadding).padding(20.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Text("Settings")
        Text("Speak workout instructions")
        Switch(
            checked = instructionCoachingEnabled,
            onCheckedChange = audioCoach::setInstructionCoachingEnabled,
            modifier = Modifier.semantics { contentDescription = "Speak workout instructions" },
        )
        Text("Lifetime access")
        if (hasLifetimeEntitlement) {
            Text("Unlimited workouts unlocked")
        } else if (product != null) {
            Button(
                onClick = { scope.launch { purchaseManager.purchase(activity) } },
                enabled = !isTransacting,
                modifier = Modifier.fillMaxWidth().semantics { contentDescription = "Purchase lifetime access" },
            ) { Text("Unlock for ${product!!.displayPrice}") }
        } else {
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
        Text("Health Connect")
        when (healthState.authorization) {
            HealthAuthorizationState.Authorized -> Text("Health workout history connected")
            HealthAuthorizationState.Unavailable -> Text("Health Connect is unavailable on this device. Local workout history remains available.")
            HealthAuthorizationState.Denied -> Text("Health Connect permission was not granted. Local workout history remains available.")
            HealthAuthorizationState.NotDetermined -> Text("Connect Health to save completed workouts and reconcile history.")
        }
        if (healthState.authorization != HealthAuthorizationState.Authorized && healthState.authorization != HealthAuthorizationState.Unavailable) {
            OutlinedButton(
                onClick = {
                    val permissions = healthViewModel.requestAuthorization()
                    if (permissions.isEmpty()) healthViewModel.authorizationRequestFinished() else healthPermissionLauncher.launch(permissions)
                },
                modifier = Modifier.fillMaxWidth().semantics { contentDescription = "Connect Health" },
            ) { Text("Connect Health") }
        }
        healthState.error?.let { Text(it) }
    }
}
