import Sentry

final class SentryUserReports: UserReportSubmitting {
    private static let managedTagKeys = [
        "report_source",
        "board_id",
        "hold_id",
        "plan_id",
        "step_id"
    ]

    func submit(_ report: HangTenUserReport) {
        // SentrySDK.capture(feedback:) applies the hub's current scope (no
        // isolated-scope overload in 8.58). Set tags immediately before capture
        // and remove the keys we added afterward.
        let tags = report.tags
        SentrySDK.configureScope { scope in
            for (key, value) in tags {
                scope.setTag(value: value, key: key)
            }
        }

        let feedback = SentryFeedback(
            message: report.message,
            name: nil,
            email: report.contactEmail,
            source: .custom,
            associatedEventId: nil,
            attachments: nil
        )
        SentrySDK.capture(feedback: feedback)

        SentrySDK.configureScope { scope in
            for key in Self.managedTagKeys {
                scope.removeTag(key: key)
            }
        }
    }
}
