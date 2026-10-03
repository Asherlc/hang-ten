do {
    func eligible(_ norm:Double=1e-6,_ trust:Double=1,_ previous:Bool=true,_ limit:Double?=5e-5)->Bool {
        RopeDynamicsSolver.physicalTerminalEligible(limit:limit,norm:norm,trust:trust,previousAcceptedFullStep:previous)
    }
    precondition(eligible() && !eligible(1e-6,1,false) && !eligible(1e-6,0.5))
    precondition(!eligible(5e-5) && eligible(5e-5.nextDown) && !eligible(.nan) && !eligible(.infinity))
    precondition(!eligible(1e-6,1,true,nil) && !eligible(5e-6,1,true,0.001/240))
    func metrics(_ length:Double=0.0005,_ strain:Double=0.005,_ margin:Double = -0.00005,_ topology:Bool=true)->RopeSimulationMetrics {
        RopeSimulationMetrics(totalLengthError:length,maximumLocalStrain:strain,minimumSegmentClearance:0.0035+margin,
            minimumClearanceMargin:margin,topologyValid:topology,topologyFailure:topology ? nil:"fixture",maximumSpeed:0,boardDisplacement:0)
    }
    precondition(metrics().geometryAccepted)
    precondition(!metrics(0.0005.nextUp).geometryAccepted && !metrics(0.0005,0.005.nextUp).geometryAccepted)
    precondition(!metrics(0.0005,0.005,(-0.00005).nextDown).geometryAccepted && !metrics(0.0005,0.005,-0.00005,false).geometryAccepted)
    print("PASS physical terminal epoch/trust/phase/finite and original length/strain/clearance/topology boundaries")
}
