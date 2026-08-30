package com.hangten.android.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.unit.dp
import com.hangten.android.content.Board
import com.hangten.android.content.TrainingPlan

@Composable
fun PlansScreen(
    boards: List<Board>,
    plans: List<TrainingPlan>,
    selectedBoard: Board?,
    selectedPlan: TrainingPlan?,
    onBoardSelected: (Board) -> Unit,
    onPlanSelected: (TrainingPlan) -> Unit,
    contentPadding: PaddingValues,
) {
    BoxWithConstraints(modifier = Modifier.fillMaxSize().padding(contentPadding).padding(20.dp)) {
        val horizontal = maxWidth >= 700.dp
        if (horizontal) {
            Row(horizontalArrangement = Arrangement.spacedBy(16.dp), modifier = Modifier.fillMaxSize()) {
                SelectionList("Boards", boards, selectedBoard?.id, { it.id }, { it.name }, onBoardSelected, Modifier.weight(1f))
                SelectionList("Plans", plans, selectedPlan?.id, { it.id }, { it.title }, onPlanSelected, Modifier.weight(1f))
            }
        } else {
            Column(verticalArrangement = Arrangement.spacedBy(16.dp), modifier = Modifier.fillMaxSize()) {
                SelectionList("Boards", boards, selectedBoard?.id, { it.id }, { it.name }, onBoardSelected, Modifier.weight(1f))
                SelectionList("Plans", plans, selectedPlan?.id, { it.id }, { it.title }, onPlanSelected, Modifier.weight(1f))
            }
        }
    }
}

@Composable
private fun <T> SelectionList(
    heading: String,
    entries: List<T>,
    selectedId: String?,
    id: (T) -> String,
    label: (T) -> String,
    onSelected: (T) -> Unit,
    modifier: Modifier,
) {
    Column(modifier = modifier) {
        Text(heading)
        LazyColumn(verticalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.fillMaxSize()) {
            items(entries, key = id) { entry ->
                val name = label(entry)
                Card(modifier = Modifier.fillMaxWidth()) {
                    Column(modifier = Modifier.padding(12.dp)) {
                        Text(name)
                        Button(
                            onClick = { onSelected(entry) },
                            modifier = Modifier.semantics { contentDescription = "Select ${heading.dropLast(1).lowercase()} $name" },
                        ) { Text(if (id(entry) == selectedId) "Selected" else "Select") }
                    }
                }
            }
        }
    }
}
