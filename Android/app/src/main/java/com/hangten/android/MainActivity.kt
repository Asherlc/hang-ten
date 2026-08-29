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
import com.hangten.android.billing.PlayBillingClient
import com.hangten.android.billing.PurchaseManager
import com.hangten.android.content.AssetBoardRepository
import com.hangten.android.content.AssetPlanRepository
import com.hangten.android.content.ContentAssets
import com.hangten.android.ui.HangTenApp
import com.hangten.android.ui.SharedPreferencesWorkoutAccessPreferences
import com.hangten.android.ui.WorkoutAccessStore
import androidx.compose.runtime.remember
import com.hangten.android.workout.SessionHistoryRepository
import com.hangten.android.health.AndroidHealthConnectGateway
import com.hangten.android.health.HealthConnectService
import com.hangten.android.health.SharedPreferencesHealthAuthorizationMemory
import com.hangten.android.sensors.AndroidBleForceSensorTransport
import com.hangten.android.sensors.SensorConnectionController

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
                    val purchaseManager = remember { PurchaseManager(PlayBillingClient(applicationContext)) }
                    val accessStore = remember {
                        WorkoutAccessStore(SharedPreferencesWorkoutAccessPreferences(applicationContext))
                    }
                    val healthStore = remember {
                        HealthConnectService(
                            gateway = AndroidHealthConnectGateway(applicationContext),
                            authorizationMemory = SharedPreferencesHealthAuthorizationMemory(applicationContext),
                        )
                    }
                    val sensorController = remember {
                        SensorConnectionController(AndroidBleForceSensorTransport(applicationContext))
                    }
                    HangTenApp(
                        boards = boards,
                        plans = plans,
                        historyRepository = SessionHistoryRepository(applicationContext.androidDataStore),
                        audioCoach = AndroidWorkoutAudioCoach(applicationContext, applicationContext.androidDataStore),
                        purchaseManager = purchaseManager,
                        accessStore = accessStore,
                        healthStore = healthStore,
                        sensorController = sensorController,
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
