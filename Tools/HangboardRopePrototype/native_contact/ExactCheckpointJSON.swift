import Foundation

// JSONSerialization's NSDecimalNumber bridge changes some authored Double
// facts by one ULP. JSONDecoder preserves the same parsing as the descriptor.
private struct ExactCheckpointValue:Decodable {
    let value:Any
    init(from decoder:Decoder) throws {
        let c=try decoder.singleValueContainer()
        if c.decodeNil() {value=NSNull()}
        else if let v=try? c.decode(Bool.self) {value=v}
        else if let v=try? c.decode(Double.self) {value=NSNumber(value:v)}
        else if let v=try? c.decode(String.self) {value=v}
        else if let v=try? c.decode([ExactCheckpointValue].self) {value=v.map(\.value)}
        else {value=try c.decode([String:ExactCheckpointValue].self).mapValues(\.value)}
    }
}
func decodeCheckpointJSON(_ data:Data) throws -> [String:Any] {
    try JSONDecoder().decode([String:ExactCheckpointValue].self,from:data).mapValues(\.value)
}
