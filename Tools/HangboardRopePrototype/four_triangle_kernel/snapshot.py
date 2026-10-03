from pathlib import Path

def collider_source(text):
    start=text.index('        for (index,mask) in faces.sorted(by:{$0.0<$1.0}) {',text.index('    func fusedContactEvaluation('))
    end=text.index('        return ([firstHits,rowHits,meritHits,lastHits]',start)
    loop=text[start:end]
    body=loop[loop.index('            let normal='):]
    assert body.endswith('        }\n')
    body=body[:-len('        }\n')]
    body=body.replace('let q=Self.triangleClosest(start,a,b,c)','let q=firstClosest.lane(lane)')
    body=body.replace('let q=Self.triangleClosest(end,a,b,c)','let q=lastClosest.lane(lane)')
    body=body.replace('if let t=Self.rayTriangle(start,end-start,a,b,c),t>=0,t<=1 {','if ray.1[lane],ray.0[lane]>=0,ray.0[lane]<=1 {\n                    let t=ray.0[lane]')
    body=body.replace('let ab=Self.segmentPair(start,end,a,b),bc=Self.segmentPair(start,end,b,c),ca=Self.segmentPair(start,end,c,a)',
                      'let ab=(pairs.0.0.lane(lane),pairs.0.1.lane(lane),pairs.0.2[lane]),bc=(pairs.1.0.lane(lane),pairs.1.1.lane(lane),pairs.1.2[lane]),ca=(pairs.2.0.lane(lane),pairs.2.1.lane(lane),pairs.2.2[lane])')
    prelude='''        let ordered=faces.sorted(by:{$0.0<$1.0})
        for offset in stride(from:0,to:ordered.count,by:4) {
            let count=min(4,ordered.count-offset)
            let f0=mesh.triangles[ordered[offset].0],f1=mesh.triangles[ordered[offset+min(1,count-1)].0]
            let f2=mesh.triangles[ordered[offset+min(2,count-1)].0],f3=mesh.triangles[ordered[offset+min(3,count-1)].0]
            let packet=RopeFourTriangleKernel(a:RopeFourVector(mesh.vertices[f0.x],mesh.vertices[f1.x],mesh.vertices[f2.x],mesh.vertices[f3.x]),
                b:RopeFourVector(mesh.vertices[f0.y],mesh.vertices[f1.y],mesh.vertices[f2.y],mesh.vertices[f3.y]),
                c:RopeFourVector(mesh.vertices[f0.z],mesh.vertices[f1.z],mesh.vertices[f2.z],mesh.vertices[f3.z]))
            let firstClosest=packet.closest(start),lastClosest=packet.closest(end),ray=packet.ray(start,end-start)
            let pairs=(packet.pair(start,end,packet.a,packet.b),packet.pair(start,end,packet.b,packet.c),packet.pair(start,end,packet.c,packet.a))
            for lane in 0..<count {
                let (index,mask)=ordered[offset+lane]
                let face=mesh.triangles[index],a=mesh.vertices[face.x],b=mesh.vertices[face.y],c=mesh.vertices[face.z]
'''
    text=text[:start]+prelude+body+'            }\n        }\n'+text[end:]
    return text+'\n'+(Path(__file__).parent/'Packet.swift').read_text()
