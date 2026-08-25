import SwiftUI

struct CustomRoutineEditorView: View {
    @Environment(\.dismiss) private var dismiss

    private let onSave: (CustomRoutineDefinition) throws -> Void
    private let metadataOptions = CustomRoutineMetadataOptions()
    @State private var draft: CustomRoutineDraft
    @State private var selectedMode: EditorTargetMode
    @State private var selectedBoardID: String
    @State private var validationErrors: [String] = []
    @State private var persistenceError: String?

    init(
        draft: CustomRoutineDraft,
        onSave: @escaping (CustomRoutineDefinition) throws -> Void
    ) {
        self.onSave = onSave
        _draft = State(initialValue: draft)

        switch draft.targetMode {
        case let .boardSpecific(boardID):
            _selectedMode = State(initialValue: .boardSpecific)
            _selectedBoardID = State(initialValue: boardID)
        case .generic:
            _selectedMode = State(initialValue: .generic)
            _selectedBoardID = State(initialValue: BoardCatalog.defaultBoard.id)
        }
    }

    private var isExistingRoutine: Bool {
        draft.id != nil
    }

    private var selectedBoard: TrainingBoard {
        BoardCatalog.board(for: selectedBoardID)
    }

    private var isBoardSpecific: Bool {
        if case .boardSpecific = draft.targetMode {
            return true
        }
        return false
    }

    var body: some View {
        NavigationStack {
            List {
                routineSection
                stepsSection
            }
            .navigationTitle(isExistingRoutine ? "Edit routine" : "Create routine")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") {
                        dismiss()
                    }
                }
                ToolbarItem(placement: .topBarTrailing) {
                    EditButton()
                        .accessibilityIdentifier("customRoutine.reorder")
                }
            }
            .alert("Couldn’t save routine", isPresented: persistenceAlertBinding) {
                Button("OK", role: .cancel) {
                    persistenceError = nil
                }
            } message: {
                Text(persistenceError ?? "An unknown persistence error occurred.")
            }
        }
    }

    private var routineSection: some View {
        Section("Routine") {
            Picker("Target mode", selection: $selectedMode) {
                ForEach(EditorTargetMode.allCases) { mode in
                    Text(mode.label).tag(mode)
                }
            }
            .pickerStyle(.segmented)
            .disabled(isExistingRoutine)
            .accessibilityIdentifier("customRoutine.targetMode")
            .onChange(of: selectedMode) { _, mode in
                replaceDraftTargetMode(mode: mode, boardID: selectedBoardID)
            }

            if isBoardSpecific {
                Picker("Board", selection: $selectedBoardID) {
                    ForEach(BoardCatalog.all) { board in
                        Text(board.name).tag(board.id)
                    }
                }
                .accessibilityIdentifier("customRoutine.board")
                .disabled(isExistingRoutine)
                .onChange(of: selectedBoardID) { _, boardID in
                    replaceDraftTargetMode(mode: .boardSpecific, boardID: boardID)
                }
            }

            TextField("Name", text: $draft.title)
                .accessibilityIdentifier("customRoutine.name")
            TextField("Description", text: $draft.subtitle, axis: .vertical)
                .accessibilityIdentifier("customRoutine.description")
            Picker("Difficulty", selection: $draft.difficulty) {
                Text("None").tag(String?.none)
                ForEach(metadataOptions.difficulties, id: \.self) { difficulty in
                    Text(difficulty).tag(Optional(difficulty))
                }
            }
                .accessibilityIdentifier("customRoutine.difficulty")
            Picker("Category", selection: $draft.category) {
                Text("None").tag(String?.none)
                ForEach(metadataOptions.categories, id: \.self) { category in
                    Text(category).tag(Optional(category))
                }
            }
                .accessibilityIdentifier("customRoutine.category")
            TextField("Tags (comma separated)", text: $draft.tagsText)
                .accessibilityIdentifier("customRoutine.tags")
        }
    }

    private var stepsSection: some View {
        Section("Steps") {
            ForEach(draft.steps) { step in
                CustomRoutineStepEditor(
                    step: binding(for: step),
                    targetMode: draft.targetMode,
                    board: selectedBoard
                )
            }
            .onMove { offsets, destination in
                draft.moveSteps(from: offsets, to: destination)
            }
            .onDelete { offsets in
                draft.removeSteps(at: offsets)
            }

            Button {
                draft.addStep()
            } label: {
                Label("Add step", systemImage: "plus")
            }
            .accessibilityIdentifier("customRoutine.addStep")

            if !validationErrors.isEmpty {
                VStack(alignment: .leading, spacing: 4) {
                    ForEach(validationErrors, id: \.self) { error in
                        Text(error)
                    }
                }
                .font(.footnote)
                .foregroundStyle(.red)
            }

            Button("Save", action: save)
                .accessibilityIdentifier("customRoutine.save")
        }
        .accessibilityIdentifier("customRoutine.steps")
    }

    private var persistenceAlertBinding: Binding<Bool> {
        Binding(
            get: { persistenceError != nil },
            set: { isPresented in
                if !isPresented {
                    persistenceError = nil
                }
            }
        )
    }

    private func binding(for step: CustomRoutineStepDraft) -> Binding<CustomRoutineStepDraft> {
        Binding(
            get: { draft.steps.first(where: { $0.id == step.id }) ?? step },
            set: { draft.updateStep($0) }
        )
    }

    private func replaceDraftTargetMode(mode: EditorTargetMode, boardID: String) {
        guard !isExistingRoutine else {
            return
        }

        let targetMode: CustomRoutineTargetMode = switch mode {
        case .boardSpecific:
            .boardSpecific(boardID: boardID)
        case .generic:
            .generic
        }
        guard targetMode != draft.targetMode else {
            return
        }

        draft = draft.retargeted(to: targetMode)
    }

    private func save() {
        let definition = draft.definition()
        let issues = Self.localValidationIssues(for: definition)
        guard issues.isEmpty else {
            validationErrors = issues
            return
        }

        validationErrors = []
        do {
            try onSave(definition)
            dismiss()
        } catch {
            persistenceError = error.localizedDescription
        }
    }

    static func localValidationIssues(for definition: CustomRoutineDefinition) -> [String] {
        var issues: [String] = []
        if definition.title.isEmpty {
            issues.append("A routine name is required.")
        }
        if definition.steps.isEmpty {
            issues.append("Add at least one step.")
        }
        for (index, step) in definition.steps.enumerated() where !step.duration.isFinite || step.duration <= 0 {
            issues.append("Step \(index + 1) needs a positive duration.")
        }
        for (index, step) in definition.steps.enumerated() where step.phase != .rest && step.targets.isEmpty {
            issues.append("Step \(index + 1) needs a hold target.")
        }
        return issues
    }
}

private enum EditorTargetMode: String, CaseIterable, Identifiable {
    case boardSpecific
    case generic

    var id: String { rawValue }

    var label: String {
        switch self {
        case .boardSpecific: "Board-specific"
        case .generic: "Generic"
        }
    }
}

private struct CustomRoutineStepEditor: View {
    @Binding var step: CustomRoutineStepDraft
    let targetMode: CustomRoutineTargetMode
    let board: TrainingBoard

    @State private var activeHoldID: String?

    private var isBoardSpecific: Bool {
        if case .boardSpecific = targetMode {
            return true
        }
        return false
    }

    private var selectedHoldIDs: Set<String> {
        Set(step.targets.flatMap { target in
            if case let .holdIDs(ids) = target {
                return ids
            }
            return []
        })
    }

    var body: some View {
        DisclosureGroup(step.title.isEmpty ? "New step" : step.title) {
            TextField("Step title", text: $step.title)
                .accessibilityIdentifier("customRoutine.stepTitle")
            TextField("Instruction", text: $step.instruction, axis: .vertical)
                .accessibilityIdentifier("customRoutine.stepInstruction")

            Picker("Phase", selection: $step.phase) {
                ForEach(WorkoutPhase.allCases) { phase in
                    Text(phase.label).tag(phase)
                }
            }
            .accessibilityIdentifier("customRoutine.stepPhase")
            .onChange(of: step.phase) { _, phase in
                if phase == .rest {
                    step.targets = []
                    step.timing = .fixed
                }
            }

            TextField("Duration (seconds)", value: $step.duration, format: .number)
                .keyboardType(.decimalPad)
                .accessibilityIdentifier("customRoutine.stepDuration")

            if step.isRest {
                LabeledContent("Timing") {
                    Text(WorkoutSegmentTiming.fixed.label)
                }
                .accessibilityIdentifier("customRoutine.stepTiming")
            } else {
                Picker("Timing", selection: $step.timing) {
                    ForEach(WorkoutSegmentTiming.allCases) { timing in
                        Text(timing.label).tag(timing)
                    }
                }
                .accessibilityIdentifier("customRoutine.stepTiming")
            }

            if !step.isRest {
                targetEditor
            }
        }
    }

    @ViewBuilder
    private var targetEditor: some View {
        if isBoardSpecific {
            VStack(alignment: .leading, spacing: 8) {
                Text("Select exact holds")
                    .font(.subheadline.weight(.semibold))
                BoardMapView(
                    board: board,
                    highlightedHoldIDs: selectedHoldIDs,
                    activeHoldID: activeHoldID,
                    onHoldTap: toggleHold
                )
            }
        } else {
            Picker("Target", selection: genericTargetBinding) {
                Text("Choose target").tag(GenericTargetChoice?.none)
                Section("Hold kind") {
                    ForEach(HoldKind.allCases) { kind in
                        Text(kind.label).tag(Optional(GenericTargetChoice.kind(kind)))
                    }
                }
                Section("Hold feature") {
                    ForEach(HoldFeature.allCases) { feature in
                        Text(feature.label).tag(Optional(GenericTargetChoice.feature(feature)))
                    }
                }
            }
            .accessibilityIdentifier("customRoutine.stepTarget")
        }
    }

    private var genericTargetBinding: Binding<GenericTargetChoice?> {
        Binding(
            get: {
                guard let target = step.targets.first else { return nil }
                switch target {
                case let .kind(kind):
                    return .kind(kind)
                case let .feature(feature, _, _):
                    return .feature(feature)
                default:
                    return nil
                }
            },
            set: { choice in
                step.targets = choice.map { [$0.target] } ?? []
            }
        )
    }

    private func toggleHold(_ hold: BoardHold) {
        activeHoldID = hold.id
        var holdIDs = selectedHoldIDs
        if !holdIDs.insert(hold.id).inserted {
            holdIDs.remove(hold.id)
        }
        step.targets = holdIDs.isEmpty
            ? []
            : [.holdIDs(board.holds.compactMap { holdIDs.contains($0.id) ? $0.id : nil })]
    }
}

private enum GenericTargetChoice: Hashable {
    case kind(HoldKind)
    case feature(HoldFeature)

    var target: WorkoutTargetDefinition {
        switch self {
        case let .kind(kind):
            .kind(kind)
        case let .feature(feature):
            .feature(feature, fallbacks: [])
        }
    }
}
