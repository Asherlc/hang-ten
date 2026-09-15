"""Render an actual isolated GLB through VTK's independent glTF importer."""
import argparse,json,tempfile,shutil,sys
import numpy as np
from pathlib import Path
import vtk
from PIL import Image,ImageDraw,ImageFont
from asset_io import sha256

def render(path,out,views=None,title=None):
    path=Path(path).resolve(); out=Path(out); out.mkdir(parents=True,exist_ok=True)
    digest=sha256(path)
    with tempfile.TemporaryDirectory(prefix='hangboard-render-') as td:
        asset=Path(td)/'asset.glb'; shutil.copy2(path,asset)
        ren=vtk.vtkRenderer(); ren.SetBackground(.945,.951,.963)
        rw=vtk.vtkRenderWindow(); rw.SetOffScreenRendering(1);rw.SetUseSRGBColorSpace(False);rw.SetSize(1600,900);rw.SetMultiSamples(8);rw.AddRenderer(ren)
        imp=vtk.vtkGLTFImporter();imp.SetFileName(str(asset));imp.SetRenderWindow(rw);imp.Update()
        actors=ren.GetActors();actors.InitTraversal(); ac=[]
        while True:
            a=actors.GetNextActor()
            if a is None: break
            ac.append(a)
            a.GetProperty().SetInterpolationToPhong();a.GetProperty().SetAmbient(.30);a.GetProperty().SetDiffuse(.68);a.GetProperty().SetSpecular(.10);a.GetProperty().SetSpecularPower(32)
        if not ac: raise RuntimeError('VTK imported no actors from GLB')
        bounds=ren.ComputeVisiblePropBounds(); cx=(bounds[0]+bounds[1])/2;cy=(bounds[2]+bounds[3])/2;cz=(bounds[4]+bounds[5])/2
        w=bounds[1]-bounds[0]; h=bounds[3]-bounds[2]; d=bounds[5]-bounds[4]
        ren.RemoveAllLights()
        for vec,intensity in [((-1,1.5,2),.8),((1,.3,1),.45),((.2,1,-1),.35)]:
            light=vtk.vtkLight();light.SetLightTypeToSceneLight();light.SetPosition(cx+vec[0],cy+vec[1],cz+vec[2]);light.SetFocalPoint(cx,cy,cz);light.SetIntensity(intensity);ren.AddLight(light)
        cam=ren.GetActiveCamera();cam.ParallelProjectionOn();cam.SetViewUp(0,1,0)
        if views is None:
            views=[('01-canonical-front','CANONICAL FRONT',(0,0,2),(cx,cy,cz),max(w*.31,h*.66)),
                   ('02-reverse','REVERSE',(0,0,-2),(cx,cy,cz),max(w*.31,h*.66)),
                   ('03-oblique','OBLIQUE',(.9,.65,2),(cx,cy,cz),max(w*.31,h*.75)),
                   ('04-contact-detail','CONTACT DETAIL',(.45,.6,2),(cx-w*.19,cy,cz+d*.05),w*.12),
                   ('05-neutral-material','NEUTRAL MATERIAL / CONTINUITY',(-.25,.6,2),(cx+w*.18,cy+h*.12,cz+d*.1),w*.11),
                   ('06-side','SIDE PROFILE',(2,.3,.45),(cx,cy,cz),max(h*.75,w*.22))]
        records=[]
        for filename,label,view,target,scale in views:
            cam.SetFocalPoint(*target);cam.SetPosition(*(target[i]+view[i] for i in range(3)));cam.SetViewUp(0,1,0);cam.SetParallelScale(scale);ren.ResetCameraClippingRange();rw.Render()
            cap=vtk.vtkWindowToImageFilter();cap.SetInput(rw);cap.ReadFrontBufferOff();cap.Update()
            png=out/(filename+'.png');writer=vtk.vtkPNGWriter();writer.SetFileName(str(png));writer.SetInputConnection(cap.GetOutputPort());writer.Write()
            im=Image.open(png).convert('RGB')
            # Explicit display transfer for the linear material-factor review render.
            # Geometry, lighting and the GLB material remain unchanged; this is not a texture.
            linear=np.asarray(im,dtype=np.float64)/255.
            srgb=np.where(linear<=.0031308,12.92*linear,1.055*np.power(linear,1/2.4)-.055)
            im=Image.fromarray(np.uint8(np.clip(np.rint(srgb*255),0,255)))
            canvas=Image.new('RGB',(1600,1000),'white');canvas.paste(im,(0,60));draw=ImageDraw.Draw(canvas)
            try:
                font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',23);small=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',15)
            except OSError:font=small=ImageFont.load_default()
            draw.text((28,17),title or path.stem,font=font,fill=(32,41,54));draw.text((1180,22),label,font=small,fill=(65,76,90))
            draw.text((28,965),'ACTUAL GLB RENDER | VTK '+vtk.vtkVersion.GetVTKVersion()+' | neutral untextured material',font=small,fill=(65,76,90))
            draw.text((740,965),'GLB SHA-256 '+digest[:32]+'…',font=small,fill=(65,76,90));canvas.save(png)
            records.append({'path':png.name,'sha256':sha256(png),'assetSha256':digest,'label':label,'cameraPosition':list(cam.GetPosition()),'cameraTarget':list(target),'cameraUp':[0,1,0],'parallelScale':scale})
        result={'reader':'VTK vtkGLTFImporter','version':vtk.vtkVersion.GetVTKVersion(),'assetSha256':digest,'isolatedDirectoryContents':['asset.glb'],'actorCount':len(ac),'bounds':list(bounds),'shading':'Phong geometry review of imported linear material factors; explicit IEC sRGB output transfer; uncalibrated neutral lighting','useSRGBColorSpace':bool(rw.GetUseSRGBColorSpace()),'renders':records}
        (out/'render-provenance.json').write_text(json.dumps(result,indent=2))
        rw.Finalize()
        return result
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('glb');ap.add_argument('output');ap.add_argument('--title');args=ap.parse_args()
    print(json.dumps(render(args.glb,args.output,title=args.title),indent=2))
