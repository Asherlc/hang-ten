import Foundation
import Darwin
do {
    // Independent equations: a=(2x+lambda-2xs,3height-s), C=x*x+height.
    // For p=(.1,.02,-.03), ps=.05,pv=-.04: Ra=(-.01,0), Rh=.01,Rsv=-.002.
    let d=try NonlinearPrimalDual.eliminate(s:0.4,v:0.5,h:0,rc:0)
    let entries:[(Int,Int,Double)]=[(0,0,1.2+4*d.diagonal),(1,1,-1e-8),(1,0,1),
                                 (2,2,3+d.diagonal),(2,0,2*d.diagonal)]
    let factor=try NonlinearPrimalDualFactor(size:3,equalities:[1],entries:entries)
    let rows:[NonlinearKKTDefect.Row]=[
        .init(jacobian:[(0,1)],equalityVariable:1,s:0,v:0,ps:0,pv:0,
              originB:1-1e-8*0.3,trialB:1.1-1e-8*0.32,originH:0,trialH:0),
        .init(jacobian:[(0,2),(2,1)],equalityVariable:nil,s:0.4,v:0.5,ps:0.05,pv:-0.04,
              originB:0,trialB:0,originH:1.2+1e-8*0.4-0.5,trialH:1.38+1e-8*0.45-0.46)]
    let c=try NonlinearKKTDefect.solve(factor:factor,entries:entries,masses:[2,0,3],p:[0.1,0.02,-0.03],
            originA:[1.5,0,0.2],trialA:[1.53,0,0.06],rows:rows)
    guard abs(c.remainderA[0]+0.01)<1e-14,abs(c.remainderA[2])<1e-14,
          abs(c.remainderH[1]-0.01)<1e-14,abs(c.remainderSV[1]+0.002)<1e-14,
          abs(1.2*c.x[0]+c.x[1]-2*c.s[1]-0.01)<1e-12,
          abs(3*c.x[2]-c.s[1])<1e-12,abs(c.x[0]-1e-8*c.x[1])<1e-12,
          abs(2*c.x[0]+c.x[2]+1e-8*c.s[1]-c.v[1]+0.01)<1e-12,
          abs(0.5*c.s[1]+0.4*c.v[1]-0.002)<1e-12,
          factor.solveCalls==1 else {throw RopePhysicsError.invalid("Full force-geometry defect or recovery signs wrong")}
    print("PASS curved constraint fullKKT remainder, mixed forces and one existing-factor RHS")
    let path=CommandLine.arguments[1]
    let input=try decodeCheckpointJSON(Data(contentsOf:URL(fileURLWithPath:path)))
    let es=(input["entries"] as! [[Double]]).map{(Int($0[0]),Int($0[1]),$0[2])}
    let rs=(input["rows"] as! [[String:Any]]).map{r in
        NonlinearKKTDefect.Row(jacobian:(r["jacobian"] as! [[Double]]).map{(Int($0[0]),$0[1])},
            equalityVariable:r["equalityVariable"] as? Int,s:r["s"] as! Double,v:r["v"] as! Double,
            ps:r["ps"] as! Double,pv:r["pv"] as! Double,originB:r["originB"] as! Double,
            trialB:r["trialB"] as! Double,originH:r["originH"] as! Double,trialH:r["trialH"] as! Double)
    }
    let frozen=try NonlinearPrimalDualFactor(size:input["size"] as! Int,equalities:Set(input["equalities"] as! [Int]),entries:es)
    let replay=try NonlinearKKTDefect.solve(factor:frozen,entries:es,masses:input["masses"] as! [Double],
        p:input["p"] as! [Double],originA:input["originA"] as! [Double],trialA:input["trialA"] as! [Double],rows:rs)
    for (actual,name) in [(replay.x,"expectedX"),(replay.s,"expectedS"),(replay.v,"expectedV")] {
        let expected=input[name] as! [Double]
        guard actual.count==expected.count,zip(actual,expected).allSatisfy({abs($0-$1)<=1e-12}) else {
            throw RopePhysicsError.invalid("Native defect differs from retained independent correction: \(name)")
        }
    }
    guard replay.stationarity<=1e-10,replay.equality<=1e-8,replay.contact<=1e-10,replay.complementarity<=1e-14 else {
        throw RopePhysicsError.invalid("Frozen full recovered equations fail")
    }
    print("PASS retained loaded correction matches independent x/s/v arrays and all four linear certificates")
} catch {print("FAIL",error);exit(1)}
