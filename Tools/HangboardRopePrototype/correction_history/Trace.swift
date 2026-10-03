import Foundation
// Experimental single-thread trace; never linked into app.
enum HistoryTrace {
 static var corrections:[[String:Double]]=[]
 static var qps:[[String:Int]]=[]
 static var merits=0,trials=0,retries=0,fallbacks=0,lastRows=0,lastActive=0
 static var guessKind="none",guessTrust=1.0
 static func reset() {corrections=[];qps=[];merits=0;trials=0;retries=0;fallbacks=0;guessKind="none";guessTrust=1}
 static func result()->[String:Any] {["corrections":corrections,"qps":qps,"merits":merits,"trials":trials,"retries":retries,"fallbacks":fallbacks,"guessKind":guessKind,"guessTrust":guessTrust]}
}
