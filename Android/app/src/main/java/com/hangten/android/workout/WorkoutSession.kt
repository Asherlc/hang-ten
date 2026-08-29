package com.hangten.android.workout

import com.hangten.android.content.TrainingPlan

sealed interface SessionPhase {
    data object StartCountdown : SessionPhase

    data class Active(
        val stepIndex: Int,
    ) : SessionPhase

    data object Paused : SessionPhase

    data object Complete : SessionPhase
}

data class WorkoutSnapshot(
    val phase: SessionPhase,
    val elapsedPlanMs: Long,
    val totalPlanMs: Long,
    val activeStepIndex: Int,
    val countdownRemainingMs: Long,
)

data class CompletedSession(
    val planId: String,
    val completedAtWallClockMs: Long,
    val elapsedDurationMs: Long,
)

data class WorkoutSessionState(
    val countdownElapsedMs: Long,
    val elapsedPlanMs: Long,
    val paused: Boolean,
    val completed: Boolean,
)

class WorkoutSession(
    private val plan: TrainingPlan,
    private val wallClockMillis: () -> Long = System::currentTimeMillis,
    restoredState: WorkoutSessionState? = null,
) {
    private val stepDurationsMs = plan.steps.map { (it.durationSeconds * MILLIS_PER_SECOND).toLong().coerceAtLeast(0L) }
    private val totalPlanMs = stepDurationsMs.sum()
    private var countdownElapsedMs = restoredState?.countdownElapsedMs?.coerceIn(0L, START_COUNTDOWN_MS) ?: 0L
    private var elapsedPlanMs = restoredState?.elapsedPlanMs?.coerceIn(0L, totalPlanMs) ?: 0L
    private var runningSinceMs: Long? = null
    private var paused = restoredState?.paused == true
    private var completedElapsedMs: Long? = if (restoredState?.completed == true) elapsedPlanMs else null

    fun start(nowMs: Long): WorkoutSnapshot {
        if (runningSinceMs == null && !paused && completedElapsedMs == null) {
            runningSinceMs = nowMs
        }
        return snapshot(nowMs)
    }

    fun pause(nowMs: Long): WorkoutSnapshot {
        if (isRunning(nowMs)) {
            apply(progressAt(nowMs))
            runningSinceMs = null
            paused = true
        }
        return snapshot(nowMs)
    }

    fun resume(nowMs: Long): WorkoutSnapshot {
        if (paused && completedElapsedMs == null && elapsedPlanMs < totalPlanMs) {
            runningSinceMs = nowMs
            paused = false
        }
        return snapshot(nowMs)
    }

    fun snapshot(nowMs: Long): WorkoutSnapshot {
        val progress = progressAt(nowMs)
        val elapsed = completedElapsedMs ?: progress.elapsedPlanMs
        val countdownRemaining = if (completedElapsedMs == null && !paused) {
            (START_COUNTDOWN_MS - progress.countdownElapsedMs).coerceAtLeast(0L)
        } else {
            0L
        }
        return WorkoutSnapshot(
            phase = phaseFor(elapsed, countdownRemaining),
            elapsedPlanMs = elapsed,
            totalPlanMs = totalPlanMs,
            activeStepIndex = activeStepIndex(elapsed),
            countdownRemainingMs = countdownRemaining,
        )
    }

    fun complete(nowMs: Long): CompletedSession {
        val progress = progressAt(nowMs)
        apply(progress)
        completedElapsedMs = progress.elapsedPlanMs
        runningSinceMs = null
        paused = false
        return CompletedSession(
            planId = plan.id,
            completedAtWallClockMs = wallClockMillis(),
            elapsedDurationMs = progress.elapsedPlanMs,
        )
    }

    internal fun isRunning(nowMs: Long): Boolean = runningSinceMs != null && phaseFor(
        progressAt(nowMs).elapsedPlanMs,
        (START_COUNTDOWN_MS - progressAt(nowMs).countdownElapsedMs).coerceAtLeast(0L),
    ) !is SessionPhase.Complete

    internal fun hasStarted(): Boolean = runningSinceMs != null || countdownElapsedMs > 0L || elapsedPlanMs > 0L || paused || completedElapsedMs != null

    internal fun savedState(nowMs: Long): WorkoutSessionState {
        val progress = progressAt(nowMs)
        return WorkoutSessionState(
            countdownElapsedMs = progress.countdownElapsedMs,
            elapsedPlanMs = completedElapsedMs ?: progress.elapsedPlanMs,
            paused = paused || runningSinceMs != null,
            completed = completedElapsedMs != null,
        )
    }

    private fun progressAt(nowMs: Long): Progress {
        val elapsedSinceLastStart = runningSinceMs?.let { (nowMs - it).coerceAtLeast(0L) } ?: 0L
        val countdownToFinish = (START_COUNTDOWN_MS - countdownElapsedMs).coerceAtLeast(0L)
        val countdownAdvance = elapsedSinceLastStart.coerceAtMost(countdownToFinish)
        val planAdvance = (elapsedSinceLastStart - countdownAdvance).coerceAtLeast(0L)
        return Progress(
            countdownElapsedMs = (countdownElapsedMs + countdownAdvance).coerceAtMost(START_COUNTDOWN_MS),
            elapsedPlanMs = (elapsedPlanMs + planAdvance).coerceAtMost(totalPlanMs),
        )
    }

    private fun apply(progress: Progress) {
        countdownElapsedMs = progress.countdownElapsedMs
        elapsedPlanMs = progress.elapsedPlanMs
    }

    private fun phaseFor(elapsed: Long, countdownRemaining: Long): SessionPhase = when {
        completedElapsedMs != null || elapsed >= totalPlanMs && countdownRemaining == 0L -> SessionPhase.Complete
        paused -> SessionPhase.Paused
        countdownRemaining > 0L -> SessionPhase.StartCountdown
        else -> SessionPhase.Active(activeStepIndex(elapsed))
    }

    private fun activeStepIndex(elapsed: Long): Int {
        if (stepDurationsMs.isEmpty()) return 0
        var cumulative = 0L
        stepDurationsMs.forEachIndexed { index, duration ->
            cumulative += duration
            if (elapsed < cumulative) return index
        }
        return stepDurationsMs.lastIndex
    }

    private data class Progress(
        val countdownElapsedMs: Long,
        val elapsedPlanMs: Long,
    )

    private companion object {
        const val MILLIS_PER_SECOND = 1_000f
        const val START_COUNTDOWN_MS = 3_000L
    }
}
