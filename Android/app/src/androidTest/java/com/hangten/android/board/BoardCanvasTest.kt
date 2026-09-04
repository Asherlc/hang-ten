package com.hangten.android.board

import android.graphics.Bitmap
import androidx.activity.ComponentActivity
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.size
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.graphics.toPixelMap
import androidx.compose.ui.semantics.SemanticsProperties
import androidx.compose.ui.test.SemanticsMatcher
import androidx.compose.ui.test.assert
import androidx.compose.ui.test.captureToImage
import androidx.compose.ui.test.click
import androidx.compose.ui.test.junit4.createAndroidComposeRule
import androidx.compose.ui.test.onNodeWithContentDescription
import androidx.compose.ui.test.performTouchInput
import androidx.compose.ui.unit.dp
import com.hangten.android.content.Board
import com.hangten.android.content.BoardCordRect
import com.hangten.android.content.BoardCordRig
import com.hangten.android.content.BoardCordSize
import com.hangten.android.content.BoardHold
import com.hangten.android.content.BoardPresentation
import com.hangten.android.content.BoardGeometry
import com.hangten.android.content.BoardRoutedCordLayer
import com.hangten.android.content.BoardRoutedCordOcclusion
import com.hangten.android.content.BoardRoutedCordPairing
import com.hangten.android.content.BoardRoutedCordPathCommand
import com.hangten.android.content.BoardRoutedCordPort
import com.hangten.android.content.BoardRoutedCordSpace
import com.hangten.android.content.BoardRoutedCordStyle
import com.hangten.android.content.BoardRoutedCordTensionGroup
import com.hangten.android.content.HoldShape
import com.hangten.android.content.NormalizedFrame
import com.hangten.android.content.Point
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
            click(percentOffset(x = 0.375f, y = 0.375f))
            click(percentOffset(x = 0.9f, y = 0.9f))
        }

        composeRule.runOnIdle {
            assertEquals(listOf("center-hold"), tappedHolds)
        }
    }

    @Test
    fun routedArtworkPreservesTransparencyAndDrawsEveryLayerInPhysicalOrder() {
        val rig = BoardCordRig.Routed(
            sceneSize = BoardCordSize(100f, 100f),
            sourceFrame = BoardCordRect(0f, 0f, 100f, 100f),
            innerFaceFrame = BoardCordRect(20f, 40f, 60f, 40f),
            style = BoardRoutedCordStyle(
                diameter = 6f,
                outlineColor = "#FF0000",
                baseColor = "#FF0000",
                braidColors = listOf("#FF0000", "#FF0000"),
            ),
            ports = listOf(
                BoardRoutedCordPort("body-behind", BoardRoutedCordSpace.Body, Point(50f, 70f)),
                BoardRoutedCordPort("world-behind", BoardRoutedCordSpace.World, Point(50f, 10f)),
                BoardRoutedCordPort("body-above", BoardRoutedCordSpace.Body, Point(30f, 70f)),
                BoardRoutedCordPort("world-above", BoardRoutedCordSpace.World, Point(30f, 10f)),
                BoardRoutedCordPort("body-overpass", BoardRoutedCordSpace.Body, Point(70f, 70f)),
                BoardRoutedCordPort("world-overpass", BoardRoutedCordSpace.World, Point(70f, 10f)),
            ),
            tensionGroups = listOf(
                tensionGroup("behind", "body-behind", "world-behind", BoardRoutedCordLayer.BehindFace),
                tensionGroup("above", "body-above", "world-above", BoardRoutedCordLayer.AboveFace),
                tensionGroup("overpass", "body-overpass", "world-overpass", BoardRoutedCordLayer.Overpass),
            ),
            paths = emptyList(),
            occlusions = listOf(
                BoardRoutedCordOcclusion.FacePatch(
                    commands = listOf(
                        BoardRoutedCordPathCommand.Move(Point(27f, 50f)),
                        BoardRoutedCordPathCommand.Line(Point(33f, 50f)),
                        BoardRoutedCordPathCommand.Line(Point(33f, 60f)),
                        BoardRoutedCordPathCommand.Line(Point(27f, 60f)),
                        BoardRoutedCordPathCommand.Close,
                    ),
                ),
            ),
        )
        val presentation = BoardPresentation(
            id = "primary",
            name = "Primary",
            assetPath = "assets/missing-raster-fixture.png",
            aspectRatio = 1f,
            isDefault = true,
            cordRig = rig,
        )
        val board = Board(
            id = "routed-raster-fixture",
            manufacturer = "Fixture",
            name = "Routed Raster Fixture",
            subtitle = "Fixture",
            productUrl = "https://example.invalid/routed-raster-fixture",
            aspectRatio = 1f,
            presentations = listOf(presentation),
            holds = emptyList(),
        )
        val faceBitmap = Bitmap.createBitmap(60, 40, Bitmap.Config.ARGB_8888).apply {
            eraseColor(android.graphics.Color.GREEN)
        }

        composeRule.setContent {
            // Node captures are composited by the host window; a sentinel behind the canvas
            // proves that routed artwork leaves pixels outside the scene transparent.
            Box(Modifier.size(200.dp).background(Color.Magenta)) {
                BoardCanvas(
                    board = board,
                    activeHoldIDs = emptySet(),
                    onHoldTap = {},
                    modifier = Modifier.size(200.dp),
                    imageOverride = faceBitmap.asImageBitmap(),
                )
            }
        }

        val pixels = composeRule.onNodeWithContentDescription("Board Routed Raster Fixture")
            .captureToImage()
            .toPixelMap()
        fun pixel(x: Float, y: Float): Color = pixels[
            (pixels.width * x).toInt().coerceIn(0, pixels.width - 1),
            (pixels.height * y).toInt().coerceIn(0, pixels.height - 1),
        ]

        assertColor(Color.Green, pixel(0.5f, 0.55f))
        assertColor(Color.Red, pixel(0.3f, 0.45f))
        assertColor(Color.Green, pixel(0.3f, 0.55f))
        assertColor(Color.Red, pixel(0.7f, 0.55f))
        assertColor(Color.Magenta, pixel(0.05f, 0.95f))
    }

    private fun tensionGroup(
        id: String,
        bodyPortId: String,
        worldPortId: String,
        layer: BoardRoutedCordLayer,
    ) = BoardRoutedCordTensionGroup(
        id = id,
        bodyPortIds = listOf(bodyPortId),
        worldPortIds = listOf(worldPortId),
        pairing = BoardRoutedCordPairing.Declared,
        layer = layer,
    )

    private fun assertColor(expected: Color, actual: Color) {
        assertEquals(expected.red, actual.red, 0.05f)
        assertEquals(expected.green, actual.green, 0.05f)
        assertEquals(expected.blue, actual.blue, 0.05f)
        assertEquals(expected.alpha, actual.alpha, 0.05f)
    }
}
