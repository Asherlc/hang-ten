# Batch 05 iOS acceptance

This audit binds actual iPhone Simulator captures to the six final USDZ packages.
The original dispatch base was `5a9ed0201e55cd1f1d664e5e2a8bd533d58bb20a`.
The separately reviewed, intervening Frictitious UV correction is
`de2478c1ba6e65c8364f01d646dc18aaec642616`; the native task diff starts there.
No geometry or source-material colors were changed by this native task.

## Evidence and coverage

`manifest.json` records each package's exact model/descriptor SHA-256, canonical
contact count, and each retained PNG's SHA-256. Filenames identify board and
state: `portrait-neutral`, `portrait-active`, `portrait-orbit`, `portrait-reset`,
`landscape-active`, and `landscape-neutral`. These are actual app screenshots,
not desktop renders. Train supplies the neutral state because Hold specs always
selects a contact. Material clearing is separately tested through the real native
scene API; no clear-selection UI was invented.

The six retained `Batch05BoardModelInteractionUITests` physically tap exposed
screen coordinates, change the initially selected contact, preserve selection
while orbiting, and tap a visible surface to reset. A reset must return every
contact's projected frame to its canonical position, within 0.5 screen points,
after the animation completes. Accessibility activation callbacks are not used
for selection proof. Forge's thin rail uses a reviewed interior point in its
actual orbit capture rather than an edge-on bounding-box center.

| Package | Canonical contacts | Physically tapped contact |
| --- | ---: | --- |
| DoorMount Pro 7 | 13 | edge-35-right |
| Megalith | 20 | center-edge-25 |
| Rock Prodigy Forge | 20 | variable-edge-rail-right |
| Rock Prodigy Natural | 14 | upper-pocket-right |
| Zlagboard.Evo | 21 | edge-35-center |
| Zlagboard.Pro 2.0 | 28 | edge-35-center |

All 116 canonical contacts and every native mesh piece are checked against the
real loader and exact reviewed descriptor bindings. For each piece, an exposed
sample must pass the closest body-inclusive segment and screen visibility hits,
plus the production contact-mask nearest screen hit, at one of nine review
angles. Separate checks cover material cloning/isolation, original material
identity on clear, non-pickable bodies, all positions, no transient cord,
portrait/landscape body bounds (including actual detail aspect ratios), and
camera reset preserving position. Projected bounds permit only 0.001-point
floating-point error; a Pro corner measured -0.00000749 points at a wide viewport.

## Defects found and corrected

Frictitious's missing UV attributes made the body and two Megalith ownership
meshes white in SceneKit. Native image-versus-color and body-only diagnostics
isolated missing UVs; the separate UV task supplied constant pixel-center UVs
on exactly four meshes. Exact original materials, texture pixels, geometry,
normals, contact bindings and mounting-hole omissions were preserved. The
retained native UV regression checks every Frictitious geometry node.

Orbit and pinch changed the camera while accessibility frames remained stale.
The finalized window-backed regression failed against the original renderer
with six assertions, then passed with the correction. The rendered camera's
model/presentation transforms, projection, orthographic scale and viewport now
invalidate accessibility projection only when changed; unchanged frames do not
recompute it, and the fix does not start continuous rendering. Animated reset
and resizing are included. Apple's
[container-space accessibility frame](https://developer.apple.com/documentation/uikit/uiaccessibilityelement/accessibilityframeincontainerspace)
and [projectPoint](https://developer.apple.com/documentation/scenekit/scnscenerenderer/projectpoint(_:))
documentation informed this correction.

The Train/picker cards applied a decorative 18-point rounded mask to models.
This erased the nearly square Zlag body corners, which initially looked like a
detail-view framing defect. Actual Evo body projections lay inside the full
334 × 57.333-point viewport and depth range; the approved E3/P3 source photos
confirmed the detail silhouette was correct. A real screenshot regression
failed on the original cream-colored masked corner and passed after restricting
the shared card mask to raster media. Model geometry, camera and detail layout
remain unchanged. Apple's [clipShape](https://developer.apple.com/documentation/swiftui/view/clipshape(_:style:))
documents that pixels outside the shape are removed. Fresh
[orthographic scale](https://developer.apple.com/documentation/scenekit/scncamera/orthographicscale),
[near](https://developer.apple.com/documentation/scenekit/scncamera/znear) and
[far](https://developer.apple.com/documentation/scenekit/scncamera/zfar) documentation
was checked while ruling out camera clipping.

The full Swift suite also caught a stale 33-model allowlist: one test method
failed six assertions. Adding the approved batch IDs corrected that inventory; the resulting 39-ID set was
compared exactly with the live catalog's model inventory.

## Source-backed omissions

The latest user instruction omits screw holes while retaining all six models
and grip cavities. Four larger Trango passages remain physical source-backed
features whose purpose is unresolved. They are not claimed conclusively
non-mounting. In the already approved packet, Forge F2's manufacturer CAD grip
chart retains the large IMR passage while omitting small mounting holes; F4
pages 4–5 and F5 establish eight small mounting screws/holes. Natural N2 pages
4–5 show six upper screws fitted while two lower passages remain open, and its
page 7 grip diagram retains those passages. No unsupported function was added.
The exact packet, URLs, and hashes remain in the parent audit evidence manifest.

## Validation and limitations

The controller accepted the six final models and all retained board capture
states. Final results and exact build/ODR/source/image hashes are recorded in
[`manifest.json`](manifest.json).

| Check | Result |
| --- | --- |
| Full package/model/staging/tool Python suite | 658 passed, 24 subtests passed |
| Full corrected Swift unit suite | 1,290 executed, 2 opt-in live StoreKit skips, 0 failures |
| Full UI suite | 34 passed; later Evo/Pro scoped checks passed after test-harness corrections |
| Signed simulator Debug and device Release compile | Passed; device Release signing disabled only for compilation |
| Actual built and installed ODR inspection | All six exact models in correct tagged packs; metadata/descriptor in base bundle; no base USDZ |
| Workflow actionlint | Passed |
| Catalog / cord / hard cut | 63 packages, 39 models; 31 excluded and 8 represented cords; six model-only packages and 116 contacts |
| Owned resource cleanup | Exact simulator absent, DerivedData removed, pending/owned UUID records consumed, four pytest temporary directories absent |

The full Swift run first exposed one stale-inventory test with six assertion
failures; the corrected full unit run passed. A later Pro reset check exhausted
its five-second budget during AX traversal, then passed with the same 0.5-point
checks and a 15-second budget. The full 34-test UI result predates that test-only
timeout adjustment; the focused Pro rerun verifies the final assertion.

Runtime smoke exercised initial countdown, visible hand/hold task cues, running
and paused rotation, background/resume, the speaker-off control, skip countdown,
completion, Save session, and persisted local History. The early landscape
running capture precedes hand-model readiness; the later portrait and paused
captures show the ready model. Numeric 3-2-1 scheduling was observed in real-app
logs; speaker output, spoken task-phrase intelligibility, and actual ducking or
silence are not certified by screenshots/logs. Existing full-suite countdown,
task-cue, audio cancellation and ducking-policy tests passed.

The actual user-triggered Health sheet requested workout read and write access.
A focused check enabled both through the real sheet and verified Connected
before and after relaunch (one test passed). The retained post-Allow screenshot
also shows `History synced from Apple Health.` A saved detailed local session
was independently present; that row alone is not treated as proof of a HealthKit
import. Physical-device record inspection/restoration remains outside this gate.

Temporary smoke attempts encountered test-driver assumptions: rest transitions
do not always count down, the speaker preference persists, XCTest reinstall
loses an unsaved modal, completion opens a summary sheet above Log session, and
this runtime exposes Turn On All as StaticText. The final Health-only check
resolved the last locator failure. These attempts are not reported as a passing
monolithic runtime suite, and none changed production workout/Health code.

The representative installed-copy missing/corrupt captures both show explicit
unavailable with no rendered fallback. Canonical and built assets were untouched;
a durable backup/finally restoration and subsequent signed reinstall were
verified against all six final model hashes. Existing loader/hash rejection
tests supply the native failure-path coverage. The QoS warning also occurs in
an unchanged existing SceneKit test; no performance improvement is claimed.
Bulk xcresults, diagnostic controls, and logs are workspace-local under
`.context/hangboards-batch-05-astra-migration`; they are not promised as committed
artifacts. One-off material/candidate diagnostics were removed from the shipping
test suite, with their source preserved locally for reproducibility.

This is simulator acceptance. It does not certify physical-device performance,
TestFlight-hosted ODR delivery, StoreKit live purchases, audible speaker/ducking
quality, or cross-device HealthKit restoration. No release/upload was requested.
The canonical-content Android gate is validated separately; its concrete result
is included in the final manifest rather than inferred from default PATH lookup.

### Cross-platform gate

Android staging, Debug lint (nine warnings, no errors), Debug APK assembly,
synthetic-client-ID Release AAB, and byte-for-byte canonical staging checks
passed. JVM tests ran 122 cases: 118 passed and four failed on pre-existing,
main-branch-identical code/fixtures. The Android reader accepts only schema 2,
while all 63 canonical packages already use schema 3 on main; replay fails first
on unchanged `aelith.cyclops-011`. Three fixture mutations also use indentation
that no longer matches after `trimIndent()`, making their exact-substring
replacements no-ops. Current Kotlin [trimIndent](https://kotlinlang.org/api/core/kotlin-stdlib/kotlin.text/trim-indent.html)
and [replace](https://kotlinlang.org/api/core/kotlin-stdlib/kotlin.text/replace.html)
documentation confirms these semantics.

The documented Android PR verification job is also absent from existing CI.
No Android implementation or workflow was changed in this native task. API 35
connected tests were not run: the image was absent, disk space was constrained,
and canonical decoding was already blocked. Android's [command-line test guide](https://developer.android.com/studio/test/command-line)
distinguishes those connected tests from local JVM tests. This audit therefore
does **not** claim all-repository or Android native acceptance. The separately
retained local `android-validation-report.md` records baseline identity proof,
commands, APK/AAB hashes, and exact owned SDK/cache/build cleanup.

### Task retrospective

Native preflight found a real exporter defect that desktop renders missed:
missing UVs on rebuilt meshes. Isolating the original embedded texture from
runtime lighting avoided a global color/lighting workaround. Physical taps,
body-inclusive visibility checks and review of actual screenshots also caught
stale accessibility projections, a decorative silhouette mask, and an initially
missed Forge reset. Each production correction retained a meaningful RED/GREEN
regression; package geometry corrections remained with the separate UV task.

The final reset assertion checks every contact, because a top-edge center alone
can move less than two points during a visibly wrong orbit. Its waiter allows
15 seconds for cross-process traversal of 28 accessibility targets; tolerances
remain 0.5 points. Temporary workout drivers must initialize persisted speaker
settings and distinguish work-to-rest transitions from countdown transitions.
AXe's empty application tree was not treated as proof of loader failure: actual
missing/corrupt screenshots and the native loader tests supplied that evidence.
For the next batch, run actual iOS material and interaction preflight before
large screenshot collection, and check the full current catalog inventory early.
