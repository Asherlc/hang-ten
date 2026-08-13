import Foundation

// The exporter decodes board artwork so it uses the same strict package path
// as the app, but it does not render workout highlights.
enum BoardHighlightMode: Hashable {
    case active
    case preview
}

@main
enum ExportPlanLibrary {
    static func main() throws {
        guard CommandLine.arguments.count == 2 else {
            throw ExportError.missingOutputPath
        }

        let store = try PlanLibraryStore(
            definition: BuiltInPlanLibraryDefinition.document
        )
        let output = URL(fileURLWithPath: CommandLine.arguments[1])
        try store.write(to: output, prettyPrinted: true, options: .atomic)
        print("Exported \(store.plans.count) plans to \(output.path)")
    }
}

private enum ExportError: LocalizedError {
    case missingOutputPath

    var errorDescription: String? {
        "Usage: ExportPlanLibrary <output-path>"
    }
}
