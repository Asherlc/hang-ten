# Hang Ten

Hang Ten is a SwiftUI hangboard coach built around a simple promise: show the
athlete the exact holds to use, the intended grip and fingers, and the current
task without making them translate a paper routine while they train.

Each supported board is a complete flat package containing its presentation PNG
and directly authored canonical hold paths. The same saved path renders the
normal contact, active highlight, and interaction area, so a highlight cannot
drift away from its physical hold.

## Included

- Audited flat board packages with normalized, manually authored geometry,
  exact mirroring where the physical product is symmetric, and exact-path
  highlights.
- Source-backed physical inventories that omit unsupported optional metadata.
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
identity, conservative hold metadata, and canonical geometry live in directly
discovered `Hangboards/<board-folder>/board.json` packages alongside
`assets/primary.png`. The app loads validated package bytes without rewriting
geometry or maintaining another geometry source.

## Run

Open `HangTen.xcodeproj` in Xcode 26, or build from the repository root:

```sh
rtk xcodebuild -project HangTen.xcodeproj \
  -scheme HangTen \
  -sdk iphonesimulator \
  -configuration Debug \
  -derivedDataPath .context/DerivedData \
  build
```

All Paseo/local-agent builds must use a workspace-local DerivedData path so
indexes and build output disappear with the workspace.

## Lifetime unlock StoreKit setup

The shared Hang Ten scheme uses
`HangTen/Resources/HangTen.storekit` for local Run and Test actions. It defines
`com.hangten.training.lifetime` as a non-consumable with a $2.99 USD test price.
In Xcode, run the app on an isolated simulator, save two free workouts, start a
third routine, and use **Debug > StoreKit > Manage Transactions** to inspect,
refund, or delete the local purchase. Verify both **Unlock for $2.99** and
**Restore Purchases** transition the retained routine into Session; deleting
the local transaction should make the paywall appear again.

The real StoreKit integration tests are opt-in because Xcode 26.6 command-line
test processes can fail to sync a local StoreKit configuration to StoreKit's
test service. Run them only after Xcode has opened this project and successfully
run the shared **HangTen** scheme with `HangTen.storekit` active:

```sh
HANGTEN_RUN_STOREKIT_LIVE_TESTS=1 rtk xcodebuild test \
  -project HangTen.xcodeproj \
  -scheme HangTen \
  -destination 'platform=iOS Simulator,id=<isolated-simulator-uuid>' \
  -derivedDataPath .context/DerivedData \
  -only-testing:HangTenTests/LiveStoreKitConfigurationTests
```

For IDE execution, add `HANGTEN_RUN_STOREKIT_LIVE_TESTS=1` to the Test action's
environment variables and use **Product > Test**. Before release, also validate
purchase and Restore Purchases on a signed build using a Sandbox Apple Account;
the local configuration is not a substitute for Sandbox validation.

Before App Store distribution, an authorized App Store Connect operator must
create a non-consumable for the existing `com.hangten.training` app with product
ID `com.hangten.training.lifetime`, reference name **Hang Ten Lifetime Unlock**,
and the $2.99 price tier. Add the product to the release, complete its required
localization and review metadata, then use a Sandbox Apple Account to exercise
purchase and Restore Purchases on a signed build. The product has not been
created by this repository change; App Store Connect and Sandbox setup are an
external release handoff.

## GitHub Device Flow release setup

Before distributing a build with board-package GitHub sync, enable Device Flow
in the existing GitHub OAuth App. Add its public client ID as the
`HANGTEN_GITHUB_OAUTH_CLIENT_ID` variable in the `app-store-connect` GitHub
Actions environment (a repository variable with the same name may also supply
trusted non-release workflows). GitHub reserves the `GITHUB_` prefix for its
own configuration-variable names, so the release job maps that value to the
iOS `GITHUB_OAUTH_CLIENT_ID` build setting. It writes the setting to its
temporary mode-`0600` xcconfig and verifies that the archived app's Info.plist
contains a nonempty client ID.

For local Xcode builds, copy `HangTen/Config/Analytics.local.xcconfig.example` to
the ignored `HangTen/Config/Analytics.local.xcconfig` file and set
`GITHUB_OAUTH_CLIENT_ID` there. Do not create a `GITHUB_CLIENT_SECRET` iOS app
build setting, `app-store-connect` Actions secret, or bundled Info.plist key:
Device Flow uses only the public client ID. Keep the public
`GITHUB_OAUTH_CLIENT_ID` in the iOS app's Info.plist. This iOS-only restriction
does not apply to the browser-hosted Workbench, whose server-side OAuth flow
retains its separately hosted `GITHUB_CLIENT_SECRET` configuration. The app
requests `repo read:org` and no longer accepts personal access tokens.

## Maintainer-generated countdown audio

Hang Ten ships reviewed audio files and never stores an ElevenLabs API key or
makes ElevenLabs requests at runtime. An authorized maintainer can generate a
local countdown pack with the developer-only script described in
[`HangTen/Resources/CountdownAudio/README.md`](HangTen/Resources/CountdownAudio/README.md).
Review and explicitly commit the generated files before they can ship.

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
- `HANGTEN_GITHUB_OAUTH_CLIENT_ID`: the existing GitHub OAuth App's public
  client ID; its Device Flow option must be enabled. The workflow maps it to
  the app's `GITHUB_OAUTH_CLIENT_ID` build setting. Do not configure a client
  secret.
## Analytics CI configuration

The app runs without analytics when its API key is absent. This is intentional
for local builds and untrusted fork pull requests. Analytics credentials are
not provisioned by this repository: after creating the Hang Ten Amplitude
project, an authorized maintainer must configure the following to enable
anonymous telemetry in trusted GitHub Actions builds:

- Repository secret `ANALYTICS_API_KEY`: the Hang Ten Amplitude API key.
  Although it is a client-side key, retain it as a
  secret so it is not committed or exposed in workflow logs.

The release workflow runs in the `app-store-connect` environment, whose
secrets and variables are scoped separately from the repository. After the
project exists, define the same `ANALYTICS_API_KEY` environment secret there so
the signed TestFlight archive includes analytics. A missing key remains a safe
no-op rather than failing CI. The workflows place this value in a mode-`0600`
temporary xcconfig, pass only that file path to Xcode, and remove it when the
job step exits so the key is not interpolated into captured build logs.

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

Canonical hangboard packages are checked by the read-only validator in
`Tools/HangboardPackages`. Validate the final inventory or inspect its status
from the repository root:

```sh
rtk scripts/hangboard-packages.sh validate --root Hangboards --final-inventory
rtk scripts/hangboard-packages.sh status --root Hangboards
```

The repository currently has eight directly discovered, complete packages.
Each package contains exactly `board.json` and
`assets/primary.png`. The Xcode build phase runs
`scripts/stage-board-packages.py`, which bundles the validated packages without
rewriting their geometry or presentation bytes.

Use the packaged macOS Hangboard Workbench for direct local visual editing.
Browser-hosted Workbench deployments must use the GitHub-backed
`--allow-remote` server mode.

Workbench edits are explicit operator changes to canonical package geometry;
the saved paths remain the exact rendering and hit-testing source of truth.

Regenerate the bundled routine document after an audited plan change:

```sh
rtk scripts/export-plan-library.sh
rtk scripts/export-plan-library.sh --check
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
