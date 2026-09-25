import SwiftUI

/// Add Hang or Pull-up to the live free-workout log, with hold and hand pickers.
struct FreeWorkoutAddExerciseSheet: View {
    let board: BoardRevision
    let onAdd: (FreeExerciseType, FreeWorkoutHoldSelection, WorkoutSide) -> Void
    let onCancel: () -> Void

    @State private var exerciseType: FreeExerciseType = .hang
    @State private var holdSelection: FreeWorkoutHoldSelection = .generic(.jug)
    @State private var hand: WorkoutSide = .both

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

                Section("Hand") {
                    Picker("Hand", selection: $hand) {
                        Text("Left").tag(WorkoutSide.left)
                        Text("Right").tag(WorkoutSide.right)
                        Text("Both").tag(WorkoutSide.both)
                    }
                    .pickerStyle(.segmented)
                    .accessibilityIdentifier("freeWorkout.addExercise.hand")
                }

                Section("Hold") {
                    Picker("Hold", selection: $holdSelection) {
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
                        onAdd(exerciseType, holdSelection, hand)
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
