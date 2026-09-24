import SwiftUI

/// Full-screen guided hang overlay: countdown, board highlight, pause / cancel / complete.
struct FreeWorkoutGuidedHangView: View {
    @EnvironmentObject private var audioCoach: WorkoutAudioCoach
    @AppStorage("workoutAudioCuesEnabled") private var audioCuesEnabled = true

    let board: BoardRevision
    let holdName: String
    let weightKGF: Double?
    let duration: TimeInterval
    let highlightedHoldIDs: Set<String>
    let onComplete: (_ elapsed: TimeInterval) -> Void
    let onCancel: () -> Void

    @State private var countdown = FreeWorkoutGuidedHangCountdown()
    @State private var didFinish = false

    var body: some View {
        TimelineView(.periodic(from: .now, by: 0.05)) { context in
            let now = context.date
            let remaining = countdown.remaining(at: now)
            VStack(spacing: 0) {
                header(remaining: remaining)
                BoardMapView(board: board, highlightedHoldIDs: highlightedHoldIDs)
                    .frame(minHeight: 200)
                    .clipShape(RoundedRectangle(cornerRadius: 18, style: .continuous))
                    .padding(.horizontal, 20)
                    .padding(.top, 12)
                    .accessibilityIdentifier("freeWorkout.guidedHang.boardMap")

                Spacer(minLength: 16)

                Text(countdownLabel(remaining))
                    .font(.system(size: 72, weight: .bold, design: .rounded))
                    .foregroundStyle(Color.hangInk)
                    .monospacedDigit()
                    .accessibilityIdentifier("freeWorkout.guidedHang.remaining")

                if countdown.isPaused {
                    Text("Paused")
                        .font(.system(size: 16, weight: .semibold, design: .rounded))
                        .foregroundStyle(Color.hangMuted)
                        .padding(.top, 4)
                }

                Spacer(minLength: 16)

                controls(at: now)
                    .padding(.horizontal, 20)
                    .padding(.bottom, 28)
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity)
            .background(Color.hangBackground)
            .onChange(of: now) { _, date in
                guard !didFinish else { return }
                var next = countdown
                next.tick(at: date)
                if next != countdown {
                    countdown = next
                }
                if next.isCompleted {
                    finish(elapsed: next.plannedDuration)
                }
            }
        }
        .onAppear(perform: beginHang)
        .onDisappear {
            audioCoach.stop()
        }
        .accessibilityElement(children: .contain)
        .accessibilityIdentifier("freeWorkout.guidedHang")
    }

    private func header(remaining _: TimeInterval) -> some View {
        VStack(alignment: .leading, spacing: 6) {
            SectionLabel(title: "Guided hang")
            Text(holdName)
                .font(.system(size: 24, weight: .bold, design: .rounded))
                .foregroundStyle(Color.hangInk)
            HStack(spacing: 12) {
                Text(FreeWorkoutDraft.durationLabel(duration))
                if let weightKGF {
                    Text("\(weightKGF.formatted()) kg")
                }
            }
            .font(.system(size: 15, weight: .semibold, design: .rounded))
            .foregroundStyle(Color.hangMuted)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(.horizontal, 20)
        .padding(.top, 20)
    }

    private func controls(at now: Date) -> some View {
        HStack(spacing: 12) {
            Button(countdown.isPaused ? "Resume" : "Pause") {
                togglePause(at: now)
            }
            .buttonStyle(.bordered)
            .tint(.hangGreenDark)
            .accessibilityIdentifier("freeWorkout.guidedHang.pause")

            Button("Cancel", role: .cancel) {
                cancelHang()
            }
            .buttonStyle(.bordered)
            .accessibilityIdentifier("freeWorkout.guidedHang.cancel")

            Button("Complete early") {
                finish(elapsed: countdown.elapsed(at: now))
            }
            .buttonStyle(.borderedProminent)
            .tint(.hangGreenDark)
            .accessibilityIdentifier("freeWorkout.guidedHang.completeEarly")
        }
        .controlSize(.large)
    }

    private func beginHang() {
        countdown.start(duration: duration)
        armEndCountdownAudio(remaining: duration, at: WorkoutClock.monotonicTime)
    }

    private func togglePause(at now: Date) {
        if countdown.isPaused {
            countdown.resume(at: now)
            armEndCountdownAudio(
                remaining: countdown.remaining(at: now),
                at: WorkoutClock.monotonicTime
            )
        } else {
            audioCoach.stop()
            countdown.pause(at: now)
        }
    }

    private func cancelHang() {
        guard !didFinish else { return }
        didFinish = true
        audioCoach.stop()
        countdown.cancel()
        onCancel()
    }

    private func finish(elapsed: TimeInterval) {
        guard !didFinish else { return }
        didFinish = true
        audioCoach.stop()
        countdown.complete()
        onComplete(max(1, elapsed))
    }

    private func armEndCountdownAudio(remaining: TimeInterval, at monotonicNow: TimeInterval) {
        audioCoach.stop()
        guard audioCuesEnabled else { return }
        guard let plan = FreeWorkoutGuidedHangCountdown.endCountdownAudio(
            plannedDuration: countdown.plannedDuration > 0
                ? countdown.plannedDuration
                : duration,
            remaining: remaining
        ) else { return }

        if audioCoach.countdownPreparationState == .idle
            || audioCoach.countdownPreparationState == .failed
        {
            audioCoach.prepareCountdownAudio()
        }

        let startUptime = monotonicNow + plan.delay
        _ = audioCoach.startCountdown(plan.schedule, startUptime: startUptime)
    }

    private func countdownLabel(_ remaining: TimeInterval) -> String {
        let totalSeconds = Int(remaining.rounded(.up))
        let minutes = totalSeconds / 60
        let seconds = totalSeconds % 60
        return String(format: "%d:%02d", minutes, seconds)
    }
}
