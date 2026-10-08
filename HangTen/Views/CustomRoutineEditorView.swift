import SwiftUI

struct CustomRoutineEditorView: View {
    @Environment(\.dismiss) private var dismiss

    private let onSave: (CustomRoutineDefinition) throws -> Void
    private let metadataOptions = CustomRoutineMetadataOptions()
    @State private var draft: CustomRoutineDraft
    @State private var selectedMode: EditorTargetMode
    @State private var selectedBoardID: String
    @State private var persistenceError: String?
    @State private var hasAttemptedSave = false
    @State private var validationScrollRequest = 0
    @State private var editMode = EditMode.inactive
    @State private var editingSet: CustomRoutineSet?

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

    private var selectedBoard: BoardRevision {
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
            ScrollViewReader { scrollProxy in
                List {
                    if !validationIssues.isEmpty {
                        Section("Check routine") {
                            Text(validationIssues.joined(separator: "\n"))
                                .foregroundStyle(.red)
                                .accessibilityIdentifier("customRoutine.validationErrors")
                        }
                        .id("customRoutine.validation")
                    }
                    routineSection
                    stepsSection
                }
                .environment(\.editMode, $editMode)
                .scrollContentBackground(.hidden)
                .background(Color.hangBackground)
                .onChange(of: draft.editorItems.count) { _, count in
                    if count < 2 { editMode = .inactive }
                }
                .onChange(of: validationScrollRequest) { _, _ in
                    guard !validationIssues.isEmpty else { return }
                    withAnimation {
                        scrollProxy.scrollTo("customRoutine.validation", anchor: .top)
                    }
                }
                .navigationTitle(isExistingRoutine ? "Edit routine" : "Create routine")
                .navigationBarTitleDisplayMode(.inline)
                .toolbar {
                    ToolbarItem(placement: .cancellationAction) {
                        Button("Cancel") {
                            dismiss()
                        }
                    }
                    ToolbarItem(placement: .confirmationAction) {
                        Button("Save") {
                            save()
                            if !validationIssues.isEmpty {
                                validationScrollRequest += 1
                            }
                        }
                        .buttonStyle(.borderedProminent)
                        .tint(.hangGreenDark)
                        .accessibilityIdentifier("customRoutine.save")
                    }
                }
                .alert("Couldn’t save routine", isPresented: persistenceAlertBinding) {
                    Button("OK", role: .cancel) {
                        persistenceError = nil
                    }
                } message: {
                    Text(persistenceError ?? "An unknown persistence error occurred.")
                }
                .sheet(item: $editingSet) { set in
                    CustomRoutineSetEditor(
                        set: set,
                        steps: draft.steps,
                        otherSets: draft.sets.filter { $0.id != set.id },
                        minimumStepCount: set.stepIDs.count > 1 ? 2 : 1,
                        isNew: !draft.sets.contains(where: { $0.id == set.id }),
                        onSave: { draft.updateSet($0) }
                    )
                }
            }
        }
    }

    private var validationIssues: [String] {
        hasAttemptedSave ? Self.localValidationIssues(for: draft.definition()) : []
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
        Section {
            ForEach(draft.editorItems) { item in
                editorItem(item)
                .deleteDisabled(editMode.isEditing)
            }
            .onMove { offsets, destination in
                draft.moveEditorItems(from: offsets, to: destination)
            }
            .onDelete { offsets in
                draft.removeEditorItems(at: offsets)
            }

            Button {
                draft.addStep()
            } label: {
                Label("Add step", systemImage: "plus")
            }
            .accessibilityIdentifier("customRoutine.addStep")

            Button {
                editingSet = draft.newSet()
            } label: {
                Label("Create set", systemImage: "repeat")
            }
            .disabled(draft.newSet() == nil)
            .accessibilityIdentifier("customRoutine.addSet")

        } header: {
            HStack {
                Text("Steps")
                    .accessibilityIdentifier("customRoutine.steps")
                Spacer()
                if draft.editorItems.count > 1 {
                    Button(editMode.isEditing ? "Done" : "Reorder") {
                        withAnimation {
                            editMode = editMode.isEditing ? .inactive : .active
                        }
                    }
                    .buttonStyle(.plain)
                    .font(.system(.footnote, design: .rounded, weight: .semibold))
                    .foregroundStyle(Color.hangGreenDark)
                    .frame(minHeight: 44)
                    .accessibilityIdentifier("customRoutine.reorder")
                }
            }
            .textCase(nil)
        } footer: {
            Text("Combine consecutive steps into a set to repeat them together. Sets move together when reordered.")
        }
    }

    @ViewBuilder
    /// Renders one editable row, with a shared count and child forms when the row represents a set.
    private func editorItem(_ item: CustomRoutineEditorItem) -> some View {
        switch item {
        case let .step(step):
            stepEditor(step)
        case let .set(set, steps):
            DisclosureGroup {
                Stepper(value: setCountBinding(for: set), in: CustomRoutineSet.supportedCounts) {
                    Text("Repeat \(set.repeatCount) \(set.repeatCount == 1 ? "time" : "times")")
                }
                .accessibilityIdentifier("customRoutine.setRepeatCount")

                Button("Edit set") {
                    editingSet = set
                }
                .buttonStyle(.borderless)
                .accessibilityIdentifier("customRoutine.editSet")

                ForEach(steps) { step in
                    stepEditor(step, inSet: true)
                }

                Button("Ungroup set") {
                    draft.removeSet(id: set.id)
                }
                .buttonStyle(.borderless)
                .accessibilityIdentifier("customRoutine.ungroupSet")
            } label: {
                VStack(alignment: .leading, spacing: 4) {
                    Label("Set", systemImage: "repeat")
                    Text("Repeat \(set.repeatCount) \(set.repeatCount == 1 ? "time" : "times")")
                        .font(.subheadline)
                    Text(steps.map { $0.title.isEmpty ? "New step" : $0.title }.joined(separator: " → "))
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
            }
        }
    }

    /// Connects a child form to its authored step and set, including explicit removal inside grouped rows.
    private func stepEditor(_ step: CustomRoutineStepDraft, inSet: Bool = false) -> some View {
        CustomRoutineStepEditor(
            step: binding(for: step),
            routineSet: setBinding(for: step),
            targetMode: draft.targetMode,
            board: selectedBoard,
            onAddPair: { draft.addLeftAndRightPair(from: $0, board: selectedBoard) },
            onEditSet: { editingSet = $0 },
            onRemove: inSet ? {
                if let index = draft.steps.firstIndex(where: { $0.id == step.id }) {
                    draft.removeSteps(at: IndexSet(integer: index))
                }
            } : nil,
            setSummary: inSet ? nil : draft.sets.first(where: { $0.stepIDs.contains(step.id) }).map(setSummary)
        )
    }

    /// Reads and updates the current set by identity rather than mutating a captured row snapshot.
    private func setCountBinding(for set: CustomRoutineSet) -> Binding<Int> {
        Binding(
            get: { draft.sets.first(where: { $0.id == set.id })?.repeatCount ?? set.repeatCount },
            set: { count in
                if var existing = draft.sets.first(where: { $0.id == set.id }) {
                    existing.repeatCount = count
                    draft.updateSet(existing)
                }
            }
        )
    }

    /// Summarizes the authored step range and total run count for an inline repeat label.
    private func setSummary(_ set: CustomRoutineSet) -> String {
        guard let range = set.range(in: draft.steps.map(\.id)) else { return "Choose steps to repeat" }
        let steps = range.count == 1 ? "Step \(range.lowerBound + 1)" : "Steps \(range.lowerBound + 1)–\(range.upperBound)"
        return "\(steps) · \(set.repeatCount) \(set.repeatCount == 1 ? "time" : "times")"
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

    /// Binds shared set metadata and permits disabling repeats only for a single-step set.
    private func setBinding(for step: CustomRoutineStepDraft) -> Binding<CustomRoutineSet?> {
        Binding(
            get: { draft.sets.first(where: { $0.stepIDs.contains(step.id) }) },
            set: { set in
                if let set {
                    draft.updateSet(set)
                } else if let existing = draft.sets.first(where: { $0.stepIDs == [step.id] }) {
                    draft.removeSet(id: existing.id)
                }
            }
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
        hasAttemptedSave = true
        let definition = draft.definition()
        let issues = Self.localValidationIssues(for: definition)
        guard issues.isEmpty else { return }

        do {
            try onSave(definition)
            dismiss()
        } catch {
            persistenceError = error.localizedDescription
        }
    }

    /// Builds immediate editor feedback for missing fields, invalid step semantics, and malformed sets.
    static func localValidationIssues(for definition: CustomRoutineDefinition) -> [String] {
        var issues: [String] = []
        if definition.title.isEmpty {
            issues.append("A routine name is required.")
        }
        if definition.steps.isEmpty {
            issues.append("Add at least one step.")
        } else if CustomRoutineValidator.terminalRestIssue(for: definition) == .terminalRestStep {
            issues.append("End the routine with a work step.")
        }
        for (index, step) in definition.steps.enumerated() where !step.duration.isFinite || step.duration <= 0 {
            issues.append("Step \(index + 1) needs a positive duration.")
        }
        for (index, step) in definition.steps.enumerated() where step.phase != .rest && step.workRequirements.isEmpty {
            issues.append("Step \(index + 1) needs a hold target.")
        }
        for (index, step) in definition.steps.enumerated() where !WorkoutStepSemantics.hasValidHandUseAndSide(step.handUse, step.side) {
            issues.append("Step \(index + 1) needs a side compatible with its hand use.")
        }
        for (index, step) in definition.steps.enumerated() where !WorkoutStepSemantics.hasValidActionAndRepetitions(step.action, step.repetitions) {
            issues.append("Step \(index + 1) needs positive repetitions for a loaded lift.")
        }
        for (index, step) in definition.steps.enumerated() where !WorkoutStepSemantics.hasValidExternalLoad(step.externalLoadKGF) {
            issues.append("Step \(index + 1) needs a finite external load.")
        }
        for issue in CustomRoutineValidator.setIssues(for: definition) {
            switch issue {
            case let .invalidSetRepeatCount(index):
                issues.append("Set \(index + 1) needs a repeat count from 1 to 100.")
            case let .overlappingSetSteps(index):
                issues.append("Set \(index + 1) overlaps another set.")
            case let .invalidSetSteps(index), let .duplicateSetID(index):
                issues.append("Set \(index + 1) needs consecutive steps.")
            default: break
            }
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
    @Binding var routineSet: CustomRoutineSet?
    let targetMode: CustomRoutineTargetMode
    let board: BoardRevision
    let onAddPair: (CustomRoutineStepDraft) -> Void
    let onEditSet: (CustomRoutineSet) -> Void
    let onRemove: (() -> Void)?
    let setSummary: String?

    @State private var activeHoldID: String?
    @State private var genericDepthSelection: GenericDepthSelection = .none
    @State private var exactDepthMinimum = ""
    @State private var exactDepthMaximum = ""

    private var isBoardSpecific: Bool {
        if case .boardSpecific = targetMode {
            return true
        }
        return false
    }

    private var selectedHoldIDs: Set<String> {
        CustomRoutineBoardPreview.contactIDs(for: step, on: board)
    }

    var body: some View {
        DisclosureGroup {
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
                    step.handUse = .double
                    step.side = .both
                    step.action = .hang
                    step.repetitions = nil
                    step.externalLoadKGF = nil
                } else if phase == .pull && step.handUse == .either {
                    step.transitionHandUse(to: .double)
                }
            }

            TextField("Duration (seconds)", value: $step.duration, format: .number)
                .keyboardType(.decimalPad)
                .accessibilityIdentifier("customRoutine.stepDuration")

            repeatControls

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
                Picker("Action", selection: $step.action) {
                    Text("Hang").tag(WorkoutAction.hang)
                    Text("Isometric pull").tag(WorkoutAction.isometricPull)
                    Text("Loaded lift").tag(WorkoutAction.loadedLift)
                }
                .onChange(of: step.action) { _, action in
                    step.repetitions = action == .loadedLift ? max(step.repetitions ?? 1, 1) : nil
                    if action == .isometricPull && step.handUse == .either {
                        step.transitionHandUse(to: .double)
                    }
                }
                .accessibilityIdentifier("customRoutine.stepAction")

                Picker("Hand use", selection: $step.handUse) {
                    Text("Single hand").tag(WorkoutHandUse.single)
                    if step.phase != .pull && step.action != .isometricPull {
                        Text("Either hand (choose at start)").tag(WorkoutHandUse.either)
                    }
                    Text("Both hands").tag(WorkoutHandUse.double)
                }
                .onChange(of: step.handUse) { _, handUse in
                    step.transitionHandUse(to: handUse)
                }
                .accessibilityIdentifier("customRoutine.stepHandUse")

                Picker("Side", selection: $step.side) {
                    if step.handUse == .single {
                        Text("Left").tag(WorkoutSide.left)
                        Text("Right").tag(WorkoutSide.right)
                    } else {
                        Text("Both").tag(WorkoutSide.both)
                    }
                }
                .accessibilityIdentifier("customRoutine.stepSide")

                if step.action == .loadedLift {
                    TextField("Repetitions", value: $step.repetitions, format: .number)
                        .keyboardType(.numberPad)
                        .accessibilityIdentifier("customRoutine.stepRepetitions")
                    TextField("External load (kg; negative is assistance)", value: $step.externalLoadKGF, format: .number)
                        .keyboardType(.numbersAndPunctuation)
                        .accessibilityIdentifier("customRoutine.stepExternalLoad")
                }

                Button("Add left + right pair") {
                    onAddPair(step)
                }
                .accessibilityIdentifier("customRoutine.addLeftRightPair")

                targetEditor
            }

            if let onRemove {
                Button("Remove step", role: .destructive, action: onRemove)
                    .buttonStyle(.borderless)
                    .accessibilityIdentifier("customRoutine.removeSetStep")
            }
        } label: {
            VStack(alignment: .leading, spacing: 4) {
                Text(step.title.isEmpty ? "New step" : step.title)
                if let setSummary {
                    Label(setSummary, systemImage: "repeat")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
            }
        }
    }

    private var isInSet: Bool {
        (routineSet?.stepIDs.count ?? 0) > 1
    }

    private var repeatEnabledBinding: Binding<Bool> {
        Binding(
            get: { routineSet != nil },
            set: { enabled in
                guard !isInSet else { return }
                if enabled {
                    if routineSet == nil {
                        routineSet = CustomRoutineSet(stepIDs: [step.id])
                    }
                } else {
                    routineSet = nil
                }
            }
        )
    }

    private var repeatCountBinding: Binding<Int> {
        Binding(
            get: { routineSet?.repeatCount ?? 2 },
            set: { count in
                guard var set = routineSet, set.stepIDs == [step.id] else { return }
                set.repeatCount = count
                routineSet = set
            }
        )
    }

    @ViewBuilder
    private var repeatControls: some View {
        if isInSet {
            if let routineSet {
                Button("Edit set") {
                    onEditSet(routineSet)
                }
                .buttonStyle(.borderless)
                .accessibilityIdentifier("customRoutine.editStepSet")
            }
        } else {
            Toggle("Repeat", isOn: repeatEnabledBinding)
                .tint(.hangGreenDark)
                .accessibilityIdentifier("customRoutine.stepRepeat")

            if let routineSet {
                Stepper(value: repeatCountBinding, in: CustomRoutineSet.supportedCounts) {
                    Text("Run \(routineSet.repeatCount) \(routineSet.repeatCount == 1 ? "time" : "times")")
                }
                .accessibilityIdentifier("customRoutine.stepRepeatCount")
                Text("The count includes the first run.")
                    .font(.caption)
                    .foregroundStyle(.secondary)
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
                    selectedPresentationID: CustomRoutineBoardPreview.presentationID(for: step, on: board),
                    activeHoldID: activeHoldID,
                    onHoldTap: toggleHold
                )
            }
        } else {
            Group {
            Picker("Hold kind", selection: genericKindBinding) {
                Text("Choose target").tag(HoldKind?.none)
                ForEach(HoldKind.allCases) { kind in
                    Text(kind.label).tag(Optional(kind))
                }
            }
            .accessibilityIdentifier("customRoutine.stepTarget")

            if let kind = genericKind, !Self.supportedShapes(for: kind).isEmpty {
                Picker("Hold shape", selection: genericShapeBinding) {
                    Text("Any shape").tag(HoldShape?.none)
                    ForEach(Self.supportedShapes(for: kind)) { shape in
                        Text(shape.label).tag(Optional(shape))
                    }
                }
                .accessibilityIdentifier("customRoutine.stepShape")
            }

            if genericKind != nil {
                Picker("Hold depth", selection: $genericDepthSelection) {
                    Text("Any depth").tag(GenericDepthSelection.none)
                    Section("Size") {
                        ForEach(HoldSize.allCases) { size in
                            Text(size.label).tag(GenericDepthSelection.category(size))
                        }
                    }
                    Text("Exact range (mm)").tag(GenericDepthSelection.exactRange)
                }
                .accessibilityIdentifier("customRoutine.stepDepth")
                .onChange(of: genericDepthSelection) { _, selection in
                    switch selection {
                    case .none:
                        replaceGenericTarget(depth: nil)
                    case let .category(size):
                        replaceGenericTarget(depth: .category(size))
                    case .exactRange:
                        loadExactDepthFields()
                        updateExactDepthFromFields()
                    }
                }

                if genericDepthSelection == .exactRange {
                    TextField("Minimum depth (mm)", text: $exactDepthMinimum)
                        .keyboardType(.decimalPad)
                        .accessibilityIdentifier("customRoutine.stepDepthMinimum")
                        .onChange(of: exactDepthMinimum) { _, _ in updateExactDepthFromFields() }
                    TextField("Maximum depth (mm)", text: $exactDepthMaximum)
                        .keyboardType(.decimalPad)
                        .accessibilityIdentifier("customRoutine.stepDepthMaximum")
                        .onChange(of: exactDepthMaximum) { _, _ in updateExactDepthFromFields() }
                }
            }
            }
            .onAppear(perform: configureGenericDepthSelection)
        }
    }

    private var genericKind: HoldKind? {
        step.targets.first?.kind
    }

    private var genericKindBinding: Binding<HoldKind?> {
        Binding(
            get: { genericKind },
            set: { kind in
                guard let kind else {
                    step.targets = []
                    genericDepthSelection = .none
                    return
                }
                let current = step.targets.first
                let shape = current?.shape.flatMap { Self.supportedShapes(for: kind).contains($0) ? $0 : nil }
                step.targets = [
                    ContactRequirement(
                        kind: kind,
                        shape: shape,
                        depth: current?.depth,
                        fingerCapacity: current?.fingerCapacity,
                        handCapacity: current?.handCapacity,
                        selection: .single
                    )
                ]
                configureGenericDepthSelection()
            }
        )
    }

    private var genericShapeBinding: Binding<HoldShape?> {
        Binding(
            get: { step.targets.first?.shape },
            set: { replaceGenericTarget(shape: $0) }
        )
    }

    private func replaceGenericTarget(shape: HoldShape?) {
        guard let current = step.targets.first else { return }
        step.targets = [
            ContactRequirement(
                kind: current.kind,
                shape: shape,
                depth: current.depth,
                fingerCapacity: current.fingerCapacity,
                handCapacity: current.handCapacity,
                selection: .single
            )
        ]
    }

    private func replaceGenericTarget(depth: HoldDepth?) {
        guard let current = step.targets.first else { return }
        step.targets = [
            ContactRequirement(
                kind: current.kind,
                shape: current.shape,
                depth: depth,
                fingerCapacity: current.fingerCapacity,
                handCapacity: current.handCapacity,
                selection: .single
            )
        ]
    }

    private func configureGenericDepthSelection() {
        guard let depth = step.targets.first?.depth else {
            genericDepthSelection = .none
            exactDepthMinimum = ""
            exactDepthMaximum = ""
            return
        }
        switch depth {
        case let .category(size):
            genericDepthSelection = .category(size)
        case let .range(range):
            genericDepthSelection = .exactRange
            exactDepthMinimum = range.minimum.formatted()
            exactDepthMaximum = range.maximum.formatted()
        }
    }

    private func loadExactDepthFields() {
        if case let .range(range)? = step.targets.first?.depth {
            exactDepthMinimum = range.minimum.formatted()
            exactDepthMaximum = range.maximum.formatted()
        }
    }

    private func updateExactDepthFromFields() {
        guard let minimum = Double(exactDepthMinimum),
              let maximum = Double(exactDepthMaximum),
              minimum > 0,
              maximum >= minimum else {
            replaceGenericTarget(depth: nil)
            return
        }
        replaceGenericTarget(depth: .range(.init(minimum: minimum, maximum: maximum)))
    }

    private static func supportedShapes(for kind: HoldKind) -> [HoldShape] {
        switch kind {
        case .edge:
            [.flat, .incut, .slot]
        case .sloper, .pinch, .jug:
            [.flat, .round]
        case .pocket, .gaston:
            []
        }
    }

    private func toggleHold(_ hold: PhysicalContact) {
        activeHoldID = hold.id
        CustomRoutineBoardPreview.toggle(hold, in: &step, on: board)
    }
}

private struct CustomRoutineSetEditor: View {
    @Environment(\.dismiss) private var dismiss
    let set: CustomRoutineSet
    let steps: [CustomRoutineStepDraft]
    let otherSets: [CustomRoutineSet]
    let minimumStepCount: Int
    let isNew: Bool
    let onSave: (CustomRoutineSet) -> Void

    @State private var firstStepID: String
    @State private var lastStepID: String
    @State private var repeatCount: Int

    /// Seeds the set sheet from the selected range and count, enforcing its required number of members.
    init(
        set: CustomRoutineSet,
        steps: [CustomRoutineStepDraft],
        otherSets: [CustomRoutineSet],
        minimumStepCount: Int,
        isNew: Bool,
        onSave: @escaping (CustomRoutineSet) -> Void
    ) {
        self.set = set
        self.steps = steps
        self.otherSets = otherSets
        self.minimumStepCount = minimumStepCount
        self.isNew = isNew
        self.onSave = onSave
        _firstStepID = State(initialValue: set.stepIDs.first ?? "")
        _lastStepID = State(initialValue: set.stepIDs.last ?? "")
        _repeatCount = State(initialValue: set.repeatCount)
    }

    private var availableIndices: [Int] {
        let usedIDs = Set(otherSets.flatMap(\.stepIDs))
        return steps.indices.filter { !usedIDs.contains(steps[$0].id) }
    }

    private var endIndices: [Int] {
        guard let start = steps.firstIndex(where: { $0.id == firstStepID }) else { return [] }
        let available = Set(availableIndices)
        return Array(steps.indices.dropFirst(start).prefix { available.contains($0) })
    }

    private var selectedStepIDs: [String] {
        guard let start = steps.firstIndex(where: { $0.id == firstStepID }),
              let end = endIndices.first(where: { steps[$0].id == lastStepID }) else { return [] }
        return steps[start...end].map(\.id)
    }

    var body: some View {
        NavigationStack {
            Form {
                Section(minimumStepCount > 1 ? "Steps in set" : "Steps to repeat") {
                    Picker("From step", selection: $firstStepID) {
                        ForEach(availableIndices, id: \.self) { index in
                            Text(stepLabel(at: index)).tag(steps[index].id)
                        }
                    }
                    .pickerStyle(.navigationLink)
                    .accessibilityIdentifier("customRoutine.setStart")
                    .onChange(of: firstStepID) { _, _ in
                        if !endIndices.contains(where: { steps[$0].id == lastStepID }) {
                            lastStepID = firstStepID
                        }
                    }
                    Picker("Through step", selection: $lastStepID) {
                        ForEach(endIndices, id: \.self) { index in
                            Text(stepLabel(at: index)).tag(steps[index].id)
                        }
                    }
                    .pickerStyle(.navigationLink)
                    .accessibilityIdentifier("customRoutine.setEnd")
                }
                Section {
                    Stepper(value: $repeatCount, in: CustomRoutineSet.supportedCounts) {
                        Text("\(minimumStepCount > 1 ? "Repeat" : "Run") \(repeatCount) \(repeatCount == 1 ? "time" : "times")")
                    }
                    .accessibilityIdentifier("customRoutine.setCount")
                } footer: {
                    Text("The count includes the first run. Each repetition follows the selected steps in order.")
                }
                if selectedStepIDs.count >= minimumStepCount {
                    Section("One repetition") {
                        ForEach(steps.filter { selectedStepIDs.contains($0.id) }) { step in
                            LabeledContent(step.title.isEmpty ? "New step" : step.title) {
                                Text(step.isStopwatch ? "Stopwatch" : "\(step.duration.formatted())s")
                            }
                        }
                    }
                } else {
                    Text("Choose at least \(minimumStepCount) consecutive steps for the set.")
                        .foregroundStyle(.secondary)
                }
            }
            .scrollContentBackground(.hidden)
            .background(Color.hangBackground)
            .navigationTitle(minimumStepCount > 1 ? (isNew ? "Create set" : "Edit set") : "Repeat steps")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") { dismiss() }
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Done") {
                        onSave(CustomRoutineSet(id: set.id, stepIDs: selectedStepIDs, repeatCount: repeatCount))
                        dismiss()
                    }
                    .disabled(selectedStepIDs.count < minimumStepCount)
                    .accessibilityIdentifier("customRoutine.setSave")
                }
            }
        }
    }

    private func stepLabel(at index: Int) -> String {
        "\(index + 1). \(steps[index].title.isEmpty ? "New step" : steps[index].title)"
    }
}

private enum GenericDepthSelection: Hashable {
    case none
    case category(HoldSize)
    case exactRange
}
