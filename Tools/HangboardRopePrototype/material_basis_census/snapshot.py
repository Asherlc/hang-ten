"""Input-only material displacement basis census; no reduced solver/adoption."""
from pathlib import Path
from armijo.snapshot import once

def solver_source(source):
    source=once(source,'        let solved=try contactCorrection(rows:rows,weights:weights,prediction:prediction)',
        '        let basisQueryCosts=MaterialBasisTrace.lastBatchCosts\n        let solved=try contactCorrection(rows:rows,weights:weights,prediction:prediction)')
    source=once(source,'            clearances.append(batch.clearances)',
        '            if MaterialBasisTrace.enabled {MaterialBasisTrace.lastBatchCosts=batch.costs}\n            clearances.append(batch.clearances)')
    return once(source,'"woodTerms":woodTerms.count,',
        '''"woodTerms":woodTerms.count,
                        "basisData":MaterialBasisTrace.enabled ? [
                            "height":heightCorrection,"boardMass":before.boardMass,
                            "queryCosts":basisQueryCosts,
                            "ropes":before.ropes.enumerated().map{r,rope -> [String:Any] in
                                ["positions":rope.positions.map{[$0.x,$0.y,$0.z]},
                                 "displacements":rope.positions.indices.map{i -> [Double] in
                                    let d=RopeArmijo.displacement(rope,i,corrections[r][i],heightCorrection)
                                    return [d.x,d.y,d.z]},
                                 "weights":weights[r],"restLengths":rope.restLengths,
                                 "supports":rope.supports.keys.sorted(),"attachments":rope.attachments.keys.sorted(),
                                 "portals":rope.portalCrossings.values.map{$0.segment}.sorted()]
                            },
                            "contacts":rows.filter{$0.contact}.map{row in row.particles.indices.map{[row.ropeIndex($0),row.particles[$0]]}},
                            "equalityRows":rows.filter{!$0.contact}.count,
                            "contactRows":rows.filter{$0.contact}.count
                        ]:NSNull(),''')

def driver_source(source):
    return source[:source.index('func fixtures()throws')]+Path(__file__).with_name('Main.swift.txt').read_text()

def collider_source(source):
    source='import Foundation\n'+source
    source=once(source,'    let pointCount:Int,linkCount:Int\n    init(points:Int) {',
        '''    let pointCount:Int,linkCount:Int
    let queryCosts:UnsafeMutablePointer<Double>?
    init(points:Int) {
        queryCosts=MaterialBasisTrace.enabled ? .allocate(capacity:points-1):nil
        queryCosts?.initialize(repeating:0,count:points-1)''')
    source=once(source,'    deinit {inside.deinitialize',
        '    deinit {queryCosts?.deinitialize(count:linkCount);queryCosts?.deallocate();inside.deinitialize')
    source=once(source,'clearances:[Double?]) {','clearances:[Double?],costs:[Double]) {')
    source=once(source,'            for i in ranges(links,job) {\n                storage.results[i]=',
        '            for i in ranges(links,job) {\n                let started=storage.queryCosts==nil ? 0:ProcessInfo.processInfo.systemUptime\n                storage.results[i]=')
    source=once(source,'startInside:storage.inside[i],endInside:storage.inside[i+1])',
        'startInside:storage.inside[i],endInside:storage.inside[i+1])\n                if let costs=storage.queryCosts {costs[i]=ProcessInfo.processInfo.systemUptime-started}')
    source=once(source,'        return (p,r,m,clearances)',
        '        return (p,r,m,clearances,storage.queryCosts.map{p in (0..<links).map{p[$0]}} ?? [])')
    return source
