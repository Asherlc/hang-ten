package com.hangten.android.telemetry

enum class AppTab(val value: String) { Train("train"), Plans("plans"), History("history") }

enum class PlanSource(val value: String) { Catalog("catalog"), Favorite("favorite"), Custom("custom") }

enum class WorkoutOutcome(val value: String) { Completed("completed"), Abandoned("abandoned") }

enum class BoardFamily(val value: String) {
    CompactII("compact_ii"),
    RockProdigyTrainingCenter("rock_prodigy_training_center"),
}

enum class HealthAuthorizationOutcome(val value: String) { Granted("granted"), Denied("denied"), Unavailable("unavailable"), Error("error") }

enum class MotherboardConnectionOutcome(val value: String) { Connected("connected"), Failed("failed"), Disconnected("disconnected") }

enum class DiagnosticCategory(val value: String) { Persistence("persistence") }

enum class DiagnosticOperation(val value: String) { Save("save") }

enum class DiagnosticErrorKind(val value: String) { Cancellation("cancellation"), Other("other") }

data class HangTenDiagnostic(
    val category: DiagnosticCategory,
    val operation: DiagnosticOperation,
    val errorKind: DiagnosticErrorKind,
)

sealed interface HangTenTelemetryEvent {
    val name: String
    val properties: Map<String, String>

    data class AppTabSelected(val tab: AppTab) : HangTenTelemetryEvent {
        override val name = "app tab selected"
        override val properties = mapOf("tab" to tab.value)
    }

    data class PlanBrowsed(val source: PlanSource) : HangTenTelemetryEvent {
        override val name = "plan browsed"
        override val properties = mapOf("source" to source.value)
    }

    data class WorkoutStarted(val source: PlanSource) : HangTenTelemetryEvent {
        override val name = "workout started"
        override val properties = mapOf("source" to source.value)
    }

    data class WorkoutFinished(
        val outcome: WorkoutOutcome,
        private val elapsedMillis: Long,
    ) : HangTenTelemetryEvent {
        override val name = "workout finished"
        override val properties = mapOf(
            "outcome" to outcome.value,
            "duration_bucket" to durationBucket(elapsedMillis),
        )
    }

    data class BoardSelected(val family: BoardFamily) : HangTenTelemetryEvent {
        override val name = "board selected"
        override val properties = mapOf("board_family" to family.value)
    }

    data object CustomRoutineSaved : HangTenTelemetryEvent {
        override val name = "custom routine saved"
        override val properties = emptyMap<String, String>()
    }

    data class HealthAuthorizationFinished(val outcome: HealthAuthorizationOutcome) : HangTenTelemetryEvent {
        override val name = "health authorization finished"
        override val properties = mapOf("outcome" to outcome.value)
    }

    data class MotherboardConnectionFinished(val outcome: MotherboardConnectionOutcome) : HangTenTelemetryEvent {
        override val name = "motherboard connection finished"
        override val properties = mapOf("outcome" to outcome.value)
    }

    data class AppDiagnosticRecorded(val diagnostic: HangTenDiagnostic) : HangTenTelemetryEvent {
        override val name = "app diagnostic recorded"
        override val properties = diagnostic.tags
    }
}

val HangTenDiagnostic.tags: Map<String, String>
    get() = mapOf(
        "category" to category.value,
        "operation" to operation.value,
        "error_kind" to errorKind.value,
    )

fun interface TelemetryTracking {
    fun track(event: HangTenTelemetryEvent)
}

fun interface DiagnosticReporting {
    fun record(diagnostic: HangTenDiagnostic)
}

object NoOpTelemetry : TelemetryTracking, DiagnosticReporting {
    override fun track(event: HangTenTelemetryEvent) = Unit

    override fun record(diagnostic: HangTenDiagnostic) = Unit
}

fun interface AmplitudeTrackingClient {
    fun track(name: String, properties: Map<String, String>)
}

class AmplitudeTelemetry(
    private val client: AmplitudeTrackingClient,
) : TelemetryTracking {
    override fun track(event: HangTenTelemetryEvent) = client.track(event.name, event.properties)
}

fun interface SentryDiagnosticClient {
    fun captureDiagnostic(tags: Map<String, String>)
}

class SentryDiagnostics(
    private val client: SentryDiagnosticClient,
) : DiagnosticReporting {
    override fun record(diagnostic: HangTenDiagnostic) = client.captureDiagnostic(diagnostic.tags)
}

data class TelemetryConfiguration(
    val amplitudeApiKey: String,
    val sentryDsn: String,
) {
    val hasAmplitude: Boolean get() = amplitudeApiKey.isUsableConfiguration()
    val hasSentry: Boolean get() = sentryDsn.isUsableConfiguration() && sentryDsn.trim().startsWith("https://")
}

data class TelemetryDependencies(
    val tracking: TelemetryTracking,
    val diagnostics: DiagnosticReporting,
    val isNoOp: Boolean,
)

interface TelemetryAdapterFactory {
    fun createAmplitude(apiKey: String): TelemetryTracking
    fun createSentry(dsn: String): DiagnosticReporting
}

object TelemetryComposition {
    fun make(configuration: TelemetryConfiguration, factory: TelemetryAdapterFactory): TelemetryDependencies {
        val tracking = if (configuration.hasAmplitude) factory.createAmplitude(configuration.amplitudeApiKey.trim()) else NoOpTelemetry
        val diagnostics = if (configuration.hasSentry) factory.createSentry(configuration.sentryDsn.trim()) else NoOpTelemetry
        return TelemetryDependencies(tracking, diagnostics, isNoOp = !configuration.hasAmplitude && !configuration.hasSentry)
    }
}

private fun durationBucket(elapsedMillis: Long): String = when {
    elapsedMillis < 5 * 60_000L -> "under_5_minutes"
    elapsedMillis < 10 * 60_000L -> "5_to_10_minutes"
    elapsedMillis < 15 * 60_000L -> "10_to_15_minutes"
    else -> "15_plus_minutes"
}

private fun String.isUsableConfiguration(): Boolean {
    val value = trim()
    return value.isNotEmpty() && !value.startsWith("$(") && value != "your_amplitude_api_key"
}
