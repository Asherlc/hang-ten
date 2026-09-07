package com.hangten.android.board

import com.hangten.android.content.BoardCordRig
import com.hangten.android.content.BoardGeometryRotationAnchor
import com.hangten.android.content.BoardPresentation
import com.hangten.android.content.BoardRoutedCordLayer
import com.hangten.android.content.BoardRoutedCordSpace
import com.hangten.android.content.Point
import kotlin.math.PI
import kotlin.math.abs
import kotlin.math.atan2
import kotlin.math.cos
import kotlin.math.hypot
import kotlin.math.max
import kotlin.math.min
import kotlin.math.sin

private data class LoopPoint(val x: Double, val y: Double)

private data class SlidingLoopShape(
    val center: LoopPoint,
    val pull: LoopPoint,
    val coreHalfWidth: Double,
    val coreHalfHeight: Double,
    val radius: Double,
    val cosine: Double,
    val sine: Double,
) {
    val extentX = abs(cosine) * coreHalfWidth + abs(sine) * coreHalfHeight + radius
    val extentY = abs(sine) * coreHalfWidth + abs(cosine) * coreHalfHeight + radius

    fun mapLocal(x: Double, y: Double) = LoopPoint(
        center.x + cosine * x - sine * y,
        center.y + sine * x + cosine * y,
    )

    fun boundary(): List<LoopPoint> {
        val corners = listOf(
            Triple(coreHalfWidth, -coreHalfHeight, -PI / 2),
            Triple(coreHalfWidth, coreHalfHeight, 0.0),
            Triple(-coreHalfWidth, coreHalfHeight, PI / 2),
            Triple(-coreHalfWidth, -coreHalfHeight, PI),
        )
        val result = mutableListOf<LoopPoint>()
        corners.forEach { (x, y, start) ->
            for (step in 0..24) {
                val angle = start + step * PI / 48
                val point = mapLocal(x + radius * cos(angle), y + radius * sin(angle))
                val previous = result.lastOrNull()
                if (previous == null || hypot(point.x - previous.x, point.y - previous.y) > 1e-9) {
                    result += point
                }
            }
        }
        if (result.size > 1 && hypot(result.first().x - result.last().x, result.first().y - result.last().y) <= 1e-9) {
            result.removeAt(result.lastIndex)
        }
        return result
    }
}

private fun slidingLoopShape(
    rig: BoardCordRig.ExternalSlidingLoop,
    presentation: BoardPresentation,
): SlidingLoopShape? {
    val frame = rig.bodyContactFrame
    val scale = presentation.resolvedGeometryScale.toDouble()
    val anchor = presentation.geometryRotationAnchor ?: BoardGeometryRotationAnchor.Center
    val values = listOf(
        rig.sceneSize.width, rig.sceneSize.height, rig.sourceFrame.x, rig.sourceFrame.y,
        rig.sourceFrame.width, rig.sourceFrame.height, rig.innerFaceFrame.x, rig.innerFaceFrame.y,
        rig.innerFaceFrame.width, rig.innerFaceFrame.height, frame.x, frame.y, frame.width, frame.height,
        rig.cornerRadius, rig.clearance, rig.style.diameter, rig.pullPoint.x, rig.pullPoint.y,
        presentation.resolvedRotationDegrees, presentation.resolvedGeometryScale, anchor.x, anchor.y,
    )
    if (!values.all { it.isFinite() } || scale <= 0 ||
        rig.sceneSize.width <= 0 || rig.sceneSize.height <= 0 ||
        rig.sourceFrame.width <= 0 || rig.sourceFrame.height <= 0 ||
        rig.innerFaceFrame.width <= 0 || rig.innerFaceFrame.height <= 0 ||
        frame.width <= 0 || frame.height <= 0 || rig.style.diameter <= 0 ||
        rig.clearance < 0 || rig.cornerRadius < 0 ||
        rig.cornerRadius > min(frame.width, frame.height) / 2
    ) return null
    val (cosine, sine) = when (presentation.resolvedRotationDegrees) {
        0f -> 1.0 to 0.0
        90f -> 0.0 to 1.0
        180f -> -1.0 to 0.0
        270f -> 0.0 to -1.0
        else -> Math.toRadians(presentation.resolvedRotationDegrees.toDouble()).let { cos(it) to sin(it) }
    }
    val anchorX = anchor.x.toDouble() * rig.sceneSize.width
    val anchorY = anchor.y.toDouble() * rig.sceneSize.height
    val deltaX = (rig.sourceFrame.x.toDouble() + frame.x + frame.width / 2.0 - anchorX) * scale
    val deltaY = (rig.sourceFrame.y.toDouble() + frame.y + frame.height / 2.0 - anchorY) * scale
    // Only physical body dimensions scale. The cord's centerline clearance remains scene-sized.
    val offset = rig.style.diameter / 2.0 + rig.clearance
    return SlidingLoopShape(
        center = LoopPoint(anchorX + cosine * deltaX - sine * deltaY, anchorY + sine * deltaX + cosine * deltaY),
        pull = LoopPoint(rig.sourceFrame.x.toDouble() + rig.pullPoint.x, rig.sourceFrame.y.toDouble() + rig.pullPoint.y),
        coreHalfWidth = (frame.width / 2.0 - rig.cornerRadius) * scale,
        coreHalfHeight = (frame.height / 2.0 - rig.cornerRadius) * scale,
        radius = rig.cornerRadius * scale + offset,
        cosine = cosine,
        sine = sine,
    ).takeIf { shape ->
        listOf(shape.center.x, shape.center.y, shape.pull.x, shape.pull.y, shape.extentX, shape.extentY, shape.radius)
            .all { it.isFinite() }
    }
}

internal fun externalSlidingLoopPresentationValidationFailure(
    rig: BoardCordRig.ExternalSlidingLoop,
    presentation: BoardPresentation,
): String? {
    val shape = slidingLoopShape(rig, presentation) ?: return "geometry must be finite and valid"
    return slidingLoopValidationFailure(rig, shape)
}

private fun slidingLoopValidationFailure(rig: BoardCordRig.ExternalSlidingLoop, shape: SlidingLoopShape): String? {
    val tolerance = max(rig.sceneSize.width, rig.sceneSize.height) * 1e-9
    val margin = 0.8 * rig.style.diameter
    fun inside(x: Double, y: Double): Boolean =
        x >= margin - tolerance && y >= margin - tolerance &&
            x <= rig.sceneSize.width - margin + tolerance && y <= rig.sceneSize.height - margin + tolerance
    if (!inside(shape.pull.x, shape.pull.y) ||
        !inside(shape.center.x - shape.extentX, shape.center.y - shape.extentY) ||
        !inside(shape.center.x + shape.extentX, shape.center.y + shape.extentY)
    ) return "cord centerline geometry must remain inside sceneSize with the style margin"
    val deltaX = shape.pull.x - shape.center.x
    val deltaY = shape.pull.y - shape.center.y
    val localX = shape.cosine * deltaX + shape.sine * deltaY
    val localY = -shape.sine * deltaX + shape.cosine * deltaY
    if (hypot(max(0.0, abs(localX) - shape.coreHalfWidth), max(0.0, abs(localY) - shape.coreHalfHeight)) <= shape.radius + tolerance) {
        return "pullPoint must remain outside the expanded body contact shape"
    }
    if (shape.pull.y >= shape.center.y - shape.extentY - tolerance) {
        return "pullPoint must remain above the body contact shape"
    }
    return null
}

internal fun resolveExternalSlidingLoopCordGeometry(
    rig: BoardCordRig.ExternalSlidingLoop,
    presentation: BoardPresentation,
    canvasWidth: Float,
    canvasHeight: Float,
): RoutedCordRigGeometry? {
    if (!canvasWidth.isFinite() || !canvasHeight.isFinite() || canvasWidth <= 0f || canvasHeight <= 0f) return null
    val shape = slidingLoopShape(rig, presentation) ?: return null
    if (slidingLoopValidationFailure(rig, shape) != null) return null
    val boundary = shape.boundary()
    if (boundary.size < 4) return null
    val direction = atan2(shape.center.y - shape.pull.y, shape.center.x - shape.pull.x)
    val angularOffsets = boundary.map { point ->
        val difference = atan2(point.y - shape.pull.y, point.x - shape.pull.x) - direction + PI
        ((difference % (2 * PI) + 2 * PI) % (2 * PI)) - PI
    }
    val first = angularOffsets.indices.minBy { angularOffsets[it] }
    val second = angularOffsets.indices.maxBy { angularOffsets[it] }
    if (first == second || angularOffsets[second] - angularOffsets[first] >= PI) return null
    val tangents = listOf(first, second).sortedWith(compareBy<Int> { boundary[it].x }.thenBy { boundary[it].y })
    fun arc(step: Int): List<LoopPoint> = buildList {
        var index = tangents[0]
        add(boundary[index])
        while (index != tangents[1]) {
            index = (index + step + boundary.size) % boundary.size
            add(boundary[index])
        }
    }
    val forward = arc(1)
    val backward = arc(-1)
    val forwardBottom = forward.maxOf { it.y }
    val backwardBottom = backward.maxOf { it.y }
    val returnArc = if (forwardBottom > backwardBottom ||
        (forwardBottom == backwardBottom && forward.map { it.y }.average() >= backward.map { it.y }.average())
    ) forward else backward

    val scale = min(canvasWidth / rig.sceneSize.width, canvasHeight / rig.sceneSize.height)
    if (!scale.isFinite() || scale <= 0f) return null
    val sceneBounds = BoardBounds(
        (canvasWidth - rig.sceneSize.width * scale) / 2f,
        (canvasHeight - rig.sceneSize.height * scale) / 2f,
        rig.sceneSize.width * scale,
        rig.sceneSize.height * scale,
    )
    val sourceBounds = BoardBounds(
        sceneBounds.left + rig.sourceFrame.x * scale, sceneBounds.top + rig.sourceFrame.y * scale,
        rig.sourceFrame.width * scale, rig.sourceFrame.height * scale,
    )
    val faceBounds = BoardBounds(
        sourceBounds.left + rig.innerFaceFrame.x * scale, sourceBounds.top + rig.innerFaceFrame.y * scale,
        rig.innerFaceFrame.width * scale, rig.innerFaceFrame.height * scale,
    )
    fun project(point: LoopPoint) = Point(
        (sceneBounds.left + point.x * scale).toFloat(), (sceneBounds.top + point.y * scale).toFloat(),
    )
    val pullPoint = project(shape.pull)
    val contactPoints = tangents.map { project(boundary[it]) }
    val returnPoints = returnArc.map(::project)
    val spans = contactPoints.mapIndexed { index, point ->
        RoutedCordTensionSpan(
            groupId = "external-loop-tension", layer = BoardRoutedCordLayer.BehindFace,
            bodyPortId = "external-loop-contact-$index", worldPortId = "external-loop-pull",
            bodyPoint = point, worldPoint = pullPoint,
        )
    }
    val returnPath = BoardPath(returnPoints.mapIndexed { index, point ->
        if (index == 0) BoardPathCommand.MoveTo(point.x, point.y) else BoardPathCommand.LineTo(point.x, point.y)
    })
    return RoutedCordRigGeometry(
        sceneBounds = sceneBounds, sourceBounds = sourceBounds, faceBounds = faceBounds,
        faceTransform = BoardInPlaneTransform.forPresentation(presentation, sceneBounds), scale = scale,
        portPoints = spans.associate { it.bodyPortId to it.bodyPoint } + ("external-loop-pull" to pullPoint),
        spans = spans,
        paths = listOf(ResolvedRoutedCordPath(
            id = "external-loop-return", space = BoardRoutedCordSpace.World,
            layer = BoardRoutedCordLayer.BehindFace, path = returnPath, definingPoints = returnPoints,
        )),
        radialLips = emptyList(), facePatches = emptyList(),
    )
}
