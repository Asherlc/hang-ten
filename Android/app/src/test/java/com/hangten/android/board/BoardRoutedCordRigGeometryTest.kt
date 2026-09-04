package com.hangten.android.board

import com.hangten.android.content.BoardCordRect
import com.hangten.android.content.BoardCordRig
import com.hangten.android.content.BoardCordSize
import com.hangten.android.content.Board
import com.hangten.android.content.BoardGeometryRotationAnchor
import com.hangten.android.content.BoardPresentation
import com.hangten.android.content.BoardRoutedCordLayer
import com.hangten.android.content.BoardRoutedCordPairing
import com.hangten.android.content.BoardRoutedCordOcclusion
import com.hangten.android.content.BoardRoutedCordPath
import com.hangten.android.content.BoardRoutedCordPathCommand
import com.hangten.android.content.BoardRoutedCordPort
import com.hangten.android.content.BoardRoutedCordSpace
import com.hangten.android.content.BoardRoutedCordStyle
import com.hangten.android.content.BoardRoutedCordTensionGroup
import com.hangten.android.content.Point
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Test

class BoardRoutedCordRigGeometryTest {
    @Test
    fun bodyPortRotatesClockwiseAtEverySupportedAngleWhileWorldPortStaysFixed() {
        val expectedBodyPoints = listOf(
            0f to Point(30f, 60f),
            45f to Point(28.7868f, 42.9289f),
            90f to Point(40f, 30f),
            180f to Point(70f, 40f),
        )

        expectedBodyPoints.forEach { (rotationDegrees, expectedBodyPoint) ->
            val geometry = resolveRoutedCordRigGeometry(
                rig = routedRig(),
                presentation = presentation(rotationDegrees),
                canvasWidth = 100f,
                canvasHeight = 100f,
            )

            assertNotNull("Expected geometry at $rotationDegrees degrees", geometry)
            assertPoint(expectedBodyPoint, geometry!!.portPoints.getValue("body"))
            assertPoint(Point(50f, 20f), geometry.portPoints.getValue("world"))
            assertEquals(BoardBounds(0f, 0f, 100f, 100f), geometry.sceneBounds)
            assertEquals(BoardBounds(10f, 20f, 80f, 60f), geometry.sourceBounds)
            assertEquals(BoardBounds(20f, 30f, 60f, 40f), geometry.faceBounds)
        }
    }

    @Test
    fun declaredPairingPreservesIdsWhileScreenOrderUsesTransformedCoordinates() {
        val rig = routedRig(
            ports = listOf(
                port("body-a", BoardRoutedCordSpace.Body, 20f, 40f),
                port("body-b", BoardRoutedCordSpace.Body, 60f, 40f),
                port("world-a", BoardRoutedCordSpace.World, 10f, -10f),
                port("world-b", BoardRoutedCordSpace.World, 70f, -10f),
            ),
            tensionGroups = listOf(
                tensionGroup(
                    id = "declared",
                    bodyPortIds = listOf("body-a", "body-b"),
                    worldPortIds = listOf("world-b", "world-a"),
                    pairing = BoardRoutedCordPairing.Declared,
                ),
                tensionGroup(
                    id = "screen",
                    bodyPortIds = listOf("body-a", "body-b"),
                    worldPortIds = listOf("world-b", "world-a"),
                    pairing = BoardRoutedCordPairing.ScreenOrder,
                ),
            ),
        )

        val spans = resolveRoutedCordRigGeometry(
            rig,
            presentation(180f),
            canvasWidth = 100f,
            canvasHeight = 100f,
        )!!.spans

        assertEquals(
            listOf(
                "declared:body-a:world-b",
                "declared:body-b:world-a",
                "screen:body-b:world-a",
                "screen:body-a:world-b",
            ),
            spans.map { "${it.groupId}:${it.bodyPortId}:${it.worldPortId}" },
        )
    }

    @Test
    fun screenOrderUsesYThenDeclarationIndexAsStableTieBreakers() {
        val rig = routedRig(
            ports = listOf(
                port("body-first", BoardRoutedCordSpace.Body, 40f, 40f),
                port("body-second", BoardRoutedCordSpace.Body, 40f, 40f),
                port("world-first", BoardRoutedCordSpace.World, 40f, -10f),
                port("world-second", BoardRoutedCordSpace.World, 40f, -10f),
            ),
            tensionGroups = listOf(
                tensionGroup(
                    id = "ties",
                    bodyPortIds = listOf("body-second", "body-first"),
                    worldPortIds = listOf("world-second", "world-first"),
                    pairing = BoardRoutedCordPairing.ScreenOrder,
                ),
            ),
        )

        val spans = resolveRoutedCordRigGeometry(
            rig,
            presentation(180f),
            canvasWidth = 100f,
            canvasHeight = 100f,
        )!!.spans

        assertEquals(
            listOf("body-second:world-second", "body-first:world-first"),
            spans.map { "${it.bodyPortId}:${it.worldPortId}" },
        )
    }

    @Test
    fun pathsAndOcclusionsResolveInTheirDeclaredSpacesAndLayers() {
        val bodyCommands = listOf(
            BoardRoutedCordPathCommand.Move(Point(20f, 40f)),
            BoardRoutedCordPathCommand.Line(Point(30f, 40f)),
            BoardRoutedCordPathCommand.Quad(Point(35f, 30f), Point(40f, 40f)),
            BoardRoutedCordPathCommand.Curve(
                control1 = Point(45f, 30f),
                control2 = Point(50f, 35f),
                to = Point(50f, 40f),
            ),
            BoardRoutedCordPathCommand.Close,
        )
        val facePatchCommands = listOf(
            BoardRoutedCordPathCommand.Move(Point(15f, 15f)),
            BoardRoutedCordPathCommand.Line(Point(25f, 15f)),
            BoardRoutedCordPathCommand.Line(Point(25f, 25f)),
            BoardRoutedCordPathCommand.Close,
        )
        val rig = routedRig(
            paths = listOf(
                BoardRoutedCordPath(
                    id = "body-return",
                    space = BoardRoutedCordSpace.Body,
                    layer = BoardRoutedCordLayer.AboveFace,
                    commands = bodyCommands,
                ),
                BoardRoutedCordPath(
                    id = "world-loop",
                    space = BoardRoutedCordSpace.World,
                    layer = BoardRoutedCordLayer.Overpass,
                    commands = listOf(
                        BoardRoutedCordPathCommand.Move(Point(0f, 0f)),
                        BoardRoutedCordPathCommand.Line(Point(10f, 0f)),
                    ),
                ),
            ),
            occlusions = listOf(
                BoardRoutedCordOcclusion.RadialLip("body", radius = 6f, chordOffset = 2f),
                BoardRoutedCordOcclusion.FacePatch(facePatchCommands),
            ),
        )

        val geometry = resolveRoutedCordRigGeometry(
            rig,
            presentation(90f),
            canvasWidth = 100f,
            canvasHeight = 100f,
        )!!

        assertEquals(
            listOf(
                BoardPathCommand.MoveTo(40f, 30f),
                BoardPathCommand.LineTo(40f, 40f),
                BoardPathCommand.QuadTo(50f, 45f, 40f, 50f),
                BoardPathCommand.CubicTo(50f, 55f, 45f, 60f, 40f, 60f),
                BoardPathCommand.Close,
            ),
            geometry.paths.single { it.id == "body-return" }.path.commands,
        )
        assertEquals(
            listOf(
                BoardPathCommand.MoveTo(10f, 20f),
                BoardPathCommand.LineTo(20f, 20f),
            ),
            geometry.paths.single { it.id == "world-loop" }.path.commands,
        )
        val lip = geometry.radialLips.single()
        assertPoint(Point(40f, 30f), lip.center)
        assertPoint(Point(50f, 20f), lip.toward)
        assertEquals(6f, lip.radius, 0.0001f)
        assertEquals(2f, lip.chordOffset, 0.0001f)
        assertEquals(
            listOf(
                BoardPathCommand.MoveTo(65f, 25f),
                BoardPathCommand.LineTo(65f, 35f),
                BoardPathCommand.LineTo(55f, 35f),
                BoardPathCommand.Close,
            ),
            geometry.facePatches.single().path.commands,
        )
    }

    @Test
    fun validGeometrySatisfiesGravityAndSceneSafetyAtEveryPresentationAngle() {
        listOf(0f, 45f, 90f, 180f).forEach { rotationDegrees ->
            assertNull(
                "Expected valid routed geometry at $rotationDegrees degrees",
                routedCordPresentationValidationFailure(
                    rig = routedRig(),
                    presentation = presentation(rotationDegrees),
                ),
            )
        }
    }

    @Test
    fun centerlinesLeavePointEightCordDiametersInsideEverySceneEdge() {
        val diameter = 10f
        val exactlyOnInset = routedRig(
            ports = listOf(
                port("body", BoardRoutedCordSpace.Body, 20f, 40f),
                port("world", BoardRoutedCordSpace.World, -2f, 0f),
            ),
        ).copy(style = routedRig().style.copy(diameter = diameter))
        val crossingInset = exactlyOnInset.copy(
            ports = exactlyOnInset.ports.map { port ->
                if (port.id == "world") port.copy(point = Point(-2.1f, 0f)) else port
            },
        )

        assertNull(
            routedCordPresentationValidationFailure(exactlyOnInset, presentation(0f)),
        )
        assertEquals(
            RoutedCordPresentationValidationFailure.CenterlineOutsideScene,
            routedCordPresentationValidationFailure(crossingInset, presentation(0f)),
        )
    }

    @Test
    fun safetyChecksPathControlsFacePatchesRadialLipsAndGravity() {
        val outsideControlRig = routedRig(
            paths = listOf(
                BoardRoutedCordPath(
                    id = "outside-control",
                    space = BoardRoutedCordSpace.World,
                    layer = BoardRoutedCordLayer.AboveFace,
                    commands = listOf(
                        BoardRoutedCordPathCommand.Move(Point(0f, 0f)),
                        BoardRoutedCordPathCommand.Quad(
                            control = Point(-9f, 10f),
                            to = Point(10f, 0f),
                        ),
                    ),
                ),
            ),
        )
        val outsidePatchRig = routedRig(
            occlusions = listOf(
                BoardRoutedCordOcclusion.FacePatch(
                    listOf(
                        BoardRoutedCordPathCommand.Move(Point(-11f, 0f)),
                        BoardRoutedCordPathCommand.Line(Point(0f, 0f)),
                        BoardRoutedCordPathCommand.Close,
                    ),
                ),
            ),
        )
        val outsideLipRig = routedRig(
            occlusions = listOf(
                BoardRoutedCordOcclusion.RadialLip("body", radius = 31f, chordOffset = 2f),
            ),
        )
        val slackRig = routedRig(
            ports = listOf(
                port("body", BoardRoutedCordSpace.Body, 40f, 0f),
                port("world", BoardRoutedCordSpace.World, 40f, 0f),
            ),
        )

        assertEquals(
            RoutedCordPresentationValidationFailure.CenterlineOutsideScene,
            routedCordPresentationValidationFailure(outsideControlRig, presentation(0f)),
        )
        assertEquals(
            RoutedCordPresentationValidationFailure.FacePatchOutsideScene,
            routedCordPresentationValidationFailure(outsidePatchRig, presentation(0f)),
        )
        assertEquals(
            RoutedCordPresentationValidationFailure.RadialLipOutsideScene,
            routedCordPresentationValidationFailure(outsideLipRig, presentation(0f)),
        )
        assertEquals(
            RoutedCordPresentationValidationFailure.BodyNotBelowWorld("body", "world"),
            routedCordPresentationValidationFailure(slackRig, presentation(0f)),
        )
    }

    @Test
    fun boardCanvasUsesCanonicalRoutedFaceGeometryForRotationAliases() {
        val rig = routedRig()
        val canonical = presentation(0f).copy(id = "primary", cordRig = rig)
        val alias = presentation(90f)
        val board = Board(
            id = "demo.board",
            manufacturer = "Demo",
            name = "Demo",
            subtitle = "Demo",
            productUrl = "https://example.com/demo",
            aspectRatio = 1f,
            presentations = listOf(canonical, alias),
            holds = emptyList(),
        )

        val canvas = boardCanvasGeometry(board, alias, width = 100f, height = 100f)!!

        assertEquals(BoardBounds(20f, 30f, 60f, 40f), canvas.holdBounds)
        assertEquals(BoardInPlaneTransform(0f, 1f, -1f, 0f, 100f, 0f), canvas.faceTransform)
        assertEquals(rig, canvas.routedRig)
        assertNotNull(canvas.routedCordGeometry)
        assertNull(canvas.directTwoAnchorRig)
        assertNull(canvas.cordGeometry)
    }

    @Test
    fun routedArtworkOperationsFollowTheFrozenLayerAndOcclusionOrder() {
        val rig = routedRig(
            paths = listOf(
                BoardRoutedCordPath(
                    id = "overpass",
                    space = BoardRoutedCordSpace.World,
                    layer = BoardRoutedCordLayer.Overpass,
                    commands = listOf(
                        BoardRoutedCordPathCommand.Move(Point(0f, 0f)),
                        BoardRoutedCordPathCommand.Line(Point(10f, 0f)),
                    ),
                ),
            ),
            occlusions = listOf(
                BoardRoutedCordOcclusion.RadialLip("body", radius = 6f, chordOffset = 2f),
                BoardRoutedCordOcclusion.FacePatch(
                    listOf(
                        BoardRoutedCordPathCommand.Move(Point(15f, 15f)),
                        BoardRoutedCordPathCommand.Line(Point(25f, 15f)),
                        BoardRoutedCordPathCommand.Close,
                    ),
                ),
            ),
        )
        val geometry = resolveRoutedCordRigGeometry(
            rig,
            presentation(0f),
            canvasWidth = 100f,
            canvasHeight = 100f,
        )!!

        val stages = routedArtworkOperations(geometry).map { operation ->
            when (operation) {
                is RoutedArtworkOperation.CordLayer -> "cord:${operation.layer}"
                RoutedArtworkOperation.Face -> "face"
                is RoutedArtworkOperation.RadialLipFaceRedraw -> "redraw:radialLip"
                is RoutedArtworkOperation.FacePatchFaceRedraw -> "redraw:facePatch"
            }
        }

        assertEquals(
            listOf(
                "cord:BehindFace",
                "face",
                "cord:AboveFace",
                "redraw:radialLip",
                "redraw:facePatch",
                "cord:Overpass",
            ),
            stages,
        )
    }

    private fun routedRig(
        ports: List<BoardRoutedCordPort> = listOf(
            port("body", BoardRoutedCordSpace.Body, 20f, 40f),
            port("world", BoardRoutedCordSpace.World, 40f, 0f),
        ),
        tensionGroups: List<BoardRoutedCordTensionGroup> = listOf(
            tensionGroup(
                id = "main",
                bodyPortIds = listOf("body"),
                worldPortIds = listOf("world"),
                pairing = BoardRoutedCordPairing.Declared,
            ),
        ),
        paths: List<BoardRoutedCordPath> = emptyList(),
        occlusions: List<BoardRoutedCordOcclusion> = emptyList(),
    ) = BoardCordRig.Routed(
        sceneSize = BoardCordSize(100f, 100f),
        sourceFrame = BoardCordRect(10f, 20f, 80f, 60f),
        innerFaceFrame = BoardCordRect(10f, 10f, 60f, 40f),
        style = BoardRoutedCordStyle(
            diameter = 4f,
            outlineColor = "#101010",
            baseColor = "#2255AA",
            braidColors = listOf("#FFD000", "#0055CC"),
        ),
        ports = ports,
        tensionGroups = tensionGroups,
        paths = paths,
        occlusions = occlusions,
    )

    private fun port(
        id: String,
        space: BoardRoutedCordSpace,
        x: Float,
        y: Float,
    ) = BoardRoutedCordPort(id, space, Point(x, y))

    private fun tensionGroup(
        id: String,
        bodyPortIds: List<String>,
        worldPortIds: List<String>,
        pairing: BoardRoutedCordPairing,
        layer: BoardRoutedCordLayer = BoardRoutedCordLayer.BehindFace,
    ) = BoardRoutedCordTensionGroup(
        id = id,
        bodyPortIds = bodyPortIds,
        worldPortIds = worldPortIds,
        pairing = pairing,
        layer = layer,
    )

    private fun presentation(rotationDegrees: Float) = BoardPresentation(
        id = "position-$rotationDegrees",
        name = "Position",
        assetPath = "assets/primary.png",
        aspectRatio = 1f,
        isDefault = rotationDegrees == 0f,
        sourcePresentationId = if (rotationDegrees == 0f) null else "primary",
        rotationDegrees = if (rotationDegrees == 0f) null else rotationDegrees,
        geometryRotationAnchor = if (rotationDegrees == 0f) {
            null
        } else {
            BoardGeometryRotationAnchor.Center
        },
    )

    private fun assertPoint(expected: Point, actual: Point) {
        assertEquals(expected.x, actual.x, 0.0001f)
        assertEquals(expected.y, actual.y, 0.0001f)
    }
}
