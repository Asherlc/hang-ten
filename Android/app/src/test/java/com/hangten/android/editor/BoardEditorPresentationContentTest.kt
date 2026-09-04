package com.hangten.android.editor

import com.hangten.android.content.Board
import com.hangten.android.content.BoardHold
import com.hangten.android.content.BoardPresentation
import org.junit.Assert.assertEquals
import org.junit.Test

class BoardEditorPresentationContentTest {
    @Test
    fun unavailableDefaultPresentationHoldsCannotBecomeSelectionTargets() {
        val content = BoardEditorPresentationContent(filteredDefaultBoard())

        assertEquals("primary-rotated", content.presentation?.id)
        assertEquals(listOf("visible"), content.holds.map { it.id })
        assertEquals("visible", content.selectedHold("filtered-out")?.id)
    }

    private fun filteredDefaultBoard(): Board = Board(
        id = "demo",
        manufacturer = "Demo",
        name = "Demo",
        subtitle = "",
        productUrl = "https://example.com/demo",
        aspectRatio = 1f,
        presentations = listOf(
            BoardPresentation(
                id = "primary",
                name = "Primary",
                assetPath = "assets/primary.png",
                aspectRatio = 1f,
                isDefault = false,
            ),
            BoardPresentation(
                id = "primary-rotated",
                name = "Primary rotated",
                assetPath = "assets/primary.png",
                aspectRatio = 1f,
                isDefault = true,
                sourcePresentationId = "primary",
                rotationDegrees = 90f,
                availableHoldIds = listOf("visible"),
            ),
        ),
        holds = listOf(
            BoardHold(
                id = "filtered-out",
                name = "Filtered out",
                kind = "edge",
                presentationId = "primary",
                geometry = emptyList(),
            ),
            BoardHold(
                id = "visible",
                name = "Visible",
                kind = "edge",
                presentationId = "primary",
                geometry = emptyList(),
            ),
        ),
    )
}
