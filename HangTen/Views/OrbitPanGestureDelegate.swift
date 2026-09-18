import UIKit

/// Lets a 3D model's orbit drag live inside an ancestor vertical ScrollView.
/// The drag is claimed for orbiting only once it has moved more horizontally
/// than vertically; a mostly-vertical drag is left alone so the enclosing
/// scroll view still scrolls — the same arbitration a horizontal carousel
/// needs when it sits inside a vertical feed.
final class OrbitPanGestureDelegate: NSObject, UIGestureRecognizerDelegate {
    private static let minimumTranslation: CGFloat = 5

    func gestureRecognizerShouldBegin(_ gestureRecognizer: UIGestureRecognizer) -> Bool {
        guard let pan = gestureRecognizer as? UIPanGestureRecognizer, let view = pan.view else { return true }
        let translation = pan.translation(in: view)
        guard abs(translation.x) >= Self.minimumTranslation || abs(translation.y) >= Self.minimumTranslation else { return false }
        return abs(translation.x) >= abs(translation.y)
    }
}
