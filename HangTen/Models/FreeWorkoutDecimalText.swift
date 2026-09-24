import Foundation

/// Locale-aware decimal parse/format for free-workout weight (and similar) text fields.
/// `.decimalPad` emits `,` in many locales; `Double(String)` only accepts `.`.
enum FreeWorkoutDecimalText {
    static func parse(_ text: String, locale: Locale = .current) -> Double? {
        let trimmed = text.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return nil }

        let formatter = NumberFormatter()
        formatter.locale = locale
        formatter.numberStyle = .decimal
        return formatter.number(from: trimmed)?.doubleValue
    }

    static func format(_ value: Double?, locale: Locale = .current) -> String {
        guard let value else { return "" }

        let formatter = NumberFormatter()
        formatter.locale = locale
        formatter.numberStyle = .decimal
        if value.rounded() == value {
            formatter.minimumFractionDigits = 0
            formatter.maximumFractionDigits = 0
        } else {
            formatter.minimumFractionDigits = 0
            formatter.maximumFractionDigits = 1
        }
        return formatter.string(from: NSNumber(value: value)) ?? ""
    }
}
