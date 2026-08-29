package com.hangten.android.ui

import androidx.activity.ComponentActivity
import androidx.compose.ui.test.SemanticsMatcher
import androidx.compose.ui.test.assert
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.junit4.createAndroidComposeRule
import androidx.compose.ui.test.onNodeWithContentDescription
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.compose.ui.semantics.SemanticsProperties
import androidx.compose.foundation.layout.Box
import androidx.compose.ui.Modifier
import androidx.compose.runtime.mutableStateOf
import androidx.lifecycle.Lifecycle
import com.hangten.android.workout.SessionPhase
import org.junit.Rule
import org.junit.Test

class WorkoutScreenTest {
    @get:Rule
    val composeRule = createAndroidComposeRule<ComponentActivity>()

    @Test
    fun workoutScreenShowsActiveTaskAndPauseControl() {
        composeRule.setContent {
            WorkoutScreen(
                plan = fixturePlan(),
                board = fixtureBoard(),
                audioCoach = RecordingAudioCoach(),
                onSessionEnded = {},
            )
        }

        composeRule.onNodeWithContentDescription("Current task")
            .assert(SemanticsMatcher.expectValue(SemanticsProperties.StateDescription, "Fixture hang"))
        composeRule.onNodeWithText("Fixture hang").assertIsDisplayed()
        composeRule.onNodeWithContentDescription("Active board holds").assertIsDisplayed()
        composeRule.onNodeWithContentDescription("Board Fixture Board")
            .assert(SemanticsMatcher.expectValue(SemanticsProperties.StateDescription, "Active holds: fixture-edge"))
        composeRule.onNodeWithContentDescription("Pause workout").performClick()
        composeRule.onNodeWithContentDescription("Resume workout").assertIsDisplayed()
        composeRule.onNodeWithContentDescription("End session").assertIsDisplayed()
    }

    @Test
    fun disposingWorkoutScreenCancelsScheduledAudio() {
        val audio = RecordingAudioCoach()
        val showWorkout = mutableStateOf(true)
        composeRule.setContent {
            if (showWorkout.value) {
                WorkoutScreen(
                    plan = fixturePlan(),
                    board = fixtureBoard(),
                    audioCoach = audio,
                    onSessionEnded = {},
                )
            } else Box(Modifier)
        }
        composeRule.runOnIdle { org.junit.Assert.assertEquals(1, audio.scheduledCountdowns.get()) }

        composeRule.runOnIdle { showWorkout.value = false }

        composeRule.runOnIdle { org.junit.Assert.assertEquals(1, audio.cancellations.get()) }
    }

    @Test
    fun activityStopCancelsScheduledAudio() {
        val audio = RecordingAudioCoach()
        composeRule.setContent {
            WorkoutScreen(
                plan = fixturePlan(),
                board = fixtureBoard(),
                audioCoach = audio,
                onSessionEnded = {},
            )
        }
        composeRule.activityRule.scenario.moveToState(Lifecycle.State.CREATED)

        composeRule.runOnIdle { org.junit.Assert.assertEquals(1, audio.cancellations.get()) }
    }
}
