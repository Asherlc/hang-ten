package com.hangten.android.content

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class BoardPresentationSelectionTest {
    @Test
    fun selectionRequiresEveryActiveHoldAndFallsBackFromInvalidPreference() {
        val board = pivotSelectionBoard()

        assertEquals(
            "rotated",
            board.presentationContaining(
                holdIds = setOf("shared", "rotation-only"),
                preferredPresentationId = "primary",
            )?.id,
        )
    }

    @Test
    fun selectionPrefersCurrentThenDefaultWhenSeveralPresentationsFit() {
        val board = pivotSelectionBoard()

        assertEquals(
            "rotated",
            board.presentationContaining(
                holdIds = setOf("shared"),
                preferredPresentationId = "rotated",
            )?.id,
        )
        assertEquals(
            "primary",
            board.presentationContaining(holdIds = setOf("shared"))?.id,
        )
    }

    @Test
    fun selectionDoesNotChooseAPresentationThatDropsAnActiveHold() {
        val board = pivotSelectionBoard()

        assertNull(
            board.presentationContaining(
                holdIds = setOf("shared", "back-only"),
                preferredPresentationId = "primary",
            ),
        )
    }

    @Test
    fun omittedAvailabilityKeepsEveryCanonicalHoldEligible() {
        val board = pivotSelectionBoard()

        assertEquals(
            "back",
            board.presentationContaining(
                holdIds = setOf("back-only"),
                preferredPresentationId = "back",
            )?.id,
        )
    }

    private fun pivotSelectionBoard(): Board = Board(
        id = "pivot-board",
        manufacturer = "Demo",
        name = "Pivot board",
        subtitle = "",
        productUrl = "https://example.com/pivot-board",
        aspectRatio = 1f,
        presentations = listOf(
            BoardPresentation(
                id = "primary",
                name = "Primary",
                assetPath = "assets/primary.png",
                aspectRatio = 1f,
                isDefault = true,
                availableHoldIds = listOf("shared"),
            ),
            BoardPresentation(
                id = "rotated",
                name = "Rotated",
                assetPath = "assets/primary.png",
                aspectRatio = 1f,
                isDefault = false,
                sourcePresentationId = "primary",
                rotationDegrees = 90f,
                availableHoldIds = listOf("shared", "rotation-only"),
            ),
            BoardPresentation(
                id = "back",
                name = "Back",
                assetPath = "assets/back.png",
                aspectRatio = 1f,
                isDefault = false,
            ),
        ),
        holds = listOf(
            BoardHold(
                id = "shared",
                name = "Shared hold",
                kind = "edge",
                presentationId = "primary",
                geometry = emptyList(),
            ),
            BoardHold(
                id = "rotation-only",
                name = "Rotation-only hold",
                kind = "edge",
                presentationId = "primary",
                geometry = emptyList(),
            ),
            BoardHold(
                id = "back-only",
                name = "Back-only hold",
                kind = "edge",
                presentationId = "back",
                geometry = emptyList(),
            ),
        ),
    )
}
