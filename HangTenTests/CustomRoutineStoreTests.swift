import XCTest
@testable import HangTen

final class CustomRoutineStoreTests: XCTestCase {
    func testStoreDeletesFormerStorageKeysWithoutDecoding() throws {
        let suite = "CustomRoutineStoreTests.\(UUID().uuidString)"
        let defaults = try XCTUnwrap(UserDefaults(suiteName: suite))
        defer { defaults.removePersistentDomain(forName: suite) }
        let formerPayload = try JSONEncoder().encode(
            CustomRoutineLibrary(routines: [genericDefinition(id: "custom.former-key")])
        )
        for key in CustomRoutineStore.legacyKeys {
            defaults.set(formerPayload, forKey: key)
        }

        let store = CustomRoutineStore(defaults: defaults)

        XCTAssertTrue(store.routines.isEmpty)
        XCTAssertTrue(CustomRoutineStore.legacyKeys.allSatisfy {
            defaults.object(forKey: $0) == nil
        })
    }

    func testCustomRoutineLibraryEncodingContainsOnlyRoutines() throws {
        let data = try JSONEncoder().encode(CustomRoutineLibrary(routines: []))
        let document = try XCTUnwrap(
            JSONSerialization.jsonObject(with: data) as? [String: Any]
        )

        XCTAssertEqual(Set(document.keys), ["routines"])
        XCTAssertNil(document["schemaVersion"])
    }

    func testCustomRoutineSegmentsEncodeOnlyPluralTargets() throws {
        let segment = WorkoutSegmentDefinition(
            kind: .work,
            target: .fromLegacyTargets([.kind(.edge)]),
            timing: .fixed,
            duration: 10
        )
        let routine = CustomRoutineDefinition(
            id: "custom.segment-shape",
            title: "Segment shape",
            subtitle: "",
            difficulty: nil,
            category: nil,
            tags: [],
            targetMode: .generic,
            steps: [WorkoutStepDefinition(
                id: "hang",
                title: "Edge hang",
                instruction: "Hang.",
                accessory: "10s",
                duration: 10,
                phase: .hang,
                segments: [segment]
            )]
        )
        let data = try JSONEncoder().encode(CustomRoutineLibrary(routines: [routine]))
        let document = try XCTUnwrap(
            JSONSerialization.jsonObject(with: data) as? [String: Any]
        )
        let routines = try XCTUnwrap(document["routines"] as? [[String: Any]])
        let steps = try XCTUnwrap(routines[0]["steps"] as? [[String: Any]])
        let segments = try XCTUnwrap(steps[0]["segments"] as? [[String: Any]])

        let target = try XCTUnwrap(segments[0]["target"] as? [String: Any])
        XCTAssertEqual(target["kind"] as? String, "requirements")
        XCTAssertEqual(
            target["requirements"] as? [[String: String]],
            [["kind": "edge", "selection": "single"]]
        )
        XCTAssertNil(segments[0]["targets"])
    }

    func testCustomRoutineLibraryRejectsFormerSchemaVersionField() {
        XCTAssertThrowsError(
            try JSONDecoder().decode(
                CustomRoutineLibrary.self,
                from: Data(#"{"schemaVersion":1,"routines":[]}"#.utf8)
            )
        )
    }

    func testCompactIIPocketsExposeCapacityWithDistinctGripSemantics() throws {
        let twoFingerPocket = try XCTUnwrap(
            BoardCatalog.defaultBoard.contacts.first { $0.id == "pocket-29-two-left" }
        )
        let threeFingerPocket = try XCTUnwrap(
            BoardCatalog.defaultBoard.contacts.first { $0.id == "pocket-29-three-left" }
        )
        let fourFingerPocket = try XCTUnwrap(
            BoardCatalog.defaultBoard.contacts.first { $0.id == "pocket-29-four-center" }
        )

        XCTAssertEqual(twoFingerPocket.fingerCapacity, 2)
        XCTAssertEqual(threeFingerPocket.fingerCapacity, 3)
        XCTAssertEqual(fourFingerPocket.fingerCapacity, 4)
        XCTAssertEqual(twoFingerPocket.gripTypes, [.twoFingerPocket])
        XCTAssertEqual(threeFingerPocket.gripTypes, [.threeFingerPocket])
        XCTAssertEqual(fourFingerPocket.gripTypes, [.fourFingerPocket])
    }

    func testPocketCapacityDoesNotManufacturePhysicalFeatures() {
        let oneFingerPocket = PhysicalContact(
            id: "one-finger",
            name: "One finger",
            kind: .pocket,
            fingerCapacity: 1
        )
        let fourFingerPocket = PhysicalContact(
            id: "four-finger",
            name: "Four finger",
            kind: .pocket,
            fingerCapacity: 4
        )

        XCTAssertEqual(oneFingerPocket.fingerCapacity, 1)
        XCTAssertNil(oneFingerPocket.shape)
        XCTAssertEqual(fourFingerPocket.fingerCapacity, 4)
        XCTAssertNil(fourFingerPocket.shape)
    }

    func testPlanResolutionRetainsExactFingerConfiguration() throws {
        let expectedConfiguration = try XCTUnwrap(FingerConfiguration(engagedFingers: [.index]))
        let step = WorkoutStepDefinition(
            id: "exact-finger-step",
            title: "One-finger hang",
            instruction: "Hang with the index finger.",
            accessory: "10s",
            duration: 10,
            phase: .hang,
            gripType: .openHand,
            fingerConfiguration: expectedConfiguration,
            activeDuration: 10
        )
        let library = PlanLibraryDefinition(
            metadata: PlanLibraryMetadata(
                id: "exact-finger-library",
                title: "Exact fingers",
                generatedAt: "2026-08-07"
            ),
            blocks: [WorkoutBlockDefinition(id: "exact-finger-block", steps: [step])],
            plans: [
                PlanDefinition(
                    id: "exact-finger-plan",
                    metadata: PlanMetadata(
                        title: "Exact fingers",
                        subtitle: "",
                        level: "Test",
                        sourceLabel: "Created in Hang Ten",
                        sourceURL: nil,
                        provenance: .custom
                    ),
                    boardID: nil,
                    blocks: [WorkoutBlockReference(blockID: "exact-finger-block")]
                )
            ]
        )

        let resolved = try PlanDefinitionResolver(library: library).resolve(library.plans[0])

        XCTAssertEqual(resolved.steps.map(\.fingerConfiguration), [expectedConfiguration])
    }

    func testBoardSpecificDefinitionRoundTripsAndResolvesToTrainingPlan() throws {
        let suite = "CustomRoutineStoreTests.\(UUID().uuidString)"
        let defaults = try XCTUnwrap(UserDefaults(suiteName: suite))
        defer { defaults.removePersistentDomain(forName: suite) }

        let definition = CustomRoutineDefinition(
            id: "custom.board",
            title: "Edge strength",
            subtitle: "Short edge work",
            difficulty: "Advanced",
            category: "strength",
            tags: ["custom", "edges"],
            targetMode: .boardSpecific(boardID: BoardCatalog.defaultBoard.id),
            steps: [
                WorkoutStepDefinition(
                    id: "step-1",
                    title: "Hang",
                    instruction: "Hang from the 19 mm edges.",
                    accessory: "10s",
                    duration: 10,
                    phase: .hang,
                    segments: [
                        WorkoutSegmentDefinition(
                            kind: .work,
                            target: .fromLegacyTargets([.kind(.edge)]),
                            timing: .fixed,
                            duration: 10
                        )
                    ],
                    gripType: .halfCrimp,
                    activeDuration: 10
                )
            ]
        )
        let store = CustomRoutineStore(defaults: defaults)

        try store.save(definition)

        let persistedData = try XCTUnwrap(defaults.data(forKey: CustomRoutineStore.defaultKey))
        let persistedDocument = try XCTUnwrap(
            JSONSerialization.jsonObject(with: persistedData) as? [String: Any]
        )
        let persisted = try XCTUnwrap(store.routines.first)
        let reloaded = CustomRoutineStore(defaults: defaults)

        XCTAssertEqual(Set(persistedDocument.keys), ["routines"])
        XCTAssertEqual(reloaded.routines, [persisted])
        XCTAssertEqual(persisted.steps.map(\.id), ["step-1"])
        XCTAssertEqual(persisted.steps.map { $0.segments.count }, [1])
        let plan = try reloaded.plan(for: persisted)
        XCTAssertEqual(plan.id, definition.id)
        XCTAssertEqual(plan.title, definition.title)
        XCTAssertEqual(plan.steps[0].workRequirements, [.kind(.edge)])
        XCTAssertEqual(plan.provenance, .custom)
        XCTAssertNil(plan.sourceURL)
    }

    func testGenericDefinitionRequiresTargetsThatResolveOnARegisteredBoard() throws {
        let definition = CustomRoutineDefinition(
            id: "custom.generic",
            title: "Generic edge work",
            subtitle: "",
            difficulty: nil,
            category: nil,
            tags: [],
            targetMode: .generic,
            steps: [
                WorkoutStepDefinition(
                    id: "step-1",
                    title: "Edge hang",
                    instruction: "Hang.",
                    accessory: "10s",
                    duration: 10,
                    phase: .hang,
                    segments: [
                        WorkoutSegmentDefinition(
                            kind: .work,
                            target: .fromLegacyTargets([.kind(.edge)]),
                            timing: .fixed,
                            duration: 10
                        )
                    ],
                    activeDuration: 10
                )
            ]
        )

        XCTAssertTrue(CustomRoutineValidator.issues(for: definition, availableBoards: BoardCatalog.all).isEmpty)
    }

    func testDoubleHandCustomStepAcceptsTwoPortableBoardContacts() throws {
        let board = try XCTUnwrap(
            BoardCatalog.all.first { $0.id == "frictitious.port-a-board" }
        )
        let definition = CustomRoutineDefinition(
            id: "custom.port-a-board-double",
            title: "Portable double",
            subtitle: "",
            difficulty: nil,
            category: nil,
            tags: [],
            targetMode: .boardSpecific(boardID: board.id),
            steps: [
                WorkoutStepDefinition(
                    id: "step-1",
                    title: "Two-hand pull",
                    instruction: "",
                    accessory: "",
                    duration: 10,
                    phase: .pull,
                    handUse: .double,
                    side: .both
                )
            ]
        )

        let issues = CustomRoutineValidator.issues(
            for: definition,
            availableBoards: [board]
        )

        XCTAssertFalse(issues.contains(.unresolvableTargets(stepIndex: 0)))
    }

    func testSaveAndResolveAllowsEmptyOptionalSubtitle() throws {
        let suite = "CustomRoutineStoreTests.\(UUID().uuidString)"
        let defaults = try XCTUnwrap(UserDefaults(suiteName: suite))
        defer { defaults.removePersistentDomain(forName: suite) }
        let definition = genericDefinition(id: "custom.empty-subtitle")
        let store = CustomRoutineStore(defaults: defaults)

        try store.save(definition)

        let persisted = try XCTUnwrap(store.routines.first)
        let plan = try store.plan(for: persisted)

        XCTAssertEqual(plan.id, definition.id)
        XCTAssertEqual(plan.title, definition.title)
        XCTAssertEqual(plan.subtitle, "")
        XCTAssertEqual(plan.provenance, .custom)
    }

    func testValidationRejectsBlankNameMissingTargetsAndInvalidDuration() {
        let definition = CustomRoutineDefinition(
            id: "custom.invalid",
            title: "   ",
            subtitle: "",
            difficulty: nil,
            category: nil,
            tags: [],
            targetMode: .boardSpecific(boardID: BoardCatalog.defaultBoard.id),
            steps: [
                WorkoutStepDefinition(
                    id: "step-1",
                    title: "Hang",
                    instruction: "Hang.",
                    accessory: "",
                    duration: 0,
                    phase: .hang)
            ]
        )

        let issues = CustomRoutineValidator.issues(for: definition, availableBoards: BoardCatalog.all)

        XCTAssertTrue(issues.contains(.emptyTitle))
        XCTAssertTrue(issues.contains(.invalidDuration(stepIndex: 0)))
        XCTAssertTrue(issues.contains(.missingTargets(stepIndex: 0)))
    }

    func testCorruptStoredDataLoadsEmptyAndPublishesPersistenceError() throws {
        let suite = "CustomRoutineStoreTests.\(UUID().uuidString)"
        let defaults = try XCTUnwrap(UserDefaults(suiteName: suite))
        defer { defaults.removePersistentDomain(forName: suite) }
        defaults.set(Data("not-json".utf8), forKey: CustomRoutineStore.defaultKey)

        let store = CustomRoutineStore(defaults: defaults)

        XCTAssertTrue(store.routines.isEmpty)
        XCTAssertNotNil(store.persistenceError)
    }

    func testLoadKeepsTheFirstPersistedRoutineForEachDuplicateIDAndWarns() throws {
        let suite = "CustomRoutineStoreTests.\(UUID().uuidString)"
        let defaults = try XCTUnwrap(UserDefaults(suiteName: suite))
        defer { defaults.removePersistentDomain(forName: suite) }
        let first = genericDefinition(id: "custom.duplicate", subtitle: "First")
        let duplicate = genericDefinition(id: "custom.duplicate", subtitle: "Second")
        defaults.set(
            try JSONEncoder().encode(CustomRoutineLibrary(routines: [first, duplicate])),
            forKey: CustomRoutineStore.defaultKey
        )

        let store = CustomRoutineStore(defaults: defaults)

        XCTAssertEqual(store.routines, [first])
        XCTAssertEqual(store.persistenceError, "Some custom routines could not be loaded.")
    }

    func testDeletingAnUnknownRoutineLeavesPersistedDataUntouched() throws {
        let suite = "CustomRoutineStoreTests.\(UUID().uuidString)"
        let defaults = try XCTUnwrap(UserDefaults(suiteName: suite))
        defer { defaults.removePersistentDomain(forName: suite) }
        let persistedData = try JSONEncoder().encode(
            CustomRoutineLibrary(routines: [genericDefinition(id: "custom.persisted")])
        )
        defaults.set(persistedData, forKey: CustomRoutineStore.defaultKey)
        let store = CustomRoutineStore(defaults: defaults)

        try store.delete(id: "custom.unknown")

        XCTAssertEqual(defaults.data(forKey: CustomRoutineStore.defaultKey), persistedData)
    }

    func testSaveNormalizesOptionalMetadataAndDuplicateTags() throws {
        let suite = "CustomRoutineStoreTests.\(UUID().uuidString)"
        let defaults = try XCTUnwrap(UserDefaults(suiteName: suite))
        defer { defaults.removePersistentDomain(forName: suite) }
        let definition = genericDefinition(
            subtitle: "  Short session  ",
            difficulty: "  ",
            category: "  strength ",
            tags: ["  Edges ", "edges", "Custom", " CUSTOM "]
        )
        let store = CustomRoutineStore(defaults: defaults)

        try store.save(definition)

        let saved = try XCTUnwrap(store.routines.first)
        XCTAssertEqual(saved.subtitle, "Short session")
        XCTAssertNil(saved.difficulty)
        XCTAssertEqual(saved.category, "strength")
        XCTAssertEqual(saved.tags, ["Edges", "Custom"])
    }

    func testSaveSplitsCommaSeparatedTagsInOrder() throws {
        let suite = "CustomRoutineStoreTests.\(UUID().uuidString)"
        let defaults = try XCTUnwrap(UserDefaults(suiteName: suite))
        defer { defaults.removePersistentDomain(forName: suite) }
        let definition = genericDefinition(tags: [" edges, custom "])
        let store = CustomRoutineStore(defaults: defaults)

        try store.save(definition)

        XCTAssertEqual(store.routines.first?.tags, ["edges", "custom"])
    }

    func testValidationRejectsUnknownBoardForBoardSpecificRoutine() {
        let definition = CustomRoutineDefinition(
            id: "custom.unknown-board",
            title: "Unknown board",
            subtitle: "",
            difficulty: nil,
            category: nil,
            tags: [],
            targetMode: .boardSpecific(boardID: "unknown-board"),
            steps: [validStep(targets: [.kind(.edge)])]
        )

        let issues = CustomRoutineValidator.issues(for: definition, availableBoards: BoardCatalog.all)

        XCTAssertTrue(issues.contains(.unknownBoard(boardID: "unknown-board")))
    }

    func testValidationRejectsGenericTargetsThatCannotResolve() {
        let definition = genericDefinition(targets: [ContactRequirement(kind: .edge, shape: .flat)])
        let jugOnlyBoard = BoardRevision(
            id: "fixture.jug-only",
            revisionID: "test-fixture",
            manufacturer: "Fixture Maker",
            name: "Jug Only",
            subtitle: "A board without edges.",
            dimensions: "10 × 5",
            aspectRatio: 2,
            contacts: [
                PhysicalContact(
                    id: "fixture.jug",
                    name: "Fixture jug",
                    kind: .jug
                )
            ],
            productURL: URL(string: "https://example.com/jug-only")!,
            photoAssetName: nil
        )

        let issues = CustomRoutineValidator.issues(for: definition, availableBoards: [jugOnlyBoard])

        XCTAssertTrue(issues.contains(.unresolvableSegmentTargets(stepIndex: 0, segmentIndex: 0)))
    }

    func testSaveRejectsRoutineWhoseImplicitNormalizedStepsEndInRest() throws {
        let suite = "CustomRoutineStoreTests.\(UUID().uuidString)"
        let defaults = try XCTUnwrap(UserDefaults(suiteName: suite))
        defer { defaults.removePersistentDomain(forName: suite) }
        let definition = CustomRoutineDefinition(
            id: "custom.trailing-rest",
            title: "Trailing rest",
            subtitle: "",
            difficulty: nil,
            category: nil,
            tags: [],
            targetMode: .boardSpecific(boardID: BoardCatalog.defaultBoard.id),
            steps: [
                WorkoutStepDefinition(
                    id: "timed-work",
                    title: "Timed work",
                    instruction: "Hang, then rest.",
                    accessory: "8s hang · 4s rest",
                    duration: 12,
                    phase: .hang,
                    segments: [
                        WorkoutSegmentDefinition(
                            kind: .work,
                            target: .fromLegacyTargets([.kind(.edge)]),
                            timing: .fixed,
                            duration: 8
                        ),
                        WorkoutSegmentDefinition(
                            kind: .rest,
                            target: nil,
                            timing: .fixed,
                            duration: 4
                        )
                    ],
                    activeDuration: 8
                )
            ]
        )

        XCTAssertThrowsError(try CustomRoutineStore(defaults: defaults).save(definition)) { error in
            guard case .validationFailed([.terminalRestStep]) = error as? CustomRoutineStoreError else {
                return XCTFail("Expected terminal-rest validation failure, got \(error)")
            }
        }
    }

    func testSaveRejectsRoutineWhoseAuthoredStepsEndInRest() throws {
        let suite = "CustomRoutineStoreTests.\(UUID().uuidString)"
        let defaults = try XCTUnwrap(UserDefaults(suiteName: suite))
        defer { defaults.removePersistentDomain(forName: suite) }
        let definition = CustomRoutineDefinition(
            id: "custom.explicit-trailing-rest",
            title: "Explicit trailing rest",
            subtitle: "",
            difficulty: nil,
            category: nil,
            tags: [],
            targetMode: .boardSpecific(boardID: BoardCatalog.defaultBoard.id),
            steps: [
                validStep(targets: [.kind(.edge)]),
                WorkoutStepDefinition(
                    id: "rest",
                    title: "Rest",
                    instruction: "",
                    accessory: "30s rest",
                    duration: 30,
                    phase: .rest,
                    segments: [
                        WorkoutSegmentDefinition(kind: .rest, target: nil, timing: .fixed, duration: 30)
                    ]
                )
            ]
        )

        XCTAssertThrowsError(try CustomRoutineStore(defaults: defaults).save(definition)) { error in
            guard case .validationFailed([.terminalRestStep]) = error as? CustomRoutineStoreError else {
                return XCTFail("Expected terminal-rest validation failure, got \(error)")
            }
        }
    }

    func testValidationAndSaveRejectRoutineWhoseCompoundStepEndsInRest() throws {
        let suite = "CustomRoutineStoreTests.\(UUID().uuidString)"
        let defaults = try XCTUnwrap(UserDefaults(suiteName: suite))
        defer { defaults.removePersistentDomain(forName: suite) }
        let definition = CustomRoutineDefinition(
            id: "custom.compound-trailing-rest",
            title: "Compound trailing rest",
            subtitle: "",
            difficulty: nil,
            category: nil,
            tags: [],
            targetMode: .boardSpecific(boardID: BoardCatalog.defaultBoard.id),
            steps: [
                WorkoutStepDefinition(
                    id: "compound-trailing-rest",
                    title: "Compound trailing rest",
                    instruction: "Hang, then rest.",
                    accessory: "8s hang · 4s rest",
                    duration: 12,
                    phase: .hang,
                    segments: [
                        WorkoutSegmentDefinition(
                            kind: .work,
                            target: .fromLegacyTargets([.kind(.edge)]),
                            timing: .fixed,
                            duration: 8
                        ),
                        WorkoutSegmentDefinition(
                            kind: .rest,
                            target: nil,
                            timing: .fixed,
                            duration: 4
                        )
                    ]
                )
            ]
        )

        XCTAssertEqual(
            CustomRoutineValidator.issues(for: definition, availableBoards: BoardCatalog.all),
            [.terminalRestStep]
        )
        XCTAssertThrowsError(try CustomRoutineStore(defaults: defaults).save(definition)) { error in
            guard case .validationFailed([.terminalRestStep]) = error as? CustomRoutineStoreError else {
                return XCTFail("Expected terminal-rest validation failure, got \(error)")
            }
        }
    }

    func testFactualRequirementsUseTheSameGrammarInEveryRoutineMode() {
        let boardSpecific = CustomRoutineDefinition(
            id: "custom.board-mode-mismatch",
            title: "Board mismatch",
            subtitle: "",
            difficulty: nil,
            category: nil,
            tags: [],
            targetMode: .boardSpecific(boardID: BoardCatalog.defaultBoard.id),
            steps: [validStep(
                targets: [.kind(.jug)],
                segments: [
                    WorkoutSegmentDefinition(
                        kind: .work,
                        target: .fromLegacyTargets([.edge(depth: .category(.medium))]),
                        timing: .fixed,
                        duration: 10
                    )
                ]
            )]
        )
        let generic = genericDefinition(
            targets: [.kind(.edge)],
            segments: [
                WorkoutSegmentDefinition(
                    kind: .work,
                    target: .fromLegacyTargets([.kind(.edge)]),
                    timing: .fixed,
                    duration: 10
                )
            ]
        )

        let boardIssues = CustomRoutineValidator.issues(
            for: boardSpecific,
            availableBoards: BoardCatalog.all
        )
        let genericIssues = CustomRoutineValidator.issues(
            for: generic,
            availableBoards: BoardCatalog.all
        )

        XCTAssertFalse(boardIssues.contains(.targetModeMismatch(stepIndex: 0, segmentIndex: nil)))
        XCTAssertFalse(boardIssues.contains(.targetModeMismatch(stepIndex: 0, segmentIndex: 0)))
        XCTAssertFalse(genericIssues.contains(.targetModeMismatch(stepIndex: 0, segmentIndex: nil)))
        XCTAssertFalse(genericIssues.contains(.targetModeMismatch(stepIndex: 0, segmentIndex: 0)))
    }

    func testGenericModeRejectsExactContactIDsBeforePersistenceNormalization() {
        let definition = genericDefinition(
            targets: [ContactRequirement(contactID: "board-only-edge", kind: .edge, selection: .single)]
        )

        let issues = CustomRoutineValidator.issues(
            for: definition,
            availableBoards: BoardCatalog.all
        )

        XCTAssertTrue(issues.contains(.targetModeMismatch(stepIndex: 0, segmentIndex: 0)))
    }

    func testStoreNormalizesOlderGenericExactContactIDsOnLoad() throws {
        let suite = "CustomRoutineStoreTests.\(UUID().uuidString)"
        let defaults = try XCTUnwrap(UserDefaults(suiteName: suite))
        defer { defaults.removePersistentDomain(forName: suite) }
        let storedDefinition = genericDefinition(
            targets: [ContactRequirement(contactID: "old-board-edge", kind: .edge, selection: .single)]
        )
        defaults.set(
            try JSONEncoder().encode(CustomRoutineLibrary(routines: [storedDefinition])),
            forKey: CustomRoutineStore.defaultKey
        )

        let store = CustomRoutineStore(defaults: defaults)

        XCTAssertNil(store.routines[0].steps[0].workRequirements[0].contactID)
        XCTAssertEqual(store.routines[0].steps[0].workRequirements[0].kind, .edge)
    }

    func testSaveAcceptsGenericEitherHandTarget() throws {
        let suite = "CustomRoutineStoreTests.\(UUID().uuidString)"
        let defaults = try XCTUnwrap(UserDefaults(suiteName: suite))
        defer { defaults.removePersistentDomain(forName: suite) }
        let requirement = ContactRequirement(
            kind: .edge,
            depth: .range(.init(minimum: 14, maximum: 14)),
            handCapacity: 1,
            selection: .single
        )
        let definition = CustomRoutineDefinition(
            id: "custom.generic-either",
            title: "Generic either",
            subtitle: "",
            difficulty: nil,
            category: nil,
            tags: [],
            targetMode: .generic,
            steps: [WorkoutStepDefinition(
                id: "either", title: "Either", instruction: "Hang.", accessory: "",
                duration: 10, phase: .hang,
                segments: [
                    WorkoutSegmentDefinition(
                        kind: .work,
                        target: .fromLegacyTargets([requirement]),
                        timing: .fixed,
                        duration: 10
                    )
                ],
                handUse: .either, side: .both
            )]
        )

        let store = CustomRoutineStore(defaults: defaults)
        try store.save(definition)

        XCTAssertNil(store.routines.first?.steps.first?.workRequirements.first?.contactID)
    }

    func testBoardSpecificEitherHandSidedTapRemainsSaveableForBothSides() throws {
        let suite = "CustomRoutineStoreTests.\(UUID().uuidString)"
        let defaults = try XCTUnwrap(UserDefaults(suiteName: suite))
        defer { defaults.removePersistentDomain(forName: suite) }
        let board = mirroredBoard()
        var step = CustomRoutineStepDraft(
            id: "either-after-tap", title: "Either edge", instruction: "", accessory: "", duration: 10,
            phase: .hang, targets: [], timing: .fixed, handUse: .single, side: .left
        )

        CustomRoutineBoardPreview.toggle(board.contacts[0], in: &step, on: board)
        XCTAssertEqual(step.targets.first?.contactID, "left")

        step.transitionHandUse(to: .either)

        let expectedTarget = factualRequirement(contactID: nil, selection: .single)
        XCTAssertEqual(step.targets, [expectedTarget])
        XCTAssertEqual(
            CustomRoutineBoardPreview.contactIDs(for: step, on: board),
            Set(["left", "right"])
        )
        let definition = CustomRoutineDefinition(
            id: "custom.board-specific-either-after-tap",
            title: "Board-specific either edge",
            subtitle: "",
            difficulty: nil,
            category: nil,
            tags: [],
            targetMode: .boardSpecific(boardID: board.id),
            steps: [WorkoutStepDefinition(
                id: step.id,
                title: step.title,
                instruction: step.instruction,
                accessory: step.accessory,
                duration: step.duration,
                phase: step.phase,
                segments: [
                    WorkoutSegmentDefinition(
                        kind: .work,
                        target: .fromLegacyTargets(step.targets),
                        timing: .fixed,
                        duration: step.duration
                    )
                ],
                handUse: step.handUse,
                side: step.side
            )]
        )

        XCTAssertTrue(CustomRoutineValidator.issues(for: definition, availableBoards: [board]).isEmpty)
        let store = CustomRoutineStore(defaults: defaults, availableBoards: [board])
        XCTAssertNoThrow(try store.save(definition))
        XCTAssertEqual(store.routines.first?.steps.first?.workRequirements, [expectedTarget])
    }

    func testSavePersistsOnlyLiteralRowsThroughSharedNormalization() throws {
        let suite = "CustomRoutineStoreTests.\(UUID().uuidString)"
        let defaults = try XCTUnwrap(UserDefaults(suiteName: suite))
        defer { defaults.removePersistentDomain(forName: suite) }
        let source = CustomRoutineDefinition(
            id: "custom.compound",
            title: "Compound source",
            subtitle: "",
            difficulty: nil,
            category: nil,
            tags: [],
            targetMode: .boardSpecific(boardID: BoardCatalog.defaultBoard.id),
            steps: [
                WorkoutStepDefinition(
                    id: "repeat",
                    title: "Repeat",
                    instruction: "Work then rest.",
                    accessory: "8s · 4s",
                    duration: 12,
                    phase: .hang,
                    segments: [
                        WorkoutSegmentDefinition(
                            kind: .work,
                            target: .fromLegacyTargets([.kind(.edge)]),
                            timing: .fixed,
                            duration: 8
                        ),
                        WorkoutSegmentDefinition(
                            kind: .rest,
                            target: nil,
                            timing: .fixed,
                            duration: 4
                        )
                    ],
                    gripType: .halfCrimp
                ),
                WorkoutStepDefinition(
                    id: "implicit",
                    title: "Open hang",
                    instruction: "Hang with open timing.",
                    accessory: "Up to 20s",
                    duration: 20,
                    phase: .hang,
                    segments: [
                        WorkoutSegmentDefinition(
                            kind: .work,
                            target: .fromLegacyTargets([.kind(.edge)]),
                            timing: .undefined,
                            duration: nil
                        )
                    ]
                ),
                WorkoutStepDefinition(
                    id: "stopwatch",
                    title: "Maximum hang",
                    instruction: "Stop when you release.",
                    accessory: "Up to 30s",
                    duration: 30,
                    phase: .hang,
                    segments: [
                        WorkoutSegmentDefinition(
                            kind: .work,
                            target: .fromLegacyTargets([.kind(.edge)]),
                            timing: .stopwatch,
                            duration: nil
                        )
                    ],
                    gripType: .openHand
                )
            ]
        )
        let store = CustomRoutineStore(defaults: defaults)

        try store.save(source)

        let stored = try XCTUnwrap(store.routines.first)
        XCTAssertEqual(stored.steps.map(\.id), [
            "repeat.segment-1", "repeat.segment-2", "implicit", "stopwatch"
        ])
        XCTAssertEqual(stored.steps.map(\.phase), [.hang, .rest, .hang, .hang])
        XCTAssertEqual(stored.steps.map(\.workRequirements), [
            [.kind(.edge)],
            [],
            [.kind(.edge)],
            [.kind(.edge)]
        ])
        XCTAssertEqual(stored.steps.map { $0.segments.count }, [1, 1, 1, 1])
        let persistedData = try XCTUnwrap(defaults.data(forKey: CustomRoutineStore.defaultKey))
        let persistedJSON = try XCTUnwrap(
            try JSONSerialization.jsonObject(with: persistedData) as? [String: Any]
        )
        let persistedRoutines = try XCTUnwrap(persistedJSON["routines"] as? [[String: Any]])
        let persistedSteps = try XCTUnwrap(persistedRoutines.first?["steps"] as? [[String: Any]])
        XCTAssertEqual(persistedSteps.first?["activeDuration"] as? Double, 8)
        XCTAssertNil(persistedSteps.first?["gripType"])
        XCTAssertNil(persistedSteps.first?["fingerConfiguration"])
        XCTAssertEqual(stored.steps[2].segments[0].timing, .undefined)
        XCTAssertEqual(stored.steps[3].segments[0].timing, .stopwatch)
        XCTAssertEqual(CustomRoutineDraft(editing: stored).definition(), stored)

        let reloaded = CustomRoutineStore(defaults: defaults)
        XCTAssertEqual(reloaded.routines, [stored])
    }

    func testSavePersistsGenericCompoundWorkAndTargetlessRestRows() throws {
        let suite = "CustomRoutineStoreTests.\(UUID().uuidString)"
        let defaults = try XCTUnwrap(UserDefaults(suiteName: suite))
        defer { defaults.removePersistentDomain(forName: suite) }
        let definition = CustomRoutineDefinition(
            id: "custom.generic-compound",
            title: "Generic repeaters",
            subtitle: "",
            difficulty: nil,
            category: nil,
            tags: [],
            targetMode: .generic,
            steps: [
                WorkoutStepDefinition(
                    id: "repeat",
                    title: "Repeat",
                    instruction: "Work, then rest.",
                    accessory: "8s · 4s",
                    duration: 12,
                    phase: .hang,
                    segments: [
                        WorkoutSegmentDefinition(
                            kind: .work,
                            target: .fromLegacyTargets([.kind(.jug)]),
                            timing: .fixed,
                            duration: 8
                        ),
                        WorkoutSegmentDefinition(
                            kind: .rest,
                            target: nil,
                            timing: .fixed,
                            duration: 4
                        )
                    ]
                ),
                WorkoutStepDefinition(
                    id: "follow-up",
                    title: "Follow-up",
                    instruction: "Finish with work.",
                    accessory: "6s",
                    duration: 6,
                    phase: .hang,
                    segments: [
                        WorkoutSegmentDefinition(
                            kind: .work,
                            target: .fromLegacyTargets([.kind(.jug)]),
                            timing: .fixed,
                            duration: 6
                        )
                    ]
                )
            ]
        )
        let store = CustomRoutineStore(defaults: defaults)

        try store.save(definition)

        let stored = try XCTUnwrap(store.routines.first)
        XCTAssertEqual(stored.steps.map(\.phase), [.hang, .rest, .hang])
        XCTAssertEqual(stored.steps.map(\.workRequirements), [[.kind(.jug)], [], [.kind(.jug)]])
        XCTAssertEqual(stored.steps.map { $0.segments.count }, [1, 1, 1])

        let reloaded = CustomRoutineStore(defaults: defaults)
        XCTAssertEqual(reloaded.routines, [stored])
    }

    func testValidationRejectsInvalidNamespaceAndBuiltInCollisionIDs() throws {
        let blank = genericDefinition(id: "   ")
        let foreign = genericDefinition(id: "routine.foreign")
        let builtInID = try XCTUnwrap(PlanCatalog.all.first?.id)
        let collision = genericDefinition(id: builtInID)

        XCTAssertTrue(
            CustomRoutineValidator.issues(for: blank, availableBoards: BoardCatalog.all)
                .contains(.invalidID(id: "   "))
        )
        XCTAssertTrue(
            CustomRoutineValidator.issues(for: foreign, availableBoards: BoardCatalog.all)
                .contains(.invalidID(id: "routine.foreign"))
        )
        XCTAssertTrue(
            CustomRoutineValidator.issues(for: collision, availableBoards: BoardCatalog.all)
                .contains(.builtInIDCollision(id: builtInID))
        )
    }

    func testValidationRejectsRestStepTargets() {
        let definition = CustomRoutineDefinition(
            id: "custom.rest-targets",
            title: "Rest target",
            subtitle: "",
            difficulty: nil,
            category: nil,
            tags: [],
            targetMode: .generic,
            steps: [
                WorkoutStepDefinition(
                    id: "rest",
                    title: "Rest",
                    instruction: "Rest.",
                    accessory: "10s",
                    duration: 10,
                    phase: .rest,
                    segments: [
                        WorkoutSegmentDefinition(
                            kind: .rest,
                            target: .fromLegacyTargets([.kind(.edge)]),
                            timing: .fixed,
                            duration: 10
                        )
                    ]
                )
            ]
        )

        XCTAssertTrue(
            CustomRoutineValidator.issues(for: definition, availableBoards: BoardCatalog.all)
                .contains(.restStepHasTargets(stepIndex: 0))
        )
    }

    func testValidationRejectsInvalidSegmentTimingDurations() {
        let definition = genericDefinition(
            segments: [
                WorkoutSegmentDefinition(kind: .work, target: .fromLegacyTargets([.kind(.jug)]), timing: .fixed, duration: nil),
                WorkoutSegmentDefinition(kind: .work, target: .fromLegacyTargets([.kind(.jug)]), timing: .stopwatch, duration: 10)
            ]
        )

        let issues = CustomRoutineValidator.issues(for: definition, availableBoards: BoardCatalog.all)

        XCTAssertTrue(issues.contains(.missingFixedSegmentDuration(stepIndex: 0, segmentIndex: 0)))
        XCTAssertTrue(issues.contains(.unexpectedSegmentDuration(stepIndex: 0, segmentIndex: 1)))
        XCTAssertTrue(issues.contains(.invalidCompoundSegmentTiming(stepIndex: 0, segmentIndex: 1)))
    }

    func testValidationRejectsCompoundSegmentDurationsThatDoNotMatchTheStepDuration() {
        let definition = genericDefinition(
            segments: [
                WorkoutSegmentDefinition(kind: .work, target: .fromLegacyTargets([.kind(.jug)]), timing: .fixed, duration: 7),
                WorkoutSegmentDefinition(kind: .rest, target: nil, timing: .fixed, duration: 4)
            ]
        )

        XCTAssertTrue(
            CustomRoutineValidator.issues(for: definition, availableBoards: BoardCatalog.all)
                .contains(.compoundDurationMismatch(stepIndex: 0))
        )
    }

    func testCustomProvenanceIsOnlyPlanMetadataAllowedToOmitSourceURL() {
        let custom = PlanMetadata(
            title: "Custom",
            subtitle: "Local",
            level: "Custom",
            sourceLabel: "Created in Hang Ten",
            sourceURL: nil,
            provenance: .custom
        )
        let adapted = PlanMetadata(
            title: "Adapted",
            subtitle: "Linked",
            level: "Test",
            sourceLabel: "Test source",
            sourceURL: nil,
            provenance: .adapted
        )

        XCTAssertTrue(PlanLibraryValidator.issues(for: library(metadata: custom), availableBoards: BoardCatalog.all).isEmpty)
        XCTAssertFalse(PlanLibraryValidator.issues(for: library(metadata: adapted), availableBoards: BoardCatalog.all).isEmpty)
    }

    func testValidationRejectsInvalidUnilateralStepSemantics() {
        let definition = CustomRoutineDefinition(
            id: "custom.invalid-unilateral",
            title: "Invalid unilateral",
            subtitle: "",
            difficulty: nil,
            category: nil,
            tags: [],
            targetMode: .generic,
            steps: [WorkoutStepDefinition(
                id: "invalid",
                title: "Invalid",
                instruction: "",
                accessory: "",
                duration: 10,
                phase: .pull,
                handUse: .single,
                side: .both,
                action: .loadedLift,
                repetitions: 0
            )]
        )

        let issues = CustomRoutineValidator.issues(
            for: definition,
            availableBoards: BoardCatalog.all
        )

        XCTAssertTrue(issues.contains(.invalidHandUseSide(stepIndex: 0)))
        XCTAssertTrue(issues.contains(.invalidActionRepetitions(stepIndex: 0)))
    }

    private func genericDefinition(
        id: String = "custom.generic",
        subtitle: String = "",
        difficulty: String? = nil,
        category: String? = nil,
        tags: [String] = [],
        targets: [ContactRequirement] = [.kind(.jug)],
        segments: [WorkoutSegmentDefinition] = []
    ) -> CustomRoutineDefinition {
        CustomRoutineDefinition(
            id: id,
            title: "Generic routine",
            subtitle: subtitle,
            difficulty: difficulty,
            category: category,
            tags: tags,
            targetMode: .generic,
            steps: [validStep(targets: targets, segments: segments)]
        )
    }

    private func validStep(
        targets: [ContactRequirement],
        segments: [WorkoutSegmentDefinition] = []
    ) -> WorkoutStepDefinition {
        let resolvedSegments: [WorkoutSegmentDefinition]
        if segments.isEmpty {
            resolvedSegments = [
                WorkoutSegmentDefinition(
                    kind: .work,
                    target: .fromLegacyTargets(targets),
                    timing: .fixed,
                    duration: 10
                )
            ]
        } else {
            resolvedSegments = segments
        }
        return WorkoutStepDefinition(
            id: "step-1",
            title: "Hang",
            instruction: "Hang.",
            accessory: "10s",
            duration: 10,
            phase: .hang,
            segments: resolvedSegments,
            activeDuration: 10
        )
    }

    private func factualRequirement(
        contactID: String?,
        selection: ContactSelectionPolicy
    ) -> ContactRequirement {
        ContactRequirement(
            contactID: contactID,
            kind: .edge,
            shape: .flat,
            depth: .range(MillimeterRange(minimum: 18, maximum: 22)),
            fingerCapacity: 2,
            handCapacity: 1,
            selection: selection
        )
    }

    private func mirroredBoard() -> BoardRevision {
        let contacts = [
            PhysicalContact(
                id: "left", name: "Left edge", kind: .edge,
                shape: .flat, fingerCapacity: 2, handCapacity: 1,
                depth: .range(.init(minimum: 18, maximum: 22)), gripTypes: [.halfCrimp], side: .left,
                pairedContactID: "right"
            ),
            PhysicalContact(
                id: "right", name: "Right edge", kind: .edge,
                shape: .flat, fingerCapacity: 2, handCapacity: 1,
                depth: .range(.init(minimum: 18, maximum: 22)), gripTypes: [.halfCrimp], side: .right,
                pairedContactID: "left"
            )
        ]
        let geometry = Dictionary(uniqueKeysWithValues: contacts.enumerated().map { index, contact in
            (contact.id, [BoardContactPiece(
                id: "\(contact.id)-piece",
                contactID: contact.id,
                frame: CGRect(x: index == 0 ? 0.1 : 0.8, y: 0, width: 0.1, height: 0.1),
                shape: .roundedRect(cornerRadiusFraction: 0),
                treatment: .surface
            )])
        })
        return BoardRevision(
            id: "custom-store-mirrored", revisionID: "test", manufacturer: "Fixture",
            name: "Mirrored", subtitle: "", dimensions: nil, aspectRatio: 1,
            contacts: contacts, productURL: URL(string: "https://example.com/mirrored")!,
            photoAssetName: nil,
            presentations: [BoardPresentation(
                id: "front", name: "Front", aspectRatio: 1, isDefault: true,
                media: .raster(BoardRasterMedia(assetPath: "", contactGeometry: geometry))
            )]
        )
    }

    private func library(metadata: PlanMetadata) -> PlanLibraryDefinition {
        PlanLibraryDefinition(
            metadata: PlanLibraryMetadata(
                id: "test.library",
                title: "Test library",
                generatedAt: "2026-08-05"
            ),
            blocks: [WorkoutBlockDefinition(id: "test.block", steps: [validStep(targets: [.kind(.jug)])])],
            plans: [PlanDefinition(id: "test.plan", metadata: metadata, boardID: nil, blocks: [WorkoutBlockReference(blockID: "test.block")])]
        )
    }
}
