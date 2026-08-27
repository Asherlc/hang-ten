import SwiftUI
import Sentry

@main
struct HangTenApp: App {
	@StateObject private var motherboardBluetoothService: MotherboardBluetoothService
	@StateObject private var motherboardSettingsStore: MotherboardSettingsStore
	@StateObject private var purchaseManager: PurchaseManager
	@StateObject private var store: AppStore

	init() {
		SentrySDK.start { options in
			options.dsn = Bundle.main.object(forInfoDictionaryKey: "SENTRY_DSN") as? String
		}

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
		#if DEBUG
		let environment = ProcessInfo.processInfo.environment
		if let reviewedFreeWorkouts = environment["HANGTEN_REVIEW_FREE_WORKOUTS_USED"].flatMap(Int.init) {
			UserDefaults.standard.set(
				min(max(reviewedFreeWorkouts, 0), 2),
				forKey: "HangTen.freeWorkoutsUsed.v1"
			)
		}
		#endif
		let workoutAccessStore = WorkoutAccessStore()
		#if DEBUG
		let purchaseManager: PurchaseManager
		if environment["HANGTEN_REVIEW_STOREKIT"] == "1" {
			purchaseManager = PurchaseManager(client: ReviewStoreKitClient(
				verifiedPurchase: environment["HANGTEN_REVIEW_VERIFIED_PURCHASE"] == "1",
				verifiedRestore: environment["HANGTEN_REVIEW_VERIFIED_RESTORE"] == "1"
			))
		} else {
			purchaseManager = PurchaseManager()
		}
		#else
		let purchaseManager = PurchaseManager()
		#endif
		let telemetry = TelemetryComposition.make(bundle: .main)

		_motherboardBluetoothService = StateObject(wrappedValue: motherboardBluetoothService)
		_motherboardSettingsStore = StateObject(wrappedValue: motherboardSettingsStore)
		_purchaseManager = StateObject(wrappedValue: purchaseManager)
		_store = StateObject(wrappedValue: AppStore(
			motherboardBluetoothService: motherboardBluetoothService,
			motherboardSettingsStore: motherboardSettingsStore,
			workoutSessionStore: workoutSessionStore,
			workoutAccessStore: workoutAccessStore,
			purchaseManager: purchaseManager,
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
				.task {
					await purchaseManager.prepare()
				}
        }
    }
}

#if DEBUG
@MainActor
private final class ReviewStoreKitClient: StoreKitClient {
	private let verifiedPurchase: Bool
	private let verifiedRestore: Bool
	private var hasEntitlement = false

	init(verifiedPurchase: Bool, verifiedRestore: Bool) {
		self.verifiedPurchase = verifiedPurchase
		self.verifiedRestore = verifiedRestore
	}

	func loadProduct(id: String) async throws -> PurchaseProduct? {
		PurchaseProduct(id: id, displayPrice: "$2.99")
	}

	func currentEntitlement(for productID: String) async throws -> StoreKitTransaction? {
		guard hasEntitlement else { return nil }
		return .verified(productID: productID)
	}

	func purchase(productID: String) async -> StoreKitPurchaseResult {
		guard verifiedPurchase else { return .userCancelled }
		hasEntitlement = true
		return .success(.verified(productID: productID))
	}

	func restorePurchases() async throws {
		hasEntitlement = verifiedRestore
	}

	func transactionUpdates() -> AsyncStream<StoreKitTransaction> {
		AsyncStream { continuation in
			continuation.finish()
		}
	}

	func finish(_ transaction: StoreKitTransaction) async {}
}
#endif
