package com.hangten.android.ui

import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.Modifier
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.navigation.NavGraph.Companion.findStartDestination
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.currentBackStackEntryAsState
import androidx.navigation.compose.rememberNavController
import androidx.lifecycle.SavedStateHandle
import androidx.lifecycle.ViewModel
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleEventObserver
import androidx.lifecycle.compose.LocalLifecycleOwner
import androidx.lifecycle.viewmodel.compose.viewModel
import com.hangten.android.audio.WorkoutAudioCoach
import com.hangten.android.billing.AcknowledgementResult
import com.hangten.android.billing.PurchaseClient
import com.hangten.android.billing.PurchaseManager
import com.hangten.android.billing.PurchaseProduct
import com.hangten.android.billing.PurchaseResult
import com.hangten.android.billing.PurchaseUpdate
import com.hangten.android.billing.RestoreResult
import com.hangten.android.content.Board
import com.hangten.android.content.TrainingPlan
import com.hangten.android.workout.CompletedSession
import com.hangten.android.workout.SessionHistoryRepository
import kotlinx.coroutines.launch
import kotlinx.coroutines.flow.emptyFlow

private enum class HangTenDestination(
    val route: String,
    val label: String,
) {
    Train("train", "Train"),
    Plans("plans", "Plans"),
    History("history", "History"),
    Settings("settings", "Settings"),
    Workout("workout", "Workout"),
}

@Composable
fun HangTenApp(
    boards: List<Board>,
    plans: List<TrainingPlan>,
    historyRepository: SessionHistoryRepository,
    audioCoach: WorkoutAudioCoach,
    modifier: Modifier = Modifier,
) {
    val context = LocalContext.current.applicationContext
    val purchaseManager = remember { PurchaseManager(UnavailablePurchaseClient) }
    val accessStore = remember { WorkoutAccessStore(SharedPreferencesWorkoutAccessPreferences(context)) }
    HangTenApp(
        boards = boards,
        plans = plans,
        historyRepository = historyRepository,
        audioCoach = audioCoach,
        purchaseManager = purchaseManager,
        accessStore = accessStore,
        modifier = modifier,
    )
}

@Composable
fun HangTenApp(
    boards: List<Board>,
    plans: List<TrainingPlan>,
    historyRepository: SessionHistoryRepository,
    audioCoach: WorkoutAudioCoach,
    purchaseManager: PurchaseManager,
    accessStore: WorkoutAccessStore,
    modifier: Modifier = Modifier,
) {
    val navController = rememberNavController()
    val coroutineScope = rememberCoroutineScope()
    val lifecycleOwner = LocalLifecycleOwner.current
    val selections: HangTenSelectionViewModel = viewModel()
    val selectedBoardID by selections.selectedBoardID.collectAsState()
    val selectedPlanID by selections.selectedPlanID.collectAsState()
    val selectedBoard = boards.firstOrNull { it.id == selectedBoardID } ?: boards.firstOrNull()
    val selectedPlan = plans.firstOrNull { it.id == selectedPlanID }
    val hasLifetimeEntitlement by purchaseManager.hasLifetimeEntitlement.collectAsState()
    var historyVersion by remember { mutableIntStateOf(0) }
    val backStackEntry by navController.currentBackStackEntryAsState()
    val destination = backStackEntry?.destination?.route

    LaunchedEffect(purchaseManager) { purchaseManager.prepare() }
    DisposableEffect(lifecycleOwner, purchaseManager) {
        val observer = LifecycleEventObserver { _, event ->
            if (event == Lifecycle.Event.ON_RESUME) {
                coroutineScope.launch { purchaseManager.refreshCurrentPurchases() }
            }
        }
        lifecycleOwner.lifecycle.addObserver(observer)
        onDispose { lifecycleOwner.lifecycle.removeObserver(observer) }
    }
    DisposableEffect(purchaseManager) { onDispose(purchaseManager::close) }

    MaterialTheme {
        Scaffold(
            modifier = modifier.fillMaxSize(),
            bottomBar = {
                if (destination != HangTenDestination.Workout.route) {
                    NavigationBar {
                        listOf(
                            HangTenDestination.Train,
                            HangTenDestination.Plans,
                            HangTenDestination.History,
                        ).forEach { item ->
                            NavigationBarItem(
                                selected = destination == item.route,
                                onClick = {
                                    navController.navigate(item.route) {
                                        popUpTo(navController.graph.findStartDestination().id) { saveState = true }
                                        launchSingleTop = true
                                        restoreState = true
                                    }
                                },
                                modifier = Modifier.semantics { contentDescription = item.label },
                                icon = { Text("•") },
                                label = { Text(item.label) },
                            )
                        }
                    }
                }
            },
        ) { padding ->
            HangTenNavHost(
                padding = padding,
                boards = boards,
                plans = plans,
                selectedBoard = selectedBoard,
                selectedPlan = selectedPlan,
                historyRepository = historyRepository,
                historyVersion = historyVersion,
                audioCoach = audioCoach,
                purchaseManager = purchaseManager,
                accessStore = accessStore,
                onBoardSelected = selections::selectBoard,
                onPlanSelected = selections::selectPlan,
                onOpenSettings = { navController.navigate(HangTenDestination.Settings.route) },
                onStartWorkout = { navController.navigate(HangTenDestination.Workout.route) },
                onSessionEnded = { completed ->
                    coroutineScope.launch {
                        historyRepository.record(completed)
                        accessStore.recordSavedWorkout(hasLifetimeEntitlement)
                        historyVersion += 1
                        navController.popBackStack(HangTenDestination.Train.route, inclusive = false)
                    }
                },
                navController = navController,
            )
        }
    }
}

class HangTenSelectionViewModel(
    private val savedStateHandle: SavedStateHandle,
) : ViewModel() {
    val selectedBoardID = savedStateHandle.getStateFlow<String?>(SELECTED_BOARD_ID, null)
    val selectedPlanID = savedStateHandle.getStateFlow<String?>(SELECTED_PLAN_ID, null)

    fun selectBoard(board: Board) {
        savedStateHandle[SELECTED_BOARD_ID] = board.id
    }

    fun selectPlan(plan: TrainingPlan) {
        savedStateHandle[SELECTED_PLAN_ID] = plan.id
    }

    private companion object {
        const val SELECTED_BOARD_ID = "selected_board_id"
        const val SELECTED_PLAN_ID = "selected_plan_id"
    }
}

@Composable
private fun HangTenNavHost(
    padding: PaddingValues,
    boards: List<Board>,
    plans: List<TrainingPlan>,
    selectedBoard: Board?,
    selectedPlan: TrainingPlan?,
    historyRepository: SessionHistoryRepository,
    historyVersion: Int,
    audioCoach: WorkoutAudioCoach,
    purchaseManager: PurchaseManager,
    accessStore: WorkoutAccessStore,
    onBoardSelected: (Board) -> Unit,
    onPlanSelected: (TrainingPlan) -> Unit,
    onOpenSettings: () -> Unit,
    onStartWorkout: () -> Unit,
    onSessionEnded: (CompletedSession) -> Unit,
    navController: androidx.navigation.NavHostController,
) {
    NavHost(
        navController = navController,
        startDestination = HangTenDestination.Train.route,
        modifier = Modifier.fillMaxSize(),
    ) {
        composable(HangTenDestination.Train.route) {
            WorkoutAccessGate(
                accessStore = accessStore,
                purchaseManager = purchaseManager,
                onWorkoutAllowed = onStartWorkout,
            ) { requestWorkout ->
                TrainScreen(
                    board = selectedBoard,
                    plan = selectedPlan,
                    onOpenPlans = { navController.navigate(HangTenDestination.Plans.route) },
                    onOpenSettings = onOpenSettings,
                    onStartWorkout = requestWorkout,
                    contentPadding = padding,
                )
            }
        }
        composable(HangTenDestination.Plans.route) {
            PlansScreen(
                boards = boards,
                plans = plans,
                selectedBoard = selectedBoard,
                selectedPlan = selectedPlan,
                onBoardSelected = onBoardSelected,
                onPlanSelected = onPlanSelected,
                contentPadding = padding,
            )
        }
        composable(HangTenDestination.History.route) {
            HistoryScreen(
                historyRepository = historyRepository,
                refreshKey = historyVersion,
                contentPadding = padding,
            )
        }
        composable(HangTenDestination.Settings.route) {
            SettingsScreen(
                audioCoach = audioCoach,
                purchaseManager = purchaseManager,
                contentPadding = padding,
            )
        }
        composable(HangTenDestination.Workout.route) {
            val plan = selectedPlan
            val board = selectedBoard
            if (plan == null || board == null) {
                navController.popBackStack()
            } else {
                WorkoutScreen(
                    plan = plan,
                    board = board,
                    audioCoach = audioCoach,
                    onSessionEnded = onSessionEnded,
                    contentPadding = padding,
                )
            }
        }
    }
}

private object UnavailablePurchaseClient : PurchaseClient {
    override val updates = emptyFlow<PurchaseUpdate>()

    override suspend fun load(id: String): PurchaseProduct? = null

    override suspend fun purchase(activity: android.app.Activity?, id: String): PurchaseResult = PurchaseResult.Failed

    override suspend fun restore(): RestoreResult = RestoreResult.Purchases(emptyList())

    override suspend fun acknowledge(purchaseToken: String): AcknowledgementResult = AcknowledgementResult.Failed
}
