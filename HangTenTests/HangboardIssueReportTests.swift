import XCTest
@testable import HangTen

final class HangboardIssueReportTests: XCTestCase {
    func testMakeIncludesExactlyTheRequiredHiddenFields() throws {
        let url = try XCTUnwrap(HangboardIssueReportURL.make(
            formURL: URL(string: "https://tally.so/r/XxbJG4")!,
            context: fixtureContext()
        ))
        let components = try XCTUnwrap(URLComponents(url: url, resolvingAgainstBaseURL: false))
        let values = try queryValues(from: components)

        XCTAssertEqual(components.path, "/r/XxbJG4")
        XCTAssertEqual(Set(values.keys), Set([
            "board_id",
            "board_name",
            "manufacturer",
            "presentation_id",
            "presentation_name",
            "platform",
            "app_version",
            "build"
        ]))
        XCTAssertEqual(values["board_id"], "test.pocket-edge")
        XCTAssertEqual(values["board_name"], "Pocket & Edge")
        XCTAssertEqual(values["manufacturer"], "Test / Climbing")
        XCTAssertEqual(values["presentation_id"], "face-b")
        XCTAssertEqual(values["presentation_name"], "Face B — deep slopers")
        XCTAssertEqual(values["platform"], "iOS")
        XCTAssertEqual(values["app_version"], "2.3.4 beta")
        XCTAssertEqual(values["build"], "567")
    }

    func testMakeDoesNotIncludeDeviceOrInterfaceOrientationFields() throws {
        let url = try XCTUnwrap(HangboardIssueReportURL.make(
            formURL: URL(string: "https://tally.so/r/XxbJG4")!,
            context: fixtureContext()
        ))
        let names = Set(try XCTUnwrap(
            URLComponents(url: url, resolvingAgainstBaseURL: false)?.queryItems
        ).map(\.name))

        XCTAssertFalse(names.contains("interface_orientation"))
        XCTAssertFalse(names.contains("device_orientation"))
        XCTAssertFalse(names.contains("device"))
        XCTAssertFalse(names.contains("device_id"))
    }

    func testContextUsesTheSelectedPhysicalPresentation() throws {
        let board = fixtureBoard()
        let faceB = try XCTUnwrap(board.presentation(id: "face-b"))
        let context = HangboardIssueReportContext(
            board: board,
            presentation: faceB,
            appVersion: "1.0",
            build: "1"
        )
        let url = try XCTUnwrap(HangboardIssueReportURL.make(
            formURL: URL(string: "https://tally.so/r/XxbJG4")!,
            context: context
        ))
        let values = try queryValues(from: try XCTUnwrap(
            URLComponents(url: url, resolvingAgainstBaseURL: false)
        ))

        XCTAssertEqual(values["presentation_id"], "face-b")
        XCTAssertEqual(values["presentation_name"], "Face B — deep slopers")
    }

    func testMakeRoundTripsSpecialCharactersThroughURLQueryEncoding() throws {
        let url = try XCTUnwrap(HangboardIssueReportURL.make(
            formURL: URL(string: "https://tally.so/r/XxbJG4")!,
            context: fixtureContext()
        ))
        let values = try queryValues(from: try XCTUnwrap(
            URLComponents(url: url, resolvingAgainstBaseURL: false)
        ))

        XCTAssertEqual(values["board_name"], "Pocket & Edge")
        XCTAssertEqual(values["manufacturer"], "Test / Climbing")
        XCTAssertEqual(values["presentation_name"], "Face B — deep slopers")
        XCTAssertEqual(values["app_version"], "2.3.4 beta")
        XCTAssertTrue(url.absoluteString.contains("Pocket%20%26%20Edge"))
    }

    func testContextReadsAppVersionAndBuildFromBundle() throws {
        let bundle = try makeBundle(info: [
            "CFBundleShortVersionString": "9.8.7",
            "CFBundleVersion": "654"
        ])
        let context = HangboardIssueReportContext(
            board: fixtureBoard(),
            presentation: try XCTUnwrap(fixtureBoard().presentation(id: "face-b")),
            bundle: bundle
        )

        XCTAssertEqual(context.appVersion, "9.8.7")
        XCTAssertEqual(context.build, "654")
    }

    func testContextUsesUnknownOnlyWhenBundleVersionValuesAreAbsent() throws {
        let context = HangboardIssueReportContext(
            board: fixtureBoard(),
            presentation: try XCTUnwrap(fixtureBoard().presentation(id: "face-b")),
            bundle: try makeBundle(info: [:])
        )

        XCTAssertEqual(context.appVersion, "unknown")
        XCTAssertEqual(context.build, "unknown")
    }

    func testConfigurationAcceptsTallyAndTallySubdomainHTTPSURLs() {
        XCTAssertEqual(
            HangboardIssueReportConfiguration.formURL(rawValue: "https://tally.so/r/XxbJG4")?.absoluteString,
            "https://tally.so/r/XxbJG4"
        )
        XCTAssertEqual(
            HangboardIssueReportConfiguration.formURL(rawValue: "https://forms.tally.so/r/report")?.host,
            "forms.tally.so"
        )
    }

    func testConfigurationRejectsBlankInsecureNonTallyAndMalformedValues() {
        let invalidValues = [
            "",
            "   ",
            "http://tally.so/r/report",
            "https://example.com/r/report",
            "https://tally.so.example.com/r/report",
            "not a URL"
        ]

        for value in invalidValues {
            XCTAssertNil(
                HangboardIssueReportConfiguration.formURL(rawValue: value),
                "Expected invalid configuration to be rejected: \(value)"
            )
        }
    }

    func testConfigurationReadsThePublishedFormURLFromBundle() throws {
        let bundle = try makeBundle(info: [
            "HANGBOARD_REPORT_FORM_URL": "https://tally.so/r/XxbJG4"
        ])

        XCTAssertEqual(
            HangboardIssueReportConfiguration.formURL(bundle: bundle)?.absoluteString,
            "https://tally.so/r/XxbJG4"
        )
    }

    private func fixtureContext() -> HangboardIssueReportContext {
        let board = fixtureBoard()
        return HangboardIssueReportContext(
            board: board,
            presentation: board.presentations[1],
            appVersion: "2.3.4 beta",
            build: "567"
        )
    }

    private func fixtureBoard() -> TrainingBoard {
        TrainingBoard(
            id: "test.pocket-edge",
            manufacturer: "Test / Climbing",
            name: "Pocket & Edge",
            subtitle: "Test board",
            dimensions: nil,
            aspectRatio: 2,
            holds: [],
            productURL: URL(string: "https://example.com/board")!,
            photoAssetName: nil,
            presentations: [
                BoardPresentation(
                    id: "face-a",
                    name: "Face A",
                    aspectRatio: 2,
                    isDefault: true
                ),
                BoardPresentation(
                    id: "face-b",
                    name: "Face B — deep slopers",
                    aspectRatio: 2,
                    isDefault: false
                )
            ]
        )
    }

    private func queryValues(from components: URLComponents) throws -> [String: String] {
        let items = try XCTUnwrap(components.queryItems)
        return try Dictionary(uniqueKeysWithValues: items.map { item in
            (item.name, try XCTUnwrap(item.value))
        })
    }

    private func makeBundle(info: [String: Any]) throws -> Bundle {
        let bundleURL = FileManager.default.temporaryDirectory
            .appendingPathComponent(UUID().uuidString)
            .appendingPathExtension("bundle")
        try FileManager.default.createDirectory(
            at: bundleURL,
            withIntermediateDirectories: true
        )
        addTeardownBlock {
            try? FileManager.default.removeItem(at: bundleURL)
        }

        var bundleInfo = info
        bundleInfo["CFBundleIdentifier"] = "com.hangten.tests.\(UUID().uuidString)"
        bundleInfo["CFBundleName"] = "HangboardIssueReportTests"
        bundleInfo["CFBundlePackageType"] = "BNDL"
        let plistData = try PropertyListSerialization.data(
            fromPropertyList: bundleInfo,
            format: .xml,
            options: 0
        )
        try plistData.write(to: bundleURL.appendingPathComponent("Info.plist"))
        return try XCTUnwrap(Bundle(url: bundleURL))
    }
}
