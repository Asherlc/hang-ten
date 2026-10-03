import Foundation
enum RetainedInitializerTrace {
    static var applied=false
    static var seconds=0.0
    static var captures=0
    static func reset(){applied=false;seconds=0;captures=0}
}
