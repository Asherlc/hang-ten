package com.hangten.android.board

import androidx.activity.ComponentActivity
import androidx.compose.ui.semantics.SemanticsProperties
import androidx.compose.ui.test.SemanticsMatcher
import androidx.compose.ui.test.assert
import androidx.compose.ui.test.click
import androidx.compose.ui.test.junit4.createAndroidComposeRule
import androidx.compose.ui.test.onNodeWithContentDescription
import androidx.compose.ui.test.performTouchInput
import androidx.compose.ui.geometry.Offset
import com.hangten.android.content.Board
import com.hangten.android.content.BoardHold
import com.hangten.android.content.BoardPresentation
import com.hangten.android.content.HoldShape
import com.hangten.android.content.BoardGeometry
import com.hangten.android.content.NormalizedFrame
import org.junit.Assert.assertEquals
import org.junit.Rule
import org.junit.Test

class BoardCanvasTest {
    @get:Rule
    val composeRule = createAndroidComposeRule<ComponentActivity>()

    @Test
    fun selectedSemanticTargetIsExposedAsActiveBoardSemantics() {
        val board = Board(
            id = "fixture-board",
            manufacturer = "Fixture",
            name = "Fixture Board",
            subtitle = "Fixture",
            productUrl = "https://example.invalid/fixture",
            aspectRatio = 2f,
            presentations = listOf(
                BoardPresentation(
                    id = "primary",
                    name = "Primary",
                    assetPath = "assets/missing-fixture.png",
                    aspectRatio = 2f,
                    isDefault = true,
                ),
            ),
            holds = listOf(
                BoardHold(
                    id = "jug-left",
                    name = "Jug left",
                    kind = "jug",
                    presentationId = "primary",
                    geometry = listOf(
                        BoardGeometry(
                            frame = NormalizedFrame(0f, 0f, 0.5f, 0.5f),
                            shape = HoldShape.RoundedRect(0.2f),
                        ),
                    ),
                ),
            ),
        )

        composeRule.setContent {
            BoardCanvas(
                board = board,
                activeHoldIDs = resolveTargets(listOf(HoldTarget(kind = "jug")), board),
                onHoldTap = {},
            )
        }

        composeRule.onNodeWithContentDescription("Board Fixture Board")
            .assert(SemanticsMatcher.expectValue(SemanticsProperties.StateDescription, "Active holds: jug-left"))
    }

    @Test
    fun transformedHoldPathInvokesTapOnlyInsideItsGeometry() {
        val board = Board(
            id = "fixture-board",
            manufacturer = "Fixture",
            name = "Fixture Board",
            subtitle = "Fixture",
            productUrl = "https://example.invalid/fixture",
            aspectRatio = 2f,
            presentations = listOf(
                BoardPresentation(
                    id = "primary",
                    name = "Primary",
                    assetPath = "assets/missing-fixture.png",
                    aspectRatio = 2f,
                    isDefault = true,
                ),
            ),
            holds = listOf(
                BoardHold(
                    id = "center-hold",
                    name = "Center hold",
                    kind = "edge",
                    presentationId = "primary",
                    geometry = listOf(
                        BoardGeometry(
                            frame = NormalizedFrame(0.25f, 0.25f, 0.25f, 0.25f),
                            shape = HoldShape.RoundedRect(0f),
                        ),
                    ),
                ),
            ),
        )
        val tappedHolds = mutableListOf<String>()

        composeRule.setContent {
            BoardCanvas(
                board = board,
                activeHoldIDs = emptySet(),
                onHoldTap = { tappedHolds += it },
            )
        }

        composeRule.onNodeWithContentDescription("Board Fixture Board").performTouchInput {
            click(Offset(x = 300f, y = 180f))
            click(Offset(x = 1000f, y = 500f))
        }

        composeRule.runOnIdle {
            assertEquals(listOf("center-hold"), tappedHolds)
        }
    }
}
