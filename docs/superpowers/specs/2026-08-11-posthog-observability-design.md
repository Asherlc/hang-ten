# Hang Ten PostHog Observability Design

## Goal

Add anonymous, privacy-protected product analytics, session replay, feature-flag
access, and handled-error OpenTelemetry diagnostics to Hang Ten
without coupling app features to PostHog APIs.

## Scope

Create a new `Hang Ten` project in the connected PostHog organization's default
region. The PostHog connector currently exposes no project-creation operation,
so creation will be performed in the authenticated PostHog web interface during
implementation. Its public client project token will be supplied locally
through an ignored Xcode configuration file and in trusted CI through GitHub
repository/environment secrets; the repository will contain a token-free
example configuration.

The integration includes PostHog product events, protected session replay, a
small feature-flag boundary, and diagnostic
OpenTelemetry logs and spans. It intentionally excludes user identification,
remote-configured product changes, experiments, surveys, and metrics collection.

## Architecture

App views and domain services depend on focused, vendor-neutral interfaces:

- `TelemetryTracking` captures typed, allow-listed product events.
- `DiagnosticReporting` records handled failures using redacted error metadata.
- `FeatureFlagProviding` reads a flag by key with an explicit local fallback.
- `SessionReplayControlling` starts and stops replay around sensitive flows.

`PostHogTelemetry` is the only adapter importing the PostHog SDK. It translates
the typed events into PostHog captures, configures protected replay, and
implements the feature-flag and replay interfaces. A separate
`OpenTelemetryDiagnostics` adapter emits diagnostic logs and spans over OTLP.
Composition occurs in `HangTenApp`, so no view or existing domain model imports
PostHog or OpenTelemetry directly.

Product analytics cannot be expressed as standard OpenTelemetry signals, and
PostHog's native iOS replay and exception capture are SDK capabilities. Those
concerns therefore stay behind the boundary. Logs and traces use OpenTelemetry
types and OTLP transport where the platform supports them, allowing a future
exporter change without feature-code changes.

## Data Flow

1. `HangTenApp` builds the telemetry composition from build settings. Local
   builds use a token-free tracked default plus an ignored override; trusted CI
   writes the token to a mode-`0600` temporary xcconfig, passes only its path to
   Xcode, and removes it when the job step exits. Missing configuration installs
   no-op implementations, allowing tests, forks, and local builds to run
   without external telemetry.
2. UI and services emit typed events or diagnostics through the interfaces.
3. The PostHog adapter sends only the approved product event and redacted error
   properties. The OpenTelemetry adapter exports diagnostics through OTLP.
4. PostHog links anonymous events, replay, and traces by its anonymous
   device/session identifiers. The app never calls `identify`.

## Privacy and Replay

The app captures anonymously from launch. It never sends person properties or
the following data to PostHog or OTLP:

- Apple Health samples, authorization details beyond a categorical outcome, or
  historical workout data.
- Bluetooth peripheral names, addresses, identifiers, or raw force readings.
- Workout titles, custom-routine content, free text, plan identifiers, raw
  timestamps, or exact durations.
- User-entered text, request or response bodies, or image content.

Replay uses the native iOS wireframe mode, masks all text inputs and images,
does not capture logs or network telemetry, and is paused before entering an
active workout or HealthKit authorization flow. This permits navigation and
configuration troubleshooting while preventing replay capture of the app's
most sensitive training and health surfaces.

## Event Contract

The allow-listed event set is deliberately small:

| Event | Allowed properties |
| --- | --- |
| `app tab selected` | `tab` (`today`, `plans`, `progress`) |
| `plan browsed` | `source` (`catalog`, `favorite`, `custom`) |
| `workout started` | `source` (`catalog`, `favorite`, `custom`) |
| `workout finished` | `outcome` (`completed`, `abandoned`), `duration_bucket` |
| `board selected` | `board_family` |
| `custom routine saved` | none |
| `health authorization finished` | `outcome` (`granted`, `denied`, `unavailable`, `error`) |
| `motherboard connection finished` | `outcome` (`connected`, `failed`, `disconnected`) |
| `app diagnostic recorded` | `category`, `operation`, `error_kind` |

`duration_bucket` is a coarse categorical bucket defined in app code, not a
precise interval. `board_family` is a non-identifying product category, never a
device identifier. Event names follow PostHog's object-verb convention.

## PostHog Project Configuration

The new project will enable session recording. Native iOS exception autocapture
is disabled so handled diagnostics are sent only through `DiagnosticReporting`.
Replay uses the privacy settings described above. The
initial project has no targeting rules, surveys, experiments, or product flags.
The adapter will nevertheless support flags through `FeatureFlagProviding` so
future flags do not leak PostHog types into app features.

The project will contain a small `Hang Ten App Health` dashboard with:

- anonymous application opens;
- the `workout started` to completed `workout finished` funnel;
- `app diagnostic recorded` volume.

## Error Handling and Testing

Telemetry failures are non-fatal. The adapters must not block app launch,
workouts, persistence, Bluetooth, or HealthKit. A no-op implementation supports
unit tests and makes missing configuration safe. Tests verify the allow-list,
redaction, duration bucketing, replay pause/resume decisions, adapter
translation, and no-op behavior without reaching PostHog.

## Sources

- [PostHog iOS session replay installation](https://posthog.com/docs/session-replay/installation/ios)
- [PostHog session replay privacy controls](https://posthog.com/docs/session-replay/privacy)
- [PostHog iOS error tracking installation](https://posthog.com/docs/error-tracking/installation/ios)
- [PostHog iOS SDK usage](https://posthog.com/docs/libraries/ios/usage)
- [PostHog OpenTelemetry tracing](https://posthog.com/docs/distributed-tracing)
- [PostHog iOS logs installation](https://posthog.com/docs/logs/installation/ios)
