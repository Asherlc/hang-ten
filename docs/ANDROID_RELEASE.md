# Android build, CI, and Google Play release

## Local prerequisites and commands

Install Android Studio with Android SDK Platform 36, an API 35 emulator image,
and a JDK 17. Open the `Android` directory in Android Studio, or use the
checked-in Gradle wrapper from the repository root. Keep local Android SDK
configuration in the ignored `Android/local.properties` file; do not commit it.

Run the local checks that CI runs before packaging:

```sh
rtk ./Android/gradlew -p Android check
rtk ./Android/gradlew -p Android :app:stageCanonicalAssets :app:testDebugUnitTest :app:lintDebug :app:assembleDebug
rtk ./Android/gradlew -p Android -PGITHUB_OAUTH_CLIENT_ID=your_public_client_id :app:bundleRelease
```

Start an API 35 emulator in Android Studio, then run the instrumented test
suite:

```sh
rtk ./Android/gradlew -p Android :app:connectedDebugAndroidTest
```

The Debug APK is written to
`Android/app/build/outputs/apk/debug/app-debug.apk`. Lint HTML/XML reports are
under `Android/app/build/reports/`, JVM test results are under
`Android/app/build/test-results/`, and connected-test results are under
`Android/app/build/outputs/androidTest-results/`.

## Google Play Billing release gate

Before promoting an Android build beyond the internal testing track, an
authorized Play Console operator must run this checklist against the signed
build installed from Google Play (not an adb-installed APK):

1. In **Monetize with Play > Products > One-time products**, create and
   activate the one-time product with the exact ID
   `com.hangten.training.lifetime`. Configure a price in every country offered
   by the release. The app must not expose a different product ID as an
   alternative unlock.
2. Add the test Google account both to the internal-track tester list and to
   **Settings > License testing**. Upload the candidate AAB to the internal
   track, publish that track, opt the account into its Play testing link, and
   install the resulting Play-delivered build.
3. Start the lifetime purchase. Confirm the Play confirmation completes, the
   app unlocks only after the purchase reaches `PURCHASED`, and the order shows
   as acknowledged in Play Console order management. Reopen the app and use
   **Restore purchases** to confirm the unlock remains available.
4. Exercise a deferred payment method that produces a `PENDING` transaction
   (for example, the Play license tester pending-payment instrument). Confirm
   the app remains locked and describes the pending state; do not treat a
   pending order as an unlock. Complete or cancel that order in Play, then
   bring the app to the foreground and confirm its state matches the final
   order.
5. Refund the completed test order in **Order management**. Background then
   foreground the app, or use **Restore purchases**, and confirm the lifetime
   entitlement is removed and the two-workout access gate returns. Purchase
   once more and repeat the restore check before recording the gate as passed.

Record the Play Console order IDs, tester account, build version code, and the
pass/fail result of each step in the release ticket. Do not include purchase
tokens, service-account keys, or other credentials in the ticket.

## Health, sensor, and GitHub release gates

These checks require physical devices or external services and are not
substituted by emulator fakes. Record the model/OS, candidate version code, and
pass/fail result in the release ticket; never record OAuth tokens, GitHub device
codes, sensor identifiers, or raw workout/sensor data.

1. On an API 36+ device with Health Connect installed, open **Settings > Connect
   Health**. Confirm the app does not request Health permission at launch, asks
   only after that explicit action, and keeps local history after denied or
   unavailable permission. With authorization granted, complete a workout,
   confirm the locally saved session remains visible, then confirm the matching
   strength-training record and its Hang Ten history reconciliation after an
   app restart.
2. On supported Android hardware, use **Settings > Connect sensor** and grant
   Bluetooth permission only from that action. Exercise the reviewed
   Motherboard, Tindeq Progressor, and PitchSix devices where available:
   confirm scan/connect, live force, tare, a measured workout, disconnect, and
   reconnect. Confirm a malformed/disconnected stream fails visibly without
   losing local workout completion. This is the required real-transport check;
   deterministic fake-transport tests do not replace it.
3. In **Settings > Board editor**, sign in with the registered public GitHub
   Device Flow client. Complete browser verification, cancel one attempt, and
   verify sign-out removes local authorization. Pull a package, make a direct
   geometry edit, validate/save it, push the allowed `board.json` plus its
   referenced image to a draft branch, and confirm the pull request. Make a
   competing remote change and confirm the Android client reports a conflict
   rather than overwriting it. Never enter a personal access token or client
   secret in the app.

## Optional diagnostics configuration

Android telemetry emits only the typed iOS-compatible event names/properties:
tab/source/outcome, a coarse duration bucket, approved board-family values, and
typed diagnostic category/operation/error-kind. It never sends plan or board
identifiers, canonical geometry, instructions, health records, raw timing,
sensor measurements, OAuth data, purchase tokens, or error text. Amplitude
autocapture and device/location fields are disabled; Sentry receives only the
typed `app diagnostic` message and tags.

Both providers are optional. A missing, placeholder, or non-HTTPS value leaves
the relevant adapter inert and does not prevent an Android release. To enable
them in a protected `google-play` environment, configure:

- Optional secret `HANGTEN_AMPLITUDE_API_KEY` for the Amplitude project key.
- Optional environment variable `HANGTEN_SENTRY_DSN` for the HTTPS Sentry DSN.

The release workflow passes these values to Gradle's Release `BuildConfig`; do not put them
in source, tickets, issue comments, or command output. The DSN is an app-side
identifier, not an authentication secret, but environment scoping still keeps
operational configuration separate from source.

## GitHub Actions verification

The stable branch-protection check is named **Android verification**. It runs
the Android validation job when Android code, `Hangboards`, the canonical plan
library, countdown audio, shared board content, or CI wiring changes. For
unrelated pull requests, the stable check reports that the path is skipped
successfully rather than remaining pending. It runs JVM tests, Debug lint and
APK assembly, a Release AAB candidate build using a synthetic public Device
Flow client ID, API 35 instrumented tests, and a pinned `actionlint` workflow
syntax check. Each run uploads an `android-verification-<run-id>` artifact
containing the Debug APK, candidate AAB, and available test/lint reports.

## One-time Google Play operator handoff

The repository cannot create Google Play Console or Google Cloud resources, so
the `google-play` environment must be configured by an authorized operator
before the release workflow can publish anything.

1. In Play Console, create the `com.hangten.training` app record and complete
   the required app setup. Enable Play App Signing. Create an upload key for
   this app and retain its keystore and passwords securely.
2. In Google Cloud, create a dedicated service account for Play publishing,
   create a JSON key, and invite that service account in Play Console with the
   minimum release permission needed to upload to the internal testing track.
   Use the same Google Cloud project that Play Console recognizes for the app.
3. In the repository's GitHub Actions settings, create a protected environment
   named `google-play`. Restrict it to the `main` branch and configure required
   reviewers if release approval is desired. Do not put these credentials in
   repository-level secrets or variables.
4. Add these **environment secrets** exactly as named:

   - `ANDROID_UPLOAD_KEYSTORE_BASE64`: base64 encoding of the upload-key
     keystore (`base64 < upload-keystore.jks | tr -d '\n'`).
   - `ANDROID_UPLOAD_KEYSTORE_PASSWORD`: upload-keystore password.
   - `ANDROID_UPLOAD_KEY_ALIAS`: alias of the upload key.
   - `ANDROID_UPLOAD_KEY_PASSWORD`: private-key password.
   - `GOOGLE_PLAY_SERVICE_ACCOUNT_JSON`: the complete JSON service-account key.
   - `HANGTEN_AMPLITUDE_API_KEY` (optional): the Amplitude project key.

5. Add this **environment variable** exactly as named:

   - `GOOGLE_PLAY_PACKAGE_NAME`: `com.hangten.training`.
   - `HANGTEN_GITHUB_OAUTH_CLIENT_ID`: the registered GitHub OAuth App's
     public Device Flow client ID. Enable Device Flow for that app before
     release. This is intentionally a GitHub environment **variable**, not a
     secret: Android embeds the public client ID in `BuildConfig`.
   - `HANGTEN_SENTRY_DSN` (optional): HTTPS Sentry DSN used for typed Android
     diagnostics only.

Never provide `GITHUB_CLIENT_SECRET`, an OAuth client secret, or a personal
access token to the Android Gradle build, release environment, app settings,
or source tree. For a local Release build, pass only the same public value:

```sh
rtk ./Android/gradlew -p Android -PGITHUB_OAUTH_CLIENT_ID=your_public_client_id :app:bundleRelease
```

Treat the five required secrets and local keystore as credentials. The workflow
checks that every secret and variable is nonempty before decoding the keystore
or invoking Gradle, writes the keystore and signing properties only in
runner-temporary storage with restrictive permissions, and removes them when
the build step exits. It never prints these values.

## Release behavior and artifacts

`.github/workflows/android-release.yml` runs only for a push to `main` and uses
the protected `google-play` environment. It builds a signed Release AAB,
uploads `android-release-aab-<run-id>` as an Actions artifact, then sends the
same bundle to the Google Play **internal** track.

Until the Play Console app, upload key, service account, and exact protected
environment credentials above are supplied, the release workflow fails closed
and cannot publish. This repository change does not provision those external
credentials or publish a first release.
