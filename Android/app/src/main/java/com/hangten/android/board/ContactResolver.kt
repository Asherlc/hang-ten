package com.hangten.android.board

import com.hangten.android.content.Board
import com.hangten.android.content.BoardHold
import com.hangten.android.content.ContactRequirement
import com.hangten.android.content.ContactSelectionPolicy
import com.hangten.android.content.GripType
import com.hangten.android.content.TrainingStep
import kotlin.math.abs

/**
 * Resolves plan contact requirements against the selected board's default
 * presentation, mirroring iOS `ContactResolver`: a `single` requirement picks
 * the matching contact nearest the board's horizontal center, and a
 * `bilateralPair` picks the outermost matching left/right pair. A requirement
 * that cannot resolve highlights nothing; contacts are never substituted.
 */
object ContactResolver {
    /**
     * Resolved contact IDs for every requirement of [step], in canonical board
     * order. Like iOS, one unresolvable requirement leaves the step unresolved.
     */
    fun resolve(step: TrainingStep, board: Board): Set<String> {
        val resolvedIds = mutableSetOf<String>()
        step.contactRequirements.forEach { requirement ->
            val contacts = resolve(requirement, step, board)
            if (contacts.isEmpty()) return emptySet()
            contacts.mapTo(resolvedIds) { it.id }
        }
        return board.holds.filter { it.id in resolvedIds }.mapTo(linkedSetOf()) { it.id }
    }

    /** The contacts satisfying [requirement], or an empty list when it cannot resolve. */
    fun resolve(requirement: ContactRequirement, step: TrainingStep, board: Board): List<BoardHold> {
        val defaultPresentationId = board.presentations.firstOrNull { it.isDefault }?.id ?: return emptyList()
        val candidates = board.holds.filter { contact ->
            contact.presentationId == defaultPresentationId &&
                matches(requirement, contact) &&
                matches(step.gripType, contact)
        }
        if (candidates.isEmpty()) return emptyList()
        return when (requirement.selection) {
            ContactSelectionPolicy.SINGLE -> singleCandidate(candidates)
            ContactSelectionPolicy.BILATERAL_PAIR ->
                if (step.handUse == "double" && step.side == "both") outermostPair(candidates) else emptyList()
        }
    }

    private fun matches(requirement: ContactRequirement, contact: BoardHold): Boolean {
        if (requirement.contactId != null && contact.id != requirement.contactId) return false
        if (requirement.kind != null && contact.kind != requirement.kind) return false
        if (requirement.shape != null && contact.shape != requirement.shape) return false
        if (requirement.depth != null && !requirement.depth.matches(contact.depth)) return false
        if (requirement.fingerCapacity != null && contact.fingerCapacity != requirement.fingerCapacity) return false
        if (requirement.handCapacity != null && contact.handCapacity != requirement.handCapacity) return false
        return true
    }

    /** Empty grip metadata means the contact does not constrain grip. */
    private fun matches(stepGripType: GripType?, contact: BoardHold): Boolean =
        stepGripType == null || contact.gripTypes.isEmpty() || stepGripType in contact.gripTypes

    private fun singleCandidate(candidates: List<BoardHold>): List<BoardHold> {
        if (candidates.size == 1) return candidates
        val framed = candidates.mapNotNull { contact -> contact.midX()?.let { contact to it } }
        if (framed.size != candidates.size) return emptyList()
        val selected = framed.minWithOrNull(
            compareBy<Pair<BoardHold, Float>> { (_, midX) -> abs(midX - HORIZONTAL_MIDPOINT) }
                .thenBy { (contact, _) -> contact.id },
        ) ?: return emptyList()
        return listOf(selected.first)
    }

    private fun outermostPair(candidates: List<BoardHold>): List<BoardHold> {
        if (candidates.size < 2) return emptyList()
        val framed = candidates.mapNotNull { contact -> contact.midX()?.let { contact to it } }
        if (framed.size != candidates.size) return emptyList()
        val byPosition = compareBy<Pair<BoardHold, Float>> { it.second }.thenBy { it.first.id }
        val (left, leftMidX) = framed.minWithOrNull(byPosition) ?: return emptyList()
        val (right, rightMidX) = framed.maxWithOrNull(byPosition) ?: return emptyList()
        val isValidPair = left.id != right.id &&
            leftMidX < HORIZONTAL_MIDPOINT &&
            rightMidX > HORIZONTAL_MIDPOINT &&
            left.kind == right.kind &&
            left.shape == right.shape &&
            left.depth == right.depth &&
            left.fingerCapacity == right.fingerCapacity &&
            left.handCapacity == right.handCapacity
        return if (isValidPair) listOf(left, right) else emptyList()
    }

    /** Horizontal center of the union of the contact's geometry frames. */
    private fun BoardHold.midX(): Float? {
        if (geometry.isEmpty()) return null
        val minX = geometry.minOf { it.frame.x }
        val maxX = geometry.maxOf { it.frame.x + it.frame.width }
        return (minX + maxX) / 2f
    }

    private const val HORIZONTAL_MIDPOINT = 0.5f
}
