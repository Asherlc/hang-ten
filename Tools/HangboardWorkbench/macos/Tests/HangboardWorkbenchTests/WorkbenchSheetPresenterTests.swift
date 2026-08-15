import AppKit
import XCTest
@testable import HangboardWorkbench

@MainActor
final class WorkbenchSheetPresenterTests: XCTestCase {
    func testAlertCompletionWaitsForTheSheetResponse() {
        let presenter = WorkbenchSheetPresenter()
        let alert = RecordingAlert()
        var receivedResponse: NSApplication.ModalResponse?

        presenter.present(alert, for: NSWindow()) { response in
            receivedResponse = response
        }

        XCTAssertNil(receivedResponse)
        alert.respond(with: .alertSecondButtonReturn)
        XCTAssertEqual(receivedResponse, .alertSecondButtonReturn)
    }

    func testOpenPanelCompletionWaitsForTheSheetResponse() {
        let presenter = WorkbenchSheetPresenter()
        let panel = RecordingOpenPanel()
        var receivedResponse: NSApplication.ModalResponse?

        presenter.present(panel, for: NSWindow()) { response in
            receivedResponse = response
        }

        XCTAssertNil(receivedResponse)
        panel.respond(with: .OK)
        XCTAssertEqual(receivedResponse, .OK)
    }

    func testOpenPanelWithoutWindowWaitsForTheApplicationModalResponse() {
        let presenter = WorkbenchSheetPresenter()
        let panel = RecordingOpenPanel()
        var receivedResponse: NSApplication.ModalResponse?

        presenter.present(panel, for: nil) { response in
            receivedResponse = response
        }

        XCTAssertNil(receivedResponse)
        panel.respondToApplicationModal(with: .OK)
        XCTAssertEqual(receivedResponse, .OK)
    }
}

@MainActor
private final class RecordingAlert: NSAlert {
    private var sheetCompletion: ((NSApplication.ModalResponse) -> Void)?

    override func beginSheetModal(
        for sheetWindow: NSWindow,
        completionHandler handler: ((NSApplication.ModalResponse) -> Void)? = nil
    ) {
        sheetCompletion = handler
    }

    func respond(with response: NSApplication.ModalResponse) {
        sheetCompletion?(response)
    }
}

@MainActor
private final class RecordingOpenPanel: NSOpenPanel {
    private var sheetCompletion: ((NSApplication.ModalResponse) -> Void)?
    private var applicationModalCompletion: ((NSApplication.ModalResponse) -> Void)?

    override func beginSheetModal(
        for window: NSWindow,
        completionHandler handler: @escaping (NSApplication.ModalResponse) -> Void
    ) {
        sheetCompletion = handler
    }

    override func begin(
        completionHandler handler: @escaping (NSApplication.ModalResponse) -> Void
    ) {
        applicationModalCompletion = handler
    }

    func respond(with response: NSApplication.ModalResponse) {
        sheetCompletion?(response)
    }

    func respondToApplicationModal(with response: NSApplication.ModalResponse) {
        applicationModalCompletion?(response)
    }
}
