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

private struct PlanHoldSubstitutionInput: Hashable {
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
    @State private var resolvedSubstitutionInput: PlanHoldSubstitutionInput?
    @State private var substitutionRequests: [PlanHoldSubstitutionRequest] = []
    @State private var substitutionSelections: [PlanHoldSubstitutionRequest.ID: String] = [:]
    @State private var resolvedSessionPlan: TrainingPlan?

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

    private var prescribedPlan: TrainingPlan? {
        guard let basePlan else { return nil }
        guard basePlan.id == "research.max-hangs" else { return basePlan }
        guard resolvedMaxHangsInput == maxHangsResolutionInput else { return nil }
        return PlanDetailPlanResolver.maxHangsVariant(
            from: resolvedMaxHangsPlans,
            selectedDepth: selectedMaxHangsDepth
        ) ?? basePlan
    }

    private var substitutionInput: PlanHoldSubstitutionInput? {
        prescribedPlan.map { PlanHoldSubstitutionInput(plan: $0, board: store.board(for: $0)) }
    }

    private var currentPlan: TrainingPlan? {
        guard resolvedSubstitutionInput == substitutionInput else { return prescribedPlan }
        return resolvedSessionPlan ?? prescribedPlan
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
                        titleBlock(for: currentPlan)
                        if let firstStep = currentPlan.steps.first(where: { !$0.isRestStep }),
                           !firstStep.workRequirements.isEmpty {
                            boardPreview(for: currentPlan)
                        }
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
        .onChange(of: substitutionInput, initial: true) { _, input in
            substitutionRequests = input.map {
                PlanHoldSubstitutions.requests(for: $0.plan, on: $0.board)
            } ?? []
            substitutionSelections = [:]
            resolvedSubstitutionInput = input
            resolveSubstitutedSession()
        }
        .onChange(of: substitutionSelections) { _, _ in
            resolveSubstitutedSession()
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

            Text(store.board(for: currentPlan).name)
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

            if !substitutionRequests.isEmpty {
                PlanHoldSubstitutionCard(
                    requests: substitutionRequests,
                    selections: $substitutionSelections,
                    isComplete: resolvedSessionPlan != nil
                )
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
                    startRoutineLabel
                }
                .buttonStyle(.borderedProminent)
                .controlSize(.large)
                .tint(.hangGreenDark)
                .disabled(resolvedSubstitutionInput != substitutionInput || resolvedSessionPlan == nil)
                .accessibilityIdentifier("plan.startRoutine")
            case .unavailable(let requirement):
                VStack(alignment: .leading, spacing: 8) {
                    Button(action: {}) {
                        startRoutineLabel
                    }
                    .buttonStyle(.borderedProminent)
                    .controlSize(.large)
                    .tint(.hangGreenDark)
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

    private func resolveSubstitutedSession() {
        guard let input = substitutionInput, input == resolvedSubstitutionInput else {
            resolvedSessionPlan = nil
            return
        }
        resolvedSessionPlan = PlanHoldSubstitutions.applying(
            substitutionSelections, to: input.plan, on: input.board
        )
    }

    private var initialWeightSetupCard: some View {
        VStack(alignment: .leading, spacing: 14) {
            SectionLabel(title: "Weight tracking · Optional")

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
                EmptyView()
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
                Text("Weight")
                    .font(.system(.subheadline, design: .rounded, weight: .semibold))
                TextField(
                    "Weight",
                    value: $manualWeight,
                    format: .number.precision(.fractionLength(1))
                )
                .keyboardType(.decimalPad)
                .textFieldStyle(.roundedBorder)
                .accessibilityIdentifier("workout.initialWeight.manualField")
                .accessibilityLabel("Manual weight")

                Text(motherboardSettingsStore.loadAdjustmentUnit.label)
                    .font(.system(.subheadline, design: .rounded, weight: .semibold))
                    .foregroundStyle(Color.hangMuted)
            }

            Toggle("Add bodyweight", isOn: $manualWeightIncludesBodyweight)
                .toggleStyle(FullRowSwitchToggleStyle())
                .accessibilityIdentifier("workout.initialWeight.addBodyweight")

            Text(manualWeightIncludesBodyweight
                 ? "Recorded as added load on top of bodyweight."
                 : "Recorded as a standalone weight.")
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

    private var startRoutineLabel: some View {
        Label("Start routine", systemImage: "play.fill")
            .frame(maxWidth: .infinity)
        .font(.system(.callout, design: .rounded, weight: .bold))
    }

    private func boardPreview(for currentPlan: TrainingPlan) -> some View {
        let board = store.board(for: currentPlan)
        let firstStep = currentPlan.steps.first { !$0.isRestStep }
        let resolvedHoldIDs = firstStep.map { store.contactIDs(for: $0, on: board) } ?? []
        let firstTask = firstStep?.segments.lazy.compactMap { $0.target?.planTasks }.first?.first
        let previewHandSide: WorkoutSide? = firstTask?.count == 1 && firstTask?.first?.side == nil ? .left : nil
        let presentationID = WorkoutHighlightResolver.presentationID(
            for: firstStep, on: board, selectedHandSide: previewHandSide
        ) ?? board.defaultPresentation.id
        let resolvedContacts = firstStep.map {
            WorkoutHighlightResolver.contacts(for: $0, on: board, selectedHandSide: previewHandSide)
        } ?? []
        // Prefer a pose-backed hold so Dual-style multi-pose boards face the lit contact.
        let firstStepHold = (resolvedContacts.isEmpty ? board.contacts : resolvedContacts).first { hold in
            resolvedHoldIDs.contains(hold.id)
                && board.position(
                    presentationID: presentationID,
                    containingContactID: hold.id
                ) != nil
        }
        let firstStepHoldIDs: Set<String> = {
            guard let hold = firstStepHold,
                  let position = board.position(
                    presentationID: presentationID,
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
                selectedPresentationID: presentationID,
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
            if let firstStep {
                PlanStepInstructions(step: firstStep)
            }
        }
        .hangCard()
        .accessibilityElement(children: .contain)
        .accessibilityIdentifier("plan.firstHoldCue")
    }

    private func stepsCard(for currentPlan: TrainingPlan) -> some View {
        let groups = PlanFlowPresentation.groups(for: currentPlan)

        return VStack(alignment: .leading, spacing: 0) {
            HStack {
                SectionLabel(title: "Session flow")
                Spacer()
                Text("\(currentPlan.steps.count) cues")
                    .font(.system(.caption, design: .rounded, weight: .semibold))
                    .foregroundStyle(Color.hangMuted)
            }
            .padding(.bottom, 14)

            PlanFlowRows(groups: groups)
        }
        .hangCard()
        .accessibilityElement(children: .contain)
        .accessibilityIdentifier("plan.sessionFlow")
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

/// Keep touch handling on the whole row while exposing one native switch to
/// assistive technology. The visual switch never competes with the row's tap.
private struct FullRowSwitchToggleStyle: ToggleStyle {
    func makeBody(configuration: Configuration) -> some View {
        Button {
            configuration.isOn.toggle()
        } label: {
            HStack {
                configuration.label
                Spacer(minLength: 12)
                Toggle("", isOn: configuration.$isOn)
                    .toggleStyle(.switch)
                    .labelsHidden()
                    .allowsHitTesting(false)
                    .accessibilityHidden(true)
            }
            .frame(minHeight: 44)
            .contentShape(Rectangle())
        }
        .buttonStyle(.plain)
        .accessibilityRepresentation {
            Toggle(isOn: configuration.$isOn) {
                configuration.label
            }
            .toggleStyle(.switch)
        }
    }
}

private struct PlanFlowRows: View {
    let groups: [PlanFlowGroup]
    var depth = 0

    private var isNested: Bool { depth > 0 }

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            ForEach(Array(groups.enumerated()), id: \.element.id) { index, group in
                let isLast = index == groups.count - 1
                if group.repeatCount > 1 {
                    VStack(alignment: .leading, spacing: 12) {
                        VStack(alignment: .leading, spacing: 4) {
                            HStack(alignment: .firstTextBaseline, spacing: 8) {
                                Label("Repeat \(group.repeatCount) times", systemImage: "repeat")
                                    .font(.system(.subheadline, design: .rounded, weight: .bold))
                                    .foregroundStyle(Color.hangGreenDark)
                                    .fixedSize(horizontal: false, vertical: true)
                                    .layoutPriority(1)
                                Spacer(minLength: 0)
                                Text("\(group.durationLabel) total")
                                    .font(.system(.caption, design: .rounded, weight: .semibold))
                                    .foregroundStyle(Color.hangMuted)
                                    .fixedSize(horizontal: false, vertical: true)
                            }
                            if !isNested, let first = group.sourceSteps.first, let last = group.sourceSteps.last {
                                Text("Steps \(first.number)–\(last.number)")
                                    .font(.system(.caption2, design: .rounded, weight: .medium))
                                    .foregroundStyle(Color.hangMuted)
                            }
                        }
                        PlanFlowRows(groups: group.children, depth: depth + 1)
                    }
                    .padding(14)
                    .background(
                        isNested ? Color.white.opacity(0.72) : Color.hangBackground,
                        in: RoundedRectangle(cornerRadius: 14)
                    )
                    .accessibilityElement(children: .contain)
                    .accessibilityIdentifier("plan.flow.repeat.\(depth).\(group.id)")
                    .padding(.bottom, isLast ? 0 : 14)
                } else if let step = group.sourceSteps.first {
                    StepRow(
                        step: step, title: group.title, nextInstruction: group.nextInstruction,
                        isLast: isLast, showsNumber: !isNested
                    )
                }
            }
        }
    }
}

private struct StepRow: View {
    let step: WorkoutStep
    let title: String
    let nextInstruction: String?
    let isLast: Bool
    let showsNumber: Bool

    var body: some View {
        HStack(alignment: .top, spacing: 12) {
            VStack(spacing: 0) {
                if showsNumber {
                    Text("\(step.number)")
                        .font(.system(.caption, design: .rounded, weight: .bold))
                        .foregroundStyle(step.phase.textTint)
                        .fixedSize()
                        .frame(minWidth: 31, minHeight: 31)
                        .padding(2)
                        .background(step.phase.tint.opacity(0.17), in: Circle())
                } else {
                    Circle()
                        .fill(step.phase.textTint)
                        .frame(width: 8, height: 8)
                        .frame(width: 20, height: 24)
                        .accessibilityHidden(true)
                }
                if !isLast {
                    Rectangle()
                        .fill(Color.hangLine)
                        .frame(width: 1, height: 44)
                }
            }

            VStack(alignment: .leading, spacing: 5) {
                HStack(alignment: .firstTextBaseline) {
                    Text(title)
                        .font(.system(.subheadline, design: .rounded, weight: .bold))
                        .foregroundStyle(Color.hangInk)
                    Spacer()
                    Text(step.durationLabel)
                        .font(.system(.caption, design: .rounded, weight: .bold))
                        .foregroundStyle(Color.hangMuted)
                }
                PlanStepInstructions(step: step)
                if let nextInstruction {
                    SectionLabel(title: "Up next")
                        .padding(.top, 5)
                    Text(nextInstruction)
                        .font(.system(.footnote, design: .rounded, weight: .medium))
                        .foregroundStyle(Color.hangMuted)
                        .fixedSize(horizontal: false, vertical: true)
                }
            }
            .padding(.bottom, isLast ? 0 : 12)
        }
        .accessibilityElement(children: .contain)
        .accessibilityIdentifier("plan.flow.step.\(step.id)")
    }
}

private struct PlanStepInstructions: View {
    let step: WorkoutStep

    var body: some View {
        ForEach(
            Array(InstructionAccessoryCardContent.rows(
                instruction: step.instruction,
                accessory: step.accessory
            ).enumerated()),
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
}
