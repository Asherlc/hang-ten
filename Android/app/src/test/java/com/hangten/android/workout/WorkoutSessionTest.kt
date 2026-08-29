package com.hangten.android.workout

import com.hangten.android.content.TrainingPlan
import com.hangten.android.content.TrainingStep
import org.junit.Assert.assertEquals
import org.junit.Test

class WorkoutSessionTest {
    @Test
    fun pauseFreezesTheActiveStepUntilExplicitResume() {
        val session = WorkoutSession(plan())

        session.start(nowMs = 1_000)
        session.pause(nowMs = 9_000)

        assertEquals(
            WorkoutSnapshot(
                phase = SessionPhase.Paused,
                elapsedPlanMs = 5_000,
                totalPlanMs = 20_000,
                activeStepIndex = 0,
                countdownRemainingMs = 0,
            ),
            session.snapshot(nowMs = 99_000),
        )

        session.resume(nowMs = 99_000)

        assertEquals(
            WorkoutSnapshot(
                phase = SessionPhase.Active(stepIndex = 0),
                elapsedPlanMs = 7_000,
                totalPlanMs = 20_000,
                activeStepIndex = 0,
                countdownRemainingMs = 0,
            ),
            session.snapshot(nowMs = 101_000),
        )
    }

    @Test
    fun startCountdownPrecedesFirstRoutineStepByThreeSeconds() {
        val session = WorkoutSession(plan())

        session.start(nowMs = 1_000)

        assertEquals(
            WorkoutSnapshot(
                phase = SessionPhase.StartCountdown,
                elapsedPlanMs = 0,
                totalPlanMs = 20_000,
                activeStepIndex = 0,
                countdownRemainingMs = 1_000,
            ),
            session.snapshot(nowMs = 3_000),
        )
        assertEquals(
            WorkoutSnapshot(
                phase = SessionPhase.Active(stepIndex = 0),
                elapsedPlanMs = 0,
                totalPlanMs = 20_000,
                activeStepIndex = 0,
                countdownRemainingMs = 0,
            ),
            session.snapshot(nowMs = 4_000),
        )
    }

    @Test
    fun elapsedProgressClampsAtTheTotalPlanDuration() {
        val session = WorkoutSession(plan())

        session.start(nowMs = 1_000)

        assertEquals(
            WorkoutSnapshot(
                phase = SessionPhase.Complete,
                elapsedPlanMs = 20_000,
                totalPlanMs = 20_000,
                activeStepIndex = 1,
                countdownRemainingMs = 0,
            ),
            session.snapshot(nowMs = 90_000),
        )
    }

    @Test
    fun viewModelOnStopPausesTheSessionAndCancelsAudio() {
        var nowMs = 1_000L
        var cancellationCount = 0
        val session = WorkoutSession(plan())
        val viewModel = WorkoutViewModel(
            session = session,
            elapsedRealtime = { nowMs },
            audioCancellation = WorkoutAudioCancellation { cancellationCount += 1 },
        )

        viewModel.start()
        nowMs = 9_000
        viewModel.onStop()
        nowMs = 99_000

        assertEquals(SessionPhase.Paused, session.snapshot(nowMs).phase)
        assertEquals(5_000, session.snapshot(nowMs).elapsedPlanMs)
        assertEquals(1, cancellationCount)
    }

    private fun plan(): TrainingPlan = TrainingPlan(
        id = "test-plan",
        title = "Test plan",
        subtitle = "",
        level = "",
        sourceLabel = "",
        sourceUrl = null,
        provenance = "",
        boardId = null,
        steps = listOf(step("first", 10f), step("second", 10f)),
    )

    private fun step(id: String, durationSeconds: Float) = TrainingStep(
        id = id,
        title = id,
        instruction = "",
        accessory = "",
        durationSeconds = durationSeconds,
        phase = "hang",
        targets = emptyList(),
        segments = emptyList(),
        activeDurationSeconds = null,
        gripType = null,
        fingerConfiguration = null,
    )
}
