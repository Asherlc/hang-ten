import SwiftUI

struct WorkoutTimerView: View {
    let remaining: TimeInterval
    var compact = false
    @ScaledMetric(relativeTo: .largeTitle) private var timerSize = 46.0
    @ScaledMetric(relativeTo: .largeTitle) private var compactTimerSize = 34.0

    var body: some View {
        Text(WorkoutTimeText.countdown(remaining))
            .font(.system(size: compact ? compactTimerSize : timerSize, weight: .heavy, design: .rounded).monospacedDigit())
            .foregroundStyle(Color.hangInk)
            .lineLimit(WorkoutPresentationContent.portraitTimerLineLimit)
            .minimumScaleFactor(0.6)
            .layoutPriority(2)
            .accessibilityIdentifier("workout.timer")
    }
}

enum WorkoutTimeText {
    static func countdown(_ value: TimeInterval) -> String {
        format(value, rounding: .up)
    }

    static func stopwatch(_ value: TimeInterval) -> String {
        format(value, rounding: .down)
    }

    private static func format(_ value: TimeInterval, rounding: FloatingPointRoundingRule) -> String {
        let seconds = max(0, Int(value.rounded(rounding)))
        return String(format: "%02d:%02d", seconds / 60, seconds % 60)
    }
}
