package com.hangten.android.board

import com.hangten.android.content.BoardCordRect
import com.hangten.android.content.BoardCordRig
import com.hangten.android.content.BoardCordSize
import com.hangten.android.content.BoardGeometryRotationAnchor
import com.hangten.android.content.BoardPresentation
import com.hangten.android.content.BoardRoutedCordLayer
import com.hangten.android.content.BoardRoutedCordPairing
import com.hangten.android.content.BoardRoutedCordPort
import com.hangten.android.content.BoardRoutedCordSpace
import com.hangten.android.content.BoardRoutedCordStyle
import com.hangten.android.content.BoardRoutedCordTensionGroup
import com.hangten.android.content.Point
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Test

class BoardRoutedCordRigGeometryTest {
    @Test
    fun bodyPortRotatesClockwiseAtEverySupportedAngleWhileWorldPortStaysFixed() {
        val expectedBodyPoints = listOf(
            0f to Point(30f, 60f),
            45f to Point(28.7868f, 42.9289f),
            90f to Point(40f, 30f),
            180f to Point(70f, 40f),
        )

        expectedBodyPoints.forEach { (rotationDegrees, expectedBodyPoint) ->
            val geometry = resolveRoutedCordRigGeometry(
                rig = routedRig(),
                presentation = presentation(rotationDegrees),
                canvasWidth = 100f,
                canvasHeight = 100f,
            )

            assertNotNull("Expected geometry at $rotationDegrees degrees", geometry)
            assertPoint(expectedBodyPoint, geometry!!.portPoints.getValue("body"))
            assertPoint(Point(50f, 20f), geometry.portPoints.getValue("world"))
            assertEquals(BoardBounds(0f, 0f, 100f, 100f), geometry.sceneBounds)
            assertEquals(BoardBounds(10f, 20f, 80f, 60f), geometry.sourceBounds)
            assertEquals(BoardBounds(20f, 30f, 60f, 40f), geometry.faceBounds)
        }
    }

    private fun routedRig() = BoardCordRig.Routed(
        sceneSize = BoardCordSize(100f, 100f),
        sourceFrame = BoardCordRect(10f, 20f, 80f, 60f),
        innerFaceFrame = BoardCordRect(10f, 10f, 60f, 40f),
        style = BoardRoutedCordStyle(
            diameter = 4f,
            outlineColor = "#101010",
            baseColor = "#2255AA",
            braidColors = listOf("#FFD000", "#0055CC"),
        ),
        ports = listOf(
            BoardRoutedCordPort("body", BoardRoutedCordSpace.Body, Point(20f, 40f)),
            BoardRoutedCordPort("world", BoardRoutedCordSpace.World, Point(40f, 0f)),
        ),
        tensionGroups = listOf(
            BoardRoutedCordTensionGroup(
                id = "main",
                bodyPortIds = listOf("body"),
                worldPortIds = listOf("world"),
                pairing = BoardRoutedCordPairing.Declared,
                layer = BoardRoutedCordLayer.BehindFace,
            ),
        ),
        paths = emptyList(),
        occlusions = emptyList(),
    )

    private fun presentation(rotationDegrees: Float) = BoardPresentation(
        id = "position-$rotationDegrees",
        name = "Position",
        assetPath = "assets/primary.png",
        aspectRatio = 1f,
        isDefault = rotationDegrees == 0f,
        sourcePresentationId = if (rotationDegrees == 0f) null else "primary",
        rotationDegrees = if (rotationDegrees == 0f) null else rotationDegrees,
        geometryRotationAnchor = if (rotationDegrees == 0f) {
            null
        } else {
            BoardGeometryRotationAnchor.Center
        },
    )

    private fun assertPoint(expected: Point, actual: Point) {
        assertEquals(expected.x, actual.x, 0.0001f)
        assertEquals(expected.y, actual.y, 0.0001f)
    }
}
