import Foundation
// Driver switches only outside fully joined batch calls. Workers never write these fields.
enum SolverCollection {
 static var collect=true
 static var profile=false
 static var batchNanos:UInt64=0
 static var narrowNanos:UInt64=0
}
