import UIKit

/// Pure orbit-vs-scroll arbitration used by `OrbitPanGestureDelegate` and unit tests.
/// Activation distance is enforced by `OrbitPanGestureRecognizer` so this never
/// returns `false` merely to "wait for more movement" — that would permanently
/// fail the recognizer for the rest of the touch sequence.
enum OrbitPanArbitration {
    /// Finger travel required before an orbit pan may leave `.possible`.
    static let activationDistance: CGFloat = 10

    static func hasClearedActivationDistance(
        from origin: CGPoint,
        to location: CGPoint,
        threshold: CGFloat = activationDistance
    ) -> Bool {
        hypot(location.x - origin.x, location.y - origin.y) >= threshold
    }

    /// Claims the drag for orbiting only when motion is horizontal-dominant.
    /// Mostly-vertical motion is rejected so an enclosing scroll view can scroll.
    static func shouldBegin(translation: CGPoint, velocity: CGPoint) -> Bool {
        if abs(velocity.x) > 0 || abs(velocity.y) > 0 {
            return abs(velocity.x) >= abs(velocity.y)
        }
        return abs(translation.x) >= abs(translation.y)
    }
}

/// Pan that stays `.possible` until the finger clears `activationDistance`.
/// Unlike returning `false` from `gestureRecognizerShouldBegin`, swallowing
/// early `touchesMoved` does not permanently fail the recognizer — later
/// movement can still begin a horizontal orbit, while short taps never start
/// the pan and can be claimed by a tap recognizer that requires this to fail.
final class OrbitPanGestureRecognizer: UIPanGestureRecognizer {
    var activationDistance: CGFloat = OrbitPanArbitration.activationDistance
    private var originInView: CGPoint?

    override func reset() {
        originInView = nil
        super.reset()
    }

    override func touchesBegan(_ touches: Set<UITouch>, with event: UIEvent) {
        originInView = touches.first?.location(in: view)
        super.touchesBegan(touches, with: event)
    }

    override func touchesMoved(_ touches: Set<UITouch>, with event: UIEvent) {
        if state == .possible {
            guard let origin = originInView,
                  let location = touches.first?.location(in: view),
                  OrbitPanArbitration.hasClearedActivationDistance(
                    from: origin,
                    to: location,
                    threshold: activationDistance
                  ) else {
                return
            }
        }
        super.touchesMoved(touches, with: event)
    }
}

/// Lets a 3D model's orbit drag live inside an ancestor vertical ScrollView.
/// The drag is claimed for orbiting only once it has moved more horizontally
/// than vertically; a mostly-vertical drag is left alone so the enclosing
/// scroll view still scrolls — the same arbitration a horizontal carousel
/// needs when it sits inside a vertical feed.
final class OrbitPanGestureDelegate: NSObject, UIGestureRecognizerDelegate {
    func gestureRecognizerShouldBegin(_ gestureRecognizer: UIGestureRecognizer) -> Bool {
        guard let pan = gestureRecognizer as? UIPanGestureRecognizer, let view = pan.view else { return true }
        return OrbitPanArbitration.shouldBegin(
            translation: pan.translation(in: view),
            velocity: pan.velocity(in: view)
        )
    }
}
