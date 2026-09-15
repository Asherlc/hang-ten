"""Render the eight reviewed views after independent GLB import.
The source coordinates are Z-up; the camera records here are glTF Y-up.
"""
from pathlib import Path
import argparse
from render_glb import render
p=argparse.ArgumentParser();p.add_argument('glb',type=Path);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
# These are glTF Y-up camera coordinates, not source coordinates.
views=[('01-canonical-front','CANONICAL FRONT',(0,0,2),(0,.080,.030),.249),
('02-reverse','REVERSE',(0,0,-2),(0,.080,.030),.249),
('03-oblique','OBLIQUE',(1,.47,2),(0,.080,.030),.237),
('04-contact-detail','RAIL DETAIL',(.2,.8,2),(.12,.058,.036),.062),
('05-neutral-material','MATERIAL CONTINUITY',(-.4,.5,2),(-.10,.128,.045),.064),
('06-side','SIDE PROFILE',(2,0,0),(0,.080,.030),.096),
('07-rear-oblique','HOLLOW REAR',(-.55,.55,-2),(0,.080,.025),.242),
('08-rear-detail','REAR BOSS / SHELL',(.2,.55,-2),(-.196,.070,.016),.079)]
render(a.glb,a.output,views=views,title='Evolv Basic Training Board (Long)')
