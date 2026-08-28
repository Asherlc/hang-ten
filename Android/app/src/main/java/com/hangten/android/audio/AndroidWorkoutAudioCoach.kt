package com.hangten.android.audio

import android.content.Context
import android.media.MediaPlayer
import android.os.Handler
import android.os.Looper
import android.os.SystemClock
import android.speech.tts.TextToSpeech
import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.booleanPreferencesKey
import androidx.datastore.preferences.core.edit
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.catch
import kotlinx.coroutines.flow.collect
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.launch
import java.util.Locale

class AndroidWorkoutAudioCoach(
    context: Context,
    private val dataStore: DataStore<Preferences>,
    private val scope: CoroutineScope = CoroutineScope(SupervisorJob() + Dispatchers.Main.immediate),
) : WorkoutAudioCoach {
    private val applicationContext = context.applicationContext
    private val handler = Handler(Looper.getMainLooper())
    private val scheduledCues = mutableListOf<Runnable>()
    private val players = mutableSetOf<MediaPlayer>()
    private val _instructionCoachingEnabled = MutableStateFlow(false)
    private var textToSpeech: TextToSpeech? = null
    private var textToSpeechReady = false

    override val instructionCoachingEnabled: StateFlow<Boolean> = _instructionCoachingEnabled.asStateFlow()

    init {
        scope.launch {
            dataStore.data
                .map { preferences -> preferences[INSTRUCTION_COACHING_ENABLED] ?: false }
                .catch { emit(false) }
                .collect { enabled -> _instructionCoachingEnabled.value = enabled }
        }
    }

    override fun scheduleCountdown(startElapsedMs: Long) {
        cancelCountdownCues()
        COUNTDOWN_ASSETS.forEachIndexed { index, assetName ->
            val cue = Runnable { playCountdownAsset(assetName) }
            scheduledCues += cue
            val dueAtMs = startElapsedMs + index * COUNTDOWN_INTERVAL_MS
            handler.postDelayed(cue, (dueAtMs - SystemClock.elapsedRealtime()).coerceAtLeast(0L))
        }
    }

    override fun cancel() {
        cancelCountdownCues()
        players.toList().forEach { player ->
            runCatching { player.stop() }
            runCatching { player.release() }
        }
        players.clear()
        runCatching { textToSpeech?.stop() }
    }

    override fun speakInstruction(instruction: String) {
        if (!_instructionCoachingEnabled.value || instruction.isBlank()) return
        val speaker = textToSpeech ?: TextToSpeech(applicationContext) { status ->
            textToSpeechReady = status == TextToSpeech.SUCCESS
            if (textToSpeechReady) textToSpeech?.language = Locale.getDefault()
        }.also { textToSpeech = it }
        if (textToSpeechReady) {
            runCatching { speaker.speak(instruction, TextToSpeech.QUEUE_FLUSH, null, "hang-ten-instruction") }
        }
    }

    override fun setInstructionCoachingEnabled(enabled: Boolean) {
        _instructionCoachingEnabled.value = enabled
        scope.launch {
            runCatching {
                dataStore.edit { preferences -> preferences[INSTRUCTION_COACHING_ENABLED] = enabled }
            }
        }
    }

    private fun cancelCountdownCues() {
        scheduledCues.forEach(handler::removeCallbacks)
        scheduledCues.clear()
    }

    private fun playCountdownAsset(assetName: String) {
        runCatching {
            val descriptor = applicationContext.assets.openFd("CountdownAudio/$assetName")
            MediaPlayer().apply {
                players += this
                setDataSource(descriptor.fileDescriptor, descriptor.startOffset, descriptor.length)
                descriptor.close()
                setOnCompletionListener { player ->
                    players -= player
                    player.release()
                }
                setOnErrorListener { player, _, _ ->
                    players -= player
                    player.release()
                    true
                }
                prepareAsync()
                setOnPreparedListener { it.start() }
            }
        }
    }

    private companion object {
        val INSTRUCTION_COACHING_ENABLED = booleanPreferencesKey("instruction_coaching_enabled")
        val COUNTDOWN_ASSETS = listOf("countdown-3.mp3", "countdown-2.mp3", "countdown-1.mp3")
        const val COUNTDOWN_INTERVAL_MS = 1_000L
    }
}
