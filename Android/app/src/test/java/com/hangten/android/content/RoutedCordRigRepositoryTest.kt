package com.hangten.android.content

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class RoutedCordRigRepositoryTest {
    @Test
    fun decodesEveryRoutedCordElementAndAliasesInheritTheCanonicalRig() {
        val board = loadBoard(boardJson()).getOrThrow().single()
        val canonical = board.presentation("primary")!!
        val alias = board.presentation("primary-inverted")!!
        val expectedRig = BoardCordRig.Routed(
            sceneSize = BoardCordSize(width = 1000f, height = 1000f),
            sourceFrame = BoardCordRect(x = 0f, y = 0f, width = 1000f, height = 1000f),
            innerFaceFrame = BoardCordRect(x = 0f, y = 0f, width = 1000f, height = 1000f),
            style = BoardRoutedCordStyle(
                diameter = 12f,
                outlineColor = "#101010",
                baseColor = "#2255AA",
                braidColors = listOf("#FFD000", "#0055CC"),
            ),
            ports = listOf(
                BoardRoutedCordPort("body-left", BoardRoutedCordSpace.Body, Point(200f, 650f)),
                BoardRoutedCordPort("body-right", BoardRoutedCordSpace.Body, Point(800f, 650f)),
                BoardRoutedCordPort("world-left", BoardRoutedCordSpace.World, Point(400f, 100f)),
                BoardRoutedCordPort("world-right", BoardRoutedCordSpace.World, Point(600f, 100f)),
            ),
            tensionGroups = listOf(
                BoardRoutedCordTensionGroup(
                    id = "main",
                    bodyPortIds = listOf("body-left", "body-right"),
                    worldPortIds = listOf("world-left", "world-right"),
                    pairing = BoardRoutedCordPairing.ScreenOrder,
                    layer = BoardRoutedCordLayer.BehindFace,
                ),
            ),
            paths = listOf(
                BoardRoutedCordPath(
                    id = "return-bight",
                    space = BoardRoutedCordSpace.Body,
                    layer = BoardRoutedCordLayer.AboveFace,
                    commands = listOf(
                        BoardRoutedCordPathCommand.Move(Point(200f, 650f)),
                        BoardRoutedCordPathCommand.Line(Point(300f, 700f)),
                        BoardRoutedCordPathCommand.Quad(
                            control = Point(500f, 800f),
                            to = Point(700f, 700f),
                        ),
                        BoardRoutedCordPathCommand.Curve(
                            control1 = Point(750f, 680f),
                            control2 = Point(780f, 660f),
                            to = Point(800f, 650f),
                        ),
                        BoardRoutedCordPathCommand.Close,
                    ),
                ),
            ),
            occlusions = listOf(
                BoardRoutedCordOcclusion.RadialLip(
                    bodyPortId = "body-left",
                    radius = 22f,
                    chordOffset = 6f,
                ),
                BoardRoutedCordOcclusion.FacePatch(
                    commands = listOf(
                        BoardRoutedCordPathCommand.Move(Point(760f, 610f)),
                        BoardRoutedCordPathCommand.Line(Point(840f, 610f)),
                        BoardRoutedCordPathCommand.Line(Point(840f, 690f)),
                        BoardRoutedCordPathCommand.Close,
                    ),
                ),
            ),
        )

        assertEquals(expectedRig, canonical.cordRig)
        assertEquals(expectedRig, board.resolvedCordRig(alias))
        assertEquals(canonical, board.artworkPresentation(alias))
    }

    @Test
    fun acceptsRequiredEmptyPathAndOcclusionArrays() {
        val source = boardJson(
            routedRigJson()
                .replace(pathJson(), "\"paths\": []")
                .replace(occlusionJson(), "\"occlusions\": []"),
        )

        val rig = loadBoard(source).getOrThrow().single().presentation("primary")!!.cordRig as BoardCordRig.Routed

        assertEquals(emptyList<BoardRoutedCordPath>(), rig.paths)
        assertEquals(emptyList<BoardRoutedCordOcclusion>(), rig.occlusions)
    }

    @Test
    fun rejectsMalformedRoutedTopologyAndFailsClosed() {
        val mutations = listOf(
            Mutation("\"diameter\": 12", "\"diameter\": 0", "style.diameter"),
            Mutation("\"outlineColor\": \"#101010\"", "\"outlineColor\": \"black\"", "#RRGGBB"),
            Mutation(
                "\"braidColors\": [\"#FFD000\", \"#0055CC\"]",
                "\"braidColors\": [\"#FFD000\"]",
                "exactly two",
            ),
            Mutation(
                "\"id\": \"body-right\", \"space\": \"body\"",
                "\"id\": \"body-left\", \"space\": \"body\"",
                "ports must have unique IDs",
            ),
            Mutation("\"id\": \"body-left\"", "\"id\": \"Body Left\"", "identifier-shaped"),
            Mutation("\"space\": \"body\"", "\"space\": \"board\"", "space is unsupported"),
            Mutation(
                "\"worldPortIDs\": [\"world-left\", \"world-right\"]",
                "\"worldPortIDs\": [\"world-left\"]",
                "equal cardinality",
            ),
            Mutation(
                "\"bodyPortIDs\": [\"body-left\", \"body-right\"]",
                "\"bodyPortIDs\": [\"body-left\", \"body-left\"]",
                "bodyPortIDs must be unique",
            ),
            Mutation(
                "\"worldPortIDs\": [\"world-left\", \"world-right\"]",
                "\"worldPortIDs\": [\"body-left\", \"world-right\"]",
                "worldPortIDs must reference world ports",
            ),
            Mutation("\"pairing\": \"screenOrder\"", "\"pairing\": \"nearest\"", "pairing is unsupported"),
            Mutation("\"layer\": \"behindFace\"", "\"layer\": \"under\"", "layer is unsupported"),
            Mutation(
                "\"command\": \"quad\", \"control\": [500, 800], \"to\": [700, 700]",
                "\"command\": \"arc\", \"control\": [500, 800], \"to\": [700, 700]",
                "command is unsupported",
            ),
            Mutation(
                "\"command\": \"move\", \"to\": [200, 650]",
                "\"command\": \"line\", \"to\": [200, 650]",
                "begin with exactly one move",
            ),
            Mutation(
                "\"radius\": 22, \"chordOffset\": 6",
                "\"radius\": 22, \"chordOffset\": 22",
                "0 < chordOffset < radius",
            ),
            Mutation(
                "\"bodyPortID\": \"body-left\"",
                "\"bodyPortID\": \"world-left\"",
                "radialLip must reference a body port",
            ),
            Mutation(
                "{ \"command\": \"line\", \"to\": [840, 690] },\n            { \"command\": \"close\" }",
                "{ \"command\": \"line\", \"to\": [840, 690] }",
                "facePatch commands must be closed",
            ),
            Mutation(
                "\"type\": \"facePatch\"",
                "\"type\": \"mask\"",
                "type is unsupported",
            ),
            Mutation(
                "\"baseColor\": \"#2255AA\"",
                "\"baseColor\": \"#2255AA\", \"opacity\": 1",
                "unknown key opacity",
            ),
            Mutation("\"type\": \"routed\"", "\"type\": \"routedV2\"", "type is unsupported"),
            Mutation(
                "\"sceneSize\": { \"width\": 1000, \"height\": 1000 }",
                "\"sceneSize\": { \"width\": 1000, \"height\": 1000 }, \"future\": true",
                "unknown key future",
            ),
            Mutation(
                "\"type\": \"facePatch\",\n          \"commands\"",
                "\"type\": \"facePatch\",\n          \"space\": \"world\",\n          \"commands\"",
                "unknown key space",
            ),
        )

        mutations.forEach { mutation ->
            val source = boardJson(routedRigJson().replace(mutation.old, mutation.new))
            assertFailureContains(loadBoard(source), mutation.expectedMessage)
        }
    }

    @Test
    fun rejectsMissingRequiredRoutedArraysAndEmptyRequiredTopology() {
        listOf(
            routedRigJson().replace(portJson(), "\"ports\": []") to "ports must be a non-empty array",
            routedRigJson().replace(tensionGroupJson(), "\"tensionGroups\": []") to
                "tensionGroups must be a non-empty array",
            routedRigJson(includePaths = false) to "paths is required",
            routedRigJson(includeOcclusions = false) to "occlusions is required",
        ).forEach { (rigJson, expectedMessage) ->
            assertFailureContains(loadBoard(boardJson(rigJson)), expectedMessage)
        }
    }

    @Test
    fun rejectsDuplicateTopologyIdsAndPathsWithoutOneValidDrawingSequence() {
        val duplicateGroup = appendArrayEntry(
            tensionGroupJson(),
            """        {
          "id": "main",
          "bodyPortIDs": ["body-right"],
          "worldPortIDs": ["world-right"],
          "pairing": "declared",
          "layer": "overpass"
        }""",
        )
        val duplicatePath = appendArrayEntry(
            pathJson(),
            """        {
          "id": "return-bight",
          "space": "world",
          "layer": "overpass",
          "commands": [
            { "command": "move", "to": [400, 100] },
            { "command": "line", "to": [600, 100] }
          ]
        }""",
        )
        val noDrawingSegment = pathJson().replace(
            """            { "command": "move", "to": [200, 650] },
            { "command": "line", "to": [300, 700] },
            { "command": "quad", "control": [500, 800], "to": [700, 700] },
            { "command": "curve", "control1": [750, 680], "control2": [780, 660], "to": [800, 650] },
            { "command": "close" }""",
            """            { "command": "move", "to": [200, 650] },
            { "command": "close" }""",
        )
        val nonterminalClose = pathJson().replace(
            "{ \"command\": \"line\", \"to\": [300, 700] },",
            "{ \"command\": \"close\" },\n            { \"command\": \"line\", \"to\": [300, 700] },",
        )
        val secondMove = pathJson().replace(
            "{ \"command\": \"line\", \"to\": [300, 700] },",
            "{ \"command\": \"move\", \"to\": [300, 700] },",
        )

        listOf(
            routedRigJson().replace(tensionGroupJson(), duplicateGroup) to
                "tensionGroups must have unique IDs",
            routedRigJson().replace(pathJson(), duplicatePath) to "paths must have unique IDs",
            routedRigJson().replace(pathJson(), noDrawingSegment) to "at least one line, quad, or curve",
            routedRigJson().replace(pathJson(), nonterminalClose) to "close command must appear only at the end",
            routedRigJson().replace(pathJson(), secondMove) to "begin with exactly one move",
        ).forEach { (rigJson, expectedMessage) ->
            assertFailureContains(loadBoard(boardJson(rigJson)), expectedMessage)
        }
    }

    @Test
    fun radialLipRequiresExactlyOneIncidentTensionSpan() {
        val noIncident = routedRigJson().replace(
            "\"bodyPortID\": \"body-left\"",
            "\"bodyPortID\": \"body-unused\"",
        ).replace(
            "{ \"id\": \"body-right\", \"space\": \"body\", \"point\": { \"x\": 800, \"y\": 650 } },",
            "{ \"id\": \"body-right\", \"space\": \"body\", \"point\": { \"x\": 800, \"y\": 650 } },\n"
                + "        { \"id\": \"body-unused\", \"space\": \"body\", \"point\": { \"x\": 500, \"y\": 650 } },",
        )
        val twiceIncident = routedRigJson().replace(
            tensionGroupJson(),
            """"tensionGroups": [
        {
          "id": "main",
          "bodyPortIDs": ["body-left", "body-right"],
          "worldPortIDs": ["world-left", "world-right"],
          "pairing": "screenOrder",
          "layer": "behindFace"
        },
        {
          "id": "secondary",
          "bodyPortIDs": ["body-left"],
          "worldPortIDs": ["world-left"],
          "pairing": "declared",
          "layer": "overpass"
        }
      ]""",
        )

        assertFailureContains(loadBoard(boardJson(noIncident)), "exactly one incident")
        assertFailureContains(loadBoard(boardJson(twiceIncident)), "exactly one incident")
    }

    @Test
    fun rejectsRoutedRigWhoseSceneAspectDoesNotMatchItsPresentation() {
        val source = boardJson().replace(
            "\"sceneSize\": { \"width\": 1000, \"height\": 1000 }",
            "\"sceneSize\": { \"width\": 1200, \"height\": 1000 }",
        )

        assertFailureContains(loadBoard(source), "aspectRatio must match cordRig.sceneSize")
    }

    @Test
    fun rejectsRoutedRigOwnedByAnAlias() {
        val aliasOwned = boardJson().replace(
            "\"rotationDegrees\": 180",
            "\"rotationDegrees\": 180,\n          \"cordRig\": ${routedRigJson()}",
        )
        assertFailureContains(loadBoard(aliasOwned), "cordRig must be owned by a canonical")
    }

    private fun loadBoard(source: String): Result<List<Board>> =
        AssetBoardRepository(
            FixtureAssets(
                mapOf(
                    "Hangboards/demo/board.json" to source,
                    "Hangboards/demo/assets/primary.png" to "png",
                ),
            ),
        ).loadBoards()

    private fun boardJson(rigJson: String = routedRigJson()): String =
        """
        {
          "id": "demo.board",
          "manufacturer": "Demo",
          "name": "Demo Board",
          "subtitle": "A test board.",
          "productURL": "https://example.com/demo",
          "aspectRatio": 1,
          "presentations": [
            {
              "id": "primary",
              "name": "Primary",
              "assetPath": "assets/primary.png",
              "aspectRatio": 1,
              "default": true,
              "cordRig": $rigJson
            },
            {
              "id": "primary-inverted",
              "name": "Primary inverted",
              "assetPath": "assets/primary.png",
              "aspectRatio": 1,
              "default": false,
              "sourcePresentationID": "primary",
              "rotationDegrees": 180
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
                  "frame": { "x": 0.35, "y": 0.35, "width": 0.3, "height": 0.3 },
                  "shape": { "type": "roundedRect", "cornerRadiusFraction": 0.2 }
                }
              ]
            }
          ]
        }
        """.trimIndent()

    private fun routedRigJson(
        includePaths: Boolean = true,
        includeOcclusions: Boolean = true,
    ): String {
        val topology = buildList {
            add(portJson())
            add(tensionGroupJson())
            if (includePaths) add(pathJson())
            if (includeOcclusions) add(occlusionJson())
        }.joinToString(",\n          ")
        return """
        {
          "type": "routed",
          "sceneSize": { "width": 1000, "height": 1000 },
          "sourceFrame": { "x": 0, "y": 0, "width": 1000, "height": 1000 },
          "innerFaceFrame": { "x": 0, "y": 0, "width": 1000, "height": 1000 },
          "style": {
            "diameter": 12,
            "outlineColor": "#101010",
            "baseColor": "#2255AA",
            "braidColors": ["#FFD000", "#0055CC"]
          },
          $topology
        }
        """.trimIndent()
    }

    private fun portJson(): String =
        """"ports": [
        { "id": "body-left", "space": "body", "point": { "x": 200, "y": 650 } },
        { "id": "body-right", "space": "body", "point": { "x": 800, "y": 650 } },
        { "id": "world-left", "space": "world", "point": { "x": 400, "y": 100 } },
        { "id": "world-right", "space": "world", "point": { "x": 600, "y": 100 } }
      ]"""

    private fun tensionGroupJson(): String =
        """"tensionGroups": [
        {
          "id": "main",
          "bodyPortIDs": ["body-left", "body-right"],
          "worldPortIDs": ["world-left", "world-right"],
          "pairing": "screenOrder",
          "layer": "behindFace"
        }
      ]"""

    private fun pathJson(): String =
        """"paths": [
        {
          "id": "return-bight",
          "space": "body",
          "layer": "aboveFace",
          "commands": [
            { "command": "move", "to": [200, 650] },
            { "command": "line", "to": [300, 700] },
            { "command": "quad", "control": [500, 800], "to": [700, 700] },
            { "command": "curve", "control1": [750, 680], "control2": [780, 660], "to": [800, 650] },
            { "command": "close" }
          ]
        }
      ]"""

    private fun occlusionJson(): String =
        """"occlusions": [
        {
          "type": "radialLip",
          "bodyPortID": "body-left",
          "radius": 22,
          "chordOffset": 6
        },
        {
          "type": "facePatch",
          "commands": [
            { "command": "move", "to": [760, 610] },
            { "command": "line", "to": [840, 610] },
            { "command": "line", "to": [840, 690] },
            { "command": "close" }
          ]
        }
      ]"""

    private fun appendArrayEntry(json: String, entry: String): String =
        json.dropLast(1) + ",\n$entry\n      ]"

    private data class Mutation(
        val old: String,
        val new: String,
        val expectedMessage: String,
    )
}

private fun assertFailureContains(result: Result<*>, expected: String) {
    assertFalse(result.isSuccess)
    assertTrue(
        "Expected failure containing '$expected', got '${result.exceptionOrNull()?.message}'",
        result.exceptionOrNull()?.message?.contains(expected) == true,
    )
}
