package com.hangten.android.board

import com.hangten.android.content.Board
import com.hangten.android.content.BoardHold
import org.junit.Assert.assertEquals
import org.junit.Test

class HoldTargetResolverTest {
    @Test
    fun semanticJugTargetResolvesOnlyJugsOnSelectedBoard() {
        val board = boardWith(
            BoardHold(id = "jug-left", name = "Jug left", kind = "jug", presentationId = "primary", geometry = emptyList()),
            BoardHold(id = "jug-right", name = "Jug right", kind = "jug", presentationId = "primary", geometry = emptyList()),
            BoardHold(id = "edge-20", name = "20 mm edge", kind = "edge", presentationId = "primary", geometry = emptyList()),
        )

        assertEquals(
            linkedSetOf("jug-left", "jug-right"),
            resolveTargets(listOf(HoldTarget(kind = "jug")), board),
        )
    }

    @Test
    fun explicitHoldIdsUseBoardOrderAndIgnoreIdsFromAnotherBoard() {
        val board = boardWith(
            BoardHold(id = "left", name = "Left", kind = "edge", presentationId = "primary", geometry = emptyList()),
            BoardHold(id = "right", name = "Right", kind = "edge", presentationId = "primary", geometry = emptyList()),
        )

        assertEquals(
            listOf("left", "right"),
            resolveTargets(listOf(HoldTarget(holdIds = listOf("right", "other-board", "left"))), board).toList(),
        )
    }

    private fun boardWith(vararg holds: BoardHold) = Board(
        id = "fixture-board",
        manufacturer = "Fixture",
        name = "Fixture Board",
        subtitle = "Fixture",
        productUrl = "https://example.invalid/fixture",
        aspectRatio = 2f,
        presentations = emptyList(),
        holds = holds.toList(),
    )
}
