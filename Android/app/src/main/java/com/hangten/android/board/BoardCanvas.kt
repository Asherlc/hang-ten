package com.hangten.android.board

import android.graphics.BitmapFactory
import android.graphics.Paint
import android.graphics.Path
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
import com.hangten.android.content.BoardGeometry
import com.hangten.android.content.BoardPresentation
import com.hangten.android.content.HoldShape
import com.hangten.android.content.PathCommand
import com.hangten.android.content.Point
import kotlin.math.ceil
import kotlin.math.floor
import kotlin.math.min

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
) {
    val presentation = board.presentations.firstOrNull { it.isDefault }
    val context = LocalContext.current
    val bundledImage = remember(board.id, presentation?.assetPath) {
        presentation?.let { loadBoardImage(context, board.id, it) }
    }
    val boardImage = imageOverride ?: bundledImage
    var canvasSize by remember { mutableStateOf(IntSize.Zero) }
    val activeDescription = activeHoldIDs.joinToString(separator = ", ")
        .ifEmpty { "No active holds" }
    val inputModifier = Modifier.pointerInput(board, canvasSize) {
        detectTapGestures { tap ->
            if (canvasSize == IntSize.Zero) return@detectTapGestures
            val bounds = boardBounds(canvasSize, board.aspectRatio)
            board.holds.asReversed().firstOrNull { hold ->
                hold.presentationId == presentation?.id && hold.geometry.any { geometry ->
                    geometry.toBoardPath(bounds).contains(tap.x, tap.y, bounds)
                }
            }?.let { onHoldTap(it.id) }
        }
    }

    Canvas(
        modifier = modifier
            .fillMaxWidth()
            .aspectRatio(board.aspectRatio)
            .clipToBounds()
            .onSizeChanged { canvasSize = it }
            .semantics {
                contentDescription = "Board ${board.name}"
                stateDescription = "Active holds: $activeDescription"
            }
            .then(inputModifier),
    ) {
        val bounds = boardBounds(size.width, size.height, board.aspectRatio)
        boardImage?.let { image ->
            drawIntoCanvas { canvas ->
                canvas.nativeCanvas.drawBitmap(
                    image.asAndroidBitmap(),
                    null,
                    RectF(bounds.left, bounds.top, bounds.left + bounds.width, bounds.top + bounds.height),
                    null,
                )
            }
        }
        board.holds
            .filter { it.presentationId == presentation?.id }
            .forEach { hold ->
                val path = hold.geometry.fold(Path()) { combined, geometry ->
                    combined.addPath(geometry.toBoardPath(bounds).toAndroidPath())
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
