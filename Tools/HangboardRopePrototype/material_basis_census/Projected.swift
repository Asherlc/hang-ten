import Foundation
import simd
import Accelerate

enum ProjectedCapture:Error {case done}
struct ProjectedRow {let terms:[(Int,Double)],residual:Double,contact:Bool,active:Bool}
struct ProjectedInput {
    let size:Int,bandwidth:Int,entries:[(Int,Int,Double)],columns:[[Double]],border:[[Double]],rhs:[Double],borderRHS:[Double]
    let variables:[[SIMD3<Int>]],ropes:[RopeChainState],protected:[Set<Int>]
    let selectedRows:[(Bool,Double)],rowVariables:[Int:Int],borderRows:[Int]
    var allRows:[ProjectedRow]=[],reference:[Double]=[]
}
enum ProjectedKKT {
    static var enabled=false,capture=false,red=false
    static var protected:[Set<Int>]=[]
    static var pending:ProjectedInput?
    static var inputs:[ProjectedInput]=[]
    static func knots(_ rope:RopeChainState,_ protected:Set<Int>)->([Int],[Double]) {
        var arc=[0.0]
        for l in rope.restLengths {arc.append(arc.last!+l)}
        var selected=protected.union([0,rope.positions.count-1])
        func refine(_ a:Int,_ b:Int) {
            guard b>a+1 else {return}
            var worst=0.0,index=a
            for i in (a+1)..<b {
                let t=(arc[i]-arc[a])/(arc[b]-arc[a])
                let error=simd_distance(rope.positions[i],(1-t)*rope.positions[a]+t*rope.positions[b])
                if error>worst {worst=error;index=i}
            }
            if worst>5e-6 {selected.insert(index);refine(a,index);refine(index,b)}
        }
        let required=selected.sorted()
        for (a,b) in zip(required,required.dropFirst()) {refine(a,b)}
        return (selected.sorted(),arc)
    }
    // Every fine multiplier is an identity column. Particle hats may also
    // contribute to the UNKNOWN shared height when a span ends at an attachment.
    static func maps(_ input:ProjectedInput)->([[(Int,Double)]],Int) {
        var maps=Array(repeating:[(Int,Double)](),count:input.size+input.columns.count)
        var retained=Set(0..<input.size)
        var knotLists:[[Int]]=[],arcs:[[Double]]=[]
        for r in input.ropes.indices {
            let (ks,arc)=knots(input.ropes[r],input.protected[r]);knotLists.append(ks);arcs.append(arc)
            for i in input.ropes[r].positions.indices where !ks.contains(i) {
                for axis in 0..<3 {retained.remove(input.variables[r][i][axis])}
            }
        }
        let sorted=retained.sorted(),slots=Dictionary(uniqueKeysWithValues:sorted.enumerated().map{($0.element,$0.offset)})
        let n=sorted.count
        for old in sorted {maps[old]=[(slots[old]!,1)]}
        for j in input.columns.indices {maps[input.size+j]=[(n+j,1)]}
        for r in input.ropes.indices {
            let rope=input.ropes[r],ks=knotLists[r],arc=arcs[r]
            for (a,b) in zip(ks,ks.dropFirst()) {for i in a...b {
                let t=(arc[i]-arc[a])/(arc[b]-arc[a])
                for axis in 0..<3 {
                    let old=input.variables[r][i][axis]
                    guard old>=0 else {continue}
                    var terms:[(Int,Double)]=[]
                    for (k,w) in [(a,1-t),(b,t)] where w != 0 {
                        let v=input.variables[r][k][axis]
                        if v>=0 {terms.append((slots[v]!,w))}
                        else if rope.attachments[k] != nil && axis==1 && !red {terms.append((n,w))}
                    }
                    maps[old]=terms
                }
            }}
        }
        return (maps,n)
    }
    struct Matrix {
        var system:RopeBandedSystem,columns:[[Double]],border:[[Double]],rhs:[Double],borderRHS:[Double]
        let maps:[[(Int,Double)]],size:Int,bandwidth:Int,entries:[(Int,Int,Double)]
    }
    static func assemble(_ input:ProjectedInput)throws->Matrix {
        let (maps,n)=maps(input),count=input.columns.count
        var entries=input.entries
        for j in 0..<count {
            for i in 0..<input.size where input.columns[j][i] != 0 {entries.append((input.size+j,i,input.columns[j][i]))}
            for k in 0...j where input.border[j][k] != 0 {entries.append((input.size+j,input.size+k,input.border[j][k]))}
        }
        var bw=0
        for (i,j,_) in entries {for (a,_) in maps[i] where a<n {for (b,_) in maps[j] where b<n {bw=max(bw,abs(a-b))}}}
        var system=try RopeBandedSystem(size:n,bandwidth:bw)
        var columns=Array(repeating:Array(repeating:0.0,count:n),count:count)
        var border=Array(repeating:Array(repeating:0.0,count:count),count:count)
        func add(_ a:Int,_ b:Int,_ v:Double)throws {
            if a<n && b<n {try system.addSymmetric(row:a,column:b,value:v)}
            else if a>=n && b>=n {border[a-n][b-n]+=v;if a != b {border[b-n][a-n]+=v}}
            else {columns[max(a,b)-n][min(a,b)]+=v}
        }
        for (i,j,v) in entries {
            if i==j {for (a,x) in maps[i] {for (b,y) in maps[j] where a>=b {try add(a,b,v*x*y)}}}
            else {for (a,x) in maps[i] {for (b,y) in maps[j] {try add(a,b,(a==b ? 2:1)*v*x*y)}}}
        }
        let originalRHS=input.rhs+input.borderRHS
        var rhs=Array(repeating:0.0,count:n+count)
        for i in maps.indices {for (j,w) in maps[i] {rhs[j]+=w*originalRHS[i]}}
        return Matrix(system:system,columns:columns,border:border,rhs:Array(rhs.prefix(n)),borderRHS:Array(rhs.suffix(count)),
                      maps:maps,size:n,bandwidth:bw,entries:entries)
    }
    static func reconstruct(_ z:[Double],_ maps:[[(Int,Double)]])->[Double] {
        maps.map{row in row.reduce(0){$0+$1.1*z[$1.0]}}
    }
    // Independent full dense P^T K P, not the sparse assembly algorithm.
    static func denseOracle(_ input:ProjectedInput,_ reduced:Matrix)throws->(Double,[Double]) {
        let n=reduced.size+input.columns.count,m=input.size+input.columns.count
        var K=Array(repeating:0.0,count:m*m),P=Array(repeating:0.0,count:m*n)
        for (i,j,v) in reduced.entries {K[i+j*m]=v;K[j+i*m]=v}
        for i in 0..<m {for (j,w) in reduced.maps[i] {P[i+j*m]+=w}}
        var KP=Array(repeating:0.0,count:m*n),A=Array(repeating:0.0,count:n*n),b=Array(repeating:0.0,count:n)
        cblas_dgemm(CblasColMajor,CblasNoTrans,CblasNoTrans,Int32(m),Int32(n),Int32(m),1,K,Int32(m),P,Int32(m),0,&KP,Int32(m))
        cblas_dgemm(CblasColMajor,CblasTrans,CblasNoTrans,Int32(n),Int32(n),Int32(m),1,P,Int32(m),KP,Int32(m),0,&A,Int32(n))
        let f=input.rhs+input.borderRHS
        cblas_dgemv(CblasColMajor,CblasTrans,Int32(m),Int32(n),1,P,Int32(m),f,1,0,&b,1)
        var reconstructed=Array(repeating:0.0,count:n*n)
        for (i,j,v) in reduced.system.projectedEntries() {reconstructed[i+j*n]=v;reconstructed[j+i*n]=v}
        for j in input.columns.indices {
            for i in 0..<reduced.size {reconstructed[i+(reduced.size+j)*n]=reduced.columns[j][i];reconstructed[reduced.size+j+i*n]=reduced.columns[j][i]}
            for k in input.columns.indices {reconstructed[reduced.size+k+(reduced.size+j)*n]=reduced.border[k][j]}
        }
        let matrixError=zip(A,reconstructed).map{abs($0-$1)}.max()!
        var dim=__LAPACK_int(n),one:__LAPACK_int=1,info:__LAPACK_int=0,pivots=Array(repeating:__LAPACK_int(0),count:n)
        dgesv_(&dim,&one,&A,&dim,&pivots,&b,&dim,&info)
        guard info==0 else {throw RopePhysicsError.invalid("projected dense oracle singular")}
        return (matrixError,b)
    }
    static func solve(_ input:ProjectedInput)throws->(Matrix,[Double],[Double]) {
        let matrix=try assemble(input)
        let factor=try matrix.system.factorized(borderColumns:matrix.columns,borderMatrix:matrix.border)
        let solved=try factor.solve(rhs:matrix.rhs,borderRHS:matrix.borderRHS)
        let z=solved.base+solved.border
        return (matrix,z,reconstruct(z,matrix.maps))
    }
    static func snapshot(_ input:ProjectedInput)->[String:Any] {
        func bits(_ v:Double)->String {String(v.bitPattern,radix:16)}
        return ["size":input.size,"bandwidth":input.bandwidth,
            "entries":input.entries.map{[$0.0,$0.1,bits($0.2)] as [Any]},
            "columns":input.columns.map{$0.map{bits($0)}},"border":input.border.map{$0.map{bits($0)}},
            "rhs":input.rhs.map{bits($0)},"borderRHS":input.borderRHS.map{bits($0)},
            "variables":input.variables.map{$0.map{[$0.x,$0.y,$0.z]}},"protected":input.protected.map{$0.sorted()},
            "allRows":input.allRows.map{["terms":$0.terms.map{[$0.0,bits($0.1)] as [Any]},"residual":bits($0.residual),"contact":$0.contact,"active":$0.active] as [String:Any]},
            "selectedRows":input.selectedRows.map{[$0.0,bits($0.1)] as [Any]},"rowVariables":input.rowVariables.map{[$0.key,$0.value]},
            "borderRows":input.borderRows,"reference":input.reference.map{bits($0)}]
    }
    static func report(_ input:ProjectedInput)throws->[String:Any] {
        let (matrix,z,d)=try solve(input),oracle=try denseOracle(input,matrix)
        var originalResidual=(input.rhs+input.borderRHS).map{-$0}
        for (i,j,v) in matrix.entries {originalResidual[i]+=v*input.reference[j];if i != j {originalResidual[j]+=v*input.reference[i]}}
        let originalFactor=try { () throws -> RopeBandedFactorization in
            var system=try RopeBandedSystem(size:input.size,bandwidth:input.bandwidth)
            for (i,j,v) in input.entries {try system.addSymmetric(row:i,column:j,value:v)}
            return try system.factorized(borderColumns:input.columns,borderMatrix:input.border)
        }()
        let recovered=try originalFactor.solve(rhs:input.rhs,borderRHS:input.borderRHS)
        let full=recovered.base+recovered.border
        var originalPoseError=abs(full[input.size]-input.reference[input.size])
        for rope in input.variables {for v in rope where v.x>=0 {
            originalPoseError=max(originalPoseError,simd_length(SIMD3(full[v.x]-input.reference[v.x],full[v.y]-input.reference[v.y],full[v.z]-input.reference[v.z])))
        }}
        var residual=input.rhs+input.borderRHS;residual=residual.map{-$0}
        for (i,j,v) in matrix.entries {residual[i]+=v*d[j];if i != j {residual[j]+=v*d[i]}}
        var projected=Array(repeating:0.0,count:z.count)
        for i in residual.indices {for (j,w) in matrix.maps[i] {projected[j]+=w*residual[i]}}
        let norm=projected.map{abs($0)}.max()!,oracleError=zip(z,oracle.1).map{abs($0-$1)}.max()!
        var worstInactive=0.0,worstEquality=0.0,positiveForce=0.0
        for row in input.allRows {
            let q=row.residual+row.terms.reduce(0){$0+$1.1*d[$1.0]}
            if row.contact && !row.active {worstInactive=min(worstInactive,q)}
        }
        for i in input.selectedRows.indices {
            let variable=input.rowVariables[i] ?? (input.size+1+input.borderRows.firstIndex(of:i)!)
            let multiplier=d[variable]
            if input.selectedRows[i].0 {positiveForce=max(positiveForce,multiplier)}
        }
        for row in input.allRows where !row.contact {
            let q=row.residual+row.terms.reduce(0){$0+$1.1*d[$1.0]};worstEquality=max(worstEquality,abs(q))
        }
        var poseError=abs(d[input.size]-input.reference[input.size])
        for rope in input.variables {for v in rope where v.x>=0 {
            poseError=max(poseError,simd_length(SIMD3(d[v.x]-input.reference[v.x],d[v.y]-input.reference[v.y],d[v.z]-input.reference[v.z])))
        }}
        return ["baseSize":matrix.size,"baseBandwidth":matrix.bandwidth,"bandStorageDoubles":matrix.size*(3*matrix.bandwidth+1),
                "originalBaseSize":input.size,"originalBandwidth":input.bandwidth,"selectedRowsRetained":input.selectedRows.count,
                "unprojectedReferenceResidual":originalResidual.map{abs($0)}.max()!,"unprojectedRecoveryPoseError":originalPoseError,
                "unprojectedCapturePass":originalResidual.map{abs($0)}.max()!<=1e-10 && originalPoseError<=1e-6,
                "projectedResidual":norm,"denseMatrixError":oracle.0,"denseSolutionError":oracleError,"maxPoseDifference":poseError,
                "worstInactiveGap":worstInactive,"positiveContactMultiplier":positiveForce,"rawEqualityResidual":worstEquality,
                "projectedCertificatePass":norm<=1e-10 && oracle.0<=1e-12 && oracleError<=1e-6,
                "oracleActiveSetSufficient":worstInactive>=(-1e-8) && positiveForce<=1e-10,
                "referencePosePass":poseError<=50e-6]
    }
    static func fixtures()throws {
        let points=[SIMD3<Double>(0,0,0),SIMD3(1,0,0),SIMD3(3,0,0),SIMD3(4,0,0)]
        let rope=RopeChainState(id:"projection",radius:0.0035,linearMass:0.01,restLengths:[1,2,1],positions:points,
            previousPositions:points,velocities:Array(repeating:.zero,count:4),supports:[0:.zero],attachments:[3:.zero],portals:[:],channelSegments:[:])
        let variables=[[SIMD3<Int>(repeating:-1),SIMD3(0,1,2),SIMD3(3,4,5),SIMD3<Int>(repeating:-1)]]
        var entries=(0..<8).map{($0,$0,$0<6 ? 2.0:-1e-8)}
        entries += [(6,1,1),(7,4,1)]
        let input=ProjectedInput(size:8,bandwidth:5,entries:entries,columns:[[0,0.3,0,0,0.4,0,0.2,0.1]],border:[[3]],
            rhs:[0,2,0,0,4,0,0.01,0.02],borderRHS:[1],variables:variables,ropes:[rope],protected:[[0,3]],
            selectedRows:[(false,0.01),(false,0.02)],rowVariables:[0:6,1:7],borderRows:[])
        let (maps,n)=maps(input)
        guard n==2,maps[1].count==1,maps[1][0].0==2,maps[1][0].1==0.25,
              maps[4].count==1,maps[4][0].1==0.75 else {throw RopePhysicsError.invalid("unknown height/material basis fixture")}
        let matrix=try assemble(input),oracle=try denseOracle(input,matrix),solved=try solve(input)
        guard abs(matrix.borderRHS[0]-4.5)<1e-15,abs(matrix.border[0][0]-4.25-0.15-0.6)<1e-15,
              oracle.0<1e-14,zip(solved.1,oracle.1).allSatisfy({abs($0-$1)<1e-8}) else {
            throw RopePhysicsError.invalid("coupled projected KKT/gradient fixture")
        }
    }
}
