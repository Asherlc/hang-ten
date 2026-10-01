import FreeCAD as A,Part
s=Part.BSplineSurface();s.buildFromPolesMultsKnots([[A.Vector(x,y,z) for z in [0,10]] for x,y in [(0,0),(10,0),(10,10)]],[2,1,2],[2,2],[0,1,2],[0,1],False,False,1,1)
s.increaseDegree(8,3);f=s.toShape();p,t=f.tessellate(.28)
print('points',p,'triangles',t,'UV',f.getUVNodes(),'range',f.ParameterRange)
