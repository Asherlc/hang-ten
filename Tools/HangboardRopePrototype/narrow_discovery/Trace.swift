import Foundation
// Driver flags are fixed until all collider workers join; sums update only on driver.
enum NarrowDiscoveryTrace {
    static var capture=false,verifyMerit=false
    static var faces=0,fallbackQueries=0,ccdQueries=0
    static func reset() {faces=0;fallbackQueries=0;ccdQueries=0}
}
