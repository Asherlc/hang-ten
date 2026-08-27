import SwiftUI

struct WorkoutAccessGate<Label: View>: View {
    @EnvironmentObject private var store: AppStore
    @State private var pendingPlan: TrainingPlan?
    @State private var pendingStartsImmediately = false
    @State private var showsPaywall = false
    @State private var showsWorkout = false

    private let plan: TrainingPlan
    private let startsImmediately: Bool
    private let launchesOnAppear: Bool
    private let label: Label

    init(
        plan: TrainingPlan,
        startsImmediately: Bool = false,
        launchesOnAppear: Bool = false,
        @ViewBuilder label: () -> Label
    ) {
        self.plan = plan
        self.startsImmediately = startsImmediately
        self.launchesOnAppear = launchesOnAppear
        self.label = label()
    }

    var body: some View {
        Group {
            if launchesOnAppear {
                Color.clear
            } else {
                Button(action: requestLaunch) {
                    label
                }
            }
        }
        .navigationDestination(isPresented: $showsWorkout) {
            if let pendingPlan {
                WorkoutView(
                    plan: pendingPlan,
                    startsImmediately: pendingStartsImmediately
                )
            }
        }
        .sheet(isPresented: $showsPaywall, onDismiss: continuePendingLaunchIfAllowed) {
            LifetimeUnlockPaywall(
                purchaseManager: store.purchaseManager,
                onAccessChange: accessDecisionDidChange
            )
        }
        .task {
            guard launchesOnAppear, pendingPlan == nil else { return }
            requestLaunch()
        }
    }

    private func requestLaunch() {
        pendingPlan = plan
        pendingStartsImmediately = startsImmediately

        switch store.workoutLaunchDecision {
        case .allowed:
            showsWorkout = true
        case .requiresPurchase:
            showsPaywall = true
        }
    }

    private func continuePendingLaunchIfAllowed() {
        guard pendingPlan != nil, store.workoutLaunchDecision == .allowed else { return }
        showsWorkout = true
    }

    private func accessDecisionDidChange() {
        guard showsPaywall, store.workoutLaunchDecision == .allowed else { return }
        showsPaywall = false
    }
}

extension WorkoutAccessGate where Label == EmptyView {
    init(
        plan: TrainingPlan,
        startsImmediately: Bool = false,
        launchesOnAppear: Bool = true
    ) {
        self.init(
            plan: plan,
            startsImmediately: startsImmediately,
            launchesOnAppear: launchesOnAppear
        ) {
            EmptyView()
        }
    }
}

struct LifetimeUnlockPaywall: View {
    @Environment(\.dismiss) private var dismiss
    @ObservedObject var purchaseManager: PurchaseManager
    let onAccessChange: () -> Void
    @State private var cancellationMessage: String?

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(spacing: 24) {
                    Image(systemName: "infinity.circle.fill")
                        .font(.system(size: 58, weight: .semibold))
                        .foregroundStyle(Color.hangGreenDark)

                    VStack(spacing: 12) {
                        Text("Unlock Hang Ten")
                            .font(.system(size: 30, weight: .bold, design: .rounded))
                            .foregroundStyle(Color.hangInk)

                        Text("You’ve completed your 2 free workouts. Unlock unlimited workouts for a one-time purchase.")
                            .font(.system(size: 16, weight: .medium, design: .rounded))
                            .foregroundStyle(Color.hangMuted)
                            .multilineTextAlignment(.center)
                            .fixedSize(horizontal: false, vertical: true)
                    }

                    VStack(spacing: 12) {
                        Button(action: purchase) {
                            Text(purchaseButtonTitle)
                                .font(.system(size: 17, weight: .bold, design: .rounded))
                                .frame(maxWidth: .infinity)
                                .padding(.vertical, 15)
                                .foregroundStyle(Color.hangInk)
                                .background(
                                    Color.hangGreen,
                                    in: RoundedRectangle(cornerRadius: 16, style: .continuous)
                                )
                        }
                        .buttonStyle(.plain)
                        .disabled(isTransacting || purchaseManager.product == nil)
                        .accessibilityIdentifier("paywall.purchase")

                        Button("Restore Purchases", action: restore)
                            .font(.system(size: 15, weight: .bold, design: .rounded))
                            .foregroundStyle(Color.hangGreenDark)
                            .disabled(isTransacting)
                            .accessibilityIdentifier("paywall.restore")
                    }

                    if let statusMessage {
                        HStack(alignment: .firstTextBaseline, spacing: 9) {
                            if isTransacting {
                                ProgressView()
                            }
                            Text(statusMessage)
                                .font(.system(size: 14, weight: .semibold, design: .rounded))
                                .foregroundStyle(Color.hangMuted)
                                .fixedSize(horizontal: false, vertical: true)
                        }
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .padding(14)
                        .background(Color.hangBackground, in: RoundedRectangle(cornerRadius: 14))
                    }
                }
                .hangCard(padding: 24)
                .padding(.horizontal, 20)
                .padding(.vertical, 4)
                .frame(maxWidth: 520)
                .frame(maxWidth: .infinity)
                .accessibilityElement(children: .contain)
                .accessibilityIdentifier("paywall.lifetimeUnlock")
            }
            .background(Color.hangBackground)
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button("Close") {
                        dismiss()
                    }
                    .disabled(purchaseManager.state == .purchasing)
                    .accessibilityIdentifier("paywall.close")
                }
            }
        }
        .interactiveDismissDisabled(purchaseManager.state == .purchasing)
        .onChange(of: purchaseManager.hasLifetimeEntitlement) { _, _ in
            onAccessChange()
        }
    }

    private var purchaseButtonTitle: String {
        guard let product = purchaseManager.product else {
            return "Unlock Hang Ten"
        }
        return "Unlock for \(product.displayPrice)"
    }

    private var isTransacting: Bool {
        purchaseManager.state == .loading || purchaseManager.state == .purchasing
    }

    private var statusMessage: String? {
        if let cancellationMessage {
            return cancellationMessage
        }

        switch purchaseManager.state {
        case .idle:
            return nil
        case .loading:
            return "Loading purchase options…"
        case .purchasing:
            return "Completing your purchase…"
        case .pending:
            return "Purchase pending. Your workout will unlock after the App Store approves it."
        case .failed:
            return "We couldn’t complete the purchase. Please try again or restore purchases."
        }
    }

    private func purchase() {
        cancellationMessage = nil
        Task {
            await purchaseManager.purchase()
            if purchaseManager.state == .idle,
               !purchaseManager.hasLifetimeEntitlement {
                cancellationMessage = "Purchase cancelled. You weren’t charged."
            }
        }
    }

    private func restore() {
        cancellationMessage = nil
        Task {
            await purchaseManager.restore()
        }
    }
}
