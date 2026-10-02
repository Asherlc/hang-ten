import Foundation
import simd

// Exact selected-branch envelope derivatives; linked only into owned native screens.
enum ExplicitWoodCurvature {
    struct Result {
        let distance:Double,gradient:[Double],hessian:[[Double]]
        let candidate:String,decisions:[String],tiedCandidates:[String]
        let tiedGradients:[[Double]],tiedHessians:[[[Double]]],internalBoundaries:[String]
        let maximumParameterStationarity:Double
        let eliminatedParameters:Int
    }
    private struct Branch {
        let distance:Double,gradient:[Double],hessian:[[Double]]
        let stationarity:Double,parameters:Int
    }
    private struct Parameter {let direction:SIMD3<Double>;let movingRope:Bool}
    static func selected(start:SIMD3<Double>,end:SIMD3<Double>,triangle:[SIMD3<Double>],startDerivatives:[SIMD3<Double>],endDerivatives:[SIMD3<Double>]) throws -> Result {
        try differentiate(RopeTriangleCollider.directWoodSelection(start,end,triangle),startDerivatives:startDerivatives,endDerivatives:endDerivatives)
    }
    static func differentiate(_ selection:DirectWoodCurvature.Selection,startDerivatives:[SIMD3<Double>],endDerivatives:[SIMD3<Double>]) throws -> Result {
        let count=startDerivatives.count
        guard (1...7).contains(count),endDerivatives.count==count,
              (startDerivatives+endDerivatives).allSatisfy({[$0.x,$0.y,$0.z].allSatisfy{$0.isFinite}}) else {
            throw RopePhysicsError.invalid("Invalid explicit wood seeds")
        }
        func branch(_ index:Int) throws -> Branch {
            let candidate=selection.candidates[index]
            guard candidate.name != "ray" else {throw RopePhysicsError.invalid("Intersecting explicit wood feature")}
            var parameters:[Parameter]=[]
            let s=candidate.fraction
            let derivatives=zip(startDerivatives,endDerivatives).map{$0*(1-s)+$1*s}
            if candidate.name=="start" || candidate.name=="end" {
                if candidate.region=="face" {
                    let normal=simd_normalize(simd_cross(selection.triangle[1]-selection.triangle[0],selection.triangle[2]-selection.triangle[0]))
                    let point=candidate.name=="start" ? selection.start:selection.end
                    let signed=simd_dot(point-selection.triangle[0],normal),n=signed>=0 ? normal:-normal
                    return Branch(distance:abs(signed),gradient:derivatives.map{simd_dot(n,$0)},hessian:Array(repeating:Array(repeating:0,count:count),count:count),stationarity:0,parameters:0)
                }
                let edge:(Int,Int)?
                switch candidate.region {
                case "vertexA","vertexB","vertexC":edge=nil
                case "edgeAB":edge=(0,1)
                case "edgeAC":edge=(0,2)
                case "edgeBC":edge=(1,2)
                default:throw RopePhysicsError.invalid("Unknown explicit triangle branch")
                }
                if let edge {parameters.append(Parameter(direction:selection.triangle[edge.0]-selection.triangle[edge.1],movingRope:false))}
            }else {
                guard let pair=candidate.pair,let edge=Int(candidate.name.dropFirst(4)),(0..<3).contains(edge) else {
                    throw RopePhysicsError.invalid("Unknown explicit segment branch")
                }
                if pair.ropeClamp=="free" {
                    guard ["interior","triangleStart","triangleEnd"].contains(pair.ropeFormula),s>0,s<1 else {
                        throw RopePhysicsError.invalid("Invalid free rope parameter")
                    }
                    parameters.append(Parameter(direction:selection.end-selection.start,movingRope:true))
                }else if pair.ropeClamp != "zero" && pair.ropeClamp != "one" {
                    throw RopePhysicsError.invalid("Unknown fixed rope parameter")
                }
                if pair.triangleFormula=="projected" || pair.triangleFormula=="degenerateRopeProjection" {
                    let axis=selection.triangle[(edge+1)%3]-selection.triangle[edge]
                    let ee=simd_length_squared(axis),r=selection.start-selection.triangle[edge]
                    guard ee>0,ee.isFinite else {throw RopePhysicsError.invalid("Degenerate projected triangle parameter")}
                    let f=simd_dot(axis,r),bb=simd_dot(selection.end-selection.start,axis)
                    let t=pair.triangleFormula=="degenerateRopeProjection" ? f/ee:(bb*s+f)/ee
                    guard t>0,t<1,t.isFinite else {throw RopePhysicsError.invalid("Noninterior projected triangle parameter")}
                    parameters.append(Parameter(direction:-axis,movingRope:false))
                }else if pair.triangleFormula != "zero" && pair.triangleFormula != "one" {
                    throw RopePhysicsError.invalid("Unknown fixed triangle parameter")
                }
            }
            let delta=candidate.point-candidate.surface,d=simd_length(delta)
            guard d>1e-10,d.isFinite else {throw RopePhysicsError.invalid("Degenerate explicit wood distance")}
            let normal=delta/d
            func projected(_ value:SIMD3<Double>)->SIMD3<Double> {value-normal*simd_dot(normal,value)}
            var stationarity=0.0
            for parameter in parameters {
                let length=simd_length(parameter.direction)
                guard length>0,length.isFinite else {throw RopePhysicsError.invalid("Degenerate free parameter")}
                stationarity=max(stationarity,abs(simd_dot(normal,parameter.direction))/length)
            }
            guard stationarity<=1e-10 else {throw RopePhysicsError.invalid("Nonstationary free closest parameter")}
            let projectedSeeds=derivatives.map(projected)
            let mixed=parameters.map {parameter in derivatives.indices.map {i in
                simd_dot(derivatives[i],projected(parameter.direction))/d +
                    (parameter.movingRope ? simd_dot(normal,endDerivatives[i]-startDerivatives[i]):0)
            }}
            var b00=0.0,b01=0.0,b11=0.0,determinant=0.0
            if !parameters.isEmpty {
                b00=simd_dot(parameters[0].direction,projected(parameters[0].direction))/d
                guard b00>0,b00.isFinite else {throw RopePhysicsError.invalid("Singular closest parameter Hessian")}
                if parameters.count==2 {
                    b01=simd_dot(parameters[0].direction,projected(parameters[1].direction))/d
                    b11=simd_dot(parameters[1].direction,projected(parameters[1].direction))/d
                    determinant=b00*b11-b01*b01
                    guard b11>0,determinant>0,determinant.isFinite else {throw RopePhysicsError.invalid("Singular two-parameter Hessian")}
                }
            }
            var h=Array(repeating:Array(repeating:0.0,count:count),count:count)
            for i in 0..<count {for j in 0..<count {
                var value=simd_dot(derivatives[i],projectedSeeds[j])/d
                if parameters.count==1 {value -= mixed[0][i]*mixed[0][j]/b00}
                else if parameters.count==2 {
                    let first=b11*mixed[0][j]-b01*mixed[1][j]
                    let second=b00*mixed[1][j]-b01*mixed[0][j]
                    value -= (mixed[0][i]*first+mixed[1][i]*second)/determinant
                }
                h[i][j]=value
            }}
            return Branch(distance:d,gradient:derivatives.map{simd_dot(normal,$0)},hessian:h,stationarity:stationarity,parameters:parameters.count)
        }
        func checked(_ index:Int) throws -> Branch {
            let result=try branch(index)
            guard result.distance>1e-10,result.distance.isFinite,result.gradient.allSatisfy({$0.isFinite}),result.hessian.flatMap({$0}).allSatisfy({$0.isFinite}) else {
                throw RopePhysicsError.invalid("Nonfinite explicit wood derivative")
            }
            return result
        }
        let winning=try checked(selection.winner),candidate=selection.candidates[selection.winner]
        var alternatives:[Branch]=[]
        for index in selection.ties {alternatives.append(try checked(index))}
        return Result(distance:winning.distance,gradient:winning.gradient,hessian:winning.hessian,candidate:candidate.name,
            decisions:candidate.pair.map{[$0.ropeFormula,$0.ropeClamp,$0.triangleFormula]} ?? [candidate.region],
            tiedCandidates:selection.ties.map{selection.candidates[$0].name},tiedGradients:alternatives.map{$0.gradient},tiedHessians:alternatives.map{$0.hessian},internalBoundaries:candidate.boundaries,
            maximumParameterStationarity:alternatives.reduce(winning.stationarity){max($0,$1.stationarity)},eliminatedParameters:winning.parameters)
    }
}
