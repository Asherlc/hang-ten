from pathlib import Path

def collider_source(text):
    needle='    private let tree: [Node]\n'
    assert text.count(needle)==1
    text=text.replace(needle,needle+'    private let leafReplay=RopeLeafReplay()\n')
    start=text.index('        while let (index,parent)=stack.popLast()',text.index('    func fusedContactEvaluation('))
    end=text.index('        var minimum=Double.infinity',start)
    traversal=text[start:end]
    text=text[:start]+'''        let replayKey=leafReplay.key(start,end,rowRadius,meritRadius)
        if leafReplay.mode==2 {faces=leafReplay.lookup(replayKey)} else {
'''+traversal+'''            faces.sort(by:{$0.0<$1.0})
            if leafReplay.mode==1 {leafReplay.record(replayKey,faces)}
        }
'''+text[end:]
    text=text.replace('        for (index,mask) in faces.sorted(by:{$0.0<$1.0}) {','        for (index,mask) in faces {')
    return text+'\n'+(Path(__file__).parent/'Replay.swift').read_text()
