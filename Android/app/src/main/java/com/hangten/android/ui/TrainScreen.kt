package com.hangten.android.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.unit.dp
import com.hangten.android.content.Board
import com.hangten.android.content.TrainingPlan

@Composable
fun TrainScreen(
    board: Board?,
    plan: TrainingPlan?,
    onOpenPlans: () -> Unit,
    onOpenSettings: () -> Unit,
    onStartWorkout: () -> Unit,
    contentPadding: PaddingValues,
) {
    BoxWithConstraints(
        modifier = Modifier.fillMaxSize().padding(contentPadding).padding(20.dp),
    ) {
        val horizontal = maxWidth >= 700.dp
        val content: @Composable () -> Unit = {
            SelectionCard("Board", board?.name ?: "Choose a board")
            SelectionCard("Plan", plan?.title ?: "Choose a training plan")
        }
        Column(verticalArrangement = Arrangement.spacedBy(16.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text("Train", modifier = Modifier.weight(1f))
                TextButton(
                    onClick = onOpenSettings,
                    modifier = Modifier.semantics { contentDescription = "Settings" },
                ) { Text("Settings") }
            }
            if (horizontal) {
                Row(horizontalArrangement = Arrangement.spacedBy(16.dp), modifier = Modifier.fillMaxWidth()) { content() }
            } else {
                Column(verticalArrangement = Arrangement.spacedBy(16.dp)) { content() }
            }
            OutlinedButton(
                onClick = onOpenPlans,
                modifier = Modifier.fillMaxWidth().semantics { contentDescription = "Choose board and plan" },
            ) { Text("Choose board and plan") }
            Button(
                onClick = onStartWorkout,
                enabled = board != null && plan != null,
                modifier = Modifier.fillMaxWidth().semantics { contentDescription = "Start workout" },
            ) { Text("Start workout") }
        }
    }
}

@Composable
private fun SelectionCard(label: String, value: String) {
    Card(modifier = Modifier.fillMaxWidth()) {
        Column(modifier = Modifier.padding(16.dp)) {
            Text(label)
            Text(value)
        }
    }
}
