import Foundation
import SwiftUI

struct MotherboardWorkoutPreparationView: View {
    @ObservedObject var service: MotherboardBluetoothService
    let unit: MotherboardForceUnit
    let bodyweightCaptureDuration: TimeInterval
    let onComplete: (Double?) -> Void
    let onSkip: () -> Void

    @State private var preparation = MotherboardWorkoutPreparation()
    @State private var didRequestTare = false
    @State private var didStartBodyweightCapture = false

    var body: some View {
        NavigationStack {
            VStack(alignment: .leading, spacing: 22) {
                switch preparation.step {
                case .tare:
                    tareContent
                case .bodyweight:
                    bodyweightContent
                case .ready:
                    readyContent
                }
            }
            .padding(24)
            .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
            .background(Color.hangBackground)
            .navigationTitle("Prepare Motherboard")
            .navigationBarTitleDisplayMode(.inline)
        }
        .interactiveDismissDisabled()
        .onAppear {
            guard service.state != .streaming else { return }
            handleStreamingLoss()
        }
        .onChange(of: service.state) { _, state in
            guard state != .streaming else { return }
            handleStreamingLoss()
        }
        .onChange(of: service.tareCompletionCount) { _, _ in
            guard didRequestTare, preparation.step == .tare else { return }
            didRequestTare = false
            preparation.completeTare(isStreaming: service.state == .streaming)
        }
        .onChange(of: service.isMeasuringBodyweight) { _, isMeasuring in
            guard didStartBodyweightCapture, !isMeasuring, preparation.isBodyweightCaptureInProgress else { return }
            didStartBodyweightCapture = false
            preparation.completeBodyweight(
                with: service.bodyweightKGF,
                isStreaming: service.state == .streaming
            )
        }
    }

    private var tareContent: some View {
        VStack(alignment: .leading, spacing: 16) {
            SectionLabel(title: "Step 1 of 2")
            Text("Tare board")
                .font(.system(size: 30, weight: .bold, design: .rounded))
                .foregroundStyle(Color.hangInk)
            Text("Remove your hands and all weight from the board while it establishes zero load.")
                .font(.system(size: 16, weight: .medium, design: .rounded))
                .foregroundStyle(Color.hangMuted)

            if preparation.isTareInProgress {
                ProgressView(
                    value: Double(service.tareSamplesCollected),
                    total: Double(service.tareSampleTarget)
                )
                .tint(Color.hangGreenDark)

                Text("\(service.tareSamplesCollected) of \(service.tareSampleTarget) tare samples")
                    .font(.system(size: 14, weight: .bold, design: .rounded))
                    .foregroundStyle(Color.hangInk)
            } else {
                Button("Start tare", action: startTare)
                    .buttonStyle(.borderedProminent)
                    .tint(Color.hangGreenDark)
                    .disabled(service.state != .streaming)
            }

            if preparation.failure == .tareInterrupted {
                Text("The sensor stopped streaming before tare completed. Reconnect it, then try again or skip preparation.")
                    .font(.system(size: 15, weight: .medium, design: .rounded))
                    .foregroundStyle(Color.hangMuted)

                Button("Try tare again", action: retryTare)
                    .buttonStyle(.bordered)
                    .tint(Color.hangGreenDark)
                    .disabled(service.state != .streaming)
            }

            Button("Skip preparation", action: skipPreparation)
                .font(.system(size: 15, weight: .bold, design: .rounded))
                .foregroundStyle(Color.hangMuted)
        }
    }

    @ViewBuilder
    private var bodyweightContent: some View {
        if preparation.isBodyweightCaptureInProgress {
            TimelineView(.periodic(from: .now, by: 0.1)) { context in
                bodyweightContent(at: context.date)
            }
        } else {
            bodyweightContent(at: .now)
        }
    }

    private func bodyweightContent(at date: Date) -> some View {
        let progress = bodyweightProgress(at: date)
        let remaining = max(0, bodyweightCaptureDuration * (1 - progress))

        return VStack(alignment: .leading, spacing: 16) {
            SectionLabel(title: "Step 2 of 2")
            Text(preparation.isBodyweightCaptureInProgress ? "Capture bodyweight" : "Ready to hang")
                .font(.system(size: 30, weight: .bold, design: .rounded))
                .foregroundStyle(Color.hangInk)
            Text(preparation.isBodyweightCaptureInProgress
                 ? "Hang relaxed on the jugs for \(durationText(bodyweightCaptureDuration)). Keep still while the board averages your load."
                 : "Get onto the relaxed jugs, then start the timed bodyweight measurement when you are settled.")
                .font(.system(size: 16, weight: .medium, design: .rounded))
                .foregroundStyle(Color.hangMuted)

            if preparation.isBodyweightCaptureInProgress {
                ProgressView(value: progress)
                    .tint(Color.hangGreenDark)

                HStack {
                    Text("\(service.bodyweightSampleCount) samples")
                    Spacer()
                    Text("\(durationText(remaining)) remaining")
                }
                .font(.system(size: 14, weight: .bold, design: .rounded))
                .foregroundStyle(Color.hangInk)
            } else if preparation.isAwaitingBodyweightCapture {
                Button("Start bodyweight measurement", action: startBodyweightCapture)
                    .buttonStyle(.borderedProminent)
                    .tint(Color.hangGreenDark)
                    .disabled(service.state != .streaming)
            }

            if let failure = preparation.failure {
                Text(bodyweightFailureText(for: failure))
                    .font(.system(size: 15, weight: .medium, design: .rounded))
                    .foregroundStyle(Color.hangMuted)

                Button("Retry capture", action: retryBodyweightCapture)
                    .buttonStyle(.bordered)
                    .tint(Color.hangGreenDark)
                    .disabled(service.state != .streaming)
            }

            Button("Skip bodyweight", action: skipPreparation)
                .font(.system(size: 15, weight: .bold, design: .rounded))
                .foregroundStyle(Color.hangMuted)
        }
    }

    private var readyContent: some View {
        VStack(alignment: .leading, spacing: 16) {
            SectionLabel(title: "Preparation complete")
            Text("Ready to train")
                .font(.system(size: 30, weight: .bold, design: .rounded))
                .foregroundStyle(Color.hangInk)

            if let bodyweightKGF = preparation.bodyweightKGF,
               preparation.canContinue(isStreaming: service.state == .streaming) {
                Text("Captured baseline: \(forceText(bodyweightKGF))")
                    .font(.system(size: 18, weight: .bold, design: .rounded))
                    .foregroundStyle(Color.hangInk)
                Text("Use this relaxed jug hang as your bodyweight reference for this workout.")
                    .font(.system(size: 15, weight: .medium, design: .rounded))
                    .foregroundStyle(Color.hangMuted)

                Button("Measure again", action: retryBodyweightCapture)
                    .buttonStyle(.bordered)
                    .tint(Color.hangGreenDark)
                    .disabled(service.state != .streaming)

                Button("Continue") {
                    guard service.state == .streaming,
                          preparation.canContinue(isStreaming: true) else { return }
                    onComplete(bodyweightKGF)
                }
                .buttonStyle(.borderedProminent)
                .tint(Color.hangGreenDark)
                .disabled(service.state != .streaming)
            }

            Button("Skip bodyweight", action: skipPreparation)
            .font(.system(size: 15, weight: .bold, design: .rounded))
            .foregroundStyle(Color.hangMuted)
        }
    }

    private func startTare() {
        guard service.state == .streaming else {
            handleStreamingLoss()
            return
        }
        guard preparation.startTare() else { return }
        didRequestTare = true
        #if DEBUG
        service.resetSimulationForPreparation()
        #endif
        service.tare()
    }

    private func startBodyweightCapture() {
        guard service.state == .streaming else {
            handleStreamingLoss()
            return
        }
        guard preparation.startBodyweightCapture() else { return }
        didStartBodyweightCapture = service.beginBodyweightMeasurement(duration: bodyweightCaptureDuration)
        guard !didStartBodyweightCapture else { return }
        preparation.completeBodyweight(with: nil, isStreaming: service.state == .streaming)
    }

    private func handleStreamingLoss() {
        didRequestTare = false
        didStartBodyweightCapture = false
        preparation.invalidateForStreamingLoss()
    }

    private func retryTare() {
        preparation.retryTare()
        didRequestTare = false
        startTare()
    }

    private func retryBodyweightCapture() {
        preparation.retryBodyweight()
        didStartBodyweightCapture = false
        startBodyweightCapture()
    }

    private func skipPreparation() {
        service.cancelPreparationMeasurements()
        didRequestTare = false
        didStartBodyweightCapture = false
        preparation.skip()
        onSkip()
    }

    private func bodyweightFailureText(for failure: MotherboardWorkoutPreparationFailure) -> String {
        switch failure {
        case .bodyweightCaptureInterrupted:
            "The sensor stopped streaming before the capture finished. Reconnect it, then retry or skip bodyweight."
        case .invalidBodyweightCapture:
            "No valid bodyweight baseline was captured. Hang relaxed on the jugs, then retry or skip bodyweight."
        case .tareInterrupted:
            ""
        }
    }

    private func bodyweightProgress(at date: Date) -> Double {
        guard let startedAt = service.bodyweightMeasurementStartedAt, bodyweightCaptureDuration > 0 else { return 0 }
        return min(max(date.timeIntervalSince(startedAt) / bodyweightCaptureDuration, 0), 1)
    }

    private func forceText(_ kilogramsForce: Double) -> String {
        MotherboardUserVisibleFormatting.force(kilogramsForce, unit: unit) ?? "—"
    }

    private func durationText(_ duration: TimeInterval) -> String {
        MotherboardUserVisibleFormatting.duration(duration) ?? "—"
    }
}
