import Foundation
import simd
import Darwin
let root=URL(fileURLWithPath:CommandLine.arguments[1])
guard CommandLine.arguments.count==6 || CommandLine.arguments.count==7 else{exit(2)}
if CommandLine.arguments.count==7 {
 let proposal=try decodeCheckpointJSON(Data(contentsOf:URL(fileURLWithPath:CommandLine.arguments[6])))
 DiscoveryCapture.candidates=(proposal["queries"] as! [[String:Any]]).map{($0["triangles"] as! [Double]).map{Int($0)}}
}
let descriptor=try Data(contentsOf:URL(fileURLWithPath:CommandLine.arguments[4]))
let raw=try JSONSerialization.jsonObject(with:descriptor) as! [String:Any]
let input=try RopePhysicsDescriptor.decode(descriptor).validated(modelSHA256:raw["modelSHA256"] as! String)
let collider=try RopeTriangleCollider(input:input)
var solver=try RopeDynamicsSolver.restoreFoundation(input:input,collider:collider,data:Data(contentsOf:URL(fileURLWithPath:CommandLine.arguments[3])))
alarm(10)
let frame=try solver.step(dt:1.0/240,targetOrientation:simd_quatd(angle:Double.pi/2,axis:SIMD3(0,0,1)))
guard frame.metrics.geometryAccepted else{throw RopePhysicsError.invalid("Original step rejected")}
let output=try JSONSerialization.data(withJSONObject:solver.foundationCheckpoint(),options:[.sortedKeys,.prettyPrinted])
let prior=try Data(contentsOf:URL(fileURLWithPath:CommandLine.arguments[5]))
guard output==prior else{throw RopePhysicsError.invalid("Discovery instrumentation/reconstruction changed whole accepted state")}
try output.write(to:root.appendingPathComponent("after.json"));alarm(0)
print("PASS original accepted whole-state byte identity")
