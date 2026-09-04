package com.hangten.android.board

import com.hangten.android.content.BoardCordRig
import com.hangten.android.content.BoardGeometryRotationAnchor
import com.hangten.android.content.BoardPresentation
import com.hangten.android.content.Point
import kotlin.math.min

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

        fun invertedAround(bounds: BoardBounds, anchor: BoardGeometryRotationAnchor): BoardInPlaneTransform {
            val anchorX = bounds.left + bounds.width * anchor.x
            val anchorY = bounds.top + bounds.height * anchor.y
            return BoardInPlaneTransform(-1f, 0f, 0f, -1f, 2f * anchorX, 2f * anchorY)
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
    val faceTransform = if (presentation.isInverted) {
        BoardInPlaneTransform.invertedAround(
            sceneBounds,
            presentation.geometryRotationAnchor ?: BoardGeometryRotationAnchor.Center,
        )
    } else {
        BoardInPlaneTransform.Identity
    }

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
