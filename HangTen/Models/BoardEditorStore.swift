import Foundation
import ImageIO
import UniformTypeIdentifiers

struct BoardEditedPackage: Equatable {
    let slug: String
    let packageURL: URL
    let document: BoardEditableDocument
    let imageURL: URL
    let pixelWidth: Int
    let pixelHeight: Int
}

enum BoardEditorStoreError: Error, Equatable, LocalizedError {
    case invalidSlug(String)
    case missingSourcePackage(slug: String)
    case missingEditedPackage(slug: String)
    case missingBoardDocument(slug: String)
    case invalidEditedDocument(slug: String, reason: String = "")
    case unreadablePresentationImage(slug: String)

    var errorDescription: String? {
        switch self {
        case .invalidSlug(let slug):
            "Board editor slug is invalid: \(slug)."
        case .missingSourcePackage(let slug):
            "Bundled board package \(slug) cannot be found for editing."
        case .missingEditedPackage(let slug):
            "Board package \(slug) has not been copied for editing."
        case .missingBoardDocument(let slug):
            "Edited board package \(slug) is missing board.json."
        case .invalidEditedDocument(let slug, let reason):
            reason.isEmpty
                ? "Edited board package \(slug) contains an invalid board.json."
                : "Edited board package \(slug) contains an invalid board.json: \(reason)"
        case .unreadablePresentationImage(let slug):
            "Edited board package \(slug) has an unreadable presentation image."
        }
    }
}

struct BoardEditorStore: Sendable {
    static let defaultDirectoryName = "BoardEditorPackages"

    private let baseDirectory: URL
    private let sourceLibraryURL: URL?
    private let preparationWillLoadDocument: @Sendable () -> Void
    private let documentWillLoad: @Sendable () -> Void
    private let synchronization = BoardEditorStoreSynchronization()

    init(
        baseDirectory: URL? = nil,
        sourceLibraryURL: URL? = nil,
        bundle: Bundle = .main,
        preparationWillLoadDocument: @escaping @Sendable () -> Void = {},
        documentWillLoad: @escaping @Sendable () -> Void = {}
    ) {
        self.baseDirectory = baseDirectory
            ?? FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask)[0]
                .appendingPathComponent(Self.defaultDirectoryName, isDirectory: true)
        self.sourceLibraryURL = sourceLibraryURL
            ?? bundle.resourceURL?.appendingPathComponent("Hangboards", isDirectory: true)
        self.preparationWillLoadDocument = preparationWillLoadDocument
        self.documentWillLoad = documentWillLoad
    }

    /// Copies the bundled package verbatim into the editable store when absent.
    @discardableResult
    func startEditing(slug: String) throws -> URL {
        synchronization.editingLock.lock()
        defer { synchronization.editingLock.unlock() }

        return try startEditingLocked(slug: slug).packageURL
    }

    /// Copies or reuses an editable package and loads its document while reset
    /// operations remain excluded by the package lock.
    func prepareEditablePackage(slug: String) throws -> BoardEditedPackage {
        synchronization.editingLock.lock()
        defer { synchronization.editingLock.unlock() }

        let editablePackage = try startEditingLocked(
            slug: slug,
            beforeExistingDocumentLoad: preparationWillLoadDocument
        )
        if let loadedPackage = editablePackage.loadedPackage {
            return loadedPackage
        }
        preparationWillLoadDocument()
        return try loadDocumentLocked(slug: slug)
    }

    private func startEditingLocked(
        slug: String,
        beforeExistingDocumentLoad: (@Sendable () -> Void)? = nil
    ) throws -> (packageURL: URL, loadedPackage: BoardEditedPackage?) {
        let packageURL = try validatedPackageURL(slug, requireExisting: false)
        let boardURL = packageURL.appendingPathComponent("board.json")
        if FileManager.default.fileExists(atPath: boardURL.path) {
            beforeExistingDocumentLoad?()
            return (packageURL, try loadDocumentLocked(slug: slug))
        }
        if FileManager.default.fileExists(atPath: packageURL.path) {
            try FileManager.default.removeItem(at: packageURL)
        }
        guard let sourceLibraryURL,
              FileManager.default.fileExists(
                  atPath: sourceLibraryURL.appendingPathComponent(slug, isDirectory: true).path
              ) else {
            throw BoardEditorStoreError.missingSourcePackage(slug: slug)
        }
        let sourcePackageURL = sourceLibraryURL.appendingPathComponent(slug, isDirectory: true)
        let sourceBoardURL = sourcePackageURL.appendingPathComponent("board.json")
        let sourceAssetsURL = sourcePackageURL.appendingPathComponent("assets", isDirectory: true)
        guard FileManager.default.fileExists(atPath: sourceBoardURL.path),
              FileManager.default.fileExists(atPath: sourceAssetsURL.path) else {
            throw BoardEditorStoreError.missingSourcePackage(slug: slug)
        }

        let stagingURL = baseDirectory.appendingPathComponent(
            ".\(slug)-staging-\(UUID().uuidString)",
            isDirectory: true
        )
        defer { try? FileManager.default.removeItem(at: stagingURL) }
        try FileManager.default.copyItem(at: sourcePackageURL, to: stagingURL)
        try FileManager.default.moveItem(at: stagingURL, to: packageURL)
        return (packageURL, nil)
    }

    func loadDocument(slug: String) throws -> BoardEditedPackage {
        synchronization.editingLock.lock()
        defer { synchronization.editingLock.unlock() }

        return try loadDocumentLocked(slug: slug)
    }

    private func loadDocumentLocked(slug: String) throws -> BoardEditedPackage {
        documentWillLoad()
        let packageURL = try validatedPackageURL(slug, requireExisting: true)
        let boardURL = packageURL.appendingPathComponent("board.json")
        guard FileManager.default.fileExists(atPath: boardURL.path) else {
            throw BoardEditorStoreError.missingBoardDocument(slug: slug)
        }
        let boardData: Data
        do {
            boardData = try Data(contentsOf: boardURL)
        } catch {
            throw BoardEditorStoreError.invalidEditedDocument(slug: slug)
        }
        let document: BoardEditableDocument
        do {
            document = try BoardEditableDocument(data: boardData)
        } catch let decodingError as DecodingError {
            throw BoardEditorStoreError.invalidEditedDocument(
                slug: slug,
                reason: Self.decodingReason(decodingError)
            )
        } catch {
            throw BoardEditorStoreError.invalidEditedDocument(slug: slug)
        }
        let defaultPresentation = try Self.defaultPresentation(
            in: document,
            slug: slug
        )
        let defaultImageURL = packageURL.appendingPathComponent(
            defaultPresentation.assetPath
        )
        let defaultPixelDimensions = try Self.validatePNGDimensions(
            at: defaultImageURL,
            slug: slug
        )
        let artworkSourcePresentation = Self.artworkSourcePresentation(
            for: defaultPresentation,
            in: document
        )
        let imageURL = packageURL.appendingPathComponent(
            artworkSourcePresentation.assetPath
        )
        let pixelDimensions = artworkSourcePresentation.id == defaultPresentation.id
            ? defaultPixelDimensions
            : try Self.validatePNGDimensions(at: imageURL, slug: slug)
        return BoardEditedPackage(
            slug: slug,
            packageURL: packageURL,
            document: document,
            imageURL: imageURL,
            pixelWidth: pixelDimensions.width,
            pixelHeight: pixelDimensions.height
        )
    }

    /// Validates and atomically writes the edited board.json; bundle originals
    /// are never touched.
    func save(document: BoardEditableDocument, slug: String) throws {
        let packageURL = try validatedPackageURL(slug, requireExisting: true)
        let encoded: Data
        do {
            encoded = try BoardPackageWriter.data(for: document)
        } catch {
            throw BoardEditorStoreError.invalidEditedDocument(slug: slug)
        }
        let boardURL = packageURL.appendingPathComponent("board.json")
        let temporaryURL = packageURL
            .appendingPathComponent("board.json.tmp-\(UUID().uuidString)")
        guard FileManager.default.createFile(atPath: temporaryURL.path, contents: encoded) else {
            throw BoardEditorStoreError.invalidEditedDocument(slug: slug)
        }
        defer { try? FileManager.default.removeItem(at: temporaryURL) }
        if FileManager.default.fileExists(atPath: boardURL.path) {
            _ = try FileManager.default.replaceItemAt(boardURL, withItemAt: temporaryURL)
        } else {
            try FileManager.default.moveItem(at: temporaryURL, to: boardURL)
        }
    }

    func hasEdits(slug: String) -> Bool {
        guard (try? validSlug(slug)) != nil else { return false }
        return FileManager.default.fileExists(
            atPath: baseDirectory
                .appendingPathComponent(slug, isDirectory: true)
                .appendingPathComponent("board.json").path
        )
    }

    func editedSlugs() -> [String] {
        let children = (try? FileManager.default.contentsOfDirectory(
            at: baseDirectory,
            includingPropertiesForKeys: [.isDirectoryKey],
            options: []
        )) ?? []
        return children
            .filter {
                (try? $0.resourceValues(forKeys: [.isDirectoryKey]))?.isDirectory == true &&
                    FileManager.default.fileExists(atPath: $0.appendingPathComponent("board.json").path)
            }
            .map(\.lastPathComponent)
            .sorted()
    }

    func reset(slug: String) throws {
        synchronization.editingLock.lock()
        defer { synchronization.editingLock.unlock() }

        let packageURL = try validatedPackageURL(slug, requireExisting: false)
        guard FileManager.default.fileExists(atPath: packageURL.path) else { return }
        try FileManager.default.removeItem(at: packageURL)
    }

    /// Persists a pulled presentation image at its declared package-relative
    /// path; the path must stay inside the package's assets directory.
    func persistPulledImage(slug: String, assetPath: String, data: Data) throws {
        let packageURL = try validatedPackageURL(slug, requireExisting: true)
        guard assetPath.hasPrefix("assets/"),
              !assetPath.contains(".."),
              !assetPath.hasSuffix("/") else {
            throw BoardEditorStoreError.invalidEditedDocument(slug: slug)
        }
        let destination = packageURL.appendingPathComponent(assetPath)
        let directory = destination.deletingLastPathComponent()
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
        try data.write(to: destination, options: .atomic)
    }

    func exportedFileURL(slug: String) throws -> URL {
        try validatedPackageURL(slug, requireExisting: true)
    }

    private func validatedPackageURL(
        _ slug: String,
        requireExisting: Bool
    ) throws -> URL {
        try validSlug(slug)
        try ensureBaseDirectory()
        let packageURL = baseDirectory.appendingPathComponent(slug, isDirectory: true)
        if requireExisting, !FileManager.default.fileExists(atPath: packageURL.path) {
            throw BoardEditorStoreError.missingEditedPackage(slug: slug)
        }
        return packageURL
    }

    private static func decodingReason(_ error: DecodingError) -> String {
        switch error {
        case .dataCorrupted(let context):
            context.codingPath.map(\.stringValue).joined(separator: ".")
                + ": " + context.debugDescription
        case .keyNotFound(let key, let context):
            context.codingPath.map(\.stringValue).joined(separator: ".")
                + ".\(key.stringValue) not found"
        case .typeMismatch(_, let context):
            context.codingPath.map(\.stringValue).joined(separator: ".")
                + ": " + context.debugDescription
        case .valueNotFound(let value, let context):
            context.codingPath.map(\.stringValue).joined(separator: ".")
                + ": unexpected nil \(value)"
        @unknown default:
            String(describing: error)
        }
    }

    private static func defaultPresentation(
        in document: BoardEditableDocument,
        slug: String
    ) throws -> BoardEditablePresentation {
        if let declaredDefault = document.presentations.first(where: \.isDefault) {
            return declaredDefault
        }
        guard let first = document.presentations.first else {
            throw BoardEditorStoreError.invalidEditedDocument(slug: slug)
        }
        return first
    }

    /// Explicitly rotated aliases project their canonical face at render time,
    /// as do legacy aliases that inherit a dynamic cord rig. Other legacy
    /// non-rig aliases continue to use their declared static artwork unchanged.
    private static func artworkSourcePresentation(
        for presentation: BoardEditablePresentation,
        in document: BoardEditableDocument
    ) -> BoardEditablePresentation {
        guard let sourcePresentationID = presentation.sourcePresentationID,
              let sourcePresentation = document.presentations.first(where: {
                  $0.id == sourcePresentationID
              }),
              presentation.rotationDegrees != nil || sourcePresentation.cordRig != nil else {
            return presentation
        }
        return sourcePresentation
    }

    private func validSlug(_ slug: String) throws -> String {
        guard !slug.isEmpty,
              let first = slug.unicodeScalars.first,
              let last = slug.unicodeScalars.last,
              Self.isLowercaseASCIIOrDigit(first),
              Self.isLowercaseASCIIOrDigit(last),
              slug.unicodeScalars.allSatisfy({
                  Self.isLowercaseASCIIOrDigit($0) || $0 == "-"
              }) else {
            throw BoardEditorStoreError.invalidSlug(slug)
        }
        return slug
    }

    private static func isLowercaseASCIIOrDigit(_ scalar: Unicode.Scalar) -> Bool {
        (97...122).contains(scalar.value) || (48...57).contains(scalar.value)
    }

    private func ensureBaseDirectory() throws {
        try FileManager.default.createDirectory(at: baseDirectory, withIntermediateDirectories: true)
    }

    private static func validatePNGDimensions(
        at url: URL,
        slug: String
    ) throws -> (width: Int, height: Int) {
        let data: Data
        do {
            data = try Data(contentsOf: url)
        } catch {
            throw BoardEditorStoreError.unreadablePresentationImage(slug: slug)
        }
        guard data.starts(with: [0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]),
              let source = CGImageSourceCreateWithData(
                  data as CFData,
                  [kCGImageSourceShouldCache: false] as CFDictionary
              ),
              CGImageSourceGetType(source) as String? == UTType.png.identifier,
              CGImageSourceGetCount(source) == 1,
              CGImageSourceGetStatus(source) == .statusComplete,
              CGImageSourceGetStatusAtIndex(source, 0) == .statusComplete,
              let properties = CGImageSourceCopyPropertiesAtIndex(source, 0, nil) as? [CFString: Any],
              let width = properties[kCGImagePropertyPixelWidth] as? NSNumber,
              let height = properties[kCGImagePropertyPixelHeight] as? NSNumber else {
            throw BoardEditorStoreError.unreadablePresentationImage(slug: slug)
        }
        return (width.intValue, height.intValue)
    }
}

private final class BoardEditorStoreSynchronization: @unchecked Sendable {
    let editingLock = NSLock()
}
