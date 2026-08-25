import Foundation
import Security

struct GitHubTreeEntry: Equatable {
    let path: String
    let type: String
    let sha: String
}

enum GitHubSyncError: Error, Equatable, LocalizedError {
    case notFound(String)
    case conflict(String)
    case unauthorized(String)
    case forbidden(String)
    case rateLimited(String)
    case transport(String)
    case invalidResponse(String)

    var errorDescription: String? {
        switch self {
        case .notFound(let message): message
        case .conflict(let message): message
        case .unauthorized(let message): message
        case .forbidden(let message): message
        case .rateLimited(let message): message
        case .transport(let message): message
        case .invalidResponse(let message): message
        }
    }
}

struct GitHubBoardPackagePayload: Equatable {
    let boardJSON: Data
    let primaryPNG: Data
    let assetPath: String
}

struct GitHubDeviceChallenge: Equatable {
    let deviceCode: String
    let userCode: String
    let verificationURL: URL
    let expiresIn: TimeInterval
    let pollingInterval: TimeInterval
}

enum GitHubDeviceAuthorizationResult: Equatable {
    case authorizationPending
    case slowDown
    case authorized(String)
}

struct GitHubTokenStore {
    static let defaultService = "com.hangten.training.board-editor"

    private let service: String
    private let account = "editor-sync-token"

    init(service: String = GitHubTokenStore.defaultService) {
        self.service = service
    }

    func save(_ token: String) throws {
        try? delete()
        var query: [String: Any] = baseQuery()
        query[kSecValueData as String] = Data(token.utf8)
        query[kSecAttrAccessible as String] = kSecAttrAccessibleAfterFirstUnlockThisDeviceOnly
        let status = SecItemAdd(query as CFDictionary, nil)
        guard status == errSecSuccess else {
            throw GitHubSyncError.transport("Keychain rejected the GitHub token (status \(status)).")
        }
    }

    func load() -> String? {
        var query: [String: Any] = baseQuery()
        query[kSecReturnData as String] = true
        query[kSecMatchLimit as String] = kSecMatchLimitOne
        var result: AnyObject?
        let status = SecItemCopyMatching(query as CFDictionary, &result)
        guard status == errSecSuccess, let data = result as? Data else { return nil }
        return String(data: data, encoding: .utf8)
    }

    func delete() throws {
        let status = SecItemDelete(baseQuery() as CFDictionary)
        guard status == errSecSuccess || status == errSecItemNotFound else {
            throw GitHubSyncError.transport("Keychain could not delete the GitHub token (status \(status)).")
        }
    }

    private func baseQuery() -> [String: Any] {
        [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: account,
        ]
    }
}

struct GitHubBoardSyncService {
    static let repositoryOwner = "Asherlc"
    static let repositoryName = "hang-ten"
    private static let oauthBaseURL = URL(string: "https://github.com")!

    private let baseURL: URL
    private let session: URLSession

    init(
        baseURL: URL = URL(string: "https://api.github.com")!,
        session: URLSession = .shared
    ) {
        self.baseURL = baseURL
        self.session = session
    }

    func authenticatedUser(token: String) async throws -> String {
        let payload = try await call(token: token, method: "GET", path: "/user")
        return try requiredString(payload, field: "login")
    }

    func requestDeviceChallenge(clientID: String) async throws -> GitHubDeviceChallenge {
        let payload = try await deviceAuthorizationCall(
            path: "/login/device/code",
            form: [
                ("client_id", clientID),
                ("scope", "repo read:org"),
            ]
        )
        guard case .object(let fields) = payload,
              let deviceCode = Self.nonEmptyString(fields["device_code"]),
              let userCode = Self.nonEmptyString(fields["user_code"]),
              let verificationURI = Self.nonEmptyString(fields["verification_uri"]),
              let verificationURL = URL(string: verificationURI),
              verificationURL.scheme?.lowercased() == "https",
              verificationURL.host != nil,
              let expiresIn = Self.positiveFiniteNumber(fields["expires_in"]),
              let interval = Self.positiveFiniteNumber(fields["interval"]) else {
            throw GitHubSyncError.invalidResponse("GitHub returned invalid device authorization data")
        }
        return GitHubDeviceChallenge(
            deviceCode: deviceCode,
            userCode: userCode,
            verificationURL: verificationURL,
            expiresIn: expiresIn,
            pollingInterval: interval
        )
    }

    func pollDeviceAuthorization(
        clientID: String,
        deviceCode: String
    ) async throws -> GitHubDeviceAuthorizationResult {
        let payload = try await deviceAuthorizationCall(
            path: "/login/oauth/access_token",
            form: [
                ("client_id", clientID),
                ("device_code", deviceCode),
                ("grant_type", "urn:ietf:params:oauth:grant-type:device_code"),
            ]
        )
        guard case .object(let fields) = payload else {
            throw GitHubSyncError.invalidResponse("GitHub returned invalid device authorization data")
        }
        if let token = Self.nonEmptyString(fields["access_token"]) {
            return .authorized(token)
        }
        switch Self.nonEmptyString(fields["error"]) {
        case "authorization_pending":
            return .authorizationPending
        case "slow_down":
            return .slowDown
        case "access_denied":
            throw GitHubSyncError.unauthorized("GitHub authorization was denied.")
        case "expired_token":
            throw GitHubSyncError.unauthorized("GitHub authorization expired. Please try again.")
        default:
            throw GitHubSyncError.invalidResponse("GitHub returned invalid device authorization data")
        }
    }

    func defaultBranch(token: String) async throws -> String {
        let payload = try await call(token: token, method: "GET", path: repositoryPath())
        return try requiredString(payload, field: "default_branch")
    }

    func branchHeadSHA(token: String, branch: String) async throws -> String {
        let payload = try await call(
            token: token,
            method: "GET",
            path: "\(repositoryPath())/git/ref/heads/\(Self.escapedPathSegment(branch))"
        )
        let reference = try requiredObject(payload, field: "object")
        return try requiredString(reference, field: "sha")
    }

    func listBranches(token: String) async throws -> [String] {
        var branches: [String] = []
        var page = 1
        while true {
            let payload = try await call(
                token: token,
                method: "GET",
                path: "\(repositoryPath())/branches?per_page=100&page=\(page)"
            )
            guard case .array(let items) = payload else {
                throw GitHubSyncError.invalidResponse("GitHub returned invalid branch data")
            }
            var names: [String] = []
            for item in items {
                names.append(try requiredString(item, field: "name"))
            }
            branches.append(contentsOf: names)
            if names.count < 100 {
                return branches
            }
            page += 1
        }
    }

    func createBranch(token: String, name: String, fromSHA: String) async throws {
        _ = try await call(
            token: token,
            method: "POST",
            path: "\(repositoryPath())/git/refs",
            body: ["ref": "refs/heads/\(name)", "sha": fromSHA]
        )
    }

    func treeEntries(token: String, branch: String) async throws -> [GitHubTreeEntry] {
        let payload = try await call(
            token: token,
            method: "GET",
            path: "\(repositoryPath())/git/trees/\(Self.escapedPathSegment(branch))?recursive=1"
        )
        guard case .object(let fields) = payload else {
            throw GitHubSyncError.invalidResponse("GitHub returned invalid tree data")
        }
        guard case .bool(false)? = fields["truncated"] else {
            throw GitHubSyncError.invalidResponse("GitHub returned a truncated tree")
        }
        guard case .array(let tree)? = fields["tree"] else {
            throw GitHubSyncError.invalidResponse("GitHub returned invalid tree data")
        }
        return try tree.map { entry in
            GitHubTreeEntry(
                path: try requiredString(entry, field: "path"),
                type: try requiredString(entry, field: "type"),
                sha: try requiredString(entry, field: "sha")
            )
        }
    }

    func blob(token: String, sha: String) async throws -> Data {
        let payload = try await call(
            token: token,
            method: "GET",
            path: "\(repositoryPath())/git/blobs/\(Self.escapedPathSegment(sha))"
        )
        guard case .object(let fields) = payload,
              case .string(let encoding)? = fields["encoding"] else {
            throw GitHubSyncError.invalidResponse("GitHub returned invalid response data")
        }
        guard encoding == "base64" else {
            throw GitHubSyncError.invalidResponse("GitHub returned unsupported blob encoding")
        }
        guard case .string(let content)? = fields["content"] else {
            throw GitHubSyncError.invalidResponse("GitHub returned invalid response data")
        }
        let compacted = content.split(whereSeparator: \.isWhitespace).joined()
        guard let decoded = Data(base64Encoded: compacted) else {
            throw GitHubSyncError.invalidResponse("GitHub returned invalid blob data")
        }
        return decoded
    }

    /// Commits one file through the Contents API. When no SHA is supplied the
    /// current blob SHA is resolved from the branch tree so replacing an
    /// existing file succeeds.
    @discardableResult
    func commitFile(
        token: String,
        branch: String,
        path: String,
        content: Data,
        message: String,
        sha: String?
    ) async throws -> String {
        var resolvedSHA = sha
        if resolvedSHA == nil {
            resolvedSHA = try? await existingBlobSHA(token: token, branch: branch, path: path)
        }
        var body: [String: Any] = [
            "message": message,
            "content": content.base64EncodedString(),
            "branch": branch,
        ]
        if let resolvedSHA {
            body["sha"] = resolvedSHA
        }
        let payload = try await call(
            token: token,
            method: "PUT",
            path: "\(repositoryPath())/contents/\(Self.escapedPathWithSlashes(path))",
            body: body
        )
        let commit = try requiredObject(payload, field: "commit")
        return try requiredString(commit, field: "sha")
    }

    func createPullRequest(
        token: String,
        title: String,
        head: String,
        base: String,
        body: String
    ) async throws -> URL {
        let payload = try await call(
            token: token,
            method: "POST",
            path: "\(repositoryPath())/pulls",
            body: ["title": title, "head": head, "base": base, "body": body]
        )
        let htmlURL = try requiredString(payload, field: "html_url")
        guard let url = URL(string: htmlURL) else {
            throw GitHubSyncError.invalidResponse("GitHub returned an invalid pull request URL")
        }
        return url
    }

    /// Fetches one canonical board package's board.json plus its default
    /// presentation image from the Hangboards library on the given branch.
    func fetchBoardPackage(
        token: String,
        branch: String,
        slug: String
    ) async throws -> GitHubBoardPackagePayload {
        let entries = try await treeEntries(token: token, branch: branch)
        let prefix = "Hangboards/\(slug)/"
        guard let boardEntry = entries.first(where: {
            $0.path == "\(prefix)board.json" && $0.type == "blob"
        }) else {
            throw GitHubSyncError.notFound("board package \(slug) is not available")
        }
        let boardJSON = try await blob(token: token, sha: boardEntry.sha)
        let assetPath = try Self.defaultPresentationAssetPath(boardJSON)
        guard let imageEntry = entries.first(where: {
            $0.path == "\(prefix)\(assetPath)" && $0.type == "blob"
        }) else {
            throw GitHubSyncError.notFound(
                "board package \(slug) is missing its default presentation image"
            )
        }
        let primaryPNG = try await blob(token: token, sha: imageEntry.sha)
        return GitHubBoardPackagePayload(
            boardJSON: boardJSON,
            primaryPNG: primaryPNG,
            assetPath: assetPath
        )
    }

    private static func defaultPresentationAssetPath(_ boardJSON: Data) throws -> String {
        let payload = try JSONSerialization.jsonObject(with: boardJSON)
        guard let presentations = payload as? [String: Any],
              let entries = presentations["presentations"] as? [[String: Any]] else {
            throw GitHubSyncError.invalidResponse(
                "board.json does not declare any presentations"
            )
        }
        let declared = entries.first(where: { ($0["default"] as? Bool) == true })
            ?? entries.first
        guard let assetPath = declared?["assetPath"] as? String, !assetPath.isEmpty else {
            throw GitHubSyncError.invalidResponse(
                "board.json presentations do not declare an asset path"
            )
        }
        return assetPath
    }

    private func existingBlobSHA(
        token: String,
        branch: String,
        path: String
    ) async throws -> String? {
        let entries = try await treeEntries(token: token, branch: branch)
        return entries.first { $0.path == path && $0.type == "blob" }?.sha
    }

    private func repositoryPath() -> String {
        "/repos/\(Self.escapedPathSegment(Self.repositoryOwner))/\(Self.escapedPathSegment(Self.repositoryName))"
    }

    private static func escapedPathSegment(_ value: String) -> String {
        value.addingPercentEncoding(
            withAllowedCharacters: CharacterSet(charactersIn: "-._~").union(.alphanumerics)
        ) ?? value
    }

    private static func escapedPathWithSlashes(_ value: String) -> String {
        value.addingPercentEncoding(
            withAllowedCharacters: CharacterSet(charactersIn: "-._~/").union(.alphanumerics)
        ) ?? value
    }

    private enum JSONValue {
        case null
        case bool(Bool)
        case string(String)
        case number(Double)
        case array([JSONValue])
        case object([String: JSONValue])

        init(any: Any) {
            switch any {
            case let dictionary as [String: Any]:
                self = .object(dictionary.mapValues { JSONValue(any: $0) })
            case let array as [Any]:
                self = .array(array.map { JSONValue(any: $0) })
            case let string as String:
                self = .string(string)
            case let number as NSNumber:
                self = Self.number(number)
            default:
                self = .null
            }
        }

        private static func number(_ number: NSNumber) -> JSONValue {
            if CFGetTypeID(number) == CFBooleanGetTypeID() {
                .bool(number.boolValue)
            } else {
                .number(number.doubleValue)
            }
        }
    }

    private func call(
        token: String,
        method: String,
        path: String,
        body: [String: Any]? = nil
    ) async throws -> JSONValue {
        guard let url = URL(string: baseURL.absoluteString + path) else {
            throw GitHubSyncError.transport("Unable to reach GitHub")
        }
        var request = URLRequest(url: url)
        request.httpMethod = method
        request.setValue("application/vnd.github+json", forHTTPHeaderField: "Accept")
        request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        request.setValue("2022-11-28", forHTTPHeaderField: "X-GitHub-Api-Version")
        if let body {
            request.httpBody = try JSONSerialization.data(withJSONObject: body)
            request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        }
        let data: Data
        let httpResponse: HTTPURLResponse
        do {
            let (responseData, response) = try await session.data(for: request)
            guard let http = response as? HTTPURLResponse else {
                throw GitHubSyncError.transport("GitHub returned an invalid response")
            }
            data = responseData
            httpResponse = http
        } catch let error as GitHubSyncError {
            throw error
        } catch {
            throw GitHubSyncError.transport("Unable to reach GitHub")
        }

        let status = httpResponse.statusCode
        guard !(200..<300).contains(status) else {
            do {
                let decoded = try JSONSerialization.jsonObject(with: data)
                guard decoded is [String: Any] || decoded is [Any] else {
                    throw GitHubSyncError.invalidResponse("GitHub returned invalid JSON data")
                }
                return JSONValue(any: decoded)
            } catch let error as GitHubSyncError {
                throw error
            } catch {
                throw GitHubSyncError.invalidResponse("GitHub returned malformed JSON")
            }
        }

        let message = Self.errorMessage(from: data, statusCode: status, token: token)
        switch status {
        case 404:
            throw GitHubSyncError.notFound(message)
        case 409, 412, 422:
            throw GitHubSyncError.conflict(message)
        case 401:
            throw GitHubSyncError.unauthorized(message)
        case 429:
            throw GitHubSyncError.rateLimited(message)
        case 403:
            let remaining = httpResponse.value(forHTTPHeaderField: "X-RateLimit-Remaining")
            if remaining == "0" {
                throw GitHubSyncError.rateLimited(message)
            }
            throw GitHubSyncError.forbidden(message)
        default:
            throw GitHubSyncError.transport(message)
        }
    }

    private func deviceAuthorizationCall(
        path: String,
        form: [(String, String)]
    ) async throws -> JSONValue {
        guard let url = URL(string: Self.oauthBaseURL.absoluteString + path) else {
            throw GitHubSyncError.transport("Unable to reach GitHub")
        }
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Accept")
        request.setValue("application/x-www-form-urlencoded", forHTTPHeaderField: "Content-Type")
        request.httpBody = Data(Self.formEncoded(form).utf8)
        do {
            let (data, response) = try await session.data(for: request)
            guard let httpResponse = response as? HTTPURLResponse,
                  (200..<300).contains(httpResponse.statusCode),
                  let decoded = try? JSONSerialization.jsonObject(with: data),
                  decoded is [String: Any] else {
                throw GitHubSyncError.invalidResponse("GitHub returned invalid device authorization data")
            }
            return JSONValue(any: decoded)
        } catch let error as GitHubSyncError {
            throw error
        } catch {
            throw GitHubSyncError.transport("Unable to reach GitHub")
        }
    }

    private static func formEncoded(_ fields: [(String, String)]) -> String {
        fields.map { "\(formEncodedComponent($0.0))=\(formEncodedComponent($0.1))" }
            .joined(separator: "&")
    }

    private static func formEncodedComponent(_ value: String) -> String {
        value.addingPercentEncoding(
            withAllowedCharacters: CharacterSet(charactersIn: "-._~").union(.alphanumerics)
        ) ?? value
    }

    private static func nonEmptyString(_ value: JSONValue?) -> String? {
        guard case .string(let string)? = value, !string.isEmpty else { return nil }
        return string
    }

    private static func positiveFiniteNumber(_ value: JSONValue?) -> TimeInterval? {
        guard case .number(let number)? = value, number.isFinite, number > 0 else { return nil }
        return number
    }

    private static func errorMessage(
        from data: Data,
        statusCode: Int,
        token: String
    ) -> String {
        var message: String?
        if let payload = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
           let bodyMessage = payload["message"] as? String {
            message = bodyMessage
        }
        var resolved = message ?? "GitHub request failed with HTTP \(statusCode)"
        if !token.isEmpty {
            resolved = resolved.replacingOccurrences(of: token, with: "[REDACTED]")
        }
        return resolved
    }

    private func requiredString(_ payload: JSONValue, field: String) throws -> String {
        guard case .object(let fields) = payload,
              case .string(let value)? = fields[field] else {
            throw GitHubSyncError.invalidResponse("GitHub returned invalid response data")
        }
        return value
    }

    private func requiredObject(_ payload: JSONValue, field: String) throws -> JSONValue {
        guard case .object(let fields) = payload,
              case .object(let nested)? = fields[field] else {
            throw GitHubSyncError.invalidResponse("GitHub returned invalid response data")
        }
        return .object(nested)
    }
}
