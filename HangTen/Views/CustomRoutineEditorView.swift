import SwiftUI

struct CustomRoutineEditorView: View {
    @Environment(\.dismiss) private var dismiss

    private let onSave: (CustomRoutineDefinition) throws -> Void
    @State private var draft: CustomRoutineDraft
    @State private var selectedBoardID: String?
    @State private var persistenceError: String?
    @State private var hasAttemptedSave = false
    @State private var validationScrollRequest = 0
    @FocusState private var focusedField: String?
    @State private var editMode = EditMode.inactive
    @State private var collapsedSetIDs = Set<String>()
    @State private var collapsedCircuitIDs = Set<String>()

    /// Groups the editable copy by default while retaining persisted set identities and counts.
    init(
        draft: CustomRoutineDraft,
        onSave: @escaping (CustomRoutineDefinition) throws -> Void
    ) {
        self.onSave = onSave
        _draft = State(initialValue: draft.assigningDefaultSets())

        switch draft.targetMode {
        case .boardSpecific(let boardID):
            _selectedBoardID = State(initialValue: boardID)
        case .generic:
            _selectedBoardID = State(initialValue: nil)
        }
    }

    private var isExistingRoutine: Bool {
        draft.id != nil
    }

    private var selectedBoard: BoardRevision {
        BoardCatalog.board(for: selectedBoardID ?? BoardCatalog.defaultBoard.id)
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
                    setsSection
                }
                .environment(\.editMode, $editMode)
                .scrollDismissesKeyboard(.interactively)
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
                .onSubmit { focusedField = nil }
                .toolbar {
                    ToolbarItemGroup(placement: .keyboard) {
                        Spacer()
                        Button("Done") { focusedField = nil }
                            .accessibilityIdentifier("customRoutine.keyboardDone")
                    }
                    ToolbarItem(placement: .cancellationAction) {
                        Button("Cancel") {
                            dismiss()
                        }
                    }
                    ToolbarItem(placement: .confirmationAction) {
                        Button {
                            save()
                            if !validationIssues.isEmpty {
                                validationScrollRequest += 1
                            }
                        } label: {
                            Text("Save")
                                .fontWeight(.semibold)
                                .foregroundStyle(Color.hangGreenDark)
                        }
                        .buttonStyle(.plain)
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
            }
        }
    }

    private var validationIssues: [String] {
        hasAttemptedSave ? Self.localValidationIssues(for: draft) : []
    }

    private var routineSection: some View {
        Section("Routine") {
            Picker("Board", selection: $selectedBoardID) {
                Text("No board").tag(String?.none)
                ForEach(BoardCatalog.all) { board in
                    Text(board.name).tag(Optional(board.id))
                }
            }
            .pickerStyle(.menu)
            .modifier(CustomRoutineInputStyle())
            .disabled(isExistingRoutine)
            .accessibilityIdentifier("customRoutine.board")
            .onChange(of: selectedBoardID) { _, boardID in
                replaceDraftTargetMode(boardID: boardID)
            }

            CustomRoutineField("Name") {
                TextField("e.g. Metolius 10-minute · Entry", text: $draft.title)
                    .focused($focusedField, equals: "routine.name")
                    .accessibilityIdentifier("customRoutine.name")
            }
            CustomRoutineField("Description") {
                TextField("e.g. Ten 60-second hangboard sequences.", text: $draft.subtitle, axis: .vertical)
                    .focused($focusedField, equals: "routine.description")
                    .accessibilityIdentifier("customRoutine.description")
            }
        }
    }

    private var setsSection: some View {
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
                draft.addSet()
            } label: {
                Label("Add set", systemImage: "plus")
            }
            .accessibilityIdentifier("customRoutine.addSet")

            Button {
                draft.addCircuit()
            } label: {
                Label("Add circuit", systemImage: "plus")
            }
            .accessibilityIdentifier("customRoutine.addCircuit")

        } header: {
            HStack {
                Text("Sets & circuits")
                    .accessibilityIdentifier("customRoutine.sets")
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
            Text("Add exercises and rest steps to sets. Use a circuit to repeat sets together, with rest between rounds. Repeat counts include the first run.")
        }
    }

    @ViewBuilder
    /// Renders one editable row, with a shared count and child forms when the row represents a set.
    private func editorItem(_ item: CustomRoutineEditorItem) -> some View {
        switch item {
        case .step(let step):
            stepEditor(step)
        case .set(let set, let steps):
            setEditor(set, steps: steps)
        case .circuit(let circuit, let items):
            circuitEditor(circuit, items: items)
        }
    }

    private func setEditor(_ set: CustomRoutineSet, steps: [CustomRoutineStepDraft]) -> some View {
        let number = setNumber(for: set)
        return DisclosureGroup(isExpanded: setExpansionBinding(for: set)) {
            Stepper(value: setCountBinding(for: set), in: CustomRoutineSet.supportedCounts) {
                Text("Repeat \(set.repeatCount) \(set.repeatCount == 1 ? "time" : "times")")
            }
            .accessibilityIdentifier("customRoutine.setRepeatCount.\(number)")

            ForEach(steps) { step in
                stepEditor(step, inSet: true)
            }

            Button {
                draft.addStep(to: set.id)
            } label: {
                Label("Add step", systemImage: "plus")
            }
            .buttonStyle(.borderless)
            .accessibilityIdentifier("customRoutine.addSetStep.\(number)")

        } label: {
            VStack(alignment: .leading, spacing: 4) {
                Label("Set \(number)", systemImage: "repeat")
                if collapsedSetIDs.contains(set.id) {
                    Text("Repeat \(set.repeatCount) \(set.repeatCount == 1 ? "time" : "times")")
                        .font(.subheadline)
                    Text(steps.map(\.displayTitle).joined(separator: " → "))
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
            }
            .accessibilityElement(children: .combine)
            .accessibilityIdentifier("customRoutine.setHeader.\(number)")
        }
    }

    /// Numbers sets in visible order, independent of metadata order and explicitly ungrouped rows.
    private func setNumber(for set: CustomRoutineSet) -> Int {
        let ids = draft.steps.compactMap { step in
            draft.sets.first(where: { $0.stepIDs.first == step.id })?.id
        }
        return (ids.firstIndex(of: set.id) ?? 0) + 1
    }

    /// A circuit repeats its contained sets while keeping between-round recovery separate.
    private func circuitEditor(_ circuit: CustomRoutineCircuit, items: [CustomRoutineEditorItem]) -> some View {
        let number = circuitNumber(for: circuit)
        return DisclosureGroup(isExpanded: circuitExpansionBinding(for: circuit)) {
            Stepper(value: circuitCountBinding(for: circuit), in: CustomRoutineCircuit.supportedCounts) {
                Text("Repeat \(circuit.repeatCount) \(circuit.repeatCount == 1 ? "time" : "times")")
            }
            .accessibilityIdentifier("customRoutine.circuitRepeatCount.\(number)")

            CustomRoutineField("Rest between rounds") {
                HStack(spacing: 6) {
                    TextField("", value: circuitRestBinding(for: circuit), format: .number)
                        .keyboardType(.decimalPad)
                        .accessibilityLabel("Rest between rounds in seconds")
                        .accessibilityIdentifier("customRoutine.circuitRest.\(number)")
                        .focused($focusedField, equals: "\(circuit.id).circuitRest")
                    Text("sec").foregroundStyle(.secondary)
                }
            }

            Text("Rest is added between rounds, after any rest steps in your sets.")
                .font(.caption)
                .foregroundStyle(.secondary)

            ForEach(items) { item in
                circuitChild(item)
            }

            Button {
                draft.addSet(to: circuit.id)
            } label: {
                Label("Add set", systemImage: "plus")
            }
            .buttonStyle(.borderless)
            .accessibilityIdentifier("customRoutine.addCircuitSet.\(number)")
        } label: {
            VStack(alignment: .leading, spacing: 4) {
                Label("Circuit \(number)", systemImage: "repeat.circle")
                if collapsedCircuitIDs.contains(circuit.id) {
                    Text("\(circuit.setIDs.count) \(circuit.setIDs.count == 1 ? "set" : "sets") · Repeat \(circuit.repeatCount) \(circuit.repeatCount == 1 ? "time" : "times")")
                        .font(.subheadline)
                    if circuit.restBetweenRounds > 0 {
                        Text("\(circuit.restBetweenRounds.formatted(.number)) sec rest between rounds")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }
                }
            }
            .accessibilityElement(children: .combine)
            .accessibilityIdentifier("customRoutine.circuitHeader.\(number)")
        }
    }

    @ViewBuilder
    private func circuitChild(_ item: CustomRoutineEditorItem) -> some View {
        switch item {
        case .set(let set, let steps):
            setEditor(set, steps: steps)
        case .step(let step):
            stepEditor(step, inSet: true)
        case .circuit:
            EmptyView()
        }
    }

    private func circuitNumber(for circuit: CustomRoutineCircuit) -> Int {
        let ids = draft.editorItems.compactMap { item -> String? in
            guard case .circuit(let candidate, _) = item else { return nil }
            return candidate.id
        }
        return (ids.firstIndex(of: circuit.id) ?? 0) + 1
    }

    private func circuitExpansionBinding(for circuit: CustomRoutineCircuit) -> Binding<Bool> {
        Binding(
            get: { !collapsedCircuitIDs.contains(circuit.id) },
            set: { expanded in
                if expanded {
                    collapsedCircuitIDs.remove(circuit.id)
                } else {
                    collapsedCircuitIDs.insert(circuit.id)
                }
            }
        )
    }

    private func circuitCountBinding(for circuit: CustomRoutineCircuit) -> Binding<Int> {
        Binding(
            get: { draft.circuits.first(where: { $0.id == circuit.id })?.repeatCount ?? circuit.repeatCount },
            set: { count in
                if var existing = draft.circuits.first(where: { $0.id == circuit.id }) {
                    existing.repeatCount = count
                    draft.updateCircuit(existing)
                }
            }
        )
    }

    private func circuitRestBinding(for circuit: CustomRoutineCircuit) -> Binding<TimeInterval?> {
        Binding(
            get: {
                let value = draft.circuits.first(where: { $0.id == circuit.id })?.restBetweenRounds ?? 0
                return value == 0 ? nil : value
            },
            set: { duration in
                if var existing = draft.circuits.first(where: { $0.id == circuit.id }) {
                    existing.restBetweenRounds = duration ?? 0
                    draft.updateCircuit(existing)
                }
            }
        )
    }

    /// Newly created and reopened sets expose their controls and children until explicitly collapsed.
    private func setExpansionBinding(for set: CustomRoutineSet) -> Binding<Bool> {
        Binding(
            get: { !collapsedSetIDs.contains(set.id) },
            set: { expanded in
                if expanded {
                    collapsedSetIDs.remove(set.id)
                } else {
                    collapsedSetIDs.insert(set.id)
                }
            }
        )
    }

    /// Connects a child form to its authored step and set, including explicit removal inside grouped rows.
    private func stepEditor(_ step: CustomRoutineStepDraft, inSet: Bool = false) -> some View {
        CustomRoutineStepEditor(
            step: binding(for: step),
            focusedField: $focusedField,
            targetMode: draft.targetMode,
            board: selectedBoard,
            onRemove: inSet
                ? {
                    if let index = draft.steps.firstIndex(where: { $0.id == step.id }) {
                        draft.removeSteps(at: IndexSet(integer: index))
                    }
                } : nil
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

    private func replaceDraftTargetMode(boardID: String?) {
        guard !isExistingRoutine else {
            return
        }

        let targetMode: CustomRoutineTargetMode = boardID.map { .boardSpecific(boardID: $0) } ?? .generic
        guard targetMode != draft.targetMode else {
            return
        }

        draft = draft.retargeted(to: targetMode)
    }

    private func save() {
        hasAttemptedSave = true
        let definition = draft.definition()
        let issues = Self.localValidationIssues(for: draft)
        guard issues.isEmpty else { return }

        do {
            try onSave(definition)
            dismiss()
        } catch {
            persistenceError = Self.saveErrorMessage(for: error)
        }
    }

    static func saveErrorMessage(for error: Error) -> String {
        guard let storeError = error as? CustomRoutineStoreError,
            case .validationFailed(let issues) = storeError
        else { return error.localizedDescription }
        for issue in issues {
            switch issue {
            case .unresolvableTargets(let index), .unresolvableSegmentTargets(let index, _):
                return
                    "Step \(index + 1)’s holds don’t match an available board. Try another hold type or depth."
            case .noCompatibleBoard:
                return "These hold choices don’t match an available board. Try another hold type or depth."
            default: continue
            }
        }
        return "Check the routine’s steps and try saving again."
    }

    /// Raw depth edits stay separate from the saved prescription until they are valid.
    static func localValidationIssues(for draft: CustomRoutineDraft) -> [String] {
        var issues = localValidationIssues(for: draft.definition())
        if case .generic = draft.targetMode {
            for (index, step) in draft.steps.enumerated() where !step.isRest && step.hasInvalidDepthInput {
                issues.append("Step \(index + 1) needs a positive depth or an ordered range in mm.")
            }
        }
        return issues
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
        for (index, step) in definition.steps.enumerated()
        where !WorkoutStepSemantics.hasValidHandUseAndSide(step.handUse, step.side) {
            issues.append("Step \(index + 1) needs a side compatible with its hand use.")
        }
        for (index, step) in definition.steps.enumerated()
        where !WorkoutStepSemantics.hasValidActionAndRepetitions(step.action, step.repetitions) {
            issues.append("Step \(index + 1) needs positive repetitions for a loaded lift.")
        }
        for (index, step) in definition.steps.enumerated()
        where !WorkoutStepSemantics.hasValidExternalLoad(step.externalLoadKGF) {
            issues.append("Step \(index + 1) needs a finite external load.")
        }
        for issue in CustomRoutineValidator.setIssues(for: definition) {
            switch issue {
            case .invalidSetRepeatCount(let index):
                issues.append("Set \(index + 1) needs a repeat count from 1 to 100.")
            case .overlappingSetSteps(let index):
                issues.append("Set \(index + 1) overlaps another set.")
            case .invalidSetSteps(let index), .duplicateSetID(let index):
                issues.append("Set \(index + 1) needs consecutive steps.")
            default: break
            }
        }
        for issue in CustomRoutineValidator.circuitIssues(for: definition) {
            switch issue {
            case .invalidCircuitRepeatCount(let index):
                issues.append("Circuit \(index + 1) needs a repeat count from 1 to 100.")
            case .invalidCircuitRest(let index):
                issues.append("Circuit \(index + 1) needs zero or a positive rest duration.")
            case .overlappingCircuitSets(let index):
                issues.append("Circuit \(index + 1) overlaps another circuit.")
            case .invalidCircuitSets(let index), .duplicateCircuitID(let index):
                issues.append("Circuit \(index + 1) needs consecutive sets.")
            default: break
            }
        }
        return issues
    }
}

private struct CustomRoutineStepEditor: View {
    @Binding var step: CustomRoutineStepDraft
    let focusedField: FocusState<String?>.Binding
    let targetMode: CustomRoutineTargetMode
    let board: BoardRevision
    let onRemove: (() -> Void)?

    @State private var isExpanded: Bool
    @State private var activeHoldID: String?
    @AppStorage("HangTen.customRoutine.displayUnits") private var loadUnits = CustomRoutineLoadUnit.metric

    init(
        step: Binding<CustomRoutineStepDraft>,
        focusedField: FocusState<String?>.Binding,
        targetMode: CustomRoutineTargetMode,
        board: BoardRevision,
        onRemove: (() -> Void)?
    ) {
        _step = step
        self.focusedField = focusedField
        self.targetMode = targetMode
        self.board = board
        self.onRemove = onRemove
        _isExpanded = State(initialValue: step.wrappedValue.duration == 0)
    }

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
        DisclosureGroup(isExpanded: $isExpanded) {
            VStack(alignment: .leading, spacing: 20) {
                Picker("Exercise", selection: $step.exercise) {
                    ForEach(CustomRoutineExercise.allCases, id: \.self) { exercise in
                        Text(exercise.label).tag(exercise)
                    }
                }
                .modifier(CustomRoutineInputStyle())
                .accessibilityIdentifier("customRoutine.stepExercise")

                CustomRoutineField("Time") {
                    HStack(spacing: 6) {
                        TextField("", value: durationBinding, format: .number)
                            .keyboardType(.decimalPad)
                            .accessibilityLabel("Time in seconds")
                            .accessibilityIdentifier("customRoutine.stepDuration")
                            .focused(focusedField, equals: "\(step.id).stepDuration")
                        Text("sec").foregroundStyle(.secondary)
                    }
                }
                if step.timing != .fixed {
                    Text("Active time: \(step.timing.label)")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }

                if !step.isRest {
                    editorGroup("Hands & holds") {
                        Picker("Hands", selection: $step.handChoice) {
                            ForEach(CustomRoutineHandChoice.allCases, id: \.self) { choice in
                                if choice != .either || (step.phase != .pull && step.action != .isometricPull) {
                                    Text(choice.label).tag(choice)
                                }
                            }
                        }
                        .modifier(CustomRoutineInputStyle())
                        .accessibilityIdentifier("customRoutine.stepHands")
                        Picker("Fingers", selection: $step.fingerCount) {
                            Text("Not specified").tag(Int?.none)
                            ForEach(1...4, id: \.self) { count in
                                Text(count == 1 ? "1 finger" : "\(count) fingers").tag(Optional(count))
                            }
                        }
                        .modifier(CustomRoutineInputStyle())
                        .accessibilityIdentifier("customRoutine.stepFingers")
                        Picker("Grip", selection: $step.gripType) {
                            Text("Not specified").tag(GripType?.none)
                            ForEach(gripChoices) { grip in
                                Text(grip.label).tag(Optional(grip))
                            }
                        }
                        .modifier(CustomRoutineInputStyle())
                        .accessibilityIdentifier("customRoutine.stepGrip")
                        targetEditor
                    }
                    if step.action == .loadedLift {
                        editorGroup("Load") {
                            CustomRoutineField("Repetitions") {
                                TextField("", value: $step.repetitions, format: .number)
                                    .keyboardType(.numberPad)
                                    .accessibilityIdentifier("customRoutine.stepRepetitions")
                                    .focused(focusedField, equals: "\(step.id).stepRepetitions")
                            }
                            CustomRoutineField("Added weight") {
                                HStack(spacing: 6) {
                                    TextField(
                                        "", value: externalLoadBinding,
                                        format: .number.precision(.fractionLength(0...3))
                                    )
                                    .keyboardType(.numbersAndPunctuation)
                                    .accessibilityLabel("Added weight in \(loadUnits.loadUnit.label)")
                                    .accessibilityIdentifier("customRoutine.stepExternalLoad")
                                    .focused(focusedField, equals: "\(step.id).stepExternalLoad")
                                    Picker("Weight unit", selection: $loadUnits) {
                                        ForEach(CustomRoutineLoadUnit.allCases) { units in
                                            Text(units.loadUnit.label).tag(units)
                                        }
                                    }
                                    .labelsHidden()
                                    .fixedSize()
                                    .accessibilityLabel("Weight unit")
                                    .accessibilityIdentifier("customRoutine.stepLoadUnit")
                                    .onChange(of: loadUnits) { _, _ in focusedField.wrappedValue = nil }
                                }
                            }
                            Text("Use a negative load for assistance.")
                                .font(.caption)
                                .foregroundStyle(.secondary)
                        }
                    }
                }

                CustomRoutineField("Name") {
                    TextField(nameExample, text: $step.title)
                        .accessibilityIdentifier("customRoutine.stepTitle")
                        .focused(focusedField, equals: "\(step.id).stepTitle")
                }
                CustomRoutineField("Instructions") {
                    TextField(instructionExample, text: $step.instruction, axis: .vertical)
                        .accessibilityIdentifier("customRoutine.stepInstruction")
                        .focused(focusedField, equals: "\(step.id).stepInstruction")
                }

                if let onRemove {
                    Button(role: .destructive, action: onRemove) {
                        Text("Remove step")
                            .frame(maxWidth: .infinity, minHeight: 44, alignment: .leading)
                            .contentShape(Rectangle())
                    }
                    .buttonStyle(.borderless)
                    .accessibilityIdentifier("customRoutine.removeSetStep")
                }
            }
            // Automatic pickers in a List can capture the entire grouped row.
            .pickerStyle(.menu)
            .buttonStyle(.borderless)
            .padding(.vertical, 12)
        } label: {
            VStack(alignment: .leading, spacing: 4) {
                Text(step.displayTitle)
                if !isExpanded {
                    Text(stepSummary)
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
            }
            .accessibilityElement(children: .combine)
            .accessibilityIdentifier("customRoutine.step.\(step.id)")
        }
    }

    private var gripChoices: [GripType] {
        var choices: [GripType] = [.openHand, .halfCrimp, .fullCrimp]
        if let saved = step.gripType, !choices.contains(saved) { choices.append(saved) }
        return choices
    }

    private var stepSummary: String {
        var parts = [
            step.exercise.label,
            step.duration > 0 ? "\(step.duration.formatted()) sec" : "Set duration",
        ]
        if !step.isRest {
            parts.append(step.handChoice.label)
            if let kind = step.targets.first?.kind { parts.append(kind.label) }
            if let count = step.fingerCount { parts.append(count == 1 ? "1 finger" : "\(count) fingers") }
            if let grip = step.gripType { parts.append(grip.label) }
        }
        return parts.joined(separator: " · ")
    }

    private var nameExample: String {
        switch step.exercise {
        case .hang: "e.g. Jug hang"
        case .rest: "e.g. Rest"
        case .isometricPull, .loadedLift: ""
        }
    }

    private var instructionExample: String {
        switch step.exercise {
        case .hang: "e.g. Hang from the jugs for 15 seconds."
        case .rest: "e.g. Rest before the next hang."
        case .isometricPull, .loadedLift: ""
        }
    }

    private var durationBinding: Binding<Double?> {
        Binding(
            get: { step.duration == 0 ? nil : step.duration },
            set: { step.setDuration($0) }
        )
    }

    private var externalLoadBinding: Binding<Double?> {
        Binding(
            get: { step.externalLoadKGF.map { loadUnits.loadValue(fromKilogramsForce: $0) } },
            set: { step.externalLoadKGF = $0.map { loadUnits.kilogramsForce(fromDisplayedLoad: $0) } }
        )
    }

    private func editorGroup<Content: View>(
        _ title: String,
        @ViewBuilder content: () -> Content
    ) -> some View {
        VStack(alignment: .leading, spacing: 12) {
            Text(title)
                .font(.caption.weight(.semibold))
                .foregroundStyle(Color.hangGreenDark)
            content()
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
                Picker("Hold type", selection: genericKindBinding) {
                    Text("Choose hold type").tag(HoldKind?.none)
                    ForEach(HoldKind.allCases) { kind in
                        Text(kind.label).tag(Optional(kind))
                    }
                }
                .modifier(CustomRoutineInputStyle())
                .accessibilityIdentifier("customRoutine.stepTarget")

                if genericKind != nil {
                    CustomRoutineField("Depth") {
                        HStack(spacing: 6) {
                            TextField("", text: $step.depthText)
                                .keyboardType(.numbersAndPunctuation)
                                .accessibilityLabel("Depth in millimeters")
                                .accessibilityIdentifier("customRoutine.stepDepthValue")
                                .focused(focusedField, equals: "\(step.id).stepDepthValue")
                            Text("mm").foregroundStyle(.secondary)
                        }
                    }
                    if case .category(let size)? = step.targets.first?.depth {
                        HStack {
                            Text("Saved depth: \(size.label)")
                            Spacer()
                            Button("Clear") { step.depthText = "" }
                                .frame(minHeight: 44)
                                .accessibilityLabel("Clear saved depth")
                        }
                        .font(.caption)
                        .foregroundStyle(.secondary)
                    } else {
                        Text("Optional. Separate a range with a dash.")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }
                }
            }
        }
    }

    private var genericKind: HoldKind? {
        step.targets.first?.kind
    }

    private var genericKindBinding: Binding<HoldKind?> {
        Binding(
            get: { genericKind },
            set: { kind in
                guard kind != genericKind else { return }
                step.enteredDepthText = nil
                guard let kind else {
                    step.targets = []
                    return
                }
                let current = step.targets.first
                step.targets = [
                    ContactRequirement(
                        kind: kind,
                        depth: current?.depth,
                        fingerCapacity: current?.fingerCapacity,
                        handCapacity: current?.handCapacity,
                        selection: current?.selection ?? .single
                    )
                ]
            }
        )
    }

    private func toggleHold(_ hold: PhysicalContact) {
        activeHoldID = hold.id
        CustomRoutineBoardPreview.toggle(hold, in: &step, on: board)
    }
}

/// Gives text inputs a persistent label and a visible editing surface.
private struct CustomRoutineField<Content: View>: View {
    let title: String
    @ViewBuilder let content: Content

    init(_ title: String, @ViewBuilder content: () -> Content) {
        self.title = title
        self.content = content()
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(title).font(.subheadline.weight(.semibold))
            content.modifier(CustomRoutineInputStyle())
        }
    }
}

private struct CustomRoutineInputStyle: ViewModifier {
    func body(content: Content) -> some View {
        content
            .padding(.horizontal, 12)
            .padding(.vertical, 10)
            .frame(minHeight: 44)
            .background(Color(.systemGray6), in: RoundedRectangle(cornerRadius: 8))
            .overlay {
                RoundedRectangle(cornerRadius: 8)
                    .strokeBorder(.secondary.opacity(0.18), lineWidth: 1)
            }
    }
}
