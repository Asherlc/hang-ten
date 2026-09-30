import simd

/// Computes a feasible threaded chain. Geometry-derived bearing points are
/// initialization only; the dynamics solver may slide them within each region.
enum RopeThreadedSeed {
    enum Placement {case gravityBearing,apertureCenter}
    private struct Route {
        let rope: RopePhysicsRope
        var points: [SIMD3<Double>]
        var nodeIndices: [Int: Int]
        var channelEdges: [Int: String]
    }

    static func make(input: RopePhysicsInput, profileID: String, orientation: simd_quatd,
                     collider: RopeTriangleCollider, placement:Placement = .gravityBearing) throws -> RopeSimulationState {
        guard let profile=input.profiles.first(where:{$0.id == profileID}),
              orientation.vector.x.isFinite, orientation.vector.y.isFinite,
              orientation.vector.z.isFinite, orientation.vector.w.isFinite,
              abs(simd_length(orientation.vector)-1) < 1e-8 else {
            throw RopePhysicsError.invalid("Invalid seed profile or orientation")
        }
        let portalMap=Dictionary(uniqueKeysWithValues:input.portals.map{($0.id,$0)})
        let up=orientation.inverse.act(SIMD3<Double>(0,1,0))
        func makeRoutes(height: Double) throws -> [Route] {
        var routes:[Route]=[]
        for rope in profile.ropes {
            var targets:[SIMD3<Double>]=[]
            for node in rope.nodes {
                if let id=node.portalID, let portal=portalMap[id] {
                    switch placement {
                    case .gravityBearing:
                        targets.append(try RopeRegionGeometry.bearing(portal,radius:rope.radius,up:up))
                    case .apertureCenter:
                        // A geometry-derived unseated initialization also lets
                        // tests establish that dynamics computes the bearing.
                        let region=try RopeRegionGeometry.erodedBoundary(portal,radius:rope.radius)
                        targets.append(region.reduce(.zero,+)/Double(region.count))
                    }
                } else if let point=node.point {
                    targets.append(node.kind == "support" ? orientation.inverse.act(point-SIMD3(0,height,0)) : point)
                } else { throw RopePhysicsError.invalid("Missing seed graph target") }
            }
            var route=Route(rope:rope,points:[targets[0]],nodeIndices:[0:0],channelEdges:[:])
            for (index,edge) in rope.edges.enumerated() {
                let a=targets[index], b=targets[index+1]
                let path:[SIMD3<Double>]
                if edge.kind == "channel" {
                    guard let channel=input.channels.first(where:{$0.id == edge.channelID}),channel.spine.count == 2,
                          collider.segmentContact(from:a,to:b,radius:rope.radius+RopeRegionGeometry.clearance-1e-9) == nil else {
                        throw RopePhysicsError.invalid("Channel requires a feasible straight traversal adapter")
                    }
                    path=[a,b]
                } else if collider.segmentContact(from:a,to:b,radius:rope.radius+RopeRegionGeometry.clearance) == nil {
                    path=[a,b]
                } else {
                    guard let portalID=rope.nodes[index].portalID ?? rope.nodes[index+1].portalID,
                          let portal=portalMap[portalID] else {
                        throw RopePhysicsError.invalid("Exterior wrap needs a reviewed topology adapter")
                    }
                    let startsAtPortal=rope.nodes[index].kind == "portal"
                    let computed=try exteriorPath(from:startsAtPortal ? a:b,to:startsAtPortal ? b:a,
                        portal:portal,up:up,radius:rope.radius,collider:collider)
                    path=startsAtPortal ? computed:Array(computed.reversed())
                }
                let first=route.points.count-1
                route.points += path.dropFirst()
                if let id=edge.channelID { for i in first..<(route.points.count-1) { route.channelEdges[i]=id } }
                route.nodeIndices[index+1]=route.points.count-1
            }
            routes.append(route)
        }
        return routes
        }
        func moved(_ route:Route,_ height:Double) -> [SIMD3<Double>] {
            var points=route.points
            for (nodeIndex,pointIndex) in route.nodeIndices {
                let node=route.rope.nodes[nodeIndex]
                if node.kind == "support",let point=node.point {
                    points[pointIndex]=orientation.inverse.act(point-SIMD3(0,height,0))
                }
            }
            return points
        }
        func length(_ points:[SIMD3<Double>]) -> Double {
            zip(points,points.dropFirst()).reduce(0) { $0+simd_distance($1.0,$1.1) }
        }
        let supportHeight=profile.ropes.flatMap{$0.nodes}.filter{$0.kind == "support"}.compactMap{$0.point?.y}.min()!
        let highestWood=input.collision.vertices.map{orientation.act($0).y}.max()!
        let radius=profile.ropes.map{$0.radius}.max()!
        var low = -max(0.4,profile.ropes.map{$0.restLength}.max()!)
        var high = supportHeight-highestWood-radius-0.003
        var routes=try makeRoutes(height:low)
        guard routes.allSatisfy({length($0.points) >= $0.rope.restLength}) else {
            throw RopePhysicsError.invalid("Rope exceeds bounded seed length workspace")
        }
        let upperRoutes=try makeRoutes(height:high)
        guard upperRoutes.allSatisfy({length($0.points) <= $0.rope.restLength}) else {
            throw RopePhysicsError.invalid("Rope is too short for the threaded board")
        }
        // Recompute bearings during this solve: a tangent valid at one height
        // need not remain clear at another. This is initialization work only.
        for _ in 0..<17 {
            let mid=(low+high)/2,candidate=try makeRoutes(height:mid)
            if candidate.contains(where:{length($0.points)>$0.rope.restLength}) { low=mid;routes=candidate }
            else {high=mid}
        }
        // This final tiny upward endpoint correction removes the bisection
        // residual without changing the already certified rim segments.
        var heights:[Double]=[]
        for route in routes {
            var a=low,b=high
            for _ in 0..<50 {
                let mid=(a+b)/2
                if length(moved(route,mid))>route.rope.restLength {a=mid}else{b=mid}
            }
            heights.append((a+b)/2)
        }
        guard let height=heights.first,heights.allSatisfy({abs($0-height)<0.0001}) else {
            throw RopePhysicsError.invalid("Ropes do not share a feasible board height")
        }
        var chains:[RopeChainState]=[]
        for route in routes {
            let points=moved(route,height)
            var positions:[SIMD3<Double>]=[orientation.act(points[0])+SIMD3(0,height,0)]
            var rest:[Double]=[], originalToParticle:[Int:Int]=[0:0], channels:[Int:String]=[:]
            for index in 0..<(points.count-1) {
                let a=points[index],b=points[index+1],distance=simd_distance(a,b)
                guard collider.segmentContact(from:a,to:b,radius:route.rope.radius+RopeRegionGeometry.clearance-1e-9) == nil else {
                    throw RopePhysicsError.invalid("Seed segment penetrates native wood")
                }
                let divisions=max(1,Int(ceil(distance/0.002)))
                for step in 1...divisions {
                    if let id=route.channelEdges[index] { channels[rest.count]=id }
                    rest.append(distance/Double(divisions))
                    positions.append(orientation.act(a+(b-a)*(Double(step)/Double(divisions)))+SIMD3(0,height,0))
                }
                originalToParticle[index+1]=positions.count-1
            }
            var supports:[Int:SIMD3<Double>]=[:],attachments:[Int:SIMD3<Double>]=[:],portals:[Int:String]=[:]
            for (nodeIndex,pointIndex) in route.nodeIndices {
                let node=route.rope.nodes[nodeIndex],particle=originalToParticle[pointIndex]!
                if node.kind == "support" { supports[particle]=node.point! }
                else if node.kind == "attachment" { attachments[particle]=node.point! }
                else { portals[particle]=node.portalID! }
            }
            chains.append(RopeChainState(id:route.rope.id,radius:route.rope.radius,linearMass:route.rope.linearMass,
                restLengths:rest,positions:positions,previousPositions:positions,velocities:Array(repeating:.zero,count:positions.count),
                supports:supports,attachments:attachments,portals:portals,channelSegments:channels))
        }
        var state=RopeSimulationState(profileID:profileID,boardMass:profile.boardMass,boardHeight:height,
                                   boardVerticalVelocity:0,orientation:orientation,ropes:chains)
        try RopePassageTopology.refresh(state:&state,input:input)
        return state
    }

    private struct Heap {
        var values:[(Double,Int)]=[]
        mutating func push(_ value:(Double,Int)) {
            values.append(value);var i=values.count-1
            while i>0 { let p=(i-1)/2; if values[p].0 <= values[i].0 { break }; values.swapAt(i,p);i=p }
        }
        mutating func pop() -> (Double,Int)? {
            guard !values.isEmpty else{return nil}
            let result=values[0],last=values.removeLast()
            if !values.isEmpty {
                values[0]=last;var i=0
                while 2*i+1<values.count {
                    var child=2*i+1
                    if child+1<values.count && values[child+1].0<values[child].0 { child += 1 }
                    if values[i].0<=values[child].0 {break};values.swapAt(i,child);i=child
                }
            }
            return result
        }
    }

    private static func exteriorPath(from mouth:SIMD3<Double>,to anchor:SIMD3<Double>,
        portal:RopePortalRegion,up:SIMD3<Double>,radius:Double,collider:RopeTriangleCollider) throws -> [SIMD3<Double>] {
        let normal=portal.normal, projected=up-normal*simd_dot(up,normal)
        guard simd_length(projected)>1e-6 else {
            throw RopePhysicsError.invalid("Axial hanging direction requires a 3D passage adapter")
        }
        let u=simd_normalize(projected),v=normal,spacing=0.001,offset=radius+RopeRegionGeometry.clearance
        let projections=collider.mesh.vertices.map{SIMD2(simd_dot($0-mouth,u),simd_dot($0-mouth,v))}
        let anchorUV=SIMD2(simd_dot(anchor-mouth,u),simd_dot(anchor-mouth,v))
        let top=projections.map{$0.x}.max()!+offset+spacing
        let minU=Int(floor(min(projections.map{$0.x}.min()!,0)/spacing))-20
        let maxU=Int(ceil(max(anchorUV.x,top)/spacing))+20
        let minV=Int(floor(min(projections.map{$0.y}.min()!,anchorUV.y)/spacing))-20
        let maxV=Int(ceil(max(projections.map{$0.y}.max()!,anchorUV.y)/spacing))+20
        let width=maxV-minV+1,count=(maxU-minU+1)*width
        guard count>0,count<500_000 else{throw RopePhysicsError.invalid("Seed search exceeds bounded workspace")}
        func index(_ a:Int,_ b:Int)->Int{(a-minU)*width+b-minV}
        func point(_ i:Int)->SIMD3<Double>{mouth+u*(Double(i/width+minU)*spacing)+v*(Double(i%width+minV)*spacing)}
        let start=index(0,0),goal=index(Int(anchorUV.x/spacing),Int(anchorUV.y/spacing))
        var distances=Array(repeating:Double.infinity,count:count),previous=Array(repeating:-1,count:count)
        var clearance=Array(repeating:Double.nan,count:count),heap=Heap()
        distances[start]=0;heap.push((simd_distance(mouth,anchor),start))
        func allowed(_ i:Int) -> Double {
            if clearance[i].isNaN {
                let p=point(i)
                // Stay on this mouth's exterior side until above the wood.
                // This preserves the selected threading class during search.
                if simd_dot(p-mouth,v) < -1e-10 && simd_dot(p-mouth,u)<top {clearance[i] = -.infinity}
                else{clearance[i]=collider.signedDistance(at:p)}
            }
            return clearance[i]
        }
        while let (_,current)=heap.pop() {
            if current == goal { break }
            let a=current/width+minU,b=current%width+minV,p=point(current)
            for du in -1...1 {for dv in -1...1 where du != 0 || dv != 0 {
                let aa=a+du,bb=b+dv
                guard aa>=minU,aa<=maxU,bb>=minV,bb<=maxV else{continue}
                let next=index(aa,bb),q=point(next),length=simd_distance(p,q)
                guard distances[current]+length < distances[next]-1e-12,allowed(next)>=offset-1e-10 else{continue}
                if min(allowed(current),allowed(next))<offset+length/2,
                   collider.segmentContact(from:p,to:q,radius:offset-1e-10) != nil {continue}
                distances[next]=distances[current]+length;previous[next]=current
                heap.push((distances[next]+simd_distance(q,anchor),next))
            }}
        }
        guard previous[goal]>=0 else{throw RopePhysicsError.invalid("No collision-free exterior seed route")}
        var path:[SIMD3<Double>]=[anchor],current=goal
        while current != start {path.append(point(current));current=previous[current]}
        path.append(mouth)
        // Exact shortcut queries remove grid stair steps without cutting rims.
        // Start at the support so the last bearing is a surface contact, not
        // an arbitrary high grid point retained beside the starting support.
        var result=[path[0]],i=0
        while i<path.count-1 {
            var next=path.count-1
            while next>i+1 && collider.segmentContact(from:path[i],to:path[next],radius:offset-1e-10) != nil {next -= 1}
            guard collider.segmentContact(from:path[i],to:path[next],radius:offset-1e-10) == nil else{
                throw RopePhysicsError.invalid("Grid route failed exact segment clearance")
            }
            result.append(path[next]);i=next
        }
        return Array(result.reversed())
    }
}
