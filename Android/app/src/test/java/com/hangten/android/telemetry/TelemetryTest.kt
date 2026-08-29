package com.hangten.android.telemetry

import com.hangten.android.health.HealthAuthorizationState
import com.hangten.android.sensors.SensorConnectionState
import io.sentry.Breadcrumb
import io.sentry.Hint
import io.sentry.SentryEvent
import io.sentry.android.core.SentryAndroidOptions
import io.sentry.protocol.Message
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertSame
import org.junit.Assert.assertTrue
import org.junit.Test

class TelemetryTest {
    @Test
    fun `approved events preserve iOS names and categorical properties`() {
        val diagnostic = HangTenDiagnostic(
            category = DiagnosticCategory.Persistence,
            operation = DiagnosticOperation.Save,
            errorKind = DiagnosticErrorKind.Other,
        )

        assertEquals("app tab selected", HangTenTelemetryEvent.AppTabSelected(AppTab.Train).name)
        assertEquals(mapOf("tab" to "train"), HangTenTelemetryEvent.AppTabSelected(AppTab.Train).properties)
        assertEquals("plan browsed", HangTenTelemetryEvent.PlanBrowsed(PlanSource.Catalog).name)
        assertEquals(mapOf("source" to "catalog"), HangTenTelemetryEvent.PlanBrowsed(PlanSource.Catalog).properties)
        assertEquals("workout started", HangTenTelemetryEvent.WorkoutStarted(PlanSource.Favorite).name)
        assertEquals(mapOf("source" to "favorite"), HangTenTelemetryEvent.WorkoutStarted(PlanSource.Favorite).properties)
        assertEquals("board selected", HangTenTelemetryEvent.BoardSelected(BoardFamily.CompactII).name)
        assertEquals(mapOf("board_family" to "compact_ii"), HangTenTelemetryEvent.BoardSelected(BoardFamily.CompactII).properties)
        assertEquals("custom routine saved", HangTenTelemetryEvent.CustomRoutineSaved.name)
        assertEquals(emptyMap<String, String>(), HangTenTelemetryEvent.CustomRoutineSaved.properties)
        assertEquals("health authorization finished", HangTenTelemetryEvent.HealthAuthorizationFinished(HealthAuthorizationOutcome.Granted).name)
        assertEquals(mapOf("outcome" to "granted"), HangTenTelemetryEvent.HealthAuthorizationFinished(HealthAuthorizationOutcome.Granted).properties)
        assertEquals("motherboard connection finished", HangTenTelemetryEvent.MotherboardConnectionFinished(MotherboardConnectionOutcome.Connected).name)
        assertEquals(mapOf("outcome" to "connected"), HangTenTelemetryEvent.MotherboardConnectionFinished(MotherboardConnectionOutcome.Connected).properties)
        assertEquals("app diagnostic recorded", HangTenTelemetryEvent.AppDiagnosticRecorded(diagnostic).name)
        assertEquals(
            mapOf("category" to "persistence", "operation" to "save", "error_kind" to "other"),
            HangTenTelemetryEvent.AppDiagnosticRecorded(diagnostic).properties,
        )
    }

    @Test
    fun `workout completion sends only coarse duration rather than workout content`() {
        val event = HangTenTelemetryEvent.WorkoutFinished(
            outcome = WorkoutOutcome.Completed,
            elapsedMillis = 731_000L,
        )

        assertEquals("workout finished", event.name)
        assertEquals(
            mapOf("outcome" to "completed", "duration_bucket" to "10_to_15_minutes"),
            event.properties,
        )
        assertFalse(event.properties.values.any { it.contains("731") })
        assertFalse(event.properties.keys.any { it.contains("plan") || it.contains("board") || it.contains("sensor") })
    }

    @Test
    fun `missing configuration makes both adapters no op`() {
        val amplitude = RecordingAmplitudeClient()
        val sentry = RecordingSentryClient()

        val dependencies = TelemetryComposition.make(
            TelemetryConfiguration(amplitudeApiKey = "$(ANALYTICS_API_KEY)", sentryDsn = ""),
            RecordingAdapterFactory(amplitude, sentry),
        )
        dependencies.tracking.track(HangTenTelemetryEvent.CustomRoutineSaved)
        dependencies.diagnostics.record(
            HangTenDiagnostic(DiagnosticCategory.Persistence, DiagnosticOperation.Save, DiagnosticErrorKind.Other),
        )

        assertTrue(dependencies.isNoOp)
        assertTrue(amplitude.events.isEmpty())
        assertTrue(sentry.diagnostics.isEmpty())
    }

    @Test
    fun `configured adapters forward only the typed telemetry contract`() {
        val amplitude = RecordingAmplitudeClient()
        val sentry = RecordingSentryClient()

        val dependencies = TelemetryComposition.make(
            TelemetryConfiguration(amplitudeApiKey = "amplitude-key", sentryDsn = "https://public@example.ingest.sentry.io/1"),
            RecordingAdapterFactory(amplitude, sentry),
        )
        dependencies.tracking.track(HangTenTelemetryEvent.WorkoutFinished(WorkoutOutcome.Abandoned, 301_000L))
        dependencies.diagnostics.record(
            HangTenDiagnostic(DiagnosticCategory.Persistence, DiagnosticOperation.Save, DiagnosticErrorKind.Cancellation),
        )

        assertFalse(dependencies.isNoOp)
        assertEquals(
            listOf("workout finished" to mapOf("outcome" to "abandoned", "duration_bucket" to "5_to_10_minutes")),
            amplitude.events,
        )
        assertEquals(
            listOf(mapOf("category" to "persistence", "operation" to "save", "error_kind" to "cancellation")),
            sentry.diagnostics,
        )
    }

    @Test
    fun `a missing analytics key leaves tracking inert while configured diagnostics remain typed`() {
        val amplitude = RecordingAmplitudeClient()
        val sentry = RecordingSentryClient()
        val dependencies = TelemetryComposition.make(
            TelemetryConfiguration(amplitudeApiKey = "", sentryDsn = "https://public@example.ingest.sentry.io/1"),
            RecordingAdapterFactory(amplitude, sentry),
        )

        dependencies.tracking.track(HangTenTelemetryEvent.BoardSelected(BoardFamily.CompactII))
        dependencies.diagnostics.record(HangTenDiagnostic(DiagnosticCategory.Persistence, DiagnosticOperation.Save, DiagnosticErrorKind.Other))

        assertFalse(dependencies.isNoOp)
        assertTrue(amplitude.events.isEmpty())
        assertEquals(
            listOf(mapOf("category" to "persistence", "operation" to "save", "error_kind" to "other")),
            sentry.diagnostics,
        )
    }

    @Test
    fun `Sentry diagnostics fail closed to the fixed message and exact typed tags`() {
        val options = SentryAndroidOptions()
        configureDiagnosticOnlySentry(options)

        assertFalse(options.isEnableUncaughtExceptionHandler)
        assertFalse(options.isAnrEnabled)
        assertFalse(options.isEnableNdk)
        assertFalse(options.isEnableActivityLifecycleBreadcrumbs)
        assertFalse(options.isEnableAppLifecycleBreadcrumbs)
        assertFalse(options.isEnableSystemEventBreadcrumbs)
        assertFalse(options.isEnableAppComponentBreadcrumbs)
        assertFalse(options.isEnableNetworkEventBreadcrumbs)
        assertFalse(options.isEnableUserInteractionBreadcrumbs)
        assertFalse(options.isEnableUserInteractionTracing)
        assertFalse(options.isEnableAutoActivityLifecycleTracing)
        assertEquals(0, options.maxBreadcrumbs)
        val beforeSend = requireNotNull(options.beforeSend)
        assertNull(requireNotNull(options.beforeBreadcrumb).execute(Breadcrumb(), Hint()))

        val accepted = diagnosticEvent(
            tags = mapOf("category" to "persistence", "operation" to "save", "error_kind" to "other"),
        )
        assertSame(accepted, beforeSend.execute(accepted, Hint()))
        assertNull(beforeSend.execute(diagnosticEvent(tags = emptyMap()), Hint()))
        assertNull(
            beforeSend.execute(
                diagnosticEvent(tags = mapOf("category" to "persistence", "operation" to "save", "error_kind" to "other", "detail" to "private workout")),
                Hint(),
            ),
        )
        val unexpected = diagnosticEvent(tags = mapOf("category" to "persistence", "operation" to "save", "error_kind" to "other"))
        unexpected.message = Message().apply { formatted = "unexpected error" }
        assertNull(beforeSend.execute(unexpected, Hint()))
    }

    @Test
    fun `production event mappings preserve only approved categorical values`() {
        assertEquals(BoardFamily.CompactII, boardFamilyForTelemetry("trango-rock-prodigy-compact-ii"))
        assertEquals(BoardFamily.RockProdigyTrainingCenter, boardFamilyForTelemetry("trango-rock-prodigy-training-center"))
        assertNull(boardFamilyForTelemetry("private-custom-board"))
        assertEquals(HealthAuthorizationOutcome.Granted, HealthAuthorizationState.Authorized.telemetryOutcome())
        assertEquals(HealthAuthorizationOutcome.Denied, HealthAuthorizationState.Denied.telemetryOutcome())
        assertEquals(HealthAuthorizationOutcome.Unavailable, HealthAuthorizationState.Unavailable.telemetryOutcome())
        assertNull(HealthAuthorizationState.NotDetermined.telemetryOutcome())
        assertEquals(
            HealthAuthorizationOutcome.Error,
            healthAuthorizationTelemetryOutcome(Result.failure(IllegalStateException("private Health Connect failure"))),
        )
        assertEquals(MotherboardConnectionOutcome.Connected, SensorConnectionState.Streaming.telemetryOutcome())
        assertEquals(MotherboardConnectionOutcome.Failed, SensorConnectionState.Failed.telemetryOutcome())
        assertEquals(MotherboardConnectionOutcome.Disconnected, SensorConnectionState.Disconnected.telemetryOutcome())
        assertNull(SensorConnectionState.Scanning.telemetryOutcome())
    }

    @Test
    fun `persistence save failures report matching typed analytics and diagnostics without error content`() {
        val amplitude = RecordingAmplitudeClient()
        val sentry = RecordingSentryClient()
        val dependencies = TelemetryComposition.make(
            TelemetryConfiguration(amplitudeApiKey = "amplitude-key", sentryDsn = "https://public@example.ingest.sentry.io/1"),
            RecordingAdapterFactory(amplitude, sentry),
        )

        dependencies.recordPersistenceSaveDiagnostic(IllegalStateException("private workout plan title"))

        val expected = mapOf("category" to "persistence", "operation" to "save", "error_kind" to "other")
        assertEquals(listOf("app diagnostic recorded" to expected), amplitude.events)
        assertEquals(listOf(expected), sentry.diagnostics)
        assertFalse(amplitude.events.flatMap { it.second.values }.any { it.contains("private workout") })
    }

    private fun diagnosticEvent(tags: Map<String, String>): SentryEvent = SentryEvent().apply {
        message = Message().apply { formatted = SENTRY_DIAGNOSTIC_MESSAGE }
        setTags(tags)
    }

    private class RecordingAmplitudeClient : AmplitudeTrackingClient {
        val events = mutableListOf<Pair<String, Map<String, String>>>()

        override fun track(name: String, properties: Map<String, String>) {
            events += name to properties
        }
    }

    private class RecordingSentryClient : SentryDiagnosticClient {
        val diagnostics = mutableListOf<Map<String, String>>()

        override fun captureDiagnostic(tags: Map<String, String>) {
            diagnostics += tags
        }
    }

    private class RecordingAdapterFactory(
        private val amplitude: RecordingAmplitudeClient,
        private val sentry: RecordingSentryClient,
    ) : TelemetryAdapterFactory {
        override fun createAmplitude(apiKey: String): TelemetryTracking = AmplitudeTelemetry(amplitude)

        override fun createSentry(dsn: String): DiagnosticReporting = SentryDiagnostics(sentry)
    }
}
