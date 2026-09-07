package com.hangten.android.board

import com.hangten.android.content.Board
import com.hangten.android.content.BoardCordRect
import com.hangten.android.content.BoardCordRig
import com.hangten.android.content.BoardCordSize
import com.hangten.android.content.BoardGeometryRotationAnchor
import com.hangten.android.content.BoardPresentation
import com.hangten.android.content.BoardRoutedCordLayer
import com.hangten.android.content.BoardRoutedCordStyle
import com.hangten.android.content.Point
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class BoardExternalSlidingLoopGeometryTest {
    private val rig = BoardCordRig.ExternalSlidingLoop(
        sceneSize = BoardCordSize(120f, 170f),
        sourceFrame = BoardCordRect(0f, 0f, 120f, 170f),
        innerFaceFrame = BoardCordRect(30f, 70f, 60f, 30f),
        style = BoardRoutedCordStyle(10f, "#101010", "#2255AA", listOf("#FFD000", "#0055CC")),
        bodyContactFrame = BoardCordRect(30f, 70f, 60f, 30f),
        cornerRadius = 0f,
        clearance = 0f,
        pullPoint = Point(60f, 10f),
    )

    @Test
    fun uprightAndInvertedPositionsSlideToTheSameTangenciesAndGravityLowerReturn() {
        for (rotation in listOf(0f, 180f)) {
            val geometry = resolve(rotation)
            assertPoint(Point(25.7f, 67.4f), geometry.spans[0].bodyPoint, 0.3f)
            assertPoint(Point(94.3f, 67.4f), geometry.spans[1].bodyPoint, 0.3f)
            val returnPoints = geometry.paths.single().definingPoints
            assertEquals(105f, returnPoints.maxOf { it.y }, 0.0001f)
            assertEquals(geometry.spans[0].bodyPoint, returnPoints.first())
            assertEquals(geometry.spans[1].bodyPoint, returnPoints.last())
            assertTrue(geometry.spans.all { it.worldPoint == Point(60f, 10f) && it.bodyPoint.y > it.worldPoint.y })
            val tension = geometry.tensionPaths(BoardRoutedCordLayer.BehindFace).single()
            assertEquals(BoardPathCommand.MoveTo(geometry.spans[0].bodyPoint.x, geometry.spans[0].bodyPoint.y), tension.commands.first())
            assertEquals(BoardPathCommand.LineTo(geometry.spans[1].bodyPoint.x, geometry.spans[1].bodyPoint.y), tension.commands.last())
            assertTrue(tension.commands.any { it is BoardPathCommand.CubicTo })
            assertTrue(tension.commands.none { it == BoardPathCommand.LineTo(60f, 10f) })
            assertEquals(10f, geometry.cordDiameter, 0.0001f)
            assertTrue(geometry.paths.all { it.layer == BoardRoutedCordLayer.BehindFace })
            assertTrue(geometry.radialLips.isEmpty() && geometry.facePatches.isEmpty())
        }
    }

    @Test
    fun roundedTensionApexClearsInvisiblePullPointForOutlinedStroke() {
        val geometry = resolveExternalSlidingLoopCordGeometry(
            rig = rig.copy(
                sceneSize = BoardCordSize(100f, 100f),
                sourceFrame = BoardCordRect(0f, 0f, 100f, 100f),
                innerFaceFrame = BoardCordRect(25f, 40f, 50f, 20f),
                style = BoardRoutedCordStyle(4f, "#FF0000", "#FF0000", listOf("#FF0000", "#FF0000")),
                bodyContactFrame = BoardCordRect(25f, 40f, 50f, 20f),
                cornerRadius = 4f,
                clearance = 1f,
                pullPoint = Point(50f, 10f),
            ),
            presentation = presentation(180f),
            canvasWidth = 100f,
            canvasHeight = 100f,
        )!!

        val tension = geometry.tensionPaths(BoardRoutedCordLayer.BehindFace).single()
        val roundedCenterlineApex = tension.commands
            .filterIsInstance<BoardPathCommand.CubicTo>()
            .minBy { it.y }
        val centerlineClearance = roundedCenterlineApex.y - geometry.spans.first().worldPoint.y

        // This fixture's 1.5-diameter fillet clears the pull point by 0.7509 diameters.
        // A 0.74 floor leaves approximation tolerance while keeping the centerline more
        // than one 2x raster pixel beyond the 1.18-diameter outline's 0.59-diameter radius.
        assertTrue(
            "Expected enough apex clearance for the 1.18-diameter outline and raster fringe, got $centerlineClearance",
            centerlineClearance >= geometry.cordDiameter * 0.74f,
        )
    }

    @Test
    fun diagonalPositionReturnsThroughLowestCornerWithoutCrossingEitherLoadedLeg() {
        val geometry = resolve(45f)
        val points = geometry.paths.single().definingPoints
        assertEquals(121.8198f, points.maxOf { it.y }, 0.001f)
        points.zipWithNext().forEachIndexed { index, (start, end) ->
            geometry.spans.forEachIndexed spans@{ spanIndex, span ->
                if ((spanIndex == 0 && index == 0) || (spanIndex == 1 && index == points.size - 2)) return@spans
                assertTrue(!properIntersection(span.worldPoint, span.bodyPoint, start, end))
            }
        }
    }

    @Test
    fun scaleAroundOffCenterAnchorKeepsCordClearanceAndWorldApexSceneSized() {
        val presentation = presentation(45f).copy(
            geometryScale = 0.5f,
            geometryRotationAnchor = BoardGeometryRotationAnchor(0.25f, 0.75f),
        )
        val geometry = resolveExternalSlidingLoopCordGeometry(rig, presentation, 120f, 170f)!!
        assertPoint(Point(34.8931f, 116.4832f), geometry.spans[0].bodyPoint)
        assertPoint(Point(76.4997f, 127.7313f), geometry.spans[1].bodyPoint)
        assertEquals(143.9905f, geometry.paths.single().definingPoints.maxOf { it.y }, 0.001f)
        assertEquals(Point(60f, 10f), geometry.spans[0].worldPoint)
        assertEquals(1f, geometry.scale, 0f)
        assertEquals(10f, geometry.cordDiameter, 0f)
    }

    @Test
    fun sourceOriginAndCanvasLetterboxingMoveBodyAndWorldTogetherBeforePresentationTransform() {
        val translatedRig = rig.copy(
            sceneSize = BoardCordSize(140f, 200f),
            sourceFrame = BoardCordRect(10f, 15f, 120f, 170f),
        )
        val geometry = resolveExternalSlidingLoopCordGeometry(translatedRig, presentation(0f), 280f, 440f)!!
        assertEquals(BoardBounds(0f, 20f, 280f, 400f), geometry.sceneBounds)
        assertEquals(BoardBounds(20f, 50f, 240f, 340f), geometry.sourceBounds)
        assertEquals(BoardBounds(80f, 190f, 120f, 60f), geometry.faceBounds)
        assertPoint(Point(140f, 70f), geometry.spans[0].worldPoint)
        assertEquals(260f, geometry.paths.single().definingPoints.maxOf { it.y }, 0.001f)
    }

    @Test
    fun invalidApexClippingAndNonFiniteInputsFailClosed() {
        val failures = listOf(
            rig.copy(pullPoint = Point(60f, 85f)) to "outside the expanded",
            rig.copy(pullPoint = Point(10f, 75f)) to "above the body",
            rig.copy(pullPoint = Point(60f, 1f)) to "style margin",
            rig.copy(bodyContactFrame = rig.bodyContactFrame.copy(x = -5f)) to "style margin",
            rig.copy(clearance = Float.NaN) to "finite and valid",
            rig.copy(cornerRadius = 16f) to "finite and valid",
        )
        failures.forEach { (invalid, reason) ->
            assertTrue(externalSlidingLoopPresentationValidationFailure(invalid, presentation(0f))!!.contains(reason))
            assertNull(resolveExternalSlidingLoopCordGeometry(invalid, presentation(0f), 120f, 170f))
        }
        assertNull(resolveExternalSlidingLoopCordGeometry(rig, presentation(0f), 0f, 170f))
        assertNull(resolveExternalSlidingLoopCordGeometry(rig, presentation(0f), Float.POSITIVE_INFINITY, 170f))
    }

    @Test
    fun canvasUsesCanonicalFaceAndSharedBraidStyleAtEveryPosition() {
        val canonical = presentation(0f).copy(id = "primary", sourcePresentationId = null, rotationDegrees = null, cordRig = rig)
        val aliases = listOf(45f, 180f).map(::presentation)
        val board = Board("demo", "Demo", "Demo", "Demo", "https://example.com", 120f / 170f, listOf(canonical) + aliases, emptyList())
        aliases.forEach { alias ->
            val canvas = boardCanvasGeometry(board, alias, 120f, 170f)!!
            assertEquals(canonical, board.artworkPresentation(alias))
            assertEquals(BoardBounds(30f, 70f, 60f, 30f), canvas.holdBounds)
            assertEquals(BoardInPlaneTransform.forPresentation(alias, BoardBounds(0f, 0f, 120f, 170f)), canvas.faceTransform)
            assertEquals(rig.style, canvas.routedStyle)
            assertNotNull(canvas.routedCordGeometry)
            assertEquals(
                listOf(
                    RoutedArtworkOperation.CordLayer(BoardRoutedCordLayer.BehindFace),
                    RoutedArtworkOperation.Face,
                    RoutedArtworkOperation.CordLayer(BoardRoutedCordLayer.AboveFace),
                    RoutedArtworkOperation.CordLayer(BoardRoutedCordLayer.Overpass),
                ),
                routedArtworkOperations(canvas.routedCordGeometry!!),
            )
        }
    }

    private fun resolve(rotation: Float) = resolveExternalSlidingLoopCordGeometry(rig, presentation(rotation), 120f, 170f)!!

    private fun presentation(rotation: Float) = BoardPresentation(
        id = "position-$rotation", name = "Position", assetPath = "assets/primary.png", aspectRatio = 120f / 170f,
        isDefault = false, sourcePresentationId = "primary", rotationDegrees = rotation,
    )

    private fun assertPoint(expected: Point, actual: Point, tolerance: Float = 0.001f) {
        assertEquals(expected.x, actual.x, tolerance)
        assertEquals(expected.y, actual.y, tolerance)
    }

    private fun properIntersection(a: Point, b: Point, c: Point, d: Point): Boolean {
        fun side(start: Point, end: Point, point: Point): Double =
            (end.x - start.x).toDouble() * (point.y - start.y) - (end.y - start.y).toDouble() * (point.x - start.x)
        return side(a, b, c) * side(a, b, d) < -1e-7 && side(c, d, a) * side(c, d, b) < -1e-7
    }
}
