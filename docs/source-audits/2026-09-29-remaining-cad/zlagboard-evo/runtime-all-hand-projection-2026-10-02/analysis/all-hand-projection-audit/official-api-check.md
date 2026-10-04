Apple API check for the temporary projection diagnostic

Apple documents PerspectiveCameraComponent as an entity component whose transform determines viewpoint and whose forward direction is negative Z. It provides the initializer with near, far, fieldOfViewInDegrees, and fieldOfViewOrientation used by the proposal.

Source: https://developer.apple.com/documentation/realitykit/perspectivecameracomponent

Apple defines fieldOfViewInDegrees as the full angle. With vertical orientation, that angle is vertical and horizontal coverage follows aspect ratio; the documented default is 60 degrees.

Source: https://developer.apple.com/documentation/realitykit/perspectivecameracomponent/fieldofviewindegrees

The proposed vertex-based fit is our mathematical rendering adaptation, not a manufacturer measurement or an Apple diagnosis of the stale-frame issue. Successful compilation and runtime validation remain separate requirements.
