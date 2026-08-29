package com.hangten.android.editor

import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

data class GitHubSyncUiState(
    val username: String? = null,
    val challenge: DeviceChallenge? = null,
    val signingIn: Boolean = false,
    val error: String? = null,
)

class GitHubSyncSession(
    private val deviceFlow: GitHubDeviceFlow,
    private val tokenStore: GitHubTokenStore,
    private val clientId: String,
    // The concrete GitHub API is blocking (OkHttp's execute), so keep polling off the UI
    // thread. StateFlow remains safe to observe from Compose on the main thread.
    private val scope: CoroutineScope = CoroutineScope(SupervisorJob() + Dispatchers.IO),
) {
    private val mutableState = MutableStateFlow(GitHubSyncUiState())
    val state: StateFlow<GitHubSyncUiState> = mutableState.asStateFlow()
    private var activeSignIn: Job? = null

    fun startSignIn() {
        activeSignIn?.cancel()
        mutableState.value = GitHubSyncUiState(signingIn = true)
        activeSignIn = scope.launch {
            when (val outcome = deviceFlow.authorize(clientId) { challenge ->
                mutableState.value = mutableState.value.copy(challenge = challenge)
            }) {
                is DeviceFlowOutcome.Authorized -> mutableState.value = GitHubSyncUiState(username = outcome.username)
                DeviceFlowOutcome.Cancelled -> mutableState.value = GitHubSyncUiState()
                DeviceFlowOutcome.Denied -> mutableState.value = GitHubSyncUiState(error = "GitHub authorization was denied.")
                DeviceFlowOutcome.Expired -> mutableState.value = GitHubSyncUiState(error = "GitHub authorization expired. Please try again.")
                is DeviceFlowOutcome.Failed -> mutableState.value = GitHubSyncUiState(error = outcome.message)
            }
        }
    }

    fun cancelSignIn() {
        activeSignIn?.cancel()
        activeSignIn = null
        mutableState.value = GitHubSyncUiState()
    }

    fun signOut() {
        cancelSignIn()
        tokenStore.clear()
    }

    fun close() {
        activeSignIn?.cancel()
        scope.cancel()
    }
}
