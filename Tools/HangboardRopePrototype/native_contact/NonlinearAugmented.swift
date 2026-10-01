import Foundation
import simd

/// Experimental scalar augmented energy; not linked into the application.
enum NonlinearAugmented {
    static let epsilon = 1e-8
    private static func numerator(_ c:Double,_ dual:Double,_ penalty:Double,_ contact:Bool) throws -> Double {
        guard c.isFinite,dual.isFinite,penalty.isFinite,penalty>0 else {throw RopePhysicsError.invalid("Invalid augmented scalar")}
        let value=dual+penalty*c
        guard value.isFinite else {throw RopePhysicsError.invalid("Augmented scalar overflow")}
        return contact ? min(0,value):value
    }
    static func force(_ c:Double,dual:Double,penalty:Double,contact:Bool) throws -> Double {
        return try numerator(c,dual,penalty,contact)/(1+penalty*epsilon)
    }
    static func energy(_ c:Double,dual:Double,penalty:Double,contact:Bool) throws -> Double {
        let n=try numerator(c,dual,penalty,contact)
        let value=n*n/(2*penalty*(1+penalty*epsilon))
        guard value.isFinite else {throw RopePhysicsError.invalid("Augmented energy overflow")}
        return value
    }
    static func curvature(_ c:Double,dual:Double,penalty:Double,contact:Bool) throws -> Double {
        let n=try numerator(c,dual,penalty,contact)
        return contact && n==0 ? 0:penalty/(1+penalty*epsilon)
    }
    static func direction(masses:[Double],offset:[Double],gradients:[[Double]],
                          residuals:[Double],duals:[Double],penalties:[Double],contacts:[Bool]) throws -> [Double] {
        let n=masses.count,k=residuals.count
        guard (n==1 || n==3),offset.count==n,gradients.count==k,duals.count==k,
              penalties.count==k,contacts.count==k,masses.allSatisfy({$0.isFinite && $0>0}),
              offset.allSatisfy({$0.isFinite}),gradients.allSatisfy({$0.count==n && $0.allSatisfy({$0.isFinite})}) else {
            throw RopePhysicsError.invalid("Invalid augmented block")
        }
        var matrix=Array(repeating:Array(repeating:0.0,count:n),count:n)
        var gradient=zip(masses,offset).map(*)
        for i in 0..<n {matrix[i][i]=masses[i]}
        for row in 0..<k {
            let f=try force(residuals[row],dual:duals[row],penalty:penalties[row],contact:contacts[row])
            let h=try curvature(residuals[row],dual:duals[row],penalty:penalties[row],contact:contacts[row])
            for i in 0..<n {
                gradient[i] += f*gradients[row][i]
                for j in 0..<n {matrix[i][j] += h*gradients[row][i]*gradients[row][j]}
            }
        }
        var lower=Array(repeating:Array(repeating:0.0,count:n),count:n)
        for i in 0..<n {for j in 0...i {
            var value=matrix[i][j]
            if j>0 {for k in 0..<j {value -= lower[i][k]*lower[j][k]}}
            if i==j {
                guard value.isFinite,value>0 else {throw RopePhysicsError.invalid("Nonpositive augmented block pivot")}
                lower[i][j]=sqrt(value)
            } else {lower[i][j]=value/lower[j][j]}
        }}
        var result=Array(repeating:0.0,count:n)
        for i in 0..<n {
            var value = -gradient[i]
            if i>0 {for j in 0..<i {value -= lower[i][j]*result[j]}}
            result[i]=value/lower[i][i]
        }
        for i in (0..<n).reversed() {
            var value=result[i]
            if i+1<n {for j in i+1..<n {value -= lower[j][i]*result[j]}}
            result[i]=value/lower[i][i]
        }
        guard result.allSatisfy({$0.isFinite}) else {throw RopePhysicsError.invalid("Nonfinite augmented direction")}
        return result
    }
}
