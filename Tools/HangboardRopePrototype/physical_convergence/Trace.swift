import Foundation
enum ConvergenceTrace {
 static var corrections:[[String:Double]]=[]
 static var retries=0,merits=0,trials=0
 static var capped=false,threshold=1e-8
 static func reset(threshold:Double) {corrections=[];retries=0;merits=0;trials=0;capped=false;self.threshold=threshold}
 static func result()->[String:Any] {["corrections":corrections,"retries":retries,"merits":merits,"trials":trials,"capped":capped,"threshold":threshold]}
}
