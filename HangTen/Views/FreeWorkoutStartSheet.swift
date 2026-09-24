import SwiftUI

/// Entry for free-workout log mode: resume/discard an active log, or start Empty / Last / Template.
struct FreeWorkoutStartSheet: View {
    @EnvironmentObject private var store: AppStore
    @Environment(\.dismiss) private var dismiss

    @State private var activeLog: FreeWorkoutLog?
    @State private var latest: FreeWorkoutLog?
    @State private var templates: [FreeWorkoutTemplate] = []
    @State private var path: [FreeWorkoutStartRoute] = []

    var body: some View {
        NavigationStack(path: $path) {
            Group {
                if activeLog != nil {
                    resumeContent
                } else {
                    startChoicesContent
                }
            }
            .background(Color.hangBackground)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") { dismiss() }
                }
            }
            .navigationTitle("Free workout")
            .navigationBarTitleDisplayMode(.inline)
            .navigationDestination(for: FreeWorkoutStartRoute.self) { route in
                switch route {
                case .session:
                    FreeWorkoutLogSessionView(
                        onFinished: { dismiss() },
                        onClose: {
                            path.removeAll()
                            activeLog = ActiveFreeWorkoutStore.load()
                        }
                    )
                }
            }
            .onAppear(perform: prepare)
        }
        .accessibilityIdentifier("freeWorkout.start")
    }

    private var resumeContent: some View {
        VStack(alignment: .leading, spacing: 20) {
            VStack(alignment: .leading, spacing: 8) {
                SectionLabel(title: "In progress")
                Text("You have a free workout in progress.")
                    .font(.system(size: 16, weight: .bold, design: .rounded))
                    .foregroundStyle(Color.hangInk)
                if let activeLog {
                    Text(resumeSubtitle(for: activeLog))
                        .font(.system(size: 13, weight: .medium, design: .rounded))
                        .foregroundStyle(Color.hangMuted)
                }
            }

            VStack(spacing: 12) {
                Button {
                    path = [.session]
                } label: {
                    Label("Resume", systemImage: "play.fill")
                        .frame(maxWidth: .infinity)
                }
                .buttonStyle(.borderedProminent)
                .tint(.hangGreenDark)
                .controlSize(.large)
                .accessibilityIdentifier("freeWorkout.resume")

                Button(role: .destructive) {
                    discardActive()
                } label: {
                    Label("Discard", systemImage: "trash")
                        .frame(maxWidth: .infinity)
                }
                .buttonStyle(.bordered)
                .controlSize(.large)
                .accessibilityIdentifier("freeWorkout.discard")
            }

            Spacer(minLength: 0)
        }
        .padding(20)
        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
    }

    private var startChoicesContent: some View {
        List {
            Section {
                Button {
                    startEmpty()
                } label: {
                    Label("Empty workout", systemImage: "plus.circle")
                }
                .accessibilityIdentifier("freeWorkout.empty")

                Button {
                    startFromLatest()
                } label: {
                    Label("Last workout", systemImage: "clock.arrow.circlepath")
                }
                .disabled(latest == nil)
                .accessibilityIdentifier("freeWorkout.last")
            } header: {
                Text("Start")
            } footer: {
                if latest == nil {
                    Text("Finish a free workout to unlock Last workout.")
                }
            }

            if !templates.isEmpty {
                Section("Templates") {
                    ForEach(templates) { template in
                        Button {
                            startFromTemplate(template)
                        } label: {
                            VStack(alignment: .leading, spacing: 4) {
                                Text(template.name)
                                    .font(.system(size: 16, weight: .semibold, design: .rounded))
                                    .foregroundStyle(Color.hangInk)
                                Text(templateSubtitle(template))
                                    .font(.system(size: 13, weight: .medium, design: .rounded))
                                    .foregroundStyle(Color.hangMuted)
                            }
                        }
                        .accessibilityIdentifier("freeWorkout.template.\(template.id.uuidString)")
                    }
                }
            }
        }
        .listStyle(.insetGrouped)
        .scrollContentBackground(.hidden)
    }

    private func prepare() {
        FreeWorkoutDraftMigration.runIfNeeded()
        refresh()
    }

    private func refresh() {
        activeLog = ActiveFreeWorkoutStore.load()
        latest = FreeWorkoutHistoryStore.latest()
        templates = FreeWorkoutTemplateStore.load()
    }

    private func discardActive() {
        ActiveFreeWorkoutStore.clear()
        activeLog = nil
        path.removeAll()
        refresh()
    }

    private func startEmpty() {
        let log = FreeWorkoutLog(boardID: store.selectedBoard.id)
        ActiveFreeWorkoutStore.save(log)
        activeLog = log
        path = [.session]
    }

    private func startFromLatest() {
        guard let latest else { return }
        var log = latest.uncheckedClone()
        log.boardID = store.selectedBoard.id
        ActiveFreeWorkoutStore.save(log)
        activeLog = log
        path = [.session]
    }

    private func startFromTemplate(_ template: FreeWorkoutTemplate) {
        var log = template.log.uncheckedClone()
        log.boardID = store.selectedBoard.id
        ActiveFreeWorkoutStore.save(log)
        activeLog = log
        path = [.session]
    }

    private func resumeSubtitle(for log: FreeWorkoutLog) -> String {
        let exerciseCount = log.exercises.count
        let completedSets = log.exercises.reduce(0) { partial, exercise in
            partial + exercise.sets.filter(\.isCompleted).count
        }
        let exerciseWord = exerciseCount == 1 ? "exercise" : "exercises"
        let setWord = completedSets == 1 ? "set" : "sets"
        return "\(exerciseCount) \(exerciseWord) · \(completedSets) completed \(setWord)"
    }

    private func templateSubtitle(_ template: FreeWorkoutTemplate) -> String {
        let count = template.log.exercises.count
        return count == 1 ? "1 exercise" : "\(count) exercises"
    }
}

private enum FreeWorkoutStartRoute: Hashable {
    case session
}
