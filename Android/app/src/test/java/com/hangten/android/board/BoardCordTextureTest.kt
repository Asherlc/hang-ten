package com.hangten.android.board

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class BoardCordTextureTest {
    @Test
    fun horizontalCordFibersMatchWorkbenchOffsetsSpacingOpacityAndWidths() {
        val marks = routedCordFiberMarks(
            path = BoardPath(
                listOf(
                    BoardPathCommand.MoveTo(0f, 0f),
                    BoardPathCommand.LineTo(100f, 0f),
                ),
            ),
            diameter = 10f,
        )

        assertMark(
            marks[0],
            color = RoutedCordFiberColor.Braid0,
            startX = 1.5f,
            startY = -3.4f,
            endX = 5.3f,
            endY = 2.9f,
            opacity = 0.58f,
            width = 0.55f,
        )
        assertMark(
            marks[1],
            color = RoutedCordFiberColor.Braid1,
            startX = 4.092f,
            startY = 3.1f,
            endX = 7.492f,
            endY = -2.8f,
            opacity = 0.46f,
            width = 0.45f,
        )
        assertMark(
            marks[2],
            color = RoutedCordFiberColor.Dark,
            startX = 3.096f,
            startY = -2.5f,
            endX = 6.296f,
            endY = 1.3f,
            opacity = 0.36f,
            width = 0.26f,
        )
        assertEquals(3.4f + 4.6f - 1.9f, marks[3].start.x, 0.0001f)
    }

    @Test
    fun fiberOffsetsRotateWithTheLocalPathTangent() {
        val marks = routedCordFiberMarks(
            path = BoardPath(
                listOf(
                    BoardPathCommand.MoveTo(0f, 0f),
                    BoardPathCommand.LineTo(0f, 100f),
                ),
            ),
            diameter = 10f,
        )

        assertMark(
            marks.first(),
            color = RoutedCordFiberColor.Braid0,
            startX = 3.4f,
            startY = 1.5f,
            endX = -2.9f,
            endY = 5.3f,
            opacity = 0.58f,
            width = 0.55f,
        )
    }

    @Test
    fun disconnectedSubpathsDoNotCreateFibersAcrossTheGap() {
        val marks = routedCordFiberMarks(
            path = BoardPath(
                listOf(
                    BoardPathCommand.MoveTo(0f, 0f),
                    BoardPathCommand.LineTo(30f, 0f),
                    BoardPathCommand.MoveTo(100f, 0f),
                    BoardPathCommand.LineTo(130f, 0f),
                ),
            ),
            diameter = 10f,
        )

        assertTrue(marks.any { it.start.x < 30f })
        assertTrue(marks.any { it.start.x > 100f })
        assertTrue(marks.none { it.start.x in 35f..95f || it.end.x in 35f..95f })
    }

    private fun assertMark(
        actual: RoutedCordFiberMark,
        color: RoutedCordFiberColor,
        startX: Float,
        startY: Float,
        endX: Float,
        endY: Float,
        opacity: Float,
        width: Float,
    ) {
        assertEquals(color, actual.color)
        assertEquals(startX, actual.start.x, 0.0001f)
        assertEquals(startY, actual.start.y, 0.0001f)
        assertEquals(endX, actual.end.x, 0.0001f)
        assertEquals(endY, actual.end.y, 0.0001f)
        assertEquals(opacity, actual.opacity, 0.0001f)
        assertEquals(width, actual.width, 0.0001f)
    }
}
