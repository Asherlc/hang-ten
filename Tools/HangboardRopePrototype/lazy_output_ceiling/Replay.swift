// Native-only prerecorded scalar output oracle. Never used by the app.
private final class RopeLazyOutputReplay: @unchecked Sendable {
    struct Geometry {
        let depths:[[Double]]
        let clearances:[[Double?]]
        var identity:[UInt64] {
            depths.flatMap{$0.map(\.bitPattern)} + clearances.flatMap{$0.flatMap{v in
                v.map{[UInt64(1),$0.bitPattern]} ?? [UInt64(0),UInt64(0)]
            }}
        }
    }
    // Driver-only mutation, outside the joined query workers. Timed runs only
    // read the frozen table; this class is not a general runtime cache.
    var mode=0,fullBuilds=0,scalarLookups=0,rowUpgrades=0,clearanceLookups=0
    private var values:[[UInt64]:Geometry]=[:]
    func resetCounts() {fullBuilds=0;scalarLookups=0;rowUpgrades=0;clearanceLookups=0}
    func record(bits:[UInt64],merits:[[[RopeSegmentContact]]],clearances:[[Double?]]) {
        let key=bits
        let value=Geometry(depths:merits.map{$0.map{$0.map(\.penetrationDepth).max() ?? 0}},clearances:clearances)
        if let old=values[key] {precondition(old.identity==value.identity)} else {
            precondition(values.count<1_000 && value.depths.flatMap{$0}.count<=10_000)
            values[key]=value
        }
    }
    func lookup(bits:[UInt64])->Geometry {
        guard let result=values[bits] else {fatalError("Unrecorded exact scalar input")}
        return result
    }
    var counts:[String:Int] {[
        "fullBuilds":fullBuilds,"scalarLookups":scalarLookups,"rowUpgrades":rowUpgrades,
        "clearanceLookups":clearanceLookups,"recordedConfigurations":values.count
    ]}
}
extension RopeDynamicsSolver {
    private func lazyGeometryKey(_ candidate:RopeSimulationState)->[UInt64] {
        var bits=[candidate.boardHeight.bitPattern,candidate.orientation.vector.x.bitPattern,
            candidate.orientation.vector.y.bitPattern,candidate.orientation.vector.z.bitPattern,
            candidate.orientation.vector.w.bitPattern,UInt64(candidate.ropes.count)]
        for rope in candidate.ropes {
            bits += [rope.radius.bitPattern,UInt64(rope.positions.count)]
            for p in rope.positions {bits += [p.x.bitPattern,p.y.bitPattern,p.z.bitPattern]}
        }
        return bits
    }
    func setLazyOutputMode(_ mode:Int) {precondition((0...2).contains(mode));lazyOutputReplay.mode=mode}
    func resetLazyOutputCounts() {lazyOutputReplay.resetCounts()}
    var lazyOutputCounts:[String:Int] {lazyOutputReplay.counts}
}
