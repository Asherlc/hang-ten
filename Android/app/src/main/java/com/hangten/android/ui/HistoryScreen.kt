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
import androidx.compose.runtime.getValue
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.hangten.android.workout.CompletedSession
import com.hangten.android.workout.SessionHistoryRepository
import java.text.DateFormat
import java.util.Date

@Composable
fun HistoryScreen(
    historyRepository: SessionHistoryRepository,
    refreshKey: Int,
    contentPadding: PaddingValues,
) {
    var sessions by remember { mutableStateOf<List<CompletedSession>>(emptyList()) }
    LaunchedEffect(historyRepository, refreshKey) {
        sessions = runCatching { historyRepository.completedSessions() }.getOrDefault(emptyList())
    }
    Column(
        modifier = Modifier.fillMaxSize().padding(contentPadding).padding(20.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Text("History")
        if (sessions.isEmpty()) {
            Text("No completed sessions yet.")
        } else {
            LazyColumn(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                items(sessions, key = { "${it.planId}-${it.completedAtWallClockMs}" }) { session ->
                    Text("${session.planId} · ${formatDuration(session.elapsedDurationMs)} · ${DateFormat.getDateTimeInstance().format(Date(session.completedAtWallClockMs))}")
                }
            }
        }
    }
}

private fun formatDuration(durationMs: Long): String = "%d:%02d".format(durationMs / 60_000, durationMs / 1_000 % 60)
