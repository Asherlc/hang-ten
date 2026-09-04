package com.hangten.android.board

import com.hangten.android.content.BoardCordRig
import com.hangten.android.content.BoardGeometryRotationAnchor
import com.hangten.android.content.BoardPresentation
import com.hangten.android.content.BoardRoutedCordLayer
import com.hangten.android.content.BoardRoutedCordOcclusion
import com.hangten.android.content.BoardRoutedCordPairing
import com.hangten.android.content.BoardRoutedCordPathCommand
import com.hangten.android.content.BoardRoutedCordSpace
import com.hangten.android.content.Point
import kotlin.math.cos
import kotlin.math.min
import kotlin.math.sin

internal data class BoardInPlaneTransform(
    val a: Float,
    val b: Float,
    val c: Float,
    val d: Float,
    val tx: Float,
    val ty: Float,
) {
    fun map(point: Point): Point = Point(
        x = a * point.x + c * point.y + tx,
        y = b * point.x + d * point.y + ty,
    )

    companion object {
        val Identity = BoardInPlaneTransform(1f, 0f, 0f, 1f, 0f, 0f)

        fun forPresentation(
            presentation: BoardPresentation,
            bounds: BoardBounds,
        ): BoardInPlaneTransform = rotatedAround(
            bounds,
            presentation.geometryRotationAnchor ?: BoardGeometryRotationAnchor.Center,
            presentation.resolvedRotationDegrees,
        )

        fun invertedAround(bounds: BoardBounds, anchor: BoardGeometryRotationAnchor): BoardInPlaneTransform {
            return rotatedAround(bounds, anchor, 180f)
        }

        fun rotatedAround(
            bounds: BoardBounds,
            anchor: BoardGeometryRotationAnchor,
            rotationDegrees: Float,
        ): BoardInPlaneTransform {
            val normalizedDegrees = ((rotationDegrees % 360f) + 360f) % 360f
            val (cosine, sine) = when (normalizedDegrees) {
                0f -> 1f to 0f
                90f -> 0f to 1f
                180f -> -1f to 0f
                270f -> 0f to -1f
                else -> {
                    val radians = Math.toRadians(normalizedDegrees.toDouble())
                    cos(radians).toFloat() to sin(radians).toFloat()
                }
            }
            val anchorX = bounds.left + bounds.width * anchor.x
            val anchorY = bounds.top + bounds.height * anchor.y
            return BoardInPlaneTransform(
                a = cosine,
                b = sine,
                c = if (sine == 0f) 0f else -sine,
                d = cosine,
                tx = anchorX - cosine * anchorX + sine * anchorY,
                ty = anchorY - sine * anchorX - cosine * anchorY,
            )
        }
    }
}

internal data class BoardCordStrand(
    val start: Point,
    val end: Point,
)

internal data class DirectTwoAnchorCordGeometry(
    val sceneBounds: BoardBounds,
    val faceBounds: BoardBounds,
    val faceTransform: BoardInPlaneTransform,
    val projectedAttachments: List<Point>,
    val pairedAttachments: List<Point>,
    val strands: List<BoardCordStrand>,
    val pullPoint: Point,
    val scale: Float,
) {
    fun projectFacePoint(normalizedPoint: Point): Point = faceTransform.map(
        Point(
            x = faceBounds.left + faceBounds.width * normalizedPoint.x,
            y = faceBounds.top + faceBounds.height * normalizedPoint.y,
        ),
    )
}

internal data class RoutedCordRigGeometry(
    val sceneBounds: BoardBounds,
    val sourceBounds: BoardBounds,
    val faceBounds: BoardBounds,
    val faceTransform: BoardInPlaneTransform,
    val scale: Float,
    val portPoints: Map<String, Point>,
    val spans: List<RoutedCordTensionSpan>,
    val paths: List<ResolvedRoutedCordPath>,
    val radialLips: List<ResolvedRoutedCordRadialLip>,
    val facePatches: List<ResolvedRoutedCordFacePatch>,
) {
    fun tensionSpans(layer: BoardRoutedCordLayer): List<RoutedCordTensionSpan> =
        spans.filter { it.layer == layer }

    fun authoredPaths(layer: BoardRoutedCordLayer): List<ResolvedRoutedCordPath> =
        paths.filter { it.layer == layer }
}

internal data class RoutedCordTensionSpan(
    val groupId: String,
    val layer: BoardRoutedCordLayer,
    val bodyPortId: String,
    val worldPortId: String,
    val bodyPoint: Point,
    val worldPoint: Point,
) {
    val path: BoardPath
        get() = BoardPath(
            commands = listOf(
                BoardPathCommand.MoveTo(worldPoint.x, worldPoint.y),
                BoardPathCommand.LineTo(bodyPoint.x, bodyPoint.y),
            ),
        )
}

internal data class ResolvedRoutedCordPath(
    val id: String,
    val space: BoardRoutedCordSpace,
    val layer: BoardRoutedCordLayer,
    val path: BoardPath,
    val definingPoints: List<Point>,
)

internal data class ResolvedRoutedCordRadialLip(
    val bodyPortId: String,
    val center: Point,
    val toward: Point,
    val radius: Float,
    val chordOffset: Float,
)

internal data class ResolvedRoutedCordFacePatch(
    val path: BoardPath,
    val definingPoints: List<Point>,
)

internal fun resolveRoutedCordRigGeometry(
    rig: BoardCordRig.Routed,
    presentation: BoardPresentation,
    canvasWidth: Float,
    canvasHeight: Float,
): RoutedCordRigGeometry? {
    if (!canvasWidth.isFinite() || !canvasHeight.isFinite() || canvasWidth <= 0f || canvasHeight <= 0f) {
        return null
    }
    if (!rig.sceneSize.width.isFinite() || !rig.sceneSize.height.isFinite() ||
        rig.sceneSize.width <= 0f || rig.sceneSize.height <= 0f
    ) {
        return null
    }
    val scale = min(canvasWidth / rig.sceneSize.width, canvasHeight / rig.sceneSize.height)
    if (!scale.isFinite() || scale <= 0f) return null

    val sceneBounds = BoardBounds(
        left = (canvasWidth - rig.sceneSize.width * scale) / 2f,
        top = (canvasHeight - rig.sceneSize.height * scale) / 2f,
        width = rig.sceneSize.width * scale,
        height = rig.sceneSize.height * scale,
    )
    val sourceBounds = BoardBounds(
        left = sceneBounds.left + rig.sourceFrame.x * scale,
        top = sceneBounds.top + rig.sourceFrame.y * scale,
        width = rig.sourceFrame.width * scale,
        height = rig.sourceFrame.height * scale,
    )
    val faceBounds = BoardBounds(
        left = sourceBounds.left + rig.innerFaceFrame.x * scale,
        top = sourceBounds.top + rig.innerFaceFrame.y * scale,
        width = rig.innerFaceFrame.width * scale,
        height = rig.innerFaceFrame.height * scale,
    )
    val faceTransform = BoardInPlaneTransform.forPresentation(presentation, sceneBounds)

    fun sourceRelativePoint(point: Point): Point = Point(
        x = sourceBounds.left + point.x * scale,
        y = sourceBounds.top + point.y * scale,
    )

    fun resolvedPoint(point: Point, space: BoardRoutedCordSpace): Point {
        val sourcePoint = sourceRelativePoint(point)
        return if (space == BoardRoutedCordSpace.Body) faceTransform.map(sourcePoint) else sourcePoint
    }

    val portPoints = rig.ports.associate { port ->
        port.id to resolvedPoint(port.point, port.space)
    }

    data class OrderedPort(
        val id: String,
        val point: Point,
        val declarationIndex: Int,
    )

    fun orderedPorts(ids: List<String>, pairing: BoardRoutedCordPairing): List<OrderedPort>? {
        val resolved = ids.mapIndexed { index, id ->
            OrderedPort(
                id = id,
                point = portPoints[id] ?: return null,
                declarationIndex = index,
            )
        }
        return if (pairing == BoardRoutedCordPairing.ScreenOrder) {
            resolved.sortedWith(
                compareBy<OrderedPort> { it.point.x }
                    .thenBy { it.point.y }
                    .thenBy { it.declarationIndex },
            )
        } else {
            resolved
        }
    }

    val spans = buildList {
        rig.tensionGroups.forEach { group ->
            val bodyPorts = orderedPorts(group.bodyPortIds, group.pairing) ?: return null
            val worldPorts = orderedPorts(group.worldPortIds, group.pairing) ?: return null
            if (bodyPorts.size != worldPorts.size) return null
            bodyPorts.zip(worldPorts).forEach { (bodyPort, worldPort) ->
                add(
                    RoutedCordTensionSpan(
                        groupId = group.id,
                        layer = group.layer,
                        bodyPortId = bodyPort.id,
                        worldPortId = worldPort.id,
                        bodyPoint = bodyPort.point,
                        worldPoint = worldPort.point,
                    ),
                )
            }
        }
    }

    fun resolvedPath(
        commands: List<BoardRoutedCordPathCommand>,
        space: BoardRoutedCordSpace,
    ): Pair<BoardPath, List<Point>> {
        val definingPoints = mutableListOf<Point>()
        val boardCommands = commands.map { command ->
            when (command) {
                is BoardRoutedCordPathCommand.Move -> resolvedPoint(command.to, space).let { point ->
                    definingPoints += point
                    BoardPathCommand.MoveTo(point.x, point.y)
                }
                is BoardRoutedCordPathCommand.Line -> resolvedPoint(command.to, space).let { point ->
                    definingPoints += point
                    BoardPathCommand.LineTo(point.x, point.y)
                }
                is BoardRoutedCordPathCommand.Quad -> {
                    val control = resolvedPoint(command.control, space)
                    val destination = resolvedPoint(command.to, space)
                    definingPoints += control
                    definingPoints += destination
                    BoardPathCommand.QuadTo(
                        controlX = control.x,
                        controlY = control.y,
                        x = destination.x,
                        y = destination.y,
                    )
                }
                is BoardRoutedCordPathCommand.Curve -> {
                    val control1 = resolvedPoint(command.control1, space)
                    val control2 = resolvedPoint(command.control2, space)
                    val destination = resolvedPoint(command.to, space)
                    definingPoints += control1
                    definingPoints += control2
                    definingPoints += destination
                    BoardPathCommand.CubicTo(
                        control1X = control1.x,
                        control1Y = control1.y,
                        control2X = control2.x,
                        control2Y = control2.y,
                        x = destination.x,
                        y = destination.y,
                    )
                }
                BoardRoutedCordPathCommand.Close -> BoardPathCommand.Close
            }
        }
        return BoardPath(commands = boardCommands) to definingPoints
    }

    val paths = rig.paths.map { authoredPath ->
        val (path, definingPoints) = resolvedPath(authoredPath.commands, authoredPath.space)
        ResolvedRoutedCordPath(
            id = authoredPath.id,
            space = authoredPath.space,
            layer = authoredPath.layer,
            path = path,
            definingPoints = definingPoints,
        )
    }
    val radialLips = mutableListOf<ResolvedRoutedCordRadialLip>()
    val facePatches = mutableListOf<ResolvedRoutedCordFacePatch>()
    rig.occlusions.forEach { occlusion ->
        when (occlusion) {
            is BoardRoutedCordOcclusion.RadialLip -> {
                val incidentSpan = spans.singleOrNull { it.bodyPortId == occlusion.bodyPortId }
                    ?: return null
                radialLips += ResolvedRoutedCordRadialLip(
                    bodyPortId = occlusion.bodyPortId,
                    center = incidentSpan.bodyPoint,
                    toward = incidentSpan.worldPoint,
                    radius = occlusion.radius * scale,
                    chordOffset = occlusion.chordOffset * scale,
                )
            }
            is BoardRoutedCordOcclusion.FacePatch -> {
                val (path, definingPoints) = resolvedPath(
                    commands = occlusion.commands,
                    space = BoardRoutedCordSpace.Body,
                )
                facePatches += ResolvedRoutedCordFacePatch(path, definingPoints)
            }
        }
    }

    return RoutedCordRigGeometry(
        sceneBounds = sceneBounds,
        sourceBounds = sourceBounds,
        faceBounds = faceBounds,
        faceTransform = faceTransform,
        scale = scale,
        portPoints = portPoints,
        spans = spans,
        paths = paths,
        radialLips = radialLips,
        facePatches = facePatches,
    )
}

internal fun resolveDirectTwoAnchorCordGeometry(
    rig: BoardCordRig.DirectTwoAnchor,
    presentation: BoardPresentation,
    canvasWidth: Float,
    canvasHeight: Float,
): DirectTwoAnchorCordGeometry? {
    if (!canvasWidth.isFinite() || !canvasHeight.isFinite() || canvasWidth <= 0f || canvasHeight <= 0f) {
        return null
    }
    if (!rig.sceneSize.width.isFinite() || !rig.sceneSize.height.isFinite() ||
        rig.sceneSize.width <= 0f || rig.sceneSize.height <= 0f
    ) {
        return null
    }
    val scale = min(canvasWidth / rig.sceneSize.width, canvasHeight / rig.sceneSize.height)
    if (!scale.isFinite() || scale <= 0f) return null

    val sceneBounds = BoardBounds(
        left = (canvasWidth - rig.sceneSize.width * scale) / 2f,
        top = (canvasHeight - rig.sceneSize.height * scale) / 2f,
        width = rig.sceneSize.width * scale,
        height = rig.sceneSize.height * scale,
    )
    val faceBounds = BoardBounds(
        left = sceneBounds.left + (rig.sourceFrame.x + rig.innerFaceFrame.x) * scale,
        top = sceneBounds.top + (rig.sourceFrame.y + rig.innerFaceFrame.y) * scale,
        width = rig.innerFaceFrame.width * scale,
        height = rig.innerFaceFrame.height * scale,
    )
    val faceTransform = BoardInPlaneTransform.forPresentation(presentation, sceneBounds)

    fun sourceRelativePoint(point: Point): Point = Point(
        x = sceneBounds.left + (rig.sourceFrame.x + point.x) * scale,
        y = sceneBounds.top + (rig.sourceFrame.y + point.y) * scale,
    )

    val projectedAttachments = rig.attachmentPoints.map { faceTransform.map(sourceRelativePoint(it)) }
    val pairedAttachments = projectedAttachments.sortedWith(compareBy<Point> { it.x }.thenBy { it.y })
    val pullPoint = sourceRelativePoint(rig.pullPoint)
    val exits = listOf(
        Point(pullPoint.x - 22f * scale, pullPoint.y),
        Point(pullPoint.x + 22f * scale, pullPoint.y),
    )
    val strands = exits.zip(pairedAttachments) { exit, attachment -> BoardCordStrand(exit, attachment) }

    return DirectTwoAnchorCordGeometry(
        sceneBounds = sceneBounds,
        faceBounds = faceBounds,
        faceTransform = faceTransform,
        projectedAttachments = projectedAttachments,
        pairedAttachments = pairedAttachments,
        strands = strands,
        pullPoint = pullPoint,
        scale = scale,
    )
}
