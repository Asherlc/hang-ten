import Foundation
let data=Data(#"{"radius":0.0035,"mass":0.01,"positions":[[0.25,-0.5,1]],"count":3,"active":true,"optional":null}"#.utf8)
let raw=try decodeCheckpointJSON(data)
let radius=raw["radius"] as! Double,mass=raw["mass"] as! Double
// Hand-checked IEEE754 encodings of the immutable authored facts.
guard radius.bitPattern==4570216873058560377,mass.bitPattern==4576918229304087675,
      raw["count"] as! Int==3,raw["active"] as! Bool,
      raw["optional"] is NSNull,
      raw["positions"] as! [[Double]]==[[0.25,-0.5,1]] else {
    print("FAIL checkpoint facts changed during decoding");exit(1)
}
print("PASS exact checkpoint numeric facts and structure")
