#!/usr/bin/env python3
"""Build a self-contained 360 point-cloud scene from a 2:1 panorama."""
from pathlib import Path
import argparse, base64, hashlib, html, json, math
import numpy as np
from PIL import Image
from depth_geometry import read_depth, save_depth
from stabilize_depth_map import stabilize_depth
from infer_depth_anything_v2 import infer_depth

def build_geometry(im, dep, rows=720, completion="none"):
    dep=dep.copy()
    h,w=dep.shape
    assert w==2*h and im.shape[:2]==dep.shape
    for i in range(32):
        weight=(1-i/32)**2
        target=(dep[:,i]+dep[:,-1-i])/2
        dep[:,i]=dep[:,i]*(1-weight)+target*weight
        dep[:,-1-i]=dep[:,-1-i]*(1-weight)+target*weight
    rng=np.random.default_rng(360)
    positions=[];colors=[];sizes=[];kinds=[]
    def add(xyz,rgb,spacing,kind):
        n=len(xyz)
        positions.append(np.asarray(xyz,dtype='<f4'))
        colors.append(np.asarray(rgb,dtype=np.uint8))
        sizes.append(np.broadcast_to(spacing,(n,)).astype('<f4'))
        kinds.append(np.full(n,kind,dtype=np.uint8))
    for row in range(rows):
        v=(row+.5)/rows
        lat=(.5-v)*np.pi
        count=max(8,round(rows*2*np.cos(lat)))
        u=((np.arange(count)+.5*(row%2)+rng.uniform(-.28,.28,count))/count)%1
        lat=lat+rng.uniform(-.28,.28,count)*np.pi/rows
        x=(u*w).astype(int)%w
        y=np.clip(((.5-lat/np.pi)*h).astype(int),0,h-1)
        d=dep[y,x]
        # Relative, artist-calibrated scene units; not metric reconstruction.
        radius=7+110*(1-np.maximum(d,0))**2.25
        sky=np.clip((lat-.35)/.25,0,1)*(1-np.clip(d/.15,0,1))
        radius=radius*(1-sky)+380*sky
        # The lower pavement joins a continuous ground surface. Keep downward
        # architecture above that surface rather than letting a filler plane cut it.
        ground_boundary=np.full_like(u,.78)
        ground=(y/h>ground_boundary).astype(float) if completion=="terrain" else np.zeros_like(u)
        floor_radius=4/np.maximum(-np.sin(lat),.05)
        radius=radius*(1-ground)+floor_radius*ground
        radius=np.where((lat<-.04)&(ground==0)&(completion=="terrain"),np.minimum(radius,3.96/np.maximum(-np.sin(lat),.001)),radius)
        lon=(u-.5)*2*np.pi
        direction=np.stack([np.sin(lon)*np.cos(lat),np.sin(lat),-np.cos(lon)*np.cos(lat)],axis=1)
        xyz=direction*radius[:,None]
        spacing=np.maximum(radius*np.pi/rows,.019)
        add(xyz,im[y,x],spacing,0)
        # Coarse rock backing, never repeated temple facades on unseen surfaces.
        rock=(d>.23)&(lat>-.60)&(lat<.72)&(rng.random(count)<.36)
        for thickness in ((1.5,4.0,8.0) if completion=="terrain" else ()):
            idx=np.where(rock)[0]
            rear=xyz[idx]+direction[idx]*thickness
            luminance=im[y[idx],x[idx]].astype(float).mean(axis=1)
            material=np.stack([luminance*1.10,luminance*.82,luminance*.57],axis=1)
            material*=rng.uniform(.7,1.05,len(idx))[:,None]
            add(rear,np.clip(material,0,255),spacing[idx]*1.8,1)
    # Continuous terrain fills ground revealed by camera translation. Colours
    # sample only the existing pavement/earth at the bottom of the panorama.
    for step,inner,outer in (((.10,0,32),(.32,32,105)) if completion=="terrain" else ()):
        axis=np.arange(-outer,outer,step)
        xx,zz=np.meshgrid(axis,axis)
        rr=np.hypot(xx,zz)
        keep=(rr<outer)&(rr>=inner)
        xx=xx[keep]+rng.uniform(-step*.45,step*.45,keep.sum())
        zz=zz[keep]+rng.uniform(-step*.45,step*.45,keep.sum())
        rr=np.hypot(xx,zz)
        yy=-4.045-np.maximum(rr-65,0)*.20
        uv=(np.arctan2(xx,-zz)/(2*np.pi)+.5)%1
        vv=.5-np.arctan2(yy,rr)/np.pi
        boundary=np.full_like(uv,.78)
        observed_ground=vv>boundary
        tx=(uv*w).astype(int)%w
        ty=np.clip((vv*h).astype(int),0,h-1)
        # Existing pavement where observed; subdued earth material elsewhere.
        matx=rng.integers(0,w,len(xx));maty=rng.integers(int(h*.87),int(h*.95),len(xx))
        terrain_rgb=im[maty,matx].astype(float)
        terrain_rgb=terrain_rgb*.45+np.array([88,64,44])*.55
        terrain_rgb[observed_ground]=im[ty[observed_ground],tx[observed_ground]]
        terrain_rgb*=rng.uniform(.88,1.04,len(xx))[:,None]
        add(np.stack([xx,yy,zz],axis=1),np.clip(terrain_rgb,0,255),step*1.05,2)
    xyz=np.concatenate(positions);rgb=np.concatenate(colors);spacing=np.concatenate(sizes);kind=np.concatenate(kinds)
    return xyz,rgb,spacing,kind

def write_scene(image, depth, output, *, rows=720, completion="none", title="360° 点云漫游",
                movement_range=20, speed=4, yaw=0, pitch=0, provenance="supplied-stable-depth", raw_depth=None):
    with Image.open(image) as source:
        im=np.asarray(source.convert('RGB'))
    dep=read_depth(depth)
    if dep.shape!=im.shape[:2]:
        raise ValueError('Depth dimensions must match the panorama; do not silently stretch depth')
    if not np.isfinite(dep).all() or float(np.ptp(dep))<1e-6:
        raise ValueError('Depth must contain finite, varying relative depth')
    if im.shape[1]!=2*im.shape[0] or im.shape[0]<64:
        raise ValueError('Input must be a 2:1 equirectangular panorama, at least 128 x 64')
    xyz,rgb,spacing,kind=build_geometry(im,dep,rows,completion)
    packed=np.zeros((len(xyz),20),dtype=np.uint8)
    packed[:,:12]=xyz.view(np.uint8).reshape(-1,12)
    packed[:,12:15]=rgb;packed[:,15]=255
    packed[:,16:20]=spacing.view(np.uint8).reshape(-1,4)
    digest=hashlib.sha256(image.read_bytes()).hexdigest()
    config={'yaw':yaw,'pitch':pitch,'speed':speed,'movementRange':movement_range,
            'minHeight':-3.1 if completion=='terrain' else -movement_range,'maxHeight':max(100,movement_range),
            'storageKey':f'panorama-cloud-v1:{digest}:{completion}'}
    template=(Path(__file__).resolve().parents[1]/'assets/panorama-pointcloud.html').read_text(encoding='utf-8')
    # Replace payload last so user-provided title text cannot alter embedded data.
    rendered=template.replace('__TITLE__',html.escape(title)).replace('__SUBTITLE__','全景深度 · 地形近似补全' if completion=='terrain' else '全景深度 · 360° 自由环顾')
    rendered=rendered.replace('__CONFIG__',json.dumps(config)).replace('__COUNT__',str(len(xyz))).replace('__POINTS__',base64.b64encode(packed.tobytes()).decode())
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(rendered,encoding='utf-8')
    dtype=np.dtype([('x','<f4'),('y','<f4'),('z','<f4'),('red','u1'),('green','u1'),('blue','u1'),('source_kind','u1')])
    ply=np.empty(len(xyz),dtype=dtype)
    for i,k in enumerate(('x','y','z')):ply[k]=xyz[:,i]
    for i,k in enumerate(('red','green','blue')):ply[k]=rgb[:,i]
    ply['source_kind']=kind
    ply_path=output.with_suffix('.ply')
    header=f'ply\nformat binary_little_endian 1.0\ncomment source_kind 0 panorama depth; 1 inferred rock; 2 inferred terrain\nelement vertex {len(xyz)}\nproperty float x\nproperty float y\nproperty float z\nproperty uchar red\nproperty uchar green\nproperty uchar blue\nproperty uchar source_kind\nend_header\n'
    ply_path.write_bytes(header.encode()+ply.tobytes())
    report={'image':str(image),'image_sha256':digest,'html':str(output),'ply':str(ply_path),
            'stable_depth':str(depth),'raw_depth':str(raw_depth) if raw_depth else None,
            'depth_provenance':provenance,'completion':completion,'points':len(xyz),
            'point_sources':{str(i):int((kind==i).sum()) for i in (0,1,2)},'camera':config,
            'limitations':'Relative depth, not metric or complete 3D reconstruction. Unseen architecture is not recovered. Large movements may reveal stretching and gaps.'}
    output.with_suffix('.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    return report

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('image',type=Path)
    g=p.add_mutually_exclusive_group()
    g.add_argument('--depth',type=Path,help='Existing stable depth; skip inference')
    g.add_argument('--raw-depth',type=Path,help='Existing raw depth; stabilize without inference')
    p.add_argument('--out-dir',type=Path)
    p.add_argument('--completion',choices=('none','terrain'),default='none',help='terrain is an explicit approximate outdoor completion')
    p.add_argument('--rows',type=int,default=720)
    p.add_argument('--movement-range',type=float)
    p.add_argument('--speed',type=float,default=4)
    p.add_argument('--yaw',type=float,default=0,help='Initial yaw in radians')
    p.add_argument('--pitch',type=float,default=0,help='Initial pitch in radians')
    p.add_argument('--title',default='360° 点云漫游')
    a=p.parse_args(argv)
    radius=a.movement_range if a.movement_range is not None else (95 if a.completion=='terrain' else 20)
    if not 128<=a.rows<=1000:p.error('--rows must be 128..1000')
    if not math.isfinite(radius) or not .1<=radius<=500:p.error('--movement-range must be 0.1..500')
    if not math.isfinite(a.speed) or not 1<=a.speed<=12:p.error('--speed must be 1..12')
    if not all(math.isfinite(v) for v in (a.yaw,a.pitch)):p.error('view angles must be finite')
    image=a.image.expanduser().resolve()
    with Image.open(image) as im:
        if im.width!=im.height*2 or im.height<64:p.error('Input must be a 2:1 equirectangular panorama, at least 128 x 64; ordinary images need panorama generation first')
    out=a.out_dir.expanduser().resolve() if a.out_dir else image.parent
    out.mkdir(parents=True,exist_ok=True)
    stable=out/f'{image.stem}-scene-depth-stable.png'
    raw=None
    if a.depth:
        depth=a.depth.expanduser().resolve()
        values=read_depth(depth)
        if depth!=stable:save_depth(values,stable)
        provenance='supplied-stable-depth'
    else:
        if a.raw_depth:
            raw=a.raw_depth.expanduser().resolve();provenance='supplied-raw-depth'
        else:
            raw=out/f'{image.stem}-scene-depth-raw.png'
            infer_depth(image,raw,backend='depth-anything-v2-small')
            provenance='depth-anything-v2-small'
        stabilize_depth(raw,stable)
    report=write_scene(image,stable,out/f'{image.stem}-360-pointcloud.html',rows=a.rows,completion=a.completion,
                       title=a.title,movement_range=radius,speed=a.speed,yaw=a.yaw,pitch=a.pitch,provenance=provenance,raw_depth=raw)
    print(json.dumps(report,ensure_ascii=False,indent=2))
    return 0

if __name__=='__main__':
    raise SystemExit(main())
