import Darwin
import Foundation

struct BackendUnexpectedExit: Swift.Error, LocalizedError, Equatable, Sendable {
    let sessionID: UUID
    let status: Int32
    let stderrText: String

    var errorDescription: String? {
        let summary = "The Hangboard Workbench backend exited unexpectedly (status \(status))."
        let detail = stderrText.trimmingCharacters(in: .whitespacesAndNewlines)
        return detail.isEmpty ? summary : "\(summary)\n\n\(detail)"
    }
}

protocol BackendProcess: AnyObject, Sendable {
    var isRunning: Bool { get }
    var terminationStatus: Int32 { get }
    var stderrText: String { get }

    func run(executableURL: URL, arguments: [String]) throws
    func setTerminationHandler(_ handler: @escaping @Sendable () -> Void)
    func terminate()
    func waitUntilExit()
}

protocol BackendControlling: Sendable {
    func start(repositoryRoot: URL, port: UInt16) async throws -> URL
    func stop() async
}

actor BackendController: BackendControlling {
    struct Session: Sendable {
        let id: UUID
        let url: URL
        let runtimeIdentity: String
        let checkoutIdentity: String
        let unexpectedExits: AsyncStream<BackendUnexpectedExit>
    }

    enum Error: Swift.Error, LocalizedError, Equatable {
        case alreadyRunning
        case launchFailed(String)
        case childExited(Int32, String)
        case startupTimedOut(String)
        case couldNotSelectPort

        var errorDescription: String? {
            switch self {
            case .alreadyRunning:
                return "The Hangboard Workbench backend is already running."
            case let .launchFailed(detail):
                return Self.message("The Hangboard Workbench backend could not be launched.", detail: detail)
            case let .childExited(status, detail):
                return Self.message(
                    "The Hangboard Workbench backend exited during startup (status \(status)).",
                    detail: detail
                )
            case let .startupTimedOut(detail):
                return Self.message("The Hangboard Workbench backend did not become ready in time.", detail: detail)
            case .couldNotSelectPort:
                return "A local port could not be selected for the Hangboard Workbench backend."
            }
        }

        private static func message(_ summary: String, detail: String) -> String {
            let trimmed = detail.trimmingCharacters(in: .whitespacesAndNewlines)
            return trimmed.isEmpty ? summary : "\(summary)\n\n\(trimmed)"
        }
    }

    typealias ProcessFactory = @Sendable () -> any BackendProcess
    typealias HealthProbe = @Sendable (URL) async throws -> Bool
    typealias Sleep = @Sendable (Duration) async throws -> Void
    typealias PortSelector = @Sendable () throws -> UInt16

    private let executableURL: URL
    private let processFactory: ProcessFactory
    private let healthProbe: HealthProbe
    private let sleep: Sleep
    private let portSelector: PortSelector
    private let startupTimeout: Duration
    private let pollingInterval: Duration
    private let runtimeIdentity: String

    private final class Child: @unchecked Sendable {
        let id = UUID()
        let process: any BackendProcess
        let unexpectedExits: AsyncStream<BackendUnexpectedExit>
        let exitContinuation: AsyncStream<BackendUnexpectedExit>.Continuation
        var cleanup: Task<String, Never>?
        var didStart = false
        var expectsTermination = false

        init(process: any BackendProcess) {
            self.process = process
            let exits = AsyncStream<BackendUnexpectedExit>.makeStream()
            unexpectedExits = exits.stream
            exitContinuation = exits.continuation
        }
    }

    private var child: Child?

    init(
        executableURL: URL? = nil,
        processFactory: @escaping ProcessFactory = { FoundationBackendProcess() },
        healthProbe: @escaping HealthProbe = { url in try await BackendController.probeHealth(url) },
        sleep: @escaping Sleep = { duration in try await Task.sleep(for: duration) },
        portSelector: @escaping PortSelector = { try BackendController.selectLoopbackPort() },
        startupTimeout: Duration = .seconds(10),
        pollingInterval: Duration = .milliseconds(100)
    ) {
        let resourceRoot = Bundle.main.resourceURL ?? Bundle.main.bundleURL
        self.executableURL = executableURL
            ?? resourceRoot.appending(path: "workbench-runtime/hangboard-workbench")
        self.processFactory = processFactory
        self.healthProbe = healthProbe
        self.sleep = sleep
        self.portSelector = portSelector
        self.startupTimeout = startupTimeout
        self.pollingInterval = pollingInterval
        self.runtimeIdentity = Self.readRuntimeIdentity(beside: self.executableURL)
    }

    func start(repositoryRoot: URL, port requestedPort: UInt16 = 0) async throws -> URL {
        let session = try await startSession(repositoryRoot: repositoryRoot, port: requestedPort)
        do {
            try Task.checkCancellation()
        } catch {
            await stop(session: session)
            throw error
        }
        return session.url
    }

    func startSession(repositoryRoot: URL, port requestedPort: UInt16 = 0) async throws -> Session {
        try Task.checkCancellation()
        guard child == nil else {
            throw Error.alreadyRunning
        }

        let root = try CheckoutSelection.validatedURL(repositoryRoot)
        let checkoutIdentity = Self.readCheckoutIdentity(at: root)
        let port = requestedPort == 0 ? try portSelector() : requestedPort
        let editorURL = try Self.editorURL(port: port)
        let healthURL = editorURL.appending(path: "api/health")
        let arguments = [
            "--repository-root", root.path,
            "--host", "127.0.0.1",
            "--port", String(port),
            "--no-open",
        ]

        try Task.checkCancellation()
        let process = processFactory()
        let launchedChild = Child(process: process)
        let launchedChildID = launchedChild.id
        process.setTerminationHandler { [weak self] in
            Task {
                await self?.processDidTerminate(childID: launchedChildID)
            }
        }
        do {
            try process.run(executableURL: executableURL, arguments: arguments)
        } catch {
            launchedChild.exitContinuation.finish()
            throw Error.launchFailed(error.localizedDescription)
        }
        child = launchedChild

        let clock = ContinuousClock()
        let deadline = clock.now.advanced(by: startupTimeout)
        while true {
            try await requireCurrent(launchedChild)

            guard process.isRunning else {
                let status = process.terminationStatus
                let stderr = await removeAndStop(launchedChild)
                throw Error.childExited(status, stderr)
            }

            let isHealthy = (try? await healthProbe(healthURL)) == true
            try await requireCurrent(launchedChild)
            if isHealthy {
                launchedChild.didStart = true
                return Session(
                    id: launchedChild.id,
                    url: editorURL,
                    runtimeIdentity: runtimeIdentity,
                    checkoutIdentity: checkoutIdentity,
                    unexpectedExits: launchedChild.unexpectedExits
                )
            }

            if clock.now >= deadline {
                let stderr = await removeAndStop(launchedChild)
                throw Error.startupTimedOut(stderr)
            }

            do {
                try await sleep(pollingInterval)
            } catch {
                _ = await removeAndStop(launchedChild)
                throw error
            }
        }
    }

    func stop() async {
        guard let child else {
            return
        }
        _ = await removeAndStop(child)
    }

    func stop(session: Session) async {
        guard let child, child.id == session.id else {
            return
        }
        _ = await removeAndStop(child)
    }

    private func requireCurrent(_ launchedChild: Child) async throws {
        do {
            try Task.checkCancellation()
        } catch {
            _ = await removeAndStop(launchedChild)
            throw error
        }
        guard child === launchedChild else {
            throw CancellationError()
        }
    }

    private func removeAndStop(_ launchedChild: Child) async -> String {
        launchedChild.expectsTermination = true
        launchedChild.exitContinuation.finish()
        if child === launchedChild {
            child = nil
        }
        let process = launchedChild.process
        if process.isRunning {
            process.terminate()
        }
        return await collectExit(from: launchedChild)
    }

    private func processDidTerminate(childID: UUID) async {
        guard let exitedChild = child,
              exitedChild.id == childID,
              exitedChild.didStart,
              !exitedChild.expectsTermination else {
            return
        }

        child = nil
        let status = exitedChild.process.terminationStatus
        let stderr = await collectExit(from: exitedChild)
        exitedChild.exitContinuation.yield(
            BackendUnexpectedExit(
                sessionID: exitedChild.id,
                status: status,
                stderrText: stderr
            )
        )
        exitedChild.exitContinuation.finish()
    }

    private func collectExit(from launchedChild: Child) async -> String {
        if let cleanup = launchedChild.cleanup {
            return await cleanup.value
        }

        let process = launchedChild.process
        let cleanup = Task.detached(priority: .utility) {
            process.waitUntilExit()
            return process.stderrText
        }
        launchedChild.cleanup = cleanup
        return await cleanup.value
    }

    private static func editorURL(port: UInt16) throws -> URL {
        guard let url = URL(string: "http://127.0.0.1:\(port)/") else {
            throw Error.couldNotSelectPort
        }
        return url
    }

    private static func readRuntimeIdentity(beside executableURL: URL) -> String {
        let directory = executableURL.deletingLastPathComponent()
        let candidates = [
            directory.appending(path: "build-commit.txt"),
            directory.appending(path: "_internal/build-commit.txt"),
        ]
        for candidate in candidates {
            if let value = try? String(contentsOf: candidate, encoding: .ascii)
                .trimmingCharacters(in: .whitespacesAndNewlines),
               value.range(of: "^[0-9a-f]{40}$", options: .regularExpression) != nil {
                return value
            }
        }
        return "unknown"
    }

    static func readCheckoutIdentity(at repositoryRoot: URL) -> String {
        guard let gitDirectories = gitDirectories(at: repositoryRoot), let git = gitDirectories.first,
              let head = readSmallASCII(git.appending(path: "HEAD")) else { return "unknown" }
        if isCommitIdentity(head) { return head }
        guard head.hasPrefix("ref: ") else { return "unknown" }
        let reference = String(head.dropFirst(5))
        guard isSafeReference(reference) else { return "unknown" }
        for directory in gitDirectories {
            if let value = readSmallASCII(directory.appending(path: reference)), isCommitIdentity(value) {
                return value
            }
        }
        for directory in gitDirectories {
            guard let packed = readSmallASCII(directory.appending(path: "packed-refs"), trimming: false) else { continue }
            for line in packed.split(whereSeparator: \.isNewline) {
                let fields = line.split(separator: " ", maxSplits: 1).map(String.init)
                if fields.count == 2, fields[1] == reference, isCommitIdentity(fields[0]) { return fields[0] }
            }
        }
        return "unknown"
    }

    private static func gitDirectories(at repositoryRoot: URL) -> [URL]? {
        let dotGit = repositoryRoot.appending(path: ".git")
        var isDirectory: ObjCBool = false
        guard FileManager.default.fileExists(atPath: dotGit.path, isDirectory: &isDirectory) else { return nil }
        if isDirectory.boolValue { return [dotGit.standardizedFileURL] }

        guard let pointer = readSmallASCII(dotGit), pointer.hasPrefix("gitdir: ") else { return nil }
        let rawPath = String(pointer.dropFirst(8))
        guard !rawPath.isEmpty, !rawPath.contains("\0") else { return nil }
        let worktreeGit = URL(fileURLWithPath: rawPath, relativeTo: repositoryRoot).standardizedFileURL
        var directories = [worktreeGit]
        if let commonPath = readSmallASCII(worktreeGit.appending(path: "commondir")),
           !commonPath.isEmpty, !commonPath.contains("\0") {
            directories.append(
                URL(fileURLWithPath: commonPath, relativeTo: worktreeGit).standardizedFileURL
            )
        }
        return directories
    }

    private static func readSmallASCII(_ url: URL, trimming: Bool = true) -> String? {
        guard let handle = try? FileHandle(forReadingFrom: url) else { return nil }
        defer { try? handle.close() }
        guard let data = try? handle.read(upToCount: 65_537), data.count <= 65_536,
              var value = String(data: data, encoding: .ascii) else { return nil }
        if trimming { value = value.trimmingCharacters(in: .whitespacesAndNewlines) }
        return value
    }

    private static func isSafeReference(_ reference: String) -> Bool {
        guard reference.hasPrefix("refs/"), reference.count <= 1024,
              !reference.contains("\\"), !reference.contains("//") else { return false }
        return reference.split(separator: "/", omittingEmptySubsequences: false).allSatisfy {
            !$0.isEmpty && $0 != "." && $0 != ".."
        }
    }

    private static func isCommitIdentity(_ value: String) -> Bool {
        value.range(of: "^[0-9a-f]{40}$", options: .regularExpression) != nil
    }

    private static func probeHealth(_ url: URL) async throws -> Bool {
        var request = URLRequest(url: url)
        request.timeoutInterval = 1
        let (data, response) = try await URLSession.shared.data(for: request)
        guard let response = response as? HTTPURLResponse,
              response.statusCode == 200,
              let payload = try JSONSerialization.jsonObject(with: data) as? [String: Any] else {
            return false
        }
        return payload["ok"] as? Bool == true
    }

    private static func selectLoopbackPort() throws -> UInt16 {
        let descriptor = socket(AF_INET, SOCK_STREAM, 0)
        guard descriptor >= 0 else {
            throw Error.couldNotSelectPort
        }
        defer { close(descriptor) }

        var address = sockaddr_in()
        address.sin_len = UInt8(MemoryLayout<sockaddr_in>.size)
        address.sin_family = sa_family_t(AF_INET)
        address.sin_port = in_port_t(0).bigEndian
        address.sin_addr = in_addr(s_addr: inet_addr("127.0.0.1"))

        let didBind = withUnsafePointer(to: &address) { pointer in
            pointer.withMemoryRebound(to: sockaddr.self, capacity: 1) { socketAddress in
                Darwin.bind(descriptor, socketAddress, socklen_t(MemoryLayout<sockaddr_in>.size))
            }
        }
        guard didBind == 0 else {
            throw Error.couldNotSelectPort
        }

        var boundAddress = sockaddr_in()
        var boundAddressLength = socklen_t(MemoryLayout<sockaddr_in>.size)
        let didRead = withUnsafeMutablePointer(to: &boundAddress) { pointer in
            pointer.withMemoryRebound(to: sockaddr.self, capacity: 1) { socketAddress in
                getsockname(descriptor, socketAddress, &boundAddressLength)
            }
        }
        guard didRead == 0 else {
            throw Error.couldNotSelectPort
        }
        return UInt16(bigEndian: boundAddress.sin_port)
    }
}

private final class FoundationBackendProcess: BackendProcess, @unchecked Sendable {
    private let process = Process()
    private let standardErrorPipe = Pipe()

    var isRunning: Bool { process.isRunning }
    var terminationStatus: Int32 { process.terminationStatus }

    var stderrText: String {
        let data = standardErrorPipe.fileHandleForReading.readDataToEndOfFile()
        return String(data: data, encoding: .utf8) ?? ""
    }

    func run(executableURL: URL, arguments: [String]) throws {
        process.executableURL = executableURL
        process.arguments = arguments
        process.standardError = standardErrorPipe
        try process.run()
    }

    func setTerminationHandler(_ handler: @escaping @Sendable () -> Void) {
        process.terminationHandler = { _ in handler() }
    }

    func terminate() {
        process.terminate()
    }

    func waitUntilExit() {
        process.waitUntilExit()
    }
}
