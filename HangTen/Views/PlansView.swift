import SwiftUI
import UIKit

extension Color {
    static var workoutBrowserAccent: Color {
        Color(uiColor: UIColor { traits in
            traits.userInterfaceStyle == .dark
                ? UIColor(red: 0.65, green: 0.85, blue: 0.55, alpha: 1)
                : UIColor(red: 0.235, green: 0.405, blue: 0.240, alpha: 1)
        })
    }

    fileprivate static var workoutBrowserButtonText: Color {
        Color(uiColor: UIColor { traits in
            traits.userInterfaceStyle == .dark ? .black : .white
        })
    }
}

private enum WorkoutBrowserDestination: Hashable {
    case all
    case myRoutines
    case focus(WorkoutFocus)

    var title: String {
        switch self {
        case .all: "All workouts"
        case .myRoutines: "My routines"
        case .focus(let focus): focus.title
        }
    }
}

struct PlansView: View {
    @EnvironmentObject private var store: AppStore
    @Environment(\.dynamicTypeSize) private var dynamicTypeSize
    @State private var search = ""
    @State private var isCreatingRoutine = false
    // periphery:ignore - NavigationStack reads and writes the projected $path binding.
    @State private var path: [WorkoutBrowserDestination] = {
        #if DEBUG
        let environment = ProcessInfo.processInfo.environment
        if environment["HANGTEN_REVIEW_CHOOSER_MY_ROUTINES"] == "1" { return [.myRoutines] }
        if environment["HANGTEN_REVIEW_CHOOSER_RESULTS"] == "1"
            || environment["HANGTEN_REVIEW_CHOOSER_FILTERS"] == "1" {
            return [.all]
        }
        #endif
        return []
    }()

    private var availableFocuses: [WorkoutFocus] {
        WorkoutFocus.allCases.filter { focus in
            store.plans.contains {
                store.metadata(for: $0).focus == focus
                    && !store.isIncompatible($0, on: store.selectedBoard)
            }
        }
    }

    var body: some View {
        NavigationStack(path: $path) {
            List {
                Section {
                    NavigationLink {
                        BoardPickerView()
                    } label: {
                        if dynamicTypeSize.isAccessibilitySize {
                            boardLabel
                        } else {
                            Label { boardLabel } icon: {
                                Image(systemName: "rectangle.portrait.fill")
                                    .foregroundStyle(Color.workoutBrowserAccent)
                            }
                        }
                    }
                    .accessibilityIdentifier("plans.changeBoard")
                }

                if search.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
                    if !availableFocuses.isEmpty {
                        Section("Browse by focus") {
                            ForEach(availableFocuses) { focus in
                                NavigationLink(value: WorkoutBrowserDestination.focus(focus)) {
                                    VStack(alignment: .leading, spacing: 4) {
                                        Text(focus.title).font(.headline)
                                        if focus == .mixed {
                                            Text(focus.subtitle).font(.subheadline).foregroundStyle(.secondary)
                                        }
                                    }
                                    .padding(.vertical, 5)
                                }
                                .accessibilityIdentifier("workouts.focus.\(focus.rawValue)")
                            }
                        }
                    }
                    Section {
                        NavigationLink("All workouts", value: WorkoutBrowserDestination.all)
                            .accessibilityIdentifier("workouts.all")
                        NavigationLink("My routines", value: WorkoutBrowserDestination.myRoutines)
                            .accessibilityIdentifier("workouts.myRoutines")
                        Button { isCreatingRoutine = true } label: {
                            Label("Create routine", systemImage: "plus")
                        }
                        .accessibilityIdentifier("customRoutine.create")
                    }
                    if !store.favoritePlans.isEmpty {
                        Section("Favorites") {
                            ForEach(store.favoritePlans) { plan in
                                WorkoutBrowserRow(plan: plan)
                            }
                        }
                    }
                } else {
                    Section("Search results") {
                        let matches = store.plans.filter {
                            $0.matchesWorkoutSearch(search, metadata: store.metadata(for: $0))
                        }
                        if matches.isEmpty {
                            WorkoutBrowserEmptyView(isSearching: true)
                        } else {
                            ForEach(matches) { plan in WorkoutBrowserRow(plan: plan) }
                        }
                    }
                }
                if let error = store.customRoutinePersistenceError {
                    Section {
                        Label {
                            VStack(alignment: .leading, spacing: 4) {
                                Text("Some custom routines are unavailable").font(.headline)
                                Text(error).font(.subheadline).foregroundStyle(.secondary)
                            }
                        } icon: {
                            Image(systemName: "exclamationmark.triangle.fill").foregroundStyle(.orange)
                        }
                        .accessibilityIdentifier("customRoutine.persistenceError")
                    }
                }
            }
            .tint(.workoutBrowserAccent)
            .navigationTitle("Plans")
            .searchable(text: $search, placement: .navigationBarDrawer(displayMode: .always), prompt: "Search workouts")
            .navigationDestination(for: WorkoutBrowserDestination.self) { destination in
                WorkoutBrowserResultsView(destination: destination)
            }
            .sheet(isPresented: $isCreatingRoutine) {
                CustomRoutineEditorView(
                    draft: CustomRoutineDraft(createWith: .boardSpecific(boardID: store.selectedBoard.id)),
                    onSave: store.saveCustomRoutine
                )
            }
        }
    }
    private var boardLabel: some View {
        VStack(alignment: .leading, spacing: 3) {
            Text("Training on").font(.caption).foregroundStyle(.secondary)
            Text(store.selectedBoard.name).font(.headline)
                .fixedSize(horizontal: false, vertical: true)
        }
    }

}

private struct WorkoutBrowserResultsView: View {
    @EnvironmentObject private var store: AppStore
    let destination: WorkoutBrowserDestination
    @State private var filters = WorkoutBrowserFilters()
    @State private var search = ""
    @State private var showsFilters = false
    @State private var isCreatingRoutine = false

    private var candidates: [TrainingPlan] {
        store.plans.filter { plan in
            switch destination {
            case .all: true
            case .myRoutines: store.isCustom(plan)
            case .focus(let focus):
                store.metadata(for: plan).focus == focus
                    && !store.isIncompatible(plan, on: store.selectedBoard)
            }
        }
    }

    private var results: [TrainingPlan] {
        candidates.filter {
            filters.matches($0, metadata: store.metadata(for: $0))
                && $0.matchesWorkoutSearch(search, metadata: store.metadata(for: $0))
        }
    }

    var body: some View {
        List {
            if !filters.isEmpty {
                Section {
                    appliedFilters
                }
            }
            Section {
                if destination == .myRoutines && candidates.isEmpty && search.isEmpty && filters.isEmpty {
                    VStack(alignment: .leading, spacing: 8) {
                        Text(store.customPlans.isEmpty ? "Create your first routine" : "No routines for this board")
                            .font(.headline)
                        Text("Create a routine for \(store.selectedBoard.name) with the exercises you want to practice.")
                            .font(.subheadline).foregroundStyle(.secondary)
                    }
                    .padding(.vertical, 8)
                    Button { isCreatingRoutine = true } label: {
                        Label("Create routine", systemImage: "plus")
                    }
                    .accessibilityIdentifier("customRoutine.create")
                } else if results.isEmpty {
                    WorkoutBrowserEmptyView(isSearching: !search.isEmpty)
                    if !filters.isEmpty {
                        Button("Clear filters") { filters.clear() }
                    }
                } else {
                    ForEach(results) { plan in WorkoutBrowserRow(plan: plan) }
                }
            } header: {
                Text("\(results.count) \(results.count == 1 ? "workout" : "workouts")")
            }
        }
        .tint(.workoutBrowserAccent)
        .navigationTitle(destination.title)
        .navigationBarTitleDisplayMode(.large)
        .searchable(text: $search, placement: .navigationBarDrawer(displayMode: .always), prompt: "Search workouts")
        .toolbar {
            ToolbarItem(placement: .topBarTrailing) {
                Button { showsFilters = true } label: {
                    Label(filters.isEmpty ? "Filter" : "Filter (\(filters.activeFacetCount))", systemImage: "line.3.horizontal.decrease")
                        .foregroundStyle(Color.workoutBrowserAccent)
                }
                .accessibilityIdentifier("workouts.filter")
            }
        }
        .sheet(isPresented: $showsFilters) {
            WorkoutBrowserFilterSheet(
                filters: filters,
                plans: candidates,
                metadata: { store.metadata(for: $0) },
                search: search
            ) { filters = $0 }
        }
        .sheet(isPresented: $isCreatingRoutine) {
            CustomRoutineEditorView(
                draft: CustomRoutineDraft(createWith: .boardSpecific(boardID: store.selectedBoard.id)),
                onSave: store.saveCustomRoutine
            )
        }
        .onAppear {
            #if DEBUG
            if ProcessInfo.processInfo.environment["HANGTEN_REVIEW_CHOOSER_FILTERS"] == "1" {
                showsFilters = true
            }
            #endif
        }
    }

    private var appliedFilters: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("Applied filters").font(.subheadline).foregroundStyle(.secondary)
            // Vertical wrapping remains readable at accessibility text sizes.
            if filters.duration != .any {
                removeFilter(filters.duration.title) { filters.duration = .any }
            }
            ForEach(WorkoutExercise.allCases.filter { filters.exercises.contains($0) }) { exercise in
                removeFilter(exercise.title) { filters.exercises.remove(exercise) }
            }
            ForEach(filters.levels.sorted(), id: \.self) { level in
                removeFilter(level) { filters.levels.remove(level) }
            }
            Button("Clear all") { filters.clear() }.font(.subheadline)
        }
        .padding(.vertical, 4)
    }

    private func removeFilter(_ title: String, action: @escaping () -> Void) -> some View {
        Button(action: action) {
            Label(title, systemImage: "xmark.circle.fill")
                .font(.subheadline)
                .padding(.horizontal, 12)
                .frame(minHeight: 44)
                .background(Color.workoutBrowserAccent.opacity(0.12), in: Capsule())
        }
        .buttonStyle(.plain)
        .foregroundStyle(Color.workoutBrowserAccent)
        .accessibilityLabel("Remove filter: \(title)")
        .accessibilityIdentifier("workouts.removeFilter.\(title)")
    }
}

private struct WorkoutBrowserRow: View {
    @EnvironmentObject private var store: AppStore
    @Environment(\.dynamicTypeSize) private var dynamicTypeSize
    let plan: TrainingPlan

    var body: some View {
        let layout = dynamicTypeSize.isAccessibilitySize
            ? AnyLayout(VStackLayout(alignment: .leading, spacing: 4))
            : AnyLayout(HStackLayout(alignment: .top, spacing: 8))
        layout {
            NavigationLink {
                PlanDetailView(plan: plan)
            } label: {
                VStack(alignment: .leading, spacing: 6) {
                    Text(plan.title).font(.headline)
                    Text("\(plan.browserDurationLabel) · \(plan.level)")
                        .font(.subheadline).foregroundStyle(.secondary)
                    if store.isIncompatible(plan, on: store.selectedBoard) {
                        Label("Not on this board", systemImage: "exclamationmark.circle")
                            .font(.caption).foregroundStyle(.secondary)
                    }
                    if !plan.subtitle.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
                        Text(plan.subtitle).font(.subheadline).foregroundStyle(.secondary)
                    }
                    let exercises = WorkoutExercise.allCases.filter { plan.workoutExercises.contains($0) }
                    if !exercises.isEmpty {
                        Text(exercises.map(\.title).joined(separator: " · "))
                            .font(.caption).foregroundStyle(.secondary)
                    }
                }
                .frame(maxWidth: .infinity, alignment: .leading)
                .padding(.vertical, 6)
                .fixedSize(horizontal: false, vertical: true)
            }
            .accessibilityIdentifier("workouts.row.\(plan.id)")
            Button { store.toggleFavorite(plan) } label: {
                if dynamicTypeSize.isAccessibilitySize {
                    Label(store.isFavorite(plan) ? "Favorited" : "Favorite", systemImage: store.isFavorite(plan) ? "star.fill" : "star")
                        .font(.subheadline).frame(minHeight: 44)
                } else {
                    Image(systemName: store.isFavorite(plan) ? "star.fill" : "star")
                        .frame(minWidth: 44, minHeight: 44)
                }
            }
            .buttonStyle(.borderless)
            .accessibilityLabel("\(store.isFavorite(plan) ? "Remove" : "Add") \(plan.title) \(store.isFavorite(plan) ? "from" : "to") favorites")
        }
    }
}

private struct WorkoutBrowserEmptyView: View {
    var isSearching: Bool

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Label("No matching workouts", systemImage: "magnifyingglass").font(.headline)
            Text(isSearching ? "Try another search or adjust your filters." : "Try adjusting your filters or choosing another board.")
                .font(.subheadline).foregroundStyle(.secondary)
        }
        .padding(.vertical, 12)
    }
}

private struct WorkoutBrowserFilterSheet: View {
    @Environment(\.dynamicTypeSize) private var dynamicTypeSize
    @Environment(\.dismiss) private var dismiss
    @State private var draft: WorkoutBrowserFilters
    let plans: [TrainingPlan]
    let metadata: (TrainingPlan) -> PlanMetadata
    let search: String
    let onApply: (WorkoutBrowserFilters) -> Void

    init(filters: WorkoutBrowserFilters, plans: [TrainingPlan], metadata: @escaping (TrainingPlan) -> PlanMetadata, search: String, onApply: @escaping (WorkoutBrowserFilters) -> Void) {
        _draft = State(initialValue: filters)
        self.plans = plans
        self.metadata = metadata
        self.search = search
        self.onApply = onApply
    }

    private var matchingCount: Int {
        plans.filter { draft.matches($0, metadata: metadata($0)) && $0.matchesWorkoutSearch(search, metadata: metadata($0)) }.count
    }

    var body: some View {
        NavigationStack {
            List {
                Section("Duration") {
                    ForEach(WorkoutDurationFilter.allCases) { duration in
                        selectionRow(duration.title, selected: draft.duration == duration) {
                            draft.duration = duration
                        }
                    }
                }
                let availableExercises = WorkoutExercise.allCases.filter { exercise in
                    plans.contains { $0.workoutExercises.contains(exercise) } || draft.exercises.contains(exercise)
                }
                if !availableExercises.isEmpty {
                    Section {
                        ForEach(availableExercises) { exercise in
                            selectionRow(exercise.title, selected: draft.exercises.contains(exercise)) {
                                if !draft.exercises.insert(exercise).inserted { draft.exercises.remove(exercise) }
                            }
                        }
                    } header: { Text("Exercises") } footer: { Text("Matches any selected exercise.") }
                }
                let levels = Set(plans.map(\.level)).union(draft.levels).filter { !$0.isEmpty }.sorted {
                    let progression = ["entry", "beginner", "intermediate", "advanced"]
                    let lhs = progression.firstIndex(of: $0.lowercased()) ?? progression.count
                    let rhs = progression.firstIndex(of: $1.lowercased()) ?? progression.count
                    return lhs == rhs ? $0.localizedCaseInsensitiveCompare($1) == .orderedAscending : lhs < rhs
                }
                if !levels.isEmpty {
                    Section {
                        ForEach(levels, id: \.self) { level in
                            selectionRow(level, selected: draft.levels.contains(level)) {
                                if !draft.levels.insert(level).inserted { draft.levels.remove(level) }
                            }
                        }
                    } header: { Text("Difficulty") } footer: { Text("Matches any selected difficulty.") }
                }
                Section {
                    Button("Clear all") { draft.clear() }
                        .disabled(draft.isEmpty)
                }
            }
            .tint(.workoutBrowserAccent)
            .navigationTitle("Filter workouts")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") { dismiss() }.accessibilityIdentifier("workouts.filter.cancel")
                }
            }
            .safeAreaInset(edge: .bottom) {
                Button {
                    onApply(draft)
                    dismiss()
                } label: {
                    Text(dynamicTypeSize.isAccessibilitySize ? "Show" : "Show \(matchingCount) \(matchingCount == 1 ? "workout" : "workouts")")
                        .font(.headline)
                        .frame(maxWidth: .infinity, minHeight: 44)
                }
                .buttonStyle(.borderedProminent)
                .foregroundStyle(Color.workoutBrowserButtonText)
                .accessibilityIdentifier("workouts.filter.apply")
                .accessibilityLabel("Show workouts")
                .accessibilityValue("\(matchingCount) matching \(matchingCount == 1 ? "workout" : "workouts")")
                .padding()
                .background(.regularMaterial)
            }
        }
    }

    private func selectionRow(_ title: String, selected: Bool, action: @escaping () -> Void) -> some View {
        Button(action: action) {
            HStack {
                Text(title).foregroundStyle(.primary)
                Spacer()
                if selected { Image(systemName: "checkmark").foregroundStyle(Color.workoutBrowserAccent) }
            }
            .frame(minHeight: 32)
        }
        .accessibilityAddTraits(selected ? [.isSelected] : [])
        .accessibilityValue(selected ? "Selected" : "Not selected")
        .accessibilityIdentifier("workouts.filter.option.\(title)")
    }
}

private struct PlanCard: View {
    let plan: TrainingPlan
    var isIncompatible: Bool = false

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text(plan.title)
                .font(.system(.headline, design: .rounded))
                .foregroundStyle(Color.hangInk)
                .frame(maxWidth: .infinity, alignment: .leading)
                .padding(.trailing, 44)
                .fixedSize(horizontal: false, vertical: true)

            ViewThatFits(in: .horizontal) {
                HStack(spacing: 12) { metadata }
                    .fixedSize(horizontal: true, vertical: false)
                VStack(alignment: .leading, spacing: 8) { metadata }
            }

            if isIncompatible {
                Label("Missing required holds", systemImage: "exclamationmark.triangle")
                    .font(.system(.footnote, design: .rounded, weight: .semibold))
                    .foregroundStyle(Color.holdActiveDeep)
            }
        }
        .hangCard()
    }

    @ViewBuilder
    private var metadata: some View {
        Pill(title: plan.level, tint: .hangGreenDark, fill: Color.hangGreen.opacity(0.25))
        Label(plan.durationLabel, systemImage: "timer")
            .font(.system(.subheadline, design: .rounded, weight: .medium))
            .foregroundStyle(Color.hangMuted)
    }
}

struct FavoritePlanCard: View {
    let plan: TrainingPlan
    let isFavorite: Bool
    var isIncompatible: Bool = false
    let onToggle: () -> Void

    var body: some View {
        ZStack(alignment: .topTrailing) {
            NavigationLink(destination: PlanDetailView(plan: plan)) {
                PlanCard(plan: plan, isIncompatible: isIncompatible)
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
