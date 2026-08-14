# Hang Ten

Hang Ten is a SwiftUI hangboard coach built around a simple promise: show the
athlete the exact holds to use, the intended grip and fingers, and the current
task without making them translate a paper routine while they train.

The first supported board is the Metolius Wood Grips Compact II. Its map is a
deterministic, textureless vector illustration based on Metolius's product
photography and hold-depth diagram. The same declared contact path renders a
hold cavity, its active red highlight, and its interaction area, so a highlight
cannot drift away from the hold.

## Included

- A reusable hangboard design language with normalized geometry, mirrored
  pairs, dimensional planes, recess depths, and exact-path highlights.
- An audited Compact II hold map covering its jugs, flat and round slopers,
  29/19 mm edges, and 2-, 3-, and 4-finger pockets.
- All three source-linked Metolius board-flexible ten-minute sequences: Entry,
  Intermediate, and Advanced, represented as faithful task-order expansions
  with adapted guided timing.
- Source-linked adapted protocols already merged into the project: Max Hangs,
  F80/F100 force-board sessions, Eva IntHangs, 7/3 Repeaters, Abrahangs,
  7–53 Max Hangs, 3–6–9 Ladders, Density Hangs, and Zlagboard 60/60.
- A runnable minute-by-minute session with pause/resume, direct step selection,
  skipping the current timed step, a spoken 3-2-1 start countdown, and final
  three-second countdown cues.
- Mirrored Phosphor hand cues for grip pose and participating fingers.
- Portrait and landscape workout layouts.
- An explicit Apple Health permission card. Completed sessions save as
  functional-strength workouts after authorization.
- A Motherboard Bluetooth sensor card for live force, calibration, tare, and
  threshold-based loaded-time recording. Its protocol is reverse-engineered;
  see [runtime-service notes](docs/IOS_RUNTIME_SERVICES.md) for its limits and
  physical-device validation requirements.
- A source-linked plan library and lightweight local session progress.

Runtime routine definitions are stored in
`HangTen/Resources/PlanLibrary.json`. `HangTen/Models/PlanStorage.swift`
decodes and validates that schema-versioned document; the source-audited seed
in `TrainingModels.swift` is its export fixture and DEBUG drift oracle. Board
and hold metadata lives in `Hangboards/catalog.json` and flat
`Hangboards/<board-folder>/` packages. The app loads the staged package bytes
from its resource bundle; no Swift board catalog is generated or hand-authored.

## Run

Open `HangTen.xcodeproj` in Xcode 26, or build from the repository root:

```sh
xcodebuild -project HangTen.xcodeproj \
  -scheme HangTen \
  -sdk iphonesimulator \
  -configuration Debug \
  -derivedDataPath .context/DerivedData \
  build
```

All Conductor/local-agent builds must use a workspace-local DerivedData path so
indexes and build output disappear with the workspace.

## Continuous integration and delivery

GitHub Actions runs the simulator Debug build and device Release build for
every pull request targeting `main` and every push to `main`. A successful
`main` run automatically archives the exact tested commit, signs it, and
uploads the IPA to App Store Connect/TestFlight.

The release workflow uses a GitHub environment named `app-store-connect`.
Configure that environment with no required reviewers for zero-touch delivery,
and restrict it to the `main` branch. Add these environment secrets:

- `APPSTORE_API_PRIVATE_KEY`: the App Store Connect API `.p8` private key.
- `APPSTORE_CERTIFICATES_FILE_BASE64`: a base64-encoded Apple Distribution
  `.p12` containing its private key.
- `APPSTORE_CERTIFICATES_PASSWORD`: the `.p12` password.

Add these environment variables:

- `APPLE_TEAM_ID`: the 10-character Apple Developer Team ID.
- `APPSTORE_API_KEY_ID`: the App Store Connect API key ID.
- `APPSTORE_ISSUER_ID`: the App Store Connect API issuer ID.

## PostHog CI configuration

The app runs without telemetry when its PostHog client token is absent. This is
intentional for local builds and untrusted fork pull requests. PostHog
credentials are not provisioned by this repository: after creating the new
Hang Ten PostHog project, an authorized maintainer must configure the following
to enable anonymous telemetry in trusted GitHub Actions builds:

- Repository secret `POSTHOG_CLIENT_TOKEN`: the Hang Ten PostHog public client
  project key (`phc_...`). Although it is a client-side key, retain it as a
  secret so it is not committed or exposed in workflow logs.
- Repository variable `POSTHOG_HOST`: the PostHog ingestion host. Use
  `https://us.i.posthog.com` unless the project is in another region.

The release workflow runs in the `app-store-connect` environment, whose
secrets and variables are scoped separately from the repository. After the
project exists, define the same `POSTHOG_CLIENT_TOKEN` environment secret and
`POSTHOG_HOST` environment variable there so the signed TestFlight archive
includes telemetry. The host defaults to `https://us.i.posthog.com` when the
variable is omitted; a missing token remains a safe no-op rather than failing
CI. The workflows place these values in a mode-`0600` temporary xcconfig, pass
only that file path to Xcode, and remove it when the job step exits so token
values are not interpolated into captured build logs.

The API key needs the Admin role for provisioning-profile access, and App Store
Connect must already contain an app record for `com.hangten.training` plus an
App Store provisioning profile for that bundle ID. The workflow assigns a
unique build number for each run and retry. Update `MARKETING_VERSION` in the
Xcode project when shipping a new App Store version.

This automates delivery to App Store Connect/TestFlight. Apple still controls
App Review and the final public App Store release decision.

In a parallel-agent environment, do not install to an arbitrary `booted`
simulator. Follow [the isolated simulator guide](docs/IOS_SIMULATOR_VALIDATION.md).

## Extension guides

- [Add a hangboard](docs/ADDING_A_BOARD.md)
- [Add a training routine](docs/ADDING_A_ROUTINE.md)
- [Validate in an isolated iOS Simulator](docs/IOS_SIMULATOR_VALIDATION.md)
- [Audio, orientation, and HealthKit](docs/IOS_RUNTIME_SERVICES.md)

The Hangboard Workbench owns direct package validation and editing. Check the
canonical board library with its focused test suite:

```sh
uv run --with pytest python -m pytest -q Tools/HangboardWorkbench/tests/test_board_package.py
```

The registry lists only complete source-backed packages with exactly an `id`
and flat `path`; Git branches are the in-progress mechanism. Unregistered
image candidates contain only `assets/primary.png` and are not app content.
The Xcode build phase runs `scripts/stage-board-packages.py`, which
bundles only registered packages and the registry into the app resource bundle.

Matching repo skills live under `.codex/skills/` and load these guides before
making changes.

Regenerate the bundled routine document after an audited plan change:

```sh
scripts/export-plan-library.sh
scripts/export-plan-library.sh --check
```

## Routine scope

Metolius publishes a generic ten-minute guide whose tasks name semantic hold
types such as “Round Sloper” and “Large Edge.” Hang Ten preserves those three
source sequences as ten 60-second cycles and resolves each named type to the
selected board's audited hold metadata. The app expands each cycle into
guided task and rest steps; when the source gives no duration, the app-defined
adaptation uses five seconds per pull-up and one second per other counted
repetition. Those timing defaults are app guidance, not Metolius prescriptions.

Metolius also publishes separate Contact and Simulator 3D guides. Those use
numbered holds tied to their respective boards, so they are intentionally not
presented as Compact II routines. Add each only after its physical board map is
implemented and its numbered holds can be resolved exactly.

The Metolius task expansions and the additional research and coach protocols
are visibly marked Adapted because
their app versions add guidance, warm-up/cooldown steps, or Compact II hold
mapping. Their individual source links remain attached; they are not presented
as unchanged manufacturer routines.

## Safety

Hangboard training can injure fingers, arms, and shoulders. Warm up thoroughly,
use a securely installed board, avoid overtraining, and stop if you feel pain.
Hang Ten is a timer and visual cue, not medical advice. Read the linked
manufacturer guidance before training.

## Sources and licenses

- [Metolius Wood Grips II product page](https://www.metoliusclimbing.com/collections/training-boards/products/wood-grips-ii-training-boards)
- [Metolius ten-minute hangboard guide](https://www.metoliusclimbing.com/pages/10-minute-sequences-hangboard-training-guide)
- [Metolius training-board manual](https://cdn.shopify.com/s/files/1/0955/0030/4457/files/Training-Board-instructions.pdf?v=1759261826)
- [Phosphor Icons](https://github.com/phosphor-icons/core), used under the MIT
  license; see `THIRD_PARTY_NOTICES.md`.
