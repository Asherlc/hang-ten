package com.hangten.android.telemetry

import android.content.Context
import com.amplitude.android.Amplitude
import com.amplitude.android.TrackingOptions
import io.sentry.Sentry
import io.sentry.android.core.SentryAndroid

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
            options.isSendDefaultPii = false
            options.isEnableAutoSessionTracking = false
            options.isEnableUncaughtExceptionHandler = false
            options.maxBreadcrumbs = 0
            options.tracesSampleRate = 0.0
            options.profilesSampleRate = 0.0
        }
    }

    override fun captureDiagnostic(tags: Map<String, String>) {
        Sentry.captureMessage("app diagnostic") { scope ->
            tags.forEach(scope::setTag)
        }
    }
}
