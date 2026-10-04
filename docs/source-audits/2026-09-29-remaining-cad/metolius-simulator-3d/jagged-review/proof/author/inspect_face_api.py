import FreeCAD as A,Part
print([x for x in dir(Part.Face) if any(k in x.lower() for k in ['uv','tess','mesh','triang','param','split'])])
