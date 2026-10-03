import Foundation
// Native-only observer, called on the solver's main thread after joined geometry work.
enum ContactCycleTrace {
    static var enabled=false
    static var corrections:[[String:Any]]=[]
}
