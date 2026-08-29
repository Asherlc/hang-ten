package com.hangten.android.editor

data class BoardEditorServices(
    val store: BoardEditorStore,
    val tokenStore: GitHubTokenStore,
    val syncSession: GitHubSyncSession,
    val packageSync: GitHubPackageSync,
) {
    fun close() = syncSession.close()
}
