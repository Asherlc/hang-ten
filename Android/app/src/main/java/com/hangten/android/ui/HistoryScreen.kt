package com.hangten.android.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.hangten.android.health.HealthHistorySource
import com.hangten.android.health.HealthViewModel
import java.text.DateFormat
import java.util.Date

@Composable
fun HistoryScreen(
    healthViewModel: HealthViewModel,
    refreshKey: Int,
    contentPadding: PaddingValues,
) {
    val healthState by healthViewModel.state.collectAsState()
    LaunchedEffect(healthViewModel, refreshKey) {
        healthViewModel.refreshHistory()
    }
    Column(
        modifier = Modifier.fillMaxSize().padding(contentPadding).padding(20.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Text("History")
        when (healthState.historySource) {
            HealthHistorySource.HealthConnect -> Text("History reconciled with Health Connect.")
            HealthHistorySource.LocalFallback -> Text("Showing local workout history.")
            HealthHistorySource.Unavailable -> Unit
        }
        healthState.error?.let { Text(it) }
        if (healthState.sessions.isEmpty()) {
            Text("No completed sessions yet.")
        } else {
            LazyColumn(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                items(healthState.sessions, key = { "${it.planId}-${it.completedAtWallClockMs}" }) { session ->
                    Text("${session.planId} · ${formatDuration(session.elapsedDurationMs)} · ${DateFormat.getDateTimeInstance().format(Date(session.completedAtWallClockMs))}")
                }
            }
        }
    }
}

private fun formatDuration(durationMs: Long): String = "%d:%02d".format(durationMs / 60_000, durationMs / 1_000 % 60)
