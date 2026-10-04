
#if DEBUG
/// Temporary diagnostic recorder. No observable state and no entity mutations.
@MainActor
final class BoardHighlightDiagnostic {
    static let isEnabled = ProcessInfo.processInfo.environment["HANGTEN_REVIEW_HIGHLIGHT_DIAGNOSTIC"] == "1"
    static let shared = BoardHighlightDiagnostic()
    private let enabled: Bool
    private var sink: FileHandle?
    private var sequence = 0
    private var failed = false
    private var samplers: [UUID: Task<Void, Never>] = [:]
    private var viewSignatures: [UUID: String] = [:]
    private var requestedIDs: [UUID: Set<String>] = [:]
    private var requestedModes: [UUID: String] = [:]

    private init() {
        let env = ProcessInfo.processInfo.environment
        enabled = Self.isEnabled
        guard enabled else { return }
        do {
            let rawRun = env["HANGTEN_REVIEW_DIAGNOSTIC_RUN"] ?? "placid-badger-cad-second-half"
            let run = String(rawRun.filter { $0.isASCII && ($0.isLetter || $0.isNumber || $0 == "-" || $0 == "_") }.prefix(100))
            guard !run.isEmpty else { throw CocoaError(.fileWriteInvalidFileName) }
            let directory = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0]
                .appendingPathComponent("HighlightDiagnostic-\(run)", isDirectory: true)
            try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
            // Unique per process: never append to or truncate an earlier evidence file.
            let url = directory.appendingPathComponent("events-\(UUID().uuidString).jsonl")
            guard FileManager.default.createFile(atPath: url.path, contents: nil) else {
                throw CocoaError(.fileWriteUnknown)
            }
            sink = try FileHandle(forWritingTo: url)
            emit(["event": "recorder-open", "path": url.path,
                  "processID": ProcessInfo.processInfo.processIdentifier])
        } catch { fail(error) }
    }

    private func fail(_ error: Error) {
        failed = true
        let text = "[BoardHighlightDiagnostic] recorder failure: \(error)\n"
        try? FileHandle.standardError.write(contentsOf: Data(text.utf8))
    }

    private func emit(_ fields: [String: Any]) {
        guard enabled, !failed, let sink else { return }
        // Hard bound: the diagnostic never becomes an indefinite background logger.
        guard sequence < 4096 else { return }
        sequence += 1
        var value = fields
        value["sequence"] = sequence
        value["epoch"] = Date().timeIntervalSince1970
        value["uptime"] = ProcessInfo.processInfo.systemUptime
        value["complete"] = true
        if sequence == 4096 { value["eventLimitReached"] = true }
        do {
            var data = try JSONSerialization.data(withJSONObject: value, options: [.sortedKeys])
            data.append(0x0a)
            try sink.write(contentsOf: data)
            // Direct FileHandle writes bypass stdio buffering; synchronize at sparse markers.
            if fields["event"] as? String == "sample-end"
                || fields["event"] as? String == "view-disappear" || sequence == 4096 {
                try sink.synchronize()
            }
        } catch { fail(error) }
    }

    private func identity(_ object: AnyObject) -> String { String(describing: ObjectIdentifier(object)) }
    private func matrix(_ entity: Entity) -> [Float] {
        let m = entity.transform.matrix
        return [m.columns.0, m.columns.1, m.columns.2, m.columns.3]
            .flatMap { [$0.x, $0.y, $0.z, $0.w] }
    }

    func capture(_ event: String, scene: BoardModelRealityScene,
                 view: UUID? = nil, roots: [Entity]? = nil,
                 ids: Set<String>? = nil, mode: BoardHighlightMode? = nil,
                 priorIDs: Set<String>? = nil, priorMode: BoardHighlightMode? = nil) {
        guard enabled else { return }
        let key = scene.diagnosticLifecycleToken
        if let ids { requestedIDs[key] = ids }
        if let mode { requestedModes[key] = String(describing: mode) }
        let selected = requestedIDs[key] ?? []
        if let view, let roots, event == "view-make" || event == "view-update" {
            let signature = ([key.uuidString] + roots.map(identity) + [
                String(describing: matrix(scene.root)), String(describing: matrix(scene.camera)),
                requestedModes[key] ?? "unset", selected.sorted().joined(separator: ",")
            ]).joined(separator: "|")
            if event == "view-update", viewSignatures[view] == signature { return }
            viewSignatures[view] = signature
        }
        let surfaces: [[String: Any]] = selected.sorted().flatMap { id in
            (scene.contactEntities[id] ?? []).map { entity in
                var chain: [String] = []
                var parent: Entity? = entity
                var underRoot = false
                while let current = parent {
                    chain.append(identity(current))
                    if current === scene.root { underRoot = true }
                    parent = current.parent
                }
                var row: [String: Any] = ["contactID": id, "entityID": identity(entity),
                    "name": entity.name, "ancestors": chain, "underRegisteredRoot": underRoot,
                    "attached": entity.scene != nil, "enabled": entity.isEnabled,
                    "transform": matrix(entity)]
                if let material = entity.model?.materials.first {
                    row["materialType"] = String(describing: type(of: material))
                    if let pbr = material as? PhysicallyBasedMaterial {
                        var r: CGFloat = 0, g: CGFloat = 0, b: CGFloat = 0, a: CGFloat = 0
                        row["resolvedRGBAValid"] = pbr.baseColor.tint.getRed(&r, green: &g, blue: &b, alpha: &a)
                        row["rgba"] = [Double(r), Double(g), Double(b), Double(a)]
                    }
                }
                return row
            }
        }
        var row: [String: Any] = ["event": event, "sceneID": identity(scene),
            "sceneLifecycleToken": scene.diagnosticLifecycleToken.uuidString,
            "rootID": identity(scene.root), "cameraID": identity(scene.camera),
            "modelSHA256": scene.descriptorForTesting.modelSHA256,
            "selectedIDs": selected.sorted(), "requestedMode": requestedModes[key] ?? "unset",
            "cachedIDs": (scene.diagnosticSelection.0 ?? []).sorted(),
            "cachedMode": scene.diagnosticSelection.1.map { String(describing: $0) } ?? "unset",
            "rootAttached": scene.root.scene != nil, "rootEnabled": scene.root.isEnabled,
            "rootTransform": matrix(scene.root), "cameraTransform": matrix(scene.camera),
            "surfaces": surfaces]
        if let view { row["viewToken"] = view.uuidString }
        if let roots {
            row["contentRootIDs"] = roots.map(identity)
            row["contentContainsRegisteredRoot"] = roots.contains { $0 === scene.root }
        }
        if let priorIDs { row["priorCachedIDs"] = priorIDs.sorted() }
        if let priorMode { row["priorCachedMode"] = String(describing: priorMode) }
        emit(row)
    }

    func startSamples(view: UUID, scene: BoardModelRealityScene) {
        guard enabled, samplers[view] == nil else { return }
        samplers[view] = Task { @MainActor [weak scene] in
            for _ in 0..<120 {
                do { try await Task.sleep(for: .seconds(1)) }
                catch { return }
                guard !Task.isCancelled, let scene else { return }
                self.capture("sample", scene: scene, view: view)
            }
            if let scene { self.capture("sample-end", scene: scene, view: view) }
        }
    }

    func disappear(view: UUID, scene: BoardModelRealityScene) {
        guard enabled else { return }
        capture("view-disappear", scene: scene, view: view)
        samplers.removeValue(forKey: view)?.cancel()
        viewSignatures.removeValue(forKey: view)
    }
}
#endif
