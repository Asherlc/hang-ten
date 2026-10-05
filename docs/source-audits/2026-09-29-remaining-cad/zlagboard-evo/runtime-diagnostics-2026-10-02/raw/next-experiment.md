# Evo color refresh: next discriminating experiment

The retained 401b1084 diagnostic patch is ready for a full app build after the root's gate. The exact helper and representative RealityView hooks passed Swift 6 typechecking against the installed iPhoneSimulator27.0 SDK with iOS26 deployment. This checks SDK APIs, not the complete app dependency graph. The patch still applies cleanly without mutation.

## First run: unchanged real workout with observation only

Run the actual Evo workout, using the same bilateral outer-bottom contacts that fail across active/rest. Enable only HANGTEN_REVIEW_HIGHLIGHT_DIAGNOSTIC=1 and an owner-qualified HANGTEN_REVIEW_DIAGNOSTIC_RUN value. Keep orientation fixed for one complete active → rest → next-active sequence. Capture whole screenshots with host wallclock start AND end stamps. Copy the direct JSONL file from the app's Documents directory before termination. Existing 120-second samples must span every capture window; a sequence that starts after sample-end is not decisive.

Verify every JSONL line parses, sequence increases without gaps, no recorder error or event limit occurred, and both before/after snapshots surround each semantic write. Correlate scene lifecycle UUID, view UUID, content root ID, selected entity IDs and their ancestor chain. A pointer alone or attached=true is insufficient. Confirm the selected CPU tint in samples immediately before and after each screenshot's wallclock interval, and look for any intervening scene replacement or later write. Clock comparisons need bracketing; do not compare app uptime directly with host wallclock.

If actual callback input remains active while the UI says rest, the error is upstream of material mutation. If preview writes blue and another callback writes active/red before capture, trace the last writer and scene/view identity. If replacement or multiple roots occur, identify the visible scene before drawing a renderer conclusion. If the same registered scene and entities stay blue across a red screenshot, proceed to the second experiment below. If logging prevents reproduction, record it as timing-sensitive/inconclusive; do not keep the instrumentation as a fix.

## Second run only if persistent CPU/pixel disagreement is established

Use one held failing state in the actual workout, captured before pausing. Pause is an intervention that may invalidate SwiftUI and clear the issue, so retain before/after evidence. Do not replace the workout with the earlier hosted harness as the only reproducer.

Authorize a separate controlled DEBUG probe that directly disables the exact selected ModelEntity instances for two seconds, then restores their saved isEnabled values. Schedule it from an off-body task; do not change SwiftUI @State, cameraRevision, material, root identity or selection. Record probe start/end plus exact entity IDs and save whole screenshots before/during/after. This is a diagnostic mutation, absent from the current patch, and requires a separate root gate.

If selected geometry disappears while the visible tint had stayed stale, the renderer is responding to that entity while its material path is stale. If red geometry remains, wrong/duplicate visible entities or a stale drawable remains possible; it does not yet prove a material bug. A separate root-translation probe can determine whether any transform reaches the displayed scene; do not combine the two probes in the same first intervention. If either intervention causes blue to appear, it shows invalidation sensitivity but is not a production solution.

Only after identifying a material-specific failure compare a generated single PBR box to the imported contact in the same visible RealityView, followed by one PBR-versus-Unlit comparison if needed. Preserve the actual imported-model case. A generated-box-only success does not resolve the board failure.

## Boundaries

The four failed attempts (extra onChange writer, external single writer, @State bridge, whole ModelComponent assignment) are not proposed again. No production fix, CAD edit, runtime allocation, or source application occurred in this preparation. The current two-file patch is observation only and must be removed once diagnosis is complete.
