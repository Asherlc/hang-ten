package com.hangten.android.board

import com.hangten.android.content.Board
import com.hangten.android.content.PlanTarget

typealias HoldTarget = PlanTarget

fun resolveTargets(targets: List<HoldTarget>, board: Board): Set<String> = buildSet {
    targets.forEach { target -> addAll(resolveTarget(target, board)) }
}

private fun resolveTarget(target: HoldTarget, board: Board): List<String> = when {
    target.holdIds != null -> selectHoldIds(target.holdIds, board)
    target.semantic != null -> resolveSemantic(target.semantic, board)
    target.semantics != null -> target.semantics.flatMap { resolveSemantic(it, board) }
    target.kind != null -> selectKindOrFallback(target.kind, target.fingerCapacity, target.fallbackFeatures, board)
    target.feature != null -> selectFeatureOrFallback(target.feature, target.fingerCapacity, target.fallbackFeatures, board)
    else -> emptyList()
}

private fun selectHoldIds(holdIds: List<String>, board: Board): List<String> = board.holds
    .filter { it.id in holdIds }
    .map { it.id }

private fun resolveSemantic(semantic: String, board: Board): List<String> = board.semanticHolds[semantic]?.let { mapping ->
    if (mapping.holdIds.isNotEmpty()) selectHoldIds(mapping.holdIds, board)
    else board.holds.filter { it.kind == mapping.kind }.map { it.id }
}.orEmpty()

private fun selectKindOrFallback(
    kind: String,
    fingerCapacity: Int?,
    fallbackFeatures: List<String>,
    board: Board,
): List<String> = board.holds
    .filter { it.kind == kind && it.matchesFingerCapacity(fingerCapacity) }
    .map { it.id }
    .ifEmpty { selectFirstFallback(fallbackFeatures, fingerCapacity, board) }

private fun selectFeatureOrFallback(
    feature: String,
    fingerCapacity: Int?,
    fallbackFeatures: List<String>,
    board: Board,
): List<String> = board.holds
    .filter { feature in it.features && it.matchesFingerCapacity(fingerCapacity) }
    .map { it.id }
    .ifEmpty { selectFirstFallback(fallbackFeatures, fingerCapacity, board) }

private fun selectFirstFallback(
    fallbackFeatures: List<String>,
    fingerCapacity: Int?,
    board: Board,
): List<String> = fallbackFeatures.firstNotNullOfOrNull { feature ->
    board.holds
        .filter { feature in it.features && it.matchesFingerCapacity(fingerCapacity) }
        .map { it.id }
        .takeIf { it.isNotEmpty() }
}.orEmpty()

private fun com.hangten.android.content.BoardHold.matchesFingerCapacity(fingerCapacity: Int?): Boolean =
    fingerCapacity == null || this.fingerCapacity == fingerCapacity
