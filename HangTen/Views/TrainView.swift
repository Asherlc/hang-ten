import SwiftUI

enum TrainReviewDestination: Hashable {
    case plan
    case settings
    case boardDetail
    case boardPicker

    static func initial(environment: [String: String]) -> Self? {
        #if DEBUG
        if environment["HANGTEN_REVIEW_PLAN"] == "1" {
            return .plan
        }
        if environment["HANGTEN_REVIEW_SETTINGS"] == "1"
            || environment["HANGTEN_REVIEW_HEALTH"] == "1"
            || environment["HANGTEN_REVIEW_MOTHERBOARD"] == "1" {
            return .settings
        }
        if environment["HANGTEN_REVIEW_BOARD_DETAIL"] == "1" {
            return .boardDetail
        }
        if environment["HANGTEN_REVIEW_BOARD_PICKER"] == "1" {
            return .boardPicker
        }
        #endif
        return nil
    }
}

struct TrainView: View {
    @EnvironmentObject private var store: AppStore
    @EnvironmentObject private var deepLinkManager: DeepLinkManager
    @Environment(\.verticalSizeClass) private var verticalSizeClass
    @Environment(\.dynamicTypeSize) private var dynamicTypeSize
    @State private var showsDeepLinkedBoardDetail = false
    @State private var showsDeepLinkedWorkout = false
    @State private var deepLinkedWorkoutPlan: TrainingPlan?
    private let onBrowsePlans: () -> Void
    // periphery:ignore - Navigation reads and writes the projected $reviewDestination binding.
    @State private var reviewDestination = TrainReviewDestination.initial(
        environment: ProcessInfo.processInfo.environment
    )
    @State private var showsFreeWorkout = false

    init(onBrowsePlans: @escaping () -> Void) {
        self.onBrowsePlans = onBrowsePlans
    }

    var body: some View {
        NavigationStack {
            ScrollView(showsIndicators: false) {
                VStack(alignment: .leading, spacing: 22) {
                    selectedBoardCard
                    freeWorkoutButton
                    favoritesSection
                }
                .padding(.horizontal, 20)
                .padding(.top, 18)
                .padding(.bottom, 30)
            }
            .background(Color.hangBackground)
            .navigationTitle("Train")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    NavigationLink {
                        AppSettingsView()
                    } label: {
                        Image(systemName: "gearshape")
                    }
                    .accessibilityLabel("Settings")
                    .accessibilityIdentifier("train.settings")
                }
            }
            .navigationDestination(item: $reviewDestination) { destination in
                switch destination {
                case .plan:
                    if let plan = reviewPlan {
                        PlanDetailView(plan: plan)
                    } else {
                        noCompatiblePlan
                    }
                case .settings:
                    AppSettingsView()
                case .boardDetail:
                    BoardDetailView(
                        board: store.selectedBoard,
                        initialHoldID: ProcessInfo.processInfo.environment["HANGTEN_REVIEW_BOARD_HOLD_ID"]
                    )
                case .boardPicker:
                    BoardPickerView()
                }
            }
            .navigationDestination(isPresented: $showsDeepLinkedBoardDetail) {
                BoardDetailView(board: store.selectedBoard, initialHoldID: deepLinkManager.pendingHoldID)
                    .onAppear { deepLinkManager.clearPending() }
            }
            .navigationDestination(isPresented: $showsDeepLinkedWorkout) {
                if let plan = deepLinkedWorkoutPlan {
                    WorkoutAccessGate(plan: plan)
                } else {
                    noCompatiblePlan
                }
            }
            .onChange(of: deepLinkManager.pendingBoardID, initial: true) { _, boardID in
                guard boardID != nil else { return }
                showsDeepLinkedBoardDetail = true
            }
            .onChange(of: deepLinkManager.pendingWorkoutPlanID, initial: true) { _, planID in
                guard let planID else { return }
                guard let plan = store.plans.first(where: { $0.id == planID })
                        ?? PlanCatalog.plan(id: planID) else {
                    deepLinkManager.clearPending()
                    return
                }
                if let boardID = plan.boardID,
                   let board = BoardCatalog.all.first(where: { $0.id == boardID }) {
                    store.selectBoard(board)
                }
                switch PlanStartAvailabilityPolicy.availability(
                    for: plan,
                    metadata: store.metadata(for: plan)
                ) {
                case .available:
                    break
                case .unavailable:
                    deepLinkManager.clearPending()
                    return
                }
                deepLinkedWorkoutPlan = plan
                showsDeepLinkedWorkout = true
                deepLinkManager.clearPending()
            }
            .sheet(isPresented: $showsFreeWorkout) {
                FreeWorkoutStartSheet(isPresented: $showsFreeWorkout)
                    .environmentObject(store)
            }
        }
    }

    private var reviewPlan: TrainingPlan? {
        store.featuredPlan
    }

    private var selectedBoardCard: some View {
        let isCompact = verticalSizeClass == .compact && !dynamicTypeSize.isAccessibilitySize
        let layout = isCompact
            ? AnyLayout(HStackLayout(alignment: .center, spacing: 20))
            : AnyLayout(VStackLayout(alignment: .leading, spacing: 12))
        return layout {
            BoardMapView(board: store.selectedBoard, maximumMapHeight: isCompact ? 72 : 80)
                .cardPreviewStyle()
                .frame(width: isCompact ? 220 : nil)

            VStack(alignment: .leading, spacing: 12) {
                VStack(alignment: .leading, spacing: 5) {
                    SectionLabel(title: "Your board")
                    Text(store.selectedBoard.name)
                        .font(.system(.title3, design: .rounded, weight: .bold))
                        .foregroundStyle(Color.hangInk)
                }

                ViewThatFits(in: .horizontal) {
                    HStack(spacing: 12) { boardActions }
                        .fixedSize(horizontal: true, vertical: false)
                    VStack(alignment: .leading, spacing: 8) { boardActions }
                }
                .buttonStyle(.bordered)
                .controlSize(.large)
                .font(.system(.subheadline, design: .rounded, weight: .semibold))
                .tint(.hangGreenDark)
            }
            .frame(maxWidth: .infinity, alignment: .leading)
            .layoutPriority(1)
        }
        .hangCard()
        .accessibilityElement(children: .contain)
        .accessibilityIdentifier("train.board")
    }

    @ViewBuilder
    private var boardActions: some View {
        NavigationLink("Change board") {
            BoardPickerView()
        }
        .accessibilityIdentifier("train.changeBoard")

        NavigationLink("View hold specs") {
            BoardDetailView(board: store.selectedBoard)
        }
        .accessibilityIdentifier("train.boardDetails")
    }

    private var freeWorkoutButton: some View {
        Button {
            showsFreeWorkout = true
        } label: {
            Label("Start free workout", systemImage: "plus")
                .frame(maxWidth: .infinity)
        }
        .buttonStyle(.borderedProminent)
        .controlSize(.large)
        .tint(.hangGreenDark)
        .accessibilityIdentifier("train.freeWorkout")
    }

    @ViewBuilder
    private var favoritesSection: some View {
        if store.favoritePlans.isEmpty {
            VStack(alignment: .leading, spacing: 17) {
                SectionLabel(title: "Favorites")
                Text("No favorites yet")
                    .font(.system(.headline, design: .rounded))
                    .foregroundStyle(Color.hangInk)
                Text("Star a plan to keep it handy here.")
                    .font(.system(.subheadline, design: .rounded))
                    .foregroundStyle(Color.hangMuted)
                Button("Browse plans", action: onBrowsePlans)
                    .buttonStyle(.bordered)
                    .controlSize(.large)
                    .tint(.hangGreenDark)
                    .accessibilityIdentifier("train.browsePlans")
            }
            .frame(maxWidth: .infinity, alignment: .leading)
            .hangCard()
        } else {
            VStack(alignment: .leading, spacing: 12) {
                SectionLabel(title: "Favorites")
                ForEach(store.favoritePlans) { plan in
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

    private var noCompatiblePlan: some View {
        VStack(alignment: .leading, spacing: 8) {
            SectionLabel(title: "No compatible routine")
            Text("No routines are available for this board.")
                .font(.system(.callout, design: .rounded, weight: .bold))
                .foregroundStyle(Color.hangInk)
            Text("Choose another board or browse plans.")
                .font(.system(.footnote, design: .rounded, weight: .medium))
                .foregroundStyle(Color.hangMuted)
        }
        .hangCard()
    }
}

struct BoardDetailView: View {
    let board: BoardRevision
    @EnvironmentObject private var store: AppStore
    @Environment(\.verticalSizeClass) private var verticalSizeClass
    @State private var selectedHoldID: String?
    @State private var selectedPositionID: String?
    @State private var showsReportProblem = false
    @State private var compactMetrics = BoardDetailCompactMetrics()

    private let compactContentSpacing: CGFloat = 10
    private let compactCardPadding: CGFloat = 8
    private let compactVerticalPadding: CGFloat = 8
    /// Segmented presentation picker height reserved above the map in `mapContent`.
    private let compactPresentationPickerHeight: CGFloat = 32

    private var isCompactHeight: Bool {
        verticalSizeClass == .compact
    }

    init(board: BoardRevision, initialHoldID: String? = nil) {
        self.board = board
        var resolvedHoldID = board.contacts.first(where: {
            board.defaultPresentation.containsContact(id: $0.id)
        })?.id
        // Select a specific hold with the deep link
        // `hangten://board/<boardID>/hold/<contactID>`; see DeepLinkManager.
        if let initialHoldID, board.contacts.contains(where: { $0.id == initialHoldID }) {
            resolvedHoldID = initialHoldID
        }
        _selectedHoldID = State(initialValue: resolvedHoldID)
    }

    private var selectedHold: PhysicalContact? {
        guard let selectedHoldID else { return nil }
        if let selectedPositionID,
           let configured = board.contacts(inPosition: selectedPositionID).first(where: { $0.id == selectedHoldID }) {
            return configured
        }
        return board.contacts.first { $0.id == selectedHoldID }
    }

    var body: some View {
        ScrollView(showsIndicators: false) {
            VStack(alignment: .leading, spacing: isCompactHeight ? compactContentSpacing : 20) {
                VStack(alignment: .leading, spacing: isCompactHeight ? 2 : 5) {
                    SectionLabel(title: board.manufacturer)
                    Text(board.name)
                        .font(.system(size: isCompactHeight ? 22 : 28, weight: .bold, design: .rounded))
                        .foregroundStyle(Color.hangInk)
                    Link(destination: board.productURL) {
                        Label("Product page", systemImage: "arrow.up.right")
                            .frame(minHeight: 44)
                            .contentShape(Rectangle())
                    }
                    .font(.system(.footnote, design: .rounded, weight: .medium))
                    .foregroundStyle(Color.hangGreenDark)
                }
                .overlay {
                    GeometryReader { summary in
                        Color.clear.preference(
                            key: BoardDetailCompactMetricsPreferenceKey.self,
                            value: BoardDetailCompactMetrics(summaryHeight: summary.size.height)
                        )
                    }
                    .allowsHitTesting(false)
                }

                BoardDetailMapView(
                    board: board,
                    selectedHoldID: $selectedHoldID,
                    selectedPositionID: $selectedPositionID,
                    maximumMapHeight: compactMaximumMapHeight,
                    selectedHoldContent: selectedHold.map { AnyView(selectedHoldCard($0)) }
                )
                .hangCard(padding: isCompactHeight ? compactCardPadding : 14)
            }
            .padding(.horizontal, isCompactHeight ? 12 : 20)
            .padding(.vertical, isCompactHeight ? compactVerticalPadding : 18)
        }
        .background(Color.hangBackground)
        .background {
            if isCompactHeight {
                GeometryReader { viewport in
                    Color.clear.preference(
                        key: BoardDetailCompactMetricsPreferenceKey.self,
                        value: BoardDetailCompactMetrics(viewportHeight: viewport.size.height)
                    )
                }
            }
        }
        .onPreferenceChange(BoardDetailCompactMetricsPreferenceKey.self) {
            compactMetrics = $0
        }
        .navigationTitle("Hold specs")
        .navigationBarTitleDisplayMode(.inline)
        .toolbar(isCompactHeight ? .hidden : .automatic, for: .tabBar)
        .toolbar {
            ToolbarItem(placement: .topBarTrailing) {
                Button {
                    showsReportProblem = true
                } label: {
                    Image(systemName: "exclamationmark.bubble")
                }
                .accessibilityLabel("Report a problem")
                .accessibilityIdentifier("boardDetail.reportProblem")
            }
        }
        .sheet(isPresented: $showsReportProblem) {
            ReportProblemView(
                source: .boardDetail,
                boardID: board.id,
                holdID: selectedHoldID
            )
            .environmentObject(store)
        }
        .accessibilityIdentifier("boardDetail.screen")
    }

    private var compactMaximumMapHeight: CGFloat? {
        guard isCompactHeight,
              compactMetrics.viewportHeight > 0,
              compactMetrics.summaryHeight > 0 else { return nil }
        let presentationPickerReserve = board.presentations.count > 1
            ? compactPresentationPickerHeight
            : 0
        return max(
            1,
            compactMetrics.viewportHeight
                - (compactVerticalPadding * 2)
                - compactMetrics.summaryHeight
                - compactContentSpacing
                // hangCard pads all sides; only the top inset sits above the map.
                // Bottom card padding is below scrollable selected-hold/legend content.
                - compactCardPadding
                - presentationPickerReserve
        )
    }

    private func selectedHoldCard(_ hold: PhysicalContact) -> some View {
        VStack(alignment: .leading, spacing: 14) {
            SectionLabel(title: "Selected hold", tint: .holdActiveDeep)
            Text(hold.name)
                .font(.system(.title3, design: .rounded, weight: .bold))
                .foregroundStyle(Color.hangInk)

            ForEach(BoardHoldSpecifications.entries(for: hold)) { specification in
                HStack(alignment: .firstTextBaseline, spacing: 16) {
                    Text(specification.label)
                        .font(.system(.footnote, design: .rounded, weight: .medium))
                        .foregroundStyle(Color.hangMuted)
                    Spacer()
                    Text(specification.value)
                        .font(.system(.subheadline, design: .rounded, weight: .bold))
                        .foregroundStyle(Color.hangInk)
                }
            }
        }
        .hangCard()
        .accessibilityElement(children: .contain)
        .accessibilityIdentifier("boardDetail.selectedHold.\(hold.id)")
    }
}

private struct BoardDetailCompactMetrics: Equatable {
    var viewportHeight: CGFloat = 0
    var summaryHeight: CGFloat = 0
}

private struct BoardDetailCompactMetricsPreferenceKey: PreferenceKey {
    static var defaultValue = BoardDetailCompactMetrics()

    static func reduce(
        value: inout BoardDetailCompactMetrics,
        nextValue: () -> BoardDetailCompactMetrics
    ) {
        let next = nextValue()
        if next.viewportHeight > 0 {
            value.viewportHeight = next.viewportHeight
        }
        if next.summaryHeight > 0 {
            value.summaryHeight = next.summaryHeight
        }
    }
}

struct BoardPickerView: View {
    @EnvironmentObject private var store: AppStore
    @Environment(\.dismiss) private var dismiss
    @Environment(\.dynamicTypeSize) private var dynamicTypeSize
    @State private var filters = BoardPickerFilters()
    @State private var favoritesOnly = false
    @State private var inspectedBoardID: String?
    @State private var isSearchPresented = false

    private var filteredBoards: [BoardRevision] {
        filters.filteredBoards(
            from: BoardCatalog.all,
            favoriteBoardIDs: store.favoriteBoardIDs
        ).filter { !favoritesOnly || store.isFavorite($0) }
    }

    private var manufacturerOptions: [String] {
        BoardPickerFilters.manufacturerOptions(from: BoardCatalog.all)
    }

    private var galleryColumns: [GridItem] {
        dynamicTypeSize.isAccessibilitySize
            ? [GridItem(.flexible())]
            : [GridItem(.adaptive(minimum: 160), spacing: 14)]
    }

    var body: some View {
        ScrollView(showsIndicators: false) {
            VStack(alignment: .leading, spacing: 20) {
                scopeControls

                if let manufacturer = filters.manufacturer {
                    Text(manufacturer)
                        .font(.system(.title3, design: .rounded, weight: .bold))
                        .foregroundStyle(Color.hangInk)
                }

                if filteredBoards.isEmpty {
                    emptyState
                } else {
                    gallery(filteredBoards)
                }
            }
            .padding(.horizontal, 20)
            .padding(.top, 12)
            .padding(.bottom, 30)
        }
        .background(Color.hangBackground)
        .navigationTitle("Choose board")
        .navigationBarTitleDisplayMode(.inline)
        .searchable(
            text: $filters.searchText,
            isPresented: $isSearchPresented,
            placement: .navigationBarDrawer(displayMode: .always),
            prompt: "Search boards"
        )
        .accessibilityIdentifier("boardPicker.search")
        .navigationDestination(item: $inspectedBoardID) { boardID in
            BoardDetailView(board: BoardCatalog.board(for: boardID))
        }
    }

    private var scopeControls: some View {
        HStack(spacing: 12) {
            Picker("Boards", selection: $favoritesOnly) {
                Text("All boards").tag(false)
                Text("Favorites").tag(true)
            }
            .pickerStyle(.segmented)
            .accessibilityIdentifier("boardPicker.scope")

            Menu {
                Picker("Manufacturer", selection: $filters.manufacturer) {
                    Text("All manufacturers").tag(nil as String?)
                    ForEach(manufacturerOptions, id: \.self) { manufacturer in
                        Text(manufacturer).tag(Optional(manufacturer))
                    }
                }
            } label: {
                Image(systemName: filters.manufacturer == nil
                      ? "line.3.horizontal.decrease" : "line.3.horizontal.decrease.circle.fill")
                    .font(.system(size: 20, weight: .semibold))
                    .foregroundStyle(Color.hangGreenDark)
                    .frame(width: 44, height: 44)
            }
            .accessibilityLabel("Filter by manufacturer")
            .accessibilityValue(filters.manufacturer ?? "All manufacturers")
            .accessibilityIdentifier("boardPicker.manufacturerFilter")
        }
    }

    private var emptyState: some View {
        VStack(spacing: 10) {
            Image(systemName: favoritesOnly ? "star" : "magnifyingglass")
                .font(.system(size: 30, weight: .regular))
                .foregroundStyle(Color.hangMuted)
            Text(favoritesOnly ? "No matching favorites" : "No boards match your filters")
                .font(.system(.headline, design: .rounded, weight: .semibold))
                .foregroundStyle(Color.hangInk)
            Text(favoritesOnly && store.favoriteBoardIDs.isEmpty
                 ? "Star a board to keep it here."
                 : "Try another search or manufacturer.")
                .font(.system(.subheadline, design: .rounded))
                .foregroundStyle(Color.hangMuted)
            Button("Show all boards") {
                favoritesOnly = false
                filters.clear()
            }
            .buttonStyle(.bordered)
            .tint(.hangGreenDark)
            .accessibilityIdentifier("boardPicker.clearFilters")
        }
        .frame(maxWidth: .infinity)
        .padding(.vertical, 48)
    }

    private func gallery(_ boards: [BoardRevision]) -> some View {
        LazyVGrid(columns: galleryColumns, alignment: .leading, spacing: 14) {
            ForEach(boards) { board in
                card(board)
            }
        }
    }

    private func card(_ board: BoardRevision) -> some View {
        BoardPickerCard(
            board: board,
            isSelected: board.id == store.selectedBoard.id,
            isFavorite: store.isFavorite(board),
            onSelect: {
                isSearchPresented = false
                store.selectBoard(board)
                dismiss()
            },
            onToggleFavorite: { store.toggleFavorite(board) },
            onViewSpecs: {
                isSearchPresented = false
                inspectedBoardID = board.id
            }
        )
    }
}

struct BoardPickerFilters {
    var searchText = ""
    var manufacturer: String?

    var isEmpty: Bool {
        searchText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty && manufacturer == nil
    }

    static func manufacturerOptions(from boards: [BoardRevision]) -> [String] {
        var manufacturerByNormalizedName: [String: String] = [:]
        for board in boards {
            let normalizedName = normalized(board.manufacturer)
            if manufacturerByNormalizedName[normalizedName] == nil {
                manufacturerByNormalizedName[normalizedName] = board.manufacturer
            }
        }
        return manufacturerByNormalizedName.values.sorted {
            $0.localizedCaseInsensitiveCompare($1) == .orderedAscending
        }
    }

    func filteredBoards(
        from boards: [BoardRevision],
        favoriteBoardIDs: Set<String> = []
    ) -> [BoardRevision] {
        let filteredBoards = boards.filter(matches)
        return filteredBoards.filter { favoriteBoardIDs.contains($0.id) }
            + filteredBoards.filter { !favoriteBoardIDs.contains($0.id) }
    }

    mutating func clear() {
        searchText = ""
        manufacturer = nil
    }

    private func matches(_ board: BoardRevision) -> Bool {
        let matchesManufacturer = manufacturer.map {
            Self.normalized(board.manufacturer) == Self.normalized($0)
        } ?? true
        guard matchesManufacturer else { return false }

        let searchTerm = searchText.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !searchTerm.isEmpty else { return true }
        return [board.name, board.manufacturer, board.subtitle].contains {
            Self.normalized($0).contains(Self.normalized(searchTerm))
        }
    }

    private static func normalized(_ text: String) -> String {
        text.folding(options: [.caseInsensitive, .diacriticInsensitive], locale: Locale(identifier: "en_US_POSIX"))
    }
}

private struct BoardPickerCard: View {
    let board: BoardRevision
    let isSelected: Bool
    let isFavorite: Bool
    let onSelect: () -> Void
    let onToggleFavorite: () -> Void
    let onViewSpecs: () -> Void

    var body: some View {
        ZStack(alignment: .bottomTrailing) {
            Button(action: onSelect) {
                VStack(alignment: .leading, spacing: 12) {
                    BoardMapView(board: board, isDisplayOnly: true, maximumMapHeight: 150)
                        .cardPreviewStyle()
                        .frame(height: 150)
                        .accessibilityHidden(true)
                        .allowsHitTesting(false)

                    Text(board.name)
                        .font(.system(.subheadline, design: .rounded, weight: .semibold))
                        .foregroundStyle(Color.hangInk)
                        .fixedSize(horizontal: false, vertical: true)
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .padding(.trailing, 40)
                        .frame(minHeight: 44, alignment: .top)
                }
                .frame(maxWidth: .infinity)
                .padding(14)
                .contentShape(Rectangle())
            }
            .buttonStyle(.plain)
            .accessibilityLabel(board.name)
            .accessibilityAddTraits(isSelected ? .isSelected : [])
            .accessibilityIdentifier("boardPicker.board.\(board.id)")

            Button(action: onToggleFavorite) {
                Image(systemName: isFavorite ? "star.fill" : "star")
                    .font(.system(size: 18, weight: .medium))
                    .foregroundStyle(isFavorite ? Color.hangGreenDark : Color.hangMuted)
                    .frame(width: 44, height: 44)
                    .contentShape(Rectangle())
            }
            .buttonStyle(.plain)
            .accessibilityLabel(
                isFavorite
                    ? "Remove \(board.name) from favorites"
                    : "Add \(board.name) to favorites"
            )
            .accessibilityIdentifier("boardPicker.favorite.\(board.id)")
            .padding(.trailing, 8)
            .padding(.bottom, 8)
        }
        .hangCard(padding: 0)
        .overlay(alignment: .topLeading) {
            if isSelected {
                Image(systemName: "checkmark.circle.fill")
                    .font(.system(size: 20, weight: .semibold))
                    .foregroundStyle(Color.hangGreenDark)
                    .frame(width: 44, height: 44)
                    .padding(8)
                    .accessibilityHidden(true)
                    .allowsHitTesting(false)
            }
        }
        .overlay(alignment: .topTrailing) {
            Button(action: onViewSpecs) {
                Image(systemName: "info.circle")
                    .font(.system(size: 18, weight: .regular))
                    .foregroundStyle(Color.hangMuted)
                    .frame(width: 44, height: 44)
                    .contentShape(Rectangle())
            }
            .buttonStyle(.plain)
            .accessibilityLabel("View hold specs for \(board.name)")
            .accessibilityIdentifier("boardPicker.holdSpecs.\(board.id)")
            .padding(8)
        }
    }
}

// Raster photos keep their card treatment; model silhouettes come from the USDZ.
private extension BoardMapView {
    @ViewBuilder
    func cardPreviewStyle() -> some View {
        switch board.defaultPresentation.media {
        case .raster:
            clipShape(RoundedRectangle(cornerRadius: 18, style: .continuous))
        case .model:
            self
        }
    }
}
