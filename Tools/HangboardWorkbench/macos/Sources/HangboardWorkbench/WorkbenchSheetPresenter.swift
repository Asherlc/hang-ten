import AppKit

@MainActor
final class WorkbenchSheetPresenter {
    typealias Completion = @MainActor (NSApplication.ModalResponse) -> Void

    func present(
        _ alert: NSAlert,
        for window: NSWindow,
        completion: @escaping Completion
    ) {
        alert.beginSheetModal(for: window, completionHandler: completion)
    }

    func present(
        _ panel: NSOpenPanel,
        for window: NSWindow,
        completion: @escaping Completion
    ) {
        panel.beginSheetModal(for: window, completionHandler: completion)
    }
}
