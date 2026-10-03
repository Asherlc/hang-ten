extension RopeDynamicsSolver {
    static func terminalEligible(limit:Double?,norm:Double,strain:Double,trust:Double,
                                 previousAcceptedFullStep:Bool)->Bool {
        guard let limit,limit.isFinite,limit>0,norm.isFinite,norm>=0,
              strain.isFinite,strain>=0,previousAcceptedFullStep,trust==1 else{return false}
        return strain<0.0002 && norm<limit
    }
}
