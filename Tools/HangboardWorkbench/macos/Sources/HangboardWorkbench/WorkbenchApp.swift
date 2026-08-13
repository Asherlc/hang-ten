import AppKit
import Darwin
import Foundation
import WebKit

struct HeadlessConfiguration: Equatable, Sendable {
    enum ArgumentError: Swift.Error, LocalizedError, Equatable {
        case duplicateOption(String)
        case missingValue(String)
        case missingRequiredOption(String)
        case invalidPort(String)
        case unknownOption(String)

        var errorDescription: String? {
            switch self {
            case let .duplicateOption(option):
                return "Headless option was supplied more than once: \(option)"
            case let .missingValue(option):
                return "Headless option requires a value: \(option)"
            case let .missingRequiredOption(option):
                return "Headless launch requires \(option)."
            case let .invalidPort(value):
                return "Headless port must be an integer from 0 through 65535, not \(value)."
            case let .unknownOption(option):
                return "Unknown headless option: \(option)"
            }
        }
    }

    let repositoryRoot: URL
    let port: UInt16

    static func parse(_ arguments: [String]) throws -> HeadlessConfiguration? {
        guard arguments.contains("--headless") else {
            return nil
        }

        var sawHeadless = false
        var repositoryRoot: URL?
        var port: UInt16?
        var index = arguments.startIndex
        while index < arguments.endIndex {
            let option = arguments[index]
            switch option {
            case "--headless":
                guard !sawHeadless else {
                    throw ArgumentError.duplicateOption(option)
                }
                sawHeadless = true
                index += 1
            case "--repository-root":
                guard repositoryRoot == nil else {
                    throw ArgumentError.duplicateOption(option)
                }
                let valueIndex = arguments.index(after: index)
                guard valueIndex < arguments.endIndex else {
                    throw ArgumentError.missingValue(option)
                }
                let value = arguments[valueIndex]
                guard !value.hasPrefix("--") else {
                    throw ArgumentError.missingValue(option)
                }
                repositoryRoot = URL(fileURLWithPath: value).standardizedFileURL
                index = arguments.index(after: valueIndex)
            case "--port":
                guard port == nil else {
                    throw ArgumentError.duplicateOption(option)
                }
                let valueIndex = arguments.index(after: index)
                guard valueIndex < arguments.endIndex else {
                    throw ArgumentError.missingValue(option)
                }
                let value = arguments[valueIndex]
                guard let parsedPort = UInt16(value) else {
                    throw ArgumentError.invalidPort(value)
                }
                port = parsedPort
                index = arguments.index(after: valueIndex)
            default:
                throw ArgumentError.unknownOption(option)
            }
        }

        guard let repositoryRoot else {
            throw ArgumentError.missingRequiredOption("--repository-root PATH")
        }
        guard let port else {
            throw ArgumentError.missingRequiredOption("--port PORT")
        }
        return HeadlessConfiguration(repositoryRoot: repositoryRoot, port: port)
    }
}

enum HeadlessRunner {
    static func run(
        configuration: HeadlessConfiguration,
        backend: any BackendControlling,
        waitForTermination: (@Sendable () async -> Void)? = nil
    ) async throws {
        // Constructing the default waiter installs the signal source before the
        // child launches, so SIGTERM cannot strand a backend during startup.
        let waitForTermination = waitForTermination ?? makeSIGTERMWaiter()
        _ = try await backend.start(repositoryRoot: configuration.repositoryRoot, port: configuration.port)
        await waitForTermination()
        await backend.stop()
    }

    private static func makeSIGTERMWaiter() -> @Sendable () async -> Void {
        let previousHandler = Darwin.signal(SIGTERM, SIG_IGN)
        let stream = AsyncStream<Void> { continuation in
            let source = DispatchSource.makeSignalSource(signal: SIGTERM, queue: .global(qos: .utility))
            source.setEventHandler {
                continuation.yield()
                continuation.finish()
            }
            continuation.onTermination = { _ in
                source.cancel()
                Darwin.signal(SIGTERM, previousHandler)
            }
            source.resume()
        }
        return {
            for await _ in stream {
                return
            }
        }
    }
}

@MainActor
final class WorkbenchSessionCoordinator {
    private(set) var activeSessionID: UUID?
    private var unexpectedExitHandler: ((BackendUnexpectedExit) -> Void)?
    private var exitObservationTask: Task<Void, Never>?

    func requestCheckoutReplacement(
        confirmDiscarding: (@escaping @MainActor (Bool) -> Void) -> Void,
        performReplacement: @escaping @MainActor () -> Void
    ) {
        confirmDiscarding { confirmed in
            guard confirmed else { return }
            performReplacement()
        }
    }

    func activateSession(
        _ session: BackendController.Session,
        onUnexpectedExit: @escaping (BackendUnexpectedExit) -> Void
    ) {
        activateSession(id: session.id, onUnexpectedExit: onUnexpectedExit)
        exitObservationTask = Task { [weak self] in
            for await exit in session.unexpectedExits {
                guard !Task.isCancelled else { return }
                self?.receiveUnexpectedExit(exit)
            }
        }
    }

    func activateSession(
        id: UUID,
        onUnexpectedExit: @escaping (BackendUnexpectedExit) -> Void
    ) {
        exitObservationTask?.cancel()
        exitObservationTask = nil
        activeSessionID = id
        unexpectedExitHandler = onUnexpectedExit
    }

    func deactivateSession() {
        exitObservationTask?.cancel()
        exitObservationTask = nil
        activeSessionID = nil
        unexpectedExitHandler = nil
    }

    func receiveUnexpectedExit(_ exit: BackendUnexpectedExit) {
        guard activeSessionID == exit.sessionID else { return }
        let handler = unexpectedExitHandler
        deactivateSession()
        handler?(exit)
    }
}

@main
enum WorkbenchMain {
    @MainActor
    static func main() async {
        do {
            if let headless = try HeadlessConfiguration.parse(Array(CommandLine.arguments.dropFirst())) {
                try await HeadlessRunner.run(configuration: headless, backend: BackendController())
                return
            }
        } catch {
            FileHandle.standardError.write(Data("Hangboard Workbench: \(error.localizedDescription)\n".utf8))
            Darwin.exit(2)
        }

        let application = NSApplication.shared
        let delegate = WorkbenchAppDelegate()
        application.delegate = delegate
        application.setActivationPolicy(.regular)
        withExtendedLifetime(delegate) {
            application.run()
        }
    }
}

@MainActor
private final class WorkbenchAppDelegate: NSObject, NSApplicationDelegate, NSWindowDelegate, WKNavigationDelegate, WKScriptMessageHandler {
    private enum Recovery: Equatable {
        case backendStopped
        case webContentStopped
        case connectionQuestionable
    }

    private let backend = BackendController()
    private let selection = CheckoutSelection()
    private let sessionCoordinator = WorkbenchSessionCoordinator()
    private let webView = WKWebView(frame: .zero)

    private var window: NSWindow?
    private var startupTask: Task<Void, Never>?
    private var shutdownInProgress = false
    private var shutdownComplete = false
    private var allowWindowClose = false
    private var activeCheckout: URL?
    private var activeSession: BackendController.Session?
    private var healthTask: Task<Void, Never>?
    private var startupGeneration = UUID()
    private var reportedFailureSessionID: UUID?

    func applicationDidFinishLaunching(_ notification: Notification) {
        webView.navigationDelegate = self
        webView.configuration.userContentController.add(self, name: "workbenchDiagnostics")
        installMainMenu()
        createWindow()
        NSApplication.shared.activate(ignoringOtherApps: true)

        if let checkout = selection.lastValidCheckout() {
            load(checkout)
        } else {
            chooseCheckout(nil)
        }
    }

    func applicationShouldTerminateAfterLastWindowClosed(_ sender: NSApplication) -> Bool {
        true
    }

    func applicationShouldTerminate(_ sender: NSApplication) -> NSApplication.TerminateReply {
        guard !shutdownComplete else {
            return .terminateNow
        }
        guard !shutdownInProgress else {
            return .terminateLater
        }

        requestShutdown { confirmed in
            sender.reply(toApplicationShouldTerminate: confirmed)
        }
        return .terminateLater
    }

    func windowShouldClose(_ sender: NSWindow) -> Bool {
        guard !allowWindowClose else {
            return true
        }
        requestShutdown { [weak self, weak sender] confirmed in
            guard confirmed, let self, let sender else { return }
            self.allowWindowClose = true
            sender.performClose(nil)
        }
        return false
    }

    @objc
    private func chooseCheckout(_ sender: Any?) {
        guard !shutdownInProgress else { return }
        let panel = NSOpenPanel()
        panel.title = "Choose Hang Ten Checkout"
        panel.message = "Choose the root directory of a Hang Ten checkout."
        panel.prompt = "Choose Checkout"
        panel.canChooseDirectories = true
        panel.canChooseFiles = false
        panel.allowsMultipleSelection = false
        panel.canCreateDirectories = false
        panel.directoryURL = selection.lastValidCheckout()

        guard panel.runModal() == .OK, let url = panel.url else {
            if selection.lastValidCheckout() == nil && webView.url == nil {
                showMessage(
                    title: "Choose a Hang Ten Checkout",
                    detail: "Hangboard Workbench needs a checkout before it can start.",
                    retryTitle: "Choose Checkout…"
                )
            }
            return
        }

        do {
            let checkout = try CheckoutSelection.validatedURL(url)
            sessionCoordinator.requestCheckoutReplacement(
                confirmDiscarding: { [weak self] completion in
                    self?.confirmDiscardingUnsavedChanges(
                        discardTitle: "Discard and Switch",
                        completion: completion
                    )
                },
                performReplacement: { [weak self] in
                    self?.load(checkout)
                }
            )
        } catch {
            showMessage(title: "That Folder Is Not a Hang Ten Checkout", detail: error.localizedDescription)
        }
    }

    private func load(_ checkout: URL) {
        let generation = UUID()
        startupGeneration = generation
        startupTask?.cancel()
        healthTask?.cancel()
        sessionCoordinator.deactivateSession()
        activeSession = nil
        reportedFailureSessionID = nil
        activeCheckout = checkout
        startupTask = Task { [weak self] in
            guard let self else { return }
            await self.backend.stop()
            guard !Task.isCancelled else { return }
            do {
                let session = try await self.backend.startSession(repositoryRoot: checkout)
                guard !Task.isCancelled, self.startupGeneration == generation else {
                    await self.backend.stop(session: session)
                    return
                }
                self.sessionCoordinator.activateSession(session) { [weak self] exit in
                    self?.showRecoverableFailure(
                        title: "Hangboard Workbench Backend Stopped",
                        detail: exit.localizedDescription,
                        session: session,
                        recovery: .backendStopped
                    )
                }
                self.activeSession = session
                self.selection.remember(checkout)
                self.showWebView(session.url)
                self.monitorHealth(of: session)
            } catch is CancellationError {
                // A replacement checkout or app shutdown owns cleanup.
            } catch {
                guard self.startupGeneration == generation else { return }
                self.showMessage(
                    title: "Hangboard Workbench Could Not Start",
                    detail: error.localizedDescription
                )
            }
        }
    }

    private func createWindow() {
        let window = NSWindow(
            contentRect: NSRect(x: 0, y: 0, width: 1280, height: 820),
            styleMask: [.titled, .closable, .miniaturizable, .resizable],
            backing: .buffered,
            defer: false
        )
        window.title = "Hangboard Workbench"
        window.minSize = NSSize(width: 900, height: 620)
        window.center()
        window.delegate = self
        window.contentView = webView
        window.makeKeyAndOrderFront(nil)
        self.window = window
    }

    private func installMainMenu() {
        let mainMenu = NSMenu()
        let appItem = NSMenuItem()
        mainMenu.addItem(appItem)

        let appMenu = NSMenu()
        let choose = appMenu.addItem(
            withTitle: "Choose Hang Ten Checkout…",
            action: #selector(chooseCheckout(_:)),
            keyEquivalent: "o"
        )
        choose.target = self
        appMenu.addItem(.separator())
        let quit = appMenu.addItem(
            withTitle: "Quit Hangboard Workbench",
            action: #selector(NSApplication.terminate(_:)),
            keyEquivalent: "q"
        )
        quit.target = NSApplication.shared
        appItem.submenu = appMenu
        NSApplication.shared.mainMenu = mainMenu
    }

    private func showWebView(_ url: URL) {
        window?.contentView = webView
        webView.load(URLRequest(url: url))
    }

    private func monitorHealth(of session: BackendController.Session) {
        healthTask?.cancel()
        healthTask = Task { [weak self] in
            var failures = 0
            while !Task.isCancelled {
                try? await Task.sleep(for: .seconds(2))
                guard !Task.isCancelled else { return }
                var request = URLRequest(url: session.url.appending(path: "api/health"))
                request.timeoutInterval = 1
                request.cachePolicy = .reloadIgnoringLocalAndRemoteCacheData
                request.setValue("no-store", forHTTPHeaderField: "Cache-Control")
                let healthy: Bool
                do {
                    let (data, response) = try await URLSession.shared.data(for: request)
                    healthy = (response as? HTTPURLResponse)?.statusCode == 200
                        && ((try? JSONSerialization.jsonObject(with: data)) as? [String: Any])?["ok"] as? Bool == true
                } catch {
                    healthy = false
                }
                failures = healthy ? 0 : failures + 1
                guard failures >= 3 else { continue }
                guard self?.activeSession?.id == session.id else { return }
                self?.showRecoverableFailure(
                    title: "Hangboard Workbench Backend Is Unreachable",
                    detail: "The backend failed three consecutive health checks.",
                    session: session,
                    recovery: .connectionQuestionable
                )
                return
            }
        }
    }

    func webView(_ webView: WKWebView, didFail navigation: WKNavigation!, withError error: Swift.Error) {
        guard (error as NSError).code != NSURLErrorCancelled else { return }
        guard let session = activeSession else { return }
        showRecoverableFailure(title: "Editor Navigation Failed", detail: error.localizedDescription, session: session, recovery: .connectionQuestionable)
    }

    func webView(_ webView: WKWebView, didFailProvisionalNavigation navigation: WKNavigation!, withError error: Swift.Error) {
        guard (error as NSError).code != NSURLErrorCancelled else { return }
        guard let session = activeSession else { return }
        showRecoverableFailure(title: "Editor Could Not Connect", detail: error.localizedDescription, session: session, recovery: .connectionQuestionable)
    }

    func webViewWebContentProcessDidTerminate(_ webView: WKWebView) {
        guard let session = activeSession else { return }
        showRecoverableFailure(
            title: "Editor Web Process Stopped",
            detail: "WebKit terminated the process displaying the editor.",
            session: session,
            recovery: .webContentStopped
        )
    }

    private func showRecoverableFailure(
        title: String,
        detail: String,
        session: BackendController.Session,
        recovery: Recovery
    ) {
        guard activeSession?.id == session.id, reportedFailureSessionID != session.id else { return }
        reportedFailureSessionID = session.id
        healthTask?.cancel()
        let alert = NSAlert()
        alert.alertStyle = .warning
        alert.messageText = title
        alert.informativeText = diagnosticDetail(detail, session: session)
        switch recovery {
        case .backendStopped:
            alert.addButton(withTitle: "Restart Backend…")
            alert.addButton(withTitle: "Keep Editor Open")
        case .webContentStopped:
            alert.addButton(withTitle: "Reload Editor")
            alert.addButton(withTitle: "Restart Backend…")
        case .connectionQuestionable:
            alert.addButton(withTitle: "Keep Editor Open")
            alert.addButton(withTitle: "Restart Backend…")
        }
        let response = alert.runModal()
        if recovery == .webContentStopped, response == .alertFirstButtonReturn {
            reportedFailureSessionID = nil
            webView.reload()
            monitorHealth(of: session)
        } else if (recovery == .connectionQuestionable && response == .alertSecondButtonReturn)
                    || (recovery != .connectionQuestionable && response == .alertFirstButtonReturn)
                    || (recovery == .webContentStopped && response == .alertSecondButtonReturn) {
            requestBackendRestart(session: session)
        } else {
            reportedFailureSessionID = nil
            // Do not immediately resume health alerts: retaining the editor is
            // an explicit choice to protect unsaved state and avoid alert loops.
        }
    }

    private func diagnosticDetail(_ detail: String, session: BackendController.Session) -> String {
        let mismatch = session.runtimeIdentity != "unknown" && session.checkoutIdentity != "unknown"
            && session.runtimeIdentity != session.checkoutIdentity
            ? "\nBuild mismatch: the packaged runtime and selected checkout are from different commits."
            : ""
        return "\(detail)\n\nBackend: \(session.url.absoluteString)\nRuntime build: \(session.runtimeIdentity)\nCheckout build: \(session.checkoutIdentity)\(mismatch)\nCheckout: \(activeCheckout?.path ?? "unknown")"
    }

    func userContentController(_ userContentController: WKUserContentController, didReceive message: WKScriptMessage) {
        guard message.name == "workbenchDiagnostics", let session = activeSession else { return }
        guard message.frameInfo.securityOrigin.host == session.url.host,
              message.frameInfo.securityOrigin.port == session.url.port else { return }
        guard let body = message.body as? [String: Any], body.count <= 5,
              Set(body.keys).isSubset(of: ["path", "category", "message", "status", "attempts"]),
              let path = body["path"] as? String,
              let category = body["category"] as? String,
              let detail = body["message"] as? String,
              path.count <= 256, path.hasPrefix("/api/"), !path.contains(".."),
              detail.count <= 1024,
              ["transport", "server", "unreadable-response"].contains(category) else { return }
        let statusNumber = body["status"] as? NSNumber
        guard statusNumber == nil || statusNumber!.doubleValue == Double(statusNumber!.intValue) else { return }
        let statusCode = statusNumber?.intValue
        guard statusCode == nil || (100...599).contains(statusCode!) else { return }
        if category == "server" { guard let statusCode, statusCode >= 500 else { return } }
        if category == "unreadable-response" {
            guard let statusCode, (200...299).contains(statusCode) || statusCode >= 500 else { return }
        }
        if category == "transport" {
            guard let attempts = body["attempts"] as? NSNumber,
                  attempts.doubleValue == Double(attempts.intValue),
                  (1...3).contains(attempts.intValue) else { return }
        } else if body["attempts"] != nil {
            return
        }
        let status = statusCode.map { ", HTTP \($0)" } ?? ""
        showRecoverableFailure(
            title: "Editor Request Failed",
            detail: "\(category) failure for \(path)\(status): \(detail)",
            session: session,
            recovery: .connectionQuestionable
        )
    }

    private func requestBackendRestart(session: BackendController.Session) {
        guard activeSession?.id == session.id else { return }
        guard let checkout = activeCheckout ?? selection.lastValidCheckout() else {
            chooseCheckout(nil)
            return
        }
        confirmDiscardingUnsavedChanges(discardTitle: "Discard and Restart") { [weak self] confirmed in
            guard let self else { return }
            guard confirmed else {
                self.reportedFailureSessionID = nil
                self.monitorHealth(of: session)
                return
            }
            self.load(checkout)
        }
    }

    @objc
    private func restartBackend(_ sender: Any?) {
        guard let checkout = activeCheckout ?? selection.lastValidCheckout() else {
            chooseCheckout(sender)
            return
        }
        guard let session = activeSession else {
            load(checkout)
            return
        }
        requestBackendRestart(session: session)
    }

    private func showMessage(title: String, detail: String, retryTitle: String = "Choose Another Checkout…") {
        let titleLabel = NSTextField(labelWithString: title)
        titleLabel.font = .systemFont(ofSize: 22, weight: .semibold)
        titleLabel.alignment = .center

        let detailLabel = NSTextField(wrappingLabelWithString: detail)
        detailLabel.font = .systemFont(ofSize: 13)
        detailLabel.alignment = .center
        detailLabel.maximumNumberOfLines = 12

        let retryAction = retryTitle == "Restart Backend" ? #selector(restartBackend(_:)) : #selector(chooseCheckout(_:))
        let retryButton = NSButton(title: retryTitle, target: self, action: retryAction)
        retryButton.bezelStyle = .rounded
        retryButton.keyEquivalent = "\r"

        let stack = NSStackView(views: [titleLabel, detailLabel, retryButton])
        stack.orientation = .vertical
        stack.alignment = .centerX
        stack.spacing = 16
        stack.edgeInsets = NSEdgeInsets(top: 48, left: 48, bottom: 48, right: 48)
        window?.contentView = stack
    }

    private func requestShutdown(completion: @escaping @MainActor (Bool) -> Void) {
        guard !shutdownInProgress else { return }
        shutdownInProgress = true
        startupTask?.cancel()
        healthTask?.cancel()

        confirmDiscardingUnsavedChanges(discardTitle: "Discard and Quit") { [weak self] confirmed in
            guard let self else { return }
            guard confirmed else {
                self.shutdownInProgress = false
                completion(false)
                return
            }
            Task {
                self.sessionCoordinator.deactivateSession()
                await self.backend.stop()
                self.shutdownComplete = true
                self.shutdownInProgress = false
                completion(true)
            }
        }
    }

    private func confirmDiscardingUnsavedChanges(
        discardTitle: String,
        completion: @escaping @MainActor (Bool) -> Void
    ) {
        guard window?.contentView === webView, webView.url != nil else {
            completion(true)
            return
        }

        let script = """
        (() => {
          const event = new Event('beforeunload', { cancelable: true });
          const allowed = window.dispatchEvent(event);
          return allowed && !event.defaultPrevented;
        })()
        """
        webView.evaluateJavaScript(script) { result, error in
            let canCloseWithoutPrompt = error == nil && (result as? Bool == true)
            guard !canCloseWithoutPrompt else {
                completion(true)
                return
            }

            let alert = NSAlert()
            alert.alertStyle = .warning
            alert.messageText = "Discard unsaved work?"
            alert.informativeText = "Hangboard Workbench has unsaved editor changes."
            alert.addButton(withTitle: discardTitle)
            alert.addButton(withTitle: "Cancel")
            completion(alert.runModal() == .alertFirstButtonReturn)
        }
    }
}
