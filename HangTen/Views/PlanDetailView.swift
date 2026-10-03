import SwiftUI

enum PlanDetailPlanResolver {
    static func maxHangsVariant(
        from plans: [Double: TrainingPlan],
        selectedDepth: Double?
    ) -> TrainingPlan? {
        let depth = selectedDepth.flatMap { plans[$0] != nil ? $0 : nil }
            ?? plans.keys.max()
        return depth.flatMap { plans[$0] }
    }

    static func resolve(
        capturedPlan: TrainingPlan,
        eligiblePlans: [TrainingPlan]
    ) -> TrainingPlan? {
        eligiblePlans.first { $0.id == capturedPlan.id }
    }
}

enum PlanStartAvailability: Equatable {
    case available
    case unavailable(requirement: String)
}

enum PlanStartAvailabilityPolicy {
    private static let forceFeedbackRequirementTag = "requires-instrumented-12mm-force-feedback"
    private static let forceFeedbackPlanIDs: Set<String> = [
        "research.force-feedback-f80",
        "research.force-feedback-f100"
    ]

    static func availability(
        for plan: TrainingPlan,
        metadata: PlanMetadata? = nil
    ) -> PlanStartAvailability {
        let requiresForceFeedback = forceFeedbackPlanIDs.contains(plan.id) ||
            metadata?.tags.contains(forceFeedbackRequirementTag) == true
        guard requiresForceFeedback else { return .available }
        return .unavailable(
            requirement: "Requires real-time force feedback from an instrumented 12 mm edge."
        )
    }
}

private enum PlanDetailResolutionError: LocalizedError {
    case unavailable

    var errorDescription: String? {
        "This routine is not available for the selected board."
    }
}

private struct MaxHangsEdgeResolutionInput: Hashable {
    let plan: TrainingPlan
    let board: BoardRevision
}

struct PlanDetailView: View {
    @EnvironmentObject private var store: AppStore
    @EnvironmentObject private var motherboardBluetoothService: MotherboardBluetoothService
    @EnvironmentObject private var motherboardSettingsStore: MotherboardSettingsStore
    @Environment(\.dismiss) private var dismiss
    let plan: TrainingPlan
    @State private var editorDraft: CustomRoutineDraft?
    @State private var isShowingEditor = false
    @State private var isShowingDeleteConfirmation = false
    @State private var lifecycleError: String?
    @State private var initialWeightSource = WorkoutInitialWeightSource.untracked
    @State private var manualWeight = 0.0
    @State private var manualWeightIncludesBodyweight = false

    @State private var selectedMaxHangsDepth: Double?
    @State private var resolvedMaxHangsInput: MaxHangsEdgeResolutionInput?
    @State private var resolvedMaxHangsPlans: [Double: TrainingPlan] = [:]

    private var basePlan: TrainingPlan? {
        PlanDetailPlanResolver.resolve(
            capturedPlan: plan,
            eligiblePlans: store.plans
        )
    }

    private var maxHangsResolutionInput: MaxHangsEdgeResolutionInput? {
        guard let basePlan, basePlan.id == "research.max-hangs" else { return nil }
        return MaxHangsEdgeResolutionInput(plan: basePlan, board: store.board(for: basePlan))
    }

    private var maxHangsDepths: [Double] {
        guard resolvedMaxHangsInput == maxHangsResolutionInput else { return [] }
        return resolvedMaxHangsPlans.keys.sorted(by: >)
    }

    private var currentPlan: TrainingPlan? {
        guard let basePlan else { return nil }
        guard basePlan.id == "research.max-hangs" else { return basePlan }
        guard resolvedMaxHangsInput == maxHangsResolutionInput else { return nil }
        return PlanDetailPlanResolver.maxHangsVariant(
            from: resolvedMaxHangsPlans,
            selectedDepth: selectedMaxHangsDepth
        )
    }

    @MainActor
    static func duplicateDefinition(
        for plan: TrainingPlan,
        in store: AppStore,
        resolvedPlan: TrainingPlan? = nil
    ) throws -> CustomRoutineDefinition {
        if let resolvedPlan {
            return try store.duplicateRoutine(resolvedPlan)
        }
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
                        if let firstStep = currentPlan.steps.first,
                           !firstStep.workRequirements.isEmpty {
                            boardPreview(for: currentPlan)
                        }
                        titleBlock(for: currentPlan)
                        stepsCard(for: currentPlan)
                        sourceCard(for: currentPlan)
                    }
                    .padding(.horizontal, 20)
                    .padding(.top, 18)
                    .padding(.bottom, 116)
                }
            } else if maxHangsResolutionInput != resolvedMaxHangsInput {
                ProgressView()
            } else {
                unavailableContent
            }
        }
        .onChange(of: maxHangsResolutionInput, initial: true) { _, input in
            resolvedMaxHangsPlans = input.map {
                MaxHangsEdgeSelection.resolvedPlans(for: $0.plan, on: $0.board)
            } ?? [:]
            resolvedMaxHangsInput = input
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
                Spacer()
                Label(currentPlan.durationLabel, systemImage: "timer")
                    .font(.system(.footnote, design: .rounded, weight: .bold))
                    .foregroundStyle(Color.hangMuted)
            }
            Text(currentPlan.title)
                .font(.system(.largeTitle, design: .rounded, weight: .bold))
                .foregroundStyle(Color.hangInk)
            Text(currentPlan.subtitle)
                .font(.system(.subheadline, design: .rounded, weight: .medium))
                .foregroundStyle(Color.hangMuted)
                .fixedSize(horizontal: false, vertical: true)

            Label(store.board(for: currentPlan).name, systemImage: "rectangle.portrait")
                .font(.system(.footnote, design: .rounded, weight: .semibold))
                .foregroundStyle(Color.hangMuted)

            let labels = WorkoutLabelPresentationContent.displayLabels(
                for: store.metadata(for: currentPlan).athleteFacingLabels
            )
            if !labels.isEmpty {
                Text(labels.joined(separator: " · "))
                    .font(.system(.subheadline, design: .rounded, weight: .medium))
                    .foregroundStyle(Color.hangGreenDark)
                    .fixedSize(horizontal: false, vertical: true)
                    .accessibilityLabel("Workout labels: \(labels.joined(separator: ", "))")
            }

            if currentPlan.id == "research.max-hangs", !maxHangsDepths.isEmpty {
                VStack(alignment: .leading, spacing: 8) {
                    SectionLabel(title: "Training edge")
                    Picker("Edge depth", selection: Binding(
                        get: { selectedMaxHangsDepth.flatMap { maxHangsDepths.contains($0) ? $0 : nil } ?? maxHangsDepths.first ?? 20 },
                        set: { selectedMaxHangsDepth = $0 }
                    )) {
                        ForEach(maxHangsDepths, id: \.self) { depth in
                            Text("\(depth, format: .number) mm").tag(depth)
                        }
                    }
                    .pickerStyle(.menu)
                    .accessibilityIdentifier("plan.maxHangs.edgePicker")
                    Text("Choose one edge size for this session. Adjust added weight to keep 3 seconds in reserve. Warm up progressively before starting.")
                        .font(.system(.footnote, design: .rounded, weight: .medium))
                        .foregroundStyle(Color.hangMuted)
                        .fixedSize(horizontal: false, vertical: true)
                }
                .hangCard()
            }

            initialWeightSetupCard

            switch PlanStartAvailabilityPolicy.availability(
                for: currentPlan,
                metadata: store.metadata(for: currentPlan)
            ) {
            case .available:
                WorkoutAccessGate(
                    plan: currentPlan,
                    initialWeight: initialWeightConfiguration
                ) {
                    startRoutineLabel(for: currentPlan)
                }
                .buttonStyle(.plain)
                .accessibilityIdentifier("plan.startRoutine")
            case .unavailable(let requirement):
                VStack(alignment: .leading, spacing: 8) {
                    Button(action: {}) {
                        startRoutineLabel(for: currentPlan)
                    }
                    .buttonStyle(.plain)
                    .disabled(true)
                    Text(requirement)
                        .font(.system(.footnote, design: .rounded, weight: .semibold))
                        .foregroundStyle(Color.hangMuted)
                        .fixedSize(horizontal: false, vertical: true)
                }
                .accessibilityElement(children: .combine)
                .accessibilityLabel("Routine unavailable. \(requirement)")
            }
        }
    }

    private var initialWeightSetupCard: some View {
        VStack(alignment: .leading, spacing: 14) {
            VStack(alignment: .leading, spacing: 5) {
                SectionLabel(title: "Weight tracking")
                Text("Optional. Skip tracking, connect a supported scale, or enter a weight manually before you start.")
                    .font(.system(.footnote, design: .rounded, weight: .medium))
                    .foregroundStyle(Color.hangMuted)
                    .fixedSize(horizontal: false, vertical: true)
            }

            Picker("Weight tracking", selection: $initialWeightSource) {
                ForEach(WorkoutInitialWeightSource.allCases) { source in
                    Text(source.label).tag(source)
                }
            }
            .pickerStyle(.segmented)
            .accessibilityIdentifier("workout.initialWeight.sourcePicker")
            .accessibilityLabel("Weight tracking")

            switch initialWeightSource {
            case .untracked:
                Text("No weight or scale data will be recorded. You can still run and save the routine.")
                    .font(.system(.footnote, design: .rounded, weight: .medium))
                    .foregroundStyle(Color.hangMuted)
                    .fixedSize(horizontal: false, vertical: true)
            case .sensor:
                scaleSetup
            case .manual:
                manualWeightSetup
            }
        }
        .hangCard()
        .accessibilityElement(children: .contain)
        .accessibilityIdentifier("plan.initialWeight.setup")
    }

    private var manualWeightSetup: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                TextField(
                    "Weight",
                    value: $manualWeight,
                    format: .number.precision(.fractionLength(1))
                )
                .keyboardType(.decimalPad)
                .accessibilityIdentifier("workout.initialWeight.manualField")
                .accessibilityLabel("Manual weight")

                Text(motherboardSettingsStore.loadAdjustmentUnit.label)
                    .font(.system(.subheadline, design: .rounded, weight: .semibold))
                    .foregroundStyle(Color.hangMuted)
            }

            HStack {
                Button("Add bodyweight") {
                    manualWeightIncludesBodyweight.toggle()
                }
                .buttonStyle(.plain)
                .frame(minHeight: 44)
                .contentShape(Rectangle())
                .accessibilityIdentifier("workout.initialWeight.addBodyweight.label")
                Spacer(minLength: 12)
                Toggle("Add bodyweight", isOn: $manualWeightIncludesBodyweight)
                    .labelsHidden()
                    .fixedSize()
                    .accessibilityIdentifier("workout.initialWeight.addBodyweight")
                    .accessibilityLabel("Add bodyweight")
            }

            Text("Off records a standalone weight. On records this as added load on top of bodyweight.")
                .font(.system(.caption, design: .rounded, weight: .medium))
                .foregroundStyle(Color.hangMuted)
                .fixedSize(horizontal: false, vertical: true)
        }
    }

    private var scaleSetup: some View {
        VStack(alignment: .leading, spacing: 12) {
            Picker("Scale profile", selection: $motherboardSettingsStore.forceSensorProfile) {
                ForEach(ForceSensorProfile.connectableCases) { profile in
                    Text(profile.label).tag(profile)
                }
            }
            .disabled(scaleConnectionIsActive)
            .accessibilityIdentifier("plan.initialWeight.scaleProfile")

            Text(scaleConnectionDetail)
                .font(.system(.footnote, design: .rounded, weight: .medium))
                .foregroundStyle(Color.hangMuted)
                .fixedSize(horizontal: false, vertical: true)
                .accessibilityIdentifier("plan.initialWeight.scaleStatus")

            Button(action: toggleScaleConnection) {
                Label(scaleConnectionActionTitle, systemImage: scaleConnectionActionIcon)
                    .font(.system(.subheadline, design: .rounded, weight: .bold))
                    .frame(maxWidth: .infinity)
            }
            .buttonStyle(.bordered)
            .tint(Color.hangGreenDark)
            .accessibilityIdentifier("plan.initialWeight.connect")
            .accessibilityLabel(scaleConnectionActionTitle)
        }
    }

    private var initialWeightConfiguration: WorkoutInitialWeightConfiguration {
        switch initialWeightSource {
        case .untracked:
            .untracked
        case .sensor:
            .sensor
        case .manual:
            .manual(
                weightKGF: motherboardSettingsStore.loadAdjustmentUnit.kilogramsForce(
                    fromDisplayedForce: manualWeight
                ),
                includesBodyweight: manualWeightIncludesBodyweight
            )
        }
    }

    private var scaleConnectionIsActive: Bool {
        switch motherboardBluetoothService.state {
        case .scanning, .connecting, .calibrating, .streaming:
            true
        case .bluetoothUnavailable, .unauthorized, .idle, .disconnected, .failed:
            false
        }
    }

    private var scaleConnectionActionTitle: String {
        switch motherboardBluetoothService.state {
        case .scanning, .connecting, .calibrating:
            "Cancel connection"
        case .streaming:
            "Disconnect scale"
        case .bluetoothUnavailable, .unauthorized, .idle, .disconnected, .failed:
            "Connect supported scale"
        }
    }

    private var scaleConnectionActionIcon: String {
        scaleConnectionIsActive ? "xmark.circle" : "scalemass"
    }

    private var scaleConnectionDetail: String {
        switch motherboardBluetoothService.state {
        case .bluetoothUnavailable:
            "Turn on Bluetooth, then check Hang Ten’s Bluetooth access in Settings. Starting the routine remains available."
        case .unauthorized:
            "Allow Bluetooth access in Settings to connect a supported scale. Starting the routine remains available."
        case .idle, .disconnected:
            "Connect any supported scale to track live load, or start the routine without live scale data."
        case .scanning:
            "Looking nearby for a supported scale. You can still start the routine."
        case .connecting:
            "Connecting to the supported scale. You can still start the routine."
        case .calibrating:
            "Preparing the supported scale for live readings."
        case .streaming:
            "Your supported scale is connected and ready."
        case .failed:
            "Couldn’t connect to the selected scale. Retry or start the routine without live scale data."
        }
    }

    private func toggleScaleConnection() {
        if scaleConnectionIsActive {
            motherboardBluetoothService.disconnect()
        } else {
            motherboardBluetoothService.connect(profile: motherboardSettingsStore.forceSensorProfile)
        }
    }

    private func startRoutineLabel(for plan: TrainingPlan) -> some View {
        HStack {
            Image(systemName: "play.fill")
            Text("Start routine")
            Spacer()
            Text(plan.durationLabel)
                .font(.system(.caption, design: .rounded, weight: .bold))
        }
        .font(.system(.callout, design: .rounded, weight: .bold))
        .foregroundStyle(Color.hangInk)
        .padding(.horizontal, 17)
        .padding(.vertical, 15)
        .background(Color.hangGreen, in: RoundedRectangle(cornerRadius: 16, style: .continuous))
    }

    private func boardPreview(for currentPlan: TrainingPlan) -> some View {
        let board = store.board(for: currentPlan)
        let firstStep = currentPlan.steps.first
        let resolvedHoldIDs = firstStep.map { store.contactIDs(for: $0, on: board) } ?? []
        // Prefer a pose-backed hold so Dual-style multi-pose boards face the lit contact.
        let firstStepHold = board.contacts.first { hold in
            resolvedHoldIDs.contains(hold.id)
                && board.position(
                    presentationID: board.defaultPresentation.id,
                    containingContactID: hold.id
                ) != nil
        }
        let firstStepHoldIDs: Set<String> = {
            guard let hold = firstStepHold,
                  let position = board.position(
                    presentationID: board.defaultPresentation.id,
                    containingContactID: hold.id
                  ) else {
                return resolvedHoldIDs
            }
            let visible = resolvedHoldIDs.intersection(Set(position.contactIDs))
            return visible.isEmpty ? resolvedHoldIDs : visible
        }()
        let firstStepHoldCue = WorkoutHoldCuePolicy.resolve(
            step: firstStep,
            hold: firstStepHold,
            on: board
        )

        return VStack(alignment: .leading, spacing: 12) {
            SectionLabel(title: "First hold cue")
            BoardMapView(
                board: board,
                highlightedHoldIDs: firstStepHoldIDs,
                activeHoldID: firstStepHold?.id
            )
                .padding(.horizontal, 12)
            if let firstStepHoldCue, let hold = firstStepHoldCue.hold {
                GripDiagramView(
                    hold: hold,
                    gripType: firstStepHoldCue.gripType,
                    fingerConfiguration: firstStepHoldCue.fingerConfiguration
                )
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
                    .font(.system(.caption, design: .rounded, weight: .semibold))
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
                    .font(.system(.subheadline, design: .rounded, weight: .bold))
                    .foregroundStyle(Color.hangInk)
                Text("This is a custom routine stored on this device.")
                    .font(.system(.caption, design: .rounded, weight: .medium))
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
                    Text(PlanSourcePresentationContent.label(for: currentPlan))
                        .font(.system(.subheadline, design: .rounded, weight: .bold))
                        .foregroundStyle(Color.hangInk)
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
                .font(.system(.title2, design: .rounded, weight: .bold))
                .foregroundStyle(Color.hangInk)
            Text("Choose another board or a different routine.")
                .font(.system(.subheadline, design: .rounded, weight: .medium))
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
                duplicate: try Self.duplicateDefinition(for: plan, in: store, resolvedPlan: currentPlan)
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
                Text("\(step.number)")
                    .font(.system(.caption, design: .rounded, weight: .bold))
                    .foregroundStyle(step.phase.textTint)
                    .fixedSize()
                    .frame(minWidth: 31, minHeight: 31)
                    .padding(2)
                    .background(step.phase.tint.opacity(0.17), in: Circle())
                if !isLast {
                    Rectangle()
                        .fill(Color.hangLine)
                        .frame(width: 1, height: 44)
                }
            }

            VStack(alignment: .leading, spacing: 5) {
                HStack(alignment: .firstTextBaseline) {
                    Text(step.title)
                        .font(.system(.subheadline, design: .rounded, weight: .bold))
                        .foregroundStyle(Color.hangInk)
                    Spacer()
                    Text(step.durationLabel)
                        .font(.system(.caption, design: .rounded, weight: .bold))
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
                            .font(.system(.footnote, design: .rounded, weight: .medium))
                            .foregroundStyle(Color.hangMuted)
                            .fixedSize(horizontal: false, vertical: true)
                    case .accessory:
                        Text(row.text)
                            .font(.system(.caption2, design: .rounded, weight: .bold))
                            .foregroundStyle(step.phase.textTint)
                    }
                }
            }
            .padding(.bottom, isLast ? 0 : 12)
        }
    }
}
