import Foundation
import Darwin
enum ForegroundQoSTrace {
    // Driver-thread writes only before/after fully joined batches.
    static var observe=false
    static var workers:[[String:Any]]=[]
    static func cpuSeconds()->Double {
        var usage=rusage()
        precondition(getrusage(RUSAGE_SELF,&usage)==0)
        return Double(usage.ru_utime.tv_sec+usage.ru_stime.tv_sec)+Double(usage.ru_utime.tv_usec+usage.ru_stime.tv_usec)/1_000_000
    }
}
