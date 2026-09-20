import SwiftUI

struct ReportProblemView: View {
    @EnvironmentObject private var store: AppStore
    @Environment(\.dismiss) private var dismiss

    let source: HangTenUserReport.Source
    let boardID: String
    var holdID: String? = nil
    var planID: String? = nil
    var stepID: String? = nil

    @State private var message = ""
    @State private var contactEmail = ""
    @State private var showsConfirmation = false

    private var trimmedMessage: String {
        message.trimmingCharacters(in: .whitespacesAndNewlines)
    }

    private var canSend: Bool {
        !trimmedMessage.isEmpty
    }

    var body: some View {
        NavigationStack {
            ScrollView(showsIndicators: false) {
                VStack(alignment: .leading, spacing: 20) {
                    Text("Wrong hold, highlight alignment, or workout step? Describe what you see.")
                        .font(.system(size: 15, weight: .medium, design: .rounded))
                        .foregroundStyle(Color.hangMuted)

                    VStack(alignment: .leading, spacing: 8) {
                        SectionLabel(title: "What went wrong")
                        TextEditor(text: $message)
                            .font(.system(size: 16, weight: .medium, design: .rounded))
                            .foregroundStyle(Color.hangInk)
                            .scrollContentBackground(.hidden)
                            .frame(minHeight: 140)
                            .padding(12)
                            .background(Color.hangBackground, in: RoundedRectangle(cornerRadius: 16, style: .continuous))
                            .accessibilityIdentifier("reportProblem.message")
                    }

                    VStack(alignment: .leading, spacing: 8) {
                        SectionLabel(title: "Email (optional)")
                        TextField("Email for follow-up", text: $contactEmail)
                            .font(.system(size: 16, weight: .medium, design: .rounded))
                            .foregroundStyle(Color.hangInk)
                            .textContentType(.emailAddress)
                            .keyboardType(.emailAddress)
                            .textInputAutocapitalization(.never)
                            .autocorrectionDisabled()
                            .padding(12)
                            .background(Color.hangBackground, in: RoundedRectangle(cornerRadius: 16, style: .continuous))
                            .accessibilityIdentifier("reportProblem.email")
                    }

                    Button(action: send) {
                        Text("Send report")
                            .font(.system(size: 17, weight: .bold, design: .rounded))
                            .frame(maxWidth: .infinity)
                            .padding(.vertical, 14)
                    }
                    .buttonStyle(.borderedProminent)
                    .tint(Color.hangGreenDark)
                    .disabled(!canSend)
                    .accessibilityIdentifier("reportProblem.send")
                }
                .padding(20)
            }
            .background(Color.hangBackground)
            .navigationTitle("Report a problem")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") {
                        dismiss()
                    }
                    .accessibilityIdentifier("reportProblem.cancel")
                }
            }
            .alert("Thanks — we got your report.", isPresented: $showsConfirmation) {
                Button("OK", role: .cancel) {
                    dismiss()
                }
            }
        }
        .accessibilityIdentifier("reportProblem.screen")
    }

    private func send() {
        guard canSend else { return }
        store.submitUserReport(
            HangTenUserReport(
                source: source,
                message: trimmedMessage,
                contactEmail: contactEmail,
                boardID: boardID,
                holdID: holdID,
                planID: planID,
                stepID: stepID
            )
        )
        showsConfirmation = true
    }
}
