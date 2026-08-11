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
private final class WorkbenchAppDelegate: NSObject, NSApplicationDelegate, NSWindowDelegate {
    private let backend = BackendController()
    private let selection = CheckoutSelection()
    private let webView = WKWebView(frame: .zero)

    private var window: NSWindow?
    private var startupTask: Task<Void, Never>?
    private var shutdownInProgress = false
    private var shutdownComplete = false
    private var allowWindowClose = false

    func applicationDidFinishLaunching(_ notification: Notification) {
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
            load(try CheckoutSelection.validatedURL(url))
        } catch {
            showMessage(title: "That Folder Is Not a Hang Ten Checkout", detail: error.localizedDescription)
        }
    }

    private func load(_ checkout: URL) {
        startupTask?.cancel()
        startupTask = Task { [weak self] in
            guard let self else { return }
            await self.backend.stop()
            guard !Task.isCancelled else { return }
            do {
                let session = try await self.backend.startSession(repositoryRoot: checkout)
                guard !Task.isCancelled else {
                    await self.backend.stop(session: session)
                    return
                }
                self.selection.remember(checkout)
                self.showWebView(session.url)
            } catch is CancellationError {
                // A replacement checkout or app shutdown owns cleanup.
            } catch {
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

    private func showMessage(title: String, detail: String, retryTitle: String = "Choose Another Checkout…") {
        let titleLabel = NSTextField(labelWithString: title)
        titleLabel.font = .systemFont(ofSize: 22, weight: .semibold)
        titleLabel.alignment = .center

        let detailLabel = NSTextField(wrappingLabelWithString: detail)
        detailLabel.font = .systemFont(ofSize: 13)
        detailLabel.alignment = .center
        detailLabel.maximumNumberOfLines = 12

        let retryButton = NSButton(title: retryTitle, target: self, action: #selector(chooseCheckout(_:)))
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

        confirmDiscardingUnsavedChanges { [weak self] confirmed in
            guard let self else { return }
            guard confirmed else {
                self.shutdownInProgress = false
                completion(false)
                return
            }
            Task {
                await self.backend.stop()
                self.shutdownComplete = true
                self.shutdownInProgress = false
                completion(true)
            }
        }
    }

    private func confirmDiscardingUnsavedChanges(completion: @escaping @MainActor (Bool) -> Void) {
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
            alert.addButton(withTitle: "Discard and Quit")
            alert.addButton(withTitle: "Cancel")
            completion(alert.runModal() == .alertFirstButtonReturn)
        }
    }
}
