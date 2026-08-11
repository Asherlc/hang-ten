import Darwin
import Foundation

protocol BackendProcess: AnyObject, Sendable {
    var isRunning: Bool { get }
    var terminationStatus: Int32 { get }
    var stderrText: String { get }

    func run(executableURL: URL, arguments: [String]) throws
    func terminate()
    func waitUntilExit()
}

protocol BackendControlling: Sendable {
    func start(repositoryRoot: URL, port: UInt16) async throws -> URL
    func stop() async
}

actor BackendController: BackendControlling {
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

    private var child: (any BackendProcess)?

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
    }

    func start(repositoryRoot: URL, port requestedPort: UInt16 = 0) async throws -> URL {
        try Task.checkCancellation()
        guard child == nil else {
            throw Error.alreadyRunning
        }

        let root = try CheckoutSelection.validatedURL(repositoryRoot)
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
        do {
            try process.run(executableURL: executableURL, arguments: arguments)
        } catch {
            throw Error.launchFailed(error.localizedDescription)
        }
        child = process

        let clock = ContinuousClock()
        let deadline = clock.now.advanced(by: startupTimeout)
        while true {
            do {
                try Task.checkCancellation()
            } catch {
                _ = await removeAndStop(process)
                throw error
            }

            guard process.isRunning else {
                await waitForExit(process)
                child = nil
                throw Error.childExited(process.terminationStatus, process.stderrText)
            }

            if (try? await healthProbe(healthURL)) == true {
                return editorURL
            }

            if clock.now >= deadline {
                let stderr = await removeAndStop(process)
                throw Error.startupTimedOut(stderr)
            }

            do {
                try await sleep(pollingInterval)
            } catch {
                _ = await removeAndStop(process)
                throw error
            }
        }
    }

    func stop() async {
        guard let process = child else {
            return
        }
        _ = await removeAndStop(process)
    }

    private func removeAndStop(_ process: any BackendProcess) async -> String {
        if child === process {
            child = nil
        }
        if process.isRunning {
            process.terminate()
        }
        await waitForExit(process)
        return process.stderrText
    }

    private func waitForExit(_ process: any BackendProcess) async {
        await Task.detached(priority: .utility) {
            process.waitUntilExit()
        }.value
    }

    private static func editorURL(port: UInt16) throws -> URL {
        guard let url = URL(string: "http://127.0.0.1:\(port)/") else {
            throw Error.couldNotSelectPort
        }
        return url
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

    func terminate() {
        process.terminate()
    }

    func waitUntilExit() {
        process.waitUntilExit()
    }
}
