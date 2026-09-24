package com.hangten.android.content

import com.hangten.android.board.boardAssetPath
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class BoardRepositoryTest {
    @Test
    fun decodesAPathContactAndAConstrainedRoundedRectangle() {
        val board = loadRaster(rasterBoardJson()).getOrThrow().single()

        assertEquals("demo.board", board.id)
        assertEquals("demo", board.packageSlug)
        assertEquals("assets/primary.png", board.presentations.single().assetPath)
        assertTrue(board.presentations.single().isDefault)
        assertEquals(listOf("path-edge", "rounded-pocket"), board.holds.map { it.id })

        val edge = board.holds[0]
        assertEquals("edge", edge.kind)
        assertEquals("primary", edge.presentationId)
        assertEquals(HoldDepth.Range(20.0, 20.0), edge.depth)
        assertEquals(setOf(GripType.HALF_CRIMP, GripType.OPEN_HAND), edge.gripTypes)
        assertEquals(
            listOf(
                PathCommand.Move(Point(0f, 0f)),
                PathCommand.Line(Point(1f, 0f)),
                PathCommand.Line(Point(1f, 1f)),
                PathCommand.Close,
            ),
            (edge.geometry.single().shape as HoldShape.Path).commands,
        )

        val pocket = board.holds[1]
        assertEquals(2, pocket.fingerCapacity)
        assertEquals(HoldDepth.Category(HoldSize.MEDIUM), pocket.depth)
        assertEquals("round", pocket.shape)
        assertEquals(HoldShape.RoundedRect(0.25f), pocket.geometry.single().shape)
    }

    @Test
    fun rejectsBoardWhosePresentationAssetIsAbsent() {
        val result = AssetBoardRepository(
            FixtureAssets(mapOf("Hangboards/demo/board.json" to rasterBoardJson())),
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
    fun rejectsSupersededSchemaVersions() {
        val result = loadRaster(rasterBoardJson().replaceOnce("\"schemaVersion\": 3", "\"schemaVersion\": 2"))

        assertTrueFailureContaining(result, "schemaVersion must be 3")
    }

    @Test
    fun rejectsLegacyHoldInventory() {
        val result = loadRaster(
            rasterBoardJson().replaceOnce("\"contacts\": [", "\"holds\": [],\n  \"contacts\": ["),
        )

        assertTrueFailureContaining(result, "unknown key holds")
    }

    @Test
    fun rejectsOutOfRangeContactFingerCapacity() {
        val result = loadRaster(rasterBoardJson().replaceOnce("\"fingerCapacity\": 2", "\"fingerCapacity\": 5"))

        assertTrueFailureContaining(result, "fingerCapacity")
    }

    @Test
    fun rejectsUnsupportedContactGripType() {
        val result = loadRaster(rasterBoardJson().replaceOnce("\"openHand\"", "\"crimpish\""))

        assertTrueFailureContaining(result, "gripTypes")
    }

    @Test
    fun rejectsContactOnUnknownEquipmentObject() {
        val result = loadRaster(
            rasterBoardJson().replaceOnce("\"equipmentObjects\": [{ \"id\": \"primary\" }]", "\"equipmentObjects\": [{ \"id\": \"frame\" }]"),
        )

        assertTrueFailureContaining(result, "contact path-edge references unknown equipment object primary")
    }

    @Test
    fun rejectsGeometryForAnUnknownContact() {
        val result = loadRaster(rasterBoardJson().replaceOnce("\"rounded-pocket\": [", "\"unknown-contact\": ["))

        assertTrueFailureContaining(result, "unknown contact unknown-contact")
    }

    @Test
    fun materializesPositionsWithoutContactIDsWithTheCompleteContactInventory() {
        val board = loadRaster(
            rasterBoardJson().replaceOnce(
                "\"presentations\": [",
                "\"positions\": [{\"id\": \"primary-position\", \"presentationID\": \"primary\"}],\n  \"presentations\": [",
            ),
        ).getOrThrow().single()

        assertEquals(listOf("primary-position"), board.positions.map { it.id })
        assertEquals(listOf("path-edge", "rounded-pocket"), board.positions.single().contactIds)
    }

    @Test
    fun drawsEachContactOnItsOriginalPresentationAndIgnoresDerivedGeometry() {
        val withInvertedPresentation = rasterBoardJson().replaceOnce(
            "  ]\n}",
            """
              ,
                {
                  "id": "inverted",
                  "name": "Inverted",
                  "aspectRatio": 2.0,
                  "isDefault": false,
                  "derivation": { "type": "derived", "sourcePresentationID": "primary", "isInverted": true },
                  "media": {
                    "type": "raster",
                    "assetPath": "assets/inverted.png",
                    "contactGeometry": {
                      "path-edge": [
                        { "frame": { "x": 0.5, "y": 0.5, "width": 0.1, "height": 0.1 }, "shape": { "type": "roundedRect", "cornerRadiusFraction": 0.1 } }
                      ]
                    }
                  }
                }
              ]
            }
            """.trimIndent(),
        )
        val board = AssetBoardRepository(
            FixtureAssets(
                mapOf(
                    "Hangboards/demo/board.json" to withInvertedPresentation,
                    "Hangboards/demo/assets/primary.png" to "png",
                    "Hangboards/demo/assets/inverted.png" to "png",
                ),
            ),
        ).loadBoards().getOrThrow().single()

        assertEquals(listOf("primary", "inverted"), board.presentations.map { it.id })
        assertEquals(listOf("primary", "primary"), board.holds.map { it.presentationId })
        assertTrue(board.holds[0].geometry.single().shape is HoldShape.Path)
    }

    @Test
    fun rejectsRasterOrientationInsteadOfIgnoringIt() {
        val result = loadRaster(
            rasterBoardJson().replaceOnce("\"type\": \"raster\",", "\"type\": \"raster\",\n\"orientation\": {},"),
        )

        assertTrueFailureContaining(result, "unknown key")
        assertTrueFailureContaining(result, "orientation")
    }

    @Test
    fun rejectsUnknownRasterMediaKeys() {
        val result = loadRaster(
            rasterBoardJson().replaceOnce("\"type\": \"raster\",", "\"type\": \"raster\",\n\"unexpected\": true,"),
        )

        assertTrueFailureContaining(result, "unknown key unexpected")
    }

    @Test
    fun rejectsLegacyRasterHoldGeometry() {
        val result = loadRaster(rasterBoardJson().replaceOnce("\"contactGeometry\"", "\"holdGeometry\""))

        assertTrueFailureContaining(result, "unknown key holdGeometry")
    }

    @Test
    fun acceptsValidModelOrientationBeforeOmittingTheModelOnlyBoard() {
        val result = loadModelWithOrientation(
            "{\"pivot\": \"modelBoundsCenter\", \"rotations\": {\"front\": [0, 0, 0, 1], \"reverse\": [0, 1, 0, 0]}}",
        )

        assertTrue(result.isSuccess)
        assertTrue(result.getOrThrow().isEmpty())
    }

    @Test
    fun rejectsUnknownModelOrientationKeysInsteadOfTreatingThemAsRasterGeometry() {
        val result = loadModelWithOrientation(
            "{\"pivot\": \"modelBoundsCenter\", \"rotations\": {\"primary\": [0, 0, 0, 1]}, \"unexpected\": true}",
        )

        assertTrueFailureContaining(result, "orientation")
        assertTrueFailureContaining(result, "unknown key")
    }

    @Test
    fun rejectsModelContactGeometryInsteadOfTreatingItAsRasterData() {
        // The model media decoder has a closed key set; contactGeometry belongs
        // only to raster media and must never be consulted for model assets.
        val result = AssetBoardRepository(
            FixtureAssets(
                mapOf(
                    "Hangboards/model/board.json" to modelOnlyBoardJson(
                        mediaExtras = "\"contactGeometry\": {}",
                    ),
                ),
            ),
        ).loadBoards()

        assertTrueFailureContaining(result, "unknown key contactGeometry")
    }

    @Test
    fun rejectsInvalidOrientationPivot() {
        val result = loadModelWithOrientation(
            "{\"pivot\": \"worldOrigin\", \"rotations\": {\"front\": [0, 0, 0, 1], \"reverse\": [0, 1, 0, 0]}}",
        )

        assertTrueFailureContaining(result, "orientation pivot")
    }

    @Test
    fun rejectsNonUnitOrientationQuaternion() {
        val result = loadModelWithOrientation(
            "{\"pivot\": \"modelBoundsCenter\", \"rotations\": {\"front\": [0, 0, 0, 2], \"reverse\": [0, 1, 0, 0]}}",
        )

        assertTrueFailureContaining(result, "unit quaternion")
    }

    @Test
    fun acceptsOrientationQuaternionComponentsRoundedToNineDecimalPlaces() {
        val result = loadModelWithOrientation(
            "{\"pivot\": \"modelBoundsCenter\", \"rotations\": {\"front\": [0.707106781, 0, 0, 0.707106781], \"reverse\": [0, 1, 0, 0]}}",
        )

        assertTrue(result.isSuccess)
        assertTrue(result.getOrThrow().isEmpty())
    }

    @Test
    fun rejectsOrientationQuaternionWithMoreThanNineDecimalPlaces() {
        val result = loadModelWithOrientation(
            "{\"pivot\": \"modelBoundsCenter\", \"rotations\": {\"front\": [0.1234567891, 0, 0, 0.992349949], \"reverse\": [0, 1, 0, 0]}}",
        )

        assertTrueFailureContaining(result, "nine decimal")
    }

    @Test
    fun rejectsOrientationMembersThatAreNotPivotThenRotations() {
        val result = loadModelWithOrientation(
            "{\"rotations\": {\"front\": [0, 0, 0, 1], \"reverse\": [0, 1, 0, 0]}, \"pivot\": \"modelBoundsCenter\"}",
        )

        assertTrueFailureContaining(result, "canonical pivot and rotations")
    }

    @Test
    fun rejectsOrientationRotationsThatAreNotSortedByPositionID() {
        val result = loadModelWithOrientation(
            "{\"pivot\": \"modelBoundsCenter\", \"rotations\": {\"reverse\": [0, 1, 0, 0], \"front\": [0, 0, 0, 1]}}",
        )

        assertTrueFailureContaining(result, "sorted by position ID")
    }

    @Test
    fun rejectsRotationIdsThatDoNotMatchPositions() {
        val result = loadModelWithOrientation(
            "{\"pivot\": \"modelBoundsCenter\", \"rotations\": {\"front\": [0, 0, 0, 1], \"other\": [0, 1, 0, 0]}}",
        )

        assertTrueFailureContaining(result, "rotation IDs")
    }

    @Test
    fun rejectsDuplicatePositionIDs() {
        val result = loadModelWithOrientation(
            "{\"pivot\": \"modelBoundsCenter\", \"rotations\": {\"front\": [0, 0, 0, 1]}}",
            positionsJSON = "\"positions\": [{\"id\": \"front\", \"presentationID\": \"primary\", \"contactIDs\": [\"jug-front\", \"jug-reverse\"]}, {\"id\": \"front\", \"presentationID\": \"primary\", \"contactIDs\": [\"jug-front\", \"jug-reverse\"]}]",
        )

        assertTrueFailureContaining(result, "unique positions")
    }

    @Test
    fun rejectsBlankPositionIDs() {
        val result = loadModelWithOrientation(
            "{\"pivot\": \"modelBoundsCenter\", \"rotations\": {\"front\": [0, 0, 0, 1]}}",
            positionsJSON = "\"positions\": [{\"id\": \" \", \"presentationID\": \"primary\", \"contactIDs\": [\"jug-front\"]}]",
        )

        assertTrueFailureContaining(result, "positions[0].id")
    }

    @Test
    fun rejectsEmptyExplicitModelContactIDs() {
        val result = loadModelWithOrientation(
            "{\"pivot\": \"modelBoundsCenter\", \"rotations\": {\"front\": [0, 0, 0, 1], \"reverse\": [0, 1, 0, 0]}}",
            positionsJSON = "\"positions\": [{\"id\": \"front\", \"presentationID\": \"primary\", \"contactIDs\": []}, {\"id\": \"reverse\", \"presentationID\": \"primary\", \"contactIDs\": [\"jug-reverse\"]}]",
        )

        assertTrueFailureContaining(result, "contactIDs must not be empty")
    }

    @Test
    fun rejectsModelPositionContactIDsWithoutUnionCoverage() {
        val result = loadModelWithOrientation(
            "{\"pivot\": \"modelBoundsCenter\", \"rotations\": {\"front\": [0, 0, 0, 1], \"reverse\": [0, 1, 0, 0]}}",
            contactsJSON = defaultModelContactsJSON + ", " + contactJson("jug-extra", "Extra jug", "jug"),
        )

        assertTrueFailureContaining(result, "union coverage")
    }

    @Test
    fun acceptsIdenticalOverlappingModelPositionContactIDs() {
        val result = loadModelWithOrientation(
            "{\"pivot\": \"modelBoundsCenter\", \"rotations\": {\"front\": [0, 0, 0, 1], \"reverse\": [0, 1, 0, 0]}}",
            positionsJSON = "\"positions\": [{\"id\": \"front\", \"presentationID\": \"primary\", \"contactIDs\": [\"jug-front\", \"jug-reverse\"]}, {\"id\": \"reverse\", \"presentationID\": \"primary\", \"contactIDs\": [\"jug-front\", \"jug-reverse\"]}]",
        )

        assertTrue(result.isSuccess)
        assertTrue(result.getOrThrow().isEmpty())
    }

    @Test
    fun rejectsMixedImplicitAndExplicitModelPositions() {
        val result = loadModelWithOrientation(
            "{\"pivot\": \"modelBoundsCenter\", \"rotations\": {\"front\": [0, 0, 0, 1], \"reverse\": [0, 1, 0, 0]}}",
            positionsJSON = "\"positions\": [{\"id\": \"front\", \"presentationID\": \"primary\"}, {\"id\": \"reverse\", \"presentationID\": \"primary\", \"contactIDs\": [\"jug-reverse\"]}]",
        )

        assertTrueFailureContaining(result, "explicitly provided for every model position")
    }

    @Test
    fun retainsOrientationAndSuspensionTogether() {
        val result = loadModelWithOrientation(
            "{\"pivot\": \"modelBoundsCenter\", \"rotations\": {\"front\": [0, 0, 0, 1], \"reverse\": [0, 1, 0, 0]}}",
            suspension = "{\"type\": \"twoBranchCord\", \"passages\": {}, \"branches\": {}, \"anchor\": {}, \"canonicalPoses\": {}}",
        )

        assertTrue(result.isSuccess)
        assertTrue(result.getOrThrow().isEmpty())
    }

    @Test
    fun rejectsSupersededSingleCordSuspension() {
        val result = loadModelWithOrientation(
            "{\"pivot\": \"modelBoundsCenter\", \"rotations\": {\"front\": [0, 0, 0, 1], \"reverse\": [0, 1, 0, 0]}}",
            suspension = "{\"type\": \"singleCord\", \"attachment\": {}, \"anchor\": {}, \"cord\": {}, \"canonicalPoses\": {}}",
        )

        assertTrueFailureContaining(result, "suspension.type is unsupported: singleCord")
    }

    @Test
    fun preservesPackageSlugForTheCanvasAssetLookupWhenItDiffersFromTheLogicalBoardId() {
        val board = AssetBoardRepository(
            FixtureAssets(
                mapOf(
                    "Hangboards/asset-package-slug/board.json" to rasterBoardJson()
                        .replaceOnce("\"id\": \"demo.board\"", "\"id\": \"canonical.board-id\""),
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
    fun omitsModelOnlyPackageWithoutPngFallbackWhileKeepingRasterNeighbor() {
        val accessedPaths = mutableListOf<String>()
        val assets = FixtureAssets(
            mapOf(
                "Hangboards/raster-neighbor/board.json" to rasterBoardJson()
                    .replaceOnce("demo.board", "raster.neighbor")
                    .replaceOnce("Demo Board", "Raster Neighbor"),
                "Hangboards/raster-neighbor/assets/primary.png" to "png",
                "Hangboards/tension-flash-board/board.json" to modelOnlyBoardJson()
                    .replaceOnce("model.only", "tension.flash-board")
                    .replaceOnce("Model only", "Flash Board"),
                "Hangboards/tension-flash-board/assets/primary.usdz" to "usdz",
                "Hangboards/tension-flash-board/assets/primary.model.json" to "descriptor",
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
    }

    private fun loadRaster(boardJson: String): Result<List<Board>> = AssetBoardRepository(
        FixtureAssets(
            mapOf(
                "Hangboards/demo/board.json" to boardJson,
                "Hangboards/demo/assets/primary.png" to "png",
            ),
        ),
    ).loadBoards()

    private fun rasterBoardJson(): String =
        """
        {
          "schemaVersion": 3,
          "id": "demo.board",
          "manufacturer": "Demo",
          "name": "Demo Board",
          "subtitle": "A test board.",
          "productURL": "https://example.com/demo",
          "aspectRatio": 2.0,
          "equipmentObjects": [{ "id": "primary" }],
          "revisionID": "demo-revision",
          "contacts": [
            {
              "id": "path-edge",
              "equipmentObjectID": "primary",
              "name": "Path edge",
              "kind": "edge",
              "depth": { "range": { "minimum": 20, "maximum": 20 } },
              "gripTypes": ["halfCrimp", "openHand"]
            },
            {
              "id": "rounded-pocket",
              "equipmentObjectID": "primary",
              "name": "Rounded pocket",
              "kind": "pocket",
              "shape": "round",
              "depth": { "category": "medium" },
              "fingerCapacity": 2,
              "gripTypes": []
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
                "contactGeometry": {
                  "path-edge": [
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
                  ],
                  "rounded-pocket": [
                    {
                      "frame": { "x": 0.5, "y": 0.2, "width": 0.3, "height": 0.4 },
                      "shape": { "type": "roundedRect", "cornerRadiusFraction": 0.25 },
                      "shapeConstraint": { "shape": "roundedRectangle", "rotationDegrees": 0.0 }
                    }
                  ]
                }
              }
            }
          ]
        }
        """.trimIndent()

    private fun contactJson(id: String, name: String, kind: String): String =
        "{\"id\": \"$id\", \"equipmentObjectID\": \"primary\", \"name\": \"$name\", \"kind\": \"$kind\", \"gripTypes\": []}"

    private val defaultModelContactsJSON =
        contactJson("jug-front", "Front jug", "jug") + ", " + contactJson("jug-reverse", "Reverse jug", "jug")

    private val defaultModelPositionsJSON =
        "\"positions\": [{\"id\": \"front\", \"presentationID\": \"primary\", \"contactIDs\": [\"jug-front\"]}, {\"id\": \"reverse\", \"presentationID\": \"primary\", \"contactIDs\": [\"jug-reverse\"]}]"

    private fun modelOnlyBoardJson(
        positions: String? = null,
        contacts: String = contactJson("jug", "Jug", "jug"),
        mediaExtras: String? = null,
    ): String =
        """
        {
          "schemaVersion": 3,
          "id": "model.only",
          "revisionID": "model-revision",
          "manufacturer": "Demo",
          "name": "Model only",
          "subtitle": "A model-only board.",
          "productURL": "https://example.com/model",
          "aspectRatio": 2.0,
          "equipmentObjects": [{ "id": "primary" }],
          "contacts": [$contacts],
          ${positions?.let { "$it," }.orEmpty()}
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
                "descriptorPath": "assets/primary.model.json",
                "display": {}${mediaExtras?.let { ",\n                $it" }.orEmpty()}
              }
            }
          ]
        }
        """.trimIndent()

    private fun loadModelWithOrientation(
        orientation: String,
        positionsJSON: String? = defaultModelPositionsJSON,
        contactsJSON: String = defaultModelContactsJSON,
        suspension: String? = null,
    ): Result<List<Board>> = AssetBoardRepository(
        FixtureAssets(
            mapOf(
                "Hangboards/model/board.json" to modelOnlyBoardJson(
                    positions = positionsJSON,
                    contacts = contactsJSON,
                    mediaExtras = listOfNotNull(
                        "\"orientation\": $orientation",
                        suspension?.let { "\"suspension\": $it" },
                    ).joinToString(",\n                "),
                ),
            ),
        ),
    ).loadBoards()
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

/**
 * Replaces exactly one occurrence, failing loudly when the fixture text is
 * absent so a stale fixture edit can never silently test the unmodified JSON.
 */
internal fun String.replaceOnce(oldValue: String, newValue: String): String {
    val index = indexOf(oldValue)
    check(index >= 0) { "Fixture does not contain: $oldValue" }
    check(indexOf(oldValue, index + oldValue.length) < 0) { "Fixture contains more than one: $oldValue" }
    return replaceRange(index, index + oldValue.length, newValue)
}

private fun assertTrueFailureContaining(result: Result<*>, expected: String) {
    assertFalse(result.isSuccess)
    val message = result.exceptionOrNull()?.message
    assertTrue("Expected failure containing \"$expected\" but was: $message", message?.contains(expected) == true)
}
