import Foundation

final class CheckoutSelection {
    enum ValidationError: LocalizedError, Equatable {
        case notHangTenCheckout

        var errorDescription: String? {
            "Choose a local Hang Ten repository copy containing .git and Hangboards."
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
        let lexical = url.standardizedFileURL
        guard fileType(at: lexical, fileManager: fileManager) != .typeSymbolicLink,
              isDirectory(lexical, fileManager: fileManager),
              isRegularFileOrDirectory(
                  lexical.appending(path: ".git"),
                  fileManager: fileManager
              ),
              isDirectory(
                  lexical.appending(path: "Hangboards"),
                  fileManager: fileManager
              ) else {
            throw ValidationError.notHangTenCheckout
        }
        return lexical.resolvingSymlinksInPath()
    }

    private static func isDirectory(_ url: URL, fileManager: FileManager) -> Bool {
        fileType(at: url, fileManager: fileManager) == .typeDirectory
    }

    private static func isRegularFileOrDirectory(_ url: URL, fileManager: FileManager) -> Bool {
        switch fileType(at: url, fileManager: fileManager) {
        case .typeRegular, .typeDirectory:
            true
        default:
            false
        }
    }

    private static func fileType(at url: URL, fileManager: FileManager) -> FileAttributeType? {
        try? fileManager.attributesOfItem(atPath: url.path)[.type] as? FileAttributeType
    }
}
