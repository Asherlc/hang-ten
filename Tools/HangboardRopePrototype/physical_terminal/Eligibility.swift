extension RopeDynamicsSolver {
    static func physicalTerminalEligible(limit:Double?,norm:Double,trust:Double,
                                         previousAcceptedFullStep:Bool)->Bool {
        guard let limit,limit.isFinite,limit>0,norm.isFinite,norm>=0,
              previousAcceptedFullStep,trust==1 else{return false}
        return norm<limit
    }
}
