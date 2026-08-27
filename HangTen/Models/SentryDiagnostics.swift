import Sentry

final class SentryDiagnostics: DiagnosticReporting {
    func record(_ diagnostic: HangTenDiagnostic) {
        let scope = Scope()
        scope.setTag(value: diagnostic.category.rawValue, key: "category")
        scope.setTag(value: diagnostic.operation.rawValue, key: "operation")
        scope.setTag(value: diagnostic.errorKind.rawValue, key: "error_kind")
        SentrySDK.capture(message: "app diagnostic", scope: scope)
    }
}
