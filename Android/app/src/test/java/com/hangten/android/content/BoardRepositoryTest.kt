package com.hangten.android.content

import com.hangten.android.board.boardAssetPath
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
        assertEquals("demo", board.packageSlug)
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
    fun decodesSchemaV2RasterMediaIntoTheExistingCanvasModel() {
        val result = AssetBoardRepository(
            FixtureAssets(
                mapOf(
                    "Hangboards/demo/board.json" to schemaV2RasterBoardJson(),
                    "Hangboards/demo/assets/primary.png" to "png",
                ),
            ),
        ).loadBoards()

        val board = result.getOrThrow().single()
        assertEquals("demo.board", board.id)
        assertEquals("assets/primary.png", board.presentations.single().assetPath)
        assertTrue(board.presentations.single().isDefault)
        assertEquals("path-hold", board.holds.single().id)
        assertEquals("primary", board.holds.single().presentationId)
        assertTrue(board.holds.single().geometry.single().shape is HoldShape.Path)
    }

    @Test
    fun preservesPackageSlugForTheCanvasAssetLookupWhenItDiffersFromTheLogicalBoardId() {
        val board = AssetBoardRepository(
            FixtureAssets(
                mapOf(
                    "Hangboards/asset-package-slug/board.json" to schemaV2RasterBoardJson()
                        .replace("\"id\": \"demo.board\"", "\"id\": \"canonical.board-id\""),
                    "Hangboards/asset-package-slug/assets/primary.png" to "png",
                ),
            ),
        ).loadBoards().getOrThrow().single()

        assertEquals("canonical.board-id", board.id)
        assertEquals("asset-package-slug", board.packageSlug)
        assertEquals(
            "Hangboards/asset-package-slug/assets/primary.png",
            boardAssetPath(board, board.presentations.single()),
        )
    }

    @Test
    fun omitsSchemaV2ModelOnlyPackagesWithoutTryingToLoadARasterFallback() {
        val result = AssetBoardRepository(
            FixtureAssets(
                mapOf(
                    "Hangboards/raster/board.json" to schemaV2RasterBoardJson(),
                    "Hangboards/raster/assets/primary.png" to "png",
                    "Hangboards/model/board.json" to schemaV2ModelOnlyBoardJson(),
                    "PlanLibrary.json" to
                        """
                        {
                          "boardMappings": [
                            { "boardID": "model.only", "semanticHolds": { "jugs": { "kind": "jug" } } }
                          ]
                        }
                        """.trimIndent(),
                ),
            ),
        ).loadBoards()

        val boards = result.getOrThrow()
        assertEquals(listOf("demo.board"), boards.map { it.id })
        assertEquals(emptyMap<String, SemanticHoldMapping>(), boards.single().semanticHolds)
    }

    @Test
    fun omitsFlashModelOnlyPackageWithoutPngFallbackWhileKeepingRasterNeighbor() {
        val accessedPaths = mutableListOf<String>()
        val assets = FixtureAssets(
            mapOf(
                "Hangboards/raster-neighbor/board.json" to schemaV2RasterBoardJson()
                    .replace("demo.board", "raster.neighbor")
                    .replace("Demo Board", "Raster Neighbor"),
                "Hangboards/raster-neighbor/assets/primary.png" to "png",
                "Hangboards/tension-flash-board/board.json" to schemaV2ModelOnlyBoardJson()
                    .replace("model.only", "tension.flash-board")
                    .replace("Model only", "Flash Board"),
                "Hangboards/tension-flash-board/assets/primary.usdz" to "usdz",
                "Hangboards/tension-flash-board/assets/primary.model.json" to "descriptor",
                "PlanLibrary.json" to
                    """
                    {
                      "boardMappings": [
                        {
                          "boardID": "tension.flash-board",
                          "semanticHolds": { "jugs": { "kind": "jug" } }
                        }
                      ]
                    }
                    """.trimIndent(),
            ),
            accessedPaths = accessedPaths,
        )

        val boards = AssetBoardRepository(assets).loadBoards().getOrThrow()

        assertEquals(listOf("raster.neighbor"), boards.map { it.id })
        assertEquals("Raster Neighbor", boards.single().name)
        assertEquals("assets/primary.png", boards.single().presentations.single().assetPath)
        assertFalse("Hangboards/tension-flash-board/assets/primary.png" in accessedPaths)
        assertFalse("Hangboards/tension-flash-board/assets/primary.usdz" in accessedPaths)
        assertFalse("Hangboards/tension-flash-board/assets/primary.model.json" in accessedPaths)
        assertEquals(emptyMap<String, SemanticHoldMapping>(), boards.single().semanticHolds)
    }

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

    private fun schemaV2RasterBoardJson(): String =
        """
        {
          "schemaVersion": 2,
          "id": "demo.board",
          "manufacturer": "Demo",
          "name": "Demo Board",
          "subtitle": "A test board.",
          "productURL": "https://example.com/demo",
          "aspectRatio": 2.0,
          "equipmentObjects": [{ "id": "primary" }],
          "holds": [
            {
              "id": "path-hold",
              "equipmentObjectID": "primary",
              "name": "Path hold",
              "kind": "edge",
              "features": ["mediumEdge"]
            }
          ],
          "presentations": [
            {
              "id": "primary",
              "name": "Primary",
              "aspectRatio": 2.0,
              "isDefault": true,
              "derivation": { "type": "original" },
              "media": {
                "type": "raster",
                "assetPath": "assets/primary.png",
                "holdGeometry": {
                  "path-hold": [
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
                }
              }
            }
          ]
        }
        """.trimIndent()

    private fun schemaV2ModelOnlyBoardJson(): String =
        """
        {
          "schemaVersion": 2,
          "id": "model.only",
          "manufacturer": "Demo",
          "name": "Model only",
          "subtitle": "A model-only board.",
          "productURL": "https://example.com/model",
          "aspectRatio": 2.0,
          "equipmentObjects": [{ "id": "primary" }],
          "holds": [
            { "id": "jug", "equipmentObjectID": "primary", "name": "Jug", "kind": "jug" }
          ],
          "presentations": [
            {
              "id": "primary",
              "name": "Primary",
              "aspectRatio": 2.0,
              "isDefault": true,
              "derivation": { "type": "original" },
              "media": {
                "type": "model",
                "assetPath": "assets/primary.usdz",
                "descriptorPath": "assets/primary.model.json"
              }
            }
          ]
        }
        """.trimIndent()
}

class FixtureAssets(
    private val files: Map<String, String>,
    private val accessedPaths: MutableList<String> = mutableListOf(),
) : ContentAssets {
    override fun list(path: String): List<String>? {
        val prefix = path.trimEnd('/') + "/"
        return files.keys
            .mapNotNull { file -> file.removePrefix(prefix).substringBefore('/', "") }
            .filter { it.isNotEmpty() }
            .distinct()
            .takeIf { it.isNotEmpty() }
    }

    override fun read(path: String): String? {
        accessedPaths += path
        return files[path]
    }

    override fun exists(path: String): Boolean {
        accessedPaths += path
        return path in files
    }
}

private fun assertTrueFailureContaining(result: Result<*>, expected: String) {
    assertFalse(result.isSuccess)
    assertEquals(true, result.exceptionOrNull()?.message?.contains(expected))
}
