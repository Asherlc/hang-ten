package com.hangten.android.health

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.hangten.android.workout.CompletedSession
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

interface WorkoutHistory {
    suspend fun record(completedSession: CompletedSession)
    suspend fun completedSessions(): List<CompletedSession>
}

enum class HealthHistorySource { HealthConnect, LocalFallback, Unavailable }

data class HealthUiState(
    val authorization: HealthAuthorizationState = HealthAuthorizationState.NotDetermined,
    val historySource: HealthHistorySource = HealthHistorySource.Unavailable,
    val sessions: List<CompletedSession> = emptyList(),
    val error: String? = null,
) {
    val isLocalFallbackOnly: Boolean
        get() = historySource == HealthHistorySource.LocalFallback
}

class HealthViewModel(
    private val healthStore: WorkoutHealthStore,
    private val history: WorkoutHistory,
) : ViewModel() {
    private val _state = MutableStateFlow(HealthUiState())
    val state: StateFlow<HealthUiState> = _state.asStateFlow()

    /** Called only by the visible Connect Health action. It never launches a request itself. */
    fun requestAuthorization(): Set<String> = healthStore.requestAuthorization()

    fun authorizationRequestFinished() {
        viewModelScope.launch {
            val authorization = healthStore.completeAuthorizationRequest()
            _state.value = _state.value.copy(authorization = authorization, error = null)
            refreshHistoryNow()
        }
    }

    fun refreshHistory() {
        viewModelScope.launch { refreshHistoryNow() }
    }

    /** Synchronous-to-call-coroutine reconciliation seam used by deterministic store fakes. */
    suspend fun reconcileHistory() {
        refreshHistoryNow()
    }

    suspend fun recordCompletion(workout: CompletedHealthWorkout) {
        // Local persistence is first and intentionally survives every Health Connect outcome.
        history.record(workout.session)
        val authorization = healthStore.refreshAuthorization()
        _state.value = _state.value.copy(authorization = authorization, error = null)
        if (authorization == HealthAuthorizationState.Authorized) {
            healthStore.saveCompletedWorkout(workout).exceptionOrNull()?.let { error ->
                _state.value = _state.value.copy(error = error.message ?: "Unable to save this session to Health Connect")
            }
        }
        refreshHistoryNow()
    }

    private suspend fun refreshHistoryNow() {
        val local = history.completedSessions().sortedByDescending { it.completedAtWallClockMs }
        val authorization = healthStore.refreshAuthorization()
        if (authorization != HealthAuthorizationState.Authorized) {
            _state.value = _state.value.copy(
                authorization = authorization,
                historySource = if (local.isEmpty()) HealthHistorySource.Unavailable else HealthHistorySource.LocalFallback,
                sessions = local,
            )
            return
        }

        val health = healthStore.fetchHangTenWorkouts()
        val healthWorkouts = health.getOrElse { error ->
            _state.value = _state.value.copy(error = error.message ?: "Unable to read Health Connect history")
            emptyList()
        }
        val localClientIDs = local.map(::stableClientRecordId).toSet()
        val remoteOnly = healthWorkouts.filterNot { it.clientRecordId in localClientIDs }.map(::completedSession)
        _state.value = _state.value.copy(
            authorization = authorization,
            historySource = if (healthWorkouts.isNotEmpty()) HealthHistorySource.HealthConnect else if (local.isNotEmpty()) HealthHistorySource.LocalFallback else HealthHistorySource.HealthConnect,
            sessions = (local + remoteOnly).sortedByDescending { it.completedAtWallClockMs },
        )
    }

    private fun completedSession(workout: HangTenHealthWorkout): CompletedSession = CompletedSession(
        planId = workout.planId,
        completedAtWallClockMs = workout.endTime.toEpochMilli(),
        elapsedDurationMs = (workout.endTime.toEpochMilli() - workout.startTime.toEpochMilli()).coerceAtLeast(0L),
        boardId = workout.boardId,
        planTitle = workout.planTitle,
    )
}
