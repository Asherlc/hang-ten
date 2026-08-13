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

    func testSessionReportsPackagedRuntimeBuildIdentity() async throws {
        let runtime = FileManager.default.temporaryDirectory
            .appending(path: "BackendControllerTests-runtime-\(UUID().uuidString)", directoryHint: .isDirectory)
        temporaryDirectories.append(runtime)
        try FileManager.default.createDirectory(
            at: runtime.appending(path: "_internal", directoryHint: .isDirectory),
            withIntermediateDirectories: true
        )
        let commit = String(repeating: "a", count: 40)
        try (commit + "\n").write(
            to: runtime.appending(path: "_internal/build-commit.txt"),
            atomically: true,
            encoding: .ascii
        )
        let process = FakeBackendProcess()
        let controller = BackendController(
            executableURL: runtime.appending(path: "hangboard-workbench"),
            processFactory: { process },
            healthProbe: { _ in true },
            sleep: { _ in },
            portSelector: { 4317 }
        )

        let session = try await controller.startSession(repositoryRoot: try makeCheckout())

        XCTAssertEqual(session.runtimeIdentity, commit)
        await controller.stop()
    }

    func testCheckoutIdentityReadsSymbolicAndDetachedHeadsWithoutRunningGit() throws {
        let checkout = try makeCheckout()
        let git = checkout.appending(path: ".git", directoryHint: .isDirectory)
        let commit = String(repeating: "b", count: 40)
        try FileManager.default.createDirectory(
            at: git.appending(path: "refs/heads", directoryHint: .isDirectory),
            withIntermediateDirectories: true
        )
        try "ref: refs/heads/main\n".write(to: git.appending(path: "HEAD"), atomically: true, encoding: .ascii)
        try "\(commit)\n".write(to: git.appending(path: "refs/heads/main"), atomically: true, encoding: .ascii)
        XCTAssertEqual(BackendController.readCheckoutIdentity(at: checkout), commit)

        let detached = String(repeating: "c", count: 40)
        try detached.write(to: git.appending(path: "HEAD"), atomically: true, encoding: .ascii)
        XCTAssertEqual(BackendController.readCheckoutIdentity(at: checkout), detached)
    }

    func testCheckoutIdentityRejectsUnsafeOrMalformedHeadReferences() throws {
        let checkout = try makeCheckout()
        let head = checkout.appending(path: ".git/HEAD")
        try "ref: ../../outside\n".write(to: head, atomically: true, encoding: .ascii)
        XCTAssertEqual(BackendController.readCheckoutIdentity(at: checkout), "unknown")
        try "not-a-commit\n".write(to: head, atomically: true, encoding: .ascii)
        XCTAssertEqual(BackendController.readCheckoutIdentity(at: checkout), "unknown")
    }

    func testCheckoutIdentityReadsLinkedWorktreeGitFileAndCommonRefs() throws {
        let checkout = try makeCheckout()
        let metadata = FileManager.default.temporaryDirectory
            .appending(path: "BackendControllerTests-worktree-\(UUID().uuidString)", directoryHint: .isDirectory)
        temporaryDirectories.append(metadata)
        let worktreeGit = metadata.appending(path: "worktrees/test", directoryHint: .isDirectory)
        try FileManager.default.createDirectory(at: worktreeGit, withIntermediateDirectories: true)
        try FileManager.default.removeItem(at: checkout.appending(path: ".git"))
        try "gitdir: \(worktreeGit.path)\n".write(to: checkout.appending(path: ".git"), atomically: true, encoding: .ascii)
        try "../..\n".write(to: worktreeGit.appending(path: "commondir"), atomically: true, encoding: .ascii)
        try "ref: refs/heads/worktree\n".write(to: worktreeGit.appending(path: "HEAD"), atomically: true, encoding: .ascii)
        try FileManager.default.createDirectory(at: metadata.appending(path: "refs/heads"), withIntermediateDirectories: true)
        let commit = String(repeating: "d", count: 40)
        try commit.write(to: metadata.appending(path: "refs/heads/worktree"), atomically: true, encoding: .ascii)

        XCTAssertEqual(BackendController.readCheckoutIdentity(at: checkout), commit)
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

    func testUnexpectedPostStartExitIsDeliveredWithItsSessionGeneration() async throws {
        let process = FakeBackendProcess()
        let controller = BackendController(
            executableURL: URL(fileURLWithPath: "/private/tmp/hangboard-workbench"),
            processFactory: { process },
            healthProbe: { _ in true },
            sleep: { _ in },
            portSelector: { 4317 }
        )
        let session = try await controller.startSession(repositoryRoot: try makeCheckout())
        let exitTask = Task { await firstExit(in: session.unexpectedExits) }

        process.exitUnexpectedly(status: 17, stderr: "backend crashed")

        let receivedExit = await exitTask.value
        let exit = try XCTUnwrap(receivedExit)
        XCTAssertEqual(exit.sessionID, session.id)
        XCTAssertEqual(exit.status, 17)
        XCTAssertEqual(exit.stderrText, "backend crashed")
        XCTAssertTrue(exit.localizedDescription.contains("exited unexpectedly"))
        XCTAssertTrue(exit.localizedDescription.contains("backend crashed"))
    }

    func testIntentionalStopFinishesSessionWithoutUnexpectedExit() async throws {
        let process = FakeBackendProcess()
        let controller = BackendController(
            executableURL: URL(fileURLWithPath: "/private/tmp/hangboard-workbench"),
            processFactory: { process },
            healthProbe: { _ in true },
            sleep: { _ in },
            portSelector: { 4317 }
        )
        let session = try await controller.startSession(repositoryRoot: try makeCheckout())
        let exitTask = Task { await firstExit(in: session.unexpectedExits) }

        await controller.stop(session: session)

        let receivedExit = await exitTask.value
        XCTAssertNil(receivedExit)
    }

    @MainActor
    func testCheckoutReplacementCancellationPreservesTheActiveSessionSurfaceAndSelection() {
        let coordinator = WorkbenchSessionCoordinator()
        var events: [String] = []
        var backendGeneration = "active-backend"
        var webViewLocation = "http://127.0.0.1:4317/"
        var rememberedCheckout = "/checkouts/active"

        coordinator.requestCheckoutReplacement(
            confirmDiscarding: { completion in
                events.append("confirm")
                completion(false)
            },
            performReplacement: {
                events.append("stop")
                backendGeneration = "replacement-backend"
                webViewLocation = "http://127.0.0.1:4318/"
                rememberedCheckout = "/checkouts/replacement"
            }
        )

        XCTAssertEqual(events, ["confirm"])
        XCTAssertEqual(backendGeneration, "active-backend")
        XCTAssertEqual(webViewLocation, "http://127.0.0.1:4317/")
        XCTAssertEqual(rememberedCheckout, "/checkouts/active")
    }

    @MainActor
    func testCheckoutReplacementConfirmationPrecedesBackendReplacement() {
        let coordinator = WorkbenchSessionCoordinator()
        var events: [String] = []

        coordinator.requestCheckoutReplacement(
            confirmDiscarding: { completion in
                events.append("confirm")
                completion(true)
            },
            performReplacement: {
                events.append("stop-and-replace")
            }
        )

        XCTAssertEqual(events, ["confirm", "stop-and-replace"])
    }

    @MainActor
    func testStaleBackendExitCannotOverwriteTheActiveSessionErrorSurface() {
        let coordinator = WorkbenchSessionCoordinator()
        let staleSessionID = UUID()
        let activeSessionID = UUID()
        var displayedStatuses: [Int32] = []

        coordinator.activateSession(id: activeSessionID) { exit in
            displayedStatuses.append(exit.status)
        }
        coordinator.receiveUnexpectedExit(
            BackendUnexpectedExit(
                sessionID: staleSessionID,
                status: 11,
                stderrText: "stale crash"
            )
        )
        coordinator.receiveUnexpectedExit(
            BackendUnexpectedExit(
                sessionID: activeSessionID,
                status: 12,
                stderrText: "active crash"
            )
        )

        XCTAssertEqual(displayedStatuses, [12])
        XCTAssertNil(coordinator.activeSessionID)
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

    func testCancelledStartCannotStopReplacementInstalledWhileItsProbeIsSuspended() async throws {
        let processA = FakeBackendProcess()
        let processB = FakeBackendProcess()
        let processes = LockedBox<[FakeBackendProcess]>([processA, processB])
        let probeA = ControlledHealthProbe()
        let didReturnA = LockedBox(false)
        let controller = BackendController(
            executableURL: URL(fileURLWithPath: "/private/tmp/hangboard-workbench"),
            processFactory: { processes.withValue { $0.removeFirst() } },
            healthProbe: { url in
                if url.port == 4317 {
                    return await probeA.waitForSuccessIgnoringCancellation()
                }
                return true
            },
            sleep: { _ in },
            portSelector: { 4317 }
        )
        let rootA = try makeCheckout()
        let rootB = try makeCheckout()
        let startA = Task {
            let session = try await controller.startSession(repositoryRoot: rootA, port: 4317)
            didReturnA.withValue { $0 = true }
            guard !Task.isCancelled else {
                await controller.stop(session: session)
                throw CancellationError()
            }
            return session.url
        }

        await probeA.waitUntilSuspended()
        startA.cancel()
        await controller.stop()
        let urlB = try await controller.start(repositoryRoot: rootB, port: 4318)
        await probeA.succeed()

        do {
            _ = try await startA.value
            XCTFail("Expected checkout A startup to remain cancelled")
        } catch is CancellationError {
            // Expected.
        }
        XCTAssertFalse(didReturnA.value, "Checkout A returned success after cancellation and replacement")
        XCTAssertEqual(processA.terminateCount, 1)
        XCTAssertEqual(processA.waitCount, 1, "Checkout A cleanup ran more than once")
        XCTAssertEqual(urlB.absoluteString, "http://127.0.0.1:4318/")
        XCTAssertTrue(processB.isRunning, "Checkout A cleanup terminated checkout B")
        XCTAssertEqual(processB.terminateCount, 0)

        await controller.stop()
        XCTAssertFalse(processB.isRunning)
        XCTAssertEqual(processB.terminateCount, 1, "Checkout B was not the active backend")
        XCTAssertEqual(processB.waitCount, 1)
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
            at: root.appending(path: "Tools/HangboardPipeline/src/hangboard_vectorizer"),
            withIntermediateDirectories: true
        )
        try FileManager.default.createDirectory(
            at: root.appending(path: "Hangboards"),
            withIntermediateDirectories: true
        )
        try FileManager.default.createDirectory(
            at: root.appending(path: "Tools/HangboardWorkbench"),
            withIntermediateDirectories: true
        )
        try Data().write(to: root.appending(path: "Tools/HangboardWorkbench/server.py"))
        return root
    }

    private func firstExit(
        in exits: AsyncStream<BackendUnexpectedExit>
    ) async -> BackendUnexpectedExit? {
        for await exit in exits {
            return exit
        }
        return nil
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
    var terminationHandler: (@Sendable () -> Void)?

    func run(executableURL: URL, arguments: [String]) throws {
        self.executableURL = executableURL
        self.arguments = arguments
        runCount += 1
        isRunning = true
    }

    func terminate() {
        terminateCount += 1
        isRunning = false
        terminationHandler?()
    }

    func waitUntilExit() {
        waitCount += 1
        isRunning = false
    }

    func setTerminationHandler(_ handler: @escaping @Sendable () -> Void) {
        terminationHandler = handler
    }

    func exitUnexpectedly(status: Int32, stderr: String) {
        terminationStatus = status
        stderrText = stderr
        isRunning = false
        terminationHandler?()
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

private actor ControlledHealthProbe {
    private var isSuspended = false
    private var suspensionWaiters: [CheckedContinuation<Void, Never>] = []
    private var resultContinuation: CheckedContinuation<Bool, Never>?

    func waitForSuccessIgnoringCancellation() async -> Bool {
        isSuspended = true
        let waiters = suspensionWaiters
        suspensionWaiters.removeAll()
        for waiter in waiters {
            waiter.resume()
        }
        return await withCheckedContinuation { continuation in
            resultContinuation = continuation
        }
    }

    func waitUntilSuspended() async {
        guard !isSuspended else { return }
        await withCheckedContinuation { continuation in
            suspensionWaiters.append(continuation)
        }
    }

    func succeed() {
        resultContinuation?.resume(returning: true)
        resultContinuation = nil
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
