package com.hangten.android.ui

import android.os.SystemClock
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Button
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Modifier
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.semantics.stateDescription
import androidx.compose.ui.unit.dp
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleEventObserver
import androidx.lifecycle.compose.LocalLifecycleOwner
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.lifecycle.viewmodel.initializer
import androidx.lifecycle.viewmodel.viewModelFactory
import androidx.lifecycle.createSavedStateHandle
import com.hangten.android.audio.WorkoutAudioCoach
import com.hangten.android.board.BoardCanvas
import com.hangten.android.board.resolveTargets
import com.hangten.android.content.Board
import com.hangten.android.content.TrainingPlan
import com.hangten.android.content.TrainingStep
import com.hangten.android.workout.CompletedSession
import com.hangten.android.workout.SessionPhase
import com.hangten.android.workout.WorkoutAudioCancellation
import com.hangten.android.workout.WorkoutSession
import com.hangten.android.workout.WorkoutViewModel
import kotlinx.coroutines.delay
import kotlinx.coroutines.isActive

@Composable
fun WorkoutScreen(
    plan: TrainingPlan,
    board: Board,
    audioCoach: WorkoutAudioCoach,
    onSessionEnded: (CompletedSession) -> Unit,
    contentPadding: PaddingValues = PaddingValues(),
) {
    val factory = remember(plan.id, audioCoach) {
        viewModelFactory {
            initializer {
                val savedStateHandle = createSavedStateHandle()
                WorkoutViewModel(
                    session = WorkoutSession(
                        plan = plan,
                        restoredState = WorkoutViewModel.restoredSessionState(savedStateHandle),
                    ),
                    audioCancellation = WorkoutAudioCancellation { audioCoach.cancel() },
                    savedStateHandle = savedStateHandle,
                )
            }
        }
    }
    val viewModel: WorkoutViewModel = viewModel(key = "workout-${plan.id}", factory = factory)
    val snapshot by viewModel.snapshot.collectAsState()
    val lifecycleOwner = LocalLifecycleOwner.current
    val activeStep = plan.steps.getOrNull(snapshot.activeStepIndex)

    DisposableEffect(lifecycleOwner, viewModel) {
        val observer = LifecycleEventObserver { _, event ->
            if (event == Lifecycle.Event.ON_STOP) viewModel.onStop()
        }
        lifecycleOwner.lifecycle.addObserver(observer)
        onDispose {
            lifecycleOwner.lifecycle.removeObserver(observer)
            audioCoach.cancel()
        }
    }
    LaunchedEffect(viewModel) {
        if (viewModel.startIfNeeded()) {
            audioCoach.scheduleCountdown(SystemClock.elapsedRealtime())
            activeStep?.instruction?.let(audioCoach::speakInstruction)
        }
        while (isActive) {
            val refreshed = viewModel.refresh()
            if (refreshed.phase is SessionPhase.Complete) {
                audioCoach.cancel()
                break
            }
            delay(250)
        }
    }

    BoxWithConstraints(modifier = Modifier.fillMaxSize().padding(contentPadding).padding(20.dp)) {
        val horizontal = maxWidth >= 700.dp
        val details: @Composable () -> Unit = {
            WorkoutDetails(
                step = activeStep,
                snapshot = snapshot,
                viewModel = viewModel,
                audioCoach = audioCoach,
                onSessionEnded = onSessionEnded,
            )
        }
        val boardView: @Composable () -> Unit = {
            Box(
                modifier = Modifier.fillMaxWidth().semantics {
                    contentDescription = "Active board holds"
                    stateDescription = activeStep?.targets.orEmpty().joinToString { it.semantic ?: it.kind ?: "hold" }
                },
            ) {
                BoardCanvas(
                    board = board,
                    activeHoldIDs = activeStep?.let { resolveTargets(it.targets, board) }.orEmpty(),
                    onHoldTap = {},
                )
            }
        }
        if (horizontal) {
            Row(horizontalArrangement = Arrangement.spacedBy(20.dp), modifier = Modifier.fillMaxSize()) {
                Column(modifier = Modifier.weight(1f)) { details() }
                Column(modifier = Modifier.weight(1f)) { boardView() }
            }
        } else {
            Column(verticalArrangement = Arrangement.spacedBy(20.dp), modifier = Modifier.fillMaxSize()) {
                details()
                boardView()
            }
        }
    }
}

@Composable
private fun WorkoutDetails(
    step: TrainingStep?,
    snapshot: com.hangten.android.workout.WorkoutSnapshot,
    viewModel: WorkoutViewModel,
    audioCoach: WorkoutAudioCoach,
    onSessionEnded: (CompletedSession) -> Unit,
) {
    val task = step?.title ?: "Workout complete"
    Column(
        verticalArrangement = Arrangement.spacedBy(12.dp),
        modifier = Modifier.semantics {
            contentDescription = "Current task"
            stateDescription = task
        },
    ) {
        Text(task)
        step?.instruction?.takeIf { it.isNotBlank() }?.let { Text(it) }
        Text(progressLabel(snapshot))
        when (snapshot.phase) {
            is SessionPhase.StartCountdown, is SessionPhase.Active -> Button(
                onClick = {
                    viewModel.pause()
                    audioCoach.cancel()
                },
                modifier = Modifier.fillMaxWidth().semantics { contentDescription = "Pause workout" },
            ) { Text("Pause") }
            SessionPhase.Paused -> Button(
                onClick = {
                    viewModel.resume()
                    step?.instruction?.let(audioCoach::speakInstruction)
                },
                modifier = Modifier.fillMaxWidth().semantics { contentDescription = "Resume workout" },
            ) { Text("Resume") }
            SessionPhase.Complete -> Text("Workout complete")
        }
        OutlinedButton(
            onClick = {
                val completed = viewModel.complete()
                audioCoach.cancel()
                onSessionEnded(completed)
            },
            modifier = Modifier.fillMaxWidth().semantics { contentDescription = "End session" },
        ) { Text("End session") }
    }
}

private fun progressLabel(snapshot: com.hangten.android.workout.WorkoutSnapshot): String = when (snapshot.phase) {
    SessionPhase.StartCountdown -> "Starting in ${(snapshot.countdownRemainingMs + 999) / 1_000}"
    is SessionPhase.Active -> "${snapshot.elapsedPlanMs / 1_000}s elapsed"
    SessionPhase.Paused -> "Paused"
    SessionPhase.Complete -> "Complete"
}
