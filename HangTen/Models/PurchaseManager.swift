import Combine
import Foundation
import StoreKit

struct PurchaseProduct: Equatable {
    let id: String
    let displayPrice: String
}

enum StoreKitTransaction: Equatable, Sendable {
    case verified(productID: String, transactionID: UInt64 = 0)
    case revoked(productID: String, transactionID: UInt64 = 0)
    case unverified(productID: String, transactionID: UInt64 = 0)

    var productID: String {
        switch self {
        case .verified(let productID, _), .revoked(let productID, _), .unverified(let productID, _):
            return productID
        }
    }

    var transactionID: UInt64 {
        switch self {
        case .verified(_, let transactionID), .revoked(_, let transactionID), .unverified(_, let transactionID):
            return transactionID
        }
    }

    var isVerified: Bool {
        switch self {
        case .verified, .revoked:
            return true
        case .unverified:
            return false
        }
    }

    var isRevoked: Bool {
        if case .revoked = self {
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
    private var verifiedTransactions: [UInt64: Transaction] = [:]

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
              let storeKitTransaction = verifiedTransactions.removeValue(forKey: transaction.transactionID)
        else {
            return
        }
        await storeKitTransaction.finish()
    }

    private func transaction(from verificationResult: VerificationResult<Transaction>) -> StoreKitTransaction {
        switch verificationResult {
        case .verified(let transaction):
            verifiedTransactions[transaction.id] = transaction
            if transaction.revocationDate != nil {
                return .revoked(productID: transaction.productID, transactionID: transaction.id)
            }
            return .verified(productID: transaction.productID, transactionID: transaction.id)
        case .unverified(let transaction, _):
            return .unverified(productID: transaction.productID, transactionID: transaction.id)
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
        case productLoadFailed
        case nothingToRestore
        case restoreFailed
    }

    private enum EntitlementRefreshResult {
        case entitled
        case notEntitled
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
        product = nil
        startTransactionUpdates()

        await refreshEntitlement()

        do {
            product = try await client.loadProduct(id: Self.lifetimeProductID)
            guard product != nil else {
                state = .productLoadFailed
                return
            }
        } catch {
            state = .productLoadFailed
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
            switch await refreshEntitlement() {
            case .entitled:
                break
            case .notEntitled:
                state = .nothingToRestore
            case .failed:
                state = .restoreFailed
            }
        } catch {
            state = .restoreFailed
        }
    }

    @discardableResult
    private func refreshEntitlement() async -> EntitlementRefreshResult {
        do {
            guard let transaction = try await client.currentEntitlement(for: Self.lifetimeProductID) else {
                hasLifetimeEntitlement = false
                state = .idle
                return .notEntitled
            }
            hasLifetimeEntitlement = false
            await apply(transaction)
            if hasLifetimeEntitlement {
                return .entitled
            }
            return state == .failed ? .failed : .notEntitled
        } catch {
            state = .failed
            return .failed
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
            return
        }

        guard transaction.isVerified else {
            state = .failed
            return
        }

        guard !transaction.isRevoked else {
            hasLifetimeEntitlement = false
            state = .idle
            await client.finish(transaction)
            return
        }

        hasLifetimeEntitlement = true
        state = .idle
        await client.finish(transaction)
    }
}
