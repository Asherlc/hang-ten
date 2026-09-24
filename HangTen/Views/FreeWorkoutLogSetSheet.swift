import SwiftUI

/// Manual log sheet for a hang (duration + weight) or pull-up (weight × reps).
struct FreeWorkoutLogSetSheet: View {
    let exerciseType: FreeExerciseType
    let holdName: String
    let initialWeightKGF: Double?
    let initialDuration: TimeInterval?
    let initialReps: Int?
    let onSave: (_ weightKGF: Double?, _ duration: TimeInterval?, _ reps: Int?) -> Void
    let onCancel: () -> Void

    @State private var weightText: String
    @State private var durationText: String
    @State private var repsText: String

    init(
        exerciseType: FreeExerciseType,
        holdName: String,
        initialWeightKGF: Double?,
        initialDuration: TimeInterval?,
        initialReps: Int?,
        onSave: @escaping (_ weightKGF: Double?, _ duration: TimeInterval?, _ reps: Int?) -> Void,
        onCancel: @escaping () -> Void
    ) {
        self.exerciseType = exerciseType
        self.holdName = holdName
        self.initialWeightKGF = initialWeightKGF
        self.initialDuration = initialDuration
        self.initialReps = initialReps
        self.onSave = onSave
        self.onCancel = onCancel
        _weightText = State(initialValue: FreeWorkoutDecimalText.format(initialWeightKGF))
        _durationText = State(
            initialValue: FreeWorkoutDecimalText.format(
                initialDuration ?? FreeWorkoutGuidedHangCountdown.defaultDuration
            )
        )
        _repsText = State(initialValue: FreeWorkoutDecimalText.format(initialReps.map(Double.init)))
    }

    var body: some View {
        NavigationStack {
            Form {
                Section {
                    LabeledContent("Hold", value: holdName)
                    LabeledContent("Type", value: exerciseType.label)
                }

                Section("Set") {
                    TextField("Weight (kg)", text: $weightText)
                        .keyboardType(.decimalPad)
                        .accessibilityIdentifier("freeWorkout.logSet.weight")

                    if exerciseType == .hang {
                        TextField("Duration (sec)", text: $durationText)
                            .keyboardType(.numberPad)
                            .accessibilityIdentifier("freeWorkout.logSet.duration")
                    } else {
                        TextField("Reps", text: $repsText)
                            .keyboardType(.numberPad)
                            .accessibilityIdentifier("freeWorkout.logSet.reps")
                    }
                }
            }
            .navigationTitle("Log set")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel", action: onCancel)
                        .accessibilityIdentifier("freeWorkout.logSet.cancel")
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Save") {
                        save()
                    }
                    .fontWeight(.semibold)
                    .accessibilityIdentifier("freeWorkout.logSet.save")
                }
            }
        }
        .accessibilityElement(children: .contain)
        .accessibilityIdentifier("freeWorkout.logSet")
    }

    private func save() {
        let weight = FreeWorkoutDecimalText.parse(weightText)
        switch exerciseType {
        case .hang:
            let durationValue = FreeWorkoutDecimalText.parse(durationText)
            let duration = FreeWorkoutGuidedHangCountdown.resolvedDuration(durationValue)
            onSave(weight, duration, nil)
        case .pullUp:
            let repsValue = Int(repsText.trimmingCharacters(in: .whitespacesAndNewlines))
            onSave(weight, nil, repsValue)
        }
    }
}
