"""Only patch QP rows change; original triangle merit and receipts remain."""
from pathlib import Path
from armijo.snapshot import once


def collider_source(source):
    source=once(source,'func fusedChainContacts(points:[SIMD3<Double>],rowRadius:Double,meritRadius:Double)->',
        'func fusedChainContacts(points:[SIMD3<Double>],rowRadius:Double,meritRadius:Double,planarPatchRows:Bool=false)->')
    source=once(source,'startInside:storage.inside[i],endInside:storage.inside[i+1])\n            }',
        '''startInside:storage.inside[i],endInside:storage.inside[i+1])
                if planarPatchRows {
                    let patch=fusedContactEvaluation(from:points[i],to:points[i+1],rowRadius:rowRadius,meritRadius:meritRadius,
                        startInside:storage.inside[i],endInside:storage.inside[i+1],planarRegionExperiment:true,clippedPlanarExperiment:true)
                    // Only QP point/link witnesses change. Preserve original literal
                    // triangle merit and its actual-mesh clearance receipt verbatim.
                    let merit=storage.results[i].hits[2]
                    storage.results[i].hits=[patch.hits[0],patch.hits[1],merit,patch.hits[3]]
                }
            }''')
    return source


def solver_source(source):
    source=once(source,'    var armijoExperiment=false','    var armijoExperiment=false\n    var planarPatchRowsExperiment=false')
    source=once(source,'        var portalOrder:[String]=[]','        bits.append(planarPatchRowsExperiment ? 1:0)\n        var portalOrder:[String]=[]')
    source=once(source,'meritRadius:rope.radius+RopeRegionGeometry.clearance)',
        'meritRadius:rope.radius+RopeRegionGeometry.clearance,planarPatchRows:planarPatchRowsExperiment)')
    source=once(source,'        var rows:[ConstraintRow]=[]','        var rows:[ConstraintRow]=[]\n        var woodRowIDs=Set<Int>()')
    source=once(source,'            for i in rope.positions.indices {\n                for hit in evaluation.points[r][i] {',
        '            let woodStart=rows.count\n            for i in rope.positions.indices {\n                for hit in evaluation.points[r][i] {')
    source=once(source,'            // Conservative planar sections can lie inside a curved CAD rim.',
        '            woodRowIDs.formUnion((woodStart..<rows.count).filter{rows[$0].contact})\n            // Conservative planar sections can lie inside a curved CAD rim.')
    source=once(source,'        let solved=try contactCorrection(rows:rows,weights:weights,prediction:prediction)',
        '''        func woodRow(_ id:Int)->[String:Any] {
            let row=rows[id]
            return ["row":id,"rope":row.rope,"particles":row.particles,
                "gradients":row.gradients.map{[$0.x,$0.y,$0.z]},"boardGradient":row.boardGradient,"residual":row.residual]
        }
        let solved=try contactCorrection(rows:rows,weights:weights,prediction:prediction)''')
    source=once(source,'"strain":maximumStrain(),"rows":rows.count,"slope":armijoSlope as Any? ?? NSNull(),',
        '''"strain":maximumStrain(),"rows":rows.count,
                        "initialWoodRows":ArmijoTrace.collectPlanarBindings && ArmijoTrace.corrections.isEmpty ? woodRowIDs.sorted().map(woodRow):[],
                        "activeWoodRows":ArmijoTrace.collectPlanarBindings ? solved.ids.enumerated().filter{woodRowIDs.contains($0.element)}.map {k,id -> [String:Any] in
                            var row=woodRow(id);row["multiplier"]=solved.multipliers[k];return row
                        }:[],"slope":armijoSlope as Any? ?? NSNull(),''')
    return source


def driver_source(source):
    source=source[:source.index('func fixtures()throws {')]
    return source+Path(__file__).with_name('RowsMain.swift').read_text()
