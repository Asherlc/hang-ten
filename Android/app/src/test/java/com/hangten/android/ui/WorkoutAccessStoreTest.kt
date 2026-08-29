package com.hangten.android.ui

import org.junit.Assert.assertEquals
import org.junit.Test

class WorkoutAccessStoreTest {
    @Test
    fun thirdSavedWorkoutRequiresLifetimeAccessWhileEntitledWorkoutsDoNotSpendCredits() {
        val store = WorkoutAccessStore(InMemoryWorkoutAccessPreferences())

        store.recordSavedWorkout(hasLifetimeEntitlement = false)
        store.recordSavedWorkout(hasLifetimeEntitlement = false)

        assertEquals(WorkoutLaunchDecision.RequiresPurchase, store.launchDecision(hasLifetimeEntitlement = false))
        store.recordSavedWorkout(hasLifetimeEntitlement = true)

        assertEquals(2, store.freeWorkoutsUsed.value)
        assertEquals(WorkoutLaunchDecision.Allowed, store.launchDecision(hasLifetimeEntitlement = true))
    }

    private class InMemoryWorkoutAccessPreferences : WorkoutAccessPreferences {
        private var value = 0

        override fun readFreeWorkoutsUsed(): Int = value

        override fun writeFreeWorkoutsUsed(value: Int) {
            this.value = value
        }
    }
}
