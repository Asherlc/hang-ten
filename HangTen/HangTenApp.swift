import SwiftUI

@main
struct HangTenApp: App {
	@StateObject private var motherboardBluetoothService: MotherboardBluetoothService
	@StateObject private var motherboardSettingsStore: MotherboardSettingsStore
	@StateObject private var store: AppStore

	init() {
		#if DEBUG
		let useMotherboardReviewFixture = ProcessInfo.processInfo.environment["HANGTEN_REVIEW_MOTHERBOARD"] == "1"
		let transport: MotherboardTransport = useMotherboardReviewFixture
			? SimulatedMotherboardTransport()
			: CoreBluetoothMotherboardTransport()
		#else
		let transport: MotherboardTransport = CoreBluetoothMotherboardTransport()
		#endif
		let motherboardBluetoothService = MotherboardBluetoothService(
			transport: transport
		)
		let motherboardSettingsStore = MotherboardSettingsStore()
		let workoutSessionStore = WorkoutSessionStore()
		let telemetry = TelemetryComposition.make(bundle: .main)

		_motherboardBluetoothService = StateObject(wrappedValue: motherboardBluetoothService)
		_motherboardSettingsStore = StateObject(wrappedValue: motherboardSettingsStore)
		_store = StateObject(wrappedValue: AppStore(
			motherboardBluetoothService: motherboardBluetoothService,
			motherboardSettingsStore: motherboardSettingsStore,
			workoutSessionStore: workoutSessionStore,
			telemetry: telemetry
		))

		#if DEBUG
		if useMotherboardReviewFixture {
			motherboardBluetoothService.connect()
		}
		#endif
	}

    var body: some Scene {
        WindowGroup {
            RootView()
                .environmentObject(store)
				.environmentObject(motherboardBluetoothService)
				.environmentObject(motherboardSettingsStore)
        }
    }
}
