package com.hangten.android.board

import com.hangten.android.content.Board
import com.hangten.android.content.BoardHold
import com.hangten.android.content.SemanticHoldMapping
import org.junit.Assert.assertEquals
import org.junit.Test

class HoldTargetResolverTest {
    @Test
    fun semanticJugTargetResolvesOnlyItsDeclaredHoldsOnSelectedBoard() {
        val board = boardWith(
            BoardHold(id = "jug-left", name = "Jug left", kind = "jug", presentationId = "primary", geometry = emptyList()),
            BoardHold(id = "jug-right", name = "Jug right", kind = "jug", presentationId = "primary", geometry = emptyList()),
            BoardHold(id = "edge-20", name = "20 mm edge", kind = "edge", presentationId = "primary", geometry = emptyList()),
            semanticHolds = mapOf("outer-jugs" to SemanticHoldMapping(holdIds = listOf("jug-left", "jug-right"))),
        )

        assertEquals(
            linkedSetOf("jug-left", "jug-right"),
            resolveTargets(listOf(HoldTarget(semantic = "outer-jugs")), board),
        )
    }

    @Test
    fun featureTargetUsesExactCanonicalFeatureBeforeItsFallbacks() {
        val board = boardWith(
            BoardHold(
                id = "round-sloper",
                name = "Round sloper",
                kind = "sloper",
                features = setOf("roundSloper"),
                presentationId = "primary",
                geometry = emptyList(),
            ),
            BoardHold(
                id = "large-edge",
                name = "Large edge",
                kind = "edge",
                features = setOf("largeEdge"),
                presentationId = "primary",
                geometry = emptyList(),
            ),
        )

        assertEquals(
            linkedSetOf("round-sloper"),
            resolveTargets(
                listOf(HoldTarget(feature = "roundSloper", fallbackFeatures = listOf("largeEdge"))),
                board,
            ),
        )
    }

    @Test
    fun featureTargetUsesTheFirstDeclaredAvailableFallback() {
        val board = boardWith(
            BoardHold(
                id = "large-edge",
                name = "Large edge",
                kind = "edge",
                features = setOf("largeEdge"),
                presentationId = "primary",
                geometry = emptyList(),
            ),
            BoardHold(
                id = "small-edge",
                name = "Small edge",
                kind = "edge",
                features = setOf("smallEdge"),
                presentationId = "primary",
                geometry = emptyList(),
            ),
        )

        assertEquals(
            linkedSetOf("large-edge"),
            resolveTargets(
                listOf(HoldTarget(feature = "mediumEdge", fallbackFeatures = listOf("largeEdge", "smallEdge"))),
                board,
            ),
        )
    }

    @Test
    fun pocketTargetWithFingerCapacitySelectsOnlyQualifyingHolds() {
        val board = boardWith(
            BoardHold(
                id = "two-finger-pocket",
                name = "Two finger pocket",
                kind = "pocket",
                fingerCapacity = 2,
                presentationId = "primary",
                geometry = emptyList(),
            ),
            BoardHold(
                id = "three-finger-pocket",
                name = "Three finger pocket",
                kind = "pocket",
                fingerCapacity = 3,
                presentationId = "primary",
                geometry = emptyList(),
            ),
        )

        assertEquals(
            linkedSetOf("two-finger-pocket"),
            resolveTargets(listOf(HoldTarget(kind = "pocket", fingerCapacity = 2)), board),
        )
    }

    @Test
    fun semanticListResolvesEveryDeclaredSemanticMapping() {
        val board = boardWith(
            BoardHold(id = "left", name = "Left", kind = "edge", presentationId = "primary", geometry = emptyList()),
            BoardHold(id = "right", name = "Right", kind = "edge", presentationId = "primary", geometry = emptyList()),
            semanticHolds = mapOf(
                "left-edge" to SemanticHoldMapping(holdIds = listOf("left")),
                "right-edge" to SemanticHoldMapping(holdIds = listOf("right")),
            ),
        )

        assertEquals(
            linkedSetOf("left", "right"),
            resolveTargets(listOf(HoldTarget(semantics = listOf("left-edge", "right-edge"))), board),
        )
    }

    @Test
    fun unknownSemanticResolvesNoHolds() {
        val board = boardWith(
            BoardHold(id = "edge", name = "Edge", kind = "edge", presentationId = "primary", geometry = emptyList()),
        )

        assertEquals(emptySet<String>(), resolveTargets(listOf(HoldTarget(semantic = "unknown-semantic")), board))
    }

    @Test
    fun semanticListWithOnlyUnknownMappingsResolvesNoHolds() {
        val board = boardWith(
            BoardHold(id = "edge", name = "Edge", kind = "edge", presentationId = "primary", geometry = emptyList()),
        )

        assertEquals(
            emptySet<String>(),
            resolveTargets(listOf(HoldTarget(semantics = listOf("unknown-left", "unknown-right"))), board),
        )
    }

    @Test
    fun absentFeatureWithoutFallbackResolvesNoHolds() {
        val board = boardWith(
            BoardHold(
                id = "large-edge",
                name = "Large edge",
                kind = "edge",
                features = setOf("largeEdge"),
                presentationId = "primary",
                geometry = emptyList(),
            ),
        )

        assertEquals(emptySet<String>(), resolveTargets(listOf(HoldTarget(feature = "mediumEdge")), board))
    }

    @Test
    fun fingerCapacityWithoutAQualifyingHoldResolvesNoHolds() {
        val board = boardWith(
            BoardHold(
                id = "three-finger-pocket",
                name = "Three finger pocket",
                kind = "pocket",
                fingerCapacity = 3,
                presentationId = "primary",
                geometry = emptyList(),
            ),
        )

        assertEquals(
            emptySet<String>(),
            resolveTargets(listOf(HoldTarget(kind = "pocket", fingerCapacity = 2)), board),
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

    private fun boardWith(
        vararg holds: BoardHold,
        semanticHolds: Map<String, SemanticHoldMapping> = emptyMap(),
    ) = Board(
        id = "fixture-board",
        manufacturer = "Fixture",
        name = "Fixture Board",
        subtitle = "Fixture",
        productUrl = "https://example.invalid/fixture",
        aspectRatio = 2f,
        presentations = emptyList(),
        holds = holds.toList(),
        semanticHolds = semanticHolds,
    )
}
