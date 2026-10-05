import SwiftUI
import UIKit

struct MotherboardWorkoutPreparationHandoff {
    private(set) var didAccept = false

    mutating func accept() -> Bool {
        guard !didAccept else { return false }
        didAccept = true
        return true
    }
}

@MainActor
protocol RootViewBackgroundTaskApplication: AnyObject {
	func beginBackgroundTask(withName taskName: String?, expirationHandler handler: (@MainActor @Sendable () -> Void)?) -> UIBackgroundTaskIdentifier
	func endBackgroundTask(_ identifier: UIBackgroundTaskIdentifier)
}

extension UIApplication: RootViewBackgroundTaskApplication {}

@MainActor
final class RootViewSessionPersistenceCoordinator {
	private let application: RootViewBackgroundTaskApplication
	private var backgroundTaskIdentifier = UIBackgroundTaskIdentifier.invalid

	init(application: RootViewBackgroundTaskApplication) {
		self.application = application
	}

	func flush(store: AppStore) {
		backgroundTaskIdentifier = application.beginBackgroundTask(
			withName: "Persist workout sessions",
			expirationHandler: { [weak self] in
				self?.finish()
			}
		)
		store.flushSessionPersistence { [self] in
			finish()
		}
	}

	private func finish() {
		guard backgroundTaskIdentifier != .invalid else { return }
		let identifier = backgroundTaskIdentifier
		backgroundTaskIdentifier = .invalid
		application.endBackgroundTask(identifier)
	}
}

enum RootTab: Hashable, CaseIterable {
    case train
    case plans
    case history

    static func initial(environment: [String: String]) -> RootTab {
        #if DEBUG
        if environment["HANGTEN_REVIEW_HISTORY"] == "1" {
            return .history
        }
        if environment["HANGTEN_REVIEW_PLANS"] == "1"
            || environment["HANGTEN_REVIEW_CHOOSER_RESULTS"] == "1"
            || environment["HANGTEN_REVIEW_CHOOSER_FILTERS"] == "1"
            || environment["HANGTEN_REVIEW_CHOOSER_MY_ROUTINES"] == "1" {
            return .plans
        }
        #endif
        return .train
    }
}

struct RootView: View {
    @EnvironmentObject private var store: AppStore
    @StateObject private var workoutAudioCoach = WorkoutAudioCoach()
    @StateObject private var deepLinkManager = DeepLinkManager()
    @State private var selectedTab = RootTab.initial(
        environment: ProcessInfo.processInfo.environment
    )

    var body: some View {
		TabView(selection: $selectedTab) {
			TrainView { selectedTab = .plans }
				.tabItem { Label("Train", systemImage: "figure.climbing") }
				.tag(RootTab.train)

			PlansView()
				.tabItem {
					Label("Plans", systemImage: "list.bullet.rectangle.portrait.fill")
				}
				.tag(RootTab.plans)

			HistoryView()
				.tabItem { Label("History", systemImage: "clock.arrow.circlepath") }
				.tag(RootTab.history)
		}
		.tint(selectedTab == .plans ? .workoutBrowserAccent : .hangGreenDark)
		.environmentObject(workoutAudioCoach)
		.environmentObject(deepLinkManager)
		.onReceive(NotificationCenter.default.publisher(for: UIApplication.didEnterBackgroundNotification)) { _ in
			RootViewSessionPersistenceCoordinator(application: UIApplication.shared).flush(store: store)
		}
		.onReceive(NotificationCenter.default.publisher(for: UIApplication.willTerminateNotification)) { _ in
			store.flushSessionPersistenceSynchronously()
		}
        .onAppear {
            #if DEBUG
            let environment = ProcessInfo.processInfo.environment
            let orientationMask: UIInterfaceOrientationMask?
            if environment["HANGTEN_REVIEW_LANDSCAPE"] == "1" {
                orientationMask = .landscapeRight
            } else if environment["HANGTEN_REVIEW_PORTRAIT"] == "1" {
                orientationMask = .portrait
            } else {
                orientationMask = nil
            }

            guard let orientationMask,
                  let windowScene = UIApplication.shared.connectedScenes
                    .compactMap({ $0 as? UIWindowScene })
                    .first else { return }

            windowScene.requestGeometryUpdate(
                .iOS(interfaceOrientations: orientationMask)
            )
            #endif
        }
        .onOpenURL { url in
            deepLinkManager.handle(url: url)
            if let boardID = deepLinkManager.pendingBoardID,
               let board = BoardCatalog.all.first(where: { $0.id == boardID }) {
                store.selectBoard(board)
                selectedTab = .train
            } else if deepLinkManager.pendingWorkoutPlanID != nil {
                selectedTab = .train
            }
        }
    }
}
