package com.hangten.android.workout

import android.os.SystemClock
import androidx.lifecycle.ViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow

fun interface WorkoutAudioCancellation {
    fun cancel()
}

class WorkoutViewModel(
    private val session: WorkoutSession,
    private val elapsedRealtime: () -> Long = SystemClock::elapsedRealtime,
    private val audioCancellation: WorkoutAudioCancellation = WorkoutAudioCancellation {},
) : ViewModel() {
    private val _snapshot = MutableStateFlow(session.snapshot(elapsedRealtime()))

    val snapshot: StateFlow<WorkoutSnapshot> = _snapshot.asStateFlow()

    fun start(): WorkoutSnapshot = publish { session.start(elapsedRealtime()) }

    fun pause(): WorkoutSnapshot = publish { session.pause(elapsedRealtime()) }

    fun resume(): WorkoutSnapshot = publish { session.resume(elapsedRealtime()) }

    fun complete(): CompletedSession {
        val completed = session.complete(elapsedRealtime())
        _snapshot.value = session.snapshot(elapsedRealtime())
        return completed
    }

    fun onStop() {
        if (session.isRunning(elapsedRealtime())) {
            pause()
        }
        audioCancellation.cancel()
    }

    private fun publish(block: () -> WorkoutSnapshot): WorkoutSnapshot = block().also { _snapshot.value = it }
}
