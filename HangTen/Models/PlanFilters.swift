import Foundation

struct PlanFilters: Equatable {
    var levels: Set<String> = []
    var provenances: Set<RoutineProvenance> = []
    var categories: Set<String> = []
    var tags: Set<String> = []

    var isEmpty: Bool { activeFacetCount == 0 }

    var activeFacetCount: Int {
        [levels.isEmpty, provenances.isEmpty, categories.isEmpty, tags.isEmpty]
            .filter { !$0 }
            .count
    }

    func matches(_ metadata: PlanMetadata) -> Bool {
        (levels.isEmpty || levels.contains(metadata.level)) &&
        (provenances.isEmpty || provenances.contains(metadata.provenance)) &&
        (categories.isEmpty || categories.contains(metadata.category)) &&
        (tags.isEmpty || !tags.isDisjoint(with: metadata.athleteFacingLabels))
    }

    mutating func clear() {
        levels.removeAll()
        provenances.removeAll()
        categories.removeAll()
        tags.removeAll()
    }

    mutating func toggle(level: String) { levels = Self.toggled(level, in: levels) }
    mutating func toggle(provenance: RoutineProvenance) { provenances = Self.toggled(provenance, in: provenances) }
    mutating func toggle(category: String) { categories = Self.toggled(category, in: categories) }
    mutating func toggle(tag: String) { tags = Self.toggled(tag, in: tags) }

    private static func toggled<Value: Hashable>(_ value: Value, in values: Set<Value>) -> Set<Value> {
        var toggledValues = values
        if !toggledValues.insert(value).inserted {
            toggledValues.remove(value)
        }
        return toggledValues
    }
}

struct PlanFilterOptions: Hashable {
    let levels: [String]
    let provenances: [RoutineProvenance]
    let categories: [String]
    let tags: [String]

    init(metadata: [PlanMetadata]) {
        levels = Self.sortedUnique(metadata.map(\.level))
        provenances = Array(Set(metadata.map(\.provenance))).sorted { $0.label < $1.label }
        categories = Self.sortedUnique(metadata.map(\.category))
        tags = Self.sortedUnique(metadata.flatMap(\.athleteFacingLabels))
    }

    private static func sortedUnique(_ values: [String]) -> [String] {
        Array(Set(values)).sorted {
            $0.localizedCaseInsensitiveCompare($1) == .orderedAscending
        }
    }
}
