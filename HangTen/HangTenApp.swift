import SwiftUI

@main
struct HangTenApp: App {
	@StateObject private var motherboardBluetoothService: MotherboardBluetoothService
	@StateObject private var motherboardSettingsStore: MotherboardSettingsStore
    @StateObject private var store: AppStore

	init() {
		let motherboardBluetoothService = MotherboardBluetoothService(
			transport: CoreBluetoothMotherboardTransport()
		)
		let motherboardSettingsStore = MotherboardSettingsStore()
		let workoutSessionStore = WorkoutSessionStore()

		_motherboardBluetoothService = StateObject(wrappedValue: motherboardBluetoothService)
		_motherboardSettingsStore = StateObject(wrappedValue: motherboardSettingsStore)
		_store = StateObject(wrappedValue: AppStore(
			motherboardBluetoothService: motherboardBluetoothService,
			motherboardSettingsStore: motherboardSettingsStore,
			workoutSessionStore: workoutSessionStore
		))
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
