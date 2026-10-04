"""Oracle-only empty-face cost ceiling, never a runtime geometry algorithm."""
from pathlib import Path
from armijo.snapshot import once

def collider_source(source):
    source=once(source,'startInside:Bool,endInside:Bool)->(hits:',
        'startInside:Bool,endInside:Bool,oracleDrops:[Bool]?=nil,captureDrop:((Int,Bool)->Void)?=nil)->(hits:')
    source=once(source,'        for (index,mask) in faces.sorted(by:{$0.0<$1.0}) {',
        '        for (index,mask) in faces.sorted(by:{$0.0<$1.0}) {\n            if oracleDrops?[index]==true {continue}')
    source=once(source,'            if row.best<rowSquare {minimum=',
        '            captureDrop?(index,first.hit==nil && row.hit==nil && merit.hit==nil && last.hit==nil && !(row.best<rowSquare))\n            if row.best<rowSquare {minimum=')
    source=once(source,'    let pointCount:Int,linkCount:Int\n    init(points:Int) {',
        '    let pointCount:Int,linkCount:Int\n    let capturedDrops:UnsafeMutablePointer<[Bool]>?\n    init(points:Int,captureDrops:Bool=false) {\n        capturedDrops=captureDrops ? .allocate(capacity:points-1):nil\n        capturedDrops?.initialize(repeating:[],count:points-1)')
    source=once(source,'    deinit {inside.deinitialize',
        '    deinit {capturedDrops?.deinitialize(count:linkCount);capturedDrops?.deallocate();inside.deinitialize')
    source=once(source,'func fusedChainContacts(points:[SIMD3<Double>],rowRadius:Double,meritRadius:Double)->',
        'func fusedChainContacts(points:[SIMD3<Double>],rowRadius:Double,meritRadius:Double,oracleDrops:[[Bool]]?=nil,captureDrops:Bool=false)->')
    source=once(source,'clearances:[Double?]) {','clearances:[Double?],drops:[[Bool]]) {')
    source=once(source,'RopeContactBatchStorage(points:points.count),links=',
        'RopeContactBatchStorage(points:points.count,captureDrops:captureDrops),links=')
    source=once(source,'            for i in ranges(links,job) {\n                storage.results[i]=',
        '''            for i in ranges(links,job) {
                var captured=captureDrops ? Array(repeating:false,count:mesh.triangles.count):[]
                let observer:((Int,Bool)->Void)?=captureDrops ? {face,drop in captured[face]=drop}:nil
                storage.results[i]=''')
    source=once(source,'startInside:storage.inside[i],endInside:storage.inside[i+1])',
        '''startInside:storage.inside[i],endInside:storage.inside[i+1],oracleDrops:oracleDrops?[i],captureDrop:observer)
                if captureDrops {storage.capturedDrops![i]=captured}''')
    source=once(source,'        return (p,r,m,clearances)',
        '        return (p,r,m,clearances,captureDrops ? (0..<links).map{storage.capturedDrops![$0]}:[])')
    return source

def solver_source(source):
    source=once(source,'let batch=collider.fusedChainContacts(points:board,rowRadius:rope.radius+RopeRegionGeometry.clearance+0.00005,meritRadius:rope.radius+RopeRegionGeometry.clearance)',
        '''let rr=rope.radius+RopeRegionGeometry.clearance+0.00005,rm=rope.radius+RopeRegionGeometry.clearance
            let floorRequest=EmptyFaceFloor.begin(board,rr,rm)
            let floorStart=ProcessInfo.processInfo.systemUptime
            let batch=collider.fusedChainContacts(points:board,rowRadius:rr,meritRadius:rm,oracleDrops:floorRequest.0,captureDrops:floorRequest.1)
            EmptyFaceFloor.end(board,rr,rm,drops:batch.drops,seconds:ProcessInfo.processInfo.systemUptime-floorStart)''')
    return source

def driver_source(source):
    return source[:source.index('func fixtures()throws')]+Path(__file__).with_name('Main.swift.txt').read_text()
