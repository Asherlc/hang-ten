# Hang Ten Privacy Policy

Last updated: August 26, 2026

Hang Ten Training ("Hang Ten") is provided by Asher Cohen, who is the data
controller for information processed by the app. Questions and privacy requests
can be sent to [asherlc@asherlc.com](mailto:asherlc@asherlc.com).

Hang Ten is a training timer and visual guide. It is not a medical service and
does not provide medical advice. The app does not sell personal information,
serve advertising, or use Apple Health data for advertising or marketing.

## Information stored on your device

Hang Ten stores app settings and training data locally so that the app can
remember your selected board, favorites, custom routines, sensor settings, and
workout history. Local workout records can include the routine and board,
start/end times, completed steps, loaded intervals, force samples and summaries,
bodyweight baseline, sensor profile and identifier, and battery value. Detailed
force-sensor session files are limited to the 20 most recent sessions. The app
also keeps local pending workout records until it can reconcile them with Apple
Health.

This local data is not sent to Asher Cohen merely because it is stored by the
app. It is protected by the iOS app sandbox and may be included in device backups
according to your iOS and backup settings. You can delete custom routines in the
app. Deleting the app removes its ordinary local app data; Apple Health records
and a GitHub authorization must be managed separately as described below.

## Apple Health (optional)

Hang Ten requests access to Apple Health only when you choose **Connect Apple
Health**. If you authorize access, Hang Ten:

- saves completed sessions as functional-strength workouts, including the
  workout time, routine name, board name/identifier, session identifier, task
  segments, and any available loaded-time/force summary metadata; and
- reads functional-strength workout history and keeps only workouts identified
  as Hang Ten workouts so it can restore and reconcile progress.

Health information is exchanged directly with HealthKit on your device. Hang
Ten does not send Apple Health data to Asher Cohen, GitHub, PostHog, or Sentry.
Apple controls storage and any iCloud synchronization of Health data under your
Apple settings and policies.

You can review or revoke Hang Ten's Health access in **Settings > Health > Data
Access & Devices**, or in the Health app under your profile's app permissions.
You can view or delete workouts in the Health app. Revoking access stops future
HealthKit access but does not itself delete workouts already written to Health.

## Bluetooth force sensors (optional)

Bluetooth is requested only after you choose to connect a compatible force
sensor. Hang Ten scans for nearby supported devices and processes device name,
device identifier, battery/calibration information, and live force readings to
connect, calibrate/tare, display force, and record threshold-based loaded time.
Session measurements and summaries may be stored locally as described above.
They are not sent to Asher Cohen merely through use of the sensor and are not
certified medical or scientific measurements.

You can disconnect the sensor in the app and revoke Bluetooth permission in
**Settings > Privacy & Security > Bluetooth**. Local sensor-session data is
retained with the local workout data described above.

## GitHub board editor (optional)

The board editor can connect to GitHub through GitHub Device Flow. If you choose
this feature, the app sends the device authorization request and authenticated
API requests directly to GitHub. It requests the `repo` and `read:org` scopes
and may read your GitHub username, repository branches, board JSON and images;
create branches; commit board content; and open pull requests in the Hang Ten
repository. GitHub receives the account, request, and content information needed
to provide those services under [GitHub's Privacy Statement](https://docs.github.com/en/site-policy/privacy-policies/github-general-privacy-statement).

The OAuth access token is stored in an iOS Keychain item restricted to the
device. Choosing **Sign out** in Hang Ten deletes that local token. You can also
revoke the OAuth authorization in your GitHub account settings. GitHub retains
commits, pull requests, and other content under its own settings and policies;
signing out does not delete content already sent to GitHub.

## Analytics and diagnostics

The exact network telemetry depends on the configuration included in the build:

- **PostHog.** When a valid PostHog project token is configured, Hang Ten sends
  an allow-listed set of product events, such as selected app tab, catalog or
  favorite browsing, workout start/outcome and duration bucket, supported board
  family, custom-routine saves, authorization outcome, sensor connection
  outcome, and coarse diagnostic category. Hang Ten does not call PostHog's
  identify API or intentionally send your name, email address, GitHub username,
  raw force readings, routine title, or Apple Health data. Masked session replay
  may be enabled; text inputs and images are masked, while log capture, network
  telemetry capture, screenshot mode, and automatic error capture are disabled.
  PostHog may also process technical information supplied automatically by its
  SDK to deliver analytics and feature flags. Without a valid project token,
  PostHog telemetry is disabled.
- **Sentry.** When a Sentry DSN is configured, Sentry receives crash and error
  diagnostics and associated technical context needed to identify and repair
  app failures, such as app/OS version and device/runtime information. Hang Ten
  does not intentionally attach your workout records, raw force readings, Apple
  Health data, GitHub token, or GitHub content to Sentry events. Without a valid
  DSN, Sentry reporting is disabled.

PostHog and Sentry process configured telemetry as service providers. Their
practices are described in the [PostHog Privacy Policy](https://posthog.com/privacy)
and [Sentry Privacy Policy](https://sentry.io/privacy/). Telemetry is retained
according to the applicable project and provider retention settings and only as
long as reasonably needed for product analytics, feature operation, security,
and reliability. There is currently no separate in-app telemetry switch. You
may contact Asher Cohen to ask whether a build has telemetry enabled or to
request deletion of telemetry associated with information you can reasonably
identify; the ability to locate or delete it may be limited where events are
not linked to your identity.

## Sharing, retention, and security

Hang Ten shares information only as described above: with Apple when you enable
Apple Health, with GitHub when you use GitHub sync, and with PostHog or Sentry
when those services are configured. These providers may process information in
countries other than your own. Hang Ten uses system permission prompts,
app-sandboxed storage, a device-only Keychain item for the GitHub token, and
HTTPS for service connections. No method of storage or transmission is
completely secure.

Local information remains until you delete it through an available in-app
control, it is reconciled as described above, the 20-session detailed-history
limit removes an older record, or the app's ordinary local data is removed.
Apple Health and GitHub content are retained and deleted under the controls and
policies of those services. Provider-hosted analytics and diagnostics follow
the retention terms described above.

## Your choices and rights

All Apple Health, Bluetooth, and GitHub features are optional; the core guided
training experience works without them. Depending on where you live, you may
have rights to request access, correction, deletion, restriction, or a copy of
personal information, or to object to certain processing. Contact
[asherlc@asherlc.com](mailto:asherlc@asherlc.com) to make a request. You may be
asked for enough information to verify and fulfill it. You may also complain to
your local data-protection authority.

## Children and changes

Hang Ten is not directed to children under 13, and Asher Cohen does not
knowingly collect personal information from children under 13. This policy may
be updated when the app or its data practices change. Material changes will be
published with a new "Last updated" date.

## Contact

Asher Cohen  
[asherlc@asherlc.com](mailto:asherlc@asherlc.com)
