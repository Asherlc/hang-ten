package com.hangten.android.ui

import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.junit4.createAndroidComposeRule
import androidx.compose.ui.test.onNodeWithContentDescription
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.datastore.preferences.core.PreferenceDataStoreFactory
import androidx.test.platform.app.InstrumentationRegistry
import com.hangten.android.workout.SessionHistoryRepository
import org.junit.Assert.assertEquals
import org.junit.Rule
import org.junit.Test

class WorkoutPersistenceTest {
    @get:Rule
    val composeRule = createAndroidComposeRule<ComponentActivity>()

    @Test
    fun selectedBoardAndPlanSurviveActivityRecreation() {
        val context = InstrumentationRegistry.getInstrumentation().targetContext
        val historyRepository = SessionHistoryRepository(
            PreferenceDataStoreFactory.create { context.cacheDir.resolve("selection-recreation.preferences_pb") },
        )
        val content: @androidx.compose.runtime.Composable () -> Unit = {
            HangTenApp(
                boards = listOf(fixtureBoard()),
                plans = listOf(fixturePlan()),
                historyRepository = historyRepository,
                audioCoach = RecordingAudioCoach(),
            )
        }
        composeRule.setContent(content)
        composeRule.onNodeWithContentDescription("Plans").performClick()
        composeRule.onNodeWithContentDescription("Select board Fixture Board").performClick()
        composeRule.onNodeWithContentDescription("Select plan Fixture plan").performClick()

        composeRule.activityRule.scenario.recreate()
        composeRule.activityRule.scenario.onActivity { activity -> activity.setContent { content() } }

        composeRule.onNodeWithContentDescription("Train").performClick()
        composeRule.onNodeWithText("Fixture Board").assertIsDisplayed()
        composeRule.onNodeWithText("Fixture plan").assertIsDisplayed()
    }

    @Test
    fun pausedWorkoutRetainsItsSessionWithoutReschedulingCountdownAfterRecreation() {
        val audio = RecordingAudioCoach()
        val content: @androidx.compose.runtime.Composable () -> Unit = {
            WorkoutScreen(
                plan = fixturePlan(),
                board = fixtureBoard(),
                audioCoach = audio,
                onSessionEnded = {},
            )
        }
        composeRule.setContent(content)
        composeRule.activityRule.scenario.recreate()
        composeRule.activityRule.scenario.onActivity { activity -> activity.setContent { content() } }

        composeRule.onNodeWithContentDescription("Resume workout").assertIsDisplayed()
        composeRule.onNodeWithText("Fixture hang").assertIsDisplayed()
        composeRule.runOnIdle {
            assertEquals(1, audio.scheduledCountdowns.get())
            org.junit.Assert.assertTrue(audio.cancellations.get() >= 1)
        }
    }
}
