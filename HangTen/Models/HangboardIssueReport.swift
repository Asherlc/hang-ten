import Foundation

struct HangboardIssueReportContext: Equatable {
    let boardID: String
    let boardName: String
    let manufacturer: String
    let presentationID: String
    let presentationName: String
    let platform: String
    let appVersion: String
    let build: String

    init(
        board: TrainingBoard,
        presentation: BoardPresentation,
        appVersion: String,
        build: String
    ) {
        boardID = board.id
        boardName = board.name
        manufacturer = board.manufacturer
        presentationID = presentation.id
        presentationName = presentation.name
        platform = "iOS"
        self.appVersion = appVersion
        self.build = build
    }

    init(
        board: TrainingBoard,
        presentation: BoardPresentation,
        bundle: Bundle = .main
    ) {
        self.init(
            board: board,
            presentation: presentation,
            appVersion: bundle.object(forInfoDictionaryKey: "CFBundleShortVersionString") as? String
                ?? "unknown",
            build: bundle.object(forInfoDictionaryKey: "CFBundleVersion") as? String
                ?? "unknown"
        )
    }
}

enum HangboardIssueReportConfiguration {
    static func formURL(bundle: Bundle = .main) -> URL? {
        formURL(rawValue: bundle.object(forInfoDictionaryKey: "HANGBOARD_REPORT_FORM_URL") as? String)
    }

    static func formURL(rawValue: String?) -> URL? {
        guard let rawValue,
              !rawValue.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty,
              let components = URLComponents(string: rawValue),
              components.scheme?.lowercased() == "https",
              components.user == nil,
              components.password == nil,
              let host = components.host?.lowercased(),
              host == "tally.so" || host.hasSuffix(".tally.so")
        else {
            return nil
        }

        return components.url
    }
}

enum HangboardIssueReportURL {
    static func make(formURL: URL, context: HangboardIssueReportContext) -> URL? {
        guard HangboardIssueReportConfiguration.formURL(rawValue: formURL.absoluteString) != nil,
              var components = URLComponents(url: formURL, resolvingAgainstBaseURL: false)
        else {
            return nil
        }

        components.queryItems = [
            URLQueryItem(name: "board_id", value: context.boardID),
            URLQueryItem(name: "board_name", value: context.boardName),
            URLQueryItem(name: "manufacturer", value: context.manufacturer),
            URLQueryItem(name: "presentation_id", value: context.presentationID),
            URLQueryItem(name: "presentation_name", value: context.presentationName),
            URLQueryItem(name: "platform", value: context.platform),
            URLQueryItem(name: "app_version", value: context.appVersion),
            URLQueryItem(name: "build", value: context.build)
        ]
        return components.url
    }
}
