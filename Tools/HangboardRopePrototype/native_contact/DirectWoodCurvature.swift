import Foundation
import simd

// Only linked into owned native experiment snapshots.
enum DirectWoodCurvature {
    struct PairBranch {let ropeFormula:String;let ropeClamp:String;let triangleFormula:String;var boundaries:[String]=[]}
    struct Candidate {
        let name:String
        let point:SIMD3<Double>
        let surface:SIMD3<Double>
        let fraction:Double
        let region:String
        let pair:PairBranch?
        var boundaries:[String]=[]
    }
    struct Selection {let start:SIMD3<Double>;let end:SIMD3<Double>;let triangle:[SIMD3<Double>];let candidates:[Candidate];let winner:Int;let ties:[Int]}
    struct Result {
        let distance:Double
        let gradient:[Double]
        let hessian:[[Double]]
        let candidate:String
        let decisions:[String]
        let tiedCandidates:[String]
        let tiedGradients:[[Double]]
        let tiedHessians:[[[Double]]]
        let internalBoundaries:[String]
    }
    static func selected(start:SIMD3<Double>,end:SIMD3<Double>,triangle:[SIMD3<Double>],
                         startDerivatives:[SIMD3<Double>],endDerivatives:[SIMD3<Double>]) throws -> Result {
        guard triangle.count==3,startDerivatives.count==endDerivatives.count,(1...7).contains(startDerivatives.count) else {
            throw RopePhysicsError.invalid("Invalid wood derivative coordinates")
        }
        let selection=try RopeTriangleCollider.directWoodSelection(start,end,triangle)
        return try differentiate(selection,startDerivatives:startDerivatives,endDerivatives:endDerivatives)
    }
    static func differentiate(_ selection:Selection,startDerivatives:[SIMD3<Double>],endDerivatives:[SIMD3<Double>]) throws -> Result {
        let count=startDerivatives.count
        guard (1...7).contains(count),endDerivatives.count==count,(startDerivatives+endDerivatives).allSatisfy({[$0.x,$0.y,$0.z].allSatisfy{$0.isFinite}}) else {
            throw RopePhysicsError.invalid("Invalid wood derivative seeds")
        }
        let p=JetVector.affine(selection.start,startDerivatives),q=JetVector.affine(selection.end,endDerivatives)
        let vertices=selection.triangle.map{JetVector.constant($0,count)}
        func derivative(_ index:Int) throws -> Jet {
            let candidate=selection.candidates[index]
            if candidate.name=="ray" {throw RopePhysicsError.invalid("Intersecting direct wood feature")}
            if candidate.name=="start" || candidate.name=="end" {
                let point=candidate.name=="start" ? p:q
                let a=vertices[0],b=vertices[1],c=vertices[2]
                if candidate.region=="face" {
                    let n=simd_normalize(simd_cross(selection.triangle[1]-selection.triangle[0],selection.triangle[2]-selection.triangle[0]))
                    let signed=(point-a).dot(JetVector.constant(n,count))
                    return signed.value>=0 ? signed:-signed
                }
                let ab=b-a,ac=c-a,ap=point-a
                let d1=ab.dot(ap),d2=ac.dot(ap),bp=point-b,d3=ab.dot(bp),d4=ac.dot(bp)
                let cp=point-c,d5=ab.dot(cp),d6=ac.dot(cp)
                let surface:JetVector
                switch candidate.region {
                case "vertexA":surface=a
                case "vertexB":surface=b
                case "vertexC":surface=c
                case "edgeAB":surface=a+ab*(d1/(d1-d3))
                case "edgeAC":surface=a+ac*(d2/(d2-d6))
                case "edgeBC":surface=b+(c-b)*((d4-d3)/((d4-d3)+(d5-d6)))
                default:throw RopePhysicsError.invalid("Unknown direct triangle branch")
                }
                return (point-surface).norm()
            }
            guard let branch=candidate.pair,let edge=Int(candidate.name.dropFirst(4)),(0..<3).contains(edge) else {
                throw RopePhysicsError.invalid("Unknown direct segment branch")
            }
            let a=vertices[edge],b=vertices[(edge+1)%3]
            let d1=q-p,d2=b-a,r=p-a,aa=d1.dot(d1),ee=d2.dot(d2),f=d2.dot(r),c=d1.dot(r),bb=d1.dot(d2)
            var s=Jet.constant(0,count)
            if branch.ropeClamp=="one" {s=Jet.constant(1,count)}
            else if branch.ropeClamp=="free" {
                switch branch.ropeFormula {
                case "interior":s=(bb*f-c*ee)/(aa*ee-bb*bb)
                case "triangleStart":s = -c/aa
                case "triangleEnd":s=(bb-c)/aa
                default:throw RopePhysicsError.invalid("Unknown moving rope fraction")
                }
            }
            let t:Jet
            switch branch.triangleFormula {
            case "zero":t=Jet.constant(0,count)
            case "one":t=Jet.constant(1,count)
            case "projected":t=(bb*s+f)/ee
            case "degenerateRopeProjection":t=f/ee
            default:throw RopePhysicsError.invalid("Unknown moving triangle fraction")
            }
            return (p+d1*s-a-d2*t).norm()
        }
        let jet=try derivative(selection.winner),candidate=selection.candidates[selection.winner]
        guard jet.value>1e-10,jet.value.isFinite,jet.gradient.allSatisfy({$0.isFinite}),jet.hessian.allSatisfy({$0.isFinite}) else {
            throw RopePhysicsError.invalid("Nonfinite or degenerate direct wood derivative")
        }
        var tieGradients:[[Double]]=[],tieHessians:[[[Double]]]=[]
        for index in selection.ties {
            let alternative=try derivative(index)
            guard alternative.value.isFinite,alternative.gradient.allSatisfy({$0.isFinite}),alternative.hessian.allSatisfy({$0.isFinite}) else {
                throw RopePhysicsError.invalid("Nonfinite tied wood derivative")
            }
            tieGradients.append(alternative.gradient);tieHessians.append(alternative.matrix)
        }
        let decisions=candidate.pair.map{[$0.ropeFormula,$0.ropeClamp,$0.triangleFormula]} ?? [candidate.region]
        return Result(distance:jet.value,gradient:jet.gradient,hessian:jet.matrix,candidate:candidate.name,decisions:decisions,
            tiedCandidates:selection.ties.map{selection.candidates[$0].name},tiedGradients:tieGradients,tiedHessians:tieHessians,internalBoundaries:candidate.boundaries)
    }

    private struct Jet {
        let value:Double
        let gradient:[Double]
        let hessian:[Double]
        var count:Int {gradient.count}
        var matrix:[[Double]] {(0..<count).map{Array(hessian[($0*count)..<(($0+1)*count)])}}
        static func constant(_ value:Double,_ count:Int)->Jet {Jet(value:value,gradient:Array(repeating:0,count:count),hessian:Array(repeating:0,count:count*count))}
        static prefix func -(_ a:Jet)->Jet {Jet(value:-a.value,gradient:a.gradient.map(-),hessian:a.hessian.map(-))}
        static func +(_ a:Jet,_ b:Jet)->Jet {Jet(value:a.value+b.value,gradient:zip(a.gradient,b.gradient).map(+),hessian:zip(a.hessian,b.hessian).map(+))}
        static func -(_ a:Jet,_ b:Jet)->Jet {a+(-b)}
        static func *(_ a:Jet,_ b:Jet)->Jet {
            let n=a.count
            var g=Array(repeating:0.0,count:n),h=Array(repeating:0.0,count:n*n)
            for i in 0..<n {
                g[i]=a.gradient[i]*b.value+b.gradient[i]*a.value
                for j in 0..<n {let k=i*n+j;h[k]=a.hessian[k]*b.value+b.hessian[k]*a.value+a.gradient[i]*b.gradient[j]+b.gradient[i]*a.gradient[j]}
            }
            return Jet(value:a.value*b.value,gradient:g,hessian:h)
        }
        func unary(_ value:Double,_ first:Double,_ second:Double)->Jet {
            let n=count
            var h=Array(repeating:0.0,count:n*n)
            for i in 0..<n {for j in 0..<n {let k=i*n+j;h[k]=first*hessian[k]+second*gradient[i]*gradient[j]}}
            return Jet(value:value,gradient:gradient.map{$0*first},hessian:h)
        }
        static func /(_ a:Jet,_ b:Jet)->Jet {a*b.unary(1/b.value,-1/(b.value*b.value),2/(b.value*b.value*b.value))}
        func squareRoot()->Jet {let root=sqrt(value);return unary(root,0.5/root,-0.25/(value*root))}
    }
    private struct JetVector {
        let axes:[Jet]
        static func affine(_ value:SIMD3<Double>,_ derivatives:[SIMD3<Double>])->JetVector {
            let n=derivatives.count
            return JetVector(axes:(0..<3).map{axis in Jet(value:value[axis],gradient:derivatives.map{$0[axis]},hessian:Array(repeating:0,count:n*n))})
        }
        static func constant(_ value:SIMD3<Double>,_ n:Int)->JetVector {JetVector(axes:(0..<3).map{Jet.constant(value[$0],n)})}
        static func +(_ a:JetVector,_ b:JetVector)->JetVector {JetVector(axes:zip(a.axes,b.axes).map(+))}
        static func -(_ a:JetVector,_ b:JetVector)->JetVector {JetVector(axes:zip(a.axes,b.axes).map(-))}
        static func *(_ a:JetVector,_ b:Jet)->JetVector {JetVector(axes:a.axes.map{$0*b})}
        func dot(_ b:JetVector)->Jet {(0..<3).reduce(Jet.constant(0,axes[0].count)){$0+axes[$1]*b.axes[$1]}}
        func norm()->Jet {dot(self).squareRoot()}
    }
}
