import XCTest

// Portable pure-geometry checks from the actual application test source.
// UIKit's buffer/entity lifecycle test requires the separate iOS suite.
let suite = LiveRopeMeshTests.defaultTestSuite;suite.run()
guard let result = suite.testRun,result.executionCount == 2,result.totalFailureCount == 0 else {exit(1)}
