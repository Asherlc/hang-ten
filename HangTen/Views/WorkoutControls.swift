import SwiftUI

struct WorkoutPrimaryControl: View {
    let isComplete: Bool
    let countdown: Int
    let isRunning: Bool
    let isFirstStart: Bool
    let action: () -> Void

    private var title: String {
        if isComplete { return "Review session" }
        if countdown > 0 { return "Cancel countdown" }
        if isRunning { return "Pause" }
        return isFirstStart ? "Start" : "Resume"
    }

    private var symbol: String {
        if isComplete { return "list.bullet.rectangle" }
        if countdown > 0 { return "xmark" }
        return isRunning ? "pause.fill" : "play.fill"
    }

    var body: some View {
        Button(action: action) {
            HStack {
                Image(systemName: symbol)
                Text(title)
            }
            .frame(maxWidth: .infinity)
            .font(.system(.callout, design: .rounded, weight: .bold))
        }
        .buttonStyle(.borderedProminent)
        .controlSize(.large)
        .tint(.hangGreenDark)
        .accessibilityIdentifier("workout.primaryControl")
    }
}

struct WorkoutSkipControl: View {
    let stepLabel: String
    let isEnabled: Bool
    var compact = false
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            Group {
                if compact {
                    Image(systemName: "forward.fill")
                } else {
                    Label("Skip step", systemImage: "forward.fill")
                }
            }
            .frame(maxWidth: .infinity)
            .font(.system(.subheadline, design: .rounded, weight: .bold))
            .foregroundStyle(Color.hangGreenDark)
            .padding(.horizontal, compact ? 13 : 0)
            .padding(.vertical, 10)
            .background(Color.hangGreen.opacity(0.16), in: RoundedRectangle(cornerRadius: 13, style: .continuous))
        }
        .buttonStyle(.plain)
        .disabled(!isEnabled)
        .accessibilityLabel("Skip step \(stepLabel)")
        .accessibilityIdentifier("workout.skipStep")
    }
}

struct WorkoutStopwatchControl: View {
    let stopwatch: WorkoutStopwatch
    let elapsed: TimeInterval
    var compact = false
    let onToggle: () -> Void

    private var title: String {
        if stopwatch.isFinalized { return "Stopwatch finalized" }
        if stopwatch.isRunning { return "Stop stopwatch" }
        return stopwatch.hasStarted ? "Resume stopwatch" : "Start stopwatch"
    }

    private var layout: AnyLayout {
        compact ? AnyLayout(HStackLayout(spacing: 10)) : AnyLayout(VStackLayout(spacing: 6))
    }

    var body: some View {
        layout {
            Text(WorkoutTimeText.stopwatch(elapsed))
                .font(.system(compact ? .title2 : .largeTitle, design: .rounded, weight: .heavy).monospacedDigit())
                .foregroundStyle(Color.hangInk)
                .lineLimit(1)
                .minimumScaleFactor(0.6)
                .frame(minWidth: compact ? 68 : nil, maxWidth: compact ? nil : .infinity, alignment: compact ? .leading : .center)

            Button(action: onToggle) {
                Label(title, systemImage: stopwatch.isRunning ? "pause.fill" : stopwatch.isFinalized ? "checkmark" : "stopwatch")
                    .frame(maxWidth: compact ? nil : .infinity)
                    .font(.system(compact ? .footnote : .subheadline, design: .rounded, weight: .bold))
                    .foregroundStyle(Color.hangGreenDark)
                    .padding(.horizontal, compact ? 12 : 0)
                    .padding(.vertical, compact ? 8 : 10)
                    .background(Color.hangGreen.opacity(0.16), in: RoundedRectangle(cornerRadius: compact ? 11 : 13, style: .continuous))
            }
            .buttonStyle(.plain)
            .disabled(stopwatch.isFinalized)
            .accessibilityLabel(title)
            .accessibilityIdentifier("workout.stopwatch.toggle")

            if compact { Spacer(minLength: 0) }
        }
        .padding(.vertical, compact ? 0 : 4)
        .accessibilityIdentifier("workout.stopwatch")
    }
}
