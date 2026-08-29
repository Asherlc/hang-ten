# Android build, CI, and Google Play release

## Local prerequisites and commands

Install Android Studio with the Android SDK Platform 35, an API 35 emulator
image, and a JDK 17. Open the `Android` directory in Android Studio, or use the
checked-in Gradle wrapper from the repository root. Keep local Android SDK
configuration in the ignored `Android/local.properties` file; do not commit it.

Run the local checks that CI runs before packaging:

```sh
rtk ./Android/gradlew -p Android check
rtk ./Android/gradlew -p Android :app:stageCanonicalAssets :app:testDebugUnitTest :app:lintDebug :app:assembleDebug
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

## GitHub Actions verification

The stable branch-protection check is named **Android verification**. It runs
the Android validation job when Android code, `Hangboards`, the canonical plan
library, countdown audio, shared board content, or CI wiring changes. For
unrelated pull requests, the stable check reports that the path is skipped
successfully rather than remaining pending. Each run uploads an
`android-verification-<run-id>` artifact containing the Debug APK and available
test/lint reports.

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

5. Add this **environment variable** exactly as named:

   - `GOOGLE_PLAY_PACKAGE_NAME`: `com.hangten.training`.

Treat all five secrets and the local keystore as credentials. The workflow
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
