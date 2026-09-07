package com.hangten.android.board

import com.hangten.android.content.BoardCordRect
import com.hangten.android.content.BoardCordRig
import com.hangten.android.content.BoardCordSize
import com.hangten.android.content.BoardGeometry
import com.hangten.android.content.BoardGeometryRotationAnchor
import com.hangten.android.content.BoardPresentation
import com.hangten.android.content.HoldShape
import com.hangten.android.content.NormalizedFrame
import com.hangten.android.content.Point
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test
import kotlin.math.hypot
import kotlin.math.min
import kotlin.math.tan

class BoardCordRigGeometryTest {
    private val rig = BoardCordRig.DirectTwoAnchor(
        sceneSize = BoardCordSize(width = 1200f, height = 1464f),
        sourceFrame = BoardCordRect(x = 0f, y = 214f, width = 1200f, height = 1250f),
        innerFaceFrame = BoardCordRect(x = -100f, y = -10f, width = 1400f, height = 1400f),
        attachmentPoints = listOf(Point(276f, 804f), Point(920f, 804f)),
        pullPoint = Point(600f, 71.5f),
        eyeletRadius = 34f,
    )

    @Test
    fun uprightRigMapsSquareFaceIntoTallSceneWithoutRotatingWorldUpPullPoint() {
        val geometry = resolveDirectTwoAnchorCordGeometry(
            rig = rig,
            presentation = presentation(isInverted = false),
            canvasWidth = 1200f,
            canvasHeight = 1464f,
        )!!

        assertEquals(BoardBounds(0f, 0f, 1200f, 1464f), geometry.sceneBounds)
        assertEquals(BoardBounds(-100f, 204f, 1400f, 1400f), geometry.faceBounds)
        assertPoint(Point(276f, 1018f), geometry.projectedAttachments[0])
        assertPoint(Point(920f, 1018f), geometry.projectedAttachments[1])
        assertPoint(Point(600f, 285.5f), geometry.pullPoint)
        assertPoint(Point(600f, 285.5f), geometry.strands[0].start)
        assertPoint(Point(600f, 285.5f), geometry.strands[1].start)
        assertRoundedApexPath(
            path = geometry.tensionPath,
            first = Point(276f, 1018f),
            apex = geometry.pullPoint,
            last = Point(920f, 1018f),
        )
    }

    @Test
    fun invertedRigRotatesFaceClockwiseInPlaneAndPairsStrandsByScreenX() {
        val geometry = resolveDirectTwoAnchorCordGeometry(
            rig = rig,
            presentation = presentation(isInverted = true),
            canvasWidth = 1200f,
            canvasHeight = 1464f,
        )!!

        assertEquals(BoardInPlaneTransform(-1f, 0f, 0f, -1f, 1200f, 1808f), geometry.faceTransform)
        assertPoint(Point(924f, 790f), geometry.projectedAttachments[0])
        assertPoint(Point(280f, 790f), geometry.projectedAttachments[1])
        assertEquals(listOf(Point(280f, 790f), Point(924f, 790f)), geometry.pairedAttachments)
        assertPoint(Point(280f, 790f), geometry.strands[0].end)
        assertPoint(Point(924f, 790f), geometry.strands[1].end)
        assertPoint(Point(600f, 285.5f), geometry.pullPoint)
        assertPoint(Point(880f, 1044f), geometry.projectFacePoint(Point(0.3f, 0.4f)))
    }

    @Test
    fun arbitraryRotationTurnsFaceAndAttachmentsButLeavesSupportWorldUp() {
        val geometry = resolveDirectTwoAnchorCordGeometry(
            rig = rig,
            presentation = presentation(rotationDegrees = 90f),
            canvasWidth = 1200f,
            canvasHeight = 1464f,
        )!!

        assertTransform(
            BoardInPlaneTransform(0f, 1f, -1f, 0f, 1504f, 304f),
            geometry.faceTransform,
        )
        assertPoint(Point(486f, 580f), geometry.projectedAttachments[0])
        assertPoint(Point(486f, 1224f), geometry.projectedAttachments[1])
        assertPoint(Point(600f, 285.5f), geometry.pullPoint)
        assertPoint(Point(600f, 285.5f), geometry.strands[0].start)
        assertPoint(Point(600f, 285.5f), geometry.strands[1].start)
        assertRoundedApexPath(
            path = geometry.tensionPath,
            first = Point(486f, 580f),
            apex = geometry.pullPoint,
            last = Point(486f, 1224f),
        )
    }

    @Test
    fun uniformScaleTransformsBodyAndEyeletGeometryButLeavesWorldPullFixed() {
        val geometry = resolveDirectTwoAnchorCordGeometry(
            rig = rig,
            presentation = presentation(geometryScale = 0.5f).copy(
                geometryRotationAnchor = BoardGeometryRotationAnchor.Center,
            ),
            canvasWidth = 1200f,
            canvasHeight = 1464f,
        )!!

        assertTransform(
            BoardInPlaneTransform(0.5f, 0f, 0f, 0.5f, 300f, 366f),
            geometry.faceTransform,
        )
        assertPoint(Point(438f, 875f), geometry.projectedAttachments[0])
        assertPoint(Point(760f, 875f), geometry.projectedAttachments[1])
        assertPoint(Point(600f, 285.5f), geometry.pullPoint)
        assertEquals(0.5f, geometry.geometryScale, 0.0001f)
        val first = geometry.pairedAttachments.first()
        val last = geometry.pairedAttachments.last()
        val incomingLength = hypot(first.x - geometry.pullPoint.x, first.y - geometry.pullPoint.y)
        val outgoingLength = hypot(last.x - geometry.pullPoint.x, last.y - geometry.pullPoint.y)
        val incomingRayX = (first.x - geometry.pullPoint.x) / incomingLength
        val incomingRayY = (first.y - geometry.pullPoint.y) / incomingLength
        val outgoingRayX = (last.x - geometry.pullPoint.x) / outgoingLength
        val outgoingRayY = (last.y - geometry.pullPoint.y) / outgoingLength
        val angle = kotlin.math.acos(
            (incomingRayX * outgoingRayX + incomingRayY * outgoingRayY).coerceIn(-1f, 1f),
        )
        val expectedTrim = min(1.25f * 31f / tan(angle / 2f), 0.15f * min(incomingLength, outgoingLength))
        val incomingTrim = geometry.tensionPath.commands[1] as BoardPathCommand.LineTo
        assertEquals(
            expectedTrim,
            hypot(incomingTrim.x - geometry.pullPoint.x, incomingTrim.y - geometry.pullPoint.y),
            0.001f,
        )
    }

    @Test
    fun roundedApexSplitsLargeTurnsAndFallsBackOnlyForDegenerateFiniteGeometry() {
        val rounded = pathThroughRoundedWorldApex(
            legEndpoints = listOf(Point(-10f, 100f), Point(10f, 100f)),
            apex = Point(0f, 0f),
            cordDiameter = 10f,
        )
        assertEquals(2, rounded.commands.count { it is BoardPathCommand.CubicTo })
        assertTrue(rounded.commands.none { it == BoardPathCommand.LineTo(0f, 0f) })

        val degenerate = pathThroughRoundedWorldApex(
            legEndpoints = listOf(Point(-10f, 0f), Point(10f, 0f)),
            apex = Point(0f, 0f),
            cordDiameter = 10f,
        )
        assertEquals(
            listOf(
                BoardPathCommand.MoveTo(-10f, 0f),
                BoardPathCommand.LineTo(0f, 0f),
                BoardPathCommand.LineTo(10f, 0f),
            ),
            degenerate.commands,
        )
    }

    @Test
    fun arbitraryRotationTransformsRoundedHoldOutlineInsteadOfKeepingAxisAlignedBounds() {
        val hold = BoardGeometry(
            frame = NormalizedFrame(x = 0.4f, y = 0.4f, width = 0.2f, height = 0.1f),
            shape = HoldShape.RoundedRect(cornerRadiusFraction = 0.2f),
        )
        val transform = BoardInPlaneTransform.rotatedAround(
            BoardBounds(0f, 0f, 100f, 100f),
            BoardGeometryRotationAnchor.Center,
            45f,
        )

        val transformed = hold.toBoardPath(BoardBounds(0f, 0f, 100f, 100f))
            .transformed(transform)

        assertNull(transformed.roundedRectangle)
        assertEquals(10, transformed.commands.size)
    }

    @Test
    fun zeroSizedCanvasDoesNotProduceNonFiniteRigGeometry() {
        assertNull(
            resolveDirectTwoAnchorCordGeometry(
                rig = rig,
                presentation = presentation(isInverted = false),
                canvasWidth = 0f,
                canvasHeight = 1464f,
            ),
        )
        assertNull(
            resolveDirectTwoAnchorCordGeometry(
                rig = rig,
                presentation = presentation(isInverted = false),
                canvasWidth = 1200f,
                canvasHeight = 0f,
            ),
        )
    }

    @Test
    fun holdPathUsesTheSameInnerFaceBoundsAndInPlaneTransformAsArtwork() {
        val rigGeometry = resolveDirectTwoAnchorCordGeometry(
            rig = rig,
            presentation = presentation(isInverted = true),
            canvasWidth = 1200f,
            canvasHeight = 1464f,
        )!!
        val hold = BoardGeometry(
            frame = NormalizedFrame(x = 0.2f, y = 0.3f, width = 0.4f, height = 0.2f),
            shape = HoldShape.RoundedRect(cornerRadiusFraction = 0.2f),
        )

        val rounded = hold.toBoardPath(rigGeometry.faceBounds)
            .transformed(rigGeometry.faceTransform)
            .roundedRectangle!!

        assertEquals(460f, rounded.left, 0.0001f)
        assertEquals(904f, rounded.top, 0.0001f)
        assertEquals(1020f, rounded.right, 0.0001f)
        assertEquals(1184f, rounded.bottom, 0.0001f)
        assertEquals(56f, rounded.radiusX, 0.0001f)
        assertEquals(56f, rounded.radiusY, 0.0001f)
    }

    private fun presentation(
        isInverted: Boolean = false,
        rotationDegrees: Float? = null,
        geometryScale: Float? = null,
    ) = BoardPresentation(
        id = if (isInverted || rotationDegrees != null || geometryScale != null) {
            "primary-transformed"
        } else {
            "primary"
        },
        name = "Primary",
        assetPath = "assets/primary.png",
        aspectRatio = 1200f / 1464f,
        isDefault = !isInverted,
        sourcePresentationId = if (isInverted || rotationDegrees != null || geometryScale != null) {
            "primary"
        } else {
            null
        },
        isInverted = isInverted,
        rotationDegrees = rotationDegrees,
        geometryScale = geometryScale,
        geometryRotationAnchor = if (isInverted || rotationDegrees != null || geometryScale != null) {
            BoardGeometryRotationAnchor(0.5f, 113f / 183f)
        } else {
            null
        },
        cordRig = if (isInverted || rotationDegrees != null) null else rig,
    )

    private fun assertTransform(expected: BoardInPlaneTransform, actual: BoardInPlaneTransform) {
        assertEquals(expected.a, actual.a, 0.0001f)
        assertEquals(expected.b, actual.b, 0.0001f)
        assertEquals(expected.c, actual.c, 0.0001f)
        assertEquals(expected.d, actual.d, 0.0001f)
        assertEquals(expected.tx, actual.tx, 0.0001f)
        assertEquals(expected.ty, actual.ty, 0.0001f)
    }

    private fun assertRoundedApexPath(path: BoardPath, first: Point, apex: Point, last: Point) {
        assertEquals(BoardPathCommand.MoveTo(first.x, first.y), path.commands.first())
        assertEquals(BoardPathCommand.LineTo(last.x, last.y), path.commands.last())
        assertTrue(path.commands[1] is BoardPathCommand.LineTo)
        assertTrue(path.commands.drop(2).dropLast(1).all { it is BoardPathCommand.CubicTo })
        assertTrue(path.commands.drop(2).dropLast(1).isNotEmpty())
        assertTrue(path.commands.none { it == BoardPathCommand.LineTo(apex.x, apex.y) })
        path.commands.forEach { command ->
            when (command) {
                is BoardPathCommand.MoveTo -> assertTrue(command.x.isFinite() && command.y.isFinite())
                is BoardPathCommand.LineTo -> assertTrue(command.x.isFinite() && command.y.isFinite())
                is BoardPathCommand.QuadTo -> Unit
                is BoardPathCommand.CubicTo -> assertTrue(
                    listOf(
                        command.control1X,
                        command.control1Y,
                        command.control2X,
                        command.control2Y,
                        command.x,
                        command.y,
                    ).all(Float::isFinite),
                )
                BoardPathCommand.Close -> Unit
            }
        }
    }

    private fun assertPoint(expected: Point, actual: Point) {
        assertEquals(expected.x, actual.x, 0.0001f)
        assertEquals(expected.y, actual.y, 0.0001f)
    }
}
