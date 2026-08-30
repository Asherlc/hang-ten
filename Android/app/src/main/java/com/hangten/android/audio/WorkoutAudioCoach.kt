package com.hangten.android.audio

import kotlinx.coroutines.flow.StateFlow

/**
 * Best-effort workout cues. Audio must never delay or prevent the workout clock from advancing.
 */
interface WorkoutAudioCoach {
    val instructionCoachingEnabled: StateFlow<Boolean>

    fun scheduleCountdown(startElapsedMs: Long)

    fun cancel()

    fun speakInstruction(instruction: String)

    fun setInstructionCoachingEnabled(enabled: Boolean)
}
