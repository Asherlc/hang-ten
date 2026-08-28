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
                audioCoach = FakeAudioCoach(),
                onSessionEnded = {},
            )
        }

        composeRule.onNodeWithContentDescription("Current task")
            .assert(SemanticsMatcher.expectValue(SemanticsProperties.StateDescription, "Fixture hang"))
        composeRule.onNodeWithText("Fixture hang").assertIsDisplayed()
        composeRule.onNodeWithContentDescription("Active board holds").assertIsDisplayed()
        composeRule.onNodeWithContentDescription("Pause workout").performClick()
        composeRule.onNodeWithContentDescription("Resume workout").assertIsDisplayed()
        composeRule.onNodeWithContentDescription("End session").assertIsDisplayed()
    }
}
