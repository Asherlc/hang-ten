import SwiftUI

/// Add Hang or Pull-up to the live free-workout log, with hold picker.
struct FreeWorkoutAddExerciseSheet: View {
    let board: BoardRevision
    let onAdd: (FreeExerciseType, FreeWorkoutHoldSelection) -> Void
    let onCancel: () -> Void

    @State private var exerciseType: FreeExerciseType = .hang
    @State private var holdSelection: FreeWorkoutHoldSelection = .any

    var body: some View {
        NavigationStack {
            Form {
                Section("Exercise") {
                    Picker("Type", selection: $exerciseType) {
                        ForEach(FreeExerciseType.allCases, id: \.self) { type in
                            Text(type.label)
                                .tag(type)
                                .accessibilityIdentifier(
                                    type == .hang
                                        ? "freeWorkout.addExercise.hang"
                                        : "freeWorkout.addExercise.pullUp"
                                )
                        }
                    }
                    .pickerStyle(.segmented)
                    .accessibilityIdentifier("freeWorkout.addExercise.type")
                }

                Section("Hold") {
                    Picker("Hold", selection: $holdSelection) {
                        Text("Any hold").tag(FreeWorkoutHoldSelection.any)
                        ForEach(HoldKind.allCases) { kind in
                            Text(kind.label).tag(FreeWorkoutHoldSelection.generic(kind))
                        }
                        ForEach(board.contacts) { contact in
                            Text(contact.name).tag(FreeWorkoutHoldSelection.exact(.init(contact)))
                        }
                    }
                    .accessibilityIdentifier("freeWorkout.addExercise.hold")
                }
            }
            .navigationTitle("Add exercise")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel", action: onCancel)
                        .accessibilityIdentifier("freeWorkout.addExercise.cancel")
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Add") {
                        onAdd(exerciseType, holdSelection)
                    }
                    .fontWeight(.semibold)
                    .accessibilityIdentifier("freeWorkout.addExercise.confirm")
                }
            }
        }
        .accessibilityElement(children: .contain)
        .accessibilityIdentifier("freeWorkout.addExercise")
    }
}
