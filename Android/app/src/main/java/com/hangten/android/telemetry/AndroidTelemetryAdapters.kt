package com.hangten.android.telemetry

import android.content.Context
import com.amplitude.android.Amplitude
import com.amplitude.android.TrackingOptions
import io.sentry.Sentry
import io.sentry.SentryEvent
import io.sentry.SentryOptions
import io.sentry.android.core.SentryAndroid
import io.sentry.android.core.SentryAndroidOptions

internal const val SENTRY_DIAGNOSTIC_MESSAGE = "app diagnostic"

class AndroidTelemetryAdapterFactory(
    context: Context,
) : TelemetryAdapterFactory {
    private val applicationContext = context.applicationContext

    override fun createAmplitude(apiKey: String): TelemetryTracking = AmplitudeTelemetry(
        AndroidAmplitudeTrackingClient(applicationContext, apiKey),
    )

    override fun createSentry(dsn: String): DiagnosticReporting = SentryDiagnostics(
        AndroidSentryDiagnosticClient(applicationContext, dsn),
    )
}

private class AndroidAmplitudeTrackingClient(
    context: Context,
    apiKey: String,
) : AmplitudeTrackingClient {
    private val amplitude = Amplitude(apiKey, context) {
        autocapture = emptySet()
        enableAutocaptureRemoteConfig = false
        enableDiagnostics = false
        useAdvertisingIdForDeviceId = false
        useAppSetIdForDeviceId = false
        locationListening = false
        trackingOptions = TrackingOptions()
            .disableAdid()
            .disableAppSetId()
            .disableCarrier()
            .disableCity()
            .disableCountry()
            .disableDeviceBrand()
            .disableDeviceManufacturer()
            .disableDeviceModel()
            .disableDma()
            .disableIpAddress()
            .disableLanguage()
            .disableLatLng()
            .disableOsName()
            .disableOsVersion()
            .disableApiLevel()
            .disablePlatform()
            .disableRegion()
            .disableVersionName()
    }

    override fun track(name: String, properties: Map<String, String>) {
        amplitude.track(name, properties)
    }
}

private class AndroidSentryDiagnosticClient(
    context: Context,
    dsn: String,
) : SentryDiagnosticClient {
    init {
        SentryAndroid.init(context) { options ->
            options.dsn = dsn
            configureDiagnosticOnlySentry(options)
        }
    }

    override fun captureDiagnostic(tags: Map<String, String>) {
        Sentry.captureMessage(SENTRY_DIAGNOSTIC_MESSAGE) { scope ->
            tags.forEach(scope::setTag)
        }
    }
}

/** Keeps configured Sentry diagnostic-only; every non-typed event is rejected before transport. */
internal fun configureDiagnosticOnlySentry(options: SentryAndroidOptions) {
    options.isSendDefaultPii = false
    options.isEnableExternalConfiguration = false
    options.isEnableAutoSessionTracking = false
    options.isEnableUncaughtExceptionHandler = false
    options.isEnableShutdownHook = false
    options.isEnableScopePersistence = false
    options.isSendClientReports = false
    options.isAttachStacktrace = false
    options.isAttachThreads = false
    options.isAttachServerName = false
    options.maxBreadcrumbs = 0
    options.isEnableUserInteractionBreadcrumbs = false
    options.isEnableUserInteractionTracing = false
    options.isEnableScreenTracking = false
    options.tracesSampleRate = 0.0
    options.profilesSampleRate = 0.0
    options.isAnrEnabled = false
    options.isReportHistoricalAnrs = false
    options.isAttachAnrThreadDump = false
    options.isEnableNdk = false
    options.isEnableNdkAppHangTracking = false
    options.isTombstoneEnabled = false
    options.isReportHistoricalTombstones = false
    options.isAttachRawTombstone = false
    options.isEnableActivityLifecycleBreadcrumbs = false
    options.isEnableAppLifecycleBreadcrumbs = false
    options.isEnableSystemEventBreadcrumbs = false
    options.isEnableSystemEventBreadcrumbsExtras = false
    options.isEnableAppComponentBreadcrumbs = false
    options.isEnableNetworkEventBreadcrumbs = false
    options.isEnableAutoActivityLifecycleTracing = false
    options.isEnableFramesTracking = false
    options.isEnableStandaloneAppStartTracing = false
    options.isAttachScreenshot = false
    options.isAttachViewHierarchy = false
    options.isCollectAdditionalContext = false
    options.isCollectExternalStorageContext = false
    options.isEnableRootCheck = false
    options.isEnableScopeSync = false
    options.beforeBreadcrumb = SentryOptions.BeforeBreadcrumbCallback { _, _ -> null }
    options.beforeSend = SentryOptions.BeforeSendCallback { event, _ ->
        event.takeIf(::isApprovedDiagnosticEvent)
    }
}

private fun isApprovedDiagnosticEvent(event: SentryEvent): Boolean {
    if (event.message?.formatted != SENTRY_DIAGNOSTIC_MESSAGE) return false
    val tags = event.tags ?: return false
    return tags.keys == diagnosticTagValues.keys && tags.all { (key, value) -> value in diagnosticTagValues.getValue(key) }
}

private val diagnosticTagValues = mapOf(
    "category" to DiagnosticCategory.entries.map(DiagnosticCategory::value).toSet(),
    "operation" to DiagnosticOperation.entries.map(DiagnosticOperation::value).toSet(),
    "error_kind" to DiagnosticErrorKind.entries.map(DiagnosticErrorKind::value).toSet(),
)
