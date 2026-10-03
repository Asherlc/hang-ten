    static let boardDetachTrial = isEnabled
        && ProcessInfo.processInfo.environment["HANGTEN_REVIEW_BOARD_DETACH_TRIAL"] == "1"
    private static let detachesTrainHost = boardDetachTrial
        && ProcessInfo.processInfo.environment["HANGTEN_REVIEW_DETACH_DISAPPEARING_BOARD_HOST"] == "1"
    @MainActor
    private final class TrialHost {
        let token = UUID()
        // Intentional diagnostic retention, identical in control and action arms.
        let model: BoardModelRealityScene
        let train: Bool
        weak var parent: Entity?
        weak var actualScene: RealityKit.Scene?
        var observed = false
        var disappeared = false
        var detached = false
        var invalid: String?
        init(model: BoardModelRealityScene, train: Bool) {
            self.model = model; self.train = train
        }
    }
    private var trialHosts: [ViewSceneKey: TrialHost] = [:]
    private var trialOwners: [UUID: UUID] = [:]

    /// One make per host key is supported in this diagnostic, with no reappearance.
    func allowsTrialHostCallback(scene: BoardModelRealityScene, view: UUID, make: Bool) -> Bool {
        guard Self.boardDetachTrial else { return true }
        let key = ViewSceneKey(scene: scene.diagnosticLifecycleToken, view: view)
        guard let host = trialHosts[key] else { return make }
        if make { host.invalid = "repeated-make" }
        return !make && !host.disappeared && host.invalid == nil
            && trialOwners[key.scene] == host.token
    }

    /// Called only after both content.add calls. Scene attachment may still be pending.
    func trialHostAdded(scene: BoardModelRealityScene, view: UUID, train: Bool) {
        guard Self.boardDetachTrial else { return }
        let key = ViewSceneKey(scene: scene.diagnosticLifecycleToken, view: view)
        guard trialHosts[key] == nil else { return }
        let host = TrialHost(model: scene, train: train)
        trialHosts[key] = host
        trialOwners[key.scene] = host.token
        observeTrialAttachment(scene: scene, view: view)
    }

    private func observeTrialAttachment(scene: BoardModelRealityScene, view: UUID) {
        guard Self.boardDetachTrial,
              let host = trialHosts[ViewSceneKey(scene: scene.diagnosticLifecycleToken, view: view)],
              trialOwners[scene.diagnosticLifecycleToken] == host.token,
              !host.disappeared, host.invalid == nil else { return }
        let root = scene.root, camera = scene.camera
        if host.observed {
            guard let parent = host.parent, let actual = host.actualScene,
                  root.parent === parent, camera.parent === parent,
                  root.scene === actual, camera.scene === actual else {
                host.invalid = "attachment-changed-before-disappear"; return
            }
        } else if let parent = root.parent, camera.parent === parent,
                  let actual = root.scene, camera.scene === actual {
            host.parent = parent; host.actualScene = actual; host.observed = true
        }
    }

    private func trialHostSnapshot() -> [[String: Any]] {
        trialHosts.keys.sorted { ($0.scene.uuidString + $0.view.uuidString)
            < ($1.scene.uuidString + $1.view.uuidString) }.map { key in
            let host = trialHosts[key]!
            let root = host.model.root, camera = host.model.camera
            return ["sceneLifecycleToken": key.scene.uuidString, "viewToken": key.view.uuidString,
                "ownerToken": host.token.uuidString, "trainMarked": host.train,
                "modelRetainedForTrial": true, "attachmentObserved": host.observed,
                "currentOwner": trialOwners[key.scene] == host.token,
                "disappeared": host.disappeared, "detached": host.detached,
                "invalid": host.invalid ?? "nil",
                "recordedParentID": host.parent.map(identity) ?? "nil",
                "recordedActualSceneID": host.actualScene.map(identity) ?? "nil",
                "rootParentID": root.parent.map(identity) ?? "nil",
                "cameraParentID": camera.parent.map(identity) ?? "nil",
                "rootActualSceneID": root.scene.map(identity) ?? "nil",
                "cameraActualSceneID": camera.scene.map(identity) ?? "nil",
                "reattachedAfterDetach": host.detached && (root.scene != nil || camera.scene != nil)]
        }
    }

    func trialHostDisappeared(scene: BoardModelRealityScene, view: UUID) {
        guard Self.boardDetachTrial else { return }
        let key = ViewSceneKey(scene: scene.diagnosticLifecycleToken, view: view)
        guard let host = trialHosts[key] else { return }
        // Last synchronous ownership observation; no suspension between guard and action.
        observeTrialAttachment(scene: scene, view: view)
        let alreadyDisappeared = host.disappeared
        host.disappeared = true
        capture("detach-trial-before", scene: scene, view: view)
        let root = scene.root, camera = scene.camera
        if Self.detachesTrainHost && host.train {
            if !alreadyDisappeared, host.invalid == nil, host.observed,
               host.model === scene, trialOwners[key.scene] == host.token,
               let parent = host.parent, let actual = host.actualScene,
               root.parent === parent, camera.parent === parent,
               root.scene === actual, camera.scene === actual {
                // Never remove the shared parent or touch another host's entities.
                root.removeFromParent()
                camera.removeFromParent()
                host.detached = root.scene == nil && camera.scene == nil
                if !host.detached { host.invalid = "detach-did-not-clear-scene-membership" }
            } else {
                host.invalid = host.invalid ?? "detach-ownership-guard-rejected"
            }
        }
        capture("detach-trial-after", scene: scene, view: view)
    }

