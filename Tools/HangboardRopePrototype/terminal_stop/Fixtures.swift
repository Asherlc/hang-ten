do {
    func allows(_ norm:Double=1e-6,_ strain:Double=1e-5,_ trust:Double=1,_ previous:Bool=true,_ limit:Double?=5e-5)->Bool {
        RopeDynamicsSolver.terminalEligible(limit:limit,norm:norm,strain:strain,trust:trust,previousAcceptedFullStep:previous)
    }
    guard allows(),!allows(1e-6,1e-5,1,false),!allows(1e-6,1e-5,0.5),
          !allows(5e-5),allows(5e-5.nextDown),!allows(1e-6,0.0002),
          !allows(1e-6,1e-5,1,true,nil),!allows(.nan),!allows(.infinity),
          !allows(1e-6,.nan),!allows(1e-6,1e-5,.nan),
          !allows(1e-6,1e-5,1,true,.infinity),!allows(-1e-6),
          !allows(0.001/240,1e-5,1,true,0.001/240),
          allows((0.001/240).nextDown,1e-5,1,true,0.001/240) else {
        fatalError("Terminal convergence eligibility RED/GREEN failed")
    }
    print("PASS terminal eligibility epoch/damping/strain/finite/strict boundary fixtures")
}
