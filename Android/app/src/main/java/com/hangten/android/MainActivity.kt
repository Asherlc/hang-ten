package com.hangten.android

import android.os.Bundle
import android.content.Context
import android.content.res.AssetManager
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.ui.Modifier
import androidx.datastore.preferences.preferencesDataStore
import com.hangten.android.audio.AndroidWorkoutAudioCoach
import com.hangten.android.content.AssetBoardRepository
import com.hangten.android.content.AssetPlanRepository
import com.hangten.android.content.ContentAssets
import com.hangten.android.ui.HangTenApp
import com.hangten.android.workout.SessionHistoryRepository

private val Context.androidDataStore by preferencesDataStore(name = "hang_ten")

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            MaterialTheme {
                Surface(modifier = Modifier.fillMaxSize()) {
                    val contentAssets = AndroidContentAssets(assets)
                    val boards = AssetBoardRepository(contentAssets).loadBoards().getOrDefault(emptyList())
                    val plans = AssetPlanRepository(contentAssets).loadPlans().getOrDefault(emptyList())
                    HangTenApp(
                        boards = boards,
                        plans = plans,
                        historyRepository = SessionHistoryRepository(applicationContext.androidDataStore),
                        audioCoach = AndroidWorkoutAudioCoach(applicationContext, applicationContext.androidDataStore),
                    )
                }
            }
        }
    }
}

private class AndroidContentAssets(
    private val assetManager: AssetManager,
) : ContentAssets {
    override fun list(path: String): List<String>? = assetManager.list(path)?.toList()

    override fun read(path: String): String? = runCatching {
        assetManager.open(path).bufferedReader().use { it.readText() }
    }.getOrNull()

    override fun exists(path: String): Boolean = runCatching {
        assetManager.open(path).use { }
        true
    }.getOrDefault(false)
}
