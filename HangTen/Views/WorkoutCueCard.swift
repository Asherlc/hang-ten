import SwiftUI

struct WorkoutCueCard: View {
    let rows: [InstructionAccessoryCardRow]
    let title: String
    let intervalTitle: String?
    let tint: Color
    var compact = false

    var body: some View {
        VStack(alignment: .leading, spacing: compact ? 5 : 11) {
            HStack {
                SectionLabel(title: title)
                if !compact, let intervalTitle {
                    Spacer()
                    Text(intervalTitle)
                        .font(.system(.caption, design: .rounded, weight: .bold))
                        .foregroundStyle(tint)
                }
            }

            if let instruction = rows.first(where: { $0.kind == .instruction }) {
                Text(instruction.text)
                    .font(.system(compact ? .subheadline : .callout, design: .rounded, weight: .semibold))
                    .foregroundStyle(Color.hangInk)
                    .lineLimit(compact ? 2 : nil)
                    .minimumScaleFactor(compact ? 0.82 : 1)
                    .fixedSize(horizontal: false, vertical: !compact)
            }

            if let accessory = rows.first(where: { $0.kind == .accessory }) {
                Text(accessory.text)
                    .font(.system(compact ? .caption2 : .caption, design: .rounded, weight: .bold))
                    .foregroundStyle(tint)
                    .lineLimit(compact ? 1 : nil)
                    .minimumScaleFactor(compact ? 0.78 : 1)
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .hangCard(padding: compact ? 12 : 18)
    }
}
