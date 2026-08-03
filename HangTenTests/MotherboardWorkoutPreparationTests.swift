import XCTest
@testable import HangTen

final class MotherboardWorkoutPreparationTests: XCTestCase {
    func testWorkoutPreparationHandoffAllowsOnlyTheFirstEvent() {
        var handoff = MotherboardWorkoutPreparationHandoff()

        XCTAssertTrue(handoff.accept())
        XCTAssertFalse(handoff.accept())
    }

    func testTareCompletionWaitsForExplicitBodyweightCaptureStart() {
        var preparation = MotherboardWorkoutPreparation()

        XCTAssertEqual(preparation.step, .tare)
        XCTAssertTrue(preparation.startTare())

        preparation.completeTare(isStreaming: true)

        XCTAssertEqual(preparation.step, .bodyweight)
        XCTAssertNil(preparation.bodyweightKGF)
        XCTAssertTrue(preparation.isAwaitingBodyweightCapture)
        XCTAssertFalse(preparation.isBodyweightCaptureInProgress)

        XCTAssertTrue(preparation.startBodyweightCapture())
        XCTAssertTrue(preparation.isBodyweightCaptureInProgress)

        preparation.completeBodyweight(with: 63.5, isStreaming: true)

        XCTAssertEqual(preparation.step, .ready)
        XCTAssertEqual(preparation.bodyweightKGF, 63.5)
        XCTAssertEqual(preparation.result, .completed(bodyweightKGF: 63.5))
        XCTAssertTrue(preparation.canContinue(isStreaming: true))
    }

    func testInvalidBodyweightCaptureRemainsOnBodyweightStep() {
        var preparation = MotherboardWorkoutPreparation()
        XCTAssertTrue(preparation.startTare())
        preparation.completeTare(isStreaming: true)
        XCTAssertTrue(preparation.startBodyweightCapture())

        for value in [nil, .nan, .infinity, -.infinity, 0, -1] as [Double?] {
            preparation.completeBodyweight(with: value, isStreaming: true)

            XCTAssertEqual(preparation.step, .bodyweight)
            XCTAssertNil(preparation.bodyweightKGF)
            XCTAssertEqual(preparation.result, .inProgress)
            XCTAssertEqual(preparation.failure, .invalidBodyweightCapture)
            XCTAssertFalse(preparation.canContinue(isStreaming: true))

            preparation.retryBodyweight()
            XCTAssertTrue(preparation.startBodyweightCapture())
        }
    }

    func testTareCancellationDoesNotAdvanceUntilStreamingCompletion() {
        var preparation = MotherboardWorkoutPreparation()
        XCTAssertTrue(preparation.startTare())

        preparation.completeTare(isStreaming: false)

        XCTAssertEqual(preparation.step, .tare)
        XCTAssertEqual(preparation.result, .inProgress)
        XCTAssertEqual(preparation.failure, .tareInterrupted)

        preparation.retryTare()
        XCTAssertTrue(preparation.startTare())
        preparation.completeTare(isStreaming: true)

        XCTAssertEqual(preparation.step, .bodyweight)
        XCTAssertNil(preparation.failure)
    }

    func testBodyweightCancellationDoesNotCompletePreparation() {
        var preparation = MotherboardWorkoutPreparation()
        XCTAssertTrue(preparation.startTare())
        preparation.completeTare(isStreaming: true)
        XCTAssertTrue(preparation.startBodyweightCapture())

        preparation.completeBodyweight(with: 63.5, isStreaming: false)

        XCTAssertEqual(preparation.step, .bodyweight)
        XCTAssertNil(preparation.bodyweightKGF)
        XCTAssertEqual(preparation.result, .inProgress)
        XCTAssertEqual(preparation.failure, .bodyweightCaptureInterrupted)
        XCTAssertFalse(preparation.canContinue(isStreaming: true))

        preparation.retryBodyweight()
        XCTAssertTrue(preparation.startBodyweightCapture())
        preparation.completeBodyweight(with: 63.5, isStreaming: true)

        XCTAssertEqual(preparation.step, .ready)
        XCTAssertEqual(preparation.bodyweightKGF, 63.5)
        XCTAssertTrue(preparation.canContinue(isStreaming: true))
    }

    func testStreamingLossAfterReadyInvalidatesTheCapturedBaseline() {
        var preparation = MotherboardWorkoutPreparation()
        XCTAssertTrue(preparation.startTare())
        preparation.completeTare(isStreaming: true)
        XCTAssertTrue(preparation.startBodyweightCapture())
        preparation.completeBodyweight(with: 63.5, isStreaming: true)

        XCTAssertFalse(preparation.canContinue(isStreaming: false))

        preparation.invalidateForStreamingLoss()

        XCTAssertEqual(preparation.step, .bodyweight)
        XCTAssertNil(preparation.bodyweightKGF)
        XCTAssertEqual(preparation.result, .inProgress)
        XCTAssertEqual(preparation.failure, .bodyweightCaptureInterrupted)
        XCTAssertFalse(preparation.canContinue(isStreaming: false))
    }

    func testSkipIsTerminalAtEveryPreparationStage() {
        var tarePreparation = MotherboardWorkoutPreparation()
        tarePreparation.skip()
        XCTAssertFalse(tarePreparation.startTare())
        tarePreparation.completeTare(isStreaming: true)
        tarePreparation.retryTare()

        XCTAssertEqual(tarePreparation.step, .tare)
        XCTAssertNil(tarePreparation.bodyweightKGF)
        XCTAssertEqual(tarePreparation.result, .skipped)

        var bodyweightPreparation = MotherboardWorkoutPreparation()
        XCTAssertTrue(bodyweightPreparation.startTare())
        bodyweightPreparation.completeTare(isStreaming: true)
        bodyweightPreparation.skip()
        XCTAssertFalse(bodyweightPreparation.startBodyweightCapture())
        bodyweightPreparation.completeBodyweight(with: 63.5, isStreaming: true)
        bodyweightPreparation.retryBodyweight()

        XCTAssertEqual(bodyweightPreparation.step, .bodyweight)
        XCTAssertNil(bodyweightPreparation.bodyweightKGF)
        XCTAssertEqual(bodyweightPreparation.result, .skipped)

        var readyPreparation = MotherboardWorkoutPreparation()
        XCTAssertTrue(readyPreparation.startTare())
        readyPreparation.completeTare(isStreaming: true)
        XCTAssertTrue(readyPreparation.startBodyweightCapture())
        readyPreparation.completeBodyweight(with: 63.5, isStreaming: true)
        readyPreparation.skip()
        readyPreparation.completeTare(isStreaming: true)
        readyPreparation.completeBodyweight(with: 75, isStreaming: true)
        readyPreparation.retryBodyweight()

        XCTAssertEqual(readyPreparation.step, .ready)
        XCTAssertNil(readyPreparation.bodyweightKGF)
        XCTAssertEqual(readyPreparation.result, .skipped)
    }

    func testOnlyInitialStreamingStartRequiresPreparation() {
        XCTAssertTrue(MotherboardWorkoutPreparation.requiresPreparation(
            isInitialStart: true,
            isStreaming: true
        ))
        XCTAssertFalse(MotherboardWorkoutPreparation.requiresPreparation(
            isInitialStart: false,
            isStreaming: true
        ))
        XCTAssertFalse(MotherboardWorkoutPreparation.requiresPreparation(
            isInitialStart: true,
            isStreaming: false
        ))
    }

    func testForceFormattingUsesTheRequestedLocale() {
        XCTAssertEqual(
            MotherboardUserVisibleFormatting.force(
                12.3,
                unit: .kgf,
                locale: Locale(identifier: "en_US")
            ),
            "12.3 kgf"
        )
        XCTAssertEqual(
            MotherboardUserVisibleFormatting.force(
                12.3,
                unit: .kgf,
                locale: Locale(identifier: "de_DE")
            ),
            "12,3 kgf"
        )
    }

    func testPercentageFormattingUsesTheRequestedLocalePercentStyle() {
        XCTAssertEqual(
            MotherboardUserVisibleFormatting.percentage(
                12.4,
                locale: Locale(identifier: "en_US")
            ),
            "12%"
        )
        XCTAssertEqual(
            MotherboardUserVisibleFormatting.percentage(
                12.4,
                locale: Locale(identifier: "de_DE")
            ),
            "12\u{00a0}%"
        )
    }

    func testPercentageOverflowUsesLocalizedLimitWithPlusSuffix() {
        XCTAssertEqual(
            MotherboardUserVisibleFormatting.percentage(
                12_000,
                locale: Locale(identifier: "en_US")
            ),
            "9,999%+"
        )
        XCTAssertEqual(
            MotherboardUserVisibleFormatting.percentage(
                12_000,
                locale: Locale(identifier: "de_DE")
            ),
            "9.999\u{00a0}%+"
        )
    }

    func testDurationFormattingLocalizesAbbreviatedAndSettingsUnits() {
        XCTAssertEqual(
            MotherboardUserVisibleFormatting.duration(
                1.2,
                locale: Locale(identifier: "en_US"),
                unitStyle: .short,
                fractionDigits: 1
            ),
            "1.2s"
        )
        XCTAssertEqual(
            MotherboardUserVisibleFormatting.duration(
                1.2,
                locale: Locale(identifier: "de_DE"),
                unitStyle: .short,
                fractionDigits: 1
            ),
            "1,2s"
        )
        XCTAssertEqual(
            MotherboardUserVisibleFormatting.duration(
                5,
                locale: Locale(identifier: "en_US"),
                unitStyle: .long,
                fractionDigits: 0
            ),
            "5 seconds"
        )
        XCTAssertEqual(
            MotherboardUserVisibleFormatting.duration(
                5,
                locale: Locale(identifier: "de_DE"),
                unitStyle: .long,
                fractionDigits: 0
            ),
            "5 Sekunden"
        )
    }

    func testFormattingRejectsNegativeAndNonFiniteValues() {
        for value in [-1, .nan, .infinity, -.infinity] {
            XCTAssertNil(
                MotherboardUserVisibleFormatting.force(value, unit: .kgf, locale: Locale(identifier: "en_US"))
            )
            XCTAssertNil(
                MotherboardUserVisibleFormatting.percentage(value, locale: Locale(identifier: "en_US"))
            )
            XCTAssertNil(
                MotherboardUserVisibleFormatting.duration(
                    value,
                    locale: Locale(identifier: "en_US"),
                    unitStyle: .short,
                    fractionDigits: 1
                )
            )
        }
    }
}
