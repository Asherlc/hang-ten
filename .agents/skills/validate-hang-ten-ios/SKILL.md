---
name: validate-hang-ten-ios
description: Build, install, launch, and visually validate Hang Ten on an isolated iOS Simulator, including DEBUG review routes, landscape screenshots, spoken countdowns, and HealthKit permission wiring. Use after board, routine, workout, audio, orientation, or Apple Health changes, especially in parallel Paseo workspaces. For board or hold-shape changes, validate the geometry in FreeCAD, then the compiled plain USDZ, before the simulator.
---

# Validate Hang Ten iOS

Read `docs/IOS_SIMULATOR_VALIDATION.md` and
`docs/IOS_RUNTIME_SERVICES.md` completely before running validation.

## Workflow

1. Validate the geometry in FreeCAD first, before any simulator work. Author
   and compile the FCStd, then render it (front/side/top/isometric) and compare
   each view against the reference. Do not create a simulator until the FreeCAD
   render has been reviewed and accepted; the simulator only confirms how the
   same geometry presents in the app. `docs/freecad-authoring-migration.md` owns
   the author/compile/render inner loop.
2. Render the compiled plain USDZ next, independent of FreeCAD. After the
   compile publishes `assets/primary.usdz`, render that committed asset with the
   OpenUSD `usdrecord` CLI (Hydra Storm — not FreeCAD and not `preview.py`) in
   framed front / side / top / three-quarter views. This catches depth steps,
   through-holes, and silhouette issues the FreeCAD view can understate. Review
   these views before creating a simulator; see
   `docs/freecad-authoring-migration.md` ("Off-the-shelf Hydra render").
3. Capture `workspace_path="${PASEO_WORKTREE_PATH:-$PWD}"` and derive
   `workspace_name="${workspace_path:t}"` from its final path component, then
   create `.context`. Define `manifest="$workspace_path/.context/paseo-owned-simulators"`
   and `pending_manifest="$workspace_path/.context/paseo-pending-simulators"`.
   Install `EXIT`, `INT`, and `TERM` traps before any `simctl create`. The traps
   must call `scripts/paseo-resource-cleanup.sh archive` with
   `PASEO_WORKTREE_PATH` set to that path. Create a simulator named
   `Hang Ten Paseo $workspace_name Review`, validate the returned
   UUID, and append that exact UUID to the pending manifest before any owned
   manifest write, boot, or build. Only after the pending append succeeds append
   the UUID to the owned manifest. Keep the pending record until archive cleanup
   succeeds; archive must validate the exact workspace-name marker before
   shutting down/deleting and then consume both pending and owned records.
   If pending registration fails, retain the validated UUID in memory and permit
   direct deletion only as the last-resort trap fallback. Before that delete,
   re-query the exact UUID with `xcrun simctl list devices`, parse the matching
   record's name field, and require the exact prefix `Hang Ten Paseo $workspace_name` followed by a space;
   if lookup or ownership verification fails, do not
   delete and return failure. Use that UUID for every simulator operation; never
   target `booted`.
4. Wait for launch services, then build with the local workspace-specific
   `.context/DerivedData` path and explicit destination.
5. Keep signing enabled for HealthKit validation. Install the exact built app
   and confirm its app container when parallel builds share the bundle ID.
6. Use `SIMCTL_CHILD_HANGTEN_REVIEW_*` routes to reach the plan, workout step,
   grip, Health card, landscape layout, and automatic countdown deterministically.
7. Capture and orient screenshots. Inspect board geometry, highlight alignment,
   hand mirroring, text clipping, and timer continuity.
8. Exercise spoken 3-2-1 and task cues, audio-off behavior, rotation while
   running/paused, the user-triggered Health permission sheet, and workout save.
9. On success, failure, or interruption, the cleanup trap archives the exact
   pending and owned UUIDs after verifying the exact workspace marker, consuming
   the records only after successful cleanup. Do not delete shared or unknown
   simulators.

Every validation exit trap must also remove the exact workspace-local artifacts
created by its recipe (`.context/DerivedData`, `.context/workout-raw.png`, and
`.context/workout-landscape.png`). The trap removes those exact workspace
artifacts regardless of simulator cleanup status. If archive cleanup fails,
retain both pending and owned simulator manifests for a retry; preserve the
original command status and propagate cleanup failure only when the command
itself succeeded.

When practical, validate the pending-append failure path by forcing that append
to fail and verifying immediate status-1 exit without an owned-manifest write;
the EXIT trap must still use the validated in-memory UUID fallback.

Never purge `/Users/asherlc/Library/Developer/Xcode/DerivedData` from an agent
workflow. That one-time global purge is human-operator-only.

## Validation standard

Do not accept a successful compile as visual or runtime validation. For a board change, the FreeCAD render and then the compiled plain-USDZ (usdrecord) render are reviewed before the simulator run: report both render commands and the views compared, not only the simulator result. Report the
exact build command, simulator identity, states inspected, screenshots reviewed,
and any behavior that still requires a physical device.
