"""Read optional cord-guide cylinders from the final native CAD solid.

This module is loaded only by the FreeCAD authoring exporter. Feature names
select existing CAD construction; no runtime route points are authored here.
"""

def extract_native_cord_features(document,body,groove_names,bore_names):
    import FreeCAD as App
    import Part
    def vector(v,scale=1.):return [v.x*scale,v.z*scale,-v.y*scale]
    def shared_edges(a,b):
        return [e for e in a.Edges if e.Length>1e-7 and any(e.isSame(f) for f in b.Edges)]

    def merged_aperture(feature, origin, axis, radius, record, result):
        """Witness a real exterior aperture whose rim is removed by a guide.

        A selected intersecting native guide must share final wall topology with
        both the bore and the finite exterior face. Tool endpoints and unrelated
        parallel planes cannot establish this opening.
        """
        witnesses=[]
        for guide_name,g in result.items():
            if g["kind"]!="groove":continue
            guide=document.getObject(guide_name)
            go=guide.Placement.Base;ga=guide.Placement.Rotation.multVec(App.Vector(0,0,1));ga.normalize()
            if abs(ga.dot(axis))>1e-8:continue
            t=(go-origin).dot(axis);crossing=origin+axis*t
            if (crossing-go).cross(ga).Length>1e-7 or not 0<t<float(feature.Height):continue
            bore_faces=[body.Faces[i-1] for i in record["wallFaces"]]
            guide_faces=[body.Faces[i-1] for i in g["wallFaces"]]
            shared=sum(len(shared_edges(a,b)) for a in bore_faces for b in guide_faces)
            if not shared:continue
            overlap=feature.Shape.common(guide.Shape).Volume
            if overlap<=1e-8:continue
            cavity=feature.Shape.fuse(guide.Shape)
            if len(cavity.Solids)!=1 or cavity.common(body).Volume>1e-8:continue
            circle=Part.makeCircle(radius,crossing,axis)
            disk=Part.Face(Part.Wire([circle]))
            area=disk.common(body).Area
            # Start just within the bore cutoff, end outside its actual side
            # plane. The complete finite axis crossing must be a native void.
            entry=Part.makeLine(origin+axis*1e-6,crossing+axis*1e-3)
            length=entry.common(body).Length
            if area>1e-8 or length>1e-8 or body.isInside(crossing+axis*1e-3,1e-8,True):continue
            planes=[]
            for i,face in enumerate(body.Faces):
                if not isinstance(face.Surface,Part.Plane):continue
                u0,u1,v0,v1=face.ParameterRange
                if face.normalAt((u0+u1)/2,(v0+v1)/2).dot(axis)<1-1e-8:continue
                point=face.valueAt((u0+u1)/2,(v0+v1)/2)
                if abs((point-crossing).dot(axis))>1e-7:continue
                edges=sum(len(shared_edges(face,f)) for f in guide_faces)
                distance=face.distToShape(Part.Vertex(crossing))[0]
                if not edges or distance>radius+float(guide.Radius)+1e-7:continue
                planes.append((t/1000,i+1,distance/1000))
            if planes:
                witnesses.append((planes,{"guideFeature":guide_name,"sharedWallEdges":shared,
                    "finiteToolOverlapMM3":overlap,"nativeCavityMaterialVolumeMM3":cavity.common(body).Volume,
                    "apertureMaterialAreaMM2":area,"axisMaterialLengthMM":length,
                    "outerPlaneStationMM":t,"boreWallAxialBoundsMM":[v*1000 for v in record["axialBounds"]]}))
        if len(witnesses)!=1:return None
        return witnesses[0]

    result={}
    for kind,names in (("groove",groove_names),("bore",bore_names)):
        for name in names:
            feature=document.getObject(name)
            if feature is None or not hasattr(feature,"Radius") or not hasattr(feature,"Height"):
                raise ValueError(f"native cord feature {name} is not an existing cylinder")
            origin=feature.Placement.Base;axis=feature.Placement.Rotation.multVec(App.Vector(0,0,1));axis.normalize()
            components=[abs(axis.x),abs(axis.y),abs(axis.z)]
            if max(components)<1-1e-10:raise ValueError("native cord feature extraction currently requires an axis-aligned cylinder")
            radius=float(feature.Radius);faces=[];stations=[]
            for i,face in enumerate(body.Faces):
                surface=face.Surface
                if not isinstance(surface,Part.Cylinder) or abs(surface.Radius-radius)>1e-7 or surface.Axis.cross(axis).Length>1e-8 or (surface.Center-origin).cross(axis).Length>1e-7:continue
                bounds=face.optimalBoundingBox(False,False)
                face_stations=[]
                # Exact geometry-only bounds, never the cached triangulation.
                for x in (bounds.XMin,bounds.XMax):
                    for y in (bounds.YMin,bounds.YMax):
                        for z in (bounds.ZMin,bounds.ZMax):face_stations.append((App.Vector(x,y,z)-origin).dot(axis)/1000)
                if max(face_stations)<-1e-8 or min(face_stations)>float(feature.Height)/1000+1e-8:continue
                stations.extend(face_stations);faces.append(i+1)
            if not faces:raise ValueError(f"native cord feature {name} has no wall in the final solid")
            record={"kind":kind,"origin":vector(origin,.001),"axis":vector(axis),"radius":radius/1000,"axialBounds":[min(stations),max(stations)],"wallFaces":faces,"nativeToolHeight":float(feature.Height)/1000}
            if kind=="bore":
                planes=[]
                for i,face in enumerate(body.Faces):
                    surface=face.Surface
                    if not isinstance(surface,Part.Plane) or abs(abs(surface.Axis.dot(axis))-1)>1e-8:continue
                    u0,u1,v0,v1=face.ParameterRange;point=face.valueAt((u0+u1)/2,(v0+v1)/2);station=(point-origin).dot(axis)/1000
                    if not 0<station<=record["nativeToolHeight"]+1e-8:continue
                    if abs(station-record["axialBounds"][1])>1e-8:continue
                    aperture_center=origin+axis*(station*1000)
                    distance=face.distToShape(Part.Vertex(aperture_center))[0]/1000
                    if abs(distance-record["radius"])>1e-8:continue
                    planes.append((station,i+1,distance))
                merged=None
                if not planes:
                    merged=merged_aperture(feature,origin,axis,radius,record,result)
                    if merged:planes=merged[0]
                if not planes:raise ValueError(f"native bore {name} has no actual exterior plane witness")
                outer=max(x[0] for x in planes);record.update(outerMouthStation=outer,outerPlaneFaces=[i for u,i,d in planes if abs(u-outer)<1e-8],outerPlaneApertureDistances=[d for u,i,d in planes if abs(u-outer)<1e-8],outerMouthDefinition="Existing final-solid exterior plane intersected by bore axis; nonplanar groove rim is not a tool endpoint.")
                if merged:
                    record["mergedApertureWitness"]=merged[1]
                    record["outerMouthDefinition"]="Actual outward final-solid side plane adjacent to selected native guide; finite bore/guide union and aperture/axis void certified. Circular rim is removed by the merged groove, not moved to a tool endpoint."
            result[name]=record
    return result
