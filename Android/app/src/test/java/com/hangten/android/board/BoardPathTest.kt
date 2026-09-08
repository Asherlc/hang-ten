package com.hangten.android.board

import com.hangten.android.content.Board
import com.hangten.android.content.BoardGeometry
import com.hangten.android.content.BoardGeometryRotationAnchor
import com.hangten.android.content.BoardHold
import com.hangten.android.content.BoardPresentation
import com.hangten.android.content.HoldShape
import com.hangten.android.content.NormalizedFrame
import com.hangten.android.content.PathCommand
import com.hangten.android.content.Point
import org.junit.Assert.assertEquals
import org.junit.Test

class BoardPathTest {
    @Test
    fun boardPathClosesAtItsStartingPoint() {
        val geometry = BoardGeometry(
            frame = NormalizedFrame(x = 0.1f, y = 0.2f, width = 0.5f, height = 0.25f),
            shape = HoldShape.Path(
                listOf(
                    PathCommand.Move(Point(0f, 0f)),
                    PathCommand.Line(Point(1f, 0f)),
                    PathCommand.Quad(to = Point(1f, 1f), control = Point(1f, 0.5f)),
                    PathCommand.Curve(to = Point(0f, 1f), control1 = Point(0.75f, 1f), control2 = Point(0.25f, 1f)),
                    PathCommand.Close,
                ),
            ),
        )

        val path = geometry.toBoardPath(BoardBounds(left = 10f, top = 20f, width = 200f, height = 100f))

        assertEquals(
            listOf(
                BoardPathCommand.MoveTo(30f, 40f),
                BoardPathCommand.LineTo(130f, 40f),
                BoardPathCommand.QuadTo(controlX = 130f, controlY = 52.5f, x = 130f, y = 65f),
                BoardPathCommand.CubicTo(control1X = 105f, control1Y = 65f, control2X = 55f, control2Y = 65f, x = 30f, y = 65f),
                BoardPathCommand.Close,
            ),
            path.commands,
        )
        assertEquals(BoardPathCommand.MoveTo(30f, 40f), path.commands.first())
        assertEquals(BoardPathCommand.Close, path.commands.last())
    }

    @Test
    fun roundedRectangleUsesTheTransformedGeometryFrame() {
        val geometry = BoardGeometry(
            frame = NormalizedFrame(x = 0.25f, y = 0.1f, width = 0.5f, height = 0.6f),
            shape = HoldShape.RoundedRect(cornerRadiusFraction = 0.2f),
        )

        val rounded = geometry.toBoardPath(
            BoardBounds(left = 10f, top = 20f, width = 200f, height = 100f),
        ).roundedRectangle!!

        assertEquals(60f, rounded.left, 0.0001f)
        assertEquals(30f, rounded.top, 0.0001f)
        assertEquals(160f, rounded.right, 0.0001f)
        assertEquals(90f, rounded.bottom, 0.0001f)
        assertEquals(12f, rounded.radiusX, 0.0001f)
        assertEquals(12f, rounded.radiusY, 0.0001f)
    }

    @Test
    fun nonRigInvertedAliasProjectsCanonicalHoldAroundItsPresentationAnchor() {
        val canonical = presentation(id = "primary")
        val alias = presentation(
            id = "primary-inverted",
            sourcePresentationId = canonical.id,
            isInverted = true,
            rotationAnchor = BoardGeometryRotationAnchor(x = 0.25f, y = 0.25f),
        )
        val board = board(canonical, alias)

        val canvas = boardCanvasGeometry(board, alias, width = 200f, height = 100f)!!
        val projectedHold = board.holds.single().geometry.single()
            .toBoardPath(canvas.holdBounds)
            .transformed(canvas.faceTransform)
            .roundedRectangle!!

        assertEquals(BoardBounds(left = 0f, top = 0f, width = 200f, height = 100f), canvas.holdBounds)
        assertEquals(BoardInPlaneTransform(-1f, 0f, 0f, -1f, 100f, 50f), canvas.faceTransform)
        assertEquals(40f, projectedHold.left, 0.0001f)
        assertEquals(20f, projectedHold.top, 0.0001f)
        assertEquals(80f, projectedHold.right, 0.0001f)
        assertEquals(30f, projectedHold.bottom, 0.0001f)
        assertEquals(alias, board.artworkPresentation(alias))
        assertEquals(canonical.id, board.holdPresentationId(alias))
    }

    @Test
    fun nonRigCanonicalPresentationKeepsIdentityProjection() {
        val canonical = presentation(id = "primary")

        val canvas = boardCanvasGeometry(
            board(canonical),
            canonical,
            width = 200f,
            height = 100f,
        )!!

        assertEquals(BoardInPlaneTransform.Identity, canvas.faceTransform)
    }

    private fun presentation(
        id: String,
        sourcePresentationId: String? = null,
        isInverted: Boolean = false,
        rotationAnchor: BoardGeometryRotationAnchor? = null,
    ) = BoardPresentation(
        id = id,
        name = id,
        assetPath = "assets/$id.png",
        aspectRatio = 2f,
        isDefault = sourcePresentationId == null,
        sourcePresentationId = sourcePresentationId,
        isInverted = isInverted,
        geometryRotationAnchor = rotationAnchor,
    )

    private fun board(vararg presentations: BoardPresentation) = Board(
        id = "demo.board",
        manufacturer = "Demo",
        name = "Demo",
        subtitle = "Demo",
        productUrl = "https://example.com/demo",
        aspectRatio = 2f,
        presentations = presentations.toList(),
        holds = listOf(
            BoardHold(
                id = "edge",
                name = "Edge",
                kind = "edge",
                presentationId = "primary",
                geometry = listOf(
                    BoardGeometry(
                        frame = NormalizedFrame(x = 0.1f, y = 0.2f, width = 0.2f, height = 0.1f),
                        shape = HoldShape.RoundedRect(cornerRadiusFraction = 0.2f),
                    ),
                ),
            ),
        ),
    )
}
