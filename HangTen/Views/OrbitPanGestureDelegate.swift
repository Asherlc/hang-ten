import UIKit

/// Lets a 3D model's orbit drag live inside an ancestor vertical ScrollView.
/// The drag is claimed for orbiting only once it has moved more horizontally
/// than vertically; a mostly-vertical drag is left alone so the enclosing
/// scroll view still scrolls — the same arbitration a horizontal carousel
/// needs when it sits inside a vertical feed.
final class OrbitPanGestureDelegate: NSObject, UIGestureRecognizerDelegate {
    func gestureRecognizerShouldBegin(_ gestureRecognizer: UIGestureRecognizer) -> Bool {
        guard let pan = gestureRecognizer as? UIPanGestureRecognizer, let view = pan.view else { return true }
        let velocity = pan.velocity(in: view)
        guard abs(velocity.x) > 0 || abs(velocity.y) > 0 else {
            let translation = pan.translation(in: view)
            return abs(translation.x) >= abs(translation.y)
        }
        return abs(velocity.x) >= abs(velocity.y)
    }
}
