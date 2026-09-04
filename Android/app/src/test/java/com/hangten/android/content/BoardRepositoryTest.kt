package com.hangten.android.content

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class BoardRepositoryTest {
    @Test
    fun decodesAPathHoldAndAConstrainedRoundedRectangle() {
        val result = AssetBoardRepository(
            FixtureAssets(
                mapOf(
                    "Hangboards/demo/board.json" to boardJson(),
                    "Hangboards/demo/assets/primary.png" to "png",
                ),
            ),
        ).loadBoards()

        val board = result.getOrThrow().single()
        assertEquals("demo.board", board.id)
        assertEquals("path-hold", board.holds[0].id)
        assertEquals(setOf("mediumEdge"), board.holds[0].features)
        assertTrue(board.holds[0].geometry.single().shape is HoldShape.Path)
        assertEquals(
            listOf(
                PathCommand.Move(Point(0f, 0f)),
                PathCommand.Line(Point(1f, 0f)),
                PathCommand.Line(Point(1f, 1f)),
                PathCommand.Close,
            ),
            (board.holds[0].geometry.single().shape as HoldShape.Path).commands,
        )
        assertEquals("rounded-hold", board.holds[1].id)
        assertEquals(2, board.holds[1].fingerCapacity)
        assertEquals(
            HoldShape.RoundedRect(0.25f),
            board.holds[1].geometry.single().shape,
        )
    }

    @Test
    fun rejectsBoardWhosePresentationAssetIsAbsent() {
        val result = AssetBoardRepository(
            FixtureAssets(mapOf("Hangboards/demo/board.json" to boardJson())),
        ).loadBoards()

        assertTrueFailureContaining(result, "assets/primary.png")
    }

    @Test
    fun rejectsMalformedBoardJson() {
        val result = AssetBoardRepository(
            FixtureAssets(mapOf("Hangboards/demo/board.json" to "{ malformed")),
        ).loadBoards()

        assertTrueFailureContaining(result, "Malformed JSON")
    }

    @Test
    fun attachesValidatedCanonicalSemanticMappingsToTheirBoard() {
        val result = AssetBoardRepository(
            FixtureAssets(
                mapOf(
                    "Hangboards/demo/board.json" to boardJson(),
                    "Hangboards/demo/assets/primary.png" to "png",
                    "PlanLibrary.json" to
                        """
                        {
                          "boardMappings": [
                            {
                              "boardID": "demo.board",
                              "semanticHolds": {
                                "outer-edge": { "holdIDs": ["path-hold"] },
                                "pockets": { "kind": "pocket" }
                              }
                            }
                          ]
                        }
                        """.trimIndent(),
                ),
            ),
        ).loadBoards()

        assertEquals(
            SemanticHoldMapping(holdIds = listOf("path-hold")),
            result.getOrThrow().single().semanticHolds["outer-edge"],
        )
        assertEquals(
            SemanticHoldMapping(kind = "pocket"),
            result.getOrThrow().single().semanticHolds["pockets"],
        )
    }

    @Test
    fun rejectsOutOfRangeCanonicalFingerCapacity() {
        val result = AssetBoardRepository(
            FixtureAssets(
                mapOf(
                    "Hangboards/demo/board.json" to boardJson().replace("\"fingerCapacity\": 2", "\"fingerCapacity\": 5"),
                    "Hangboards/demo/assets/primary.png" to "png",
                ),
            ),
        ).loadBoards()

        assertTrueFailureContaining(result, "fingerCapacity")
    }

    @Test
    fun decodesDirectTwoAnchorRigAndResolvesItsInvertedAliasToCanonicalArtwork() {
        val board = AssetBoardRepository(
            FixtureAssets(
                mapOf(
                    "Hangboards/demo/board.json" to riggedBoardJson(),
                    "Hangboards/demo/assets/primary.png" to "png",
                ),
            ),
        ).loadBoards().getOrThrow().single()

        val canonical = board.presentation("primary")!!
        val inverted = board.presentation("primary-inverted")!!
        val expectedRig = BoardCordRig.DirectTwoAnchor(
            sceneSize = BoardCordSize(width = 1200f, height = 1464f),
            sourceFrame = BoardCordRect(x = 0f, y = 214f, width = 1200f, height = 1250f),
            innerFaceFrame = BoardCordRect(x = -100f, y = -10f, width = 1400f, height = 1400f),
            attachmentPoints = listOf(Point(276f, 804f), Point(920f, 804f)),
            pullPoint = Point(600f, 71.5f),
            eyeletRadius = 34f,
        )

        assertEquals("demo", board.packageName)
        assertEquals(expectedRig, canonical.cordRig)
        assertEquals(expectedRig, board.resolvedCordRig(inverted))
        assertEquals(canonical, board.artworkPresentation(inverted))
        assertEquals("primary", board.holdPresentationId(inverted))
        assertEquals(BoardGeometryRotationAnchor(0.5f, 113f / 183f), inverted.geometryRotationAnchor)
    }

    @Test
    fun rejectsDirectTwoAnchorRigWithNonPositiveEyeletRadius() {
        val result = AssetBoardRepository(
            FixtureAssets(
                mapOf(
                    "Hangboards/demo/board.json" to riggedBoardJson().replace(
                        "\"eyeletRadius\": 34",
                        "\"eyeletRadius\": 0",
                    ),
                    "Hangboards/demo/assets/primary.png" to "png",
                ),
            ),
        ).loadBoards()

        assertTrueFailureContaining(result, "eyeletRadius")
    }

    private fun riggedBoardJson(): String =
        """
        {
          "id": "demo.board",
          "manufacturer": "Demo",
          "name": "Demo Board",
          "subtitle": "A test board.",
          "productURL": "https://example.com/demo",
          "aspectRatio": 0.819672131147541,
          "presentations": [
            {
              "id": "primary",
              "name": "Primary",
              "assetPath": "assets/primary.png",
              "aspectRatio": 0.819672131147541,
              "default": true,
              "cordRig": {
                "type": "directTwoAnchor",
                "sceneSize": { "width": 1200, "height": 1464 },
                "sourceFrame": { "x": 0, "y": 214, "width": 1200, "height": 1250 },
                "innerFaceFrame": { "x": -100, "y": -10, "width": 1400, "height": 1400 },
                "attachmentPoints": [
                  { "x": 276, "y": 804 },
                  { "x": 920, "y": 804 }
                ],
                "pullPoint": { "x": 600, "y": 71.5 },
                "eyeletRadius": 34
              }
            },
            {
              "id": "primary-inverted",
              "name": "Primary inverted",
              "assetPath": "assets/primary.png",
              "aspectRatio": 0.819672131147541,
              "default": false,
              "sourcePresentationID": "primary",
              "isInverted": true,
              "geometryRotationAnchor": { "x": 0.5, "y": 0.6174863387978142 }
            }
          ],
          "holds": [
            {
              "id": "edge",
              "name": "Edge",
              "kind": "edge",
              "presentationID": "primary",
              "geometry": [
                {
                  "frame": { "x": 0.2, "y": 0.3, "width": 0.4, "height": 0.2 },
                  "shape": { "type": "roundedRect", "cornerRadiusFraction": 0.2 }
                }
              ]
            }
          ]
        }
        """.trimIndent()

    private fun boardJson(): String =
        """
        {
          "id": "demo.board",
          "manufacturer": "Demo",
          "name": "Demo Board",
          "subtitle": "A test board.",
          "productURL": "https://example.com/demo",
          "aspectRatio": 2.0,
          "presentations": [
            {
              "id": "primary",
              "name": "Primary",
              "assetPath": "assets/primary.png",
              "aspectRatio": 2.0,
              "default": true
            }
          ],
          "holds": [
            {
              "id": "path-hold",
              "name": "Path hold",
              "kind": "edge",
              "features": ["mediumEdge"],
              "presentationID": "primary",
              "geometry": [
                {
                  "frame": { "x": 0.1, "y": 0.2, "width": 0.3, "height": 0.4 },
                  "shape": {
                    "type": "path",
                    "commands": [
                      { "command": "move", "to": [0.0, 0.0] },
                      { "command": "line", "to": [1.0, 0.0] },
                      { "command": "line", "to": [1.0, 1.0] },
                      { "command": "close" }
                    ]
                  }
                }
              ]
            },
            {
              "id": "rounded-hold",
              "name": "Rounded hold",
              "kind": "pocket",
              "fingerCapacity": 2,
              "presentationID": "primary",
              "geometry": [
                {
                  "frame": { "x": 0.5, "y": 0.2, "width": 0.3, "height": 0.4 },
                  "shape": {
                    "type": "roundedRect",
                    "cornerRadiusFraction": 0.25
                  },
                  "shapeConstraint": { "shape": "roundedRectangle", "rotationDegrees": 0.0 }
                }
              ]
            }
          ]
        }
        """.trimIndent()
}

class FixtureAssets(
    private val files: Map<String, String>,
) : ContentAssets {
    override fun list(path: String): List<String>? {
        val prefix = path.trimEnd('/') + "/"
        return files.keys
            .mapNotNull { file -> file.removePrefix(prefix).substringBefore('/', "") }
            .filter { it.isNotEmpty() }
            .distinct()
            .takeIf { it.isNotEmpty() }
    }

    override fun read(path: String): String? = files[path]

    override fun exists(path: String): Boolean = path in files
}

private fun assertTrueFailureContaining(result: Result<*>, expected: String) {
    assertFalse(result.isSuccess)
    assertEquals(true, result.exceptionOrNull()?.message?.contains(expected))
}
