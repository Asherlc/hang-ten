import UIKit

/// Orbit-versus-scroll arbitration for the SwiftUI board preview's drag gesture.
enum OrbitPanArbitration {
    /// Minimum finger travel before SwiftUI begins recognizing an orbit drag.
    static let activationDistance: CGFloat = 10

    /// Claims the drag for orbiting only when motion is horizontal-dominant.
    /// Mostly-vertical motion is rejected so an enclosing scroll view can scroll.
    static func shouldBegin(translation: CGPoint, velocity: CGPoint) -> Bool {
        if abs(velocity.x) > 0 || abs(velocity.y) > 0 {
            return abs(velocity.x) >= abs(velocity.y)
        }
        return abs(translation.x) >= abs(translation.y)
    }
}
