import SwiftUI

struct TrainView: View {
    @EnvironmentObject private var store: AppStore
    private let onBrowsePlans: () -> Void
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
    @State private var showsSettingsReview: Bool = {
        #if DEBUG
        let environment = ProcessInfo.processInfo.environment
        return environment["HANGTEN_REVIEW_SETTINGS"] == "1"
            || environment["HANGTEN_REVIEW_HEALTH"] == "1"
            || environment["HANGTEN_REVIEW_MOTHERBOARD"] == "1"
        #else
        return false
        #endif
    }()
    @State private var showsBoardPickerReview: Bool = {
        #if DEBUG
        return ProcessInfo.processInfo.environment["HANGTEN_REVIEW_BOARD_PICKER"] == "1"
        #else
        return false
        #endif
    }()

    init(onBrowsePlans: @escaping () -> Void) {
        self.onBrowsePlans = onBrowsePlans
    }

    var body: some View {
        NavigationStack {
            ScrollView(showsIndicators: false) {
                VStack(alignment: .leading, spacing: 22) {
                    selectedBoardCard
                    favoritesSection
                }
                .padding(.horizontal, 20)
                .padding(.top, 18)
                .padding(.bottom, 30)
            }
            .background(Color.hangBackground)
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
            .navigationDestination(isPresented: $showsSettingsReview) {
                AppSettingsView()
            }
            .navigationDestination(isPresented: $showsBoardPickerReview) {
                BoardPickerView()
            }
        }
    }

    private var reviewPlan: TrainingPlan? {
        store.featuredPlan
    }

    private var selectedBoardCard: some View {
        VStack(alignment: .leading, spacing: 16) {
            BoardMapView(board: store.selectedBoard)
                .clipShape(RoundedRectangle(cornerRadius: 18, style: .continuous))

            VStack(alignment: .leading, spacing: 5) {
                SectionLabel(title: "Your board")
                Text(store.selectedBoard.name)
                    .font(.system(size: 21, weight: .bold, design: .rounded))
                    .foregroundStyle(Color.hangInk)
                Text(store.selectedBoard.dimensions)
                    .font(.system(size: 13, weight: .medium, design: .rounded))
                    .foregroundStyle(Color.hangMuted)
            }

            HStack(spacing: 16) {
                Link(destination: store.selectedBoard.productURL) {
                    Label("Product page", systemImage: "arrow.up.right")
                }

                Spacer()

                NavigationLink("Change board") {
                    BoardPickerView()
                }
                .accessibilityIdentifier("train.changeBoard")
            }
            .font(.system(size: 13, weight: .bold, design: .rounded))
            .foregroundStyle(Color.hangGreenDark)
        }
        .hangCard()
        .accessibilityIdentifier("train.board")
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
                Button("Browse plans", action: onBrowsePlans)
                    .buttonStyle(.borderedProminent)
                    .tint(.hangGreenDark)
                    .accessibilityIdentifier("train.browsePlans")
            }
            .hangCard()
        } else {
            VStack(alignment: .leading, spacing: 12) {
                SectionLabel(title: "Favorites")
                ForEach(store.favoritePlans) { plan in
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
}

struct BoardPickerView: View {
    @EnvironmentObject private var store: AppStore
    @Environment(\.dismiss) private var dismiss
    @State private var filters = BoardPickerFilters()

    private var filteredBoards: [TrainingBoard] {
        filters.filteredBoards(from: BoardCatalog.all)
    }

    private var manufacturerOptions: [String] {
        BoardPickerFilters.manufacturerOptions(from: BoardCatalog.all)
    }

    var body: some View {
        ScrollView(showsIndicators: false) {
            LazyVStack(spacing: 16) {
                Picker("Manufacturer", selection: $filters.manufacturer) {
                    Text("All manufacturers")
                        .tag(nil as String?)
                    ForEach(manufacturerOptions, id: \.self) { manufacturer in
                        Text(manufacturer)
                            .tag(Optional(manufacturer))
                    }
                }
                .pickerStyle(.menu)
                .frame(maxWidth: .infinity, alignment: .leading)
                .accessibilityIdentifier("boardPicker.manufacturerFilter")

                if filteredBoards.isEmpty {
                    VStack(spacing: 8) {
                        Text("No boards match your filters.")
                            .font(.system(size: 18, weight: .bold, design: .rounded))
                            .foregroundStyle(Color.hangInk)
                        Text("Try a different search or manufacturer.")
                            .font(.system(size: 14, weight: .medium, design: .rounded))
                            .foregroundStyle(Color.hangMuted)
                        Button("Clear filters") {
                            filters.clear()
                        }
                        .buttonStyle(.bordered)
                        .tint(.hangGreenDark)
                        .accessibilityIdentifier("boardPicker.clearFilters")
                    }
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, 36)
                } else {
                    ForEach(filteredBoards) { board in
                        Button {
                            store.selectBoard(board)
                            dismiss()
                        } label: {
                            BoardPickerCard(
                                board: board,
                                isSelected: board.id == store.selectedBoard.id
                            )
                        }
                        .buttonStyle(.plain)
                        .accessibilityIdentifier("boardPicker.board.\(board.id)")
                    }
                }
            }
            .padding(.horizontal, 20)
            .padding(.top, 18)
            .padding(.bottom, 30)
        }
        .background(Color.hangBackground)
        .navigationTitle("Choose board")
        .navigationBarTitleDisplayMode(.inline)
        .searchable(text: $filters.searchText, prompt: "Search boards")
        .accessibilityIdentifier("boardPicker.search")
    }
}

struct BoardPickerFilters {
    var searchText = ""
    var manufacturer: String?

    var isEmpty: Bool {
        searchText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty && manufacturer == nil
    }

    static func manufacturerOptions(from boards: [TrainingBoard]) -> [String] {
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

    func filteredBoards(from boards: [TrainingBoard]) -> [TrainingBoard] {
        boards.filter(matches)
    }

    mutating func clear() {
        searchText = ""
        manufacturer = nil
    }

    private func matches(_ board: TrainingBoard) -> Bool {
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
        text.folding(options: [.caseInsensitive, .diacriticInsensitive], locale: .current)
    }
}

private struct BoardPickerCard: View {
    let board: TrainingBoard
    let isSelected: Bool

    var body: some View {
        VStack(alignment: .leading, spacing: 14) {
            BoardMapView(board: board)
                .clipShape(RoundedRectangle(cornerRadius: 18, style: .continuous))

            HStack(alignment: .top, spacing: 12) {
                VStack(alignment: .leading, spacing: 4) {
                    Text(board.name)
                        .font(.system(size: 18, weight: .bold, design: .rounded))
                        .foregroundStyle(Color.hangInk)
                    Text(board.dimensions)
                        .font(.system(size: 13, weight: .medium, design: .rounded))
                        .foregroundStyle(Color.hangMuted)
                }

                Spacer()

                if isSelected {
                    Image(systemName: "checkmark.circle.fill")
                        .font(.system(size: 22, weight: .bold))
                        .foregroundStyle(Color.hangGreenDark)
                        .accessibilityLabel("Selected")
                }
            }
        }
        .hangCard()
    }
}
