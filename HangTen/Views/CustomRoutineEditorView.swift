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

            LabeledContent("Name") {
                TextField("e.g. Evening session", text: $draft.title)
                    .multilineTextAlignment(.leading)
                    .focused($focusedField, equals: "routine.name")
                    .accessibilityIdentifier("customRoutine.name")
            }
            DisclosureGroup("Routine details") {
                VStack(alignment: .leading, spacing: 8) {
                    Text("Description").font(.subheadline.weight(.semibold))
                    TextField("e.g. My routine for weekday evenings", text: $draft.subtitle, axis: .vertical)
                        .focused($focusedField, equals: "routine.description")
                        .accessibilityIdentifier("customRoutine.description")
                }
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
                LabeledContent("Tags") {
                    TextField("e.g. home, evenings", text: $draft.tagsText)
                        .multilineTextAlignment(.trailing)
                        .focused($focusedField, equals: "routine.tags")
                        .accessibilityIdentifier("customRoutine.tags")
                }
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
        case let .step(step):
            stepEditor(step)
        case let .set(set, steps):
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
            guard case let .set(candidate, _) = item else { return nil }
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
            onRemove: inSet ? {
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
            persistenceError = Self.saveErrorMessage(for: error)
        }
    }

    static func saveErrorMessage(for error: Error) -> String {
        guard let storeError = error as? CustomRoutineStoreError,
              case let .validationFailed(issues) = storeError else { return error.localizedDescription }
        for issue in issues {
            switch issue {
            case let .unresolvableTargets(index), let .unresolvableSegmentTargets(index, _):
                return "Step \(index + 1)’s holds don’t match an available board. Try another hold type, shape, or depth."
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
    let focusedField: FocusState<String?>.Binding
    let targetMode: CustomRoutineTargetMode
    let board: BoardRevision
    let onRemove: (() -> Void)?

    @State private var isExpanded: Bool
    @State private var areHoldDetailsExpanded = false
    @State private var activeHoldID: String?
    @State private var genericDepthSelection: GenericDepthSelection = .none
    @State private var exactDepthMinimum = ""
    @State private var exactDepthMaximum = ""

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
                .frame(minHeight: 44)
                .accessibilityIdentifier("customRoutine.stepExercise")

                LabeledContent("Duration") {
                    HStack(spacing: 6) {
                        TextField("e.g. 15", value: durationBinding, format: .number)
                            .keyboardType(.decimalPad)
                            .multilineTextAlignment(.trailing)
                            .accessibilityLabel("Duration in seconds")
                            .frame(minHeight: 44)
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
                        .frame(minHeight: 44)
                        .accessibilityIdentifier("customRoutine.stepHands")
                        targetEditor
                    }
                    if step.action == .loadedLift {
                        editorGroup("Load") {
                            LabeledContent("Repetitions") {
                                TextField("e.g. 5", value: $step.repetitions, format: .number)
                                    .keyboardType(.numberPad)
                                    .multilineTextAlignment(.trailing)
                                    .frame(minHeight: 44)
                                    .accessibilityIdentifier("customRoutine.stepRepetitions")
                                    .focused(focusedField, equals: "\(step.id).stepRepetitions")
                            }
                            LabeledContent("External load (kg)") {
                                TextField("e.g. -10", value: $step.externalLoadKGF, format: .number)
                                    .keyboardType(.numbersAndPunctuation)
                                    .multilineTextAlignment(.trailing)
                                    .frame(minHeight: 44)
                                    .accessibilityIdentifier("customRoutine.stepExternalLoad")
                                    .focused(focusedField, equals: "\(step.id).stepExternalLoad")
                            }
                            Text("Use a negative load for assistance.")
                                .font(.caption)
                                .foregroundStyle(.secondary)
                        }
                    }
                }

                LabeledContent("Name") {
                    TextField("e.g. First hang", text: $step.title)
                        .multilineTextAlignment(.leading)
                        .frame(minHeight: 44)
                        .accessibilityIdentifier("customRoutine.stepTitle")
                        .focused(focusedField, equals: "\(step.id).stepTitle")
                }
                VStack(alignment: .leading, spacing: 8) {
                    Text("Instructions").font(.subheadline.weight(.semibold))
                    TextField("e.g. Use my usual board setup", text: $step.instruction, axis: .vertical)
                        .frame(minHeight: 44)
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
            .disclosureGroupStyle(InlineEditorDisclosureStyle())
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
        var parts = [step.exercise.label,
                     step.duration > 0 ? "\(step.duration.formatted()) sec" : "Set duration"]
        if !step.isRest {
            parts.append(step.handChoice.label)
            if let kind = step.targets.first?.kind { parts.append(kind.label) }
        }
        return parts.joined(separator: " · ")
    }

    private var durationBinding: Binding<Double?> {
        Binding(
            get: { step.duration == 0 ? nil : step.duration },
            set: { step.setDuration($0) }
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
                .frame(minHeight: 44)
                .accessibilityIdentifier("customRoutine.stepTarget")

                if genericKind != nil {
                    DisclosureGroup(isExpanded: $areHoldDetailsExpanded) {
                        if let kind = genericKind, !Self.supportedShapes(for: kind).isEmpty {
                            Picker("Hold shape", selection: genericShapeBinding) {
                                Text("Any shape").tag(HoldShape?.none)
                                ForEach(Self.supportedShapes(for: kind)) { shape in
                                    Text(shape.label).tag(Optional(shape))
                                }
                            }
                            .frame(minHeight: 44)
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
                            .frame(minHeight: 44)
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
                                LabeledContent("Minimum depth (mm)") {
                                    TextField("e.g. 18", text: $exactDepthMinimum)
                                        .keyboardType(.decimalPad)
                                        .multilineTextAlignment(.trailing)
                                        .frame(minHeight: 44)
                                        .accessibilityIdentifier("customRoutine.stepDepthMinimum")
                                        .focused(focusedField, equals: "\(step.id).stepDepthMinimum")
                                        .onChange(of: exactDepthMinimum) { _, _ in updateExactDepthFromFields() }
                                }
                                LabeledContent("Maximum depth (mm)") {
                                    TextField("e.g. 22", text: $exactDepthMaximum)
                                        .keyboardType(.decimalPad)
                                        .multilineTextAlignment(.trailing)
                                        .frame(minHeight: 44)
                                        .accessibilityIdentifier("customRoutine.stepDepthMaximum")
                                        .focused(focusedField, equals: "\(step.id).stepDepthMaximum")
                                        .onChange(of: exactDepthMaximum) { _, _ in updateExactDepthFromFields() }
                                }
                            }
                        }
                    } label: {
                        Text(genericRefinementSummary.isEmpty ? "Hold details" : genericRefinementSummary)
                            .frame(minHeight: 44)
                            .accessibilityIdentifier("customRoutine.holdDetails")
                    }
                    .frame(minHeight: 44)
                }
            }
            .onAppear(perform: configureGenericDepthSelection)
        }
    }

    private var genericKind: HoldKind? {
        step.targets.first?.kind
    }

    private var genericRefinementSummary: String {
        guard let target = step.targets.first else { return "" }
        var parts = target.shape.map { ["\($0.label) shape"] } ?? []
        switch target.depth {
        case let .category(size): parts.append("\(size.label) depth")
        case let .range(range):
            parts.append("\(range.minimum.formatted())–\(range.maximum.formatted()) mm")
        case nil: break
        }
        return parts.joined(separator: " · ")
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

/// Keeps each optional group’s toggle inside its own touch target in a shared List row.
private struct InlineEditorDisclosureStyle: DisclosureGroupStyle {
    func makeBody(configuration: Configuration) -> some View {
        VStack(alignment: .leading, spacing: 12) {
            Button {
                withAnimation { configuration.isExpanded.toggle() }
            } label: {
                HStack {
                    configuration.label
                    Spacer()
                    Image(systemName: configuration.isExpanded ? "chevron.down" : "chevron.right")
                        .font(.subheadline.weight(.semibold))
                }
                .frame(minHeight: 44)
                .contentShape(Rectangle())
            }
            .buttonStyle(.plain)
            if configuration.isExpanded {
                configuration.content
            }
        }
    }
}

private enum GenericDepthSelection: Hashable {
    case none
    case category(HoldSize)
    case exactRange
}
