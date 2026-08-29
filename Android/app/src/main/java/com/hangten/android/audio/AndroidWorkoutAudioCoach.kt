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

interface InstructionSpeaker {
    fun speak(instruction: String)

    fun stop()
}

fun interface TextToSpeechFactory {
    fun create(onInitialized: (InstructionSpeaker?) -> Unit)
}

class AndroidWorkoutAudioCoach(
    context: Context,
    private val dataStore: DataStore<Preferences>,
    private val scope: CoroutineScope = CoroutineScope(SupervisorJob() + Dispatchers.Main.immediate),
    private val textToSpeechFactory: TextToSpeechFactory = AndroidTextToSpeechFactory(context.applicationContext),
) : WorkoutAudioCoach {
    private val applicationContext = context.applicationContext
    private val handler = Handler(Looper.getMainLooper())
    private val scheduledCues = mutableListOf<Runnable>()
    private val players = mutableSetOf<MediaPlayer>()
    private val _instructionCoachingEnabled = MutableStateFlow(false)
    private var instructionSpeaker: InstructionSpeaker? = null
    private var initializingInstructionSpeaker = false
    private var pendingInstruction: String? = null

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
        pendingInstruction = null
        players.toList().forEach { player ->
            runCatching { player.stop() }
            runCatching { player.release() }
        }
        players.clear()
        runCatching { instructionSpeaker?.stop() }
    }

    override fun speakInstruction(instruction: String) {
        if (!_instructionCoachingEnabled.value || instruction.isBlank()) return
        instructionSpeaker?.let { speaker ->
            runCatching { speaker.speak(instruction) }
            return
        }
        pendingInstruction = instruction
        if (!initializingInstructionSpeaker) {
            initializingInstructionSpeaker = true
            textToSpeechFactory.create { speaker ->
                instructionSpeaker = speaker
                initializingInstructionSpeaker = false
                val queuedInstruction = pendingInstruction
                pendingInstruction = null
                if (_instructionCoachingEnabled.value && speaker != null && queuedInstruction != null) {
                    runCatching { speaker.speak(queuedInstruction) }
                }
            }
        }
    }

    override fun setInstructionCoachingEnabled(enabled: Boolean) {
        _instructionCoachingEnabled.value = enabled
        if (!enabled) {
            pendingInstruction = null
            runCatching { instructionSpeaker?.stop() }
        }
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

private class AndroidTextToSpeechFactory(
    private val context: Context,
) : TextToSpeechFactory {
    override fun create(onInitialized: (InstructionSpeaker?) -> Unit) {
        var textToSpeech: TextToSpeech? = null
        textToSpeech = TextToSpeech(context) { status ->
            Handler(Looper.getMainLooper()).post {
                val readySpeaker = textToSpeech?.takeIf { status == TextToSpeech.SUCCESS }?.let { speaker ->
                    speaker.language = Locale.getDefault()
                    AndroidInstructionSpeaker(speaker)
                }
                onInitialized(readySpeaker)
            }
        }
    }
}

private class AndroidInstructionSpeaker(
    private val textToSpeech: TextToSpeech,
) : InstructionSpeaker {
    override fun speak(instruction: String) {
        textToSpeech.speak(instruction, TextToSpeech.QUEUE_FLUSH, null, "hang-ten-instruction")
    }

    override fun stop() {
        textToSpeech.stop()
    }
}
