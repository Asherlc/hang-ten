package com.hangten.android.board

import android.graphics.BitmapFactory
import android.graphics.DashPathEffect
import android.graphics.Matrix
import android.graphics.Paint
import android.graphics.Path
import android.graphics.PathDashPathEffect
import android.graphics.RectF
import android.graphics.Region
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clipToBounds
import androidx.compose.ui.graphics.ImageBitmap
import androidx.compose.ui.graphics.asAndroidBitmap
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.graphics.drawscope.drawIntoCanvas
import androidx.compose.ui.graphics.nativeCanvas
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.layout.onSizeChanged
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.semantics.stateDescription
import androidx.compose.ui.unit.IntSize
import com.hangten.android.content.Board
import com.hangten.android.content.BoardCordRig
import com.hangten.android.content.BoardGeometry
import com.hangten.android.content.BoardPresentation
import com.hangten.android.content.BoardRoutedCordLayer
import com.hangten.android.content.HoldShape
import com.hangten.android.content.PathCommand
import com.hangten.android.content.Point
import kotlin.math.atan2
import kotlin.math.ceil
import kotlin.math.floor
import kotlin.math.max
import kotlin.math.min
import kotlin.math.sqrt

internal data class BoardBounds(
    val left: Float,
    val top: Float,
    val width: Float,
    val height: Float,
)

internal sealed interface BoardPathCommand {
    data class MoveTo(val x: Float, val y: Float) : BoardPathCommand
    data class LineTo(val x: Float, val y: Float) : BoardPathCommand
    data class QuadTo(val controlX: Float, val controlY: Float, val x: Float, val y: Float) : BoardPathCommand
    data class CubicTo(
        val control1X: Float,
        val control1Y: Float,
        val control2X: Float,
        val control2Y: Float,
        val x: Float,
        val y: Float,
    ) : BoardPathCommand

    data object Close : BoardPathCommand
}

internal data class BoardPath(
    val commands: List<BoardPathCommand> = emptyList(),
    val roundedRectangle: RoundedRectangle? = null,
) {
    data class RoundedRectangle(
        val left: Float,
        val top: Float,
        val right: Float,
        val bottom: Float,
        val radiusX: Float,
        val radiusY: Float,
    )
}

internal fun BoardGeometry.toBoardPath(bounds: BoardBounds): BoardPath {
    fun point(normalized: Point): Pair<Float, Float> = normalized.let {
        bounds.left + (frame.x + frame.width * it.x) * bounds.width to
            bounds.top + (frame.y + frame.height * it.y) * bounds.height
    }

    return when (val shape = shape) {
        is HoldShape.RoundedRect -> {
            val left = bounds.left + frame.x * bounds.width
            val top = bounds.top + frame.y * bounds.height
            val width = frame.width * bounds.width
            val height = frame.height * bounds.height
            val radius = min(width, height) * shape.cornerRadiusFraction
            BoardPath(
                roundedRectangle = BoardPath.RoundedRectangle(
                    left = left,
                    top = top,
                    right = left + width,
                    bottom = top + height,
                    radiusX = radius,
                    radiusY = radius,
                ),
            )
        }

        is HoldShape.Path -> BoardPath(
            commands = shape.commands.map { command ->
                when (command) {
                    is PathCommand.Move -> point(command.to).let { BoardPathCommand.MoveTo(it.first, it.second) }
                    is PathCommand.Line -> point(command.to).let { BoardPathCommand.LineTo(it.first, it.second) }
                    is PathCommand.Quad -> {
                        val control = point(command.control)
                        val destination = point(command.to)
                        BoardPathCommand.QuadTo(control.first, control.second, destination.first, destination.second)
                    }

                    is PathCommand.Curve -> {
                        val control1 = point(command.control1)
                        val control2 = point(command.control2)
                        val destination = point(command.to)
                        BoardPathCommand.CubicTo(
                            control1.first,
                            control1.second,
                            control2.first,
                            control2.second,
                            destination.first,
                            destination.second,
                        )
                    }

                    PathCommand.Close -> BoardPathCommand.Close
                }
            },
        )
    }
}

internal fun BoardPath.transformed(transform: BoardInPlaneTransform): BoardPath {
    fun mapped(x: Float, y: Float): Point = transform.map(Point(x, y))

    val keepsAxesAligned = transform.b == 0f && transform.c == 0f
    val transformedRoundedRectangle = roundedRectangle?.takeIf { keepsAxesAligned }?.let { rounded ->
        val first = mapped(rounded.left, rounded.top)
        val second = mapped(rounded.right, rounded.bottom)
        BoardPath.RoundedRectangle(
            left = minOf(first.x, second.x),
            top = minOf(first.y, second.y),
            right = maxOf(first.x, second.x),
            bottom = maxOf(first.y, second.y),
            radiusX = rounded.radiusX,
            radiusY = rounded.radiusY,
        )
    }
    val sourceCommands = if (roundedRectangle != null && !keepsAxesAligned) {
        roundedRectangle.commands()
    } else {
        commands
    }
    val transformedCommands = sourceCommands.map { command ->
        when (command) {
            is BoardPathCommand.MoveTo -> mapped(command.x, command.y).let {
                BoardPathCommand.MoveTo(it.x, it.y)
            }
            is BoardPathCommand.LineTo -> mapped(command.x, command.y).let {
                BoardPathCommand.LineTo(it.x, it.y)
            }
            is BoardPathCommand.QuadTo -> {
                val control = mapped(command.controlX, command.controlY)
                val destination = mapped(command.x, command.y)
                BoardPathCommand.QuadTo(control.x, control.y, destination.x, destination.y)
            }
            is BoardPathCommand.CubicTo -> {
                val control1 = mapped(command.control1X, command.control1Y)
                val control2 = mapped(command.control2X, command.control2Y)
                val destination = mapped(command.x, command.y)
                BoardPathCommand.CubicTo(
                    control1.x,
                    control1.y,
                    control2.x,
                    control2.y,
                    destination.x,
                    destination.y,
                )
            }
            BoardPathCommand.Close -> BoardPathCommand.Close
        }
    }
    return BoardPath(commands = transformedCommands, roundedRectangle = transformedRoundedRectangle)
}

private fun BoardPath.RoundedRectangle.commands(): List<BoardPathCommand> {
    val controlScale = 0.5522848f
    val leftInner = left + radiusX
    val rightInner = right - radiusX
    val topInner = top + radiusY
    val bottomInner = bottom - radiusY
    return listOf(
        BoardPathCommand.MoveTo(leftInner, top),
        BoardPathCommand.LineTo(rightInner, top),
        BoardPathCommand.CubicTo(
            rightInner + radiusX * controlScale,
            top,
            right,
            topInner - radiusY * controlScale,
            right,
            topInner,
        ),
        BoardPathCommand.LineTo(right, bottomInner),
        BoardPathCommand.CubicTo(
            right,
            bottomInner + radiusY * controlScale,
            rightInner + radiusX * controlScale,
            bottom,
            rightInner,
            bottom,
        ),
        BoardPathCommand.LineTo(leftInner, bottom),
        BoardPathCommand.CubicTo(
            leftInner - radiusX * controlScale,
            bottom,
            left,
            bottomInner + radiusY * controlScale,
            left,
            bottomInner,
        ),
        BoardPathCommand.LineTo(left, topInner),
        BoardPathCommand.CubicTo(
            left,
            topInner - radiusY * controlScale,
            leftInner - radiusX * controlScale,
            top,
            leftInner,
            top,
        ),
        BoardPathCommand.Close,
    )
}

private fun BoardPath.toAndroidPath(): Path = Path().apply {
    roundedRectangle?.let { rounded ->
        addRoundRect(
            rounded.left,
            rounded.top,
            rounded.right,
            rounded.bottom,
            rounded.radiusX,
            rounded.radiusY,
            Path.Direction.CW,
        )
    }
    commands.forEach { command ->
        when (command) {
            is BoardPathCommand.MoveTo -> moveTo(command.x, command.y)
            is BoardPathCommand.LineTo -> lineTo(command.x, command.y)
            is BoardPathCommand.QuadTo -> quadTo(command.controlX, command.controlY, command.x, command.y)
            is BoardPathCommand.CubicTo -> cubicTo(
                command.control1X,
                command.control1Y,
                command.control2X,
                command.control2Y,
                command.x,
                command.y,
            )

            BoardPathCommand.Close -> close()
        }
    }
}

private fun BoardPath.contains(x: Float, y: Float, bounds: BoardBounds): Boolean {
    val path = toAndroidPath()
    val clip = Region(
        floor(bounds.left).toInt(),
        floor(bounds.top).toInt(),
        ceil(bounds.left + bounds.width).toInt(),
        ceil(bounds.top + bounds.height).toInt(),
    )
    return Region().apply { setPath(path, clip) }.contains(x.toInt(), y.toInt())
}

@Composable
fun BoardCanvas(
    board: Board,
    activeHoldIDs: Set<String>,
    onHoldTap: (String) -> Unit,
    modifier: Modifier = Modifier,
    imageOverride: ImageBitmap? = null,
    presentationId: String? = null,
) {
    val presentation = board.presentation(presentationId)
        ?: board.presentations.firstOrNull { it.isDefault }
        ?: board.presentations.firstOrNull()
    val artworkPresentation = presentation?.let(board::artworkPresentation)
    val context = LocalContext.current
    val bundledImage = remember(board.packageName, artworkPresentation?.assetPath) {
        artworkPresentation?.let { loadBoardImage(context, board.packageName, it) }
    }
    val boardImage = imageOverride ?: bundledImage
    var canvasSize by remember { mutableStateOf(IntSize.Zero) }
    val activeDescription = activeHoldIDs.joinToString(separator = ", ")
        .ifEmpty { "No active holds" }
    val inputModifier = Modifier.pointerInput(board, presentation, canvasSize) {
        detectTapGestures { tap ->
            val selectedPresentation = presentation ?: return@detectTapGestures
            val canvasGeometry = boardCanvasGeometry(board, selectedPresentation, canvasSize)
                ?: return@detectTapGestures
            val clipBounds = BoardBounds(0f, 0f, canvasSize.width.toFloat(), canvasSize.height.toFloat())
            board.effectiveHolds(selectedPresentation).asReversed().firstOrNull { hold ->
                hold.geometry.any { geometry ->
                    geometry.toBoardPath(canvasGeometry.holdBounds)
                        .transformed(canvasGeometry.faceTransform)
                        .contains(tap.x, tap.y, clipBounds)
                }
            }?.let { onHoldTap(it.id) }
        }
    }

    Canvas(
        modifier = modifier
            .fillMaxWidth()
            .aspectRatio(presentation?.aspectRatio ?: board.aspectRatio)
            .clipToBounds()
            .onSizeChanged { canvasSize = it }
            .semantics {
                contentDescription = "Board ${board.name}"
                stateDescription = "Active holds: $activeDescription"
            }
            .then(inputModifier),
    ) {
        val selectedPresentation = presentation ?: return@Canvas
        val canvasGeometry = boardCanvasGeometry(
            board,
            selectedPresentation,
            size.width,
            size.height,
        ) ?: return@Canvas
        boardImage?.let { image ->
            drawIntoCanvas { canvas ->
                val nativeCanvas = canvas.nativeCanvas
                when {
                    canvasGeometry.routedRig != null && canvasGeometry.routedCordGeometry != null -> {
                        drawRoutedBoardArtwork(
                            nativeCanvas,
                            image,
                            canvasGeometry.routedRig,
                            canvasGeometry.routedCordGeometry,
                        )
                    }
                    canvasGeometry.cordGeometry != null -> {
                        drawRiggedBoardArtwork(
                            nativeCanvas,
                            image,
                            canvasGeometry.directTwoAnchorRig!!,
                            canvasGeometry.cordGeometry,
                        )
                    }
                    else -> {
                        drawFaceBitmap(
                            nativeCanvas,
                            image,
                            canvasGeometry.holdBounds,
                            if (selectedPresentation.rotationDegrees == null) {
                                BoardInPlaneTransform.Identity
                            } else {
                                canvasGeometry.faceTransform
                            },
                        )
                    }
                }
            }
        }
        board.effectiveHolds(selectedPresentation)
            .forEach { hold ->
                val path = hold.geometry.fold(Path()) { combined, geometry ->
                    combined.addPath(
                        geometry.toBoardPath(canvasGeometry.holdBounds)
                            .transformed(canvasGeometry.faceTransform)
                            .toAndroidPath(),
                    )
                    combined
                }
                val isActive = hold.id in activeHoldIDs
                drawIntoCanvas { canvas ->
                    canvas.nativeCanvas.drawPath(
                        path,
                        Paint(Paint.ANTI_ALIAS_FLAG).apply {
                            color = if (isActive) ACTIVE_HOLD_COLOR else INACTIVE_HOLD_COLOR
                            style = if (isActive) Paint.Style.FILL_AND_STROKE else Paint.Style.STROKE
                            strokeWidth = if (isActive) 4f else 2f
                        },
                    )
                }
            }
    }
}

internal data class BoardCanvasGeometry(
    val holdBounds: BoardBounds,
    val faceTransform: BoardInPlaneTransform,
    val directTwoAnchorRig: BoardCordRig.DirectTwoAnchor? = null,
    val cordGeometry: DirectTwoAnchorCordGeometry? = null,
    val routedRig: BoardCordRig.Routed? = null,
    val routedCordGeometry: RoutedCordRigGeometry? = null,
)

private fun boardCanvasGeometry(
    board: Board,
    presentation: BoardPresentation,
    size: IntSize,
): BoardCanvasGeometry? = boardCanvasGeometry(
    board = board,
    presentation = presentation,
    width = size.width.toFloat(),
    height = size.height.toFloat(),
)

internal fun boardCanvasGeometry(
    board: Board,
    presentation: BoardPresentation,
    width: Float,
    height: Float,
): BoardCanvasGeometry? {
    if (!width.isFinite() || !height.isFinite() || width <= 0f || height <= 0f) return null
    when (val rig = board.resolvedCordRig(presentation)) {
        is BoardCordRig.DirectTwoAnchor -> {
            val geometry = resolveDirectTwoAnchorCordGeometry(rig, presentation, width, height)
                ?: return null
            return BoardCanvasGeometry(
                holdBounds = geometry.faceBounds,
                faceTransform = geometry.faceTransform,
                directTwoAnchorRig = rig,
                cordGeometry = geometry,
            )
        }
        is BoardCordRig.Routed -> {
            val geometry = resolveRoutedCordRigGeometry(rig, presentation, width, height)
                ?: return null
            return BoardCanvasGeometry(
                holdBounds = geometry.faceBounds,
                faceTransform = geometry.faceTransform,
                routedRig = rig,
                routedCordGeometry = geometry,
            )
        }
        null -> Unit
    }
    val holdBounds = boardBounds(width, height, presentation.aspectRatio)
    return BoardCanvasGeometry(
        holdBounds = holdBounds,
        faceTransform = BoardInPlaneTransform.forPresentation(presentation, holdBounds),
    )
}

internal sealed interface RoutedArtworkOperation {
    data class CordLayer(val layer: BoardRoutedCordLayer) : RoutedArtworkOperation
    data object Face : RoutedArtworkOperation
    data class RadialLipFaceRedraw(
        val lip: ResolvedRoutedCordRadialLip,
    ) : RoutedArtworkOperation
    data class FacePatchFaceRedraw(
        val patch: ResolvedRoutedCordFacePatch,
    ) : RoutedArtworkOperation
}

internal fun routedArtworkOperations(
    geometry: RoutedCordRigGeometry,
): List<RoutedArtworkOperation> = buildList {
    add(RoutedArtworkOperation.CordLayer(BoardRoutedCordLayer.BehindFace))
    add(RoutedArtworkOperation.Face)
    add(RoutedArtworkOperation.CordLayer(BoardRoutedCordLayer.AboveFace))
    geometry.radialLips.forEach { add(RoutedArtworkOperation.RadialLipFaceRedraw(it)) }
    geometry.facePatches.forEach { add(RoutedArtworkOperation.FacePatchFaceRedraw(it)) }
    add(RoutedArtworkOperation.CordLayer(BoardRoutedCordLayer.Overpass))
}

private fun drawRoutedBoardArtwork(
    canvas: android.graphics.Canvas,
    image: ImageBitmap,
    rig: BoardCordRig.Routed,
    geometry: RoutedCordRigGeometry,
) {
    routedArtworkOperations(geometry).forEach { operation ->
        when (operation) {
            is RoutedArtworkOperation.CordLayer -> drawRoutedCordLayer(
                canvas = canvas,
                rig = rig,
                geometry = geometry,
                layer = operation.layer,
            )
            RoutedArtworkOperation.Face -> drawFaceBitmap(
                canvas = canvas,
                image = image,
                bounds = geometry.faceBounds,
                transform = geometry.faceTransform,
            )
            is RoutedArtworkOperation.RadialLipFaceRedraw -> {
                val clip = eyeletForegroundCrescent(
                    center = operation.lip.center,
                    toward = operation.lip.toward,
                    radius = operation.lip.radius,
                    chordOffset = operation.lip.chordOffset,
                ) ?: return@forEach
                drawFaceBitmap(
                    canvas = canvas,
                    image = image,
                    bounds = geometry.faceBounds,
                    transform = geometry.faceTransform,
                    clip = clip,
                )
            }
            is RoutedArtworkOperation.FacePatchFaceRedraw -> drawFaceBitmap(
                canvas = canvas,
                image = image,
                bounds = geometry.faceBounds,
                transform = geometry.faceTransform,
                clip = operation.patch.path.toAndroidPath(),
            )
        }
    }
}

private fun drawRoutedCordLayer(
    canvas: android.graphics.Canvas,
    rig: BoardCordRig.Routed,
    geometry: RoutedCordRigGeometry,
    layer: BoardRoutedCordLayer,
) {
    val paths = geometry.tensionSpans(layer).map { it.path.toAndroidPath() } +
        geometry.authoredPaths(layer).map { it.path.toAndroidPath() }
    if (paths.isEmpty()) return

    val diameter = rig.style.diameter * geometry.scale
    if (!diameter.isFinite() || diameter <= 0f) return
    strokePaths(
        canvas = canvas,
        paths = paths,
        color = routedColor(rig.style.outlineColor),
        width = diameter * 1.6f,
    )
    strokePaths(
        canvas = canvas,
        paths = paths,
        color = routedColor(rig.style.baseColor),
        width = diameter,
    )
    drawRoutedBraid(
        canvas = canvas,
        paths = paths,
        geometry = geometry,
        diameter = diameter,
        colors = rig.style.braidColors.map(::routedColor),
    )
}

private fun drawRoutedBraid(
    canvas: android.graphics.Canvas,
    paths: List<Path>,
    geometry: RoutedCordRigGeometry,
    diameter: Float,
    colors: List<Int>,
) {
    if (colors.size != 2) return
    val clipPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        style = Paint.Style.STROKE
        strokeWidth = diameter * 0.84f
        strokeCap = Paint.Cap.ROUND
        strokeJoin = Paint.Join.ROUND
    }
    val braidClip = Path()
    paths.forEach { path ->
        val strokedPath = Path()
        clipPaint.getFillPath(path, strokedPath)
        braidClip.addPath(strokedPath)
    }

    val save = canvas.save()
    canvas.clipPath(braidClip)
    val spacing = max(diameter * 0.72f, 1f)
    val fiberWidth = max(diameter * 0.18f, 0.5f)
    val diagonalSpan = geometry.sceneBounds.width + geometry.sceneBounds.height
    var offset = -diagonalSpan
    var index = 0
    while (offset <= diagonalSpan * 2f) {
        val fiber = Path().apply {
            if (index % 2 == 0) {
                moveTo(geometry.sceneBounds.left + offset, geometry.sceneBounds.top + geometry.sceneBounds.height)
                lineTo(
                    geometry.sceneBounds.left + offset + geometry.sceneBounds.height,
                    geometry.sceneBounds.top,
                )
            } else {
                moveTo(geometry.sceneBounds.left + offset, geometry.sceneBounds.top)
                lineTo(
                    geometry.sceneBounds.left + offset + geometry.sceneBounds.height,
                    geometry.sceneBounds.top + geometry.sceneBounds.height,
                )
            }
        }
        strokePaths(
            canvas = canvas,
            paths = listOf(fiber),
            color = colors[index % colors.size],
            width = fiberWidth,
        )
        offset += spacing
        index += 1
    }
    canvas.restoreToCount(save)
}

private fun routedColor(hex: String): Int {
    if (hex.length != 7 || hex.firstOrNull() != '#') return android.graphics.Color.TRANSPARENT
    return hex.drop(1).toIntOrNull(16)?.let { 0xFF000000.toInt() or it }
        ?: android.graphics.Color.TRANSPARENT
}

private fun drawRiggedBoardArtwork(
    canvas: android.graphics.Canvas,
    image: ImageBitmap,
    rig: BoardCordRig.DirectTwoAnchor,
    geometry: DirectTwoAnchorCordGeometry,
) {
    drawFaceBitmap(canvas, image, geometry.faceBounds, geometry.faceTransform)

    val supportPaths = supportPaths(geometry)
    val strandPaths = geometry.strands.map { strand ->
        Path().apply {
            moveTo(strand.start.x, strand.start.y)
            lineTo(strand.end.x, strand.end.y)
        }
    }
    val mainPaths = supportPaths.dropLast(1) + strandPaths
    val knotOverpass = supportPaths.last()
    drawRope(canvas, mainPaths, geometry.scale)
    drawRope(canvas, listOf(knotOverpass), geometry.scale)

    val ridgePaths = mainPaths + knotOverpass
    val ridgeSave = canvas.save()
    canvas.translate(-2f * geometry.scale, -1f * geometry.scale)
    strokePaths(
        canvas = canvas,
        paths = ridgePaths,
        color = 0x2EC4C9CC,
        width = 2.4f * geometry.scale,
        pathEffect = DashPathEffect(
            floatArrayOf(1.5f * geometry.scale, 5.5f * geometry.scale),
            0f,
        ),
    )
    canvas.restoreToCount(ridgeSave)

    geometry.pairedAttachments.zip(geometry.strands.map { it.start }).forEach { (attachment, exit) ->
        val crescent = eyeletForegroundCrescent(
            center = attachment,
            toward = exit,
            radius = rig.eyeletRadius * geometry.scale,
            chordOffset = 7f * geometry.scale,
        ) ?: return@forEach
        drawFaceBitmap(
            canvas = canvas,
            image = image,
            bounds = geometry.faceBounds,
            transform = geometry.faceTransform,
            clip = crescent,
        )
    }
}

private fun drawFaceBitmap(
    canvas: android.graphics.Canvas,
    image: ImageBitmap,
    bounds: BoardBounds,
    transform: BoardInPlaneTransform,
    clip: Path? = null,
) {
    val save = canvas.save()
    clip?.let(canvas::clipPath)
    canvas.concat(transform.toAndroidMatrix())
    canvas.drawBitmap(
        image.asAndroidBitmap(),
        null,
        RectF(bounds.left, bounds.top, bounds.left + bounds.width, bounds.top + bounds.height),
        Paint(Paint.ANTI_ALIAS_FLAG or Paint.FILTER_BITMAP_FLAG or Paint.DITHER_FLAG),
    )
    canvas.restoreToCount(save)
}

private fun BoardInPlaneTransform.toAndroidMatrix(): Matrix = Matrix().apply {
    setValues(
        floatArrayOf(
            a, c, tx,
            b, d, ty,
            0f, 0f, 1f,
        ),
    )
}

private fun supportPaths(geometry: DirectTwoAnchorCordGeometry): List<Path> {
    fun point(x: Float, y: Float): Point = Point(
        x = geometry.pullPoint.x + x * geometry.scale,
        y = geometry.pullPoint.y + y * geometry.scale,
    )

    val bight = Path().apply {
        point(-12f, -61f).also { moveTo(it.x, it.y) }
        val firstEnd = point(-21f, -142f)
        val firstControl1 = point(-26f, -82f)
        val firstControl2 = point(-30f, -115f)
        cubicTo(
            firstControl1.x,
            firstControl1.y,
            firstControl2.x,
            firstControl2.y,
            firstEnd.x,
            firstEnd.y,
        )
        val secondEnd = point(1f, -177f)
        val secondControl1 = point(-14f, -163f)
        val secondControl2 = point(-5f, -174f)
        cubicTo(
            secondControl1.x,
            secondControl1.y,
            secondControl2.x,
            secondControl2.y,
            secondEnd.x,
            secondEnd.y,
        )
        val thirdEnd = point(24f, -136f)
        val thirdControl1 = point(9f, -171f)
        val thirdControl2 = point(18f, -157f)
        cubicTo(
            thirdControl1.x,
            thirdControl1.y,
            thirdControl2.x,
            thirdControl2.y,
            thirdEnd.x,
            thirdEnd.y,
        )
        val fourthEnd = point(12f, -61f)
        val fourthControl1 = point(31f, -109f)
        val fourthControl2 = point(26f, -81f)
        cubicTo(
            fourthControl1.x,
            fourthControl1.y,
            fourthControl2.x,
            fourthControl2.y,
            fourthEnd.x,
            fourthEnd.y,
        )
    }

    fun knotAndExit(mirror: Float): Path = Path().apply {
        point(-12f * mirror, -63f).also { moveTo(it.x, it.y) }
        val firstEnd = point(21f * mirror, -39f)
        val firstControl1 = point(1f * mirror, -52f)
        val firstControl2 = point(18f * mirror, -51f)
        cubicTo(
            firstControl1.x,
            firstControl1.y,
            firstControl2.x,
            firstControl2.y,
            firstEnd.x,
            firstEnd.y,
        )
        val secondEnd = point(5f * mirror, -18f)
        val secondControl1 = point(24f * mirror, -28f)
        val secondControl2 = point(16f * mirror, -19f)
        cubicTo(
            secondControl1.x,
            secondControl1.y,
            secondControl2.x,
            secondControl2.y,
            secondEnd.x,
            secondEnd.y,
        )
        val thirdEnd = point(-22f * mirror, 0f)
        val thirdControl1 = point(-8f * mirror, -17f)
        val thirdControl2 = point(-17f * mirror, -9f)
        cubicTo(
            thirdControl1.x,
            thirdControl1.y,
            thirdControl2.x,
            thirdControl2.y,
            thirdEnd.x,
            thirdEnd.y,
        )
    }

    val overpass = Path().apply {
        point(-18f, -35f).also { moveTo(it.x, it.y) }
        val end = point(18f, -35f)
        val control1 = point(-10f, -24f)
        val control2 = point(9f, -22f)
        cubicTo(control1.x, control1.y, control2.x, control2.y, end.x, end.y)
    }
    return listOf(bight, knotAndExit(1f), knotAndExit(-1f), overpass)
}

private fun drawRope(
    canvas: android.graphics.Canvas,
    paths: List<Path>,
    scale: Float,
) {
    val shadowSave = canvas.save()
    canvas.translate(4f * scale, 5f * scale)
    strokePaths(canvas, paths, color = 0x57000000, width = 35f * scale)
    canvas.restoreToCount(shadowSave)

    strokePaths(canvas, paths, color = 0xFF050607.toInt(), width = 31f * scale)
    strokePaths(canvas, paths, color = 0xFF151718.toInt(), width = 25f * scale)

    val lightStamp = Path().apply {
        moveTo(-4f * scale, -5f * scale)
        lineTo(4f * scale, 5f * scale)
    }
    strokePaths(
        canvas = canvas,
        paths = paths,
        color = 0x94939698.toInt(),
        width = 1.7f * scale,
        pathEffect = PathDashPathEffect(
            lightStamp,
            12f * scale,
            0f,
            PathDashPathEffect.Style.ROTATE,
        ),
    )
    val darkStamp = Path().apply {
        moveTo(-4f * scale, 5f * scale)
        lineTo(4f * scale, -5f * scale)
    }
    strokePaths(
        canvas = canvas,
        paths = paths,
        color = 0xE6030404.toInt(),
        width = 2f * scale,
        pathEffect = PathDashPathEffect(
            darkStamp,
            12f * scale,
            6f * scale,
            PathDashPathEffect.Style.ROTATE,
        ),
    )
}

private fun strokePaths(
    canvas: android.graphics.Canvas,
    paths: List<Path>,
    color: Int,
    width: Float,
    pathEffect: android.graphics.PathEffect? = null,
) {
    val paint = Paint(Paint.ANTI_ALIAS_FLAG or Paint.DITHER_FLAG).apply {
        this.color = color
        style = Paint.Style.STROKE
        strokeWidth = width
        strokeCap = Paint.Cap.ROUND
        strokeJoin = Paint.Join.ROUND
        this.pathEffect = pathEffect
    }
    paths.forEach { canvas.drawPath(it, paint) }
}

private fun eyeletForegroundCrescent(
    center: Point,
    toward: Point,
    radius: Float,
    chordOffset: Float,
): Path? {
    val deltaX = toward.x - center.x
    val deltaY = toward.y - center.y
    val length = sqrt(deltaX * deltaX + deltaY * deltaY)
    if (!length.isFinite() || length <= 0f || radius < chordOffset) return null

    val unitX = deltaX / length
    val unitY = deltaY / length
    val normalX = -unitY
    val normalY = unitX
    val halfChord = sqrt(radius * radius - chordOffset * chordOffset)
    val start = Point(
        center.x + chordOffset * unitX + halfChord * normalX,
        center.y + chordOffset * unitY + halfChord * normalY,
    )
    val end = Point(
        center.x + chordOffset * unitX - halfChord * normalX,
        center.y + chordOffset * unitY - halfChord * normalY,
    )
    val startDegrees = Math.toDegrees(
        atan2((start.y - center.y).toDouble(), (start.x - center.x).toDouble()),
    ).toFloat()
    val endDegrees = Math.toDegrees(
        atan2((end.y - center.y).toDouble(), (end.x - center.x).toDouble()),
    ).toFloat()
    val sweepDegrees = ((endDegrees - startDegrees) % 360f + 360f) % 360f
    return Path().apply {
        moveTo(start.x, start.y)
        arcTo(
            RectF(center.x - radius, center.y - radius, center.x + radius, center.y + radius),
            startDegrees,
            sweepDegrees,
            false,
        )
        close()
    }
}

private fun boardBounds(size: IntSize, aspectRatio: Float): BoardBounds =
    boardBounds(size.width.toFloat(), size.height.toFloat(), aspectRatio)

private fun boardBounds(width: Float, height: Float, aspectRatio: Float): BoardBounds {
    val availableAspectRatio = width / height
    return if (availableAspectRatio > aspectRatio) {
        val boardWidth = height * aspectRatio
        BoardBounds(left = (width - boardWidth) / 2f, top = 0f, width = boardWidth, height = height)
    } else {
        val boardHeight = width / aspectRatio
        BoardBounds(left = 0f, top = (height - boardHeight) / 2f, width = width, height = boardHeight)
    }
}

private fun loadBoardImage(context: android.content.Context, boardID: String, presentation: BoardPresentation): ImageBitmap? =
    runCatching {
        context.assets.open("Hangboards/$boardID/${presentation.assetPath}").use { stream ->
            requireNotNull(BitmapFactory.decodeStream(stream)).asImageBitmap()
        }
    }.getOrNull()

private val ACTIVE_HOLD_COLOR = 0xCCFFB300.toInt()
private val INACTIVE_HOLD_COLOR = 0xDDF7F3E8.toInt()
