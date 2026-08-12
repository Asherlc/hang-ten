import Foundation
import OpenTelemetryApi
import OpenTelemetryProtocolExporterCommon
import OpenTelemetryProtocolExporterHttp
import OpenTelemetrySdk

final class OpenTelemetryDiagnostics: DiagnosticReporting {
    private let tracer: any Tracer

    init?(configuration: PostHogConfiguration) {
        guard
            configuration.isConfigured,
            let traceEndpoint = configuration.traceEndpoint
        else {
            return nil
        }

        let exporter = OtlpHttpTraceExporter(
            endpoint: traceEndpoint,
            config: OtlpConfiguration(
                headers: [("Authorization", "Bearer \(configuration.projectToken)")]
            )
        )
        let provider = TracerProviderBuilder()
            .with(resource: Resource(attributes: [
                "service.name": .string("com.hangten.training")
            ]))
            .add(spanProcessor: SimpleSpanProcessor(spanExporter: exporter))
            .build()

        OpenTelemetry.registerTracerProvider(tracerProvider: provider)
        tracer = provider.get(instrumentationName: "com.hangten.training.diagnostics")
    }

    func record(_ diagnostic: HangTenDiagnostic) {
        let span = tracer
            .spanBuilder(spanName: "app diagnostic")
            .setAttribute(key: "category", value: diagnostic.category.rawValue)
            .setAttribute(key: "operation", value: diagnostic.operation.rawValue)
            .setAttribute(key: "error_kind", value: diagnostic.errorKind.rawValue)
            .startSpan()
        span.end()
    }
}
