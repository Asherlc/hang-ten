import SwiftUI
import UIKit

struct WorkoutView: View {
    private enum PendingCountdownStart: Equatable {
        case initial
        case skip(targetElapsed: TimeInterval)

        var kind: WorkoutCountdownKind {
            switch self {
            case .initial: .initial
            case .skip: .skip
            }
        }
    }

    private struct RendererPreparationContent: Equatable {
        let presentationID: String
        let contactIDs: Set<String>
        let taskIndex: Int
        let selectedSide: WorkoutSide?
        let pose: GripHandPose
        let viewport: CGSize
        let isLandscape: Bool
    }

    private enum LandscapeLayout {
        static let sideCueSlotWidth: CGFloat = 142
        static let boardMaxHeight: CGFloat = 132
        static let normalCueRowHeight: CGFloat = 149
        static let previewLabelHeight: CGFloat = 13
    }

    @EnvironmentObject private var store: AppStore
	@EnvironmentObject private var motherboardBluetoothService: MotherboardBluetoothService
	@EnvironmentObject private var motherboardSettingsStore: MotherboardSettingsStore
	@EnvironmentObject private var audioCoach: WorkoutAudioCoach
	@Environment(\.dismiss) private var dismiss
	@Environment(\.scenePhase) private var scenePhase
    @Environment(\.dynamicTypeSize) private var dynamicTypeSize
    @AppStorage("workoutAudioCuesEnabled") private var audioCuesEnabled = true

    let plan: TrainingPlan
    let initialWeight: WorkoutInitialWeightConfiguration

    init(
        plan: TrainingPlan,
        initialWeight: WorkoutInitialWeightConfiguration = .untracked
    ) {
        self.plan = plan
        self.initialWeight = initialWeight
    }

    @State private var sessionState = WorkoutSessionState()
    @State private var didAutoStart = false
    @State private var showEndConfirmation = false
    @State private var showsStepPicker = false
    @State private var showsReportProblem = false
    @State private var didComplete = false
    @State private var didApplyReviewStep = false
	    @State private var recorder = MotherboardWorkoutRecorder()
	@State private var completedSession: WorkoutSessionRecord?
	@State private var summarySession: WorkoutSessionRecord?
    @State private var didSaveSession = false
    @State private var didInterruptRecorder = false
	@State private var showsWorkoutPreparation = false
	@State private var didCompleteWorkoutPreparation = false
	    @State private var workoutPreparationHandoff = MotherboardWorkoutPreparationHandoff()
	    @State private var bodyweightKGF: Double?
	    @State private var motherboardMeasurementCollector = MotherboardWorkoutMeasurementCollector()
	    @State private var stopwatches: [WorkoutActivitySegmentKey: WorkoutStopwatch] = [:]
	    @State private var completedStopwatchDurations: [WorkoutActivitySegmentKey: TimeInterval] = [:]
	    @State private var liftCompletion = WorkoutLiftCompletion()
	    @State private var pendingCountdownStart: PendingCountdownStart?
	    @State private var countdownArmTask: Task<Void, Never>?
        @State private var rendererStartGate = WorkoutRendererStartGate()
	    @State private var handPreference: WorkoutSessionHandPreference?
	    /// Preference-expanded steps; source of truth for timeline once set.
	    @State private var sessionSteps: [WorkoutStep]?
	    @State private var taskCursor = WorkoutTaskCursor()
	    @State private var bothHandsResolvable = true

    private var board: BoardRevision {
        store.board(for: plan)
    }

    private var boardIsOneHanded: Bool {
        board.isOneHanded
    }

    private var planNeedsHandChoice: Bool {
        WorkoutSessionHandResolver.needsHandChoice(plan: plan, board: board)
    }

	/// Session-expanded steps when a preference is chosen; otherwise authored plan steps.
	private var activeSteps: [WorkoutStep] {
		sessionSteps ?? plan.steps
	}

	private var sessionDuration: TimeInterval {
		activeSteps.reduce(0) { $0 + $1.duration }
	}

	private var timeline: WorkoutTimeline {
		WorkoutTimeline(steps: activeSteps)
	}

    var body: some View {
		GeometryReader { geometry in
			TimelineView(.periodic(from: .now, by: 0.25)) { context in
				let monotonicTime = WorkoutClock.monotonicTime
				let elapsed = currentElapsed(at: monotonicTime)
				let step = step(at: elapsed)
				// Session steps are already preference-materialized / alternate-expanded.
				let presentedStep = step
				let stepElapsed = elapsedInStep(at: elapsed)
				let countdown = countdownRemaining(at: monotonicTime)
				let canNavigate = canNavigate(at: monotonicTime)
				let isComplete = elapsed >= sessionDuration
				let isTimedResting = isRestInterval(step: step, stepElapsed: stepElapsed)
				let boardCue = timeline.boardCue(
					currentStep: step,
					stepElapsed: stepElapsed,
					countdown: countdown,
					isComplete: isComplete
				)
				let isResting = boardCue.isResting
				let highlightedStep = boardCue.step
				let resolvedHighlightedStep = highlightedStep
				let highlightedTaskIndex = resolvedHighlightedStep.map {
					$0.id == step.id ? taskCursor.index(for: $0) : 0
				} ?? 0
				let highlightedSelectedHandSide = resolvedHighlightedStep.flatMap {
					$0.id == step.id ? taskCursor.selectedSide(for: $0) : nil
				}
				let previewHoldIDs = resolvedHighlightedStep.map {
					WorkoutHighlightResolver.contactIDs(
						for: $0, on: board,
						taskIndex: highlightedTaskIndex,
						selectedHandSide: highlightedSelectedHandSide
					)
				} ?? []
				let highlightedHoldIDs = boardCue.isSuppressed ? [] : Set(previewHoldIDs)
				let highlightMode = boardCue.mode
				let showsHoldPreview = highlightMode == .preview && !highlightedHoldIDs.isEmpty
				let activeHold = resolvedHighlightedStep.flatMap {
					WorkoutHighlightResolver.contacts(for: $0, on: board,
						taskIndex: highlightedTaskIndex,
						selectedHandSide: highlightedSelectedHandSide).first {
							highlightedHoldIDs.contains($0.id)
						}
				}
				let holdCue = WorkoutHoldCuePolicy.resolve(
					step: resolvedHighlightedStep,
					hold: activeHold,
					on: board,
					taskIndex: highlightedTaskIndex,
					selectedHandSide: highlightedSelectedHandSide
				)
                let preparationSelection = BoardMapPresentationSelection(
                    board: board,
                    requestedPresentationID: WorkoutHighlightResolver.presentationID(
                        for: resolvedHighlightedStep, on: board,
                        taskIndex: highlightedTaskIndex,
                        selectedHandSide: highlightedSelectedHandSide),
                    activeHoldID: holdCue?.hold?.id,
                    highlightedHoldIDs: highlightedHoldIDs)
				let isLandscape = geometry.size.width > geometry.size.height && !dynamicTypeSize.isAccessibilitySize
                let requiresPreparedHands = holdCue != nil && (
                    (!isLandscape && holdCue?.hold != nil)
                    || WorkoutHoldCueVisibilityPolicy.showsCue(
                        for: .left, step: resolvedHighlightedStep,
                        taskIndex: highlightedTaskIndex,
                        selectedHandSide: highlightedSelectedHandSide)
                    || WorkoutHoldCueVisibilityPolicy.showsCue(
                        for: .right, step: resolvedHighlightedStep,
                        taskIndex: highlightedTaskIndex,
                        selectedHandSide: highlightedSelectedHandSide))
                let preparationContent = RendererPreparationContent(
                    presentationID: preparationSelection.presentationID,
                    contactIDs: highlightedHoldIDs,
                    taskIndex: highlightedTaskIndex,
                    selectedSide: highlightedSelectedHandSide,
                    pose: GripHandPose(posture: holdCue?.gripType,
                                      fingerConfiguration: holdCue?.fingerConfiguration),
                    viewport: geometry.size,
                    isLandscape: isLandscape)
				let audioMoment = audioMoment(
					step: step,
					stepElapsed: stepElapsed,
					elapsed: elapsed,
					countdown: countdown,
					isTimedResting: isTimedResting,
					isComplete: isComplete
				)
				let audioCountdownStartUptime = audioCountdownStartUptime(
					step: step,
					elapsed: elapsed,
					countdown: countdown,
					isTimedResting: isTimedResting,
					moment: audioMoment
				)

				Group {
					if isLandscape {
						landscapeSession(
							step: presentedStep,
							stepElapsed: stepElapsed,
							elapsed: elapsed,
							monotonicTime: monotonicTime,
							countdown: countdown,
							canNavigate: canNavigate,
							isResting: isResting,
							isComplete: isComplete,
							highlightedHoldIDs: highlightedHoldIDs,
							highlightMode: highlightMode,
							showsHoldPreview: showsHoldPreview,
							holdCue: holdCue,
							cueStep: resolvedHighlightedStep,
							highlightedTaskIndex: highlightedTaskIndex,
							highlightedSelectedHandSide: highlightedSelectedHandSide,
							isSkipCountdown: sessionState.countdownKind == .skip
						)
					} else {
						portraitSession(
							step: presentedStep,
							stepElapsed: stepElapsed,
							elapsed: elapsed,
							monotonicTime: monotonicTime,
							countdown: countdown,
							canNavigate: canNavigate,
							isResting: isResting,
							isComplete: isComplete,
							highlightedHoldIDs: highlightedHoldIDs,
							highlightMode: highlightMode,
							showsHoldPreview: showsHoldPreview,
							holdCue: holdCue,
							cueStep: resolvedHighlightedStep,
							highlightedTaskIndex: highlightedTaskIndex,
							highlightedSelectedHandSide: highlightedSelectedHandSide,
							isSkipCountdown: sessionState.countdownKind == .skip
						)
					}
				}
				.frame(maxWidth: .infinity, maxHeight: .infinity)
				.background(Color.hangBackground)
                .environment(\.workoutRendererPreparationID, rendererStartGate.requestID)
                .onPreferenceChange(WorkoutRendererReadinessKey.self) { readiness in
                    guard scenePhase == .active,
                          rendererStartGate.consume(readiness, requiresBoard: true,
                                                    requiresHands: requiresPreparedHands) else { return }
                    requestCountdownStart(.initial)
                }
                .onChange(of: preparationContent) { _, _ in
                    guard sessionState.routineStartedAt == nil,
                          rendererStartGate.requestID != nil else { return }
                    cancelPendingCountdownArm()
                    audioCoach.stop()
                    requestCountdownStart(.initial)
                }
				.onChange(of: isComplete) { _, routineComplete in
					guard routineComplete else { return }
					finalizeRoutine()
				}
				.onChange(of: step.id) { _, _ in
					recorder.pause(at: elapsed)
				}
				.onChange(of: isResting) { _, resting in
					guard resting else { return }
					recorder.pause(at: elapsed)
				}
				.onChange(of: audioMoment, initial: true) { previousMoment, moment in
					guard audioCuesEnabled else {
						audioCoach.stop()
						return
					}

				_ = WorkoutAudioCueRouter.route(
					WorkoutAudioCuePolicy.action(
						previous: previousMoment,
						current: moment,
						countdownStartUptime: audioCountdownStartUptime
					),
					to: audioCoach
				)
				}
				.onChange(of: countdown, initial: true) { _, countdown in
					guard countdown == 0 else { return }
					sessionState.transitionExpiredCountdown(at: monotonicTime)
				}
				.onChange(of: isComplete, initial: true) { _, complete in
					guard complete else { return }
					finalizeAllStopwatches(at: monotonicTime)
				}
				.onChange(of: step.id) { previousStepID, _ in
					finalizeStopwatches(for: previousStepID, at: monotonicTime)
				}
				.onChange(of: isResting) { wasResting, resting in
					guard resting, !wasResting else { return }
					finalizeCurrentStopwatch(at: monotonicTime)
				}
				.sheet(isPresented: $showsStepPicker) {
					WorkoutStepPickerView(
						steps: activeSteps,
						currentStepID: step.id
					) { selectedStep in
						jump(to: selectedStep)
					}
				}
			}
		}
        .navigationTitle("Session")
        .navigationBarTitleDisplayMode(.inline)
		.toolbar(.hidden, for: .tabBar)
        .toolbar {
			ToolbarItemGroup(placement: .topBarTrailing) {
				Button {
					audioCuesEnabled.toggle()
					if !audioCuesEnabled {
						audioCoach.stop()
					}
				} label: {
					Image(systemName: audioCuesEnabled ? "speaker.wave.2.fill" : "speaker.slash.fill")
				}
				.accessibilityLabel(audioCuesEnabled ? "Turn off spoken cues" : "Turn on spoken cues")

				Button {
					showsReportProblem = true
				} label: {
					Image(systemName: "exclamationmark.bubble")
				}
				.accessibilityLabel("Report a problem")
				.accessibilityIdentifier("workout.reportProblem")

				Button("End") {
					showEndConfirmation = true
				}
				.font(.system(.footnote, design: .rounded, weight: .bold))
				.foregroundStyle(Color.hangGreenDark)
			}
        }
        .sheet(isPresented: $showsReportProblem) {
            ReportProblemView(
                source: .workout,
                boardID: board.id,
                planID: plan.id,
                stepID: step(at: currentElapsed(at: WorkoutClock.monotonicTime)).id
            )
            .environmentObject(store)
        }
        .confirmationDialog("End this session?", isPresented: $showEndConfirmation, titleVisibility: .visible) {
            Button("End session", role: .destructive) {
                endSession()
            }
            Button("Keep training", role: .cancel) {}
        } message: {
            Text("This will stop the timer without logging a workout to Apple Health.")
        }
		.sheet(item: $summarySession) { session in
			WorkoutSummaryView(
				session: session,
				unit: motherboardSettingsStore.forceUnit,
				loadAdjustmentUnit: motherboardSettingsStore.loadAdjustmentUnit,
				onSave: { save(session) },
				onDiscard: { discard(session) }
			)
		}
		.sheet(isPresented: $showsWorkoutPreparation) {
			MotherboardWorkoutPreparationView(
				service: motherboardBluetoothService,
				unit: motherboardSettingsStore.forceUnit,
				bodyweightCaptureDuration: motherboardSettingsStore.bodyweightCaptureDuration,
				onComplete: { baseline in
					guard workoutPreparationHandoff.accept() else { return }
					bodyweightKGF = baseline
					didCompleteWorkoutPreparation = true
					showsWorkoutPreparation = false
					toggleRunning()
				},
				onSkip: {
					guard workoutPreparationHandoff.accept() else { return }
					bodyweightKGF = nil
					didCompleteWorkoutPreparation = true
					showsWorkoutPreparation = false
					toggleRunning()
				}
			)
		}
		.onAppear {
			UIApplication.shared.isIdleTimerDisabled = true
			configureRecorder()
			if planNeedsHandChoice {
				bothHandsResolvable = WorkoutSessionHandResolver.bothHandsResolve(plan: plan, board: board)
				if handPreference == nil {
					applyHandPreference(
						WorkoutSessionHandResolver.defaultPreference(plan: plan, board: board)
					)
				}
			}
			#if DEBUG
			if !didApplyReviewStep {
				didApplyReviewStep = true
				if let rawStep = ProcessInfo.processInfo.environment["HANGTEN_REVIEW_STEP"],
				   let requestedStep = Int(rawStep),
				   requestedStep > 1 {
						sessionState.pausedElapsed = activeSteps
							.prefix(min(requestedStep - 1, activeSteps.count))
							.reduce(0) { $0 + $1.duration }
				}
			}

				if ProcessInfo.processInfo.environment["HANGTEN_REVIEW_AUTOSTART"] == "1",
				   sessionState.activeStartUptime == nil {
					didCompleteWorkoutPreparation = true
					toggleRunning()
				}
			#endif
			if !planNeedsHandChoice,
			   WorkoutSessionPolicy.shouldAutoStart(
				didAutoStart: didAutoStart,
				isRunning: sessionState.activeStartUptime != nil,
				routineStartedAt: sessionState.routineStartedAt
			) {
				didAutoStart = true
				toggleRunning()
			}
			initializeStopwatches()
		}
		.onChange(of: scenePhase) { _, phase in
			guard phase != .active else { return }
			pauseForInterruption()
		}
		.onChange(of: audioCoach.countdownPreparationState) { _, state in
			guard let pendingCountdownStart else { return }
			switch WorkoutSessionPolicy.consumePendingCountdown(
				&self.pendingCountdownStart,
				afterPreparationState: state
			) {
			case .none:
				return
			case .beginVisibly:
				beginVisibleCountdown(pendingCountdownStart, at: WorkoutClock.monotonicTime)
			case .requestAudioCountdown:
				requestCountdownStart(pendingCountdownStart)
			}
		}
		.onReceive(motherboardBluetoothService.$latestMeasurement.compactMap { $0 }) { measurement in
			let monotonicTime = WorkoutClock.monotonicTime
			guard sessionState.activeStartUptime != nil, isScaleTrackingReady else { return }
			consume(measurement, at: monotonicTime)
			capture(measurement, at: monotonicTime)
		}
		.onChange(of: motherboardBluetoothService.state) { previousState, state in
			guard isScaleTrackingReady,
			      previousState == .streaming,
			      state != .streaming else { return }
			interruptRecorderForSensorLoss()
		}
        .onDisappear {
            rendererStartGate.cancel()
			countdownArmTask?.cancel()
			countdownArmTask = nil
			pendingCountdownStart = nil
			interruptRecorderIfNeeded()
			finalizeAllStopwatches(at: WorkoutClock.monotonicTime)
			UIApplication.shared.isIdleTimerDisabled = false
			audioCoach.stop()
		}
    }

	private func portraitSession(
		step: WorkoutStep,
		stepElapsed: TimeInterval,
		elapsed: TimeInterval,
		monotonicTime: TimeInterval,
		countdown: Int,
		canNavigate: Bool,
		isResting: Bool,
		isComplete: Bool,
		highlightedHoldIDs: Set<String>,
		highlightMode: BoardHighlightMode,
		showsHoldPreview: Bool,
		holdCue: WorkoutHoldCue?,
		cueStep: WorkoutStep?,
		highlightedTaskIndex: Int,
		highlightedSelectedHandSide: WorkoutSide?,
		isSkipCountdown: Bool
	) -> some View {
		ScrollView(showsIndicators: false) {
			VStack(alignment: .leading, spacing: 19) {
				sessionHeader(
					step: step,
					stepElapsed: stepElapsed,
					elapsed: elapsed,
					countdown: countdown,
					canNavigate: canNavigate,
					isResting: isResting,
					isComplete: isComplete
				)
				controlGroup(step: step, isResting: isResting, isComplete: isComplete, countdown: countdown, monotonicTime: monotonicTime, canNavigate: canNavigate)
				if showsHoldPreview {
					SectionLabel(title: "Next hold preview", tint: WorkoutPhase.rest.textTint)
				}
				BoardMapView(
					board: board,
					highlightedHoldIDs: highlightedHoldIDs,
					highlightMode: highlightMode,
					selectedPresentationID: WorkoutHighlightResolver.presentationID(
                            for: cueStep, on: board, taskIndex: highlightedTaskIndex,
                            selectedHandSide: highlightedSelectedHandSide),
                        activeHoldID: holdCue?.hold?.id
				)
					.padding(.horizontal, 2)
				taskControls(for: step, cueStep: cueStep, countdown: countdown, isResting: isResting)
				if let holdCue, WorkoutHoldCueVisibilityPolicy.showsCue(
					holdCue: holdCue,
					countdown: mountedCueCountdown(countdown),
					isComplete: isComplete,
					isSkipCountdown: isSkipCountdown
				) {
                    Group {
					if let hold = holdCue.hold {
						GripDiagramView(
							hold: hold,
							gripType: holdCue.gripType,
							fingerConfiguration: holdCue.fingerConfiguration,
							resolvedHandSide: resolvedHandSide(for: cueStep ?? step)
						)
					} else {
						portraitHandCueCards(
							holdCue: holdCue,
							cueStep: cueStep,
							taskIndex: highlightedTaskIndex,
							selectedHandSide: highlightedSelectedHandSide
						)
					}
                    }
                    .opacity(isInitialCountdown && countdown > 0 ? 0 : 1)
                    .allowsHitTesting(!(isInitialCountdown && countdown > 0))
                    .accessibilityHidden(isInitialCountdown && countdown > 0)
				}
				if let cueCardRows = WorkoutPresentationContent.cueCardRows(
					step: step,
					countdown: countdown,
					isComplete: isComplete
				) {
					cueCard(
						rows: cueCardRows,
						step: step,
						countdown: countdown,
						isResting: isResting
					)
				}
				if isScaleTrackingReady, motherboardBluetoothService.state.showsWorkoutMeter {
					meter(step: step)
				}
			}
			.padding(.horizontal, 20)
			.padding(.top, 16)
			.padding(.bottom, 34)
		}
	}

	@ViewBuilder
	private func taskControls(
		for step: WorkoutStep,
		cueStep: WorkoutStep?,
		countdown: Int,
		isResting: Bool
	) -> some View {
		if let cueStep {
			let taskCount = taskCursor.count(for: cueStep)
			let taskIndex = cueStep.id == step.id ? taskCursor.index(for: cueStep) : 0
			let tasks = cueStep.segments.lazy.compactMap { $0.target?.planTasks }.first
			if WorkoutTaskPresentationPolicy.requiresTwoBoards(
				for: cueStep, on: board, taskIndex: taskIndex
			) {
				Text("Use two boards, one hand on each.")
					.font(.system(.footnote, design: .rounded, weight: .medium))
					.foregroundStyle(Color.hangInk)
			}
			if cueStep.id == step.id, !isResting, countdown == 0,
			   let tasks, tasks.indices.contains(taskIndex),
			   tasks[taskIndex].count == 1, tasks[taskIndex][0].side == nil {
				HStack(spacing: 10) {
					Text("Choose a hand")
						.font(.system(.footnote, design: .rounded, weight: .semibold))
					ForEach([WorkoutSide.left, .right], id: \.self) { side in
						Button(side == .left ? "Left" : "Right") {
							taskCursor.choose(side, in: step)
						}
						.accessibilityIdentifier("workout.taskHand.\(side.rawValue)")
							.buttonStyle(.bordered)
							.tint(taskCursor.selectedSide(for: step) == side ? Color.hangGreenDark : Color.hangMuted)
					}
				}
			}
			if cueStep.id == step.id, !isResting, countdown == 0, taskCount > 1 {
				HStack(spacing: 12) {
					Button("Previous hold") { taskCursor.retreat(in: step) }
						.disabled(taskIndex == 0)
						.accessibilityIdentifier("workout.previousHold")
					Spacer(minLength: 4)
					Text("Hold \(taskIndex + 1) of \(taskCount)")
						.font(.system(.footnote, design: .rounded, weight: .semibold))
					Spacer(minLength: 4)
					Button("Next hold") { taskCursor.advance(in: step) }
						.disabled(taskIndex + 1 == taskCount)
						.accessibilityIdentifier("workout.nextHold")
				}
				.buttonStyle(.bordered)
			}
		}
	}

    private var isInitialCountdown: Bool { sessionState.countdownKind == .initial }

    private func mountedCueCountdown(_ countdown: Int) -> Int {
        isInitialCountdown ? 0 : countdown
    }


	@ViewBuilder
	private func portraitHandCueCards(
		holdCue: WorkoutHoldCue,
		cueStep: WorkoutStep?,
		taskIndex: Int,
		selectedHandSide: WorkoutSide?
	) -> some View {
		let showsLeft = WorkoutHoldCueVisibilityPolicy.showsCue(
			for: .left, step: cueStep, taskIndex: taskIndex, selectedHandSide: selectedHandSide
		)
		let showsRight = WorkoutHoldCueVisibilityPolicy.showsCue(
			for: .right, step: cueStep, taskIndex: taskIndex, selectedHandSide: selectedHandSide
		)
		if showsLeft && showsRight {
			GripHandPairCueCards(posture: holdCue.gripType,
								fingerConfiguration: holdCue.fingerConfiguration)
		} else {
			HStack(spacing: 12) {
				if showsLeft {
					GripHandCueCard(posture: holdCue.gripType,
									fingerConfiguration: holdCue.fingerConfiguration, side: .left)
				}
				if showsRight {
					GripHandCueCard(posture: holdCue.gripType,
									fingerConfiguration: holdCue.fingerConfiguration, side: .right)
				}
			}
		}
	}

	private func landscapeSession(
		step: WorkoutStep,
		stepElapsed: TimeInterval,
		elapsed: TimeInterval,
		monotonicTime: TimeInterval,
		countdown: Int,
		canNavigate: Bool,
		isResting: Bool,
		isComplete: Bool,
		highlightedHoldIDs: Set<String>,
		highlightMode: BoardHighlightMode,
		showsHoldPreview: Bool,
		holdCue: WorkoutHoldCue?,
		cueStep: WorkoutStep?,
		highlightedTaskIndex: Int,
		highlightedSelectedHandSide: WorkoutSide?,
		isSkipCountdown: Bool
	) -> some View {
		let showsPairedHandCue: Bool = {
			guard let holdCue else { return false }
			return WorkoutLandscapeHandCuePolicy.showsHandCue(
				for: .left, holdCue: holdCue, cueStep: cueStep, countdown: mountedCueCountdown(countdown),
				isComplete: isComplete, isSkipCountdown: isSkipCountdown,
				taskIndex: highlightedTaskIndex,
				selectedHandSide: highlightedSelectedHandSide
			) && WorkoutLandscapeHandCuePolicy.showsHandCue(
				for: .right, holdCue: holdCue, cueStep: cueStep, countdown: mountedCueCountdown(countdown),
				isComplete: isComplete, isSkipCountdown: isSkipCountdown,
				taskIndex: highlightedTaskIndex,
				selectedHandSide: highlightedSelectedHandSide
			)
		}()
		return ScrollView(showsIndicators: false) {
			VStack(spacing: 9) {
				landscapeHeader(
					step: step,
					stepElapsed: stepElapsed,
					countdown: countdown,
					canNavigate: canNavigate,
					isResting: isResting,
					isComplete: isComplete
				)

				ProgressView(value: min(elapsed, sessionDuration), total: sessionDuration)
					.tint(Color.hangGreenDark)

				VStack(spacing: 2) {
					if showsPairedHandCue, let holdCue {
						GripHandPairModelView(posture: holdCue.gripType,
											 fingerConfiguration: holdCue.fingerConfiguration)
							.frame(height: 68)
                            .opacity(isInitialCountdown && countdown > 0 ? 0 : 1)
                            .allowsHitTesting(!(isInitialCountdown && countdown > 0))
                    .accessibilityHidden(isInitialCountdown && countdown > 0)
							.accessibilityHidden(true)
					}
					HStack(spacing: 12) {
					landscapeHandCueSlot(
						holdCue: holdCue,
						cueStep: cueStep,
						countdown: countdown,
						isComplete: isComplete,
						isSkipCountdown: isSkipCountdown,
						taskIndex: highlightedTaskIndex,
						selectedHandSide: highlightedSelectedHandSide,
						side: .left,
						usesSharedPairPreview: showsPairedHandCue
					)

					VStack(alignment: .leading, spacing: 4) {
						SectionLabel(title: "Next hold preview", tint: WorkoutPhase.rest.textTint)
							.frame(maxWidth: .infinity, minHeight: LandscapeLayout.previewLabelHeight, alignment: .center)
							.opacity(showsHoldPreview ? 1 : 0)
							.accessibilityHidden(!showsHoldPreview)
						BoardMapView(
							board: board,
							highlightedHoldIDs: highlightedHoldIDs,
							highlightMode: highlightMode,
							selectedPresentationID: WorkoutHighlightResolver.presentationID(
                            for: cueStep, on: board, taskIndex: highlightedTaskIndex,
                            selectedHandSide: highlightedSelectedHandSide),
                        activeHoldID: holdCue?.hold?.id
						)
							.frame(maxWidth: .infinity)
							.frame(maxHeight: LandscapeLayout.boardMaxHeight)
						taskControls(for: step, cueStep: cueStep, countdown: countdown, isResting: isResting)
					}
					.frame(maxWidth: .infinity)

					landscapeHandCueSlot(
						holdCue: holdCue,
						cueStep: cueStep,
						countdown: countdown,
						isComplete: isComplete,
						isSkipCountdown: isSkipCountdown,
						taskIndex: highlightedTaskIndex,
						selectedHandSide: highlightedSelectedHandSide,
						side: .right,
						usesSharedPairPreview: showsPairedHandCue
					)
					}
				}
				.frame(maxHeight: LandscapeLayout.normalCueRowHeight)

				if WorkoutLandscapeControlLayoutPolicy.usesCompactControls(
					isFirstStart: WorkoutSessionPolicy.isFirstStart(routineStartedAt: sessionState.routineStartedAt),
					countdown: countdown,
					isComplete: isComplete
				) {
					landscapePreStartControls(
						step: step,
						isResting: isResting,
						isComplete: isComplete,
						countdown: countdown,
						monotonicTime: monotonicTime,
						canNavigate: canNavigate,
						currentStopwatchKey: currentStopwatchKey(for: step)
					)
				} else {
					HStack(alignment: .center, spacing: 12) {
						if let cueCardRows = WorkoutPresentationContent.cueCardRows(
							step: step,
							countdown: countdown,
							isComplete: isComplete
						) {
							cueCard(
								rows: cueCardRows,
								step: step,
								countdown: countdown,
								isResting: isResting,
								compact: true
							)
						}
						controlGroup(step: step, isResting: isResting, isComplete: isComplete, countdown: countdown, monotonicTime: monotonicTime, canNavigate: canNavigate)
							.frame(width: 224)
					}
				}
				if isScaleTrackingReady, motherboardBluetoothService.state.showsWorkoutMeter {
					meter(step: step)
				}
			}
			.padding(.horizontal, 16)
			.padding(.vertical, 10)
        }
	}

	private func landscapeHandCueSlot(
		holdCue: WorkoutHoldCue?,
		cueStep: WorkoutStep?,
		countdown: Int,
		isComplete: Bool,
		isSkipCountdown: Bool,
		taskIndex: Int,
		selectedHandSide: WorkoutSide?,
		side: GripCueSide,
		usesSharedPairPreview: Bool = false
	) -> some View {
		ZStack {
			Color.clear
				.accessibilityHidden(true)
			if let holdCue, WorkoutLandscapeHandCuePolicy.showsHandCue(
				for: side == .left ? .left : .right,
				holdCue: holdCue,
				cueStep: cueStep,
				countdown: mountedCueCountdown(countdown),
				isComplete: isComplete,
				isSkipCountdown: isSkipCountdown,
				taskIndex: taskIndex,
				selectedHandSide: selectedHandSide
			) {
				GripHandCueCard(
					posture: holdCue.gripType,
					fingerConfiguration: holdCue.fingerConfiguration,
					side: side,
					usesSharedPairPreview: usesSharedPairPreview
				)
                .opacity(isInitialCountdown && countdown > 0 ? 0 : 1)
                .allowsHitTesting(!(isInitialCountdown && countdown > 0))
                    .accessibilityHidden(isInitialCountdown && countdown > 0)
			}
		}
		.frame(width: LandscapeLayout.sideCueSlotWidth)
		.frame(maxHeight: LandscapeLayout.normalCueRowHeight)
	}

	private func landscapeHeader(
		step: WorkoutStep,
		stepElapsed: TimeInterval,
		countdown: Int,
		canNavigate: Bool,
		isResting: Bool,
		isComplete: Bool
	) -> some View {
		HStack(alignment: .center, spacing: 16) {
			VStack(alignment: .leading, spacing: 3) {
				SectionLabel(
					title: isComplete
						? "Session complete"
						: countdown > 0
							? "Get ready"
							: "Step \(step.number) of \(activeSteps.count)"
				)
				Text(WorkoutPresentationContent.title(step: step, isComplete: isComplete))
					.font(.system(.title2, design: .rounded, weight: .bold))
					.foregroundStyle(Color.hangInk)
					.lineLimit(1)
			}

			Spacer(minLength: 12)

			Pill(
				title: rendererStartGate.isPending ? "Preparing" : isComplete ? "Done" : countdown > 0 ? "Ready" : isResting ? "Rest" : intervalLabel(for: step),
				tint: isComplete ? Color.hangGreenDark : countdown > 0 ? Color.hangInk : isResting ? WorkoutPhase.rest.textTint : step.phase.textTint,
				fill: (isComplete ? Color.hangGreen : countdown > 0 ? Color.warmUp : isResting ? Color.restBlue : step.phase.tint).opacity(0.18)
			)

            WorkoutTimerView(
                remaining: timerRemaining(step: step, stepElapsed: stepElapsed, countdown: countdown, isComplete: isComplete),
                compact: true
            )

			Button("Routine") {
				showsStepPicker = true
			}
			.font(.system(.footnote, design: .rounded, weight: .bold))
			.foregroundStyle(Color.hangGreenDark)
			.disabled(!canNavigate)
			.accessibilityLabel("Routine, current step \(step.number): \(step.title)")
			.accessibilityIdentifier("workout.routinePicker")

			if planNeedsHandChoice {
				handPreferenceMenu()
			}
		}
	}

	private func landscapePreStartControls(
		step: WorkoutStep,
		isResting: Bool,
		isComplete: Bool,
		countdown: Int,
		monotonicTime: TimeInterval,
		canNavigate: Bool,
		currentStopwatchKey: WorkoutActivitySegmentKey?
	) -> some View {
		let presentation = WorkoutLandscapePreStartPresentation.content(
			for: step,
			countdown: countdown,
			isResting: isResting,
			isComplete: isComplete,
			currentStopwatchKey: currentStopwatchKey
		)
		return HStack(alignment: .center, spacing: 12) {
			if let cueCardRows = presentation.cueCardRows {
				cueCard(
					rows: cueCardRows,
					step: step,
					countdown: countdown,
					isResting: isResting,
					compact: true
				)
				.frame(minWidth: 156, maxWidth: .infinity)
			}

			VStack(spacing: 6) {
				HStack(spacing: 10) {
					Spacer(minLength: 0)

					controlButton(isComplete: isComplete, countdown: countdown)
						.frame(maxWidth: 164)
					skipStepButton(step: step, canNavigate: canNavigate, compact: true)
				}

				if let stopwatchKey = presentation.stopwatchKey {
					stopwatchControl(for: stopwatchKey, at: monotonicTime, compact: true)
				}

				if countdown == 0, !isResting, !isComplete, step.action == .loadedLift {
					liftCompletionControl(for: step, sessionCanNavigate: canNavigate)
				}
			}
			.frame(maxWidth: 400)
			.layoutPriority(1)
		}
	}

    private func sessionHeader(
        step: WorkoutStep,
        stepElapsed: TimeInterval,
        elapsed: TimeInterval,
        countdown: Int,
        canNavigate: Bool,
        isResting: Bool,
        isComplete: Bool
    ) -> some View {
        VStack(alignment: .leading, spacing: 13) {
            HStack {
                SectionLabel(
                    title: isComplete
                        ? "Session complete"
                        : countdown > 0
                            ? "Get ready"
                            : "Step \(step.number) of \(activeSteps.count)"
                )
                Spacer()
                Pill(
                    title: isComplete ? "Done" : countdown > 0 ? "Ready" : isResting ? "Rest" : intervalLabel(for: step),
                    tint: isComplete ? Color.hangGreenDark : countdown > 0 ? Color.hangInk : isResting ? WorkoutPhase.rest.textTint : step.phase.textTint,
                    fill: (isComplete ? Color.hangGreen : countdown > 0 ? Color.warmUp : isResting ? Color.restBlue : step.phase.tint).opacity(0.19)
                )
            }

            Button("Routine") {
                showsStepPicker = true
            }
            .font(.system(.footnote, design: .rounded, weight: .bold))
            .foregroundStyle(Color.hangGreenDark)
            .disabled(!canNavigate)
            .accessibilityLabel("Routine, current step \(step.number): \(step.title)")
            .accessibilityIdentifier("workout.routinePicker")

            if planNeedsHandChoice {
                handPreferenceMenu()
            }

			Text(WorkoutPresentationContent.title(step: step, isComplete: isComplete))
				.font(.system(.largeTitle, design: .rounded, weight: .bold))
				.foregroundStyle(Color.hangInk)

			if !step.isRestStep {
				Text(WorkoutStepFormatting.labels(
					for: step,
					taskIndex: taskCursor.index(for: step),
					selectedHandSide: taskCursor.selectedSide(for: step)
				).joined(separator: " • "))
					.font(.system(.footnote, design: .rounded, weight: .bold))
					.foregroundStyle(step.phase.textTint)
			}

            if rendererStartGate.isPending {
                Text("Preparing 3D views…")
                    .font(.subheadline)
                    .accessibilityIdentifier("workout.preparingRenderers")
            }
            portraitTimerLabel(step: step, stepElapsed: stepElapsed, countdown: countdown, isComplete: isComplete)

            ProgressView(value: min(elapsed, sessionDuration), total: sessionDuration)
                .tint(Color.hangGreenDark)
        }
    }

    private func portraitTimerLabel(
        step: WorkoutStep,
        stepElapsed: TimeInterval,
        countdown: Int,
        isComplete: Bool
    ) -> some View {
        WorkoutTimerView(remaining: timerRemaining(step: step, stepElapsed: stepElapsed, countdown: countdown, isComplete: isComplete))
    }

    private func timerRemaining(step: WorkoutStep, stepElapsed: TimeInterval, countdown: Int, isComplete: Bool) -> TimeInterval {
        isComplete ? 0 : countdown > 0 ? TimeInterval(countdown) : intervalRemaining(step: step, stepElapsed: stepElapsed)
    }

    private func cueCard(
        rows: [InstructionAccessoryCardRow],
        step: WorkoutStep,
        countdown: Int,
        isResting: Bool,
        compact: Bool = false
    ) -> some View {
        WorkoutCueCard(
            rows: rows,
            title: countdown > 0 ? "Next" : isResting ? "Recovery" : "Instructions",
            intervalTitle: countdown == 0 ? intervalLabel(for: step) : nil,
            tint: isResting && !compact ? WorkoutPhase.rest.textTint : step.phase.textTint,
            compact: compact
        )
    }

	private func controlGroup(
		step: WorkoutStep,
		isResting: Bool,
		isComplete: Bool,
		countdown: Int,
		monotonicTime: TimeInterval,
		canNavigate: Bool
	) -> some View {
        VStack(spacing: 10) {
			controlButton(isComplete: isComplete, countdown: countdown)

			if countdown == 0, !isResting, !isComplete, step.action == .loadedLift {
				liftCompletionControl(for: step, sessionCanNavigate: canNavigate)
			}

            if countdown == 0, !isResting, !isComplete, let key = currentStopwatchKey(for: step) {
                stopwatchControl(for: key, at: monotonicTime)
            }

			skipStepButton(step: step, canNavigate: canNavigate)
		}
	}

	private func liftCompletionControl(
		for step: WorkoutStep,
		sessionCanNavigate: Bool
	) -> some View {
		let prescribed = step.repetitions ?? 0
		let completed = liftCompletion.completedRepetitions(for: step)
		let unit = motherboardSettingsStore.forceUnit
		return VStack(spacing: 6) {
			HStack(spacing: 8) {
				Text("External load")
					.font(.system(.footnote, design: .rounded, weight: .bold))
					.foregroundStyle(Color.hangMuted)
				TextField(
					"0",
					value: loadedLiftExternalLoadBinding(for: step, unit: unit),
					format: .number.precision(.fractionLength(1))
				)
				.keyboardType(.numbersAndPunctuation)
				.multilineTextAlignment(.center)
				.frame(maxWidth: 100)
				.textFieldStyle(.roundedBorder)
				.accessibilityIdentifier("workout.loadedLiftExternalLoad")
				Text(unit.label)
					.font(.system(.footnote, design: .rounded, weight: .bold))
					.foregroundStyle(Color.hangMuted)
			}
			Text("\(completed) of \(prescribed) lifts complete")
				.font(.system(.footnote, design: .rounded, weight: .bold))
				.foregroundStyle(Color.hangMuted)
			Button("Complete lift") {
				liftCompletion.completeLift(for: step)
			}
			.frame(maxWidth: .infinity)
			.font(.system(.subheadline, design: .rounded, weight: .bold))
			.foregroundStyle(Color.hangGreenDark)
			.padding(.vertical, 10)
			.background(Color.hangGreen.opacity(0.16), in: RoundedRectangle(cornerRadius: 13, style: .continuous))
			.disabled(
				!WorkoutLiftCompletionPolicy.isEnabled(
					completedRepetitions: completed,
					prescribedRepetitions: prescribed,
					sessionCanNavigate: sessionCanNavigate
				)
			)
			.accessibilityIdentifier("workout.completeLift")
		}
	}

	private func loadedLiftExternalLoadBinding(
		for step: WorkoutStep,
		unit: MotherboardForceUnit
	) -> Binding<Double> {
		Binding(
			get: {
				unit.value(fromKilogramsForce: liftCompletion.externalLoadKGF(for: step) ?? 0)
			},
			set: { displayedValue in
				liftCompletion.setExternalLoadKGF(
					unit.kilogramsForce(fromDisplayedForce: displayedValue),
					for: step
				)
			}
		)
	}

    private func skipStepButton(step: WorkoutStep, canNavigate: Bool, compact: Bool = false) -> some View {
        WorkoutSkipControl(
            stepLabel: "\(step.number): \(step.title)",
            isEnabled: canNavigate,
            compact: compact,
            action: skipCurrentStep
        )
    }

    @ViewBuilder
    private func controlButton(isComplete: Bool, countdown: Int) -> some View {
        if rendererStartGate.isPending {
            Button {
                cancelPendingCountdownArm()
                audioCoach.stop()
            } label: {
                Label("Cancel preparation", systemImage: "xmark")
                    .frame(maxWidth: .infinity)
                    .font(.system(.callout, design: .rounded, weight: .bold))
                    .foregroundStyle(Color.hangInk)
                    .padding(.horizontal, 18)
                    .padding(.vertical, 16)
                    .background(Color.hangGreen, in: RoundedRectangle(cornerRadius: 17))
            }
            .buttonStyle(.plain)
        } else {
        WorkoutPrimaryControl(
            isComplete: isComplete,
            countdown: countdown,
            isRunning: sessionState.activeStartUptime != nil,
            isFirstStart: WorkoutSessionPolicy.isFirstStart(routineStartedAt: sessionState.routineStartedAt)
        ) {
            if isComplete {
                completeSession()
            } else if countdown > 0 {
                cancelCountdown()
            } else {
                toggleRunning()
            }
        }
        }
    }

    private func stopwatchControl(
        for key: WorkoutActivitySegmentKey,
        at monotonicTime: TimeInterval,
        compact: Bool = false
    ) -> some View {
        let stopwatch = stopwatches[key] ?? WorkoutStopwatch()
        return WorkoutStopwatchControl(
            stopwatch: stopwatch,
            elapsed: stopwatch.elapsed(at: monotonicTime) ?? 0,
            compact: compact
        ) {
            toggleStopwatch(for: key, at: WorkoutClock.monotonicTime)
        }
    }

	private func handPreferenceMenu() -> some View {
		Menu {
			handPreferenceMenuButton(.left, title: "Left hand", accessibilityID: "handSide.left")
			handPreferenceMenuButton(.right, title: "Right hand", accessibilityID: "handSide.right")
			handPreferenceMenuButton(.alternate, title: "Alternate hands", accessibilityID: "handSide.alternate")
			handPreferenceMenuButton(
				.both,
				title: HandChoiceCopy.bothHandsTitle(boardIsOneHanded: boardIsOneHanded),
				accessibilityID: "handSide.both",
				disabled: !bothHandsResolvable,
				hint: HandChoiceCopy.bothHandsHint(boardIsOneHanded: boardIsOneHanded)
			)
		} label: {
			HStack(spacing: 6) {
				Image(systemName: "hand.raised")
				Text(handChoiceLabel)
			}
			.font(.system(.footnote, design: .rounded, weight: .bold))
			.foregroundStyle(Color.hangGreenDark)
		}
		.disabled(!WorkoutSessionPolicy.isFirstStart(routineStartedAt: sessionState.routineStartedAt))
		.accessibilityLabel("Hand choice, \(handChoiceLabel)")
		.accessibilityIdentifier("workout.handPicker")
	}

	@ViewBuilder
	private func handPreferenceMenuButton(
		_ preference: WorkoutSessionHandPreference,
		title: String,
		accessibilityID: String,
		disabled: Bool = false,
		hint: String? = nil
	) -> some View {
		let button = Button {
			applyHandPreference(preference)
		} label: {
			if handPreference == preference {
				Label(title, systemImage: "checkmark")
			} else {
				Text(title)
			}
		}
		.disabled(disabled)
		.accessibilityIdentifier(accessibilityID)

		if let hint {
			button.accessibilityHint(Text(hint))
		} else {
			button
		}
	}

	private var handChoiceLabel: String {
		switch handPreference {
		case .left: "Left hand"
		case .right: "Right hand"
		case .alternate: "Alternate hands"
		case .both, .none: HandChoiceCopy.bothHandsTitle(boardIsOneHanded: boardIsOneHanded)
		}
	}

	private func applyHandPreference(_ preference: WorkoutSessionHandPreference) {
		handPreference = preference
		sessionSteps = WorkoutSessionHandResolver.sessionSteps(
			from: plan.steps,
			preference: preference,
			boardIsOneHanded: boardIsOneHanded
		)
		initializeStopwatches()
	}

	private func resolvedHandSide(for step: WorkoutStep) -> WorkoutSide? {
		if let selectedTaskSide = taskCursor.selectedSide(for: step) {
			return selectedTaskSide
		}
		if step.side == .left || step.side == .right {
			return step.side
		}
		return handPreference?.selectedHandSide
	}

    private func toggleRunning() {
		if sessionState.activeStartUptime == nil,
		   WorkoutSessionPolicy.isFirstStart(routineStartedAt: sessionState.routineStartedAt),
		   planNeedsHandChoice,
		   handPreference == nil {
			applyHandPreference(
				WorkoutSessionHandResolver.defaultPreference(plan: plan, board: board)
			)
		}
		let monotonicTime = WorkoutClock.monotonicTime
		if rendererStartGate.isPending || pendingCountdownStart != nil || countdownArmTask != nil {
            let shouldPause = WorkoutSessionPolicy.shouldPauseAfterCancellingPendingCountdown(
                kind: pendingCountdownStart?.kind,
                isRunning: sessionState.activeStartUptime != nil
            )
			countdownArmTask?.cancel()
			countdownArmTask = nil
			pendingCountdownStart = nil
            rendererStartGate.cancel()
			audioCoach.stop()
            guard shouldPause else { return }
		}
		if sessionState.activeStartUptime != nil {
			if countdownRemaining(at: monotonicTime) > 0 {
				cancelCountdown()
				return
			}
			recorder.pause(at: currentElapsed(at: monotonicTime))
			pauseStopwatches(at: monotonicTime)
			sessionState.toggleRunning(uptime: monotonicTime)
			audioCoach.stop()
		} else if needsWorkoutPreparation {
			showsWorkoutPreparation = true
		} else {
			let isFirstStart = WorkoutSessionPolicy.isFirstStart(
				routineStartedAt: sessionState.routineStartedAt
			)
			if isFirstStart {
				motherboardMeasurementCollector.reset()
				requestCountdownStart(.initial)
				return
			}
			sessionState.toggleRunning(
				uptime: monotonicTime,
				now: nil
			)
		}
    }

	private func requestCountdownStart(_ countdown: PendingCountdownStart) {
        if countdown == .initial, !rendererStartGate.requestFirstStart() { return }
		if audioCuesEnabled,
		   WorkoutSessionPolicy.shouldPrepareCountdownAudio(
			preparationState: audioCoach.countdownPreparationState
		   ) {
			audioCoach.prepareCountdownAudio()
		}
		if audioCuesEnabled,
		   WorkoutSessionPolicy.shouldDeferCountdownStart(
			isFirstStart: countdown == .initial,
			preparationState: audioCoach.countdownPreparationState
		   ) {
			pendingCountdownStart = countdown
			return
		}

		let now = WorkoutClock.monotonicTime
		guard audioCuesEnabled, audioCoach.countdownPreparationState == .ready else {
			beginVisibleCountdown(countdown, at: now)
			return
		}

		let armUptime = now + WorkoutSessionPolicy.countdownAudioArmLead(
			environment: ProcessInfo.processInfo.environment
		)
		let targetElapsed: TimeInterval
		switch countdown {
		case .initial:
			targetElapsed = 0
		case .skip(let elapsed):
			targetElapsed = elapsed
		}
		let schedule = CountdownAudioSchedule(remainingFrom: "3")
			.appendingShortIntervals(
				WorkoutCountdownIntervalPolicy.shortDurations(
					in: activeSteps,
					startingAt: targetElapsed
				),
				startingAt: 3
			)
		_ = audioCoach.startCountdown(schedule, startUptime: armUptime)
		countdownArmTask?.cancel()
        pendingCountdownStart = countdown
		countdownArmTask = Task { @MainActor in
			do {
				try await Task.sleep(for: .seconds(max(0, armUptime - WorkoutClock.monotonicTime)))
			} catch {
				return
			}
			guard !Task.isCancelled else { return }
			countdownArmTask = nil
            pendingCountdownStart = nil
			beginVisibleCountdown(countdown, at: armUptime)
		}
	}

	private func beginVisibleCountdown(
		_ countdown: PendingCountdownStart,
		at armUptime: TimeInterval
	) {
		switch countdown {
		case .initial:
            rendererStartGate.finishPreparation()
			sessionState.toggleRunning(uptime: armUptime, now: Date())
		case .skip(let targetElapsed):
			sessionState.startSkipCountdown(to: targetElapsed, at: armUptime)
		}
	}

    private func cancelCountdown() {
        rendererStartGate.cancel()
		let monotonicTime = WorkoutClock.monotonicTime
		sessionState.cancelCountdown(at: monotonicTime)
		audioCoach.stop()
    }

	private func endSession() {
		cancelPendingCountdownArm()
		interruptRecorderIfNeeded()
        finalizeAllStopwatches(at: WorkoutClock.monotonicTime)
		sessionState.activeStartUptime = nil
		audioCoach.stop()
        dismiss()
    }

	private func pauseForInterruption() {
		cancelPendingCountdownArm()
		let monotonicTime = WorkoutClock.monotonicTime
		pauseStopwatches(at: monotonicTime)
		guard sessionState.activeStartUptime != nil else {
			audioCoach.stop()
			return
		}
		if countdownRemaining(at: monotonicTime) == 0 {
			recorder.pause(at: currentElapsed(at: monotonicTime))
		}
		sessionState.pauseForInterruption(at: monotonicTime)
		audioCoach.stop()
	}

	private func completeSession() {
		cancelPendingCountdownArm()
		finalizeRoutine(monotonicTime: WorkoutClock.monotonicTime)
		if let completedSession {
			summarySession = completedSession
		}
		audioCoach.stop()
	}

	private func cancelPendingCountdownArm() {
        rendererStartGate.cancel()
		countdownArmTask?.cancel()
		countdownArmTask = nil
		pendingCountdownStart = nil
	}

	private func meter(step: WorkoutStep) -> some View {
		MotherboardMeterView(
			measurement: motherboardBluetoothService.latestMeasurement,
			peakLoadKGF: recorder.currentStepID == step.id ? recorder.currentPeakLoadKGF : nil,
			actualLoadedTime: recorder.currentStepID == step.id ? recorder.currentLoadedDuration : 0,
			plannedActiveDuration: step.activeDuration,
			bodyweightKGF: bodyweightKGF,
			unit: motherboardSettingsStore.forceUnit,
			state: motherboardBluetoothService.state,
			thresholdKGF: motherboardSettingsStore.thresholdKGF
		)
	}

	private func consume(_ measurement: MotherboardMeasurement, at monotonicTime: TimeInterval) {
		guard isScaleTrackingReady else { return }
		guard sessionState.activeStartUptime != nil,
			  countdownRemaining(at: monotonicTime) == 0,
              WorkoutSessionPolicy.isMeasurementEligible(
				routineStartedAt: sessionState.routineStartedAt,
              measurementTimestamp: measurement.timestamp
              ) else { return }

		let elapsed = currentElapsed(at: monotonicTime)
		guard elapsed < sessionDuration else { return }
		let currentStep = step(at: elapsed)
		guard !currentStep.isRestStep,
			  !isRestInterval(step: currentStep, stepElapsed: elapsedInStep(at: elapsed)) else { return }

		recorder.consume(
			measurement,
			stepID: currentStep.id,
			plannedActiveDuration: currentStep.activeDuration,
			workoutElapsed: elapsed,
			stepStartElapsed: stepStartElapsed(at: elapsed),
			isActive: true
		)
	}

	private func capture(_ measurement: MotherboardMeasurement, at monotonicTime: TimeInterval) {
		guard isScaleTrackingReady else { return }
		guard sessionState.activeStartUptime != nil,
			  motherboardBluetoothService.connectedProfile == .motherboard else { return }
		motherboardMeasurementCollector.capture(
			measurement,
			startedAt: sessionState.routineStartedAt,
			countdownRemaining: countdownRemaining(at: monotonicTime),
			workoutElapsed: currentElapsed(at: monotonicTime),
			planDuration: sessionDuration
		)
	}

	private func finalizeRoutine(monotonicTime: TimeInterval = WorkoutClock.monotonicTime) {
		guard !didComplete else { return }
		didComplete = true
		completedStopwatchDurations = WorkoutStopwatchLifecycle.finalizeAndSnapshotStopwatches(
			at: monotonicTime,
			in: &stopwatches
		)
		recorder.pause(at: sessionDuration)

		let completedMeasurements = Dictionary(
			uniqueKeysWithValues: recorder.finish(at: sessionDuration).map { ($0.stepID, $0) }
		)
		// Session steps already carry resolved handUse/side (left/right/both/alternate expansion).
		let steps = activeSteps.map { step in
			let measurement = completedMeasurements[step.id] ?? WorkoutStepMeasurement(
				stepID: step.id,
				plannedActiveDuration: step.activeDuration,
				intervals: [],
				peakLoadKGF: nil,
				sampleCount: 0,
				status: .unmeasured
			)
			return WorkoutStepMeasurement(
				stepID: measurement.stepID,
				plannedActiveDuration: measurement.plannedActiveDuration,
				intervals: measurement.intervals,
				peakLoadKGF: measurement.peakLoadKGF,
				sampleCount: measurement.sampleCount,
				status: measurement.status,
				handUse: step.handUse,
				side: step.side,
				action: step.action,
				repetitions: step.repetitions,
				completedRepetitions: step.action == .loadedLift
					? liftCompletion.completedRepetitions(for: step)
					: nil,
				externalLoadKGF: step.action == .loadedLift
					? liftCompletion.externalLoadKGF(for: step)
					: step.externalLoadKGF,
				isRest: step.isRestStep
			)
		}
		let recordedAt = Date()
		let startDate = sessionState.routineStartedAt ?? recordedAt.addingTimeInterval(-sessionDuration)
		let endDate = WorkoutSessionPolicy.completedWorkoutInterval(
			sessionStartedAt: startDate,
			recordedAt: recordedAt
		).end
		let session = WorkoutSessionRecord(
			id: UUID(),
			planID: plan.id,
			planTitle: plan.title,
			recordedAt: recordedAt,
			startDate: startDate,
			endDate: endDate,
			motherboardIdentifier: initialWeight.source == .sensor ? motherboardBluetoothService.connectedDeviceID?.uuidString : nil,
			batteryValue: initialWeight.source == .sensor ? motherboardBluetoothService.batteryValue : nil,
			steps: steps,
			stepTitles: activeSteps.map(\.title),
			forceSensorProfile: WorkoutSessionPolicy.recordedForceSensorProfile(
				source: initialWeight.source,
				connectedProfile: motherboardBluetoothService.connectedProfile,
				configuredProfile: motherboardSettingsStore.forceSensorProfile
			),
			bodyweightKGF: initialWeight.source == .sensor ? bodyweightKGF : nil,
			initialWeight: initialWeight,
			loadAdjustmentKGF: 0,
			loadAdjustmentDisplayUnit: motherboardSettingsStore.loadAdjustmentUnit,
			motherboardMeasurements: initialWeight.source == .sensor
				? motherboardMeasurementCollector.measurements
				: [],
			motherboardMeasurementsTruncated: initialWeight.source == .sensor
				&& motherboardMeasurementCollector.didTruncate
		)
		completedSession = session
		summarySession = session
	}

	private func configureRecorder() {
		guard sessionState.activeStartUptime == nil, sessionState.pausedElapsed == 0, !didComplete else { return }
		recorder = MotherboardWorkoutRecorder(configuration: .init(
			thresholdKGF: motherboardSettingsStore.thresholdKGF
		))
	}

	private var needsWorkoutPreparation: Bool {
		initialWeight.source == .sensor && MotherboardWorkoutPreparation.requiresPreparation(
			isInitialStart: sessionState.activeStartUptime == nil
				&& sessionState.pausedElapsed == 0
				&& !didCompleteWorkoutPreparation,
			isStreaming: motherboardBluetoothService.state == .streaming
		)
	}

	private var isScaleTrackingReady: Bool {
		WorkoutSessionPolicy.isScaleTrackingReady(
			source: initialWeight.source,
			didCompleteInitialPreparation: didCompleteWorkoutPreparation
		)
	}

	private func save(_ session: WorkoutSessionRecord) {
		guard !didSaveSession, completedSession?.id == session.id else { return }
		didSaveSession = true
		store.markSessionComplete(
			plan,
			board: board,
			stopwatchDurations: completedStopwatchDurations,
			startDate: session.startDate,
			endDate: session.endDate,
			handPreference: planNeedsHandChoice ? handPreference : nil,
			sessionSteps: planNeedsHandChoice ? sessionSteps : nil,
			performedTaskIndicesByStepID: taskCursor.performedTaskIndicesByStepID,
			selectedTaskSidesByStepID: taskCursor.selectedTaskSidesByStepID,
			session: session
		)
		summarySession = nil
		dismiss()
	}

	private func discard(_ session: WorkoutSessionRecord) {
		guard completedSession?.id == session.id else { return }
		summarySession = nil
		completedSession = nil
		sessionState = WorkoutSessionState()
		audioCoach.stop()
		dismiss()
	}

	private func interruptRecorderForSensorLoss() {
		guard isScaleTrackingReady else { return }
		let monotonicTime = WorkoutClock.monotonicTime
		guard sessionState.activeStartUptime != nil,
			  countdownRemaining(at: monotonicTime) == 0,
			  !didComplete else { return }

		let elapsed = currentElapsed(at: monotonicTime)
		let currentStep = step(at: elapsed)
		guard !currentStep.isRestStep,
			  !isRestInterval(step: currentStep, stepElapsed: elapsedInStep(at: elapsed)) else { return }

		recorder.interrupt(
			stepID: currentStep.id,
			plannedActiveDuration: currentStep.activeDuration,
			stepStartElapsed: stepStartElapsed(at: elapsed),
			at: elapsed
		)
	}

	private func interruptRecorderIfNeeded() {
		guard isScaleTrackingReady else { return }
		let monotonicTime = WorkoutClock.monotonicTime
		let hasStartedActiveWork = sessionState.activeStartUptime != nil && countdownRemaining(at: monotonicTime) == 0
		let hasElapsedWork = currentElapsed(at: monotonicTime) > 0
		guard !didComplete, !didInterruptRecorder, hasStartedActiveWork || hasElapsedWork else { return }
		recorder.interrupt(at: currentElapsed(at: monotonicTime))
		didInterruptRecorder = true
	}

    private func currentElapsed(at uptime: TimeInterval) -> TimeInterval {
        sessionState.currentElapsed(planDuration: sessionDuration, at: uptime)
    }

    private func countdownRemaining(at uptime: TimeInterval) -> Int {
        sessionState.countdownRemaining(at: uptime)
    }

    private func step(at elapsed: TimeInterval) -> WorkoutStep {
        guard let step = timeline.step(at: elapsed) ?? activeSteps.last else {
            preconditionFailure("A workout session requires at least one step.")
        }
        return step
    }

    private func elapsedInStep(at elapsed: TimeInterval) -> TimeInterval {
        timeline.elapsedInStep(at: elapsed)
    }

    private func canNavigate(at uptime: TimeInterval) -> Bool {
        sessionState.canNavigate(planDuration: sessionDuration, at: uptime)
    }

    private func seek(to targetElapsed: TimeInterval, at uptime: TimeInterval) {
        sessionState.seek(to: targetElapsed, planDuration: sessionDuration, at: uptime)
        audioCoach.stop()
    }

    private func jump(to step: WorkoutStep) {
        let monotonicTime = WorkoutClock.monotonicTime
        guard canNavigate(at: monotonicTime) else { return }

        let elapsed = currentElapsed(at: monotonicTime)
        guard let target = timeline.selectionTarget(for: step.id, at: elapsed) else { return }
		finalizeCurrentStopwatch(at: monotonicTime)
		seek(to: target, at: monotonicTime)
    }

    private func skipCurrentStep() {
        let monotonicTime = WorkoutClock.monotonicTime
        guard let decision = sessionState.skipDecision(
            timeline: timeline, planDuration: sessionDuration, at: monotonicTime
        ) else { return }
        finalizeCurrentStopwatch(at: monotonicTime)
        audioCoach.stop()
        switch decision {
        case .seek(let target):
            sessionState.seek(to: target, planDuration: sessionDuration, at: monotonicTime)
        case .countdown(let target):
            requestCountdownStart(.skip(targetElapsed: target))
        }
    }

	private func stepStartElapsed(at elapsed: TimeInterval) -> TimeInterval {
		var cursor: TimeInterval = 0
        for step in activeSteps {
            if elapsed < cursor + step.duration {
                return cursor
            }
            cursor += step.duration
		}
		return max(0, cursor - (activeSteps.last?.duration ?? 0))
	}
	private func initializeStopwatches() {
		for step in activeSteps {
			for (index, segment) in step.segments.enumerated() where segment.kind == .work && segment.timing == .stopwatch {
				let key = WorkoutActivitySegmentKey(stepID: step.id, segmentIndex: index)
				if stopwatches[key] == nil { stopwatches[key] = WorkoutStopwatch() }
			}
		}
	}

	private func currentStopwatchKey(for step: WorkoutStep) -> WorkoutActivitySegmentKey? {
		let keys = step.segments.enumerated().compactMap { index, segment -> WorkoutActivitySegmentKey? in
			guard segment.kind == .work, segment.timing == .stopwatch else { return nil }
			return WorkoutActivitySegmentKey(stepID: step.id, segmentIndex: index)
		}
		return keys.first(where: { !(stopwatches[$0]?.isFinalized ?? false) }) ?? keys.last
	}

	private func toggleStopwatch(for key: WorkoutActivitySegmentKey, at monotonicTime: TimeInterval) {
		guard var stopwatch = stopwatches[key], !stopwatch.isFinalized else { return }
		if stopwatch.isRunning {
			stopwatch.pause(at: monotonicTime)
		} else {
			stopwatch.start(at: monotonicTime)
		}
		stopwatches[key] = stopwatch
	}

	private func pauseStopwatches(at monotonicTime: TimeInterval) {
		for key in stopwatches.keys {
			guard var stopwatch = stopwatches[key], stopwatch.isRunning else { continue }
			stopwatch.pause(at: monotonicTime)
			stopwatches[key] = stopwatch
		}
	}

	private func finalizeCurrentStopwatch(at monotonicTime: TimeInterval) {
		let elapsed = currentElapsed(at: monotonicTime)
		let step = step(at: elapsed)
		guard let key = currentStopwatchKey(for: step) else { return }
		WorkoutStopwatchLifecycle.finalizeStopwatch(for: key, at: monotonicTime, in: &stopwatches)
	}

	private func finalizeStopwatches(for stepID: String, at monotonicTime: TimeInterval) {
		WorkoutStopwatchLifecycle.finalizeStopwatches(for: stepID, at: monotonicTime, in: &stopwatches)
	}

	private func finalizeAllStopwatches(at monotonicTime: TimeInterval) {
		for key in stopwatches.keys {
			WorkoutStopwatchLifecycle.finalizeStopwatch(for: key, at: monotonicTime, in: &stopwatches)
		}
	}

    private func isRestInterval(step: WorkoutStep, stepElapsed: TimeInterval) -> Bool {
        step.phase == .rest || (step.hasRestInterval && stepElapsed >= step.activeDuration)
    }

    private func intervalRemaining(step: WorkoutStep, stepElapsed: TimeInterval) -> TimeInterval {
        if isRestInterval(step: step, stepElapsed: stepElapsed) {
            return max(0, step.duration - stepElapsed)
        }
        return max(0, step.activeDuration - stepElapsed)
    }

    private func intervalLabel(for step: WorkoutStep) -> String {
        if step.phase == .rest {
            return step.phase.label
        }
        if step.timedWorkDuration != nil {
            switch step.phase {
            case .hang:
                return "Hang"
            case .pull:
                return "Pull"
            case .conditioning:
                return "Conditioning"
            default:
                break
            }
        }
        return step.hasRestInterval ? "Hang" : "Cycle"
    }

	private func audioMoment(
		step: WorkoutStep,
		stepElapsed: TimeInterval,
		elapsed: TimeInterval,
		countdown: Int,
		isTimedResting: Bool,
		isComplete: Bool
	) -> WorkoutAudioMoment? {
		guard sessionState.activeStartUptime != nil else { return nil }
		let segmentName = isTimedResting ? "rest" : "active"

		if countdown > 0 {
			return WorkoutAudioCuePolicy.moment(
				stepID: step.id,
				segmentName: segmentName,
				initialCountdown: countdown,
				intervalSecondsRemaining: 0,
				isComplete: isComplete,
				countdownKind: sessionState.countdownKind
			)
		}
		let secondsRemaining = Int(
			ceil(intervalRemaining(step: step, stepElapsed: stepElapsed))
		)
		let intervalDuration = WorkoutCountdownIntervalPolicy.duration(
			for: step,
			isTimedResting: isTimedResting
		)
		let intervalEndElapsed = stepStartElapsed(at: elapsed)
			+ (isTimedResting ? step.duration : step.activeDuration)

		return WorkoutAudioCuePolicy.scheduledMoment(
			stepID: step.id,
			segmentName: segmentName,
			initialCountdown: countdown,
			intervalSecondsRemaining: secondsRemaining,
			intervalDuration: intervalDuration,
			followingShortSegmentDurations: WorkoutCountdownIntervalPolicy.shortDurations(
				in: activeSteps,
				startingAt: intervalEndElapsed
			),
			isComplete: isComplete
		)
	}

	private func audioCountdownStartUptime(
		step: WorkoutStep,
		elapsed: TimeInterval,
		countdown: Int,
		isTimedResting: Bool,
		moment: WorkoutAudioMoment?
	) -> TimeInterval? {
		guard let activeStartUptime = sessionState.activeStartUptime,
		      let moment,
		      let remaining = Int(moment.phrase),
		      (1...3).contains(remaining) else { return nil }

		if countdown > 0 {
			return activeStartUptime - TimeInterval(remaining)
		}

		let intervalEndElapsed = stepStartElapsed(at: elapsed)
			+ (isTimedResting ? step.duration : step.activeDuration)
		return activeStartUptime
			+ intervalEndElapsed
			- sessionState.pausedElapsed
			- TimeInterval(remaining)
	}
}


/// Current mounted hosts, not cached resources or proof of a displayed frame.
struct WorkoutRendererReadiness: Equatable {
    enum Kind: Equatable { case board, hand }
    struct Renderer: Equatable {
        let kind: Kind
        let isReady: Bool
        var preparationID: UUID? = nil
    }
    var renderers: [UUID: Renderer] = [:]
    func isReady(requiresBoard: Bool, requiresHands: Bool) -> Bool {
        (!requiresBoard || renderers.values.contains { $0.kind == .board })
            && (!requiresHands || renderers.values.contains { $0.kind == .hand })
            && renderers.values.allSatisfy(\.isReady)
    }
}


struct WorkoutRendererReadinessKey: PreferenceKey {
    static var defaultValue: WorkoutRendererReadiness { .init() }
    static func reduce(value: inout WorkoutRendererReadiness,
                       nextValue: () -> WorkoutRendererReadiness) {
        value.renderers.merge(nextValue().renderers) { _, current in current }
    }
}

private struct WorkoutRendererPreparationIDKey: EnvironmentKey {
    static let defaultValue: UUID? = nil
}

extension EnvironmentValues {
    /// A new start intent requires fresh synchronization of the mounted hosts.
    /// Nil leaves non-workout renderers outside the preparation protocol.
    var workoutRendererPreparationID: UUID? {
        get { self[WorkoutRendererPreparationIDKey.self] }
        set { self[WorkoutRendererPreparationIDKey.self] = newValue }
    }
}


/// First-start intent is consumed once. Late host changes cannot restart a
/// cancelled preparation, and resume/Skip never enter this policy.
struct WorkoutRendererStartGate {
    private(set) var requestID: UUID?
    private(set) var isPending = false
    private var isReleased = false

    mutating func requestFirstStart() -> Bool {
        if isReleased { return true }
        if !isPending { requestID = UUID() }
        isPending = true
        return false
    }

    mutating func consume(_ readiness: WorkoutRendererReadiness,
                          requiresBoard: Bool, requiresHands: Bool) -> Bool {
        guard isPending,
              readiness.renderers.values.allSatisfy({ $0.preparationID == requestID }),
              readiness.isReady(requiresBoard: requiresBoard,
                                requiresHands: requiresHands) else { return false }
        isPending = false
        isReleased = true
        return true
    }

    mutating func finishPreparation() {
        // Once the initial countdown starts, later phase/camera changes use
        // the normal renderer path without preparation-driven invalidations.
        requestID = nil
        isPending = false
    }

    mutating func cancel() {
        requestID = nil
        isPending = false
        isReleased = false
    }
}
