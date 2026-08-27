import Combine
import Foundation
import StoreKit

struct PurchaseProduct: Equatable {
    let id: String
    let displayPrice: String
}

enum StoreKitTransaction: Equatable, Sendable {
    case verified(productID: String)
    case unverified(productID: String)

    var productID: String {
        switch self {
        case .verified(let productID), .unverified(let productID):
            return productID
        }
    }

    var isVerified: Bool {
        if case .verified = self {
            return true
        }
        return false
    }
}

enum StoreKitPurchaseResult {
    case success(StoreKitTransaction)
    case pending
    case userCancelled
    case failed(Error)
}

@MainActor
protocol StoreKitClient: AnyObject {
    func loadProduct(id: String) async throws -> PurchaseProduct?
    func currentEntitlement(for productID: String) async throws -> StoreKitTransaction?
    func purchase(productID: String) async -> StoreKitPurchaseResult
    func restorePurchases() async throws
    func transactionUpdates() -> AsyncStream<StoreKitTransaction>
    func finish(_ transaction: StoreKitTransaction) async
}

@MainActor
final class LiveStoreKitClient: StoreKitClient {
    private enum ClientError: Error {
        case productNotLoaded
        case unknownPurchaseResult
    }

    private var products: [String: Product] = [:]
    private var verifiedTransactions: [String: Transaction] = [:]

    func loadProduct(id: String) async throws -> PurchaseProduct? {
        let loadedProducts = try await Product.products(for: [id])
        guard let product = loadedProducts.first(where: { $0.id == id }) else {
            return nil
        }
        products[id] = product
        return PurchaseProduct(id: product.id, displayPrice: product.displayPrice)
    }

    func currentEntitlement(for productID: String) async throws -> StoreKitTransaction? {
        for await verificationResult in Transaction.currentEntitlements {
            let transaction = transaction(from: verificationResult)
            guard transaction.productID == productID else { continue }
            return transaction
        }
        return nil
    }

    func purchase(productID: String) async -> StoreKitPurchaseResult {
        guard let product = products[productID] else {
            return .failed(ClientError.productNotLoaded)
        }

        do {
            switch try await product.purchase() {
            case .success(let verificationResult):
                return .success(transaction(from: verificationResult))
            case .pending:
                return .pending
            case .userCancelled:
                return .userCancelled
            @unknown default:
                return .failed(ClientError.unknownPurchaseResult)
            }
        } catch {
            return .failed(error)
        }
    }

    func restorePurchases() async throws {
        try await StoreKit.AppStore.sync()
    }

    func transactionUpdates() -> AsyncStream<StoreKitTransaction> {
        AsyncStream { continuation in
            let task = Task { [weak self] in
                for await verificationResult in Transaction.updates {
                    guard let self else { break }
                    continuation.yield(self.transaction(from: verificationResult))
                }
                continuation.finish()
            }
            continuation.onTermination = { _ in task.cancel() }
        }
    }

    func finish(_ transaction: StoreKitTransaction) async {
        guard transaction.isVerified,
              let storeKitTransaction = verifiedTransactions.removeValue(forKey: transaction.productID)
        else {
            return
        }
        await storeKitTransaction.finish()
    }

    private func transaction(from verificationResult: VerificationResult<Transaction>) -> StoreKitTransaction {
        switch verificationResult {
        case .verified(let transaction):
            verifiedTransactions[transaction.productID] = transaction
            return .verified(productID: transaction.productID)
        case .unverified(let transaction, _):
            return .unverified(productID: transaction.productID)
        }
    }
}

@MainActor
final class PurchaseManager: ObservableObject {
    enum State: Equatable {
        case idle
        case loading
        case purchasing
        case pending
        case failed
    }

    static let lifetimeProductID = "com.hangten.training.lifetime"

    @Published private(set) var hasLifetimeEntitlement = false
    @Published private(set) var product: PurchaseProduct?
    @Published private(set) var state: State = .idle

    private let client: any StoreKitClient
    private var transactionUpdatesTask: Task<Void, Never>?

    init(client: any StoreKitClient) {
        self.client = client
    }

    convenience init() {
        self.init(client: LiveStoreKitClient())
    }

    deinit {
        transactionUpdatesTask?.cancel()
    }

    func prepare() async {
        state = .loading
        startTransactionUpdates()

        do {
            product = try await client.loadProduct(id: Self.lifetimeProductID)
            guard product != nil else {
                state = .failed
                return
            }
            await refreshEntitlement()
        } catch {
            state = .failed
        }
    }

    func purchase() async {
        state = .purchasing

        switch await client.purchase(productID: Self.lifetimeProductID) {
        case .success(let transaction):
            await apply(transaction)
        case .pending:
            state = .pending
        case .userCancelled:
            state = .idle
        case .failed:
            state = .failed
        }
    }

    func restore() async {
        state = .loading

        do {
            try await client.restorePurchases()
            await refreshEntitlement()
        } catch {
            state = .failed
        }
    }

    private func refreshEntitlement() async {
        do {
            guard let transaction = try await client.currentEntitlement(for: Self.lifetimeProductID) else {
                state = .idle
                return
            }
            await apply(transaction)
        } catch {
            state = .failed
        }
    }

    private func startTransactionUpdates() {
        guard transactionUpdatesTask == nil else { return }
        transactionUpdatesTask = Task { [weak self] in
            guard let self else { return }
            for await transaction in self.client.transactionUpdates() {
                await self.apply(transaction)
            }
        }
    }

    private func apply(_ transaction: StoreKitTransaction) async {
        guard transaction.productID == Self.lifetimeProductID else {
            if transaction.isVerified {
                await client.finish(transaction)
            }
            return
        }

        guard transaction.isVerified else {
            state = .failed
            return
        }

        hasLifetimeEntitlement = true
        state = .idle
        await client.finish(transaction)
    }
}
