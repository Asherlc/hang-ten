package com.hangten.android.ui

import android.content.Context
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow

enum class WorkoutLaunchDecision {
    Allowed,
    RequiresPurchase,
}

interface WorkoutAccessPreferences {
    fun readFreeWorkoutsUsed(): Int
    fun writeFreeWorkoutsUsed(value: Int)
}

class SharedPreferencesWorkoutAccessPreferences(context: Context) : WorkoutAccessPreferences {
    private val preferences = context.getSharedPreferences(PREFERENCES_NAME, Context.MODE_PRIVATE)

    override fun readFreeWorkoutsUsed(): Int = preferences.getInt(FREE_WORKOUTS_USED, 0)

    override fun writeFreeWorkoutsUsed(value: Int) {
        preferences.edit().putInt(FREE_WORKOUTS_USED, value).apply()
    }

    private companion object {
        const val PREFERENCES_NAME = "hang_ten_access"
        const val FREE_WORKOUTS_USED = "free_workouts_used"
    }
}

class WorkoutAccessStore(
    private val preferences: WorkoutAccessPreferences,
) {
    private val _freeWorkoutsUsed = MutableStateFlow(preferences.readFreeWorkoutsUsed().coerceIn(0, FREE_WORKOUT_LIMIT))
    val freeWorkoutsUsed: StateFlow<Int> = _freeWorkoutsUsed.asStateFlow()

    fun launchDecision(hasLifetimeEntitlement: Boolean): WorkoutLaunchDecision = if (
        hasLifetimeEntitlement || _freeWorkoutsUsed.value < FREE_WORKOUT_LIMIT
    ) {
        WorkoutLaunchDecision.Allowed
    } else {
        WorkoutLaunchDecision.RequiresPurchase
    }

    fun recordSavedWorkout(hasLifetimeEntitlement: Boolean) {
        if (hasLifetimeEntitlement || _freeWorkoutsUsed.value >= FREE_WORKOUT_LIMIT) return
        val next = _freeWorkoutsUsed.value + 1
        preferences.writeFreeWorkoutsUsed(next)
        _freeWorkoutsUsed.value = next
    }

    private companion object {
        const val FREE_WORKOUT_LIMIT = 2
    }
}
