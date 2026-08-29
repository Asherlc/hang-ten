package com.hangten.android.workout

import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringPreferencesKey
import java.util.Base64
import kotlinx.coroutines.flow.first

class SessionHistoryRepository(
    private val dataStore: DataStore<Preferences>,
) : com.hangten.android.health.WorkoutHistory {
    override suspend fun record(completedSession: CompletedSession) {
        dataStore.edit { preferences ->
            val sessions = decode(preferences[HISTORY_KEY]).toMutableList()
            sessions += completedSession
            preferences[HISTORY_KEY] = encode(
                sessions.sortedByDescending { it.completedAtWallClockMs }.take(MAX_HISTORY_ENTRIES),
            )
        }
    }

    override suspend fun completedSessions(): List<CompletedSession> = decode(dataStore.data.first()[HISTORY_KEY])

    private fun encode(sessions: List<CompletedSession>): String = sessions.joinToString("\n") { session ->
        listOf(
            planIdEncoder.encodeToString(session.planId.toByteArray(Charsets.UTF_8)),
            session.completedAtWallClockMs.toString(),
            session.elapsedDurationMs.toString(),
            planIdEncoder.encodeToString(session.boardId.orEmpty().toByteArray(Charsets.UTF_8)),
            planIdEncoder.encodeToString(session.planTitle.orEmpty().toByteArray(Charsets.UTF_8)),
        ).joinToString(",")
    }

    private fun decode(serialized: String?): List<CompletedSession> = serialized.orEmpty().lineSequence()
        .mapNotNull(::decodeSession)
        .sortedByDescending { it.completedAtWallClockMs }
        .take(MAX_HISTORY_ENTRIES)
        .toList()

    private fun decodeSession(encoded: String): CompletedSession? = runCatching {
        val fields = encoded.split(',')
        require(fields.size == 3 || fields.size == 5)
        CompletedSession(
            planId = String(planIdDecoder.decode(fields[0]), Charsets.UTF_8),
            completedAtWallClockMs = fields[1].toLong(),
            elapsedDurationMs = fields[2].toLong().also(::requireNonNegative),
            boardId = fields.getOrNull(3)?.let { String(planIdDecoder.decode(it), Charsets.UTF_8).ifBlank { null } },
            planTitle = fields.getOrNull(4)?.let { String(planIdDecoder.decode(it), Charsets.UTF_8).ifBlank { null } },
        )
    }.getOrNull()

    private fun requireNonNegative(value: Long): Long = value.also { require(it >= 0L) }

    private companion object {
        val HISTORY_KEY = stringPreferencesKey("completed_session_history")
        val planIdEncoder: Base64.Encoder = Base64.getUrlEncoder().withoutPadding()
        val planIdDecoder: Base64.Decoder = Base64.getUrlDecoder()
        const val MAX_HISTORY_ENTRIES = 20
    }
}
