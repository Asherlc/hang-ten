package com.hangten.android.board

import com.hangten.android.content.Board
import com.hangten.android.content.BoardHold
import com.hangten.android.content.PlanTarget

typealias HoldTarget = PlanTarget

fun resolveTargets(targets: List<HoldTarget>, board: Board): Set<String> = board.holds
    .filter { hold -> targets.any { target -> target.matches(hold) } }
    .mapTo(linkedSetOf()) { it.id }

internal fun HoldTarget.matches(hold: BoardHold): Boolean = when {
    holdIds != null -> hold.id in holdIds
    kind != null -> hold.kind == kind
    else -> false
}
