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
import androidx.lifecycle.viewmodel.initializer
import androidx.lifecycle.viewmodel.viewModelFactory
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
import com.hangten.android.health.HealthViewModel
import com.hangten.android.health.WorkoutHealthStore
import com.hangten.android.health.CompletedHealthWorkout
import com.hangten.android.workout.SessionHistoryRepository
import com.hangten.android.sensors.SensorConnectionController
import com.hangten.android.editor.BoardEditorListScreen
import com.hangten.android.editor.BoardEditorScreen
import com.hangten.android.editor.BoardEditorServices
import com.hangten.android.telemetry.AppTab
import com.hangten.android.telemetry.HangTenTelemetryEvent
import com.hangten.android.telemetry.NoOpTelemetry
import com.hangten.android.telemetry.PlanSource
import com.hangten.android.telemetry.TelemetryDependencies
import com.hangten.android.telemetry.WorkoutOutcome
import com.hangten.android.telemetry.boardFamilyForTelemetry
import com.hangten.android.telemetry.recordPersistenceSaveDiagnostic
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
    BoardEditor("board-editor", "Board editor"),
    Workout("workout", "Workout"),
}

private fun HangTenDestination.telemetryTab(): AppTab = when (this) {
    HangTenDestination.Train -> AppTab.Train
    HangTenDestination.Plans -> AppTab.Plans
    HangTenDestination.History -> AppTab.History
    else -> error("Only root tabs have telemetry values.")
}

private fun noOpTelemetryDependencies() = TelemetryDependencies(
    tracking = NoOpTelemetry,
    diagnostics = NoOpTelemetry,
    isNoOp = true,
)

@Composable
fun HangTenApp(
    boards: List<Board>,
    plans: List<TrainingPlan>,
    historyRepository: SessionHistoryRepository,
    audioCoach: WorkoutAudioCoach,
    healthStore: WorkoutHealthStore = UnavailableHealthStore,
    sensorController: SensorConnectionController? = null,
    boardEditorServices: BoardEditorServices? = null,
    telemetry: TelemetryDependencies = noOpTelemetryDependencies(),
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
        healthStore = healthStore,
        sensorController = sensorController,
        boardEditorServices = boardEditorServices,
        telemetry = telemetry,
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
    healthStore: WorkoutHealthStore = UnavailableHealthStore,
    sensorController: SensorConnectionController? = null,
    boardEditorServices: BoardEditorServices? = null,
    telemetry: TelemetryDependencies = noOpTelemetryDependencies(),
    modifier: Modifier = Modifier,
) {
    val navController = rememberNavController()
    val coroutineScope = rememberCoroutineScope()
    val lifecycleOwner = LocalLifecycleOwner.current
    val selections: HangTenSelectionViewModel = viewModel()
    val healthViewModel: HealthViewModel = viewModel(
        key = "health-connect",
        factory = remember(healthStore, historyRepository) {
            viewModelFactory { initializer { HealthViewModel(healthStore, historyRepository) } }
        },
    )
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
    DisposableEffect(boardEditorServices) { onDispose { boardEditorServices?.close() } }

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
                                    telemetry.tracking.track(HangTenTelemetryEvent.AppTabSelected(item.telemetryTab()))
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
                healthViewModel = healthViewModel,
                historyVersion = historyVersion,
                audioCoach = audioCoach,
                purchaseManager = purchaseManager,
                accessStore = accessStore,
                sensorController = sensorController,
                boardEditorServices = boardEditorServices,
                telemetry = telemetry,
                onBoardSelected = { board ->
                    boardFamilyForTelemetry(board.id)?.let { family ->
                        telemetry.tracking.track(HangTenTelemetryEvent.BoardSelected(family))
                    }
                    selections.selectBoard(board)
                },
                onPlanSelected = selections::selectPlan,
                onOpenSettings = { navController.navigate(HangTenDestination.Settings.route) },
                onStartWorkout = { navController.navigate(HangTenDestination.Workout.route) },
                onSessionEnded = { completed ->
                    coroutineScope.launch {
                        telemetry.tracking.track(
                            HangTenTelemetryEvent.WorkoutFinished(
                                WorkoutOutcome.Completed,
                                completed.session.elapsedDurationMs,
                            ),
                        )
                        healthViewModel.recordCompletion(completed)
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
    healthViewModel: HealthViewModel,
    historyVersion: Int,
    audioCoach: WorkoutAudioCoach,
    purchaseManager: PurchaseManager,
    accessStore: WorkoutAccessStore,
    sensorController: SensorConnectionController?,
    boardEditorServices: BoardEditorServices?,
    telemetry: TelemetryDependencies,
    onBoardSelected: (Board) -> Unit,
    onPlanSelected: (TrainingPlan) -> Unit,
    onOpenSettings: () -> Unit,
    onStartWorkout: () -> Unit,
    onSessionEnded: (CompletedHealthWorkout) -> Unit,
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
                onWorkoutAllowed = {
                    telemetry.tracking.track(HangTenTelemetryEvent.WorkoutStarted(PlanSource.Catalog))
                    onStartWorkout()
                },
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
            LaunchedEffect(Unit) {
                telemetry.tracking.track(HangTenTelemetryEvent.PlanBrowsed(PlanSource.Catalog))
            }
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
                healthViewModel = healthViewModel,
                refreshKey = historyVersion,
                contentPadding = padding,
            )
        }
        composable(HangTenDestination.Settings.route) {
            SettingsScreen(
                audioCoach = audioCoach,
                purchaseManager = purchaseManager,
                healthViewModel = healthViewModel,
                sensorController = sensorController,
                onOpenBoardEditor = boardEditorServices?.let { { navController.navigate(HangTenDestination.BoardEditor.route) } },
                onHealthAuthorizationFinished = { outcome ->
                    telemetry.tracking.track(HangTenTelemetryEvent.HealthAuthorizationFinished(outcome))
                },
                onMotherboardConnectionFinished = { outcome ->
                    telemetry.tracking.track(HangTenTelemetryEvent.MotherboardConnectionFinished(outcome))
                },
                contentPadding = padding,
            )
        }
        composable(HangTenDestination.BoardEditor.route) {
            boardEditorServices?.let { services ->
                BoardEditorListScreen(
                    boards = boards,
                    session = services.syncSession,
                    onOpenBoard = { slug -> navController.navigate("${HangTenDestination.BoardEditor.route}/$slug") },
                    contentPadding = padding,
                )
            }
        }
        composable("${HangTenDestination.BoardEditor.route}/{slug}") { entry ->
            val slug = entry.arguments?.getString("slug")
            if (slug == null || boardEditorServices == null) {
                navController.popBackStack()
            } else {
                BoardEditorScreen(
                    slug = slug,
                    store = boardEditorServices.store,
                    tokenStore = boardEditorServices.tokenStore,
                    packageSync = boardEditorServices.packageSync,
                    contentPadding = padding,
                    onCustomSave = {
                        telemetry.tracking.track(HangTenTelemetryEvent.CustomRoutineSaved)
                    },
                    onSaveFailure = telemetry::recordPersistenceSaveDiagnostic,
                )
            }
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
                    sensorController = sensorController,
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

private object UnavailableHealthStore : WorkoutHealthStore {
    override fun requestAuthorization(): Set<String> = emptySet()

    override suspend fun completeAuthorizationRequest() = com.hangten.android.health.HealthAuthorizationState.Unavailable

    override suspend fun refreshAuthorization() = com.hangten.android.health.HealthAuthorizationState.Unavailable

    override suspend fun saveCompletedWorkout(workout: CompletedHealthWorkout) = Result.failure<com.hangten.android.health.HangTenHealthWorkout>(
        IllegalStateException("Health Connect is unavailable"),
    )

    override suspend fun fetchHangTenWorkouts() = Result.failure<List<com.hangten.android.health.HangTenHealthWorkout>>(
        IllegalStateException("Health Connect is unavailable"),
    )
}
