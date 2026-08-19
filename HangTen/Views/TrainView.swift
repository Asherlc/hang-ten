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

    var body: some View {
        ScrollView(showsIndicators: false) {
            LazyVStack(spacing: 16) {
                ForEach(BoardCatalog.all) { board in
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
            .padding(.horizontal, 20)
            .padding(.top, 18)
            .padding(.bottom, 30)
        }
        .background(Color.hangBackground)
        .navigationTitle("Choose board")
        .navigationBarTitleDisplayMode(.inline)
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
