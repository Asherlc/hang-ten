import SwiftUI

struct WorkoutCueCard: View {
    let rows: [InstructionAccessoryCardRow]
    let title: String
    let tint: Color
    var compact = false

    var body: some View {
        VStack(alignment: .leading, spacing: compact ? 5 : 11) {
            SectionLabel(title: title)

            if let instruction = rows.first(where: { $0.kind == .instruction }) {
                Text(instruction.text)
                    .font(.system(compact ? .subheadline : .callout, design: .rounded, weight: .semibold))
                    .foregroundStyle(Color.hangInk)
                    .fixedSize(horizontal: false, vertical: true)
            }

            if let accessory = rows.first(where: { $0.kind == .accessory }) {
                Text(accessory.text)
                    .font(.system(compact ? .caption2 : .caption, design: .rounded, weight: .bold))
                    .foregroundStyle(tint)
                    .fixedSize(horizontal: false, vertical: true)
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .hangCard(padding: compact ? 12 : 18)
    }
}
