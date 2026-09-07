package com.hangten.android.board

import com.hangten.android.content.Point
import kotlin.math.ceil
import kotlin.math.hypot
import kotlin.math.max

internal enum class RoutedCordFiberColor {
    Braid0,
    Braid1,
    Dark,
}

internal data class RoutedCordFiberMark(
    val color: RoutedCordFiberColor,
    val start: Point,
    val end: Point,
    val opacity: Float,
    val width: Float,
)

private data class CordPolylinePoint(
    val point: Point,
    val distance: Float,
)

private data class CordSample(
    val point: Point,
    val tangent: Point,
)

private fun distance(first: Point, second: Point): Float = hypot(second.x - first.x, second.y - first.y)

private fun quadraticPoint(start: Point, control: Point, end: Point, amount: Float): Point {
    val inverse = 1f - amount
    return Point(
        x = inverse * inverse * start.x + 2f * inverse * amount * control.x + amount * amount * end.x,
        y = inverse * inverse * start.y + 2f * inverse * amount * control.y + amount * amount * end.y,
    )
}

private fun cubicPoint(
    start: Point,
    firstControl: Point,
    secondControl: Point,
    end: Point,
    amount: Float,
): Point {
    val inverse = 1f - amount
    return Point(
        x = inverse * inverse * inverse * start.x +
            3f * inverse * inverse * amount * firstControl.x +
            3f * inverse * amount * amount * secondControl.x +
            amount * amount * amount * end.x,
        y = inverse * inverse * inverse * start.y +
            3f * inverse * inverse * amount * firstControl.y +
            3f * inverse * amount * amount * secondControl.y +
            amount * amount * amount * end.y,
    )
}

private fun pathPolylines(path: BoardPath, curveStep: Float): List<List<CordPolylinePoint>> {
    val contours = mutableListOf<List<Point>>()
    var points = mutableListOf<Point>()
    var current: Point? = null
    var subpathStart: Point? = null

    fun finishContour() {
        if (points.isNotEmpty()) contours += points
        points = mutableListOf()
    }

    path.commands.forEach { command ->
        when (command) {
            is BoardPathCommand.MoveTo -> {
                finishContour()
                Point(command.x, command.y).also { point ->
                    current = point
                    subpathStart = point
                    points += point
                }
            }
            is BoardPathCommand.LineTo -> {
                if (current != null) {
                    Point(command.x, command.y).also { point ->
                        points += point
                        current = point
                    }
                }
            }
            is BoardPathCommand.QuadTo -> {
                val start = current ?: return@forEach
                val control = Point(command.controlX, command.controlY)
                val end = Point(command.x, command.y)
                val estimatedLength = distance(start, control) + distance(control, end)
                val steps = max(2, ceil(estimatedLength / curveStep).toInt())
                for (index in 1..steps) points += quadraticPoint(start, control, end, index.toFloat() / steps)
                current = end
            }
            is BoardPathCommand.CubicTo -> {
                val start = current ?: return@forEach
                val firstControl = Point(command.control1X, command.control1Y)
                val secondControl = Point(command.control2X, command.control2Y)
                val end = Point(command.x, command.y)
                val estimatedLength = distance(start, firstControl) +
                    distance(firstControl, secondControl) + distance(secondControl, end)
                val steps = max(3, ceil(estimatedLength / curveStep).toInt())
                for (index in 1..steps) {
                    points += cubicPoint(start, firstControl, secondControl, end, index.toFloat() / steps)
                }
                current = end
            }
            BoardPathCommand.Close -> {
                val start = subpathStart
                val end = current
                if (start != null && end != null && distance(end, start) > 0f) points += start
                current = start
            }
        }
    }
    finishContour()

    return contours.map { contour ->
        var traveled = 0f
        contour.mapIndexed { index, point ->
            if (index > 0) traveled += distance(contour[index - 1], point)
            CordPolylinePoint(point, traveled)
        }
    }
}

private fun pointAndTangentAt(
    polyline: List<CordPolylinePoint>,
    targetDistance: Float,
): CordSample? {
    for (index in 1 until polyline.size) {
        val start = polyline[index - 1]
        val end = polyline[index]
        if (end.distance < targetDistance) continue
        val segmentLength = end.distance - start.distance
        if (segmentLength <= 0f) continue
        val amount = ((targetDistance - start.distance) / segmentLength).coerceIn(0f, 1f)
        return CordSample(
            point = Point(
                start.point.x + (end.point.x - start.point.x) * amount,
                start.point.y + (end.point.y - start.point.y) * amount,
            ),
            tangent = Point(
                (end.point.x - start.point.x) / segmentLength,
                (end.point.y - start.point.y) / segmentLength,
            ),
        )
    }
    return null
}

private fun fiberMark(
    sample: CordSample,
    diameter: Float,
    color: RoutedCordFiberColor,
): RoutedCordFiberMark {
    val normal = Point(-sample.tangent.y, sample.tangent.x)
    val light = color == RoutedCordFiberColor.Braid1
    val dark = color == RoutedCordFiberColor.Dark
    val alongStart = if (dark) -0.15f else if (light) -0.17f else -0.19f
    val alongEnd = if (dark || light) 0.17f else 0.19f
    val acrossStart = if (dark) -0.25f else if (light) 0.31f else -0.34f
    val acrossEnd = if (dark) 0.13f else if (light) -0.28f else 0.29f
    fun translated(along: Float, across: Float) = Point(
        x = sample.point.x + diameter * (sample.tangent.x * along + normal.x * across),
        y = sample.point.y + diameter * (sample.tangent.y * along + normal.y * across),
    )
    return RoutedCordFiberMark(
        color = color,
        start = translated(alongStart, acrossStart),
        end = translated(alongEnd, acrossEnd),
        opacity = if (dark) 0.36f else if (light) 0.46f else 0.58f,
        width = diameter * if (dark) 0.026f else if (light) 0.045f else 0.055f,
    )
}

internal fun routedCordFiberMarks(path: BoardPath, diameter: Float): List<RoutedCordFiberMark> {
    if (!diameter.isFinite() || diameter <= 0f) return emptyList()
    val spacing = diameter * 0.46f
    return pathPolylines(path, max(diameter * 0.22f, 0.25f)).flatMap { polyline ->
        val pathLength = polyline.lastOrNull()?.distance ?: 0f
        if (!pathLength.isFinite() || pathLength <= diameter) return@flatMap emptyList()
        buildList {
            var distanceAlong = diameter * 0.34f
            while (distanceAlong < pathLength - diameter * 0.24f) {
                pointAndTangentAt(polyline, distanceAlong)?.let {
                    add(fiberMark(it, diameter, RoutedCordFiberColor.Braid0))
                }
                val lightDistance = distanceAlong + spacing * 0.52f
                if (lightDistance < pathLength - diameter * 0.3f) {
                    pointAndTangentAt(polyline, lightDistance)?.let {
                        add(fiberMark(it, diameter, RoutedCordFiberColor.Braid1))
                    }
                }
                val darkDistance = distanceAlong + spacing * 0.26f
                if (darkDistance < pathLength - diameter * 0.3f) {
                    pointAndTangentAt(polyline, darkDistance)?.let {
                        add(fiberMark(it, diameter, RoutedCordFiberColor.Dark))
                    }
                }
                distanceAlong += spacing
            }
        }
    }
}
