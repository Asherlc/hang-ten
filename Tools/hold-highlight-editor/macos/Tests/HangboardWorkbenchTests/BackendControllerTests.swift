import Foundation
import XCTest
@testable import HangboardWorkbench

final class BackendControllerTests: XCTestCase {
    private var temporaryDirectories: [URL] = []

    override func tearDown() {
        for directory in temporaryDirectories {
            try? FileManager.default.removeItem(at: directory)
        }
        super.tearDown()
    }

    func testStartPassesOnlyLoopbackBackendArgumentsAndPollsHealth() async throws {
        let process = FakeBackendProcess()
        let probedURLs = LockedBox<[URL]>([])
        let root = try makeCheckout()
        let controller = BackendController(
            executableURL: URL(fileURLWithPath: "/private/tmp/workbench-runtime/hangboard-workbench"),
            processFactory: { process },
            healthProbe: { url in
                probedURLs.withValue {
                    $0.append(url)
                    return $0.count >= 2
                }
            },
            sleep: { _ in },
            portSelector: { 4317 }
        )

        let url = try await controller.start(repositoryRoot: root, port: 0)

        XCTAssertEqual(url.absoluteString, "http://127.0.0.1:4317/")
        XCTAssertEqual(process.executableURL?.path, "/private/tmp/workbench-runtime/hangboard-workbench")
        XCTAssertEqual(
            process.arguments,
            [
                "--repository-root", root.resolvingSymlinksInPath().path,
                "--host", "127.0.0.1",
                "--port", "4317",
                "--no-open",
            ]
        )
        XCTAssertEqual(
            probedURLs.value.map(\.absoluteString),
            ["http://127.0.0.1:4317/api/health", "http://127.0.0.1:4317/api/health"]
        )
    }

    func testStartTimesOutAndCleansUpItsChild() async throws {
        let process = FakeBackendProcess()
        process.stderrText = "backend startup detail"
        let controller = BackendController(
            executableURL: URL(fileURLWithPath: "/private/tmp/hangboard-workbench"),
            processFactory: { process },
            healthProbe: { _ in false },
            sleep: { _ in },
            portSelector: { 4317 },
            startupTimeout: .zero
        )

        do {
            _ = try await controller.start(repositoryRoot: try makeCheckout())
            XCTFail("Expected startup timeout")
        } catch let error as BackendController.Error {
            guard case .startupTimedOut("backend startup detail") = error else {
                return XCTFail("Expected startupTimedOut, got \(error)")
            }
        }
        XCTAssertEqual(process.terminateCount, 1)
        XCTAssertEqual(process.waitCount, 1)
    }

    func testStopTerminatesAndWaitsForTheExactChildOnce() async throws {
        let process = FakeBackendProcess()
        let controller = BackendController(
            executableURL: URL(fileURLWithPath: "/private/tmp/hangboard-workbench"),
            processFactory: { process },
            healthProbe: { _ in true },
            sleep: { _ in },
            portSelector: { 4317 }
        )
        _ = try await controller.start(repositoryRoot: try makeCheckout())

        await controller.stop()
        await controller.stop()

        XCTAssertEqual(process.terminateCount, 1)
        XCTAssertEqual(process.waitCount, 1)
    }

    func testCancelledStartDoesNotCreateOrLaunchAProcess() async throws {
        let process = FakeBackendProcess()
        let factoryCount = LockedBox(0)
        let controller = BackendController(
            executableURL: URL(fileURLWithPath: "/private/tmp/hangboard-workbench"),
            processFactory: {
                factoryCount.withValue { $0 += 1 }
                return process
            },
            healthProbe: { _ in true },
            sleep: { _ in },
            portSelector: { 4317 }
        )
        let root = try makeCheckout()
        let task = Task {
            withUnsafeCurrentTask { $0?.cancel() }
            return try await controller.start(repositoryRoot: root)
        }

        do {
            _ = try await task.value
            XCTFail("Expected cancellation")
        } catch is CancellationError {
            // Expected.
        }
        XCTAssertEqual(factoryCount.value, 0)
        XCTAssertEqual(process.runCount, 0)
    }

    func testCancellationWhilePollingStopsTheLaunchedChild() async throws {
        let process = FakeBackendProcess()
        let controller = BackendController(
            executableURL: URL(fileURLWithPath: "/private/tmp/hangboard-workbench"),
            processFactory: { process },
            healthProbe: { _ in false },
            sleep: { _ in throw CancellationError() },
            portSelector: { 4317 }
        )

        do {
            _ = try await controller.start(repositoryRoot: try makeCheckout())
            XCTFail("Expected cancellation")
        } catch is CancellationError {
            // Expected.
        }
        XCTAssertEqual(process.runCount, 1)
        XCTAssertEqual(process.terminateCount, 1)
        XCTAssertEqual(process.waitCount, 1)
    }

    func testHeadlessArgumentsRequireRepositoryRootAndPort() throws {
        let configuration = try XCTUnwrap(
            HeadlessConfiguration.parse([
                "--headless", "--repository-root", "/tmp/hang-ten", "--port", "4317",
            ])
        )

        XCTAssertEqual(configuration.repositoryRoot.path, "/tmp/hang-ten")
        XCTAssertEqual(configuration.port, 4317)
        XCTAssertThrowsError(try HeadlessConfiguration.parse(["--headless", "--repository-root", "/tmp/hang-ten"]))
        XCTAssertNil(try HeadlessConfiguration.parse([]))
    }

    func testHeadlessRunnerStartsWaitsForTerminationThenStops() async throws {
        let backend = FakeBackendController()
        let configuration = HeadlessConfiguration(
            repositoryRoot: URL(fileURLWithPath: "/tmp/hang-ten"),
            port: 4317
        )

        try await HeadlessRunner.run(configuration: configuration, backend: backend) {
            await backend.recordTerminationWait()
        }

        let events = await backend.events
        XCTAssertEqual(events, ["start:/tmp/hang-ten:4317", "wait", "stop"])
    }

    private func makeCheckout() throws -> URL {
        let root = FileManager.default.temporaryDirectory
            .appending(path: "BackendControllerTests-\(UUID().uuidString)", directoryHint: .isDirectory)
        temporaryDirectories.append(root)
        try FileManager.default.createDirectory(at: root.appending(path: ".git"), withIntermediateDirectories: true)
        try FileManager.default.createDirectory(
            at: root.appending(path: "Tools/HangboardOnboarding/boards"),
            withIntermediateDirectories: true
        )
        try FileManager.default.createDirectory(
            at: root.appending(path: "Tools/hold-highlight-editor"),
            withIntermediateDirectories: true
        )
        return root
    }

}

private final class FakeBackendProcess: BackendProcess, @unchecked Sendable {
    var executableURL: URL?
    var arguments: [String] = []
    var isRunning = false
    var terminationStatus: Int32 = 0
    var stderrText = ""
    var runCount = 0
    var terminateCount = 0
    var waitCount = 0

    func run(executableURL: URL, arguments: [String]) throws {
        self.executableURL = executableURL
        self.arguments = arguments
        runCount += 1
        isRunning = true
    }

    func terminate() {
        terminateCount += 1
        isRunning = false
    }

    func waitUntilExit() {
        waitCount += 1
        isRunning = false
    }
}

private actor FakeBackendController: BackendControlling {
    var events: [String] = []

    func start(repositoryRoot: URL, port: UInt16) async throws -> URL {
        events.append("start:\(repositoryRoot.path):\(port)")
        return URL(string: "http://127.0.0.1:\(port)/")!
    }

    func stop() async {
        events.append("stop")
    }

    func recordTerminationWait() {
        events.append("wait")
    }
}

private final class LockedBox<Value>: @unchecked Sendable {
    private let lock = NSLock()
    private var storage: Value

    init(_ value: Value) {
        storage = value
    }

    var value: Value {
        lock.withLock { storage }
    }

    func withValue<Result>(_ operation: (inout Value) -> Result) -> Result {
        lock.withLock { operation(&storage) }
    }
}
