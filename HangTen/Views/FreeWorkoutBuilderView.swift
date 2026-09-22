import SwiftUI

struct FreeWorkoutBuilderView: View {
    @EnvironmentObject private var store: AppStore
    @Environment(\.dismiss) private var dismiss
    @State private var draft: FreeWorkoutDraft = FreeWorkoutDraftStore.load() ?? .starter
    @State private var sessionPlan: TrainingPlan?
    @State private var sessionDraft: FreeWorkoutDraft?
    @State private var saveAsPlan = false

    var body: some View {
        NavigationStack {
            List {
                Section("Workout") {
                    TextField("Name", text: $draft.title)
                        .accessibilityIdentifier("freeWorkout.name")
                        .onChange(of: draft.title) { _, _ in persist() }
                    ForEach($draft.exercises) { $exercise in
                        FreeWorkoutExerciseEditor(
                            exercise: $exercise,
                            board: store.selectedBoard,
                            onDelete: { delete(exercise) }
                        )
                    }
                    .onMove { offsets, destination in
                        draft.exercises.move(fromOffsets: offsets, toOffset: destination)
                        persist()
                    }
                    .onChange(of: draft.exercises) { _, _ in persist() }
                }
                Section("Add") {
                    Button {
                        draft.exercises.append(.hang())
                        persist()
                    } label: {
                        Label("Add hang", systemImage: "plus")
                    }
                    .accessibilityIdentifier("freeWorkout.addHang")
                    Button {
                        draft.exercises.append(.pull())
                        persist()
                    } label: {
                        Label("Add pull-ups", systemImage: "plus")
                    }
                    .accessibilityIdentifier("freeWorkout.addPull")
                    Button {
                        draft.exercises.append(.rest())
                        persist()
                    } label: {
                        Label("Add rest", systemImage: "plus")
                    }
                    .accessibilityIdentifier("freeWorkout.addRest")
                }
                Section("Finish") {
                    Text("Saved routines use generic hold types. They do not retain exact board contacts.")
                        .font(.footnote)
                        .foregroundStyle(.secondary)
                    Toggle("Save as reusable routine", isOn: $saveAsPlan)
                        .accessibilityIdentifier("freeWorkout.saveAsPlan")
                    Button("Start workout", action: start)
                        .buttonStyle(.borderedProminent)
                        .tint(.hangGreenDark)
                        .disabled(draft.exercises.isEmpty)
                        .accessibilityIdentifier("freeWorkout.start")
                }
            }
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") { dismiss() }
                }
            }
            .navigationTitle("Free workout")
            .navigationDestination(item: $sessionPlan) { plan in
                if let sessionDraft {
                    FreeWorkoutSessionView(
                        plan: plan,
                        draft: sessionDraft,
                        saveAsPlan: saveAsPlan,
                        onDismiss: { dismiss() }
                    )
                }
            }
        }
        .accessibilityIdentifier("freeWorkout.builder")
    }

    private func delete(_ exercise: FreeWorkoutExerciseDraft) {
        draft.exercises.removeAll { $0.id == exercise.id }
        persist()
    }

    private func persist() {
        FreeWorkoutDraftStore.save(draft)
    }

    private func start() {
        persist()
        sessionDraft = draft
        sessionPlan = draft.trainingPlan()
    }
}

private struct FreeWorkoutExerciseEditor: View {
    @Binding var exercise: FreeWorkoutExerciseDraft
    let board: BoardRevision
    let onDelete: () -> Void

    var body: some View {
        DisclosureGroup(exercise.title.isEmpty ? exercise.kind.label : exercise.title) {
            if exercise.kind != .rest {
                TextField("Title", text: $exercise.title)
                    .accessibilityIdentifier("freeWorkout.exerciseTitle.\(exercise.id)")
                holdPicker
                gripPicker
            }
            if exercise.kind == .hang {
                durationField(title: "Hang (seconds)", value: $exercise.workDuration)
                durationField(title: "Rest after (seconds)", value: $exercise.restDuration)
                loadField
            } else if exercise.kind == .pull {
                Stepper(
                    "Reps: \(exercise.repetitions ?? 5)",
                    value: repBinding,
                    in: 1...100
                )
                .accessibilityIdentifier("freeWorkout.exerciseReps.\(exercise.id)")
                durationField(title: "Time cap (seconds)", value: $exercise.workDuration)
                durationField(title: "Rest after (seconds)", value: $exercise.restDuration)
                loadField
            } else {
                durationField(title: "Rest (seconds)", value: $exercise.restDuration)
            }
            Button("Delete", role: .destructive, action: onDelete)
                .accessibilityIdentifier("freeWorkout.deleteExercise.\(exercise.id)")
        }
    }

    private var repBinding: Binding<Int> {
        Binding(
            get: { exercise.repetitions ?? 5 },
            set: { exercise.repetitions = $0 }
        )
    }

    @ViewBuilder
    private var holdPicker: some View {
        Picker("Hold", selection: holdSelection) {
            Text("Any hold").tag(FreeWorkoutHoldSelection.any)
            ForEach(HoldKind.allCases) { kind in
                Text(kind.label).tag(FreeWorkoutHoldSelection.generic(kind))
            }
            ForEach(board.contacts) { contact in
                Text(contact.name).tag(FreeWorkoutHoldSelection.exact(contact.id))
            }
        }
        .accessibilityIdentifier("freeWorkout.exerciseHold.\(exercise.id)")
    }

    private var holdSelection: Binding<FreeWorkoutHoldSelection> {
        Binding(
            get: {
                if let contactID = exercise.contactID {
                    return .exact(contactID)
                }
                if let holdKind = exercise.holdKind {
                    return .generic(holdKind)
                }
                return .any
            },
            set: { selection in
                switch selection {
                case .any:
                    exercise.contactID = nil
                    exercise.contactKind = nil
                    exercise.contactShape = nil
                    exercise.contactDepth = nil
                    exercise.contactFingerCapacity = nil
                    exercise.holdKind = nil
                case .generic(let kind):
                    exercise.contactID = nil
                    exercise.contactKind = nil
                    exercise.contactShape = nil
                    exercise.contactDepth = nil
                    exercise.contactFingerCapacity = nil
                    exercise.holdKind = kind
                case .exact(let contactID):
                    guard let contact = board.contacts.first(where: { $0.id == contactID }) else { return }
                    exercise.contactID = contact.id
                    exercise.contactKind = contact.kind
                    exercise.contactShape = contact.shape
                    exercise.contactDepth = contact.depth
                    exercise.contactFingerCapacity = contact.fingerCapacity
                    exercise.holdKind = nil
                }
            }
        )
    }

    @ViewBuilder
    private var gripPicker: some View {
        Picker("Grip", selection: $exercise.gripType) {
            Text("No cue").tag(GripType?.none)
            ForEach(GripType.allCases) { grip in
                Text(grip.label).tag(Optional(grip))
            }
        }
        .accessibilityIdentifier("freeWorkout.exerciseGrip.\(exercise.id)")
    }

    private func durationField(title: String, value: Binding<TimeInterval>) -> some View {
        TextField(title, value: value, format: .number)
            .keyboardType(.decimalPad)
    }

    @ViewBuilder
    private var loadField: some View {
        TextField(
            "Added weight (kg; 0 or empty for bodyweight)",
            value: $exercise.externalLoadKGF,
            format: .number
        )
        .keyboardType(.numbersAndPunctuation)
        .accessibilityIdentifier("freeWorkout.exerciseLoad.\(exercise.id)")
    }
}

private enum FreeWorkoutHoldSelection: Hashable {
    case any
    case generic(HoldKind)
    case exact(String)
}
