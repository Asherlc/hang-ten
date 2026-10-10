import SwiftUI

struct PlanHoldSubstitutionCard: View {
    let requests: [PlanHoldSubstitutionRequest]
    @Binding var selections: [PlanHoldSubstitutionRequest.ID: String]
    let isComplete: Bool

    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            Label(isComplete ? "Your adapted session" : "Choose substitutes",
                  systemImage: "arrow.triangle.swap")
                .font(.system(.headline, design: .rounded, weight: .bold))
                .foregroundStyle(Color.hangInk)
            Text("This board is missing required holds. Substitutions are your adaptation of the source plan; timing and grip instructions stay the same.")
                .font(.system(.footnote, design: .rounded, weight: .medium))
                .foregroundStyle(Color.hangMuted)
                .fixedSize(horizontal: false, vertical: true)

            ForEach(Array(requests.enumerated()), id: \.element.id) { index, request in
                VStack(alignment: .leading, spacing: 8) {
                    Text("Plan requires: \(request.requiredHoldLabel)")
                        .font(.system(.subheadline, design: .rounded, weight: .semibold))
                        .foregroundStyle(Color.hangInk)
                        .fixedSize(horizontal: false, vertical: true)
                    if request.stepTitles.count > 1 {
                        Text("This choice applies to each matching cue.")
                            .font(.system(.caption, design: .rounded))
                            .foregroundStyle(Color.hangMuted)
                    }
                    if request.options.isEmpty {
                        Text("No substitute on this board supports the required hands and grip. Choose another board or routine.")
                            .font(.system(.footnote, design: .rounded, weight: .medium))
                            .foregroundStyle(Color.hangMuted)
                            .fixedSize(horizontal: false, vertical: true)
                    } else {
                        substitutionMenu(for: request, index: index)
                    }
                }
                if index < requests.count - 1 { Divider() }
            }
            if !isComplete, requests.allSatisfy({ !$0.options.isEmpty }) {
                Text("Choose a substitute for each missing requirement to start.")
                    .font(.system(.footnote, design: .rounded, weight: .semibold))
                    .foregroundStyle(Color.hangMuted)
                    .fixedSize(horizontal: false, vertical: true)
            }
        }
        .hangCard()
        .accessibilityElement(children: .contain)
        .accessibilityIdentifier("plan.substitutions")
    }

    private func substitutionMenu(for request: PlanHoldSubstitutionRequest, index: Int) -> some View {
        let selected = request.options.first { $0.id == selections[request.id] }
        return Menu {
            ForEach(Array(request.options.enumerated()), id: \.element.id) { optionIndex, option in
                Button {
                    selections[request.id] = option.id
                } label: {
                    if selected?.id == option.id {
                        Label(option.label, systemImage: "checkmark")
                    } else {
                        Text(option.label)
                    }
                }
                .accessibilityIdentifier("plan.substitution.option.\(index).\(optionIndex)")
            }
            if selected != nil {
                Button("Clear substitution") { selections[request.id] = nil }
            }
        } label: {
            HStack(alignment: .top, spacing: 8) {
                Text(selected?.label ?? "Choose a substitute")
                    .multilineTextAlignment(.leading)
                    .fixedSize(horizontal: false, vertical: true)
                Spacer(minLength: 0)
                Image(systemName: "chevron.up.chevron.down")
            }
            .font(.system(.subheadline, design: .rounded, weight: .semibold))
            .foregroundStyle(Color.hangGreenDark)
            .padding(12)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(Color.hangGreen.opacity(0.15), in: RoundedRectangle(cornerRadius: 10))
        }
        .accessibilityLabel("Substitute for \(request.requiredHoldLabel): \(selected?.label ?? "Choose a substitute")")
        .accessibilityIdentifier("plan.substitution.picker.\(index)")
    }
}
