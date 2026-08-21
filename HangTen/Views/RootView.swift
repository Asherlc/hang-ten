import SwiftUI
import UIKit

struct MotherboardWorkoutPreparationHandoff {
    private(set) var didAccept = false

    mutating func accept() -> Bool {
        guard !didAccept else { return false }
        didAccept = true
        return true
    }
}

@MainActor
protocol RootViewBackgroundTaskApplication: AnyObject {
	func beginBackgroundTask(withName taskName: String?, expirationHandler handler: (@MainActor @Sendable () -> Void)?) -> UIBackgroundTaskIdentifier
	func endBackgroundTask(_ identifier: UIBackgroundTaskIdentifier)
}

extension UIApplication: RootViewBackgroundTaskApplication {}

@MainActor
final class RootViewSessionPersistenceCoordinator {
	private let application: RootViewBackgroundTaskApplication
	private var backgroundTaskIdentifier = UIBackgroundTaskIdentifier.invalid

	init(application: RootViewBackgroundTaskApplication) {
		self.application = application
	}

	func flush(store: AppStore) {
		backgroundTaskIdentifier = application.beginBackgroundTask(
			withName: "Persist workout sessions",
			expirationHandler: { [weak self] in
				self?.finish()
			}
		)
		store.flushSessionPersistence { [self] in
			finish()
		}
	}

	private func finish() {
		guard backgroundTaskIdentifier != .invalid else { return }
		let identifier = backgroundTaskIdentifier
		backgroundTaskIdentifier = .invalid
		application.endBackgroundTask(identifier)
	}
}

struct InstructionAccessoryCardRow: Equatable {
    enum Kind: Equatable {
        case instruction
        case accessory
    }

    let kind: Kind
    let text: String
}

enum InstructionAccessoryCardContent {
    static func rows(instruction: String, accessory: String) -> [InstructionAccessoryCardRow] {
        [
            row(kind: .instruction, text: instruction),
            row(kind: .accessory, text: accessory)
        ].compactMap { $0 }
    }

    static func instructionText(_ text: String) -> String? {
        row(kind: .instruction, text: text)?.text
    }

    static func accessoryText(_ text: String) -> String? {
        row(kind: .accessory, text: text)?.text
    }

    private static func row(
        kind: InstructionAccessoryCardRow.Kind,
        text: String
    ) -> InstructionAccessoryCardRow? {
        guard !text.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else {
            return nil
        }
        return InstructionAccessoryCardRow(kind: kind, text: text)
    }
}

enum RootTab: Hashable, CaseIterable {
    case train
    case plans
    case history

    static func initial(environment: [String: String]) -> RootTab {
        #if DEBUG
        if environment["HANGTEN_REVIEW_HISTORY"] == "1" {
            return .history
        }
        if environment["HANGTEN_REVIEW_PLANS"] == "1" {
            return .plans
        }
        #endif
        return .train
    }
}

struct RootView: View {
    @EnvironmentObject private var store: AppStore
	@StateObject private var workoutAudioCoach = WorkoutAudioCoach()
    @State private var selectedTab = RootTab.initial(
        environment: ProcessInfo.processInfo.environment
    )

    var body: some View {
        TabView(selection: $selectedTab) {
            TrainView { selectedTab = .plans }
                .tabItem { Label("Train", systemImage: "figure.climbing") }
                .tag(RootTab.train)

            PlansView()
                .tabItem {
                    Label("Plans", systemImage: "list.bullet.rectangle.portrait.fill")
                }
                .tag(RootTab.plans)

            HistoryView()
                .tabItem { Label("History", systemImage: "clock.arrow.circlepath") }
                .tag(RootTab.history)
			}
			.tint(.hangGreenDark)
			.environmentObject(workoutAudioCoach)
		.onReceive(NotificationCenter.default.publisher(for: UIApplication.didEnterBackgroundNotification)) { _ in
			RootViewSessionPersistenceCoordinator(application: UIApplication.shared).flush(store: store)
		}
		.onReceive(NotificationCenter.default.publisher(for: UIApplication.willTerminateNotification)) { _ in
			store.flushSessionPersistenceSynchronously()
		}
        .onAppear {
            #if DEBUG
            let environment = ProcessInfo.processInfo.environment
            let orientationMask: UIInterfaceOrientationMask?
            if environment["HANGTEN_REVIEW_LANDSCAPE"] == "1" {
                orientationMask = .landscapeRight
            } else if environment["HANGTEN_REVIEW_PORTRAIT"] == "1" {
                orientationMask = .portrait
            } else {
                orientationMask = nil
            }

            guard let orientationMask,
                  let windowScene = UIApplication.shared.connectedScenes
                    .compactMap({ $0 as? UIWindowScene })
                    .first else { return }

            windowScene.requestGeometryUpdate(
                .iOS(interfaceOrientations: orientationMask)
            )
            #endif
        }
    }
}

struct PlansView: View {
    @EnvironmentObject private var store: AppStore
    @State private var filters = PlanFilters()
    @State private var isCreatingRoutine = false

    var body: some View {
        let compatiblePlans = store.plans
        let metadataByPlanID = Dictionary(
            compatiblePlans.map { plan in
                (plan.id, store.metadata(for: plan))
            },
            uniquingKeysWith: { first, _ in first }
        )
        let filterOptions = PlanFilterOptions(metadata: Array(metadataByPlanID.values))
        let filteredPlans = filters.isEmpty
            ? compatiblePlans
            : compatiblePlans.filter { plan in
                guard let metadata = metadataByPlanID[plan.id] else { return false }
                return filters.matches(metadata)
            }
        let customPlanIDs = Set(store.customPlans.map(\.id))
        let myRoutines = filteredPlans.filter { customPlanIDs.contains($0.id) }
        let libraryPlans = filteredPlans.filter { !customPlanIDs.contains($0.id) }

        NavigationStack {
            ScrollView(showsIndicators: false) {
                VStack(alignment: .leading, spacing: 20) {
                    VStack(alignment: .leading, spacing: 6) {
                        SectionLabel(title: "Training library")
                        Text("Choose your session.")
                            .font(.system(size: 31, weight: .bold, design: .rounded))
                            .foregroundStyle(Color.hangInk)
                        Text("Official manufacturer sequences and source-linked adapted protocols. Hold targets are matched to your board.")
                            .font(.system(size: 15, weight: .medium, design: .rounded))
                            .foregroundStyle(Color.hangMuted)
                            .fixedSize(horizontal: false, vertical: true)

                        currentBoardControl

                        Button {
                            isCreatingRoutine = true
                        } label: {
                            Label("Create routine", systemImage: "plus")
                                .font(.system(size: 15, weight: .bold, design: .rounded))
                                .foregroundStyle(Color.hangInk)
                                .padding(.horizontal, 14)
                                .padding(.vertical, 10)
                                .background(
                                    Color.hangGreen,
                                    in: RoundedRectangle(cornerRadius: 12, style: .continuous)
                                )
                        }
                        .buttonStyle(.plain)
                        .accessibilityIdentifier("customRoutine.create")

                        if let persistenceError = store.customRoutinePersistenceError {
                            HStack(alignment: .top, spacing: 10) {
                                Image(systemName: "exclamationmark.triangle.fill")
                                    .foregroundStyle(.orange)
                                VStack(alignment: .leading, spacing: 2) {
                                    Text("Some custom routines are unavailable")
                                        .font(.system(size: 14, weight: .bold, design: .rounded))
                                        .foregroundStyle(Color.hangInk)
                                    Text(persistenceError)
                                        .font(.system(size: 12, weight: .medium, design: .rounded))
                                        .foregroundStyle(Color.hangMuted)
                                }
                            }
                            .padding(12)
                            .background(
                                Color.orange.opacity(0.12),
                                in: RoundedRectangle(cornerRadius: 12, style: .continuous)
                            )
                            .accessibilityIdentifier("customRoutine.persistenceError")
                        }

                        filterBar(options: filterOptions)
                    }

                    if !myRoutines.isEmpty {
                        VStack(alignment: .leading, spacing: 12) {
                            SectionLabel(title: "My routines")
                            ForEach(myRoutines) { plan in
                                FavoritePlanCard(
                                    plan: plan,
                                    board: store.board(for: plan),
                                    isFavorite: store.isFavorite(plan),
                                    isIncompatible: store.isIncompatible(plan, on: store.selectedBoard)
                                ) {
                                    store.toggleFavorite(plan)
                                }
                            }
                        }
                    }

                    if compatiblePlans.isEmpty {
                        VStack(alignment: .leading, spacing: 8) {
                            SectionLabel(title: "No compatible routines")
                            Text("No plan currently resolves every required hold on \(store.selectedBoard.name).")
                                .font(.system(size: 14, weight: .semibold, design: .rounded))
                                .foregroundStyle(Color.hangInk)
                        }
                        .hangCard()
                    } else if filteredPlans.isEmpty {
                        NoMatchingPlansCard {
                            filters.clear()
                        }
                    } else if !libraryPlans.isEmpty {
                        VStack(alignment: .leading, spacing: 12) {
                            SectionLabel(title: "Training library")
                            ForEach(libraryPlans) { plan in
                            FavoritePlanCard(
                                plan: plan,
                                board: store.board(for: plan),
                                isFavorite: store.isFavorite(plan),
                                isIncompatible: store.isIncompatible(plan, on: store.selectedBoard)
                            ) {
                                store.toggleFavorite(plan)
                            }
                        }
                        }
                    }

                    sourceCard
                }
                .padding(.horizontal, 20)
                .padding(.top, 18)
                .padding(.bottom, 30)
            }
            .background(Color.hangBackground)
            .toolbar(.hidden, for: .navigationBar)
            .sheet(isPresented: $isCreatingRoutine) {
                CustomRoutineEditorView(
                    draft: CustomRoutineDraft(
                        createWith: .boardSpecific(boardID: store.selectedBoard.id)
                    ),
                    onSave: store.saveCustomRoutine
                )
            }
        }
    }

    private var currentBoardControl: some View {
        NavigationLink {
            BoardPickerView()
        } label: {
            HStack(spacing: 12) {
                Image(systemName: "rectangle.portrait.fill")
                    .foregroundStyle(Color.hangGreenDark)
                VStack(alignment: .leading, spacing: 2) {
                    Text("Training on")
                        .font(.system(size: 12, weight: .semibold, design: .rounded))
                        .foregroundStyle(Color.hangMuted)
                    Text(store.selectedBoard.name)
                        .font(.system(size: 15, weight: .bold, design: .rounded))
                        .foregroundStyle(Color.hangInk)
                }
                Spacer()
                Image(systemName: "chevron.right")
                    .font(.system(size: 13, weight: .bold, design: .rounded))
                    .foregroundStyle(Color.hangGreenDark)
            }
            .padding(14)
            .background(
                Color.hangCream,
                in: RoundedRectangle(cornerRadius: 16, style: .continuous)
            )
            .overlay {
                RoundedRectangle(cornerRadius: 16, style: .continuous)
                    .stroke(Color.hangLine.opacity(0.8), lineWidth: 1)
            }
        }
        .buttonStyle(.plain)
        .accessibilityIdentifier("plans.changeBoard")
    }

    private func filterBar(options: PlanFilterOptions) -> some View {
        ScrollView(.horizontal, showsIndicators: false) {
            HStack(spacing: 8) {
                if !options.levels.isEmpty {
                    Menu {
                        filterAllButton(isSelected: filters.levels.isEmpty) {
                            filters.levels.removeAll()
                        }
                        ForEach(options.levels, id: \.self) { value in
                            filterValueButton(value, isSelected: filters.levels.contains(value)) {
                                filters.toggle(level: value)
                            }
                        }
                    } label: {
                        filterMenuLabel(
                            title: "Difficulty",
                            selectionCount: filters.levels.count,
                            singleSelection: filters.levels.first
                        )
                    }
                    .accessibilityLabel("Filter by difficulty")
                    .accessibilityValue(filterMenuAccessibilityValue(
                        selectionCount: filters.levels.count,
                        singleSelection: filters.levels.first
                    ))
                }

                if !options.provenances.isEmpty {
                    Menu {
                        filterAllButton(isSelected: filters.provenances.isEmpty) {
                            filters.provenances.removeAll()
                        }
                        ForEach(options.provenances, id: \.self) { value in
                            filterValueButton(value.label, isSelected: filters.provenances.contains(value)) {
                                filters.toggle(provenance: value)
                            }
                        }
                    } label: {
                        filterMenuLabel(
                            title: "Type",
                            selectionCount: filters.provenances.count,
                            singleSelection: filters.provenances.first?.label
                        )
                    }
                    .accessibilityLabel("Filter by type")
                    .accessibilityValue(filterMenuAccessibilityValue(
                        selectionCount: filters.provenances.count,
                        singleSelection: filters.provenances.first?.label
                    ))
                }

                if !options.categories.isEmpty {
                    Menu {
                        filterAllButton(isSelected: filters.categories.isEmpty) {
                            filters.categories.removeAll()
                        }
                        ForEach(options.categories, id: \.self) { value in
                            filterValueButton(displayName(value), isSelected: filters.categories.contains(value)) {
                                filters.toggle(category: value)
                            }
                        }
                    } label: {
                        filterMenuLabel(
                            title: "Category",
                            selectionCount: filters.categories.count,
                            singleSelection: filters.categories.first.map(displayName)
                        )
                    }
                    .accessibilityLabel("Filter by category")
                    .accessibilityValue(filterMenuAccessibilityValue(
                        selectionCount: filters.categories.count,
                        singleSelection: filters.categories.first.map(displayName)
                    ))
                }

                if !options.tags.isEmpty {
                    Menu {
                        filterAllButton(isSelected: filters.tags.isEmpty) {
                            filters.tags.removeAll()
                        }
                        ForEach(options.tags, id: \.self) { value in
                            filterValueButton(displayName(value), isSelected: filters.tags.contains(value)) {
                                filters.toggle(tag: value)
                            }
                        }
                    } label: {
                        filterMenuLabel(
                            title: "Tags",
                            selectionCount: filters.tags.count,
                            singleSelection: filters.tags.first.map(displayName)
                        )
                    }
                    .accessibilityLabel("Filter by tags")
                    .accessibilityValue(filterMenuAccessibilityValue(
                        selectionCount: filters.tags.count,
                        singleSelection: filters.tags.first.map(displayName)
                    ))
                }

                if !options.equipment.isEmpty {
                    Menu {
                        filterAllButton(isSelected: filters.equipment.isEmpty) {
                            filters.equipment.removeAll()
                        }
                        ForEach(options.equipment, id: \.self) { value in
                            filterValueButton(displayName(value), isSelected: filters.equipment.contains(value)) {
                                filters.toggle(equipment: value)
                            }
                        }
                    } label: {
                        filterMenuLabel(
                            title: "Equipment",
                            selectionCount: filters.equipment.count,
                            singleSelection: filters.equipment.first.map(displayName)
                        )
                    }
                    .accessibilityLabel("Filter by equipment")
                    .accessibilityValue(filterMenuAccessibilityValue(
                        selectionCount: filters.equipment.count,
                        singleSelection: filters.equipment.first.map(displayName)
                    ))
                }

                if !filters.isEmpty {
                    Button("Clear") {
                        filters.clear()
                    }
                    .font(.system(size: 13, weight: .bold, design: .rounded))
                    .foregroundStyle(Color.hangGreenDark)
                    .accessibilityLabel("Clear plan filters")
                }
            }
            .padding(.vertical, 2)
        }
    }

    private func filterAllButton(isSelected: Bool, action: @escaping () -> Void) -> some View {
        Button(action: action) {
            Label("All", systemImage: isSelected ? "checkmark" : "rectangle")
        }
    }

    private func filterValueButton(_ title: String, isSelected: Bool, action: @escaping () -> Void) -> some View {
        Button(action: action) {
            Label(title, systemImage: isSelected ? "checkmark" : "rectangle")
        }
    }

    private func filterMenuLabel(title: String, selectionCount: Int, singleSelection: String?) -> some View {
        let isActive = selectionCount > 0
        let label = if selectionCount == 1 {
            singleSelection ?? title
        } else if selectionCount > 1 {
            "\(selectionCount) selected"
        } else {
            title
        }

        return HStack(spacing: 5) {
            Text(label)
            Image(systemName: "chevron.down")
                .font(.system(size: 10, weight: .bold))
        }
        .font(.system(size: 13, weight: .bold, design: .rounded))
        .foregroundStyle(isActive ? Color.hangGreenDark : Color.hangInk)
        .padding(.horizontal, 11)
        .padding(.vertical, 8)
        .background(
            isActive ? Color.hangGreen.opacity(0.25) : Color.hangCream,
            in: Capsule()
        )
        .overlay {
            Capsule()
                .stroke(isActive ? Color.hangGreenDark.opacity(0.55) : Color.hangLine.opacity(0.8), lineWidth: 1)
        }
    }

    private func filterMenuAccessibilityValue(selectionCount: Int, singleSelection: String?) -> String {
        if selectionCount == 0 {
            return "All"
        } else if selectionCount == 1 {
            return singleSelection ?? "1 selected"
        } else {
            return "\(selectionCount) selected"
        }
    }

    private func displayName(_ rawValue: String) -> String {
        rawValue.replacingOccurrences(of: "-", with: " ").capitalized
    }

    private var sourceCard: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack(spacing: 8) {
                Image(systemName: "link")
                    .foregroundStyle(Color.hangGreenDark)
                SectionLabel(title: "Built from the source")
            }
            Text("The three Metolius sequences preserve their official task data. Research and coach protocols are labeled Adapted when Hang Ten adds guidance or maps them to this board; every plan retains its own source link.")
                .font(.system(size: 14, weight: .medium, design: .rounded))
                .foregroundStyle(Color.hangMuted)
                .fixedSize(horizontal: false, vertical: true)
            Link(destination: PlanCatalog.evidenceOverviewURL) {
                HStack {
                    Text("Read the evidence overview")
                    Image(systemName: "arrow.up.right")
                }
                .font(.system(size: 13, weight: .bold, design: .rounded))
                .foregroundStyle(Color.hangGreenDark)
            }
        }
        .hangCard()
    }
}

private struct NoMatchingPlansCard: View {
    let onClear: () -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            SectionLabel(title: "No matching routines")
            Text("No routines match these filters")
                .font(.system(size: 16, weight: .bold, design: .rounded))
                .foregroundStyle(Color.hangInk)
            Button("Clear filters", action: onClear)
                .font(.system(size: 13, weight: .bold, design: .rounded))
                .foregroundStyle(Color.hangGreenDark)
        }
        .hangCard()
    }
}

private struct PlanCard: View {
    let plan: TrainingPlan
    let board: TrainingBoard
    var isIncompatible: Bool = false

    var body: some View {
        VStack(alignment: .leading, spacing: 15) {
            HStack {
                Pill(title: plan.level, tint: Color.hangGreenDark, fill: Color.hangGreen.opacity(0.25))
                Pill(
                    title: plan.provenance.label,
                    tint: Color.hangGreenDark,
                    fill: Color.hangGreen.opacity(0.16)
                )
                if isIncompatible {
                    Pill(title: "Not on this board", tint: .orange, fill: Color.orange.opacity(0.12))
                }
                Spacer()
                Text(plan.durationLabel)
                    .font(.system(size: 13, weight: .bold, design: .rounded))
                    .foregroundStyle(Color.hangMuted)
            }
            .padding(.trailing, 52)

            VStack(alignment: .leading, spacing: 6) {
                Text(plan.title)
                    .font(.system(size: 21, weight: .bold, design: .rounded))
                    .foregroundStyle(Color.hangInk)
                Text(plan.subtitle)
                    .font(.system(size: 14, weight: .medium, design: .rounded))
                    .foregroundStyle(Color.hangMuted)
                    .fixedSize(horizontal: false, vertical: true)
            }

            HStack(spacing: 8) {
                Image(systemName: "rectangle.portrait.and.arrow.right")
                Text(board.name)
                Spacer()
                Image(systemName: "chevron.right")
            }
            .font(.system(size: 12, weight: .semibold, design: .rounded))
            .foregroundStyle(Color.hangGreenDark)
        }
        .hangCard()
    }
}

struct FavoritePlanCard: View {
    let plan: TrainingPlan
    let board: TrainingBoard
    let isFavorite: Bool
    var isIncompatible: Bool = false
    let onToggle: () -> Void

    var body: some View {
        ZStack(alignment: .topTrailing) {
            NavigationLink(destination: PlanDetailView(plan: plan)) {
                PlanCard(plan: plan, board: board, isIncompatible: isIncompatible)
            }
            .buttonStyle(.plain)
            .frame(maxWidth: .infinity)

            Button(action: onToggle) {
                Image(systemName: isFavorite ? "star.fill" : "star")
                    .font(.system(size: 15, weight: .bold))
                    .foregroundStyle(isFavorite ? Color.hangGreenDark : Color.hangMuted)
                    .frame(width: 34, height: 34)
                    .background(
                        isFavorite ? Color.hangGreen.opacity(0.28) : Color.hangCream,
                        in: Circle()
                    )
                    .overlay {
                        Circle()
                            .stroke(Color.hangLine.opacity(0.8), lineWidth: 1)
                    }
                    .frame(width: 44, height: 44)
                    .contentShape(Rectangle())
            }
            .buttonStyle(.plain)
            .accessibilityLabel(
                isFavorite
                    ? "Remove \(plan.title) from favorites"
                    : "Add \(plan.title) to favorites"
            )
            .padding(.top, 8)
            .padding(.trailing, 8)
        }
    }
}

enum PlanDetailPlanResolver {
    static func resolve(
        capturedPlan: TrainingPlan,
        eligiblePlans: [TrainingPlan]
    ) -> TrainingPlan? {
        eligiblePlans.first { $0.id == capturedPlan.id }
    }
}

private enum PlanDetailResolutionError: LocalizedError {
    case unavailable

    var errorDescription: String? {
        "This routine is not available for the selected board."
    }
}

struct PlanDetailView: View {
    @EnvironmentObject private var store: AppStore
    @Environment(\.dismiss) private var dismiss
    let plan: TrainingPlan
    @State private var editorDraft: CustomRoutineDraft?
    @State private var isShowingEditor = false
    @State private var isShowingDeleteConfirmation = false
    @State private var lifecycleError: String?

    private var currentPlan: TrainingPlan? {
        PlanDetailPlanResolver.resolve(
            capturedPlan: plan,
            eligiblePlans: store.plans
        )
    }

    @MainActor
    static func duplicateDefinition(
        for plan: TrainingPlan,
        in store: AppStore
    ) throws -> CustomRoutineDefinition {
        guard let currentPlan = PlanDetailPlanResolver.resolve(
            capturedPlan: plan,
            eligiblePlans: store.plans
        ) else {
            throw PlanDetailResolutionError.unavailable
        }
        return try store.duplicateRoutine(currentPlan)
    }

    var body: some View {
        Group {
            if let currentPlan {
                ScrollView(showsIndicators: false) {
                    VStack(alignment: .leading, spacing: 21) {
                        titleBlock(for: currentPlan)
                        if let firstStep = currentPlan.steps.first,
                           !firstStep.targets.isEmpty {
                            boardPreview(for: currentPlan)
                        }
                        stepsCard(for: currentPlan)
                        sourceCard(for: currentPlan)
                    }
                    .padding(.horizontal, 20)
                    .padding(.top, 18)
                    .padding(.bottom, 116)
                }
            } else {
                unavailableContent
            }
        }
        .background(Color.hangBackground)
        .navigationTitle("Plan")
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            if let currentPlan {
                ToolbarItem(placement: .topBarTrailing) {
                    Menu {
                        Button("Duplicate", action: duplicateRoutine)
                        if store.isCustom(currentPlan) {
                            Button("Edit", action: editRoutine)
                            Button("Delete", role: .destructive) {
                                isShowingDeleteConfirmation = true
                            }
                        }
                    } label: {
                        Image(systemName: "ellipsis.circle")
                    }
                    .accessibilityIdentifier("customRoutine.actions")
                }
            }
        }
        .sheet(isPresented: $isShowingEditor) {
            if let editorDraft {
                CustomRoutineEditorView(draft: editorDraft, onSave: store.saveCustomRoutine)
            }
        }
        .confirmationDialog(
            "Delete \(currentPlan?.title ?? plan.title)?",
            isPresented: $isShowingDeleteConfirmation,
            titleVisibility: .visible
        ) {
            Button("Delete", role: .destructive, action: deleteRoutine)
                .accessibilityIdentifier("customRoutine.deleteConfirm")
            Button("Cancel", role: .cancel) {}
        } message: {
            Text("This custom routine will be removed from your library.")
        }
        .alert("Routine action failed", isPresented: lifecycleErrorAlertBinding) {
            Button("OK", role: .cancel) {
                lifecycleError = nil
            }
        } message: {
            Text(lifecycleError ?? "An unknown error occurred.")
        }
    }

    private func titleBlock(for currentPlan: TrainingPlan) -> some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack {
                Pill(title: currentPlan.level, tint: Color.hangGreenDark, fill: Color.hangGreen.opacity(0.25))
                Pill(
                    title: currentPlan.provenance.label,
                    tint: Color.hangGreenDark,
                    fill: Color.hangGreen.opacity(0.16)
                )
                Spacer()
                Label(currentPlan.durationLabel, systemImage: "timer")
                    .font(.system(size: 13, weight: .bold, design: .rounded))
                    .foregroundStyle(Color.hangMuted)
            }
            Text(currentPlan.title)
                .font(.system(size: 30, weight: .bold, design: .rounded))
                .foregroundStyle(Color.hangInk)
            Text(currentPlan.subtitle)
                .font(.system(size: 15, weight: .medium, design: .rounded))
                .foregroundStyle(Color.hangMuted)
                .fixedSize(horizontal: false, vertical: true)

            NavigationLink(destination: WorkoutView(plan: currentPlan, startsImmediately: true)) {
                HStack {
                    Image(systemName: "play.fill")
                    Text("Start routine")
                    Spacer()
                    Text(currentPlan.durationLabel)
                        .font(.system(size: 12, weight: .bold, design: .rounded))
                }
                .font(.system(size: 16, weight: .bold, design: .rounded))
                .foregroundStyle(Color.hangInk)
                .padding(.horizontal, 17)
                .padding(.vertical, 15)
                .background(Color.hangGreen, in: RoundedRectangle(cornerRadius: 16, style: .continuous))
            }
            .buttonStyle(.plain)
        }
    }

    private func boardPreview(for currentPlan: TrainingPlan) -> some View {
        let board = store.board(for: currentPlan)
        let firstStep = currentPlan.steps.first
        let firstStepHoldIDs = firstStep.map { store.holdIDs(for: $0, on: board) } ?? []
        let firstStepHold = board.holds.first { firstStepHoldIDs.contains($0.id) }
        let firstStepHoldCue = WorkoutHoldCuePolicy.resolve(
            step: firstStep,
            hold: firstStepHold,
            on: board
        )

        return VStack(alignment: .leading, spacing: 12) {
            VStack(alignment: .leading, spacing: 4) {
                SectionLabel(title: "First hold cue")
                Text(board.name)
                    .font(.system(size: 15, weight: .bold, design: .rounded))
                    .foregroundStyle(Color.hangInk)
            }
            BoardMapView(board: board, highlightedHoldIDs: firstStepHoldIDs)
                .padding(.horizontal, 12)
            if let firstStepHoldCue {
                GripDiagramView(
                    hold: firstStepHoldCue.hold,
                    gripType: firstStepHoldCue.gripType,
                    fingerConfiguration: firstStepHoldCue.fingerConfiguration
                )
            }
			if store.usesFallbackMapping(currentPlan, on: board) {
				Text("Board mapping note: a source-specific hold variant uses the closest manufacturer-documented feature available on this board. The prescribed task text remains unchanged.")
					.font(.system(size: 12, weight: .medium, design: .rounded))
					.foregroundStyle(Color.hangMuted)
					.fixedSize(horizontal: false, vertical: true)
			}
        }
        .hangCard()
    }

    private func stepsCard(for currentPlan: TrainingPlan) -> some View {
        VStack(alignment: .leading, spacing: 0) {
            HStack {
                SectionLabel(title: "Session flow")
                Spacer()
                Text("\(currentPlan.steps.count) cues")
                    .font(.system(size: 12, weight: .semibold, design: .rounded))
                    .foregroundStyle(Color.hangMuted)
            }
            .padding(.bottom, 14)

            ForEach(Array(currentPlan.steps.enumerated()), id: \.element.id) { index, step in
                StepRow(step: step, isLast: index == currentPlan.steps.count - 1)
            }

        }
        .hangCard()
    }

    @ViewBuilder
    private func sourceCard(for currentPlan: TrainingPlan) -> some View {
        if let sourceURL = currentPlan.sourceURL {
            Link(destination: sourceURL) {
                sourceCardContent(for: currentPlan, showsExternalLink: true)
            }
            .buttonStyle(.plain)
        } else {
            customSourceCard
        }
    }

    private var customSourceCard: some View {
        HStack(alignment: .top, spacing: 12) {
            Image(systemName: "person.crop.circle.badge.plus")
                .font(.system(size: 17, weight: .bold))
                .foregroundStyle(Color.hangGreenDark)
            VStack(alignment: .leading, spacing: 5) {
                Text("Created in Hang Ten")
                    .font(.system(size: 14, weight: .bold, design: .rounded))
                    .foregroundStyle(Color.hangInk)
                Text("This is a custom routine stored on this device.")
                    .font(.system(size: 12, weight: .medium, design: .rounded))
                    .foregroundStyle(Color.hangMuted)
                    .fixedSize(horizontal: false, vertical: true)
            }
            Spacer(minLength: 0)
        }
        .hangCard(padding: 16)
    }

    private func sourceCardContent(
        for currentPlan: TrainingPlan,
        showsExternalLink: Bool
    ) -> some View {
        HStack(alignment: .top, spacing: 12) {
                Image(systemName: "book.pages.fill")
                    .font(.system(size: 17, weight: .bold))
                    .foregroundStyle(Color.hangGreenDark)
                VStack(alignment: .leading, spacing: 5) {
                    Text("Source: \(currentPlan.sourceLabel)")
                        .font(.system(size: 14, weight: .bold, design: .rounded))
                        .foregroundStyle(Color.hangInk)
                    Text(currentPlan.provenance.detail)
                        .font(.system(size: 12, weight: .medium, design: .rounded))
                        .foregroundStyle(Color.hangMuted)
                        .fixedSize(horizontal: false, vertical: true)
                }
                Spacer(minLength: 0)
                if showsExternalLink {
                    Image(systemName: "arrow.up.right")
                        .font(.system(size: 12, weight: .bold))
                        .foregroundStyle(Color.hangGreenDark)
                }
            }
            .hangCard(padding: 16)
    }

    private var unavailableContent: some View {
        VStack(alignment: .leading, spacing: 14) {
            Image(systemName: "rectangle.portrait.and.arrow.right")
                .font(.system(size: 28, weight: .bold))
                .foregroundStyle(Color.hangGreenDark)
            SectionLabel(title: "Routine unavailable")
            Text(plan.title)
                .font(.system(size: 24, weight: .bold, design: .rounded))
                .foregroundStyle(Color.hangInk)
            Text("This routine does not support \(store.selectedBoard.name). Choose a compatible plan for your selected board.")
                .font(.system(size: 14, weight: .medium, design: .rounded))
                .foregroundStyle(Color.hangMuted)
                .fixedSize(horizontal: false, vertical: true)
            Button("Go back", action: dismiss.callAsFunction)
                .buttonStyle(.borderedProminent)
                .tint(.hangGreenDark)
        }
        .hangCard()
        .padding(.horizontal, 20)
        .padding(.top, 18)
        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
        .accessibilityIdentifier("plan.unavailable")
    }

    private var lifecycleErrorAlertBinding: Binding<Bool> {
        Binding(
            get: { lifecycleError != nil },
            set: { isPresented in
                if !isPresented {
                    lifecycleError = nil
                }
            }
        )
    }

    private func duplicateRoutine() {
        do {
            editorDraft = CustomRoutineDraft(
                duplicate: try Self.duplicateDefinition(for: plan, in: store)
            )
            isShowingEditor = true
        } catch {
            lifecycleError = error.localizedDescription
        }
    }

    private func editRoutine() {
        guard currentPlan != nil else {
            lifecycleError = PlanDetailResolutionError.unavailable.localizedDescription
            return
        }
        guard let definition = store.customDefinition(for: plan.id) else {
            lifecycleError = "The custom routine could not be found."
            return
        }
        editorDraft = CustomRoutineDraft(editing: definition)
        isShowingEditor = true
    }

    private func deleteRoutine() {
        guard currentPlan != nil else {
            lifecycleError = PlanDetailResolutionError.unavailable.localizedDescription
            return
        }
        do {
            try store.deleteCustomRoutine(id: plan.id)
            dismiss()
        } catch {
            lifecycleError = error.localizedDescription
        }
    }
}

private struct StepRow: View {
    let step: WorkoutStep
    let isLast: Bool

    var body: some View {
        HStack(alignment: .top, spacing: 12) {
            VStack(spacing: 0) {
                ZStack {
                    Circle()
                        .fill(step.phase.tint.opacity(0.17))
                        .frame(width: 31, height: 31)
                    Text("\(step.number)")
                        .font(.system(size: 12, weight: .bold, design: .rounded))
                        .foregroundStyle(step.phase.textTint)
                }
                if !isLast {
                    Rectangle()
                        .fill(Color.hangLine)
                        .frame(width: 1, height: 44)
                }
            }

            VStack(alignment: .leading, spacing: 5) {
                HStack(alignment: .firstTextBaseline) {
                    Text(step.title)
                        .font(.system(size: 15, weight: .bold, design: .rounded))
                        .foregroundStyle(Color.hangInk)
                    Spacer()
                    Text(step.durationLabel)
                        .font(.system(size: 12, weight: .bold, design: .rounded))
                        .foregroundStyle(Color.hangMuted)
                }
                ForEach(
                    Array(
                        InstructionAccessoryCardContent.rows(
                            instruction: step.instruction,
                            accessory: step.accessory
                        ).enumerated()
                    ),
                    id: \.offset
                ) { _, row in
                    switch row.kind {
                    case .instruction:
                        Text(row.text)
                            .font(.system(size: 13, weight: .medium, design: .rounded))
                            .foregroundStyle(Color.hangMuted)
                            .fixedSize(horizontal: false, vertical: true)
                    case .accessory:
                        Text(row.text)
                            .font(.system(size: 11, weight: .bold, design: .rounded))
                            .foregroundStyle(step.phase.textTint)
                    }
                }
            }
            .padding(.bottom, isLast ? 0 : 12)
        }
    }
}

struct WorkoutAudioMoment: Hashable {
	let key: String
	let phrase: String
}

enum WorkoutAudioCueAction: Equatable {
	case none
	case speak(WorkoutAudioMoment)
	case startCountdown(remainingFrom: String, startUptime: TimeInterval)
}

enum WorkoutCountdownKind: Equatable {
    case initial
    case skip
}

struct MotherboardWorkoutMeasurementCollector {
    static let maximumMeasurementCount = 20_000
    private(set) var measurements: [MotherboardMeasurement] = []
    private(set) var didTruncate = false

    mutating func capture(
        _ measurement: MotherboardMeasurement,
        startedAt: Date?,
        countdownRemaining: Int,
        workoutElapsed: TimeInterval,
        planDuration: TimeInterval
    ) {
        guard let startedAt,
              WorkoutSessionPolicy.isMeasurementEligible(
                routineStartedAt: startedAt,
                measurementTimestamp: measurement.timestamp
              ),
              countdownRemaining == 0,
              workoutElapsed < planDuration else { return }

        if measurements.count >= Self.maximumMeasurementCount {
            didTruncate = true
            return
        }

        measurements.append(measurement)
    }

    mutating func reset() {
        measurements = []
        didTruncate = false
    }
}

enum WorkoutAudioCuePolicy {
	static func scheduledMoment(
		stepID: String,
		segmentName: String,
		initialCountdown: Int,
		intervalSecondsRemaining: Int,
		isComplete: Bool,
		countdownKind: WorkoutCountdownKind? = nil
	) -> WorkoutAudioMoment? {
		if initialCountdown == 0, intervalSecondsRemaining == 4, !isComplete {
			return WorkoutAudioMoment(
				key: "\(stepID)-\(segmentName)-3",
				phrase: "3"
			)
		}
		return moment(
			stepID: stepID,
			segmentName: segmentName,
			initialCountdown: initialCountdown,
			intervalSecondsRemaining: intervalSecondsRemaining,
			isComplete: isComplete,
			countdownKind: countdownKind
		)
	}

	static func moment(
		stepID: String,
		segmentName: String,
		initialCountdown: Int,
		intervalSecondsRemaining: Int,
		isComplete: Bool,
		countdownKind: WorkoutCountdownKind? = nil
	) -> WorkoutAudioMoment? {
		guard !isComplete else { return nil }

		if (1...3).contains(initialCountdown) {
			return WorkoutAudioMoment(
				key: "\(countdownKind == .skip ? "skip" : "initial")-\(initialCountdown)",
				phrase: "\(initialCountdown)"
			)
		}

		guard (1...3).contains(intervalSecondsRemaining) else {
			return nil
		}

		return WorkoutAudioMoment(
			key: "\(stepID)-\(segmentName)-\(intervalSecondsRemaining)",
			phrase: "\(intervalSecondsRemaining)"
		)
	}

	static func action(
		previous: WorkoutAudioMoment?,
		current moment: WorkoutAudioMoment?,
		countdownStartUptime: TimeInterval?
	) -> WorkoutAudioCueAction {
		guard let moment else { return .none }
		guard let sequenceKey = numericSequenceKey(for: moment) else {
			return .speak(moment)
		}
		if let previous,
		   numericSequenceKey(for: previous) == sequenceKey {
			return .none
		}
		guard let countdownStartUptime else { return .none }
		return .startCountdown(
			remainingFrom: moment.phrase,
			startUptime: countdownStartUptime
		)
	}

	private static func numericSequenceKey(for moment: WorkoutAudioMoment) -> String? {
		guard ["3", "2", "1"].contains(moment.phrase) else { return nil }
		let suffix = "-\(moment.phrase)"
		guard moment.key.hasSuffix(suffix) else { return nil }
		return String(moment.key.dropLast(suffix.count))
	}
}

enum WorkoutSessionPolicy {
    static let initialCountdownDuration: TimeInterval = 3
    static let skipCountdownDuration: TimeInterval = 3

    static func countdownDuration(for kind: WorkoutCountdownKind) -> TimeInterval {
        kind == .initial ? initialCountdownDuration : skipCountdownDuration
    }

    static func shouldAutoStart(
        startsImmediately: Bool,
        didAutoStart: Bool,
        isRunning: Bool,
        routineStartedAt: Date?
    ) -> Bool {
        startsImmediately
            && !didAutoStart
            && !isRunning
            && isFirstStart(routineStartedAt: routineStartedAt)
    }

    static func isFirstStart(routineStartedAt: Date?) -> Bool {
        routineStartedAt == nil
    }

    static func shouldDeferCountdownStart(
        isFirstStart _: Bool,
        preparationState: CountdownAudioPreparationState
    ) -> Bool {
        preparationState == .preparing
    }

    static func countdownAudioArmLead(environment: [String: String]) -> TimeInterval {
        #if DEBUG
        if environment["HANGTEN_REVIEW_COUNTDOWN_CAPTURE"] == "1" {
            return 5
        }
        #endif
        return 0.1
    }

    static func startDate(for kind: WorkoutCountdownKind, now: Date) -> Date {
        now.addingTimeInterval(countdownDuration(for: kind))
    }

    static func startUptime(for kind: WorkoutCountdownKind, at uptime: TimeInterval) -> TimeInterval {
        uptime + countdownDuration(for: kind)
    }

    static func countdownRemaining(startUptime: TimeInterval?, nowUptime: TimeInterval) -> Int {
        guard let startUptime, startUptime > nowUptime else { return 0 }
        return max(1, Int(ceil(startUptime - nowUptime)))
    }

    static func runStartDate(routineStartedAt: Date?, now: Date) -> Date {
        isFirstStart(routineStartedAt: routineStartedAt)
            ? startDate(for: .initial, now: now)
            : now
    }

    static func completedWorkoutInterval(
        sessionStartedAt: Date,
        planDuration: TimeInterval,
        elapsed: TimeInterval
    ) -> DateInterval {
        let activeElapsed = min(planDuration, max(0, elapsed))
        return DateInterval(
            start: sessionStartedAt,
            end: sessionStartedAt.addingTimeInterval(activeElapsed)
        )
    }

    static func completedWorkoutInterval(
        sessionStartedAt: Date,
        recordedAt: Date
    ) -> DateInterval {
        DateInterval(start: sessionStartedAt, end: max(sessionStartedAt, recordedAt))
    }

    static func isMeasurementEligible(
        routineStartedAt: Date?,
        measurementTimestamp: Date
    ) -> Bool {
        guard let routineStartedAt else { return false }
        return routineStartedAt <= measurementTimestamp
    }
}

struct WorkoutSessionState: Equatable {
    var activeStartUptime: TimeInterval?
    var countdownKind: WorkoutCountdownKind?
    var pausedElapsed: TimeInterval
    var routineStartedAt: Date?

    init(
        activeStartUptime: TimeInterval? = nil,
        countdownKind: WorkoutCountdownKind? = nil,
        pausedElapsed: TimeInterval = 0,
        routineStartedAt: Date? = nil
    ) {
        self.activeStartUptime = activeStartUptime
        self.countdownKind = countdownKind
        self.pausedElapsed = pausedElapsed
        self.routineStartedAt = routineStartedAt
    }

    func currentElapsed(planDuration: TimeInterval, at uptime: TimeInterval) -> TimeInterval {
        let activeElapsed = activeStartUptime.map { max(0, uptime - $0) } ?? 0
        return min(planDuration, pausedElapsed + max(0, activeElapsed))
    }

    func countdownRemaining(at uptime: TimeInterval) -> Int {
        pendingCountdownRemaining(at: uptime)
    }

    private func pendingCountdownRemaining(at uptime: TimeInterval) -> Int {
        guard countdownKind != nil else { return 0 }
        return WorkoutSessionPolicy.countdownRemaining(
            startUptime: activeStartUptime,
            nowUptime: uptime
        )
    }

    mutating func transitionExpiredCountdown(at uptime: TimeInterval) {
        guard countdownKind != nil, pendingCountdownRemaining(at: uptime) == 0 else { return }
        countdownKind = nil
    }

    func canNavigate(planDuration: TimeInterval, at uptime: TimeInterval) -> Bool {
        routineStartedAt != nil
            && pendingCountdownRemaining(at: uptime) == 0
            && currentElapsed(planDuration: planDuration, at: uptime) < planDuration
    }

    mutating func toggleRunning(uptime: TimeInterval, now: Date? = nil) {
        if let activeStartUptime {
            if activeStartUptime > uptime {
                cancelCountdown(at: uptime)
                return
            }
            pausedElapsed += max(0, uptime - activeStartUptime)
            self.activeStartUptime = nil
            countdownKind = nil
        } else {
            let isFirstStart = WorkoutSessionPolicy.isFirstStart(routineStartedAt: routineStartedAt)
            if isFirstStart {
                guard let now else { return }
                routineStartedAt = WorkoutSessionPolicy.startDate(for: .initial, now: now)
                activeStartUptime = WorkoutSessionPolicy.startUptime(for: .initial, at: uptime)
                countdownKind = .initial
            } else {
                activeStartUptime = uptime
                countdownKind = nil
            }
        }
    }

    mutating func cancelCountdown(at uptime: TimeInterval) {
        guard countdownKind != nil, countdownRemaining(at: uptime) > 0 else { return }

        switch countdownKind {
        case .skip:
            activeStartUptime = nil
            countdownKind = nil
        case .initial, nil:
            activeStartUptime = nil
            routineStartedAt = nil
            countdownKind = nil
        }
    }

    mutating func pauseForInterruption(at uptime: TimeInterval) {
        guard let activeStartUptime else {
            return
        }
        if activeStartUptime > uptime {
            cancelCountdown(at: uptime)
            return
        }

        pausedElapsed += max(0, uptime - activeStartUptime)
        self.activeStartUptime = nil
        countdownKind = nil
    }

    mutating func seek(to targetElapsed: TimeInterval, planDuration: TimeInterval, at uptime: TimeInterval) {
        let target = min(max(0, targetElapsed), planDuration)
        let wasActive = activeStartUptime != nil
        countdownKind = nil
        pausedElapsed = target
        if wasActive {
            activeStartUptime = uptime
        }
    }

    mutating func skipCurrentStep(timeline: WorkoutTimeline, planDuration: TimeInterval, at uptime: TimeInterval) -> Bool {
        guard canNavigate(planDuration: planDuration, at: uptime) else { return false }

        let elapsed = currentElapsed(planDuration: planDuration, at: uptime)
        guard let target = timeline.skipTarget(from: elapsed) else { return false }

        if target >= planDuration {
            seek(to: target, planDuration: planDuration, at: uptime)
        } else if timeline.step(at: target)?.phase == .rest {
            seek(to: target, planDuration: planDuration, at: uptime)
        } else {
            startSkipCountdown(to: target, at: uptime)
        }
        return true
    }

    mutating func startSkipCountdown(to targetElapsed: TimeInterval, at uptime: TimeInterval) {
        pausedElapsed = targetElapsed
        activeStartUptime = WorkoutSessionPolicy.startUptime(for: .skip, at: uptime)
        countdownKind = .skip
    }
}

enum WorkoutStopwatchLifecycle {
    static func finalizeStopwatches(
        for stepID: String,
        at monotonicTime: TimeInterval,
        in stopwatches: inout [WorkoutActivitySegmentKey: WorkoutStopwatch]
    ) {
        for key in stopwatches.keys where key.stepID == stepID {
            finalizeStopwatch(for: key, at: monotonicTime, in: &stopwatches)
        }
    }

    static func finalizeStopwatch(
        for key: WorkoutActivitySegmentKey,
        at monotonicTime: TimeInterval,
        in stopwatches: inout [WorkoutActivitySegmentKey: WorkoutStopwatch]
    ) {
        guard var stopwatch = stopwatches[key], !stopwatch.isFinalized else { return }
        stopwatch.stop(at: monotonicTime)
        stopwatches[key] = stopwatch
    }

    static func finalizeAndSnapshotStopwatches(
        at monotonicTime: TimeInterval,
        in stopwatches: inout [WorkoutActivitySegmentKey: WorkoutStopwatch]
    ) -> [WorkoutActivitySegmentKey: TimeInterval] {
        for key in stopwatches.keys {
            finalizeStopwatch(for: key, at: monotonicTime, in: &stopwatches)
        }

        return stopwatches.reduce(into: [WorkoutActivitySegmentKey: TimeInterval]()) { result, entry in
            guard entry.value.hasStarted, let elapsed = entry.value.elapsed(at: monotonicTime) else { return }
            result[entry.key] = elapsed
        }
    }
}

struct WorkoutView: View {
    private enum PendingCountdownStart: Equatable {
        case initial
        case skip(targetElapsed: TimeInterval)
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
	@AppStorage("workoutAudioCuesEnabled") private var audioCuesEnabled = true

    let plan: TrainingPlan
    let startsImmediately: Bool

    init(plan: TrainingPlan, startsImmediately: Bool = false) {
        self.plan = plan
        self.startsImmediately = startsImmediately
        self.timeline = WorkoutTimeline(steps: plan.steps)
    }

    @State private var sessionState = WorkoutSessionState()
    @State private var didAutoStart = false
    @State private var showEndConfirmation = false
    @State private var showsStepPicker = false
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
	    @State private var pendingCountdownStart: PendingCountdownStart?
	    @State private var countdownArmTask: Task<Void, Never>?

    private var board: TrainingBoard {
        store.board(for: plan)
    }

	private let timeline: WorkoutTimeline

    var body: some View {
		GeometryReader { geometry in
			TimelineView(.periodic(from: .now, by: 0.25)) { context in
				let monotonicTime = WorkoutClock.monotonicTime
				let elapsed = currentElapsed(at: monotonicTime)
				let step = step(at: elapsed)
				let stepElapsed = elapsedInStep(at: elapsed)
				let countdown = countdownRemaining(at: monotonicTime)
				let canNavigate = canNavigate(at: monotonicTime)
				let isComplete = elapsed >= plan.duration
				let isTimedResting = isRestInterval(step: step, stepElapsed: stepElapsed)
				let boardCue = timeline.boardCue(
					currentStep: step,
					stepElapsed: stepElapsed,
					countdown: countdown,
					isComplete: isComplete,
					isSkipCountdown: sessionState.countdownKind == .skip
				)
				let isResting = boardCue.isResting
				let highlightedStep = boardCue.step
				let previewHoldIDs = highlightedStep.map { store.holdIDs(for: $0, on: board) } ?? []
				let highlightedHoldIDs = boardCue.isSuppressed ? [] : Set(previewHoldIDs)
				let highlightMode = boardCue.mode
				let showsHoldPreview = highlightMode == .preview && !highlightedHoldIDs.isEmpty
				let activeHold = board.holds.first { highlightedHoldIDs.contains($0.id) }
				let holdCue = WorkoutHoldCuePolicy.resolve(step: highlightedStep, hold: activeHold, on: board)
				let isLandscape = geometry.size.width > geometry.size.height
				let audioMoment = audioMoment(
					step: step,
					stepElapsed: stepElapsed,
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
							step: step,
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
							isSkipCountdown: sessionState.countdownKind == .skip
						)
					} else {
						portraitSession(
							step: step,
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
							isSkipCountdown: sessionState.countdownKind == .skip
						)
					}
				}
				.frame(maxWidth: .infinity, maxHeight: .infinity)
				.background(Color.hangBackground)
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

				switch WorkoutAudioCuePolicy.action(
					previous: previousMoment,
					current: moment,
					countdownStartUptime: audioCountdownStartUptime
				) {
				case .none:
					break
				case .speak(let moment):
					audioCoach.speak(moment.phrase)
				case .startCountdown(let phrase, let startUptime):
					audioCoach.startCountdown(
						remainingFrom: phrase,
						startUptime: startUptime
					)
				}
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
					WorkoutStepPickerView(plan: plan, currentStepID: step.id) { selectedStep in
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

				Button("End") {
					showEndConfirmation = true
				}
				.font(.system(size: 13, weight: .bold, design: .rounded))
				.foregroundStyle(Color.hangGreenDark)
			}
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
			#if DEBUG
			if !didApplyReviewStep {
				didApplyReviewStep = true
				if let rawStep = ProcessInfo.processInfo.environment["HANGTEN_REVIEW_STEP"],
				   let requestedStep = Int(rawStep),
				   requestedStep > 1 {
						sessionState.pausedElapsed = plan.steps
							.prefix(min(requestedStep - 1, plan.steps.count))
							.reduce(0) { $0 + $1.duration }
				}
			}

				if ProcessInfo.processInfo.environment["HANGTEN_REVIEW_AUTOSTART"] == "1",
				   sessionState.activeStartUptime == nil {
					didCompleteWorkoutPreparation = true
					toggleRunning()
				}
			#endif
			if WorkoutSessionPolicy.shouldAutoStart(
				startsImmediately: startsImmediately,
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
			guard state != .preparing, let pendingCountdownStart else { return }
			self.pendingCountdownStart = nil
			requestCountdownStart(pendingCountdownStart)
		}
		.onReceive(motherboardBluetoothService.$latestMeasurement.compactMap { $0 }) { measurement in
			let monotonicTime = WorkoutClock.monotonicTime
			guard sessionState.activeStartUptime != nil else { return }
			consume(measurement, at: monotonicTime)
			capture(measurement, at: monotonicTime)
		}
		.onChange(of: motherboardBluetoothService.state) { previousState, state in
			guard previousState == .streaming, state != .streaming else { return }
			interruptRecorderForSensorLoss()
		}
		.onDisappear {
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
					highlightMode: highlightMode
				)
					.padding(.horizontal, 2)
				if let holdCue, WorkoutHoldCueVisibilityPolicy.showsCue(
					holdCue: holdCue,
					countdown: countdown,
					isComplete: isComplete,
					isSkipCountdown: isSkipCountdown
				) {
					GripDiagramView(
						hold: holdCue.hold,
						gripType: holdCue.gripType,
						fingerConfiguration: holdCue.fingerConfiguration
					)
				}
				cueCard(
					step: step,
					stepElapsed: stepElapsed,
					countdown: countdown,
					isResting: isResting,
					isComplete: isComplete,
					showsHoldPreview: showsHoldPreview
				)
				if motherboardBluetoothService.state.showsWorkoutMeter {
					meter(step: step)
				}
			}
			.padding(.horizontal, 20)
			.padding(.top, 16)
			.padding(.bottom, 34)
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
		isSkipCountdown: Bool
	) -> some View {
		VStack(spacing: 9) {
			landscapeHeader(
				step: step,
				stepElapsed: stepElapsed,
				countdown: countdown,
				canNavigate: canNavigate,
				isResting: isResting,
				isComplete: isComplete
			)

			ProgressView(value: min(elapsed, plan.duration), total: plan.duration)
				.tint(Color.hangGreenDark)

			HStack(spacing: 12) {
				landscapeHandCueSlot(
					holdCue: holdCue,
					countdown: countdown,
					isResting: isResting,
					isComplete: isComplete,
					isSkipCountdown: isSkipCountdown,
					side: .left
				)

				VStack(alignment: .leading, spacing: 4) {
					SectionLabel(title: "Next hold preview", tint: WorkoutPhase.rest.textTint)
						.frame(maxWidth: .infinity, minHeight: LandscapeLayout.previewLabelHeight, alignment: .center)
						.opacity(showsHoldPreview ? 1 : 0)
						.accessibilityHidden(!showsHoldPreview)
					BoardMapView(
						board: board,
						highlightedHoldIDs: highlightedHoldIDs,
						highlightMode: highlightMode
					)
						.frame(maxWidth: .infinity)
						.frame(maxHeight: LandscapeLayout.boardMaxHeight)
				}
				.frame(maxWidth: .infinity)

				landscapeHandCueSlot(
					holdCue: holdCue,
					countdown: countdown,
					isResting: isResting,
					isComplete: isComplete,
					isSkipCountdown: isSkipCountdown,
					side: .right
				)
			}
			.frame(maxHeight: LandscapeLayout.normalCueRowHeight)

			HStack(alignment: .center, spacing: 12) {
				landscapeCueCard(
					step: step,
					countdown: countdown,
					isResting: isResting,
					isComplete: isComplete,
					showsHoldPreview: showsHoldPreview
				)
				controlGroup(step: step, isResting: isResting, isComplete: isComplete, countdown: countdown, monotonicTime: monotonicTime, canNavigate: canNavigate)
					.frame(width: 224)
			}
			if motherboardBluetoothService.state.showsWorkoutMeter {
				meter(step: step)
			}
		}
		.padding(.horizontal, 16)
		.padding(.vertical, 10)
	}

	private func landscapeHandCueSlot(
		holdCue: WorkoutHoldCue?,
		countdown: Int,
		isResting: Bool,
		isComplete: Bool,
		isSkipCountdown: Bool,
		side: GripCueSide
	) -> some View {
		ZStack {
			Color.clear
				.accessibilityHidden(true)
			if let holdCue, WorkoutHoldCueVisibilityPolicy.showsCue(
				holdCue: holdCue,
				countdown: countdown,
				isComplete: isComplete,
				isSkipCountdown: isSkipCountdown
			) {
				GripHandCueCard(
					posture: holdCue.gripType,
					fingerConfiguration: holdCue.fingerConfiguration,
					side: side
				)
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
							: "Step \(step.number) of \(plan.steps.count)"
				)
				Text(isComplete ? "Nice work." : isResting ? "Step off and shake out" : step.title)
					.font(.system(size: 22, weight: .bold, design: .rounded))
					.foregroundStyle(Color.hangInk)
					.lineLimit(1)
			}

			Spacer(minLength: 12)

			Pill(
				title: isComplete ? "Done" : countdown > 0 ? "Ready" : isResting ? "Rest" : intervalLabel(for: step),
				tint: isComplete ? Color.hangGreenDark : countdown > 0 ? Color.hangInk : isResting ? WorkoutPhase.rest.textTint : step.phase.textTint,
				fill: (isComplete ? Color.hangGreen : countdown > 0 ? Color.warmUp : isResting ? Color.restBlue : step.phase.tint).opacity(0.18)
			)

			Text(
				timeLabel(
					isComplete
						? 0
						: countdown > 0
							? TimeInterval(countdown)
							: intervalRemaining(step: step, stepElapsed: stepElapsed)
				)
			)
			.font(.system(size: 34, weight: .heavy, design: .rounded).monospacedDigit())
			.foregroundStyle(Color.hangInk)

			Button("Routine") {
				showsStepPicker = true
			}
			.font(.system(size: 13, weight: .bold, design: .rounded))
			.foregroundStyle(Color.hangGreenDark)
			.disabled(!canNavigate)
			.accessibilityLabel("Routine, current step \(step.number): \(step.title)")
			.accessibilityIdentifier("workout.routinePicker")
		}
	}

	private func landscapeCueCard(
		step: WorkoutStep,
		countdown: Int,
		isResting: Bool,
		isComplete: Bool,
		showsHoldPreview: Bool
	) -> some View {
        let instructionText = InstructionAccessoryCardContent.instructionText(step.instruction)
        let accessoryText = InstructionAccessoryCardContent.accessoryText(step.accessory)
		return VStack(alignment: .leading, spacing: 5) {
			SectionLabel(title: isComplete ? "What next" : countdown > 0 ? "Next up" : isResting ? "Recovery cue" : "Your cue")
            if let text = isComplete
                ? "Cool down, then log how your fingers feel."
                : countdown > 0
                    ? "Get into position for \(step.title.lowercased())."
                    : instructionText {
                Text(text)
                    .font(.system(size: 14, weight: .semibold, design: .rounded))
                    .foregroundStyle(Color.hangInk)
                    .lineLimit(2)
                    .minimumScaleFactor(0.82)
            }

            if !isComplete, countdown == 0, let accessoryText {
                Text(accessoryText)
                    .font(.system(size: 11, weight: .bold, design: .rounded))
                    .foregroundStyle(step.phase.textTint)
                    .lineLimit(1)
                    .minimumScaleFactor(0.78)
            }
		}
		.frame(maxWidth: .infinity, alignment: .leading)
		.hangCard(padding: 12)
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
                            : "Step \(step.number) of \(plan.steps.count)"
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
            .font(.system(size: 13, weight: .bold, design: .rounded))
            .foregroundStyle(Color.hangGreenDark)
            .disabled(!canNavigate)
            .accessibilityLabel("Routine, current step \(step.number): \(step.title)")
            .accessibilityIdentifier("workout.routinePicker")

            Text(isComplete ? "Nice work." : countdown > 0 ? step.title : isResting ? "Step off and shake out" : step.title)
                .font(.system(size: 30, weight: .bold, design: .rounded))
                .foregroundStyle(Color.hangInk)

            HStack(alignment: .firstTextBaseline, spacing: 7) {
                Text(
                    timeLabel(
                        isComplete
                            ? 0
                            : countdown > 0
                                ? TimeInterval(countdown)
                                : intervalRemaining(step: step, stepElapsed: stepElapsed)
                    )
                )
                    .font(.system(size: 46, weight: .heavy, design: .rounded).monospacedDigit())
                    .foregroundStyle(Color.hangInk)
                Text(
                    isComplete
                        ? "ready to log"
                        : countdown > 0
                            ? "starting in"
                            : isResting ? "rest" : step.hasRestInterval ? "left in cue" : "left in cycle"
                )
                    .font(.system(size: 13, weight: .bold, design: .rounded))
                    .foregroundStyle(Color.hangMuted)
            }

            ProgressView(value: min(elapsed, plan.duration), total: plan.duration)
                .tint(Color.hangGreenDark)
        }
    }

    private func cueCard(
        step: WorkoutStep,
		stepElapsed: TimeInterval,
		countdown: Int,
		isResting: Bool,
		isComplete: Bool,
		showsHoldPreview: Bool
    ) -> some View {
        let instructionText = InstructionAccessoryCardContent.instructionText(step.instruction)
        let accessoryText = InstructionAccessoryCardContent.accessoryText(step.accessory)
        return VStack(alignment: .leading, spacing: 11) {
            HStack {
                SectionLabel(title: isComplete ? "What next" : countdown > 0 ? "Next up" : isResting ? "Recovery cue" : "Your cue")
                Spacer()
                if !isComplete, countdown == 0 {
                    Text(intervalLabel(for: step))
                        .font(.system(size: 12, weight: .bold, design: .rounded))
                        .foregroundStyle(isResting ? WorkoutPhase.rest.textTint : step.phase.textTint)
                }
            }

            if let text = isComplete
                ? "Take a few easy minutes to cool down, then log how your fingers feel."
                : countdown > 0
                    ? "Get into position for \(step.title.lowercased()). The timer starts in \(countdown)."
                    : instructionText {
                Text(text)
                    .font(.system(size: 16, weight: .semibold, design: .rounded))
                    .foregroundStyle(Color.hangInk)
                    .fixedSize(horizontal: false, vertical: true)
            }

			if !isComplete, countdown == 0, let text = accessoryText {
				Text(text)
                    .font(.system(size: 12, weight: .bold, design: .rounded))
                    .foregroundStyle(isResting ? WorkoutPhase.rest.textTint : step.phase.textTint)
            }
        }
        .hangCard()
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

            if countdown == 0, !isResting, !isComplete, let key = currentStopwatchKey(for: step) {
                stopwatchControl(for: key, at: monotonicTime)
            }

            Button {
                skipCurrentStep()
            } label: {
                Label("Skip step", systemImage: "forward.fill")
                    .frame(maxWidth: .infinity)
                    .font(.system(size: 14, weight: .bold, design: .rounded))
                    .foregroundStyle(Color.hangGreenDark)
                    .padding(.vertical, 10)
                    .background(Color.hangGreen.opacity(0.16), in: RoundedRectangle(cornerRadius: 13, style: .continuous))
            }
            .buttonStyle(.plain)
            .disabled(!canNavigate)
            .accessibilityLabel("Skip step \(step.number): \(step.title)")
            .accessibilityIdentifier("workout.skipStep")
        }
    }

    private func controlButton(isComplete: Bool, countdown: Int) -> some View {
        Button {
            if isComplete {
                completeSession()
            } else if countdown > 0 {
                cancelCountdown()
            } else {
                toggleRunning()
            }
        } label: {
			HStack {
                    Image(systemName: isComplete ? "checkmark" : countdown > 0 ? "xmark" : (sessionState.activeStartUptime == nil ? "play.fill" : "pause.fill"))
                Text(
                    isComplete
						? "Log session"
						: countdown > 0
							? "Cancel countdown"
							: (sessionState.activeStartUptime == nil && WorkoutSessionPolicy.isFirstStart(routineStartedAt: sessionState.routineStartedAt) ? "Start routine" : (sessionState.activeStartUptime == nil ? "Resume" : "Pause"))
                )
                if isComplete {
                    Image(systemName: "arrow.right")
                }
            }
			.frame(maxWidth: .infinity, alignment: .center)
            .font(.system(size: 16, weight: .bold, design: .rounded))
            .foregroundStyle(Color.hangInk)
            .padding(.horizontal, 18)
            .padding(.vertical, 16)
            .background(Color.hangGreen, in: RoundedRectangle(cornerRadius: 17, style: .continuous))
        }
        .buttonStyle(.plain)
    }

    private func stopwatchControl(for key: WorkoutActivitySegmentKey, at monotonicTime: TimeInterval) -> some View {
        let stopwatch = stopwatches[key] ?? WorkoutStopwatch()
        let elapsed = stopwatch.elapsed(at: monotonicTime) ?? 0
        let label = stopwatch.isFinalized
            ? "Stopwatch finalized"
            : stopwatch.isRunning
                ? "Stop stopwatch"
                : stopwatch.hasStarted
                    ? "Resume stopwatch"
                    : "Start stopwatch"

        return VStack(spacing: 6) {
            Text(stopwatchTimeLabel(elapsed))
                .font(.system(size: 34, weight: .heavy, design: .rounded).monospacedDigit())
                .foregroundStyle(Color.hangInk)
                .frame(maxWidth: .infinity)

            Button {
                toggleStopwatch(for: key, at: WorkoutClock.monotonicTime)
            } label: {
                Label(label, systemImage: stopwatch.isRunning ? "pause.fill" : stopwatch.isFinalized ? "checkmark" : "stopwatch")
                    .frame(maxWidth: .infinity)
                    .font(.system(size: 14, weight: .bold, design: .rounded))
                    .foregroundStyle(Color.hangGreenDark)
                    .padding(.vertical, 10)
                    .background(Color.hangGreen.opacity(0.16), in: RoundedRectangle(cornerRadius: 13, style: .continuous))
            }
	            .buttonStyle(.plain)
	            .disabled(stopwatch.isFinalized)
	            .accessibilityLabel(label)
            .accessibilityIdentifier("workout.stopwatch.toggle")
        }
        .padding(.vertical, 4)
        .accessibilityIdentifier("workout.stopwatch")
    }

    private func toggleRunning() {
		let monotonicTime = WorkoutClock.monotonicTime
		if pendingCountdownStart != nil || countdownArmTask != nil {
			countdownArmTask?.cancel()
			countdownArmTask = nil
			pendingCountdownStart = nil
			audioCoach.stop()
			return
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
		_ = audioCoach.startCountdown(remainingFrom: "3", startUptime: armUptime)
		countdownArmTask?.cancel()
		countdownArmTask = Task { @MainActor in
			do {
				try await Task.sleep(for: .seconds(max(0, armUptime - WorkoutClock.monotonicTime)))
			} catch {
				return
			}
			guard !Task.isCancelled else { return }
			countdownArmTask = nil
			beginVisibleCountdown(countdown, at: armUptime)
		}
	}

	private func beginVisibleCountdown(
		_ countdown: PendingCountdownStart,
		at armUptime: TimeInterval
	) {
		switch countdown {
		case .initial:
			sessionState.toggleRunning(uptime: armUptime, now: Date())
		case .skip(let targetElapsed):
			sessionState.startSkipCountdown(to: targetElapsed, at: armUptime)
		}
	}

    private func cancelCountdown() {
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
		guard sessionState.activeStartUptime != nil,
			  countdownRemaining(at: monotonicTime) == 0,
              WorkoutSessionPolicy.isMeasurementEligible(
				routineStartedAt: sessionState.routineStartedAt,
              measurementTimestamp: measurement.timestamp
              ) else { return }

		let elapsed = currentElapsed(at: monotonicTime)
		guard elapsed < plan.duration else { return }
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
		guard sessionState.activeStartUptime != nil,
			  motherboardBluetoothService.connectedProfile == .motherboard else { return }
		motherboardMeasurementCollector.capture(
			measurement,
			startedAt: sessionState.routineStartedAt,
			countdownRemaining: countdownRemaining(at: monotonicTime),
			workoutElapsed: currentElapsed(at: monotonicTime),
			planDuration: plan.duration
		)
	}

	private func finalizeRoutine(monotonicTime: TimeInterval = WorkoutClock.monotonicTime) {
		guard !didComplete else { return }
		didComplete = true
		completedStopwatchDurations = WorkoutStopwatchLifecycle.finalizeAndSnapshotStopwatches(
			at: monotonicTime,
			in: &stopwatches
		)
		recorder.pause(at: plan.duration)

		let completedMeasurements = Dictionary(
			uniqueKeysWithValues: recorder.finish(at: plan.duration).map { ($0.stepID, $0) }
		)
		let steps = plan.steps.map { step in
			completedMeasurements[step.id] ?? WorkoutStepMeasurement(
				stepID: step.id,
				plannedActiveDuration: step.activeDuration,
				intervals: [],
				peakLoadKGF: nil,
				sampleCount: 0,
				status: .unmeasured
			)
		}
		let recordedAt = Date()
		let startDate = sessionState.routineStartedAt ?? recordedAt.addingTimeInterval(-plan.duration)
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
			motherboardIdentifier: motherboardBluetoothService.connectedDeviceID?.uuidString,
			batteryValue: motherboardBluetoothService.batteryValue,
			steps: steps,
			forceSensorProfile: motherboardBluetoothService.connectedProfile ?? motherboardSettingsStore.forceSensorProfile,
			bodyweightKGF: bodyweightKGF,
			motherboardMeasurements: motherboardMeasurementCollector.measurements,
			motherboardMeasurementsTruncated: motherboardMeasurementCollector.didTruncate
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
		MotherboardWorkoutPreparation.requiresPreparation(
			isInitialStart: sessionState.activeStartUptime == nil
				&& sessionState.pausedElapsed == 0
				&& !didCompleteWorkoutPreparation,
			isStreaming: motherboardBluetoothService.state == .streaming
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
		let monotonicTime = WorkoutClock.monotonicTime
		let hasStartedActiveWork = sessionState.activeStartUptime != nil && countdownRemaining(at: monotonicTime) == 0
		let hasElapsedWork = currentElapsed(at: monotonicTime) > 0
		guard !didComplete, !didInterruptRecorder, hasStartedActiveWork || hasElapsedWork else { return }
		recorder.interrupt(at: currentElapsed(at: monotonicTime))
		didInterruptRecorder = true
	}

    private func currentElapsed(at uptime: TimeInterval) -> TimeInterval {
        sessionState.currentElapsed(planDuration: plan.duration, at: uptime)
    }

    private func countdownRemaining(at uptime: TimeInterval) -> Int {
        sessionState.countdownRemaining(at: uptime)
    }

    private func step(at elapsed: TimeInterval) -> WorkoutStep {
        timeline.step(at: elapsed) ?? plan.steps.last ?? PlanCatalog.metoliusTenMinute.steps[0]
    }

    private func elapsedInStep(at elapsed: TimeInterval) -> TimeInterval {
        timeline.elapsedInStep(at: elapsed)
    }

    private func canNavigate(at uptime: TimeInterval) -> Bool {
        sessionState.canNavigate(planDuration: plan.duration, at: uptime)
    }

    private func seek(to targetElapsed: TimeInterval, at uptime: TimeInterval) {
        sessionState.seek(to: targetElapsed, planDuration: plan.duration, at: uptime)
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
		guard canNavigate(at: monotonicTime) else { return }
        finalizeCurrentStopwatch(at: monotonicTime)
		let elapsed = currentElapsed(at: monotonicTime)
		guard let target = timeline.skipTarget(from: elapsed) else { return }

		if target >= plan.duration || timeline.step(at: target)?.phase == .rest {
			sessionState.seek(to: target, planDuration: plan.duration, at: monotonicTime)
			audioCoach.stop()
			return
		}

		audioCoach.stop()
		requestCountdownStart(.skip(targetElapsed: target))
	}

	private func stepStartElapsed(at elapsed: TimeInterval) -> TimeInterval {
		var cursor: TimeInterval = 0
        for step in plan.steps {
            if elapsed < cursor + step.duration {
                return cursor
            }
            cursor += step.duration
		}
		return max(0, cursor - (plan.steps.last?.duration ?? 0))
	}
	private func initializeStopwatches() {
		for step in plan.steps {
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
			guard var stopwatch = stopwatches[key], !stopwatch.isFinalized else { continue }
			stopwatch.stop(at: monotonicTime)
			stopwatches[key] = stopwatch
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

    private func timeLabel(_ value: TimeInterval) -> String {
        let seconds = max(0, Int(value.rounded(.up)))
        return String(format: "%02d:%02d", seconds / 60, seconds % 60)
    }

	private func stopwatchTimeLabel(_ value: TimeInterval) -> String {
		let seconds = max(0, Int(value.rounded(.down)))
		return String(format: "%02d:%02d", seconds / 60, seconds % 60)
	}

	private func audioMoment(
		step: WorkoutStep,
		stepElapsed: TimeInterval,
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

		return WorkoutAudioCuePolicy.scheduledMoment(
			stepID: step.id,
			segmentName: segmentName,
			initialCountdown: countdown,
			intervalSecondsRemaining: secondsRemaining,
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
