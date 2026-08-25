import XCTest
@testable import HangTen

final class GitHubBoardSyncServiceTests: XCTestCase {

    private static let token = "token-secret-123"

    final class StubState {
        static let lock = NSLock()
        static var handler: ((URLRequest) throws -> (HTTPURLResponse, Data))?
        static var requests: [URLRequest] = []

        static func reset() {
            lock.lock()
            defer { lock.unlock() }
            handler = nil
            requests = []
        }

        static func record(_ request: URLRequest) {
            lock.lock()
            defer { lock.unlock() }
            requests.append(request)
        }

        static func respond(to request: URLRequest) throws -> (HTTPURLResponse, Data) {
            lock.lock()
            let currentHandler = handler
            lock.unlock()
            guard let currentHandler else {
                throw URLError(.badServerResponse)
            }
            return try currentHandler(request)
        }
    }

    final class StubURLProtocol: URLProtocol {
        override class func canInit(with request: URLRequest) -> Bool { true }
        override class func canonicalRequest(for request: URLRequest) -> URLRequest { request }

        override func startLoading() {
            StubState.record(request)
            do {
                let (response, data) = try StubState.respond(to: request)
                client?.urlProtocol(self, didReceive: response, cacheStoragePolicy: .notAllowed)
                client?.urlProtocol(self, didLoad: data)
                client?.urlProtocolDidFinishLoading(self)
            } catch {
                client?.urlProtocol(self, didFailWithError: error)
            }
        }

        override func stopLoading() {}
    }

    private func makeService() -> GitHubBoardSyncService {
        let configuration = URLSessionConfiguration.ephemeral
        configuration.protocolClasses = [StubURLProtocol.self]
        return GitHubBoardSyncService(session: URLSession(configuration: configuration))
    }

    private func response(
        _ request: URLRequest,
        statusCode: Int = 200,
        headers: [String: String] = [:],
        data: Data = Data("{}".utf8)
    ) throws -> (HTTPURLResponse, Data) {
        (
            HTTPURLResponse(
                url: request.url!,
                statusCode: statusCode,
                httpVersion: "HTTP/1.1",
                headerFields: headers
            )!,
            data
        )
    }

    private func json(_ value: Any) -> Data {
        try! JSONSerialization.data(withJSONObject: value)
    }

    private func recordedRequest(index: Int) throws -> URLRequest {
        StubState.lock.lock()
        defer { StubState.lock.unlock() }
        return try XCTUnwrap(StubState.requests.indices.contains(index) ? StubState.requests[index] : nil)
    }

    private func requestBody(_ request: URLRequest) -> Data {
        if let body = request.httpBody { return body }
        guard let stream = request.httpBodyStream else { return Data() }
        stream.open()
        defer { stream.close() }
        var data = Data()
        let bufferSize = 4096
        let buffer = UnsafeMutablePointer<UInt8>.allocate(capacity: bufferSize)
        defer { buffer.deallocate() }
        while stream.hasBytesAvailable {
            let read = stream.read(buffer, maxLength: bufferSize)
            if read <= 0 { break }
            data.append(buffer, count: read)
        }
        return data
    }

    override func setUp() {
        super.setUp()
        StubState.reset()
    }

    override func tearDown() {
        StubState.reset()
        super.tearDown()
    }

    func testAuthenticatedUserSendsGitHubHeadersAndParsesLogin() async throws {
        StubState.lock.lock()
        StubState.handler = { [self] request in
            try response(request, data: json(["login": "octocat"]))
        }
        StubState.lock.unlock()

        let login = try await makeService().authenticatedUser(token: Self.token)

        XCTAssertEqual(login, "octocat")
        let request = try recordedRequest(index: 0)
        XCTAssertEqual(request.url?.absoluteString, "https://api.github.com/user")
        XCTAssertEqual(request.value(forHTTPHeaderField: "Authorization"), "Bearer \(Self.token)")
        XCTAssertEqual(request.value(forHTTPHeaderField: "Accept"), "application/vnd.github+json")
        XCTAssertEqual(request.value(forHTTPHeaderField: "X-GitHub-Api-Version"), "2022-11-28")
    }

    func testDefaultBranchAndBranchHeadSHAUseRepositoryEndpoints() async throws {
        StubState.lock.lock()
        StubState.handler = { [self] request in
            switch request.url?.path {
            case "/repos/Asherlc/hang-ten":
                return try response(request, data: json(["default_branch": "main"]))
            case "/repos/Asherlc/hang-ten/git/ref/heads/main":
                return try response(request, data: json(["object": ["sha": "abc123", "type": "commit"]]))
            default:
                return try response(request, statusCode: 404)
            }
        }
        StubState.lock.unlock()

        let service = makeService()
        let defaultBranchName = try await service.defaultBranch(token: Self.token)
        XCTAssertEqual(defaultBranchName, "main")
        let headSHA = try await service.branchHeadSHA(token: Self.token, branch: "main")
        XCTAssertEqual(headSHA, "abc123")
        XCTAssertEqual(
            try recordedRequest(index: 1).url?.absoluteString,
            "https://api.github.com/repos/Asherlc/hang-ten/git/ref/heads/main"
        )
    }

    func testListBranchesPaginatesUntilShortPage() async throws {
        let firstPage = (0..<100).map { ["name": "branch-\($0)"] }
        StubState.lock.lock()
        StubState.handler = { [self] request in
            let page = URLComponents(url: request.url!, resolvingAgainstBaseURL: false)?
                .queryItems?.first { $0.name == "page" }?.value
            if page == "1" {
                return try response(request, data: json(firstPage))
            }
            return try response(request, data: json([["name": "final-a"], ["name": "final-b"]]))
        }
        StubState.lock.unlock()

        let branches = try await makeService().listBranches(token: Self.token)

        XCTAssertEqual(branches.count, 102)
        XCTAssertEqual(branches.first, "branch-0")
        XCTAssertEqual(branches.suffix(2), ["final-a", "final-b"])
    }

    func testCreateBranchPostsRefBody() async throws {
        StubState.lock.lock()
        StubState.handler = { [self] request in
            try response(request, statusCode: 201, data: json(["ref": "refs/heads/edit"]))
        }
        StubState.lock.unlock()

        try await makeService().createBranch(token: Self.token, name: "edit", fromSHA: "abc123")

        let request = try recordedRequest(index: 0)
        XCTAssertEqual(request.httpMethod, "POST")
        XCTAssertEqual(request.url?.absoluteString, "https://api.github.com/repos/Asherlc/hang-ten/git/refs")
        let body = try XCTUnwrap(JSONSerialization.jsonObject(with: requestBody(request)) as? [String: Any])
        XCTAssertEqual(body["ref"] as? String, "refs/heads/edit")
        XCTAssertEqual(body["sha"] as? String, "abc123")
    }

    func testTreeEntriesRequiresCompleteRecursiveTree() async throws {
        let treePayload: [String: Any] = [
            "truncated": false,
            "tree": [
                ["path": "Hangboards/slug/board.json", "type": "blob", "sha": "sha-json"],
                ["path": "Hangboards/slug/assets", "type": "tree", "sha": "sha-tree"],
                ["path": "Hangboards/slug/assets/primary.png", "type": "blob", "sha": "sha-png"],
            ],
        ]
        StubState.lock.lock()
        StubState.handler = { [self] request in
            try response(request, data: json(treePayload))
        }
        StubState.lock.unlock()

        let entries = try await makeService().treeEntries(token: Self.token, branch: "main")

        XCTAssertEqual(entries.count, 3)
        XCTAssertEqual(entries[0].path, "Hangboards/slug/board.json")
        XCTAssertEqual(entries[2].sha, "sha-png")
        XCTAssertTrue(
            try recordedRequest(index: 0).url?.absoluteString.contains("/git/trees/main?recursive=1") == true
        )

        StubState.reset()
        StubState.lock.lock()
        StubState.handler = { [self] request in
            try response(request, data: json(["truncated": true, "tree": []]))
        }
        StubState.lock.unlock()

        do {
            _ = try await makeService().treeEntries(token: Self.token, branch: "main")
            XCTFail("truncated trees must fail")
        } catch let error as GitHubSyncError {
            guard case .invalidResponse(let message) = error else {
                return XCTFail("unexpected error \(error)")
            }
            XCTAssertTrue(message.contains("truncated"), message)
        }
    }

    func testBlobDecodesWhitespaceSeparatedBase64() async throws {
        let payloadData = Data("board-bytes".utf8)
        StubState.lock.lock()
        StubState.handler = { [self] request in
            let encoded = payloadData.base64EncodedString()
                .chunked(into: 8)
                .joined(separator: "\n")
            return try response(
                request,
                data: json(["encoding": "base64", "content": encoded])
            )
        }
        StubState.lock.unlock()

        let decoded = try await makeService().blob(token: Self.token, sha: "sha-json")

        XCTAssertEqual(decoded, payloadData)
    }

    func testCommitFileIncludesExplicitSHAAndEncodedContentsPath() async throws {
        StubState.lock.lock()
        StubState.handler = { [self] request in
            try response(
                request,
                statusCode: 200,
                data: json(["commit": ["sha": "commit-sha"]])
            )
        }
        StubState.lock.unlock()

        let commitSHA = try await makeService().commitFile(
            token: Self.token,
            branch: "edit-board",
            path: "Hangboards/slug/board.json",
            content: Data("{}".utf8),
            message: "Update fixture.board",
            sha: "existing-blob-sha"
        )

        XCTAssertEqual(commitSHA, "commit-sha")
        let request = try recordedRequest(index: 0)
        XCTAssertEqual(request.httpMethod, "PUT")
        XCTAssertEqual(
            request.url?.absoluteString,
            "https://api.github.com/repos/Asherlc/hang-ten/contents/Hangboards/slug/board.json"
        )
        let body = try XCTUnwrap(JSONSerialization.jsonObject(with: requestBody(request)) as? [String: Any])
        XCTAssertEqual(body["sha"] as? String, "existing-blob-sha")
        XCTAssertEqual(body["branch"] as? String, "edit-board")
        XCTAssertEqual(body["message"] as? String, "Update fixture.board")
        XCTAssertEqual(
            body["content"] as? String,
            Data("{}".utf8).base64EncodedString()
        )
    }

    func testCommitFileResolvesExistingBlobSHAWhenReplacingWithoutOne() async throws {
        let treePayload: [String: Any] = [
            "truncated": false,
            "tree": [
                ["path": "Hangboards/slug/board.json", "type": "blob", "sha": "resolved-blob-sha"],
            ],
        ]
        StubState.lock.lock()
        StubState.handler = { [self] request in
            if request.url?.path.contains("/git/trees/") == true {
                return try response(request, data: json(treePayload))
            }
            return try response(request, data: json(["commit": ["sha": "new-commit-sha"]]))
        }
        StubState.lock.unlock()

        let commitSHA = try await makeService().commitFile(
            token: Self.token,
            branch: "edit-board",
            path: "Hangboards/slug/board.json",
            content: Data("patched".utf8),
            message: "Update",
            sha: nil
        )

        XCTAssertEqual(commitSHA, "new-commit-sha")
        let putRequest = try recordedRequest(index: 1)
        XCTAssertEqual(putRequest.httpMethod, "PUT")
        let body = try XCTUnwrap(JSONSerialization.jsonObject(with: requestBody(putRequest)) as? [String: Any])
        XCTAssertEqual(body["sha"] as? String, "resolved-blob-sha")
    }

    func testCreatePullRequestReturnsHTMLURL() async throws {
        StubState.lock.lock()
        StubState.handler = { [self] request in
            try response(
                request,
                data: json(["html_url": "https://github.com/Asherlc/hang-ten/pull/42"])
            )
        }
        StubState.lock.unlock()

        let url = try await makeService().createPullRequest(
            token: Self.token,
            title: "Board edits",
            head: "edit-board",
            base: "main",
            body: "Native editor sync"
        )

        XCTAssertEqual(url.absoluteString, "https://github.com/Asherlc/hang-ten/pull/42")
        let body = try XCTUnwrap(
            JSONSerialization.jsonObject(with: requestBody(try recordedRequest(index: 0))) as? [String: Any]
        )
        XCTAssertEqual(body["head"] as? String, "edit-board")
        XCTAssertEqual(body["base"] as? String, "main")
    }

    func testFetchBoardPackagePullsBothBlobsFromTree() async throws {
        let boardBytes = Data(
            "{\"presentations\": [{\"id\": \"front\", \"name\": \"Front\", \"assetPath\": \"assets/cover.png\", \"aspectRatio\": 2.0, \"default\": true}]}".utf8
        )
        let pngBytes = Data([0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A])
        StubState.lock.lock()
        StubState.handler = { [self] request in
            if request.url?.path.contains("/git/trees/") == true {
                return try response(
                    request,
                    data: json([
                        "truncated": false,
                        "tree": [
                            ["path": "Hangboards/slug/board.json", "type": "blob", "sha": "sha-json"],
                            ["path": "Hangboards/slug/assets/cover.png", "type": "blob", "sha": "sha-png"],
                        ],
                    ])
                )
            }
            if request.url?.path.contains("blobs/sha-json") == true {
                return try response(
                    request,
                    data: json(["encoding": "base64", "content": boardBytes.base64EncodedString()])
                )
            }
            return try response(
                request,
                data: json(["encoding": "base64", "content": pngBytes.base64EncodedString()])
            )
        }
        StubState.lock.unlock()

        let payload = try await makeService().fetchBoardPackage(token: Self.token, branch: "main", slug: "slug")

        XCTAssertEqual(payload.boardJSON, boardBytes)
        XCTAssertEqual(payload.primaryPNG, pngBytes)
        XCTAssertEqual(payload.assetPath, "assets/cover.png")
    }

    func testFetchBoardPackageFailsWhenPackageEntriesMissing() async throws {
        StubState.lock.lock()
        StubState.handler = { [self] request in
            try response(
                request,
                data: json(["truncated": false, "tree": []])
            )
        }
        StubState.lock.unlock()

        do {
            _ = try await makeService().fetchBoardPackage(token: Self.token, branch: "main", slug: "slug")
            XCTFail("missing package entries must fail")
        } catch let error as GitHubSyncError {
            guard case .notFound = error else {
                return XCTFail("unexpected error \(error)")
            }
        }
    }

    func testHTTPStatusesMapOntoPythonClientTaxonomy() async throws {
        func expect(
            statusCode: Int,
            headers: [String: String] = [:],
            expected: GitHubSyncError,
            file: StaticString = #filePath,
            line: UInt = #line
        ) async throws {
            StubState.reset()
            StubState.lock.lock()
            StubState.handler = { [self] request in
                try response(
                    request,
                    statusCode: statusCode,
                    headers: headers,
                    data: json(["message": "boom"])
                )
            }
            StubState.lock.unlock()
            do {
                _ = try await makeService().authenticatedUser(token: Self.token)
                XCTFail("expected failure", file: file, line: line)
            } catch let error as GitHubSyncError {
                XCTAssertEqual(error, expected, file: file, line: line)
            }
        }

        try await expect(statusCode: 404, expected: .notFound("boom"))
        try await expect(statusCode: 409, expected: .conflict("boom"))
        try await expect(statusCode: 422, expected: .conflict("boom"))
        try await expect(statusCode: 401, expected: .unauthorized("boom"))
        try await expect(statusCode: 403, expected: .forbidden("boom"))
        try await expect(
            statusCode: 403,
            headers: ["X-RateLimit-Remaining": "0"],
            expected: .rateLimited("boom")
        )
        try await expect(statusCode: 429, expected: .rateLimited("boom"))
        try await expect(statusCode: 500, expected: .transport("boom"))
    }

    func testTransportAndInvalidResponseErrors() async throws {
        StubState.lock.lock()
        StubState.handler = { _ in throw URLError(.notConnectedToInternet) }
        StubState.lock.unlock()
        do {
            _ = try await makeService().authenticatedUser(token: Self.token)
            XCTFail("connection failures must surface as transport errors")
        } catch let error as GitHubSyncError {
            guard case .transport = error else {
                return XCTFail("unexpected error \(error)")
            }
        }

        StubState.reset()
        StubState.lock.lock()
        StubState.handler = { [self] request in
            try response(request, data: Data("<html>".utf8))
        }
        StubState.lock.unlock()
        do {
            _ = try await makeService().authenticatedUser(token: Self.token)
            XCTFail("malformed payloads must surface as invalid response errors")
        } catch let error as GitHubSyncError {
            guard case .invalidResponse = error else {
                return XCTFail("unexpected error \(error)")
            }
        }
    }

    func testErrorMessagesRedactToken() async throws {
        StubState.lock.lock()
        StubState.handler = { [self] request in
            try response(
                request,
                statusCode: 401,
                data: json(["message": "Bad credentials for token-secret-123"])
            )
        }
        StubState.lock.unlock()

        do {
            _ = try await makeService().authenticatedUser(token: Self.token)
            XCTFail("expected unauthorized failure")
        } catch let error as GitHubSyncError {
            guard case .unauthorized(let message) = error else {
                return XCTFail("unexpected error \(error)")
            }
            XCTAssertFalse(message.contains(Self.token))
            XCTAssertTrue(message.contains("[REDACTED]"))
        }
    }
}

private extension String {
    func chunked(into size: Int) -> [String] {
        stride(from: 0, to: count, by: size).map { offset in
            let start = index(startIndex, offsetBy: offset)
            let end = index(start, offsetBy: Swift.min(size, distance(from: start, to: endIndex)))
            return String(self[start..<end])
        }
    }
}
