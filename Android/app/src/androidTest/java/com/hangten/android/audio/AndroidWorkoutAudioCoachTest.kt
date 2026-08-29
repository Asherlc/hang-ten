package com.hangten.android.audio

import androidx.datastore.preferences.core.PreferenceDataStoreFactory
import androidx.test.platform.app.InstrumentationRegistry
import kotlinx.coroutines.flow.first
import org.junit.Assert.assertEquals
import org.junit.Test

class AndroidWorkoutAudioCoachTest {
    @Test
    fun firstEnabledInstructionIsQueuedUntilTextToSpeechInitializes() {
        val factory = RecordingSpeakerFactory()
        val coach = AndroidWorkoutAudioCoach(
            context = InstrumentationRegistry.getInstrumentation().targetContext,
            dataStore = PreferenceDataStoreFactory.create {
                InstrumentationRegistry.getInstrumentation().targetContext.cacheDir.resolve("audio-coach-test.preferences_pb")
            },
            textToSpeechFactory = factory,
        )

        coach.setInstructionCoachingEnabled(true)
        coach.speakInstruction("Use open hands")
        factory.completeInitialization()

        assertEquals(listOf("Use open hands"), factory.speaker.spoken)
    }
}

internal class RecordingSpeakerFactory : TextToSpeechFactory {
    val speaker = RecordingInstructionSpeaker()
    private var onInitialized: ((InstructionSpeaker?) -> Unit)? = null

    override fun create(onInitialized: (InstructionSpeaker?) -> Unit) {
        this.onInitialized = onInitialized
    }

    fun completeInitialization() {
        onInitialized?.invoke(speaker)
    }
}

internal class RecordingInstructionSpeaker : InstructionSpeaker {
    val spoken = mutableListOf<String>()

    override fun speak(instruction: String) {
        spoken += instruction
    }

    override fun stop() = Unit
}
