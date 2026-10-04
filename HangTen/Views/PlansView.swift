import SwiftUI

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
                    VStack(alignment: .leading, spacing: 12) {
                        currentBoardControl

                        Button {
                            isCreatingRoutine = true
                        } label: {
                            Label("Create routine", systemImage: "plus")
                        }
                        .buttonStyle(.bordered)
                        .controlSize(.large)
                        .tint(.hangGreenDark)
                        .accessibilityIdentifier("customRoutine.create")

                        if let persistenceError = store.customRoutinePersistenceError {
                            HStack(alignment: .top, spacing: 10) {
                                Image(systemName: "exclamationmark.triangle.fill")
                                    .foregroundStyle(.orange)
                                VStack(alignment: .leading, spacing: 2) {
                                    Text("Some custom routines are unavailable")
                                        .font(.system(.subheadline, design: .rounded, weight: .bold))
                                        .foregroundStyle(Color.hangInk)
                                    Text(persistenceError)
                                        .font(.system(.caption, design: .rounded, weight: .medium))
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
                            Text("No routines are available for \(store.selectedBoard.name).")
                                .font(.system(.subheadline, design: .rounded, weight: .semibold))
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
                                    isFavorite: store.isFavorite(plan),
                                    isIncompatible: store.isIncompatible(plan, on: store.selectedBoard)
                                ) {
                                    store.toggleFavorite(plan)
                                }
                            }
                        }
                    }
                }
                .padding(.horizontal, 20)
                .padding(.top, 18)
                .padding(.bottom, 30)
            }
            .background(Color.hangBackground)
            .navigationTitle("Plans")
            .navigationBarTitleDisplayMode(.inline)
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
                        .font(.system(.caption, design: .rounded, weight: .semibold))
                        .foregroundStyle(Color.hangMuted)
                    Text(store.selectedBoard.name)
                        .font(.system(.subheadline, design: .rounded, weight: .bold))
                        .foregroundStyle(Color.hangInk)
                }
                Spacer()
                Image(systemName: "chevron.right")
                    .font(.system(.footnote, design: .rounded, weight: .bold))
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
        let visibleFacets = PlanFilterPresentationContent.visibleFacets(for: options)

        return ScrollView(.horizontal, showsIndicators: false) {
            HStack(spacing: 8) {
                if visibleFacets.contains(.difficulty) {
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

                if visibleFacets.contains(.category) {
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

                if visibleFacets.contains(.tags) {
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

                if !filters.isEmpty {
                    Button("Clear") {
                        filters.clear()
                    }
                    .font(.system(.footnote, design: .rounded, weight: .bold))
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
        .font(.system(.footnote, design: .rounded, weight: .bold))
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

}

private struct NoMatchingPlansCard: View {
    let onClear: () -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            Text("No routines match these filters")
                .font(.system(.callout, design: .rounded, weight: .bold))
                .foregroundStyle(Color.hangInk)
            Button("Clear filters", action: onClear)
                .font(.system(.footnote, design: .rounded, weight: .bold))
                .foregroundStyle(Color.hangGreenDark)
        }
        .hangCard()
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
