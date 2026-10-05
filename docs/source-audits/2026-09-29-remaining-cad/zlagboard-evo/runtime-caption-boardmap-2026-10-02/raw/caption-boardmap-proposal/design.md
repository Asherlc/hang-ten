# Caption and BoardMap boundary discriminator — unapplied proposal

Use one new diagnostic binary, existing exact Simulator/DD, same model and accepted package bytes. Run C, then D, then E only after preceding control/contrast review. No production fix is proposed.

- C: existing TimelineView monotonic phase derivation and changing caption, direct BoardModelSurface.
- D: same derivation and direct Surface; keep caption present, same font/modifiers, but constant text “Standalone board”. No new caption frame or layout modifier.
- E: same constant caption; existing unmodified BoardMapView replaces direct Surface. Request default presentation; active hold edge-20-left for selected phases, nil for clear. Surface must independently resolve the same presentation/position, IDs, mode and isDisplayOnly=false. No fallback or input tuning.

All arms retain 210×36 requested and actual leaf viewport; scripted clear/red/blue/red/blue, eight seconds per phase, four captures per phase at +0.25/+1/+3/+7. No touches, AX polling, timer label, remount, sampler, frame subscription or camera mutation. Task sets the epoch once before measurement and observes afterward. All inherited probe gates are stripped; only the existing standalone/diagnostic/landscape gates and selected driver are enabled.

The patch adds a sparse, initial+semantic-change observer at the actual Surface boundary. It writes only diagnostic records/non-observable recorder storage, independently from material mutation. Existing sparse application census now includes public UIKit bounds converted to window coordinates and object identities; ARView rows also identify their public RealityKit Scene, allowing correlation to the board root scene. It does not force layout, read pixels, create GeometryReaders or write SwiftUI state. All three arms receive identical instrumentation. Startup Surface observation can follow make: readiness/measurement snapshots must contain resolved inputs; absence is invalid evidence, not assumed equality.

Validity: one stable scene/make; active app/window; exact viewport; stable renderer placement per arm; resolved Surface input equality including neutral; no other renderer host. Caption width may differ between C and D by design, but a leaf position/size difference is a layout confounder to report. E wrapper animation/aspect-ratio/state is a bundle: any failure implicates that bundle only. Whole-image hashes cannot be compared to old caption/chrome as a visual oracle; inspect each final phase image individually.

Stop on invalid or failing C. If D fails, stop before E and request bounded confirmation. If only E fails, report wrapper boundary without guessing mechanism. If all pass, hand back for a fresh actual-workout same-binary comparison rather than adding isolated context. No repeat or normal-workout run is included in this application gate unless root authorizes it explicitly.

Existing capture/check scripts need only permit C/D/E labels and remove old same-caption hash oracle; actual timing and CPU bracket checks remain. Early snapshots may precede Timeline mutation; retain mechanical failures and judge timing truthfully, with +7 settled images decisive.

Only three reserved diagnostic Swift files appear in the patch. BoardMapView and all package/hand assets remain untouched. Patch applicability and Swift syntax parsing passed; typecheck/build/runtime have not run. Source/runtime ownership remains with root until an explicit gate.
