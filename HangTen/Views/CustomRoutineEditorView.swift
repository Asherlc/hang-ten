import SwiftUI

struct CustomRoutineEditorView: View {
    @Environment(\.dismiss) private var dismiss

    private let onSave: (CustomRoutineDefinition) throws -> Void
    private let metadataOptions = CustomRoutineMetadataOptions()
    @State private var draft: CustomRoutineDraft
    @State private var selectedBoardID: String?
    @AppStorage("HangTen.customRoutine.displayUnits") private var displayUnits = CustomRoutineDisplayUnit.metric
    @State private var persistenceError: String?
    @State private var hasAttemptedSave = false
    @State private var validationScrollRequest = 0
    @FocusState private var focusedField: String?
    @State private var editMode = EditMode.inactive
    @State private var collapsedSetIDs = Set<String>()

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
        hasAttemptedSave ? Self.localValidationIssues(for: draft.definition()) : []
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
            Picker("Difficulty", selection: $draft.difficulty) {
                Text("None").tag(String?.none)
                ForEach(metadataOptions.difficulties, id: \.self) { difficulty in
                    Text(difficulty).tag(Optional(difficulty))
                }
            }
            .pickerStyle(.menu)
            .modifier(CustomRoutineInputStyle())
            .accessibilityIdentifier("customRoutine.difficulty")
            Picker("Category", selection: $draft.category) {
                Text("None").tag(String?.none)
                ForEach(metadataOptions.categories, id: \.self) { category in
                    Text(category).tag(Optional(category))
                }
            }
            .pickerStyle(.menu)
            .modifier(CustomRoutineInputStyle())
            .accessibilityIdentifier("customRoutine.category")
            CustomRoutineField("Tags") {
                TextField("e.g. manufacturer", text: $draft.tagsText)
                    .focused($focusedField, equals: "routine.tags")
                    .accessibilityIdentifier("customRoutine.tags")
            }
            VStack(alignment: .leading, spacing: 8) {
                Text("Units").font(.subheadline.weight(.semibold))
                Picker("Units", selection: $displayUnits) {
                    ForEach(CustomRoutineDisplayUnit.allCases) { units in
                        Text(units.label).tag(units)
                    }
                }
                .pickerStyle(.segmented)
                .accessibilityIdentifier("customRoutine.units")
                .onChange(of: displayUnits) { _, _ in focusedField = nil }
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

        } header: {
            HStack {
                Text("Sets")
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
            Text("Add exercises and rest steps to each set. The repeat count includes the first run.")
        }
    }

    @ViewBuilder
    /// Renders one editable row, with a shared count and child forms when the row represents a set.
    private func editorItem(_ item: CustomRoutineEditorItem) -> some View {
        switch item {
        case .step(let step):
            stepEditor(step)
        case .set(let set, let steps):
            let number = setNumber(for: set)
            DisclosureGroup(isExpanded: setExpansionBinding(for: set)) {
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
    }

    /// Numbers sets in visible order, independent of metadata order and explicitly ungrouped rows.
    private func setNumber(for set: CustomRoutineSet) -> Int {
        let ids: [String] = draft.editorItems.compactMap { item in
            guard case .set(let candidate, _) = item else { return nil }
            return candidate.id
        }
        return (ids.firstIndex(of: set.id) ?? 0) + 1
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
            displayUnits: displayUnits,
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
        let issues = Self.localValidationIssues(for: definition)
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
                    "Step \(index + 1)’s holds don’t match an available board. Try another hold type, shape, or depth."
            case .noCompatibleBoard:
                return "These hold choices don’t match an available board. Try another hold type, shape, or depth."
            default: continue
            }
        }
        return "Check the routine’s steps and try saving again."
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
        return issues
    }
}

private struct CustomRoutineStepEditor: View {
    @Binding var step: CustomRoutineStepDraft
    let focusedField: FocusState<String?>.Binding
    let targetMode: CustomRoutineTargetMode
    let board: BoardRevision
    let displayUnits: CustomRoutineDisplayUnit
    let onRemove: (() -> Void)?

    @State private var isExpanded: Bool
    @State private var activeHoldID: String?
    @State private var genericDepthSelection: GenericDepthSelection = .none
    @State private var exactDepthMinimumMM: Double?
    @State private var exactDepthMaximumMM: Double?

    init(
        step: Binding<CustomRoutineStepDraft>,
        focusedField: FocusState<String?>.Binding,
        targetMode: CustomRoutineTargetMode,
        board: BoardRevision,
        displayUnits: CustomRoutineDisplayUnit,
        onRemove: (() -> Void)?
    ) {
        _step = step
        self.focusedField = focusedField
        self.targetMode = targetMode
        self.board = board
        self.displayUnits = displayUnits
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

                CustomRoutineField("Duration") {
                    HStack(spacing: 6) {
                        TextField("", value: durationBinding, format: .number)
                            .keyboardType(.decimalPad)
                            .accessibilityLabel("Duration in seconds")
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
                            CustomRoutineField("External load") {
                                HStack(spacing: 6) {
                                    TextField(
                                        "", value: externalLoadBinding,
                                        format: .number.precision(.fractionLength(0...3))
                                    )
                                    .keyboardType(.numbersAndPunctuation)
                                    .accessibilityLabel("External load in \(displayUnits.loadUnit.label)")
                                    .accessibilityIdentifier("customRoutine.stepExternalLoad")
                                    .focused(focusedField, equals: "\(step.id).stepExternalLoad")
                                    Text(displayUnits.loadUnit.label).foregroundStyle(.secondary)
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

    private var stepSummary: String {
        var parts = [
            step.exercise.label,
            step.duration > 0 ? "\(step.duration.formatted()) sec" : "Set duration",
        ]
        if !step.isRest {
            parts.append(step.handChoice.label)
            if let kind = step.targets.first?.kind { parts.append(kind.label) }
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
            get: { step.externalLoadKGF.map { displayUnits.loadValue(fromKilogramsForce: $0) } },
            set: { step.externalLoadKGF = $0.map { displayUnits.kilogramsForce(fromDisplayedLoad: $0) } }
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
                Picker("Holds", selection: genericKindBinding) {
                    Text("Choose target").tag(HoldKind?.none)
                    ForEach(HoldKind.allCases) { kind in
                        Text(kind.label).tag(Optional(kind))
                    }
                }
                .modifier(CustomRoutineInputStyle())
                .accessibilityIdentifier("customRoutine.stepTarget")

                if genericKind != nil {
                    if let kind = genericKind, !Self.supportedShapes(for: kind).isEmpty {
                        Picker("Shape", selection: genericShapeBinding) {
                            Text("Any shape").tag(HoldShape?.none)
                            ForEach(Self.supportedShapes(for: kind)) { shape in
                                Text(shape == .incut ? "Angled inward" : shape.label).tag(Optional(shape))
                            }
                        }
                        .modifier(CustomRoutineInputStyle())
                        .accessibilityIdentifier("customRoutine.stepShape")
                    }
                    Picker("Depth", selection: $genericDepthSelection) {
                        Text("Any depth").tag(GenericDepthSelection.none)
                        Section("Size") {
                            ForEach(HoldSize.allCases) { size in
                                Text(size.label).tag(GenericDepthSelection.category(size))
                            }
                        }
                        Text("Range").tag(GenericDepthSelection.exactRange)
                    }
                    .modifier(CustomRoutineInputStyle())
                    .accessibilityIdentifier("customRoutine.stepDepth")
                    .onChange(of: genericDepthSelection) { _, selection in
                        switch selection {
                        case .none:
                            replaceGenericTarget(depth: nil)
                        case .category(let size):
                            replaceGenericTarget(depth: .category(size))
                        case .exactRange:
                            loadExactDepthFields()
                            updateExactDepthFromFields()
                        }
                    }
                    if genericDepthSelection == .exactRange {
                        depthField("Minimum", minimum: true)
                        depthField("Maximum", minimum: false)
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
            exactDepthMinimumMM = nil
            exactDepthMaximumMM = nil
            return
        }
        switch depth {
        case .category(let size):
            genericDepthSelection = .category(size)
        case .range(let range):
            genericDepthSelection = .exactRange
            exactDepthMinimumMM = range.minimum
            exactDepthMaximumMM = range.maximum
        }
    }

    private func loadExactDepthFields() {
        if case .range(let range)? = step.targets.first?.depth {
            exactDepthMinimumMM = range.minimum
            exactDepthMaximumMM = range.maximum
        }
    }

    private func depthField(_ title: String, minimum: Bool) -> some View {
        let identifier = minimum ? "stepDepthMinimum" : "stepDepthMaximum"
        return CustomRoutineField(title) {
            HStack(spacing: 6) {
                TextField("", value: depthBinding(minimum: minimum), format: .number.precision(.fractionLength(0...3)))
                    .keyboardType(.decimalPad)
                    .accessibilityLabel("\(title) depth in \(displayUnits.depthUnitLabel)")
                    .accessibilityIdentifier("customRoutine.\(identifier)")
                    .focused(focusedField, equals: "\(step.id).\(identifier)")
                Text(displayUnits.depthUnitLabel).foregroundStyle(.secondary)
            }
        }
    }

    /// Unit selection changes presentation; only an input edit writes canonical millimeters.
    private func depthBinding(minimum: Bool) -> Binding<Double?> {
        Binding(
            get: {
                (minimum ? exactDepthMinimumMM : exactDepthMaximumMM)
                    .map { displayUnits.depthValue(fromMillimeters: $0) }
            },
            set: { value in
                let millimeters = value.map { displayUnits.millimeters(fromDisplayedDepth: $0) }
                if minimum { exactDepthMinimumMM = millimeters } else { exactDepthMaximumMM = millimeters }
                updateExactDepthFromFields()
            }
        )
    }

    private func updateExactDepthFromFields() {
        guard let minimum = exactDepthMinimumMM,
            let maximum = exactDepthMaximumMM,
            minimum > 0,
            maximum >= minimum
        else {
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

private enum GenericDepthSelection: Hashable {
    case none
    case category(HoldSize)
    case exactRange
}
