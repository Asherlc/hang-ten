def render(t,colors,bounds):
 w,h=1000,636;span=np.maximum(bounds[1]-bounds[0],1e-6);scale=min((w-40)/span[0],(h-70)/span[1]);center=(bounds[0]+bounds[1])/2
 xy=t[:,:,:2].copy();xy[:,:,0]=w/2+scale*(xy[:,:,0]-center[0]);xy[:,:,1]=h/2-scale*(xy[:,:,1]-center[1])
 normal=np.cross(t[:,1]-t[:,0],t[:,2]-t[:,0]);norm=np.linalg.norm(normal,axis=1);norm[norm==0]=1;normal/=norm[:,None]
 light=.40+.60*np.clip(normal@np.array([.2,.4,.89]),0,1);shade=np.asarray(colors*light[:,None],dtype=np.uint8)
 color=np.full((h,w,3),255,np.uint8);depth=np.full((h,w),-np.inf)
 for i,v in enumerate(xy):
  lo=np.maximum(np.floor(v.min(0)).astype(int),[0,0]);hi=np.minimum(np.ceil(v.max(0)).astype(int),[w-1,h-1])
  if np.any(hi<lo):continue
  a,b,c=v;den=(b[1]-c[1])*(a[0]-c[0])+(c[0]-b[0])*(a[1]-c[1])
  if abs(den)<1e-10:continue
  yy,xx=np.mgrid[lo[1]:hi[1]+1,lo[0]:hi[0]+1];xx=xx+.5;yy=yy+.5
  u=((b[1]-c[1])*(xx-c[0])+(c[0]-b[0])*(yy-c[1]))/den
  v2=((c[1]-a[1])*(xx-c[0])+(a[0]-c[0])*(yy-c[1]))/den
  v3=1-u-v2;z=u*t[i,0,2]+v2*t[i,1,2]+v3*t[i,2,2]
  d=depth[lo[1]:hi[1]+1,lo[0]:hi[0]+1];cc=color[lo[1]:hi[1]+1,lo[0]:hi[0]+1]
  mask=(u>=-1e-8)&(v2>=-1e-8)&(v3>=-1e-8)&(z>d)
  d[mask]=z[mask];cc[mask]=shade[i]
 return Image.fromarray(color)
