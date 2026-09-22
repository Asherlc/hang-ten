"""Protected offline simplification must not move boundaries or lose attributes."""
from pathlib import Path
import importlib.util
import numpy as np
import pytest
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))

def load_tool():
    assert importlib.util.find_spec('simplify_display_models') is not None, 'simplification implementation does not exist yet'
    import simplify_display_models
    return simplify_display_models

def test_compact_keeps_exact_corner_attributes():
    tool=load_tool()
    v=np.array([[0,0,0],[1,0,0],[1,1,0],[0,0,0],[1,1,0],[0,1,0]],np.float32)
    f=np.arange(6).reshape(2,3)
    n=np.tile([0,0,1],(2,3,1)).astype(np.float32)
    uv=v[f][...,:2]
    p,a,g=tool.compact_corners(v,f,{'normals':n,'st':uv})
    assert len(p)==4
    np.testing.assert_array_equal(p[g],v[f])
    np.testing.assert_array_equal(a['normals'][g],n)
    np.testing.assert_array_equal(a['st'][g],uv)

def test_compact_preserves_uv_seam():
    tool=load_tool()
    v=np.array([[0,0,0],[1,0,0],[1,1,0],[0,1,0]],np.float32)
    f=np.array([[0,1,2],[0,2,3]])
    uv=v[f][...,:2].copy();uv[1]+=1
    p,a,g=tool.compact_corners(v,f,{'st':uv})
    assert len(p)==6
    np.testing.assert_array_equal(a['st'][g],uv)

def test_invalid_indices_fail_closed():
    tool=load_tool()
    with pytest.raises(ValueError):tool.compact_corners(np.zeros((3,3)),np.array([[0,1,4]]),{})

def test_nonfinite_values_fail_closed():
    tool=load_tool()
    with pytest.raises(ValueError):tool.compact_corners(np.full((3,3),np.nan),np.array([[0,1,2]]),{})

def test_grid_simplification_preserves_open_border():
    tool=load_tool()
    x,y=np.meshgrid(np.linspace(0,1,21),np.linspace(0,1,21));v=np.c_[x.ravel(),y.ravel(),np.zeros(x.size)].astype(np.float32)
    f=[]
    for i in range(20):
        for j in range(20):
            a=i*21+j;f.extend([[a,a+1,a+22],[a,a+22,a+21]])
    f=np.array(f,np.uint32); n=np.tile([0,0,1],(len(v),1)).astype(np.float32)
    out=tool.reduce_mesh(v,f,{'normals':n,'st':v[:,:2]},target_ratio=.2,error_relative=.001)
    assert len(out['faces'])<len(f)//2
    before=tool.boundary_edge_positions(v,f)
    after=tool.boundary_edge_positions(out['points'],out['faces'])
    assert before==after
    assert out['protected_preserved']

def test_reject_in_place_export(tmp_path):
    tool=load_tool()
    p=tmp_path/'primary.usdz';p.write_bytes(b'not a model')
    with pytest.raises(ValueError,match='separate'):tool.optimize_file(p,p,{},'conservative')

def test_reject_hash_mismatch(tmp_path):
    tool=load_tool()
    p=tmp_path/'primary.usdz';p.write_bytes(b'not a model')
    with pytest.raises(ValueError,match='SHA'):tool.optimize_file(p,tmp_path/'out/primary.usdz',{'sha256':'wrong'},'conservative')

def test_crease_normals_keep_right_angle():
    tool=load_tool()
    p=np.array([[0,0,0],[1,0,0],[0,1,0],[0,0,1]],np.float32)
    f=np.array([[0,1,2],[0,3,1]],np.int32)
    n=tool.crease_normals(p,f,35)
    np.testing.assert_allclose(n[0],np.tile([0,0,1],(3,1)),atol=1e-6)
    np.testing.assert_allclose(n[1],np.tile([0,1,0],(3,1)),atol=1e-6)

def test_crease_normals_smooth_shallow_angle():
    tool=load_tool()
    p=np.array([[0,0,0],[1,0,0],[0,1,0],[0,-1,-.1]],np.float32)
    f=np.array([[0,1,2],[0,3,1]],np.int32)
    n=tool.crease_normals(p,f,35)
    np.testing.assert_allclose(n[0,0],n[1,0],atol=1e-6)
    assert np.linalg.norm(n[0,0])==pytest.approx(1)

def test_uniform_image_uv_cleanup_is_lossless():
    tool=load_tool()
    from PIL import Image
    import io
    a=io.BytesIO();Image.new('RGB',(1,1),(80,90,100)).save(a,format='PNG')
    assert tool.is_uniform_texture(a.getvalue())
    b=io.BytesIO();im=Image.new('RGB',(2,1));im.putpixel((1,0),(200,0,0));im.save(b,format='PNG')
    assert not tool.is_uniform_texture(b.getvalue())

def test_permissive_normal_seams_keep_physical_boundary():
    tool=load_tool()
    x,y=np.meshgrid(np.linspace(0,1,12),np.linspace(0,1,12));v=np.c_[x.ravel(),y.ravel(),np.zeros(x.size)].astype(np.float32)
    f=[]
    for i in range(11):
        for j in range(11):
            a=i*12+j;f.extend([[a,a+1,a+13],[a,a+13,a+12]])
    f=np.array(f,np.uint32);n=np.tile([0,0,1],(len(f),3,1)).astype(np.float32)
    n[:,:,0]=np.linspace(0,1e-5,len(f))[:,None]
    p,attrs,g=tool.compact_corners(v,f,{'normals':n})
    out=tool.reduce_mesh(p,g,attrs,target_ratio=.25,error_relative=.001,permissive=True)
    assert len(out['faces'])<len(f)//2
    assert tool.boundary_edge_positions(v,f)==tool.boundary_edge_positions(out['points'],out['faces'])

def test_planar_normal_stabilization_does_not_move_geometry():
    tool=load_tool()
    p=np.array([[0,0,0],[1,0,0],[0,1,0],[0,0,1]],np.float32)
    f=np.array([[0,1,2],[0,2,3]])
    n=np.tile([.1,.1,.98],(2,3,1)).astype(np.float32);copy=p.copy()
    new=tool.stabilize_planar_normals(p,f,n)
    np.testing.assert_array_equal(p,copy)
    np.testing.assert_array_equal(new[0],np.tile([0,0,1],(3,1)))
    np.testing.assert_array_equal(new[1],np.tile([1,0,0],(3,1)))

def test_canonical_layer_export_is_repeatable(tmp_path):
    tool=load_tool()
    from pxr import Sdf
    layer=Sdf.Layer.CreateAnonymous('source.usda')
    assert layer.ImportFromString('#usda 1.0\ndef Xform "Root"\n{\n custom string note = "pilot"\n}\n')
    a=tmp_path/'a.usdc';b=tmp_path/'b.usdc'
    tool.write_layer_canonical(layer,a);tool.write_layer_canonical(layer,b)
    assert a.read_bytes()==b.read_bytes()

def test_geometric_topology_detects_new_nonmanifold_edge():
    tool=load_tool()
    assert hasattr(tool,'topology_signature'), 'topology guard is absent'
    p=np.array([[0,0,0],[1,0,0],[0,1,0],[0,-1,0],[.5,0,1]],np.float32)
    original=np.array([[0,1,2],[1,0,3]],np.uint32)
    invalid=np.vstack([original,[0,1,4]])
    assert tool.topology_signature(p,original)['nonmanifoldEdges']==0
    assert tool.topology_signature(p,invalid)['nonmanifoldEdges']==1
