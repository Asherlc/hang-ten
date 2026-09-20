"""Astra-authored Trango display corrections from approved F2/F5/F6/F7 and N3/N4/N5.
Original geometry.py and product excerpt retained beside this derivative.
Numbers are display estimates, not manufacturing measurements or training facts.
No image sampling or tracing. Source is millimetres, Z up, front -Y.
"""
import sys,json,hashlib
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import numpy as np
from authored_geometry import Assembly,Unit,rounded_outline,smooth,band
ORDER=['','','trango-rock-prodigy-forge','trango-rock-prodigy-natural']
def reg(a,id,desc,refs,depth=None,**kw):
    a.hold(id,desc,refs,displayDepthEstimateMm=depth,**kw)
    return id

def jug_profile(zmax,crest=6,rear=-7):
    ts=[0,.035,.08,.16,.28,.42,.58,.73,.86,.95,1]
    zs=[0,1.2,2.8,4.5,crest,crest,crest*.75,crest*.3,-1.2,rear*.7,rear]
    return lambda x,z,t: np.interp(t,ts,zs)*smooth(zmax-18,zmax-2,z)

def channel_distance(x,z,points):
    x,z=np.broadcast_arrays(x,z);result=np.full(x.shape,np.inf)
    for (ax,az),(bx,bz) in zip(points,points[1:]):
        dx=bx-ax;dz=bz-az;t=np.clip(((x-ax)*dx+(z-az)*dz)/(dx*dx+dz*dz),0,1)
        result=np.minimum(result,np.hypot(x-ax-t*dx,z-az-t*dz))
    return result

# An explicit recess area, with a broad return around the thumb tab, replaces
# the first trial's constant-width centerline canal. These points are authored
# section estimates, never sampled from an image.
NATURAL_RECESS=[(95,-12),(194,-22),(194,-31),(126,-28),(122,-25),(119,-23),(116,-25),(116,-28),(119,-33),(119,-37),(115,-41),(97,-41),(94,-38)]
FORGE_RECESS=[(218,-4),(125,-4),(123,1),(104,1),(99,-4),(100,-10),(107,-18),(107,-28),(114,-28),(114,-19),(121,-16),(218,-16)]
NATURAL_RECESS=rounded_outline(NATURAL_RECESS,[3,2,2,2,1.5,2,1.5,2,2,2,3,3,3],step=1000).tolist()
FORGE_RECESS=rounded_outline(FORGE_RECESS,[2,2,2,3,3,3,3,3,3,3,3,2],step=1000).tolist()
def recess_depth(x,z,points,depth,radius):
    x,z=np.broadcast_arrays(x,z);inside=np.zeros(x.shape,dtype=bool)
    for (ax,az),(bx,bz) in zip(points,points[1:]+points[:1]):
        if bz!=az:
            inside^=((az>z)!=(bz>z)) & (x<(bx-ax)*(z-az)/(bz-az)+ax)
    distance=channel_distance(x,z,points+points[:1])
    signed=np.where(inside,distance,-distance)
    return depth*smooth(-radius,radius,signed)
def natural_thickness(x,z):
    return 38.1-recess_depth(x,z,NATURAL_RECESS,10,2.1)

def forge_thickness(x,z):
    base=43+14*smooth(215,242,x)
    # Wider rounded transition bands replace squared, narrowly sampled jaws.
    upper=32*smooth(222,244,x)*band(z,-23,48,7)
    lower=19*smooth(219,242,x)*band(z,-62,-46,5)
    # Arched upper crimper follows F2/F5's distinct curved brow.
    brow_z=39+5*np.sin(np.pi*np.clip((x-23)/94,0,1))
    brow=4*band(x,23,117,7)*band(z,brow_z-2,brow_z+2,2.5)
    crimp=recess_depth(x,z,FORGE_RECESS,7.5,2.0)
    return base+upper+lower+brow-crimp

def forge():
    slug=ORDER[2];a=Assembly(slug);W=323.85;H=133.35;top=59.0635
    # Right half authored inner -> outer. Left is deliberately mirrored, not relabelled.
    pts=[[0,53],[111,53],[121,top],[233,top],[304,36],[W,19],[W,-17],[304,-42],[282,-51],[282,-66.675],[237,-57],[215,-53],[196,-51],[183,-66.675],[124,-66.675],[113,-50],[85,-49],[76,-55],[25,-55],[13,-44],[13,-15],[0,-5]]
    out=rounded_outline(pts,[6,3,3,4,5,7,7,6,3,4,3,3,4,9,9,3,4,9,12,8,5,6],step=2.6)
    for mirror,side in [(True,'left'),(False,'right')]:
        ids={}
        for ident,desc,d in [
            ('sloper-30','30 degree outer sloper',None),('sloper-40','40 degree middle sloper',None),
            ('flat-edge','Inner upper flat edge',None),('slopey-crimper','Curved brow above rail',None),
            ('rail','One continuous variable-depth rail',[7,20]),('mr-deep','Inner deep MR pocket',25),
            ('mr-shallow','Inner shallow MR pocket',15),('closed-crimp','Closed crimp and integral thumb shoulder',7.5),
            ('imr','One continuous three-finger pocket; IM options reuse it',[19,31]),
            ('pinch-medium','Outer upper pinch-jaw contact',50),('pinch-narrow','Outer lower pinch-jaw contact',25)]:
            ids[ident]=reg(a,side+'-'+ident,desc,['F2','F3','F5','F6','F7'],None if ident.startswith('pinch-') else d,**({'nominalPinchWidthMm':d} if ident.startswith('pinch-') else {}))
        thick=forge_thickness
        def flabel(x,z):
            if x>237 and -24<z<49:return ids['pinch-medium']
            if x>235 and -65<z<-44:return ids['pinch-narrow']
            if 99<x<218 and -31<z<-1.5:return ids['closed-crimp']
            if 25<x<115 and 36<z<49:return ids['slopey-crimper']
            return 'body'
        def profile(x,z,t):
            slope=np.tan(np.deg2rad(40))*smooth(107,119,x)
            slope+=(np.tan(np.deg2rad(30))-np.tan(np.deg2rad(40)))*smooth(229,241,x)
            if t<=.14:d=t
            elif t<.20:q=t-.14;d=.14+q-q*q/.12
            else:d=.17
            return d*thick(x,z)*slope*smooth(20,30,z)*(1-.3*smooth(.75,1,t))
        def elabel(x,z,t):
            if z>25 and t<.18:
                if x>235:return ids['sloper-30']
                if x>113:return ids['sloper-40']
                return ids['flat-edge']
            return 'body'
        u=Unit(a,side,out,thick,offset=(-76.2 if mirror else 76.2),mirror=mirror,top_profile=profile,edge_label=elabel,front_label=flabel,front_resolution=3.5)
        u.cavity({'center':[117,24],'width':175,'height':20,'radius':8,'slope':-.06,'depth':{'kind':'linear','x':[29.5,204.5],'values':[7,20]},'holds':[{'id':ids['rail']}],'lipRadius':2.3,'floorAngleEstimateDeg':6,'lipProfile':'authored-noncircular'})
        u.cavity({'center':[41,-5],'width':47,'height':21,'radius':8,'depth':25,'floorAngleEstimateDeg':6,'lipProfile':'authored-noncircular','holds':[{'id':ids['mr-deep']}]})
        u.cavity({'center':[41,-35],'width':48,'height':22,'radius':8,'depth':15,'floorAngleEstimateDeg':6,'lipProfile':'authored-noncircular','holds':[{'id':ids['mr-shallow']}]})
        # Small ergonomic scallops belong to one IMR contact, not three new holds.
        u.cavity({'center':[153,-47],'width':66,'height':24,'radius':9,'depth':{'kind':'steps','cuts':[153],'values':[19,31],'blend':3},'dips':[{'x0':125,'x1':136,'amount':1.5,'blend':2},{'x0':164,'x1':176,'amount':1.5,'blend':2}],'holds':[{'id':ids['imr']}],'floorAngleEstimateDeg':6,'lipProfile':'authored-noncircular','lipRadius':2.4},through=[{'center':[157,-44],'radius':6.5,'kind':'observed-through-opening-purpose-unresolved'}])
        u.finish()
    return a


def natural():
    slug=ORDER[3];a=Assembly(slug);W=190.5;H=152.4;top=70.2
    pts=[[0,top],[W,top],[W,-76.2],[42,-76.2],[38,-37],[0,-37]]
    out=rounded_outline(pts,[20,20,19,18,7,16],step=2.4)
    for mirror,side in [(True,'left'),(False,'right')]:
        ids={}
        for ident,desc,d in [
            ('jug','Continuous top jug (manual nominal 40 mm)',40),
            ('rail-upper','Upper variable rail, outside 20 to inside 33',[20,33]),
            ('rail-lower','Lower variable rail, outside 10 to inside 24',[10,24]),
            ('closed-crimp','Open-ended crimp channel and thumb shoulder (display estimate only)',10),
            ('pocket-3finger','Deep three-finger pocket',38),
            ('pocket-2finger','Lower two-finger pocket (display estimate only)',27),
            ('pocket-supported','Supported pocket, outside30 to inside27 (display estimate only)',[30,27]),
            ('pinch-thumb','Bottom thumb opposition shared by medium and wide pinches',None)]:
            ids[ident]=reg(a,side+'-'+ident,desc,['N1','N2','N3','N4','N5'],d)
        thick=natural_thickness
        def flabel(x,z):
            return ids['closed-crimp'] if x>89 and -44<z<-9 else 'body'
        def elabel(x,z,t):
            if z>top-4:return ids['jug']
            if z<-72 and 54<x<177:return ids['pinch-thumb']
            return 'body'
        u=Unit(a,side,out,thick,offset=-50 if mirror else 50,mirror=mirror,top_profile=jug_profile(top),edge_label=elabel,front_label=flabel,front_resolution=3)
        u.cavity({'center':[95,47],'width':164,'height':21,'radius':8,'slope':-.065,'depth':{'kind':'linear','x':[13,177],'values':[33,20]},'holds':[{'id':ids['rail-upper']}]})
        u.cavity({'center':[95,15],'width':164,'height':20,'radius':7,'slope':-.055,'depth':{'kind':'linear','x':[13,177],'values':[24,10]},'holds':[{'id':ids['rail-lower']}]})
        u.cavity({'center':[48,-18],'width':70,'height':23,'radius':9,'depth':38,'holds':[{'id':ids['pocket-3finger']}],'lipRadius':1.5})
        u.cavity({'center':[76,-57],'width':42,'height':24,'radius':9,'depth':27,'holds':[{'id':ids['pocket-2finger']}]})
        u.cavity({'center':[145,-57],'width':58,'height':23,'radius':8,'depth':{'kind':'steps','cuts':[145],'values':[27,30],'blend':1.2},'dip':{'x0':127,'x1':137,'amount':1.2,'blend':2},'holds':[{'id':ids['pocket-supported']}]},through=[{'center':[162,-56],'radius':6.3,'kind':'observed-through-opening-purpose-unresolved'}])
        u.finish()
    return a



def build(product):
    a=globals()[product]();m=a.mesh()
    # Native authoring output keeps exact assembled normals and disjoint partitions.
    out=Path.cwd()/'.context/hangboards-batch-05-astra-migration/prepared'
    out.mkdir(parents=True,exist_ok=True)
    path=out/('trango-rock-prodigy-'+product+'-authored.npz')
    np.savez_compressed(path,vertices=m.vertices,faces=m.faces,normals=m.vertex_normals,labels=np.array(a.labels))
    print(product,len(m.vertices),len(m.faces),m.is_watertight,m.is_winding_consistent,flush=True)
    assert m.is_watertight and m.is_winding_consistent
    (out/('trango-rock-prodigy-'+product+'-authored.json')).write_text(json.dumps({'product':product,'artifactSHA256':hashlib.sha256(path.read_bytes()).hexdigest(),'mountingOpenings':a.mounts,'probes':a.probes,'vertices':len(m.vertices),'triangles':len(m.faces),'watertight':bool(m.is_watertight),'windingConsistent':bool(m.is_winding_consistent),'geometryIsDisplayEstimate':True},indent=2)+'\n')
if __name__=='__main__':
    for product in sys.argv[1:] or ['forge','natural']:build(product)
