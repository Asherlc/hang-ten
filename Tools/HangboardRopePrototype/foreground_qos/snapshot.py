"""Owned host scheduling discriminator; physics and worker arithmetic unchanged."""
from pathlib import Path
from armijo.snapshot import once

def driver_source(source,enabled=True):
    source=source[:source.index('func fixtures()throws')]+Path(__file__).with_name('Main.swift.txt').read_text()
    source=once(source,'func run(_ x:inout RopeDynamicsSolver)throws->',
        'var foregroundExperiment=false\nfunc run(_ x:inout RopeDynamicsSolver)throws->')
    source=once(source,'    ArmijoTrace.collectDerivatives=x.armijoExperiment',
        '''    let requested=foregroundExperiment ? QOS_CLASS_USER_INITIATED:QOS_CLASS_DEFAULT
    guard pthread_set_qos_class_self_np(requested,0)==0 else {throw RopePhysicsError.invalid("owned thread QoS set")}
    defer {precondition(pthread_set_qos_class_self_np(QOS_CLASS_DEFAULT,0)==0)}
    var relative:Int32=0,observed=QOS_CLASS_UNSPECIFIED
    guard pthread_get_qos_class_np(pthread_self(),&observed,&relative)==0,observed==requested else {throw RopePhysicsError.invalid("owned thread QoS observation")}
    ArmijoTrace.collectDerivatives=x.armijoExperiment''')
    return source.replace('// ENABLED',str(enabled).lower())

def collider_source(source):
    source=once(source,'    let pointCount:Int,linkCount:Int\n    init(points:Int) {',
        '''    let pointCount:Int,linkCount:Int
    let observedQoS:UnsafeMutablePointer<qos_class_t>?
    init(points:Int) {
        observedQoS=ForegroundQoSTrace.observe ? .allocate(capacity:8):nil
        observedQoS?.initialize(repeating:QOS_CLASS_UNSPECIFIED,count:8)''')
    source=once(source,'    deinit {inside.deinitialize',
        '    deinit {observedQoS?.deinitialize(count:8);observedQoS?.deallocate();inside.deinitialize')
    source=once(source,'            for i in ranges(points.count,job)',
        '            if let observation=storage.observedQoS {var value=QOS_CLASS_UNSPECIFIED;precondition(pthread_get_qos_class_np(pthread_self(),&value,nil)==0);observation[job]=value}\n            for i in ranges(points.count,job)')
    source=once(source,'            for i in ranges(links,job)',
        '            if let observation=storage.observedQoS {var value=QOS_CLASS_UNSPECIFIED;precondition(pthread_get_qos_class_np(pthread_self(),&value,nil)==0);observation[4+job]=value}\n            for i in ranges(links,job)')
    source=once(source,'        var p=Array(repeating:[RopeSegmentContact](),count:points.count)',
        '''        if let observation=storage.observedQoS {
            ForegroundQoSTrace.workers.append(["parity":(0..<jobs).map{String(describing:observation[$0])},
                "links":(0..<jobs).map{String(describing:observation[4+$0])}])
        }
        var p=Array(repeating:[RopeSegmentContact](),count:points.count)''')
    return source
