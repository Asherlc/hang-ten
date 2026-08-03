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

struct RootView: View {
    @EnvironmentObject private var store: AppStore
    @State private var selectedTab: Int = {
        #if DEBUG
        if ProcessInfo.processInfo.environment["HANGTEN_REVIEW_HEALTH"] == "1" ||
            ProcessInfo.processInfo.environment["HANGTEN_REVIEW_MOTHERBOARD"] == "1" {
            return 2
        }
        if ProcessInfo.processInfo.environment["HANGTEN_REVIEW_PLANS"] == "1" {
            return 1
        }
        #else
        #endif
        return 0
    }()

    var body: some View {
        TabView(selection: $selectedTab) {
            HomeView()
                .tabItem {
                    Label("Today", systemImage: "sun.max.fill")
                }
                .tag(0)

            PlansView()
                .tabItem {
                    Label("Plans", systemImage: "list.bullet.rectangle.portrait.fill")
                }
                .tag(1)

            ProgressDashboardView()
                .tabItem {
                    Label("Progress", systemImage: "chart.bar.xaxis")
                }
                .tag(2)
        }
        .tint(.hangGreenDark)
		.onReceive(NotificationCenter.default.publisher(for: UIApplication.didEnterBackgroundNotification)) { _ in
			store.flushSessionPersistence()
		}
		.onReceive(NotificationCenter.default.publisher(for: UIApplication.willTerminateNotification)) { _ in
			store.flushSessionPersistence()
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

struct HomeView: View {
    @EnvironmentObject private var store: AppStore
    @State private var showsPlanReview: Bool = {
        #if DEBUG
        return ProcessInfo.processInfo.environment["HANGTEN_REVIEW_PLAN"] == "1"
        #else
        return false
        #endif
    }()
	@State private var showsWorkoutReview: Bool = {
		#if DEBUG
		return ProcessInfo.processInfo.environment["HANGTEN_REVIEW_WORKOUT"] == "1"
		#else
		return false
		#endif
	}()

    var body: some View {
        NavigationStack {
            ScrollView(showsIndicators: false) {
                VStack(alignment: .leading, spacing: 22) {
                    homeHeader
                    favoritesSection
                    boardCard
                    quickStats
                }
                .padding(.horizontal, 20)
                .padding(.top, 18)
                .padding(.bottom, 30)
            }
            .background(Color.hangBackground)
            .toolbar(.hidden, for: .navigationBar)
            .navigationDestination(isPresented: $showsPlanReview) {
                if let plan = reviewPlan {
                    PlanDetailView(plan: plan)
                } else {
                    noCompatiblePlan
                }
            }
			.navigationDestination(isPresented: $showsWorkoutReview) {
				if let plan = reviewPlan {
					WorkoutView(plan: plan)
				} else {
					noCompatiblePlan
				}
			}
        }
    }

    private var reviewPlan: TrainingPlan? {
        store.featuredPlan
    }

    private var homeHeader: some View {
        HStack(alignment: .top) {
            VStack(alignment: .leading, spacing: 6) {
                SectionLabel(title: "Hang Ten")
                Text("Train with intention.")
                    .font(.system(size: 31, weight: .bold, design: .rounded))
                    .foregroundStyle(Color.hangInk)
                Text("Your board. Your holds. Your next session.")
                    .font(.system(size: 15, weight: .medium, design: .rounded))
                    .foregroundStyle(Color.hangMuted)
            }

            Spacer()

            ZStack {
                Circle()
                    .fill(Color.hangGreen)
                    .frame(width: 48, height: 48)
                Image(systemName: "figure.climbing")
                    .font(.system(size: 20, weight: .bold))
                    .foregroundStyle(Color.hangInk)
            }
        }
    }

    @ViewBuilder
    private var favoritesSection: some View {
        if store.favoritePlans.isEmpty {
            VStack(alignment: .leading, spacing: 17) {
                SectionLabel(title: "Favorites")
                Text("Favorite routines from Plans to keep them handy here.")
                    .font(.system(size: 16, weight: .bold, design: .rounded))
                    .foregroundStyle(Color.hangInk)
                Text("Your favorites will appear here when they are compatible with your selected board.")
                    .font(.system(size: 13, weight: .medium, design: .rounded))
                    .foregroundStyle(Color.hangMuted)
            }
            .hangCard()
        } else {
            VStack(alignment: .leading, spacing: 12) {
                SectionLabel(title: "Favorites")
                ForEach(store.favoritePlans) { plan in
                    FavoritePlanCard(
                        plan: plan,
                        board: store.board(for: plan),
                        isFavorite: store.isFavorite(plan)
                    ) {
                        store.toggleFavorite(plan)
                    }
                }
            }
        }
    }

    private var noCompatiblePlan: some View {
        VStack(alignment: .leading, spacing: 8) {
            SectionLabel(title: "No compatible routine")
            Text("This board needs a routine whose hold targets resolve exactly.")
                .font(.system(size: 16, weight: .bold, design: .rounded))
                .foregroundStyle(Color.hangInk)
            Text("Choose another board or add a source-audited routine before starting a session.")
                .font(.system(size: 13, weight: .medium, design: .rounded))
                .foregroundStyle(Color.hangMuted)
        }
        .hangCard()
    }

    private var boardCard: some View {
        VStack(alignment: .leading, spacing: 16) {
            HStack(alignment: .top) {
                VStack(alignment: .leading, spacing: 5) {
                    SectionLabel(title: "Your board")
                    Text(store.selectedBoard.name)
                        .font(.system(size: 21, weight: .bold, design: .rounded))
                        .foregroundStyle(Color.hangInk)
                    Text(store.selectedBoard.dimensions)
                        .font(.system(size: 13, weight: .medium, design: .rounded))
                        .foregroundStyle(Color.hangMuted)
                }

                Spacer()

                Menu {
                    ForEach(BoardCatalog.all) { board in
                        Button {
                            store.selectedBoard = board
                        } label: {
                            Label(
                                board.name,
                                systemImage: board.id == store.selectedBoard.id ? "checkmark" : "rectangle"
                            )
                        }
                    }
                } label: {
                    Image(systemName: "slider.horizontal.3")
                        .font(.system(size: 16, weight: .bold))
                        .foregroundStyle(Color.hangInk)
                        .padding(10)
                        .background(Color.hangBackground, in: Circle())
                }
                .accessibilityLabel("Choose hangboard")
            }

            BoardMapView(board: store.selectedBoard, showsLabels: false)
                .clipShape(RoundedRectangle(cornerRadius: 18, style: .continuous))

            HStack(spacing: 7) {
                Circle()
                    .fill(Color.holdActive)
                    .frame(width: 8, height: 8)
                Text("Active holds appear in red")
                    .font(.system(size: 11, weight: .medium, design: .rounded))
                    .foregroundStyle(Color.hangMuted)
                Spacer()
                Link(destination: store.selectedBoard.productURL) {
                    Image(systemName: "arrow.up.right")
                        .font(.system(size: 12, weight: .bold))
                        .foregroundStyle(Color.hangGreenDark)
                }
                .accessibilityLabel("Open board product page")
            }
        }
        .hangCard()
    }

    private var quickStats: some View {
        HStack(spacing: 12) {
            StatCard(value: "\(store.sessionsCompleted)", label: "Sessions", icon: "checkmark.seal.fill")
            StatCard(value: "10", label: "Minutes", icon: "flame.fill")
            StatCard(value: "Open", label: "Grip focus", icon: "hand.raised.fill")
        }
    }
}

private struct StatCard: View {
    let value: String
    let label: String
    let icon: String

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Image(systemName: icon)
                .font(.system(size: 15, weight: .bold))
                .foregroundStyle(Color.hangGreenDark)
            Text(value)
                .font(.system(size: 21, weight: .bold, design: .rounded))
                .foregroundStyle(Color.hangInk)
            Text(label)
                .font(.system(size: 11, weight: .semibold, design: .rounded))
                .foregroundStyle(Color.hangMuted)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(14)
        .background(Color.hangCream, in: RoundedRectangle(cornerRadius: 18, style: .continuous))
        .overlay {
            RoundedRectangle(cornerRadius: 18, style: .continuous)
                .stroke(Color.hangLine.opacity(0.8), lineWidth: 1)
        }
    }
}

struct PlansView: View {
    @EnvironmentObject private var store: AppStore
    @State private var filters = PlanFilters()

    var body: some View {
        let compatiblePlans = store.plans
        let metadataByPlanID = Dictionary(
            compatiblePlans.compactMap { plan in
                PlanCatalog.metadata(for: plan.id).map { (plan.id, $0) }
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

        NavigationStack {
            ScrollView(showsIndicators: false) {
                VStack(alignment: .leading, spacing: 20) {
                    VStack(alignment: .leading, spacing: 6) {
                        SectionLabel(title: "Training library")
                        Text("Choose your session.")
                            .font(.system(size: 31, weight: .bold, design: .rounded))
                            .foregroundStyle(Color.hangInk)
                        Text("Official manufacturer sequences and source-linked adapted protocols, matched to your board.")
                            .font(.system(size: 15, weight: .medium, design: .rounded))
                            .foregroundStyle(Color.hangMuted)
                            .fixedSize(horizontal: false, vertical: true)

                        filterBar(options: filterOptions)
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
                    } else {
                        ForEach(filteredPlans) { plan in
                            FavoritePlanCard(
                                plan: plan,
                                board: store.board(for: plan),
                                isFavorite: store.isFavorite(plan)
                            ) {
                                store.toggleFavorite(plan)
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
        }
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

    var body: some View {
        VStack(alignment: .leading, spacing: 15) {
            HStack {
                Pill(title: plan.level, tint: Color.hangGreenDark, fill: Color.hangGreen.opacity(0.25))
                Pill(
                    title: plan.provenance.label,
                    tint: Color.hangGreenDark,
                    fill: Color.hangGreen.opacity(0.16)
                )
                Spacer()
                Text(plan.durationLabel)
                    .font(.system(size: 13, weight: .bold, design: .rounded))
                    .foregroundStyle(Color.hangMuted)
            }

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

private struct FavoritePlanCard: View {
    let plan: TrainingPlan
    let board: TrainingBoard
    let isFavorite: Bool
    let onToggle: () -> Void

    var body: some View {
        HStack(alignment: .center, spacing: 10) {
            NavigationLink(destination: PlanDetailView(plan: plan)) {
                PlanCard(plan: plan, board: board)
            }
            .buttonStyle(.plain)

            Button(action: onToggle) {
                Image(systemName: isFavorite ? "star.fill" : "star")
                    .font(.system(size: 18, weight: .bold))
                    .foregroundStyle(isFavorite ? Color.hangGreenDark : Color.hangMuted)
                    .frame(width: 44, height: 44)
                    .background(
                        isFavorite ? Color.hangGreen.opacity(0.28) : Color.hangCream,
                        in: Circle()
                    )
                    .overlay {
                        Circle()
                            .stroke(Color.hangLine.opacity(0.8), lineWidth: 1)
                    }
            }
            .buttonStyle(.plain)
            .accessibilityLabel(
                isFavorite
                    ? "Remove \(plan.title) from favorites"
                    : "Add \(plan.title) to favorites"
            )
        }
    }
}

struct PlanDetailView: View {
    @EnvironmentObject private var store: AppStore
    let plan: TrainingPlan

    private var board: TrainingBoard {
        store.board(for: plan)
    }

    private var firstStepHoldIDs: Set<String> {
        guard let firstStep = plan.steps.first else { return [] }
        return store.holdIDs(for: firstStep, on: board)
    }

    private var firstStepHold: BoardHold? {
        board.holds.first { firstStepHoldIDs.contains($0.id) }
    }

    private var firstStepGripType: GripType? {
        #if DEBUG
        if let rawValue = ProcessInfo.processInfo.environment["HANGTEN_REVIEW_GRIP"],
           let reviewGrip = GripType(rawValue: rawValue) {
            return reviewGrip
        }
        #endif
        return plan.steps.first?.gripType
    }

    var body: some View {
        ScrollView(showsIndicators: false) {
            VStack(alignment: .leading, spacing: 21) {
                titleBlock
                boardPreview
                stepsCard
                sourceCard
                safetyNote
            }
            .padding(.horizontal, 20)
            .padding(.top, 18)
            .padding(.bottom, 116)
        }
        .background(Color.hangBackground)
        .navigationTitle("Plan")
        .navigationBarTitleDisplayMode(.inline)
    }

    private var titleBlock: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack {
                Pill(title: plan.level, tint: Color.hangGreenDark, fill: Color.hangGreen.opacity(0.25))
                Pill(
                    title: plan.provenance.label,
                    tint: Color.hangGreenDark,
                    fill: Color.hangGreen.opacity(0.16)
                )
                Spacer()
                Label(plan.durationLabel, systemImage: "timer")
                    .font(.system(size: 13, weight: .bold, design: .rounded))
                    .foregroundStyle(Color.hangMuted)
            }
            Text(plan.title)
                .font(.system(size: 30, weight: .bold, design: .rounded))
                .foregroundStyle(Color.hangInk)
            Text(plan.subtitle)
                .font(.system(size: 15, weight: .medium, design: .rounded))
                .foregroundStyle(Color.hangMuted)
                .fixedSize(horizontal: false, vertical: true)

            NavigationLink(destination: WorkoutView(plan: plan)) {
                HStack {
                    Image(systemName: "play.fill")
                    Text("Start routine")
                    Spacer()
                    Text(plan.durationLabel)
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

    private var boardPreview: some View {
        VStack(alignment: .leading, spacing: 12) {
            VStack(alignment: .leading, spacing: 4) {
                SectionLabel(title: "First hold cue")
                Text(board.name)
                    .font(.system(size: 15, weight: .bold, design: .rounded))
                    .foregroundStyle(Color.hangInk)
            }
            BoardMapView(board: board, highlightedHoldIDs: firstStepHoldIDs)
                .padding(.horizontal, 12)
            if let firstStepHold {
                GripDiagramView(hold: firstStepHold, gripType: firstStepGripType)
            }
			if store.usesFallbackMapping(plan, on: board) {
				Text("Board mapping note: a source-specific hold variant uses the closest manufacturer-documented feature available on this board. The prescribed task text remains unchanged.")
					.font(.system(size: 12, weight: .medium, design: .rounded))
					.foregroundStyle(Color.hangMuted)
					.fixedSize(horizontal: false, vertical: true)
			}
        }
        .hangCard()
    }

    private var stepsCard: some View {
        VStack(alignment: .leading, spacing: 0) {
            HStack {
                SectionLabel(title: "Session flow")
                Spacer()
                Text("\(plan.steps.count) cues")
                    .font(.system(size: 12, weight: .semibold, design: .rounded))
                    .foregroundStyle(Color.hangMuted)
            }
            .padding(.bottom, 14)

            ForEach(Array(plan.steps.enumerated()), id: \.element.id) { index, step in
                StepRow(step: step, isLast: index == plan.steps.count - 1)
            }

        }
        .hangCard()
    }

    private var safetyNote: some View {
        HStack(alignment: .top, spacing: 12) {
            Image(systemName: "exclamationmark.triangle.fill")
                .font(.system(size: 16, weight: .bold))
                .foregroundStyle(Color.warmUp)
            VStack(alignment: .leading, spacing: 6) {
                Text("Train within your limits")
                    .font(.system(size: 14, weight: .bold, design: .rounded))
                    .foregroundStyle(Color.hangInk)
                Text("Warm up thoroughly, keep the board secure, and stop if you feel pain. This app is a timer and hold cue, not medical advice.")
                    .font(.system(size: 13, weight: .medium, design: .rounded))
                    .foregroundStyle(Color.hangMuted)
                    .fixedSize(horizontal: false, vertical: true)
            }
        }
        .padding(16)
        .background(Color.warmUp.opacity(0.13), in: RoundedRectangle(cornerRadius: 18, style: .continuous))
    }

    private var sourceCard: some View {
        Link(destination: plan.sourceURL) {
            HStack(alignment: .top, spacing: 12) {
                Image(systemName: "book.pages.fill")
                    .font(.system(size: 17, weight: .bold))
                    .foregroundStyle(Color.hangGreenDark)
                VStack(alignment: .leading, spacing: 5) {
                    Text("Source: \(plan.sourceLabel)")
                        .font(.system(size: 14, weight: .bold, design: .rounded))
                        .foregroundStyle(Color.hangInk)
                    Text(plan.provenance.detail)
                        .font(.system(size: 12, weight: .medium, design: .rounded))
                        .foregroundStyle(Color.hangMuted)
                        .fixedSize(horizontal: false, vertical: true)
                }
                Spacer(minLength: 0)
                Image(systemName: "arrow.up.right")
                    .font(.system(size: 12, weight: .bold))
                    .foregroundStyle(Color.hangGreenDark)
            }
            .hangCard(padding: 16)
        }
        .buttonStyle(.plain)
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
                Text(step.instruction)
                    .font(.system(size: 13, weight: .medium, design: .rounded))
                    .foregroundStyle(Color.hangMuted)
                    .fixedSize(horizontal: false, vertical: true)
                Text(step.accessory)
                    .font(.system(size: 11, weight: .bold, design: .rounded))
                    .foregroundStyle(step.phase.textTint)
            }
            .padding(.bottom, isLast ? 0 : 12)
        }
    }
}

private struct WorkoutAudioMoment: Hashable {
	let key: String
	let phrase: String
}

struct MotherboardWorkoutMeasurementCollector {
    private(set) var measurements: [MotherboardMeasurement] = []

    mutating func capture(
        _ measurement: MotherboardMeasurement,
        startedAt: Date?,
        countdownRemaining: Int,
        workoutElapsed: TimeInterval,
        planDuration: TimeInterval
    ) {
        guard let startedAt,
              startedAt <= measurement.timestamp,
              countdownRemaining == 0,
              workoutElapsed < planDuration else { return }

        measurements.append(measurement)
    }

    mutating func reset() {
        measurements = []
    }
}

enum WorkoutSessionPolicy {
    static func isFirstStart(routineStartedAt: Date?) -> Bool {
        routineStartedAt == nil
    }

    static func runStartDate(routineStartedAt: Date?, now: Date) -> Date {
        isFirstStart(routineStartedAt: routineStartedAt)
            ? now.addingTimeInterval(3)
            : now
    }

    static func completedWorkoutInterval(
        sessionStartedAt: Date,
        planDuration: TimeInterval,
        loggedAt: Date
    ) -> DateInterval {
        DateInterval(
            start: sessionStartedAt,
            end: min(sessionStartedAt.addingTimeInterval(planDuration), loggedAt)
        )
    }
}

enum WorkoutStopwatchLifecycle {
    static func finalizeStopwatches(
        for stepID: String,
        at date: Date,
        in stopwatches: inout [WorkoutActivitySegmentKey: WorkoutStopwatch]
    ) {
        for key in stopwatches.keys where key.stepID == stepID {
            finalizeStopwatch(for: key, at: date, in: &stopwatches)
        }
    }

    static func finalizeStopwatch(
        for key: WorkoutActivitySegmentKey,
        at date: Date,
        in stopwatches: inout [WorkoutActivitySegmentKey: WorkoutStopwatch]
    ) {
        guard var stopwatch = stopwatches[key], !stopwatch.isFinalized else { return }
        stopwatch.stop(at: date)
        stopwatches[key] = stopwatch
    }
}

struct WorkoutView: View {
    @EnvironmentObject private var store: AppStore
    @EnvironmentObject private var motherboardBluetoothService: MotherboardBluetoothService
    @EnvironmentObject private var motherboardSettingsStore: MotherboardSettingsStore
    @Environment(\.dismiss) private var dismiss
	@Environment(\.scenePhase) private var scenePhase
	@StateObject private var audioCoach = WorkoutAudioCoach()
	@AppStorage("workoutAudioCuesEnabled") private var audioCuesEnabled = true

    let plan: TrainingPlan

    @State private var startedAt: Date?
    @State private var pausedElapsed: TimeInterval = 0
    @State private var routineStartedAt: Date?
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

    private var board: TrainingBoard {
        store.board(for: plan)
    }

    private var timeline: WorkoutTimeline {
        WorkoutTimeline(steps: plan.steps)
    }

    var body: some View {
		GeometryReader { geometry in
			TimelineView(.periodic(from: .now, by: 0.25)) { context in
				let elapsed = currentElapsed(at: context.date)
				let step = step(at: elapsed)
				let stepElapsed = elapsedInStep(at: elapsed)
				let countdown = countdownRemaining(at: context.date)
				let isComplete = elapsed >= plan.duration
				let isResting = isRestInterval(step: step, stepElapsed: stepElapsed)
				let highlightedIDs = store.holdIDs(for: step, on: board)
				let activeHoldIDs = countdown > 0 || isComplete || isResting ? [] : highlightedIDs
				let activeHold = board.holds.first { activeHoldIDs.contains($0.id) }
				let isLandscape = geometry.size.width > geometry.size.height
				let audioMoment = audioMoment(
					step: step,
					stepElapsed: stepElapsed,
					countdown: countdown,
					isResting: isResting,
					isComplete: isComplete
				)

				Group {
					if isLandscape {
						landscapeSession(
							step: step,
							stepElapsed: stepElapsed,
							elapsed: elapsed,
							date: context.date,
							countdown: countdown,
							isResting: isResting,
							isComplete: isComplete,
							activeHoldIDs: activeHoldIDs,
							activeHold: activeHold
						)
					} else {
						portraitSession(
							step: step,
							stepElapsed: stepElapsed,
							elapsed: elapsed,
							date: context.date,
							countdown: countdown,
							isResting: isResting,
							isComplete: isComplete,
							activeHoldIDs: activeHoldIDs,
							activeHold: activeHold
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
				.onChange(of: audioMoment, initial: true) { _, moment in
					guard audioCuesEnabled, let moment else { return }
					audioCoach.speak(moment.phrase)
				}
				.onChange(of: isComplete, initial: true) { _, complete in
					guard complete else { return }
					finalizeAllStopwatches(at: context.date)
				}
				.onChange(of: step.id) { previousStepID, _ in
					finalizeStopwatches(for: previousStepID, at: context.date)
				}
				.onChange(of: isResting) { wasResting, resting in
					guard resting, !wasResting else { return }
					finalizeCurrentStopwatch(at: context.date)
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
					pausedElapsed = plan.steps
						.prefix(min(requestedStep - 1, plan.steps.count))
						.reduce(0) { $0 + $1.duration }
				}
			}

				if ProcessInfo.processInfo.environment["HANGTEN_REVIEW_AUTOSTART"] == "1",
				   startedAt == nil {
					didCompleteWorkoutPreparation = true
					toggleRunning()
				}
				#endif
				initializeStopwatches()
		}
		.onChange(of: scenePhase) { _, phase in
			guard phase != .active else { return }
			pauseForInterruption()
		}
		.onChange(of: motherboardBluetoothService.latestMeasurement) { _, measurement in
			guard let measurement else { return }
			consume(measurement)
		}
		.onReceive(motherboardBluetoothService.$latestMeasurement.compactMap { $0 }) { measurement in
			capture(measurement)
		}
		.onChange(of: motherboardBluetoothService.state) { previousState, state in
			guard previousState == .streaming, state != .streaming else { return }
			interruptRecorderForSensorLoss()
		}
		.onDisappear {
			interruptRecorderIfNeeded()
			finalizeAllStopwatches(at: Date())
			UIApplication.shared.isIdleTimerDisabled = false
			audioCoach.stop()
		}
    }

	private func portraitSession(
		step: WorkoutStep,
		stepElapsed: TimeInterval,
		elapsed: TimeInterval,
		date: Date,
		countdown: Int,
		isResting: Bool,
		isComplete: Bool,
		activeHoldIDs: Set<String>,
		activeHold: BoardHold?
	) -> some View {
		ScrollView(showsIndicators: false) {
			VStack(alignment: .leading, spacing: 19) {
				sessionHeader(
					step: step,
					stepElapsed: stepElapsed,
					elapsed: elapsed,
					countdown: countdown,
					isResting: isResting,
					isComplete: isComplete
				)
				controlGroup(step: step, isResting: isResting, isComplete: isComplete, countdown: countdown, date: date)
				BoardMapView(board: board, highlightedHoldIDs: activeHoldIDs)
					.padding(.horizontal, 2)
				if countdown == 0, !isComplete, !isResting, let activeHold {
					GripDiagramView(hold: activeHold, gripType: step.gripType)
				}
				cueCard(
					step: step,
					stepElapsed: stepElapsed,
					countdown: countdown,
					isResting: isResting,
					isComplete: isComplete
				)
				meter(step: step)
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
		date: Date,
		countdown: Int,
		isResting: Bool,
		isComplete: Bool,
		activeHoldIDs: Set<String>,
		activeHold: BoardHold?
	) -> some View {
		VStack(spacing: 9) {
			landscapeHeader(
				step: step,
				stepElapsed: stepElapsed,
				countdown: countdown,
				isResting: isResting,
				isComplete: isComplete
			)

			ProgressView(value: min(elapsed, plan.duration), total: plan.duration)
				.tint(Color.hangGreenDark)

			HStack(spacing: 12) {
				if countdown == 0, !isComplete, !isResting, let activeHold {
					let gripType = step.gripType ?? activeHold.gripType
					GripHandCueCard(hold: activeHold, gripType: gripType, side: .left)
						.frame(width: 142)
				}

				BoardMapView(board: board, highlightedHoldIDs: activeHoldIDs)
					.frame(maxWidth: .infinity)
					.frame(maxHeight: 130)

				if countdown == 0, !isComplete, !isResting, let activeHold {
					let gripType = step.gripType ?? activeHold.gripType
					GripHandCueCard(hold: activeHold, gripType: gripType, side: .right)
						.frame(width: 142)
				}
			}
			.frame(maxHeight: 132)

			HStack(alignment: .center, spacing: 12) {
				landscapeCueCard(
					step: step,
					countdown: countdown,
					isResting: isResting,
					isComplete: isComplete
				)
				controlGroup(step: step, isResting: isResting, isComplete: isComplete, countdown: countdown, date: date)
					.frame(width: 224)
			}
			meter(step: step)
		}
		.padding(.horizontal, 16)
		.padding(.vertical, 10)
	}

	private func landscapeHeader(
		step: WorkoutStep,
		stepElapsed: TimeInterval,
		countdown: Int,
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
		isComplete: Bool
	) -> some View {
		VStack(alignment: .leading, spacing: 5) {
			SectionLabel(title: isComplete ? "What next" : countdown > 0 ? "Next up" : isResting ? "Recovery cue" : "Your cue")
			Text(
				isComplete
					? "Cool down, then log how your fingers feel."
					: countdown > 0
						? "Get into position for \(step.title.lowercased())."
						: isResting
							? "Step off, shake out, and breathe."
							: step.instruction
			)
			.font(.system(size: 14, weight: .semibold, design: .rounded))
			.foregroundStyle(Color.hangInk)
			.lineLimit(2)
			.minimumScaleFactor(0.82)

			if !isComplete, countdown == 0, !isResting {
				Text(step.accessory)
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
        isComplete: Bool
    ) -> some View {
        VStack(alignment: .leading, spacing: 11) {
            HStack {
                SectionLabel(title: isComplete ? "What next" : countdown > 0 ? "Next up" : isResting ? "Recovery cue" : "Your cue")
                Spacer()
                if !isComplete, countdown == 0 {
                    Text(intervalLabel(for: step))
                        .font(.system(size: 12, weight: .bold, design: .rounded))
                        .foregroundStyle(isResting ? WorkoutPhase.rest.textTint : step.phase.textTint)
                }
            }

            Text(
                isComplete
                    ? "Take a few easy minutes to cool down, then log how your fingers feel."
                    : countdown > 0
                        ? "Get into position for \(step.title.lowercased()). The timer starts in \(countdown)."
                        : isResting
                            ? "Step off the board, shake out, and breathe. Your next hold cue will appear when the rest interval ends."
                            : step.instruction
            )
                .font(.system(size: 16, weight: .semibold, design: .rounded))
                .foregroundStyle(Color.hangInk)
                .fixedSize(horizontal: false, vertical: true)

            if !isComplete, countdown == 0 {
                Text(isResting ? "Rest interval · next cue follows automatically" : step.accessory)
                    .font(.system(size: 12, weight: .bold, design: .rounded))
                    .foregroundStyle(isResting ? WorkoutPhase.rest.textTint : step.phase.textTint)
            }
        }
        .hangCard()
    }

    private func controlGroup(step: WorkoutStep, isResting: Bool, isComplete: Bool, countdown: Int, date: Date) -> some View {
        VStack(spacing: 10) {
            controlButton(isComplete: isComplete, countdown: countdown)

            if countdown == 0, !isResting, !isComplete, let key = currentStopwatchKey(for: step) {
                stopwatchControl(for: key, at: date)
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
                Image(systemName: isComplete ? "checkmark" : countdown > 0 ? "xmark" : (startedAt == nil ? "play.fill" : "pause.fill"))
                Text(
                    isComplete
                        ? "Log session"
                        : countdown > 0
                            ? "Cancel countdown"
                            : (startedAt == nil && WorkoutSessionPolicy.isFirstStart(routineStartedAt: routineStartedAt) ? "Start routine" : (startedAt == nil ? "Resume" : "Pause"))
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

    private func stopwatchControl(for key: WorkoutActivitySegmentKey, at date: Date) -> some View {
        let stopwatch = stopwatches[key] ?? WorkoutStopwatch()
        let elapsed = stopwatch.elapsed(at: date) ?? 0
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
                toggleStopwatch(for: key, at: Date())
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
		if let startedAt {
			if startedAt > Date() {
				cancelCountdown()
				return
				}
				let now = Date()
				recorder.pause(at: currentElapsed(at: now))
				pausedElapsed += now.timeIntervalSince(startedAt)
				self.startedAt = nil
				pauseStopwatches(at: now)
				audioCoach.stop()
		} else if needsWorkoutPreparation {
			showsWorkoutPreparation = true
		} else {
            let now = Date()
            let isFirstStart = WorkoutSessionPolicy.isFirstStart(routineStartedAt: routineStartedAt)
            let start = WorkoutSessionPolicy.runStartDate(routineStartedAt: routineStartedAt, now: now)
            if isFirstStart {
                routineStartedAt = start
                motherboardMeasurementCollector.reset()
            }
            startedAt = start
        }
    }

    private func cancelCountdown() {
        startedAt = nil
        routineStartedAt = nil
		audioCoach.stop()
    }

	private func endSession() {
	        interruptRecorderIfNeeded()
	        finalizeAllStopwatches(at: Date())
	        startedAt = nil
		audioCoach.stop()
        dismiss()
    }

	private func pauseForInterruption() {
		pauseStopwatches(at: Date())
		guard let startedAt else {
			audioCoach.stop()
			return
		}
		if startedAt > Date() {
			cancelCountdown()
			return
		}

		let now = Date()
		recorder.pause(at: currentElapsed(at: now))
		pausedElapsed += now.timeIntervalSince(startedAt)
		self.startedAt = nil
		audioCoach.stop()
	}

	private func completeSession() {
		let loggedAt = Date()
		finalizeAllStopwatches(at: loggedAt)
		completedStopwatchDurations = stopwatches.reduce(into: [WorkoutActivitySegmentKey: TimeInterval]()) { result, entry in
			guard entry.value.hasStarted, let elapsed = entry.value.elapsed(at: loggedAt) else { return }
			result[entry.key] = elapsed
		}
		finalizeRoutine()
		if let completedSession {
			summarySession = completedSession
		}
		audioCoach.stop()
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

	private func consume(_ measurement: MotherboardMeasurement) {
		guard let startedAt,
			  startedAt <= measurement.timestamp,
			  countdownRemaining(at: measurement.timestamp) == 0 else { return }

		let elapsed = currentElapsed(at: measurement.timestamp)
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

	private func capture(_ measurement: MotherboardMeasurement) {
		motherboardMeasurementCollector.capture(
			measurement,
			startedAt: startedAt,
			countdownRemaining: countdownRemaining(at: measurement.timestamp),
			workoutElapsed: currentElapsed(at: measurement.timestamp),
			planDuration: plan.duration
		)
	}

	private func finalizeRoutine() {
		guard !didComplete else { return }
		didComplete = true
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
		let startDate = routineStartedAt ?? recordedAt.addingTimeInterval(-plan.duration)
		let endDate = WorkoutSessionPolicy.completedWorkoutInterval(
			sessionStartedAt: startDate,
			planDuration: plan.duration,
			loggedAt: recordedAt
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
			bodyweightKGF: bodyweightKGF,
			motherboardMeasurements: motherboardMeasurementCollector.measurements
		)
		completedSession = session
		summarySession = session
	}

	private func configureRecorder() {
		guard startedAt == nil, pausedElapsed == 0, !didComplete else { return }
		recorder = MotherboardWorkoutRecorder(configuration: .init(
			thresholdKGF: motherboardSettingsStore.thresholdKGF
		))
	}

	private var needsWorkoutPreparation: Bool {
		MotherboardWorkoutPreparation.requiresPreparation(
			isInitialStart: startedAt == nil && pausedElapsed == 0 && !didCompleteWorkoutPreparation,
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
		startedAt = nil
		audioCoach.stop()
		dismiss()
	}

	private func interruptRecorderForSensorLoss() {
		let now = Date()
		guard let startedAt,
			  startedAt <= now,
			  !didComplete else { return }

		let elapsed = currentElapsed(at: now)
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
		let now = Date()
		let hasStartedActiveWork = startedAt.map { $0 <= now } ?? false
		guard !didComplete, !didInterruptRecorder, hasStartedActiveWork || pausedElapsed > 0 else { return }
		recorder.interrupt(at: currentElapsed(at: now))
		didInterruptRecorder = true
	}

    private func currentElapsed(at date: Date) -> TimeInterval {
        let activeElapsed = startedAt.map { max(0, date.timeIntervalSince($0)) } ?? 0
        return min(plan.duration, pausedElapsed + max(0, activeElapsed))
    }

    private func countdownRemaining(at date: Date) -> Int {
        guard let startedAt, pausedElapsed == 0, startedAt > date else { return 0 }
        return max(1, Int(ceil(startedAt.timeIntervalSince(date))))
    }

    private func step(at elapsed: TimeInterval) -> WorkoutStep {
        timeline.step(at: elapsed) ?? plan.steps.last ?? PlanCatalog.metoliusTenMinute.steps[0]
    }

    private func elapsedInStep(at elapsed: TimeInterval) -> TimeInterval {
        timeline.elapsedInStep(at: elapsed)
    }

    private var canNavigate: Bool {
        let now = Date()
        return routineStartedAt != nil
            && countdownRemaining(at: now) == 0
            && currentElapsed(at: now) < plan.duration
    }

    private func seek(to targetElapsed: TimeInterval) {
        let target = min(max(0, targetElapsed), plan.duration)
        pausedElapsed = target
        if startedAt != nil {
            startedAt = Date()
        }
        audioCoach.stop()
    }

    private func jump(to step: WorkoutStep) {
        guard canNavigate else { return }

        let elapsed = currentElapsed(at: Date())
        guard let target = timeline.selectionTarget(for: step.id, at: elapsed) else { return }
		finalizeCurrentStopwatch(at: Date())
        seek(to: target)
    }

    private func skipCurrentStep() {
        guard canNavigate else { return }

        let elapsed = currentElapsed(at: Date())
        guard let target = timeline.skipTarget(from: elapsed) else { return }
		finalizeCurrentStopwatch(at: Date())
        seek(to: target)
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

	private func toggleStopwatch(for key: WorkoutActivitySegmentKey, at date: Date) {
		guard var stopwatch = stopwatches[key], !stopwatch.isFinalized else { return }
		if stopwatch.isRunning {
			stopwatch.pause(at: date)
		} else {
			stopwatch.start(at: date)
		}
		stopwatches[key] = stopwatch
	}

	private func pauseStopwatches(at date: Date) {
		for key in stopwatches.keys {
			guard var stopwatch = stopwatches[key], stopwatch.isRunning else { continue }
			stopwatch.pause(at: date)
			stopwatches[key] = stopwatch
		}
	}

	private func finalizeCurrentStopwatch(at date: Date) {
		let elapsed = currentElapsed(at: date)
		let step = step(at: elapsed)
		guard let key = currentStopwatchKey(for: step) else { return }
		WorkoutStopwatchLifecycle.finalizeStopwatch(for: key, at: date, in: &stopwatches)
	}

	private func finalizeStopwatches(for stepID: String, at date: Date) {
		WorkoutStopwatchLifecycle.finalizeStopwatches(for: stepID, at: date, in: &stopwatches)
	}

	private func finalizeAllStopwatches(at date: Date) {
		for key in stopwatches.keys {
			guard var stopwatch = stopwatches[key], !stopwatch.isFinalized else { continue }
			stopwatch.stop(at: date)
			stopwatches[key] = stopwatch
		}
	}

    private func isRestInterval(step: WorkoutStep, stepElapsed: TimeInterval) -> Bool {
        step.hasRestInterval && stepElapsed >= step.activeDuration
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
		isResting: Bool,
		isComplete: Bool
	) -> WorkoutAudioMoment? {
		guard startedAt != nil else { return nil }

		if countdown > 0 {
			return WorkoutAudioMoment(
				key: "initial-\(countdown)",
				phrase: "\(countdown)"
			)
		}

		if isComplete {
			return WorkoutAudioMoment(
				key: "session-complete",
				phrase: "Session complete"
			)
		}

		let segmentName = isResting ? "rest" : "active"
		let segmentElapsed = isResting
			? max(0, stepElapsed - step.activeDuration)
			: stepElapsed
		let segmentDuration = isResting ? step.restDuration : step.activeDuration

		if segmentElapsed < 0.55 {
			let phrase: String
			if segmentDuration <= 3 {
				phrase = isResting ? "Rest. 3, 2, 1" : "Hang. 3, 2, 1"
			} else {
				phrase = isResting ? "Rest" : spokenStartPhrase(for: step)
			}
			return WorkoutAudioMoment(
				key: "\(step.id)-\(segmentName)-start",
				phrase: phrase
			)
		}

		let secondsRemaining = Int(
			ceil(intervalRemaining(step: step, stepElapsed: stepElapsed))
		)
		if segmentDuration > 3, (1...3).contains(secondsRemaining) {
			return WorkoutAudioMoment(
				key: "\(step.id)-\(segmentName)-\(secondsRemaining)",
				phrase: "\(secondsRemaining)"
			)
		}

		return nil
	}

	private func spokenStartPhrase(for step: WorkoutStep) -> String {
		if step.timedWorkDuration == nil, step.phase != .rest {
			return "Begin minute \(step.number). \(step.title)"
		}

		switch step.phase {
		case .hang:
			return "Hang. \(step.title)"
		case .warmUp:
			return "Begin warm up. \(step.title)"
		case .pull:
			return "Begin. \(step.title)"
		case .coolDown:
			return "Begin cool down. \(step.title)"
		case .rest:
			return "Rest"
		}
	}
}

struct ProgressDashboardView: View {
    @EnvironmentObject private var store: AppStore
    @EnvironmentObject private var motherboardBluetoothService: MotherboardBluetoothService
    @EnvironmentObject private var motherboardSettingsStore: MotherboardSettingsStore
    @Environment(\.openURL) private var openURL
	@Environment(\.scenePhase) private var scenePhase
	@State private var didRequestHealthReview = false

    var body: some View {
        NavigationStack {
            ScrollView(showsIndicators: false) {
                VStack(alignment: .leading, spacing: 21) {
                    VStack(alignment: .leading, spacing: 6) {
                        SectionLabel(title: "Keep showing up")
                        Text("Your progress.")
                            .font(.system(size: 31, weight: .bold, design: .rounded))
                            .foregroundStyle(Color.hangInk)
                        Text("Small, consistent sessions build durable finger strength.")
                            .font(.system(size: 15, weight: .medium, design: .rounded))
                            .foregroundStyle(Color.hangMuted)
                    }

                    streakCard
					sessionHistoryCard
                    boardInfo
                    MotherboardCard(
                        service: motherboardBluetoothService,
                        settings: motherboardSettingsStore
                    )
                    healthCard
                    recoveryCard
                }
                .padding(.horizontal, 20)
                .padding(.top, 18)
                .padding(.bottom, 30)
            }
            .background(Color.hangBackground)
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    NavigationLink {
                        MotherboardSettingsView(
                            service: motherboardBluetoothService,
                            settings: motherboardSettingsStore
                        )
                    } label: {
                        Image(systemName: "gearshape")
                    }
                    .accessibilityLabel("Motherboard settings")
                }
            }
        }
		.onAppear {
			store.refreshHealthAuthorization()
			#if DEBUG
			if ProcessInfo.processInfo.environment["HANGTEN_REVIEW_REQUEST_HEALTH"] == "1",
			   !didRequestHealthReview {
				didRequestHealthReview = true
				DispatchQueue.main.asyncAfter(deadline: .now() + 0.6) {
					store.requestHealthAuthorization()
				}
			}
			#endif
		}
		.onChange(of: scenePhase) { _, phase in
			if phase == .active {
				store.refreshHealthAuthorization()
			}
		}
    }

    private var streakCard: some View {
        HStack(spacing: 17) {
            ZStack {
                Circle()
                    .stroke(Color.hangGreen.opacity(0.25), lineWidth: 10)
                Circle()
                    .trim(from: 0, to: store.sessionsCompleted == 0 ? 0.05 : 0.68)
                    .stroke(Color.hangGreenDark, style: StrokeStyle(lineWidth: 10, lineCap: .round))
                    .rotationEffect(.degrees(-90))
                Text("\(store.sessionsCompleted)")
                    .font(.system(size: 25, weight: .heavy, design: .rounded))
                    .foregroundStyle(Color.hangInk)
            }
            .frame(width: 88, height: 88)

            VStack(alignment: .leading, spacing: 6) {
                SectionLabel(title: "Sessions logged")
                Text(store.sessionsCompleted == 0 ? "Your first one is waiting." : "You’re building momentum.")
                    .font(.system(size: 18, weight: .bold, design: .rounded))
                    .foregroundStyle(Color.hangInk)
                Text(store.lastSessionTitle ?? "Start with the Metolius sequence.")
                    .font(.system(size: 13, weight: .medium, design: .rounded))
                    .foregroundStyle(Color.hangMuted)
                    .lineLimit(2)
            }
        }
        .hangCard()
    }

	private var sessionHistoryCard: some View {
		VStack(alignment: .leading, spacing: 10) {
			NavigationLink {
				WorkoutSessionHistoryView(
					sessions: store.sessionHistory,
					unit: motherboardSettingsStore.forceUnit
				)
			} label: {
				HStack(spacing: 14) {
					Image(systemName: "clock.arrow.circlepath")
						.font(.system(size: 18, weight: .bold))
						.foregroundStyle(Color.hangGreenDark)
						.frame(width: 36, height: 36)
						.background(Color.hangGreen.opacity(0.22), in: RoundedRectangle(cornerRadius: 11, style: .continuous))

					VStack(alignment: .leading, spacing: 3) {
						Text("Session history")
							.font(.system(size: 15, weight: .bold, design: .rounded))
							.foregroundStyle(Color.hangInk)
						Text(sessionHistoryDetail)
							.font(.system(size: 12, weight: .medium, design: .rounded))
							.foregroundStyle(Color.hangMuted)
							.lineLimit(1)
					}
					Spacer()
					Image(systemName: "chevron.right")
						.font(.system(size: 12, weight: .bold))
						.foregroundStyle(Color.hangMuted)
				}
			}
			.buttonStyle(.plain)

			if let error = store.sessionPersistenceError {
				Label(error, systemImage: "exclamationmark.triangle.fill")
					.font(.system(size: 12, weight: .semibold, design: .rounded))
					.foregroundStyle(Color.holdActive)
					.fixedSize(horizontal: false, vertical: true)
			}
		}
		.hangCard()
	}

	private var sessionHistoryDetail: String {
		guard let latest = store.sessionHistory.first else {
			return "Saved sessions will appear here."
		}
		return "\(store.sessionHistory.count) saved · Latest \(latest.recordedAt.formatted(date: .abbreviated, time: .omitted))"
	}

    private var boardInfo: some View {
        VStack(alignment: .leading, spacing: 14) {
            SectionLabel(title: "Current setup")
            HStack {
                Image(systemName: "rectangle.portrait.fill")
                    .font(.system(size: 17, weight: .bold))
                    .foregroundStyle(Color.hangGreenDark)
                    .frame(width: 34, height: 34)
                    .background(Color.hangGreen.opacity(0.22), in: RoundedRectangle(cornerRadius: 10, style: .continuous))
                VStack(alignment: .leading, spacing: 3) {
                    Text(store.selectedBoard.name)
                        .font(.system(size: 15, weight: .bold, design: .rounded))
                        .foregroundStyle(Color.hangInk)
                    Text(store.selectedBoard.dimensions)
                        .font(.system(size: 12, weight: .medium, design: .rounded))
                        .foregroundStyle(Color.hangMuted)
                }
                Spacer()
                Link(destination: store.selectedBoard.productURL) {
                    Image(systemName: "arrow.up.right")
                        .font(.system(size: 13, weight: .bold))
                        .foregroundStyle(Color.hangGreenDark)
                }
            }
        }
        .hangCard()
    }

    private var recoveryCard: some View {
        HStack(alignment: .top, spacing: 12) {
            Image(systemName: "moon.stars.fill")
                .font(.system(size: 17, weight: .bold))
                .foregroundStyle(Color.coolDownPurple)
            VStack(alignment: .leading, spacing: 6) {
                Text("Recovery matters")
                    .font(.system(size: 15, weight: .bold, design: .rounded))
                    .foregroundStyle(Color.hangInk)
                Text("Train only when you feel recovered. If your warm-up feels unusually hard, take the rest day.")
                    .font(.system(size: 13, weight: .medium, design: .rounded))
                    .foregroundStyle(Color.hangMuted)
                    .fixedSize(horizontal: false, vertical: true)
            }
        }
        .padding(16)
        .background(Color.coolDownPurple.opacity(0.11), in: RoundedRectangle(cornerRadius: 18, style: .continuous))
    }

    private var healthCard: some View {
		VStack(alignment: .leading, spacing: 12) {
			HStack(alignment: .top, spacing: 12) {
				Image(systemName: "heart.text.square.fill")
					.font(.system(size: 18, weight: .bold))
					.foregroundStyle(Color.holdActiveDeep)
					.frame(width: 34, height: 34)
					.background(Color.holdActive.opacity(0.12), in: RoundedRectangle(cornerRadius: 10, style: .continuous))

				VStack(alignment: .leading, spacing: 5) {
					HStack {
						Text("Apple Health")
							.font(.system(size: 15, weight: .bold, design: .rounded))
							.foregroundStyle(Color.hangInk)
						Spacer()
						Pill(
							title: store.healthAuthorizationState.statusLabel,
							tint: healthStatusTint,
							fill: healthStatusTint.opacity(0.12)
						)
					}

					Text(store.healthAuthorizationState.detail)
						.font(.system(size: 13, weight: .medium, design: .rounded))
						.foregroundStyle(Color.hangMuted)
						.fixedSize(horizontal: false, vertical: true)
				}
			}

			if let healthAuthorizationError = store.healthAuthorizationError {
				Text(healthAuthorizationError)
					.font(.system(size: 12, weight: .semibold, design: .rounded))
					.foregroundStyle(Color.holdActiveDeep)
			}

			if store.healthAuthorizationState == .notDetermined ||
				store.healthAuthorizationState == .denied {
				Button(action: handleHealthAuthorization) {
					HStack {
						Image(systemName: store.healthAuthorizationState == .denied ? "gear" : "heart.fill")
						Text(store.healthAuthorizationState == .denied ? "Open app settings" : "Connect Apple Health")
						Spacer()
						Image(systemName: "arrow.right")
					}
					.font(.system(size: 14, weight: .bold, design: .rounded))
					.foregroundStyle(Color.hangInk)
					.padding(.horizontal, 14)
					.padding(.vertical, 12)
					.background(Color.hangCream, in: RoundedRectangle(cornerRadius: 13, style: .continuous))
				}
				.buttonStyle(.plain)
			}
		}
		.padding(16)
		.background(Color.holdActive.opacity(0.08), in: RoundedRectangle(cornerRadius: 18, style: .continuous))
    }

	private var healthStatusTint: Color {
		switch store.healthAuthorizationState {
		case .authorized:
			.hangGreenDark
		case .denied:
			.holdActiveDeep
		case .notDetermined, .unavailable:
			.hangMuted
		}
	}

	private func handleHealthAuthorization() {
		if store.healthAuthorizationState == .denied,
		   let settingsURL = URL(string: UIApplication.openSettingsURLString) {
			openURL(settingsURL)
		} else {
			store.requestHealthAuthorization()
		}
	}
}
