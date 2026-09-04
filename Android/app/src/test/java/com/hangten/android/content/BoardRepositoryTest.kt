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
        assertEquals(180f, inverted.resolvedRotationDegrees)
    }

    @Test
    fun rejectsDirectTwoAnchorCordStrokeOutsideScene() {
        val result = loadRiggedBoard(
            riggedBoardJson().replace(
                "\"pullPoint\": { \"x\": 600, \"y\": 71.5 }",
                "\"pullPoint\": { \"x\": 600, \"y\": -200 }",
            ),
        )

        assertTrueFailureContaining(
            result,
            "presentation primary cord drawing must remain inside sceneSize",
        )
    }

    @Test
    fun rejectsGravityInvertedDirectTwoAnchorAlias() {
        val result = loadRiggedBoard(
            riggedBoardJson().replace(
                "\"geometryRotationAnchor\": { \"x\": 0.5, \"y\": 0.6174863387978142 }",
                "\"geometryRotationAnchor\": { \"x\": 0.5, \"y\": 0.4 }",
            ),
        )

        assertTrueFailureContaining(
            result,
            "presentation primary-inverted cord pull exits must remain above both attachment points",
        )
    }

    @Test
    fun decodesExplicitArbitraryAliasRotation() {
        val board = loadRiggedBoard(
            riggedBoardJson().replace("\"isInverted\": true", "\"rotationDegrees\": 135"),
        ).getOrThrow().single()

        val rotated = board.presentation("primary-inverted")!!

        assertEquals(135f, rotated.rotationDegrees)
        assertEquals(135f, rotated.resolvedRotationDegrees)
        assertFalse(rotated.isInverted)
    }

    @Test
    fun rejectsExplicitRotationUsingDistinctAliasAsset() {
        val source = explicitRotationBoardJson(
            assetPath = "assets/rotated.png",
            rotationDegrees = 180,
        )
        val result = AssetBoardRepository(
            FixtureAssets(
                mapOf(
                    "Hangboards/demo/board.json" to source,
                    "Hangboards/demo/assets/primary.png" to "png",
                    "Hangboards/demo/assets/rotated.png" to "png",
                ),
            ),
        ).loadBoards()

        assertTrueFailureContaining(
            result,
            "assetPath must reuse source presentation assetPath for an explicit rotation",
        )
    }

    @Test
    fun rejectsExplicitNonHalfTurnWithoutCanonicalCordRig() {
        val result = AssetBoardRepository(
            FixtureAssets(
                mapOf(
                    "Hangboards/demo/board.json" to explicitRotationBoardJson(
                        assetPath = "assets/primary.png",
                        rotationDegrees = 90,
                    ),
                    "Hangboards/demo/assets/primary.png" to "png",
                ),
            ),
        ).loadBoards()

        assertTrueFailureContaining(
            result,
            "non-180 rotation requires a canonical cordRig to prevent artwork clipping",
        )
    }

    @Test
    fun rejectsInvalidOrAmbiguousExplicitAliasRotation() {
        listOf(
            riggedBoardJson().replace("\"isInverted\": true", "\"rotationDegrees\": -1"),
            riggedBoardJson().replace("\"isInverted\": true", "\"rotationDegrees\": 360"),
            riggedBoardJson().replace(
                "\"isInverted\": true,",
                "\"isInverted\": true, \"rotationDegrees\": 180,",
            ),
        ).forEach { source ->
            assertTrueFailureContaining(loadRiggedBoard(source), "rotation")
        }
    }

    @Test
    fun rejectsArbitraryAliasRotationThatProjectsHoldGeometryOutsideCanvas() {
        val source = riggedBoardJson()
            .replace("\"isInverted\": true", "\"rotationDegrees\": 45")
            .replace(
                "\"x\": 0.2, \"y\": 0.3, \"width\": 0.4, \"height\": 0.2",
                "\"x\": 0.9, \"y\": 0.9, \"width\": 0.1, \"height\": 0.1",
            )

        assertTrueFailureContaining(
            loadRiggedBoard(source),
            "projects source hold geometry outside",
        )
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

    @Test
    fun rejectsHoldOwnedByAliasPresentation() {
        val result = loadRiggedBoard(
            riggedBoardJson().replace(
                "\"presentationID\": \"primary\"",
                "\"presentationID\": \"primary-inverted\"",
            ),
        )

        assertTrueFailureContaining(result, "hold edge must be owned by a canonical presentation")
    }

    @Test
    fun rejectsUnknownKeysThroughoutPresentationAndCordRigObjects() {
        val malformedDocuments = listOf(
            riggedBoardJson().replace(
                "\"default\": true,",
                "\"default\": true, \"defualt\": true,",
            ) to "defualt",
            riggedBoardJson().replace(
                "\"isInverted\": true,",
                "\"isInverted\": true, \"isInvertedd\": true,",
            ) to "isInvertedd",
            riggedBoardJson().replace(
                "\"geometryRotationAnchor\": { \"x\": 0.5, \"y\": 0.6174863387978142 }",
                "\"geometryRotationAnchor\": { \"x\": 0.5, \"y\": 0.6174863387978142, \"pivot\": 1 }",
            ) to "pivot",
            riggedBoardJson().replace(
                "\"eyeletRadius\": 34",
                "\"eyeletRadius\": 34, \"eyeletRaduis\": 34",
            ) to "eyeletRaduis",
            riggedBoardJson().replace(
                "\"sceneSize\": { \"width\": 1200, \"height\": 1464 }",
                "\"sceneSize\": { \"width\": 1200, \"height\": 1464, \"depth\": 1 }",
            ) to "depth",
            riggedBoardJson().replace(
                "\"sourceFrame\": { \"x\": 0, \"y\": 214, \"width\": 1200, \"height\": 1250 }",
                "\"sourceFrame\": { \"x\": 0, \"y\": 214, \"width\": 1200, \"height\": 1250, \"left\": 0 }",
            ) to "left",
            riggedBoardJson().replace(
                "\"innerFaceFrame\": { \"x\": -100, \"y\": -10, \"width\": 1400, \"height\": 1400 }",
                "\"innerFaceFrame\": { \"x\": -100, \"y\": -10, \"width\": 1400, \"height\": 1400, \"top\": -10 }",
            ) to "top",
            riggedBoardJson().replace(
                "{ \"x\": 276, \"y\": 804 }",
                "{ \"x\": 276, \"y\": 804, \"z\": 0 }",
            ) to "z",
            riggedBoardJson().replace(
                "\"pullPoint\": { \"x\": 600, \"y\": 71.5 }",
                "\"pullPoint\": { \"x\": 600, \"y\": 71.5, \"z\": 0 }",
            ) to "z",
        )

        malformedDocuments.forEach { (source, unknownKey) ->
            assertTrueFailureContaining(loadRiggedBoard(source), unknownKey)
        }
    }

    @Test
    fun presentationAvailabilityFiltersCanonicalHoldsAndLegacyPresentationsRemainUnfiltered() {
        val board = AssetBoardRepository(
            FixtureAssets(
                mapOf(
                    "Hangboards/demo/board.json" to boardJsonWithAvailability("[\"rounded-hold\"]"),
                    "Hangboards/demo/assets/primary.png" to "png",
                ),
            ),
        ).loadBoards().getOrThrow().single()

        assertEquals(
            listOf("path-hold", "rounded-hold"),
            board.effectiveHolds(board.presentation("primary")!!).map { it.id },
        )
        assertEquals(
            listOf("rounded-hold"),
            board.effectiveHolds(board.presentation("filtered")!!).map { it.id },
        )
    }

    @Test
    fun rejectsMalformedPresentationAvailability() {
        listOf(
            "[]" to "availableHoldIDs must not be empty",
            "[\"path-hold\", \"path-hold\"]" to "availableHoldIDs must be unique",
            "[\"missing\"]" to "availableHoldIDs references unknown hold missing",
            "\"path-hold\"" to "availableHoldIDs must be an array",
        ).forEach { (availableHoldIds, expectedMessage) ->
            val result = AssetBoardRepository(
                FixtureAssets(
                    mapOf(
                        "Hangboards/demo/board.json" to boardJsonWithAvailability(availableHoldIds),
                        "Hangboards/demo/assets/primary.png" to "png",
                    ),
                ),
            ).loadBoards()

            assertTrueFailureContaining(result, expectedMessage)
        }
    }

    private fun loadRiggedBoard(source: String): Result<List<Board>> =
        AssetBoardRepository(
            FixtureAssets(
                mapOf(
                    "Hangboards/demo/board.json" to source,
                    "Hangboards/demo/assets/primary.png" to "png",
                ),
            ),
        ).loadBoards()

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

    private fun boardJsonWithAvailability(availableHoldIds: String): String =
        boardJson().replace(
            "      \"default\": true\n    }\n  ],",
            "      \"default\": true\n    },\n    {\n"
                + "      \"id\": \"filtered\",\n"
                + "      \"name\": \"Filtered\",\n"
                + "      \"assetPath\": \"assets/primary.png\",\n"
                + "      \"aspectRatio\": 2.0,\n"
                + "      \"default\": false,\n"
                + "      \"sourcePresentationID\": \"primary\",\n"
                + "      \"availableHoldIDs\": $availableHoldIds\n"
                + "    }\n  ],",
        )

    private fun explicitRotationBoardJson(
        assetPath: String,
        rotationDegrees: Int,
    ): String = boardJson().replace(
        "      \"default\": true\n    }\n  ],",
        "      \"default\": true\n    },\n    {\n"
            + "      \"id\": \"rotated\",\n"
            + "      \"name\": \"Rotated\",\n"
            + "      \"assetPath\": \"$assetPath\",\n"
            + "      \"aspectRatio\": 2.0,\n"
            + "      \"default\": false,\n"
            + "      \"sourcePresentationID\": \"primary\",\n"
            + "      \"rotationDegrees\": $rotationDegrees\n"
            + "    }\n  ],",
    )

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
