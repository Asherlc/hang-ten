package com.hangten.android.ui

import androidx.activity.ComponentActivity
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.junit4.createAndroidComposeRule
import androidx.compose.ui.test.onNodeWithContentDescription
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.datastore.preferences.core.PreferenceDataStoreFactory
import com.hangten.android.audio.WorkoutAudioCoach
import com.hangten.android.content.Board
import com.hangten.android.content.BoardGeometry
import com.hangten.android.content.BoardHold
import com.hangten.android.content.BoardPresentation
import com.hangten.android.content.HoldShape
import com.hangten.android.content.NormalizedFrame
import com.hangten.android.content.TrainingPlan
import com.hangten.android.content.TrainingStep
import com.hangten.android.workout.SessionHistoryRepository
import kotlinx.coroutines.flow.MutableStateFlow
import org.junit.Rule
import org.junit.Test

class HangTenNavigationTest {
    @get:Rule
    val composeRule = createAndroidComposeRule<ComponentActivity>()

    @Test
    fun athleteCanSelectBoardPlanAndStartWorkout() {
        composeRule.setContent {
            HangTenApp(
                boards = listOf(fixtureBoard()),
                plans = listOf(fixturePlan()),
                historyRepository = historyRepository(),
                audioCoach = FakeAudioCoach(),
            )
        }

        composeRule.onNodeWithContentDescription("Plans").performClick()
        composeRule.onNodeWithContentDescription("Select board Fixture Board").performClick()
        composeRule.onNodeWithContentDescription("Select plan Fixture plan").performClick()
        composeRule.onNodeWithContentDescription("Train").performClick()
        composeRule.onNodeWithContentDescription("Start workout").performClick()

        composeRule.onNodeWithText("Fixture hang").assertIsDisplayed()
        composeRule.onNodeWithContentDescription("Pause workout").assertIsDisplayed()
    }

    private fun historyRepository(): SessionHistoryRepository = SessionHistoryRepository(
        PreferenceDataStoreFactory.create { composeRule.activity.cacheDir.resolve("navigation-history.preferences_pb") },
    )
}

internal fun fixturePlan() = TrainingPlan(
    id = "fixture-plan",
    title = "Fixture plan",
    subtitle = "Short fixture session",
    level = "Beginner",
    sourceLabel = "Fixture source",
    sourceUrl = null,
    provenance = "fixture",
    boardId = null,
    steps = listOf(
        TrainingStep(
            id = "fixture-step",
            title = "Fixture hang",
            instruction = "Hold the selected edges.",
            accessory = "",
            durationSeconds = 10f,
            phase = "hang",
            targets = emptyList(),
            segments = emptyList(),
            activeDurationSeconds = null,
            gripType = null,
            fingerConfiguration = null,
        ),
    ),
)

internal fun fixtureBoard() = Board(
    id = "fixture-board",
    manufacturer = "Fixture",
    name = "Fixture Board",
    subtitle = "Fixture board",
    productUrl = "https://example.invalid/fixture-board",
    aspectRatio = 2f,
    presentations = listOf(
        BoardPresentation(
            id = "primary",
            name = "Primary",
            assetPath = "missing.png",
            aspectRatio = 2f,
            isDefault = true,
        ),
    ),
    holds = listOf(
        BoardHold(
            id = "fixture-edge",
            name = "Fixture edge",
            kind = "edge",
            presentationId = "primary",
            geometry = listOf(
                BoardGeometry(
                    frame = NormalizedFrame(0.2f, 0.2f, 0.2f, 0.2f),
                    shape = HoldShape.RoundedRect(0.1f),
                ),
            ),
        ),
    ),
)

internal class FakeAudioCoach : WorkoutAudioCoach {
    override val instructionCoachingEnabled = MutableStateFlow(false)

    override fun scheduleCountdown(startElapsedMs: Long) = Unit

    override fun cancel() = Unit

    override fun speakInstruction(instruction: String) = Unit

    override fun setInstructionCoachingEnabled(enabled: Boolean) {
        instructionCoachingEnabled.value = enabled
    }
}
