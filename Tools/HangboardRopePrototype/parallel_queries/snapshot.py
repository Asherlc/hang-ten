from pathlib import Path

def collider_source(source):return source+'\n'+Path(__file__).with_name('Batch.swift').read_text()

def solver_source(source):
    old="""            let board=rope.positions.map{candidate.boardPoint($0)},inside=board.map{collider.queryParity($0)}
            var p=Array(repeating:[RopeSegmentContact](),count:board.count),r:[[RopeSegmentContact]]=[],m:[[RopeSegmentContact]]=[]
            for link in rope.restLengths.indices {
                let contacts=collider.fusedContacts(from:board[link],to:board[link+1],rowRadius:rope.radius+RopeRegionGeometry.clearance+0.00005,
                    meritRadius:rope.radius+RopeRegionGeometry.clearance,startInside:inside[link],endInside:inside[link+1])
                p[link]=contacts[0];r.append(contacts[1]);m.append(contacts[2])
                if link==rope.restLengths.count-1 {p[link+1]=contacts[3]}
            }
            points.append(p);rows.append(r);merits.append(m)"""
    new="""            let board=rope.positions.map{candidate.boardPoint($0)}
            let batch=collider.fusedChainContacts(points:board,rowRadius:rope.radius+RopeRegionGeometry.clearance+0.00005,meritRadius:rope.radius+RopeRegionGeometry.clearance)
            points.append(batch.points);rows.append(batch.rows);merits.append(batch.merits)"""
    assert source.count(old)==1
    return source.replace(old,new)
