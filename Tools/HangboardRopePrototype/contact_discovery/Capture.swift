import Foundation
import simd

enum DiscoveryCapture {
 static var started=false,enabled=false
 static var queries:[[String:Any]]=[]
 static var candidateQueriesConsumed=0
 static var candidates:[[Int]]?=nil
 static var assemblyStart=0.0,solveStart=0.0,solveEnd=0.0
 static func v(_ p:SIMD3<Double>)->[Double]{[p.x,p.y,p.z]}
 static func begin(){if !started{started=true;enabled=true;assemblyStart=ProcessInfo.processInfo.systemUptime}}
 static func query(_ a:SIMD3<Double>,_ b:SIMD3<Double>,_ radius:Double)->Int {
  guard enabled else{return -1}
  let id=queries.count;queries.append(["a":v(a),"b":v(b),"radius":radius]);return id
 }
 static func faces(_ id:Int)->[Int]? {guard id>=0,let candidates else{return nil};candidateQueriesConsumed += 1;return candidates[id]}
 static func finish(_ id:Int,_ hits:[RopeSegmentContact]) {
  guard id>=0 else{return}
  queries[id]["hits"]=hits.map{h in ["triangle":h.triangleID,"centerlinePoint":v(h.centerlinePoint),"surfacePoint":v(h.surfacePoint),"normal":v(h.normal),"fraction":h.fraction,"depth":h.penetrationDepth] as [String:Any]}
 }
 static func write(_ doc:[String:Any]) throws {
  guard enabled else{return};enabled=false
  var data=doc;data["queries"]=queries;data["candidateQueriesConsumed"]=candidateQueriesConsumed
  data["assemblySeconds"]=solveStart-assemblyStart
  data["solveSeconds"]=solveEnd-solveStart
  try JSONSerialization.data(withJSONObject:data,options:[.sortedKeys,.prettyPrinted]).write(to:URL(fileURLWithPath:CommandLine.arguments[2]))
 }
}
