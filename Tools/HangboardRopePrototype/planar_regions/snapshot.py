"""Exact axis-plane polygonal unions, preserving holes; isolated native source."""
from armijo.snapshot import once


def collider_source(source):
    source=once(source,'    private let tree: [Node]', '''    private let tree: [Node]
    private let planarRegions:[RopePlanarRegion]''')
    source=once(source,'        self.mesh=mesh; self.tree=nodes', '''        self.mesh=mesh; self.tree=nodes
        let bound=mesh.triangles.count==RopePlanarRegionAtlas.faceIDs.count &&
            zip(RopePlanarRegionAtlas.vertexIDs,RopePlanarRegionAtlas.vertices).allSatisfy {i,v in
                mesh.vertices.indices.contains(i) && mesh.vertices[i]==SIMD3(v[0],v[1],v[2])
            } && zip(RopePlanarRegionAtlas.selectedFaces,RopePlanarRegionAtlas.triangles).allSatisfy {i,t in
                mesh.triangles[i]==SIMD3(t[0],t[1],t[2])
            }
        planarRegions=bound ? RopePlanarRegionAtlas.axes.indices.map {id in
            let faces=RopePlanarRegionAtlas.faceLists[id],axis=RopePlanarRegionAtlas.axes[id]
            let first=mesh.triangles[faces[0]],a=mesh.vertices[first.x],b=mesh.vertices[first.y],c=mesh.vertices[first.z]
            return RopePlanarRegion(axis:axis,coordinate:a[axis],
                edges:RopePlanarRegionAtlas.boundaryEdges[id].map{(mesh.vertices[$0[0]],mesh.vertices[$0[1]])},
                normal:simd_normalize(simd_cross(b-a,c-a)),faces:faces)
        }:[]''')
    source=once(source,'endInside:Bool)->(hits:[[RopeSegmentContact]],clearance:Double?)',
        'endInside:Bool,planarRegionExperiment:Bool=false,onlyRegion:Int?=nil,clippedPlanarExperiment:Bool=false)->(hits:[[RopeSegmentContact]],clearance:Double?,regionWork:RopePlanarWork)')
    source=once(source,'radius:rowRadius)],nil)', 'radius:rowRadius)],nil,RopePlanarWork())')
    source=once(source,'        var minimum=Double.infinity',
        '        var minimum=Double.infinity,regionWork=RopePlanarWork()\n        var done=Array(repeating:false,count:planarRegionExperiment ? planarRegions.count:0)')
    source=once(source,'        for (index,mask) in faces.sorted(by:{$0.0<$1.0}) {', '''        for (index,mask) in faces.sorted(by:{$0.0<$1.0}) {
            if let onlyRegion,RopePlanarRegionAtlas.faceIDs[index] != onlyRegion {continue}
            if planarRegionExperiment,!planarRegions.isEmpty {
                let id=RopePlanarRegionAtlas.faceIDs[index]
                if id>=0 {
                    if done[id] {continue};done[id]=true;regionWork.calls += 1
                    let region=planarRegions[id]
                    let gap=max(0,max(min(start[region.axis],end[region.axis])-region.coordinate,
                        region.coordinate-max(start[region.axis],end[region.axis]))).nextDown
                    if gap>rowRadius+1e-9 {continue}
                    if let candidates=region.candidates(start,end,radius:clippedPlanarExperiment ? rowRadius:nil) {
                        regionWork.boundaryPairs += candidates.boundaryPairs
                        let first=Self.planarHits(candidates.first,radius:rowRadius,normal:region.normal,point:true)
                        let last=Self.planarHits(candidates.last,radius:rowRadius,normal:region.normal,point:true)
                        let row=Self.planarHits(candidates.link,radius:rowRadius,normal:region.normal,point:false)
                        let merit=Self.planarHits(candidates.link,radius:meritRadius,normal:region.normal,point:false)
                        for hit in first {Self.mergeFused(hit,into:&firstHits)}
                        for hit in last {Self.mergeFused(hit,into:&lastHits)}
                        for hit in row {Self.mergeFused(hit,into:&rowHits)}
                        for hit in merit {Self.mergeFused(hit,into:&meritHits)}
                    } else {
                        regionWork.fallbacks += 1
                        let original=fusedContactEvaluation(from:start,to:end,rowRadius:rowRadius,meritRadius:meritRadius,
                            startInside:false,endInside:false,onlyRegion:id)
                        for hit in original.hits[0] {Self.mergeFused(hit,into:&firstHits)}
                        for hit in original.hits[1] {Self.mergeFused(hit,into:&rowHits)}
                        for hit in original.hits[2] {Self.mergeFused(hit,into:&meritHits)}
                        for hit in original.hits[3] {Self.mergeFused(hit,into:&lastHits)}
                    }
                    continue
                }
            }''')
    source=once(source,'return ([firstHits,rowHits,meritHits,lastHits],minimum<1e-10 ? 0:minimum)',
        'return ([firstHits,rowHits,meritHits,lastHits],planarRegionExperiment ? nil:(minimum<1e-10 ? 0:minimum),regionWork)')
    source=once(source,'UnsafeMutablePointer<(hits:[[RopeSegmentContact]],clearance:Double?)>',
        'UnsafeMutablePointer<(hits:[[RopeSegmentContact]],clearance:Double?,regionWork:RopePlanarWork)>')
    source=once(source,'results.initialize(repeating:([],nil),count:linkCount)',
        'results.initialize(repeating:([],nil,RopePlanarWork()),count:linkCount)')
    source+='\n'+Path(__file__).with_name('Hits.swift').read_text()
    return source


from pathlib import Path

def driver_source(source,clipped=False):
    source=once(source,'    try fixtures();result["fixturesPass"]=true', '    try planarRegionFixtures();try fixtures();result["fixturesPass"]=true')
    if clipped:source=once(source,'try planarRegionFixtures();try fixtures();','try clippedPlanarFixtures();try planarRegionFixtures();try fixtures();')
    return source


def query_driver(source,clipped=False):
    queries=Path(__file__).with_name('Queries.swift').read_text()
    if clipped:
        queries=once(queries,'func evaluateRegions(_ enabled:Bool)', 'func evaluateRegions(_ enabled:Bool,_ clipped:Bool=false)')
        queries=once(queries,'planarRegionExperiment:enabled)', 'planarRegionExperiment:enabled,clippedPlanarExperiment:clipped)')
        queries=once(queries,'    try planarRegionFixtures()', '    try clippedPlanarFixtures();try planarRegionFixtures()')
        queries=once(queries,'let a=evaluateRegions(false),b=evaluateRegions(true)', 'let a=evaluateRegions(false),u=evaluateRegions(true),b=evaluateRegions(true,true)')
        queries=once(queries,'"maximumDepthDifferenceMeters":try validateRegions(a.1,b.1)]',
            '"maximumDepthDifferenceMeters":try validateRegions(a.1,b.1),"unboundedBoundaryPairs":u.2.boundaryPairs]')
        queries=once(queries,'        let a:(Double,[[[RopeSegmentContact]]],RopePlanarWork),b:(Double,[[[RopeSegmentContact]]],RopePlanarWork)',
            '        let a:(Double,[[[RopeSegmentContact]]],RopePlanarWork),b:(Double,[[[RopeSegmentContact]]],RopePlanarWork),u:(Double,[[[RopeSegmentContact]]],RopePlanarWork)')
        queries=once(queries,'        if iteration%2==0 {a=evaluateRegions(false);b=evaluateRegions(true)} else {b=evaluateRegions(true);a=evaluateRegions(false)}', '''        if iteration%3==0 {a=evaluateRegions(false);u=evaluateRegions(true);b=evaluateRegions(true,true)}
        else if iteration%3==1 {b=evaluateRegions(true,true);u=evaluateRegions(true);a=evaluateRegions(false)}
        else {u=evaluateRegions(true);a=evaluateRegions(false);b=evaluateRegions(true,true)}''')
        queries=once(queries,'"candidateSeconds":b.0,"ratio":b.0/a.0', '"candidateSeconds":b.0,"unboundedSeconds":u.0,"ratio":b.0/a.0,"unboundedRatio":b.0/u.0')
        queries=once(queries,'    guard median<=2.0/3 else', '''    let incremental=pairs.map{$0["unboundedRatio"] as! Double}.sorted()[3];result["medianUnboundedRatio"]=incremental
    try persist(nil)
    guard median<=2.0/3,incremental<=0.80 else''')
        queries=queries.replace('planar full-output corpus ratio<=2/3','clipped planar corpus total<=2/3 and incremental<=.8')
    return source[:source.index('func fixtures()throws {')]+queries
