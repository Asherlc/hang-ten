import Foundation

final class CheckoutSelection {
    enum ValidationError: LocalizedError, Equatable {
        case notHangTenCheckout

        var errorDescription: String? {
            "Choose a Hang Ten checkout containing .git, Tools/HangboardPipeline/src/hangboard_vectorizer, Tools/HangboardPipeline/boards, and Tools/HangboardWorkbench/server.py."
        }
    }

    private static let preferenceKey = "HangboardWorkbench.checkoutPath"

    private let defaults: UserDefaults
    private let fileManager: FileManager

    init(defaults: UserDefaults = .standard, fileManager: FileManager = .default) {
        self.defaults = defaults
        self.fileManager = fileManager
    }

    static func validatedURL(_ url: URL) throws -> URL {
        try validatedURL(url, fileManager: .default)
    }

    func lastValidCheckout() -> URL? {
        guard let path = defaults.string(forKey: Self.preferenceKey) else {
            return nil
        }
        do {
            return try Self.validatedURL(URL(fileURLWithPath: path), fileManager: fileManager)
        } catch {
            clear()
            return nil
        }
    }

    func remember(_ url: URL) {
        guard let normalized = try? Self.validatedURL(url, fileManager: fileManager) else {
            clear()
            return
        }
        defaults.set(normalized.path, forKey: Self.preferenceKey)
    }

    func clear() {
        defaults.removeObject(forKey: Self.preferenceKey)
    }

    private static func validatedURL(_ url: URL, fileManager: FileManager) throws -> URL {
        guard url.isFileURL else {
            throw ValidationError.notHangTenCheckout
        }
        let normalized = url.standardizedFileURL.resolvingSymlinksInPath()
        guard isDirectory(normalized, fileManager: fileManager),
              fileManager.fileExists(atPath: normalized.appending(path: ".git").path),
              isDirectory(
                  normalized.appending(path: "Tools/HangboardPipeline/src/hangboard_vectorizer"),
                  fileManager: fileManager
              ),
              isDirectory(
                  normalized.appending(path: "Tools/HangboardPipeline/boards"),
                  fileManager: fileManager
              ),
              fileManager.fileExists(
                  atPath: normalized.appending(path: "Tools/HangboardWorkbench/server.py").path
              ) else {
            throw ValidationError.notHangTenCheckout
        }
        return normalized
    }

    private static func isDirectory(_ url: URL, fileManager: FileManager) -> Bool {
        var isDirectory = ObjCBool(false)
        return fileManager.fileExists(atPath: url.path, isDirectory: &isDirectory) && isDirectory.boolValue
    }
}
