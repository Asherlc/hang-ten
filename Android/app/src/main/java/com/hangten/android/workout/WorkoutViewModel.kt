package com.hangten.android.workout

import android.os.SystemClock
import androidx.lifecycle.ViewModel
import androidx.lifecycle.SavedStateHandle
import com.hangten.android.sensors.MotherboardMeasurement
import com.hangten.android.sensors.SensorWorkoutRecorder
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow

fun interface WorkoutAudioCancellation {
    fun cancel()
}

class WorkoutViewModel(
    private val session: WorkoutSession,
    private val elapsedRealtime: () -> Long = SystemClock::elapsedRealtime,
    private val audioCancellation: WorkoutAudioCancellation = WorkoutAudioCancellation {},
    private val savedStateHandle: SavedStateHandle? = null,
    private val sensorRecorder: SensorWorkoutRecorder? = null,
) : ViewModel() {
    private val _snapshot = MutableStateFlow(session.snapshot(elapsedRealtime()))

    val snapshot: StateFlow<WorkoutSnapshot> = _snapshot.asStateFlow()

    fun start(): WorkoutSnapshot = publish { session.start(elapsedRealtime()) }

    fun startIfNeeded(): Boolean {
        if (session.hasStarted()) {
            refresh()
            return false
        }
        start()
        return true
    }

    fun pause(): WorkoutSnapshot = publish {
        session.snapshot(elapsedRealtime()).also { snapshot -> sensorRecorder?.pause(snapshot.elapsedPlanMs) }
        session.pause(elapsedRealtime())
    }

    fun resume(): WorkoutSnapshot = publish { session.resume(elapsedRealtime()) }

    fun refresh(): WorkoutSnapshot = publish { session.snapshot(elapsedRealtime()) }

    fun complete(): CompletedSession {
        val completed = session.complete(elapsedRealtime())
        _snapshot.value = session.snapshot(elapsedRealtime())
        persist()
        return completed.copy(sensorActivity = sensorRecorder?.complete(_snapshot.value.elapsedPlanMs))
    }

    fun consumeSensorMeasurement(measurement: MotherboardMeasurement) {
        val current = snapshot.value
        val step = planStep(current.activeStepIndex) ?: return
        sensorRecorder?.consume(
            measurement = measurement,
            stepId = step.id,
            plannedActiveDurationMs = (step.durationSeconds * 1_000).toLong(),
            elapsedMs = current.elapsedPlanMs,
            stepStartMs = stepStartElapsedMs(current.activeStepIndex),
            isActive = current.phase is SessionPhase.Active,
        )
    }

    fun onStop() {
        if (session.isRunning(elapsedRealtime())) {
            pause()
        }
        audioCancellation.cancel()
        persist()
    }

    private fun publish(block: () -> WorkoutSnapshot): WorkoutSnapshot = block().also {
        _snapshot.value = it
        persist()
    }

    private fun persist() {
        val savedState = session.savedState(elapsedRealtime())
        savedStateHandle?.apply {
            this[COUNTDOWN_ELAPSED_MS] = savedState.countdownElapsedMs
            this[ELAPSED_PLAN_MS] = savedState.elapsedPlanMs
            this[PAUSED] = savedState.paused
            this[COMPLETED] = savedState.completed
            this[HAS_SESSION_STATE] = true
        }
    }

    private fun planStep(index: Int) = session.plan.steps.getOrNull(index)

    private fun stepStartElapsedMs(index: Int): Long = session.plan.steps.take(index).sumOf { (it.durationSeconds * 1_000).toLong() }

    companion object {
        internal fun restoredSessionState(savedStateHandle: SavedStateHandle): WorkoutSessionState? {
            if (savedStateHandle.get<Boolean>(HAS_SESSION_STATE) != true) return null
            return WorkoutSessionState(
                countdownElapsedMs = savedStateHandle[COUNTDOWN_ELAPSED_MS] ?: 0L,
                elapsedPlanMs = savedStateHandle[ELAPSED_PLAN_MS] ?: 0L,
                paused = savedStateHandle[PAUSED] ?: false,
                completed = savedStateHandle[COMPLETED] ?: false,
            )
        }

        private const val HAS_SESSION_STATE = "workout.has_session_state"
        private const val COUNTDOWN_ELAPSED_MS = "workout.countdown_elapsed_ms"
        private const val ELAPSED_PLAN_MS = "workout.elapsed_plan_ms"
        private const val PAUSED = "workout.paused"
        private const val COMPLETED = "workout.completed"
    }
}
