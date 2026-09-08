package com.hangten.android.content

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class ExternalSlidingLoopRepositoryTest {
    @Test
    fun decodesEveryPhysicalAndStyleFieldAndInheritsCanonicalFaceAcrossRotations() {
        val board = load().getOrThrow().single()
        val rig = board.defaultPresentation!!.cordRig as BoardCordRig.ExternalSlidingLoop
        assertEquals(BoardCordSize(120f, 170f), rig.sceneSize)
        assertEquals(BoardCordRect(0f, 0f, 120f, 170f), rig.sourceFrame)
        assertEquals(BoardCordRect(30f, 70f, 60f, 30f), rig.innerFaceFrame)
        assertEquals(BoardCordRect(30f, 70f, 60f, 30f), rig.bodyContactFrame)
        assertEquals(8f, rig.cornerRadius, 0f)
        assertEquals(2f, rig.clearance, 0f)
        assertEquals(Point(60f, 10f), rig.pullPoint)
        assertEquals(BoardRoutedCordStyle(4f, "#101010", "#2255AA", listOf("#FFD000", "#0055CC")), rig.style)
        assertEquals(3, board.presentations.size)
        board.presentations.forEach { presentation ->
            assertEquals(rig, board.resolvedCordRig(presentation))
            assertEquals(board.defaultPresentation, board.artworkPresentation(presentation))
            assertEquals(listOf("edge"), board.effectiveHolds(presentation).map { it.id })
            assertEquals("assets/primary.png", presentation.assetPath)
        }
        val diagonal = board.presentation("mono")!!
        assertEquals(45f, diagonal.resolvedRotationDegrees)
        assertEquals(0.5f, diagonal.resolvedGeometryScale)
        assertEquals(BoardGeometryRotationAnchor(0.25f, 0.75f), diagonal.geometryRotationAnchor)
    }

    @Test
    fun rejectsMissingUnknownMalformedAndNonFiniteSchemaFields() {
        val mutations = listOf(
            Triple("\"clearance\": 2,", "", "clearance is required"),
            Triple("\"clearance\": 2", "\"clearance\": -1", "clearance must be non-negative"),
            Triple("\"cornerRadius\": 8", "\"cornerRadius\": 16", "half the shorter"),
            Triple("\"cornerRadius\": 8", "\"cornerRadius\": -1", "non-negative"),
            Triple("\"diameter\": 4", "\"diameter\": 0", "diameter must be positive"),
            Triple("\"diameter\": 4", "\"diameter\": 1e50", "diameter must be finite"),
            Triple("\"clearance\": 2", "\"clearance\": 1e999", "non-finite number"),
            Triple("\"clearance\": 2", "\"clearance\": true", "clearance must be a number"),
            Triple("\"outlineColor\": \"#101010\"", "\"outlineColor\": \"black\"", "#RRGGBB"),
            Triple("[\"#FFD000\", \"#0055CC\"]", "[\"#FFD000\"]", "exactly two colors"),
            Triple("\"clearance\": 2", "\"clearance\": 2, \"ports\": []", "unknown key ports"),
            Triple("\"bodyContactFrame\": { \"x\": 30", "\"bodyContactFrame\": { \"future\": 1, \"x\": 30", "unknown key future"),
            Triple("\"baseColor\": \"#2255AA\"", "\"baseColor\": \"#2255AA\", \"opacity\": 1", "unknown key opacity"),
            Triple("\"type\": \"externalSlidingLoop\"", "\"type\": \"externalSlidingLoopV2\"", "type is unsupported"),
        )
        mutations.forEach { (before, after, message) ->
            assertFailure(load(boardJson().replace(before, after)), message)
        }
    }

    @Test
    fun rejectsApexInsideShapeBesideShapeAndClippedCordMargin() {
        listOf(
            "{ \"x\": 60, \"y\": 85 }" to "outside the expanded body",
            "{ \"x\": 10, \"y\": 75 }" to "above the body contact shape",
            "{ \"x\": 60, \"y\": 1 }" to "inside sceneSize with the style margin",
        ).forEach { (pull, message) ->
            assertFailure(load(boardJson().replace("{ \"x\": 60, \"y\": 10 }", pull)), message)
        }
    }

    @Test
    fun validatesRotatedAliasesAndImageAspectInsteadOfAcceptingUnsafeInheritance() {
        assertFailure(load(boardJson().replace("\"geometryScale\": 0.5", "\"geometryScale\": 5")), "presentation mono external sliding loop")
        assertFailure(load(boardJson().replace("\"rotationDegrees\": 180", "\"rotationDegrees\": 180, \"cordRig\": $rigJson")), "cordRig must be owned by a canonical")
        assertFailure(load(dimensions = ContentImageDimensions(100, 100)), "innerFaceFrame aspect ratio must match")
    }

    private fun load(source: String = boardJson(), dimensions: ContentImageDimensions = ContentImageDimensions(60, 30)): Result<List<Board>> =
        AssetBoardRepository(FixtureAssets(
            files = mapOf("Hangboards/demo/board.json" to source, "Hangboards/demo/assets/primary.png" to "png"),
            imageDimensions = mapOf("Hangboards/demo/assets/primary.png" to dimensions),
        )).loadBoards()

    private val rigJson = """
        {
          "type": "externalSlidingLoop",
          "sceneSize": { "width": 120, "height": 170 },
          "sourceFrame": { "x": 0, "y": 0, "width": 120, "height": 170 },
          "innerFaceFrame": { "x": 30, "y": 70, "width": 60, "height": 30 },
          "style": {
            "diameter": 4, "outlineColor": "#101010", "baseColor": "#2255AA",
            "braidColors": ["#FFD000", "#0055CC"]
          },
          "bodyContactFrame": { "x": 30, "y": 70, "width": 60, "height": 30 },
          "cornerRadius": 8,
          "clearance": 2,
          "pullPoint": { "x": 60, "y": 10 }
        }
    """.trimIndent()

    private fun boardJson() = """
        {
          "id": "demo", "manufacturer": "Demo", "name": "Demo", "subtitle": "Demo",
          "productURL": "https://example.com", "aspectRatio": 0.7058823529411765,
          "presentations": [
            {
              "id": "primary", "name": "Front", "assetPath": "assets/primary.png",
              "aspectRatio": 0.7058823529411765, "default": true, "cordRig": $rigJson
            },
            {
              "id": "inverted", "name": "Inverted", "assetPath": "assets/primary.png",
              "aspectRatio": 0.7058823529411765, "default": false, "sourcePresentationID": "primary",
              "rotationDegrees": 180
            },
            {
              "id": "mono", "name": "Mono", "assetPath": "assets/primary.png",
              "aspectRatio": 0.7058823529411765, "default": false, "sourcePresentationID": "primary",
              "rotationDegrees": 45, "geometryScale": 0.5,
              "geometryRotationAnchor": { "x": 0.25, "y": 0.75 }, "availableHoldIDs": ["edge"]
            }
          ],
          "holds": [{
            "id": "edge", "name": "Edge", "kind": "edge", "presentationID": "primary",
            "geometry": [{
              "frame": { "x": 0.25, "y": 0.25, "width": 0.5, "height": 0.5 },
              "shape": { "type": "roundedRect", "cornerRadiusFraction": 0.2 }
            }]
          }]
        }
    """.trimIndent()

    private fun assertFailure(result: Result<*>, message: String) {
        assertFalse("Expected $message", result.isSuccess)
        assertTrue("Expected $message, got ${result.exceptionOrNull()}", result.exceptionOrNull()?.message?.contains(message) == true)
    }
}
