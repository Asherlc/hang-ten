package com.hangten.android.telemetry

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
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
