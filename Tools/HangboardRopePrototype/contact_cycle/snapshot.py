"""Native-only metadata and observer; original contact/solver arithmetic is intact."""
def once(source, old, new):
    assert source.count(old) == 1, old
    return source.replace(old, new)


from pathlib import Path

def collider_source(source):
    source = once(source, '    var timeOfImpact: Double? = nil',
                  '    var timeOfImpact: Double? = nil\n    var censusFace: Int = -1')
    source = source.replace('FusedWitness(best:rowSquare,radius:rowRadius,faceNormal:normal)',
                            'FusedWitness(best:rowSquare,radius:rowRadius,faceNormal:normal,censusFace:index)')
    source = source.replace('FusedWitness(best:meritSquare,radius:meritRadius,faceNormal:normal)',
                            'FusedWitness(best:meritSquare,radius:meritRadius,faceNormal:normal,censusFace:index)')
    source = once(source, '        let faceNormal:SIMD3<Double>\n        var hit:',
                  '        let faceNormal:SIMD3<Double>\n        let censusFace:Int\n        var hit:')
    source = once(source, 'fraction:fraction,penetrationDepth:radius-distance)\n        }\n    }\n    private static func mergeFused',
                  'fraction:fraction,penetrationDepth:radius-distance,censusFace:censusFace)\n        }\n    }\n    private static func mergeFused')
    # Reuse only the original six-candidate per-face query for observer diagnosis.
    # It is called after acceptance and never feeds rows, merit or the cache.
    bundle=(Path(__file__).resolve().parents[1]/'contact_bundle/Bundle.swift').read_text()
    query=bundle[bundle.index('    func contactForFeature('):bundle.index('    func nearestFeature(')]
    return source+'\nstruct RopeMeshFeatureContact {let face:Int;let squaredDistance:Double;let contact:RopeSegmentContact}\nextension RopeTriangleCollider {\n'+query+'\n}\n'


def solver_source(source):
    source = once(source, '        var secondRope:Int?=nil',
                  '        var secondRope:Int?=nil\n        var censusFeature:String=""\n        var censusFraction:Double?=nil')
    # Feature keys identify mesh/portal/material features, independent of row order.
    source = once(source, 'boardGradient:-normal.y+simd_dot(normal,attached),residual:0.00005-hit.penetrationDepth,contact:true,lengthSegment:nil))',
                  'boardGradient:-normal.y+simd_dot(normal,attached),residual:0.00005-hit.penetrationDepth,contact:true,lengthSegment:nil,censusFeature:"wood:p:\\(r):\\(i):\\(hit.censusFace)",censusFraction:hit.fraction))')
    source = once(source, 'residual:0.00005-hit.penetrationDepth,contact:true,lengthSegment:nil))',
                  'residual:0.00005-hit.penetrationDepth,contact:true,lengthSegment:nil,censusFeature:"wood:l:\\(r):\\(i):\\(hit.censusFace)",censusFraction:hit.fraction))')
    source = once(source, 'for boundary in boundaries where boundary.residual<0.00005 {',
                  'for (censusBoundary,boundary) in boundaries.enumerated() where boundary.residual<0.00005 {')
    source = once(source, 'residual:boundary.residual,contact:true,lengthSegment:nil))',
                  'residual:boundary.residual,contact:true,lengthSegment:nil,censusFeature:"portal:\\(r):\\(id):\\(censusBoundary)"))')
    source = once(source, 'residual:distance-2*rope.radius-0.00005,contact:true,lengthSegment:nil))',
                  'residual:distance-2*rope.radius-0.00005,contact:true,lengthSegment:nil,censusFeature:"self:\\(r):\\(i):\\(j)"))')
    source = once(source, 'contact:true,lengthSegment:nil,secondRope:second))',
                  'contact:true,lengthSegment:nil,secondRope:second,censusFeature:"cord:\\(first):\\(second):\\(i):\\(j)"))')
    source = once(source, 'if try merit(state,prediction:prediction,weights:weights,penalty:penalty)<=score+1e-18 {',
                  'let censusTrialScore=try merit(state,prediction:prediction,weights:weights,penalty:penalty)\n                if censusTrialScore<=score+1e-18 {')
    needle='                    lastCorrectionFullStep=alpha==1'
    source = once(source, needle, '''                    if ContactCycleTrace.enabled {
                        func record(_ row:ConstraintRow)->[String:Any] {
                            ["id":row.censusFeature,"particles":row.particles,
                             "gradients":row.gradients.map{[$0.x,$0.y,$0.z]},
                             "heightGradient":row.boardGradient,"residual":row.residual,
                             "fraction":row.censusFraction as Any? ?? NSNull()]
                        }
                        let active=solved.ids.filter{rows[$0].contact}
                        let represented=Set(rows.filter{$0.contact}.map{$0.censusFeature})
                        var missing:[[String:Any]]=[]
                        if let previous=ContactCycleTrace.corrections.last {
                            for id in previous["activeIDs"] as! [String] where !represented.contains(id) && id.hasPrefix("wood:") {
                                let parts=id.split(separator:":"),r=Int(parts[2])!,i=Int(parts[3])!,face=Int(parts[4])!
                                guard face>=0 else {continue}
                                let point=parts[1]=="p",rope=before.ropes[r]
                                let a=before.boardPoint(rope.positions[i]),b=before.boardPoint(rope.positions[point ? i:i+1])
                                let radius=rope.radius+RopeRegionGeometry.clearance+0.00005
                                let witness=collider.contactForFeature(face,from:a,to:b,radius:radius)
                                let prefix=parts.dropLast().joined(separator:":")+":"
                                let normal=before.orientation.act(witness.contact.normal)
                                let substitutes=rows.filter {row in
                                    guard row.censusFeature.hasPrefix(prefix),let fraction=row.censusFraction else {return false}
                                    let rowNormal=row.gradients.reduce(SIMD3<Double>.zero,+)
                                    return abs(fraction-witness.contact.fraction)<1e-6 && simd_dot(rowNormal,normal)>1-1e-8
                                }.map{$0.censusFeature}
                                let cutoff=witness.squaredDistance>=radius*radius
                                let endpoint = !point && (witness.contact.fraction<=1e-6 || witness.contact.fraction>=1-1e-6)
                                missing.append(["id":id,"cutoff":cutoff,"endpointFiltered":endpoint,
                                    "mergedSubstitutes":substitutes,"distance":sqrt(witness.squaredDistance),
                                    "fraction":witness.contact.fraction,"radius":radius])
                            }
                        }
                        ContactCycleTrace.corrections.append([
                            "rows":rows.count,"contacts":rows.filter{$0.contact}.map(record),
                            "activeIDs":active.map{rows[$0].censusFeature},
                            "activeMultipliers":solved.ids.enumerated().filter{rows[$0.element].contact}.map{lambda[$0.offset]},
                            "penalty":penalty,"maxMultiplier":lambda.map{abs($0)}.max() ?? 0,
                            "beforeScore":score,"afterScore":censusTrialScore,
                            "alpha":alpha,"movement":max(maximum,abs(heightCorrection)),"strain":maximumStrain(),
                            "previousActiveMissing":missing,
                            "portalsBefore":before.ropes.map{$0.portalCrossings.mapValues{["segment":Double($0.segment),"fraction":$0.fraction]}},
                            "portalsAfter":state.ropes.map{$0.portalCrossings.mapValues{["segment":Double($0.segment),"fraction":$0.fraction]}}
                        ])
                    }
'''+needle)
    return source
