import Foundation
import SwiftUI

/// Handles deep link parsing and routing for the Hang Ten app.
@MainActor
final class DeepLinkManager: ObservableObject {
    @Published var pendingBoardID: String?
    @Published var pendingHoldID: String?
    @Published var pendingWorkoutPlanID: String?

    /// Parses a hangten:// URL and sets pending navigation state.
    func handle(url: URL) {
        guard url.scheme == "hangten" else { return }

        // For hangten://board/<id>, url.host is "board" and pathComponents
        // contains ["/", "<id>"]. For hangten:///board/<id>, host is nil and
        // pathComponents contains ["/", "board", "<id>"]. Handle both.
        // Plan workout links use the same host-or-path shapes:
        // hangten://plan/<id>/workout and hangten:///plan/<id>/workout.
        let host = url.host
        let pathComponents = url.pathComponents.filter { $0 != "/" }
        let components = (host.map { [$0] } ?? []) + pathComponents
        guard components.count >= 2 else { return }

        switch components[0] {
        case "board":
            let boardID = components[1]
            guard BoardCatalog.all.contains(where: { $0.id == boardID }) else { return }

            pendingWorkoutPlanID = nil
            if components.count >= 4, components[2] == "hold" {
                let holdID = components[3]
                let board = BoardCatalog.all.first(where: { $0.id == boardID })
                pendingBoardID = boardID
                pendingHoldID = board?.contacts.contains(where: { $0.id == holdID }) == true ? holdID : nil
            } else {
                pendingBoardID = boardID
                pendingHoldID = nil
            }
        case "plan":
            guard components.count >= 3, components[2] == "workout" else { return }
            let planID = components[1]
            guard PlanCatalog.plan(id: planID) != nil else { return }

            pendingBoardID = nil
            pendingHoldID = nil
            pendingWorkoutPlanID = planID
        default:
            return
        }
    }

    /// Clears pending navigation after it's been handled.
    func clearPending() {
        pendingBoardID = nil
        pendingHoldID = nil
        pendingWorkoutPlanID = nil
    }
}
