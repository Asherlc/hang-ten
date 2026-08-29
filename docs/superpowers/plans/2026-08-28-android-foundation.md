# Hang Ten Android Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a native Android Hang Ten coach that consumes the canonical repository content and ships with tested, production-ready CI/CD.

**Architecture:** `Android/` is an independent Kotlin/Compose Gradle project. Its domain layer decodes repository-owned JSON assets, view models own all state and monotonic workout timing, and Compose draws canonical hold geometry. GitHub Actions executes Android quality gates and conditionally publishes signed AABs from a protected environment.

**Tech Stack:** Kotlin, Jetpack Compose, AndroidX Lifecycle/DataStore/Test, kotlinx.serialization, Gradle, GitHub Actions, Google Play Publisher.

**Spec:** `docs/superpowers/specs/2026-08-28-android-foundation-design.md`

## Global Constraints

- Support Android 10 / API 29 and later; compile and test against API 35.
- Read board packages, plans, and reviewed audio from the existing repository sources; do not commit duplicate Android copies of source content.
- A hold's decoded canonical geometry is the only source for its rendering, highlight, and hit testing.
- Use monotonic elapsed time for sessions; backgrounding pauses and cancels audio, and resume is explicit.
- Do not request Bluetooth, health, billing, or account permissions in this milestone.
- All production behavior is introduced test-first. Configuration-only changes use Gradle/lint/build validation rather than source-text regression tests.
- CI never emits credentials; release publishing requires the protected `google-play` environment.

---

### Task 1: Bootstrap the Android Gradle project and source staging

**Files:**
- Create: `Android/settings.gradle.kts`, `Android/build.gradle.kts`, `Android/gradle.properties`, `Android/app/build.gradle.kts`, `Android/app/proguard-rules.pro`
- Create: `Android/app/src/main/AndroidManifest.xml`, `Android/app/src/main/java/com/hangten/android/MainActivity.kt`
- Create: `Android/app/src/test/java/com/hangten/android/AssetStagingTest.kt`
- Create: `Android/gradlew`, `Android/gradlew.bat`, `Android/gradle/wrapper/gradle-wrapper.properties`
- Modify: `.gitignore`

**Interfaces:**
- Produces Gradle task `:app:stageCanonicalAssets` that copies `Hangboards/`, `HangTen/Resources/PlanLibrary.json`, and `HangTen/Resources/CountdownAudio/` to `build/generated/assets/canonical` and is a dependency of asset processing.
- Produces package ID `com.hangten.training` and launch activity `MainActivity`.

- [ ] **Step 1: Write the failing staging test**

```kotlin
@Test fun stagedAssetsContainPlanAndEveryBoardManifest() {
    val root = File("build/generated/assets/canonical")
    assertTrue(File(root, "PlanLibrary.json").isFile)
    assertTrue(File(root, "Hangboards").listFiles().orEmpty().all { File(it, "board.json").isFile })
}
```

- [ ] **Step 2: Run it to verify it fails**

Run: `rtk ./Android/gradlew -p Android :app:testDebugUnitTest --tests com.hangten.android.AssetStagingTest`

Expected: FAIL because no Android Gradle project or staging task exists.

- [ ] **Step 3: Create the minimal Android application and staging task**

```kotlin
val stageCanonicalAssets by tasks.registering(Copy::class) {
    from(rootProject.projectDir.parentFile.resolve("Hangboards")) { into("Hangboards") }
    from(rootProject.projectDir.parentFile.resolve("HangTen/Resources/PlanLibrary.json"))
    from(rootProject.projectDir.parentFile.resolve("HangTen/Resources/CountdownAudio")) { into("CountdownAudio") }
    into(layout.buildDirectory.dir("generated/assets/canonical"))
}
android.sourceSets.getByName("main").assets.srcDir(stageCanonicalAssets)
tasks.named("preBuild").configure { dependsOn(stageCanonicalAssets) }
```

Use Kotlin/JVM 17, Compose BOM, `minSdk = 29`, `targetSdk = 35`, and a Debug activity that displays `Hang Ten Android`.

- [ ] **Step 4: Run the staging test and Debug build**

Run: `rtk ./Android/gradlew -p Android :app:testDebugUnitTest :app:assembleDebug`

Expected: PASS and `Android/app/build/outputs/apk/debug/app-debug.apk` exists.

- [ ] **Step 5: Commit**

```bash
rtk git add Android .gitignore
rtk git commit -m "Add Android application foundation"
```

### Task 2: Decode portable board and plan content

**Files:**
- Create: `Android/app/src/main/java/com/hangten/android/content/BoardModels.kt`, `BoardRepository.kt`, `PlanModels.kt`, `PlanRepository.kt`
- Create: `Android/app/src/test/java/com/hangten/android/content/BoardRepositoryTest.kt`, `PlanRepositoryTest.kt`

**Interfaces:**
- Produces `BoardRepository.loadBoards(): Result<List<Board>>` and `PlanRepository.loadPlans(): Result<List<TrainingPlan>>`.
- `BoardHold.geometry` contains normalized frame plus either `RoundedRectShape` or ordered `PathCommand` values.
- Repositories reject malformed JSON and missing presentation assets with a descriptive failure.

- [ ] **Step 1: Write failing decoder tests**

```kotlin
@Test fun decodesAPathHoldAndAConstrainedRoundedRectangle() { /* fixtures assert IDs and shapes */ }
@Test fun rejectsBoardWhosePresentationAssetIsAbsent() { /* assert failure */ }
@Test fun decodesPlanStepsInDeclaredOrder() { /* assert first two step IDs */ }
```

- [ ] **Step 2: Verify red**

Run: `rtk ./Android/gradlew -p Android :app:testDebugUnitTest --tests '*RepositoryTest'`

Expected: FAIL because repositories and models do not exist.

- [ ] **Step 3: Implement fail-closed serializable models and asset repositories**

```kotlin
sealed interface HoldShape { data class RoundedRect(val cornerRadiusFraction: Float) : HoldShape; data class Path(val commands: List<PathCommand>) : HoldShape }
data class BoardGeometry(val frame: NormalizedFrame, val shape: HoldShape)
interface BoardRepository { fun loadBoards(): Result<List<Board>> }
```

Validate finite normalized frames, nonempty IDs, supported commands, closed paths beginning with `move`, and each `assetPath` before returning a board. Preserve plan instructions/accessory text exactly as decoded.

- [ ] **Step 4: Verify green**

Run: `rtk ./Android/gradlew -p Android :app:testDebugUnitTest --tests '*RepositoryTest'`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
rtk git add Android/app/src
rtk git commit -m "Decode canonical Android coach content"
```

### Task 3: Implement exact board geometry rendering and targeting

**Files:**
- Create: `Android/app/src/main/java/com/hangten/android/board/BoardCanvas.kt`, `HoldTargetResolver.kt`
- Create: `Android/app/src/test/java/com/hangten/android/board/HoldTargetResolverTest.kt`, `BoardPathTest.kt`
- Create: `Android/app/src/androidTest/java/com/hangten/android/board/BoardCanvasTest.kt`

**Interfaces:**
- Produces `resolveTargets(targets: List<HoldTarget>, board: Board): Set<String>` and composable `BoardCanvas(board, activeHoldIDs, onHoldTap)`.
- `BoardCanvas` maps geometry frames and path commands to one transformed Android `Path` for drawing and hit tests.

- [ ] **Step 1: Write failing target and geometry tests**

```kotlin
@Test fun semanticJugTargetResolvesOnlyJugsOnSelectedBoard() { /* expected hold IDs */ }
@Test fun boardPathClosesAtItsStartingPoint() { /* Path conversion assertion */ }
```

- [ ] **Step 2: Verify red**

Run: `rtk ./Android/gradlew -p Android :app:testDebugUnitTest --tests '*board*Test'`

Expected: FAIL because resolver and path conversion do not exist.

- [ ] **Step 3: Implement resolver and Canvas path transformation**

```kotlin
fun resolveTargets(targets: List<HoldTarget>, board: Board): Set<String> = board.holds
    .filter { hold -> targets.any { it.matches(hold) } }
    .mapTo(linkedSetOf()) { it.id }
```

Draw the image inside aspect-ratio bounds, map each normalized frame into that rectangle, draw `roundedRect`, `moveTo`, `lineTo`, `quadraticBezierTo`, `cubicTo`, and `close`, then use `Path.contains` for tap handling. Apply no inferred paths or board-specific coordinates.

- [ ] **Step 4: Verify green on JVM and emulator**

Run: `rtk ./Android/gradlew -p Android :app:testDebugUnitTest connectedDebugAndroidTest`

Expected: PASS; Compose test asserts a selected semantic target is exposed as active UI semantics.

- [ ] **Step 5: Commit**

```bash
rtk git add Android/app/src
rtk git commit -m "Render canonical Android board geometry"
```

### Task 4: Build the monotonic workout session and local history

**Files:**
- Create: `Android/app/src/main/java/com/hangten/android/workout/WorkoutSession.kt`, `WorkoutViewModel.kt`, `SessionHistoryRepository.kt`
- Create: `Android/app/src/test/java/com/hangten/android/workout/WorkoutSessionTest.kt`, `SessionHistoryRepositoryTest.kt`

**Interfaces:**
- Produces `WorkoutSession.start(nowMs)`, `pause(nowMs)`, `resume(nowMs)`, `snapshot(nowMs)`, `complete(nowMs)` and `SessionHistoryRepository.record(CompletedSession)`.
- Time source is `( ) -> Long` from `SystemClock.elapsedRealtime`; persisted history stores wall-clock completion separately from elapsed duration.

- [ ] **Step 1: Write failing clock and persistence tests**

```kotlin
@Test fun pauseFreezesTheActiveStepUntilExplicitResume() { /* start, pause, advance, assert unchanged */ }
@Test fun startCountdownPrecedesFirstRoutineStepByThreeSeconds() { /* snapshot assertions */ }
@Test fun completedSessionIsRestoredFromDataStore() = runTest { /* persist then reload */ }
```

- [ ] **Step 2: Verify red**

Run: `rtk ./Android/gradlew -p Android :app:testDebugUnitTest --tests '*workout*Test'`

Expected: FAIL because session and history classes do not exist.

- [ ] **Step 3: Implement state machine and DataStore history**

```kotlin
sealed interface SessionPhase { data object StartCountdown : SessionPhase; data class Active(val stepIndex: Int) : SessionPhase; data object Paused : SessionPhase; data object Complete : SessionPhase }
```

Use only elapsed-realtime differences to advance phases. Clamp elapsed progress to the total plan duration. `onStop` in the view model pauses running sessions and invokes the audio cancellation interface. Keep the twenty newest completed entries.

- [ ] **Step 4: Verify green**

Run: `rtk ./Android/gradlew -p Android :app:testDebugUnitTest --tests '*workout*Test' --tests '*SessionHistory*Test'`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
rtk git add Android/app/src
rtk git commit -m "Add Android workout timing and history"
```

### Task 5: Deliver the Compose coach experience and audio adapters

**Files:**
- Create: `Android/app/src/main/java/com/hangten/android/ui/HangTenApp.kt`, `TrainScreen.kt`, `PlansScreen.kt`, `HistoryScreen.kt`, `WorkoutScreen.kt`, `SettingsScreen.kt`
- Create: `Android/app/src/main/java/com/hangten/android/audio/WorkoutAudioCoach.kt`, `AndroidWorkoutAudioCoach.kt`
- Create: `Android/app/src/androidTest/java/com/hangten/android/ui/HangTenNavigationTest.kt`, `WorkoutScreenTest.kt`

**Interfaces:**
- `HangTenApp` owns bottom navigation and injects content/history/audio dependencies.
- `WorkoutAudioCoach.scheduleCountdown(startElapsedMs: Long)` and `cancel()` are called from workout lifecycle code; failure is nonfatal.

- [ ] **Step 1: Write failing navigation and session UI tests**

```kotlin
@Test fun athleteCanSelectBoardPlanAndStartWorkout() { /* navigate Plans -> select -> Train -> start */ }
@Test fun workoutScreenShowsActiveTaskAndPauseControl() { /* semantics assertions */ }
```

- [ ] **Step 2: Verify red**

Run: `rtk ./Android/gradlew -p Android :app:connectedDebugAndroidTest`

Expected: FAIL because the app navigation and screens do not exist.

- [ ] **Step 3: Implement responsive screens, settings, and audio**

```kotlin
NavigationBar { listOf(Train, Plans, History).forEach { destination -> NavigationBarItem(...) } }
```

Use responsive row/column placement based on available width. The audio adapter plays reviewed numeric assets at timeline boundaries and uses `TextToSpeech` for instructions only when enabled in DataStore. Add semantics labels for current task, active board holds, pause/resume, and end session.

- [ ] **Step 4: Verify green and package the app**

Run: `rtk ./Android/gradlew -p Android :app:lintDebug :app:connectedDebugAndroidTest :app:assembleDebug`

Expected: PASS with a lint-clean Debug APK.

- [ ] **Step 5: Commit**

```bash
rtk git add Android/app/src
rtk git commit -m "Add Android coaching experience"
```

### Task 6: Add Android CI/CD, release handoff, and project documentation

**Files:**
- Modify: `.github/ci-paths.yml`, `.github/workflows/ci.yml`, `README.md`
- Create: `.github/workflows/android-release.yml`, `docs/ANDROID_RELEASE.md`

**Interfaces:**
- CI adds required check `Android verification` for Android, shared content, and workflow changes.
- Release consumes `ANDROID_UPLOAD_KEYSTORE_BASE64`, `ANDROID_UPLOAD_KEYSTORE_PASSWORD`, `ANDROID_UPLOAD_KEY_ALIAS`, `ANDROID_UPLOAD_KEY_PASSWORD`, `GOOGLE_PLAY_SERVICE_ACCOUNT_JSON`, and `GOOGLE_PLAY_PACKAGE_NAME` only from `google-play` environment.

- [ ] **Step 1: Add Android path classification and a failing workflow validation command**

```yaml
android:
  - 'Android/**'
  - 'Hangboards/**'
  - 'HangTen/Resources/PlanLibrary.json'
  - 'HangTen/Resources/CountdownAudio/**'
```

Validate local workflow syntax with `actionlint`; initially this should fail because the Android jobs are not defined.

- [ ] **Step 2: Add Android CI jobs**

```yaml
- run: ./Android/gradlew -p Android :app:stageCanonicalAssets :app:testDebugUnitTest :app:lintDebug :app:assembleDebug
- uses: reactivecircus/android-emulator-runner@<pinned-commit>
  with:
    api-level: 35
    script: ./Android/gradlew -p Android :app:connectedDebugAndroidTest
```

Pin every third-party action to a full commit SHA. Cache Gradle by wrapper and build-script hashes, upload Debug APK plus test/lint reports, and make the stable Android required check report skipped-path success rather than leave branch protection pending.

- [ ] **Step 3: Add guarded Play release workflow**

```yaml
environment: google-play
if: github.event_name == 'push' && github.ref == 'refs/heads/main'
```

Decode the keystore with `umask 077` to `$RUNNER_TEMP`, generate a temporary signing properties file, build `:app:bundleRelease`, and upload via a pinned Google Play Publisher action to `internal`. Assert every required secret/variable is nonempty before use, delete temporary files in an `EXIT` trap, and upload the AAB as a workflow artifact.

- [ ] **Step 4: Document local, CI, and Play Console operations**

Document Android Studio/SDK prerequisites, `rtk ./Android/gradlew -p Android check`, emulator test command, artifact locations, protected environment setup, exact secret names, Play Console app/service-account/key creation, and the fact that the release workflow cannot publish until an operator supplies those credentials.

- [ ] **Step 5: Verify configuration and project quality**

Run: `rtk actionlint .github/workflows/ci.yml .github/workflows/android-release.yml && rtk ./Android/gradlew -p Android :app:stageCanonicalAssets :app:testDebugUnitTest :app:lintDebug :app:assembleDebug`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
rtk git add .github README.md docs/ANDROID_RELEASE.md
rtk git commit -m "Add Android CI and Play release delivery"
```
