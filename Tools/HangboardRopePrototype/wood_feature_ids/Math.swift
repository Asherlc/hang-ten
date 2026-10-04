import simd
// Exact native feature provenance, not a geometric-nearness heuristic.
enum WoodFeatureIdentity {
    static func key(faceID:Int,face:SIMD3<Int>,source:Int,fraction:Double)->String? {
        guard faceID>=0,face.x>=0,face.y>=0,face.z>=0,fraction.isFinite,fraction>=0,fraction<=1 else{return nil}
        let ropeClamp=fraction==0 ? 0:(fraction==1 ? 1:2)
        func vertex(_ i:Int)->String {"v/\(face[i])/rope/\(ropeClamp)"}
        func edge(_ i:Int,_ j:Int)->String {"e/\(min(face[i],face[j]))/\(max(face[i],face[j]))/rope/\(ropeClamp)"}
        if (100...106).contains(source) || (200...206).contains(source) {
            guard ropeClamp==(source<200 ? 0:1) else{return nil}
            switch source%100 {
            case 0:return vertex(0)
            case 1:return vertex(1)
            case 2:return edge(0,1)
            case 3:return vertex(2)
            case 4:return edge(0,2)
            case 5:return edge(1,2)
            case 6:return "f/\(faceID)/rope/\(ropeClamp)"
            default:return nil
            }
        }
        guard source>=400 else{return nil}
        let e=(source-400)/100,branch=(source-400)%100
        // Only ordinary valid native segment-pair branches. Degenerate/parallel retain no alias.
        guard e>=0,e<3,branch>=0,branch<9,branch%3==ropeClamp else{return nil}
        switch branch/3 {
        case 0:return vertex(e)
        case 1:return vertex((e+1)%3)
        case 2:return edge(e,(e+1)%3)
        default:return nil
        }
    }
}
