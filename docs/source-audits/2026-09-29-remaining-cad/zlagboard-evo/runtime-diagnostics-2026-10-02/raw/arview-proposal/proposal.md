# Controlled non-AR ARView host probe (proposal only)

## Question and boundary

The corrected same-binary hands ON/OFF/ON experiment is fail/pass/fail. Explicit virtual camera in the board RealityView did not resolve the hands-ON failure. Test whether hosting the existing board scene in a UIKit ARView eliminates the mismatch while the hand RealityView remains present. This isolates the hosting integration; it does not prove which internal framework mechanism is wrong.

Modify only reserved BoardModelView.swift, under DEBUG, selected at launch by HANGTEN_REVIEW_BOARD_ARVIEW_HOST=1. Retain the current RealityView branch exactly as the control. Keep hands ON and do not combine this with the hand-suppression environment. Keep camera-virtual environment unset for the first ARView/control comparison, recording that distinction: ARView explicitly nonAR is part of the new host contract. No imported asset, material assignment, contact binding, model scene class, timer, or hold selection changes. Do not silently clone the scene into the second host.

## UIViewRepresentable and attachment ownership

A private DEBUG UIViewRepresentable receives the same BoardModelRealityScene reference, GeometryReader size, current applySync closure and picking callback. Make a single ARView(frame:.zero,cameraMode:.nonAR,automaticallyConfigureSession:false). Never call session.run. Give its coordinator one identity-transform AnchorEntity(world:.zero); put the exact model.root and exact model.camera beneath it as siblings, then add that anchor to arView.scene. No other anchor/camera, mesh clone, recentering, scaling or camera transform is introduced. Identity anchoring preserves the native scene/world coordinates expected by framing and projectedContactCenter.

The existing .id(ObjectIdentifier(model)) must encompass the selected host. The coordinator owns only this host's anchor and reference to the current scene; UIKit/SwiftUI own the view. On dismantle record the final membership first, cancel only the existing (sceneLifecycleUUID,viewUUID) sampler, and remove only this coordinator's anchor. Detach root/camera only if each still has this exact anchor as parent, so a late dismantle cannot detach a replacement host's entities. Never broadly remove anchors or pause any shared session. Do not swap host types while a run is in progress: separate launches provide the control and intervention.

## Camera and appearance

Reuse the exact PerspectiveCamera already on BoardModelRealityScene. Existing applySync still sets vertical FOV30 (or unchanged review override), near0.001, far1000 and the existing camera transform. ARView nonAR uses a PerspectiveCamera according to Apple docs; no synthetic default camera or orthographic substitute is needed. Set isOpaque=false, backgroundColor=.clear, environment.background=.color(.clear) on the ARView. This transparency configuration needs an actual whole-screen check; do not assume it is visually equivalent merely because it compiles. Do not add lights, alter PBR/CustomMaterial, change exposure or tone mapping, or add renderOptions for this first diagnostic. ARView and RealityView may have different default lighting/compositing; note any appearance difference separately from red/blue refresh.

## Synchronization

makeUIView attaches the scene, calls the existing applySync once with GeometryReader size, then records make and starts the existing weak sampler. updateUIView refreshes the coordinator's stored current closure/inputs before calling that same applySync and recording an update. All runs on MainActor. Pass current highlighted IDs/mode/position as representable stored values so the same SwiftUI inputs reach this branch; do not add a Timer, display link, scene-update subscription, repeated material writes or force redraw. Do not call applySync from layoutSubviews: that would introduce a second writer and extra invalidations. Preserve the existing cameraRevision scheduling rather than inventing a replacement bridge. This changes the host callback mechanism by necessity; a pass identifies the host integration boundary, not a single SDK defect.

## Gestures, picking and accessibility

Reuse the outer SwiftUI drag and magnification gestures and the existing accessibility overlay/layout; these operate on the same scene and geometry. The RealityView SpatialTapGesture.targetedToAnyEntity cannot be presumed to work through a UIViewRepresentable. For a complete diagnostic host, a coordinator UITapGestureRecognizer can ask arView.entity(at:recognizer.location(in:arView)), pass the nearest collidable entity through model.contactID(for:), and call the existing reset-camera/selection closure. Apple documents entity(at:) as ignoring entities without CollisionComponent; retain the current actual contact collision components and do not generate body collisions. Configure tap behavior to avoid swallowing outer pan/pinch; do not install RealityKit entity-transform gestures. Preserve allowsHitTesting(!isDisplayOnly).

For the first workout experiment, onContactTap is normally nil and no orbit/tap intervention is required. A color-refresh pass would NOT validate production picking, zoom, reset, accessibility, or interaction arbitration. These need separate exact-contact tests before adopting the host in production. Camera framing/transparent background must be checked even in the first workout.

## Diagnostic membership (avoid misleading roots)

The ARView scene's actual top-level anchor is the attachmentAnchor, unlike the direct root/camera entries in RealityViewContent. Do not pass a fabricated [model.root,model.camera] array to the logger and call that a host-membership test.

At AR make/update, verify the owned anchor is actually in arView.scene.anchors, root.parent and camera.parent are that exact anchor, and root.scene/camera.scene match arView.scene. Record host UUID, ARView identity, actual scene identity, anchor identity, root/camera IDs, anchor presence and these equality results in a small separate direct-JSONL host-association record implemented locally in BoardModelView.swift. Its path/run must use the existing owner-qualified diagnostic run. A static one-time association map alone is insufficient if later host replacement is suspected; emit on make, semantic update and dismantle. No new observed state.

The existing recorder can still snapshot the exact same scene and contacts and run its weak sampler. Supply roots from actual anchor.children only when the owned anchor is present; document that for this probe contentRootIDs denotes owned anchor children, not ARView.scene.anchors. The contact ancestor chain must contain both the registered model.root and recorded attachmentAnchor IDs. Host-association records bridge that ancestry to the actual ARView scene. Alternatively allow a tiny optional host-fields extension to the existing recorder, but that would exceed the current BoardModelView-only probe scope and needs explicit coordination.

## Experiment and decision

One binary, hands ON, launch control RealityView then ARView then control RealityView. Use the existing workout and actual Skip action; no duration changes. Capture first active, settled rest, next active with whole screenshots and host time brackets; retain complete JSONL and the installed Mach-O/package parity as before. Inspect each critical image individually with SHA. CPU material must remain correct across screenshots in all variants. If ARView passes and control reverses to fail, adopt no production change yet: it supports replacing board hosting as a remedy and merits focused interactivity/lifecycle tests. If both fail, stop host replacement and use the previously proposed exact-entity visibility probe to distinguish stale drawable from another visible entity. If framing/background differs, record it as a host difference rather than altering geometry to compensate.

## Primary API references

- https://developer.apple.com/documentation/realitykit/arview
- https://developer.apple.com/documentation/realitykit/arview/cameramode-swift.enum/nonar
- https://developer.apple.com/documentation/realitykit/perspectivecamera
- https://developer.apple.com/documentation/realitykit/arview/entity(at:)
- https://developer.apple.com/documentation/realitykit/arview/environment-swift.struct/background-swift.struct/color(_:)

Apple Markdown copies are retained alongside this proposal. Web-tool Markdown fetches returned unsupported-content-type; direct official Markdown downloads succeeded. No implementation, SDK typecheck of this proposed host, build, install, UI operation or resource cleanup occurred during proposal preparation.
