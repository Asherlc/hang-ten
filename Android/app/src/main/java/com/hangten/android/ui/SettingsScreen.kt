package com.hangten.android.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.unit.dp
import com.hangten.android.audio.WorkoutAudioCoach

@Composable
fun SettingsScreen(
    audioCoach: WorkoutAudioCoach,
    contentPadding: PaddingValues,
) {
    val instructionCoachingEnabled by audioCoach.instructionCoachingEnabled.collectAsState()
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
    }
}
