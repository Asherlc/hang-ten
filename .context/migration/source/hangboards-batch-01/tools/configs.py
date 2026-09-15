"""Manually authored, product-specific dimensions and contact inventories.
Published numbers and display estimates are explicitly separated in each record.
Coordinates are mm in X-right / Y-rear / Z-up source frame; no image processing.
"""
import math

def pocket(id,x,z,width,height,depth,projection,kind='edge',published=True,refs=None,**kw):
    return dict(holdId=id,x=x,z=z,width=width,height=height,radius=min(height/2,kw.pop('radius',height/2)),
        floorY=-projection+depth,displayDepthMm=depth,publishedDepthMm=depth if published else None,
        depthClassification='published nominal' if published else 'authored estimate; per-position mapping unconfirmed',
        kind=kind,evidenceRefs=refs or ['P1','I1'],lipRound=kw.pop('lipRound',2),**kw)

def surface(id,label,xrange,yrange,zrange,**kw):
    return dict(id=id,label=label,xRange=xrange,yRange=yrange,zRange=zrange,evidenceRefs=['P1','I1'],**kw)

def woodbord():
    c=dict(slug='dewoodstok-woodbord',name='deWoodstok Woodbord',revision='FSC bamboo / EAN 7426870707987',
        material='Bamboo; neutral untextured approximation',dimensionsMm=[590,148,40],
        dimensionsClassification=['published retailer','published retailer','published retailer'],
        color=[.70,.55,.34],cornerRadiusMm=10,rimRadiusMm=3,targetTriangles=42000,voxelMm=.8,
        bodyCuts=[dict(kind='planePatch',xRange=[-400,400],intercept=148,slope=.25,blend=0,rim=2)],
        surfaceContacts=[surface('top-rim','Continuous declining upper rim',[-295,295],[-40.5,.1],[134,149])],
        pockets=[],mounts=[dict(x=s*184,z=z,radius=2.5) for s in (-1,1) for z in (50,91)],
        limitations=['The sixteen pocket locations and continuous upper rim are photo-supported; individual depth-to-position mapping is not published in the inspected references.',
          'All local radii, pocket widths/heights, mounting-hole centres and the 14-degree top slope are authored display estimates.',
          'The published depth families are preserved separately; do not interpret the estimated per-pocket depths as manufacturer measurements.'])
    for row,z,depths in [('upper',110,[35,35,30]),('middle',70,[25,None,16]),('lower',30,[20,20,13])]:
        for side,s in [('left',-1),('right',1)]:
            for col,x,width,dep in zip(['outer','two-finger','inner'],[238,150,74],[90,44,90],depths):
                if dep is None:continue
                c['pockets'].append(pocket(f'{row}-{col}-{side}',s*x,z,width,20,dep,40,published=False,kind='two-finger pocket' if col=='two-finger' else 'four-finger pocket'))
    c['publishedDepthFamiliesMm']={'fourFinger':[13,16,20,25,30,35],'twoFinger':[20,35]}
    return c

def escape():
    return dict(slug='escape-unlimited-board',name='Escape Unlimited Board',revision='EC72000 / dimensioned-photo revision',
        material='Baltic birch; neutral untextured approximation',dimensionsMm=[603.25,184.15,47.625],
        dimensionsClassification=['manufacturer dimensioned photo','manufacturer dimensioned photo','manufacturer dimensioned photo'],
        color=[.72,.60,.41],endRoundMm=4,targetTriangles=36000,voxelMm=.75,
        profileYZ=[[0,0],[-23,0],[-28,4],[-29,38],[-32,43],[-36,43],[-39,48],[-40,92],[-43,98],[-47.625,104],[-47.625,146]]+[[-47.625*math.cos(i*math.pi/128),146+38.15*math.sin(i*math.pi/128)] for i in range(1,64)]+[[0,184.15]],
        outlineXZ=[[-301.625,0],[301.625,0],[301.625,150],[293,178],[282,184.15],[-282,184.15],[-293,178],[-301.625,150]],
        surfaceContacts=[surface('top-roll','Continuous 60 mm nominal sloper / rounded top roll',[-302,302],[-48,0.1],[150,185],publishedGripLengthMm=60)],
        pockets=[pocket(f'{row}-{side}',s*148,z,267,height,depth,projection,refs=['P1','I1','I4'])
          for row,z,height,depth,projection in [('upper',123,28,45,47.625),('middle',70,25,20,40),('lower',22,22,15,28.5)]
          for side,s in [('left',-1),('right',1)]],
        mounts=[dict(x=s*285,z=z,radius=2.5,counterbore=4.5,counterboreFloorY=-(43 if z>100 else 23)) for s in (-1,1) for z in (20,132)],
        limitations=['The product-page text says 23.5 × 6 inches, but manufacturer dimensioned images say 23.75 × 7.25 × 1.875 inches. This asset explicitly follows the dimensioned-photo revision, not an asserted reconciliation.',
          'The 60 mm top label is a grip surface length, not a 60 mm perpendicular pocket depth; its exact curved arc length is not certified.',
          'Tier heights, step fillets, slot widths/heights and mounting centres are photo-derived estimates; rear is an unconfirmed planar approximation.'])



def metolius():
    c=dict(slug='metolius-wood-grips-ii-deluxe',name='Metolius Wood Grips II Deluxe',revision='WOOD005 / Deluxe, not Compact',
        material='FSC wood; neutral untextured approximation',dimensionsMm=[610,216,70],
        dimensionsClassification=['manufacturer','manufacturer','retailer rounded 7 cm; exact profile unconfirmed'],
        color=[.73,.58,.39],endRoundMm=3,outlineRoundMm=2.5,targetTriangles=65000,voxelMm=.8,gridPhaseMm=[.137,.173,.113],
        profileYZ=[[0,0],[-39,0],[-43,5],[-43,59],[-48,64],[-52,64],[-55,69],[-55,121],[-61,128],[-66,128],[-70,134],[-70,187],[-68,199],[-60,209],[-45,216],[0,216]],
        outlineXZ=[[-296,0],[296,0],[305,9],[305,205],[297,216],[247,216],[238,205],[81,205],[69,211],[-69,211],[-81,205],[-238,205],[-247,216],[-297,216],[-305,205],[-305,9]],
        surfaceContacts=[
            surface('01-jug-left','Diagram 1: outer jug, left',[-306,-240],[-71,.1],[186,217]),
            surface('01-jug-right','Diagram 1: outer jug, right',[240,306],[-71,.1],[186,217]),
            surface('02-flat-stopper-left','Diagram 2: 55 mm flat stopper, left',[-238,-80],[-71,.1],[194,217],publishedGripLengthMm=55),
            surface('02-flat-stopper-right','Diagram 2: 55 mm flat stopper, right',[80,238],[-71,.1],[194,217],publishedGripLengthMm=55),
            surface('12-round-stopper-centre','Diagram 12: 58 mm central round stopper',[-79,79],[-71,.1],[192,217],publishedGripLengthMm=58)],
        pockets=[],mounts=[dict(x=side*x,z=z,radius=2.5,
            evidenceRefs=['M-DIAGRAM-V2'],placementClassification='manually photo-derived centre; not a measured drilling template')
            for side in (-1,1) for x,z in [(215,180),(215,116),(215,55)]],
        limitations=['Overall width and height are manufacturer values. Projection 70 mm follows a rounded retailer listing, not a manufacturer dimensioned drawing.',
          'The 26 physical contacts and nonuniform 31/32/38 mm and 25/25/28 mm rows are corroborated by the readable Deluxe numbered diagram M-DIAGRAM-V2. Six mounting bores are now present; centres are estimates, not a drilling template.',
          'Tier profiles, outer-jug undercut, stopper curvature, pocket widths/heights and mounting centres are authored photo-derived estimates. The model does not claim a measured replica.',
          'Top 55/58 mm labels are grip surface dimensions and are not treated as blind-cavity depths. External screws and wood grain are omitted.'])
    for row,z,proj,edge_num,tri_num,two_num,central_num,edge_d,tri_d,two_d,centre_d in [
        ('upper',161,70,3,4,5,13,31,32,38,32),
        ('middle',96,55,6,7,8,14,25,25,28,25),
        ('lower',31,43,9,10,11,15,19,19,19,19)]:
        for side,sign in [('left',-1),('right',1)]:
            # Open ended outside ledges are deliberately cut beyond the body silhouette.
            c['pockets'].append(pocket(f'{edge_num:02}-edge-{side}',sign*275,z,110,25,edge_d,proj,kind='open-ended edge',refs=['P1','I1']))
            c['pockets'].append(pocket(f'{tri_num:02}-three-finger-{side}',sign*170,z,78,25,tri_d,proj,kind='three-finger pocket',refs=['P1','I1']))
            c['pockets'].append(pocket(f'{two_num:02}-two-finger-{side}',sign*95,z,48,25,two_d,proj,kind='two-finger pocket',refs=['P1','I1']))
        c['pockets'].append(pocket(f'{central_num:02}-four-finger-centre',0,z,110,25,centre_d,proj,kind='four-finger pocket',refs=['P1','I1']))
    return c


def moon():
    c=dict(slug='moon-armstrong-ash',name='Moon Armstrong',revision='60-112-ASH / sustainable Ash wooden revision',
        material='Ash; neutral untextured approximation',dimensionsMm=[650,165,55],
        dimensionsClassification=['manufacturer','manufacturer','manufacturer'],
        color=[.71,.59,.43],cornerRadiusMm=8,rimRadiusMm=3,targetTriangles=46000,voxelMm=.8,
        outlineXZ=[[-325,0],[325,0],[325,156],[317,165],[200,165],[193,145],[185,165],[80,165],[73,145],[60,145],[58,162],[-58,162],[-60,145],[-76,145],[-80,165],[-194,165],[-200,143],[-207,143],[-213,165],[-317,165],[-325,156]],
        bodyCuts=[],surfaceContacts=[],pockets=[],
        mounts=[dict(x=x,z=z,radius=2.5) for x in [-205,195] for z in [17,58,123]]+[dict(x=x,z=107,radius=2.5) for x in [-68,67]],
        limitations=['The Ash manufacturer photograph has an asymmetric column layout: four-edge columns at far left and right-of-centre, jug columns left-of-centre and far right. The asset preserves this layout rather than imposing mirror symmetry.',
          'The 21-contact inventory is manufacturer-supported. Local widths, heights, bores, radii and body relief are display estimates.',
          'The two mono openings now pass through as shown by the Ash photo. Their front nominal contact length remains 22 mm; a straight continuation to the planar estimated rear is an explicit display approximation, not verified rear machining or pulley routing.',
          'The central jug is now a rolled upper lip with an arched underside notch, not a capsule recess. Arch radius, undercut depth and rear termination are photo-derived display estimates. Logos, grain, pulley hardware and external mounting hardware are omitted.'])
    # Edge columns are physically asymmetric. Both have 35-degree top slopes.
    for side,x in [('left',-270),('right',130)]:
        c['bodyCuts'].append(dict(kind='planePatch',xRange=[x-53,x+53],intercept=178.5,slope=math.tan(math.radians(35)),blend=2,rim=2))
        c['surfaceContacts'].append(surface(f'top-35deg-{side}',f'35 degree top sloper: {side} edge column',[x-54,x+54],[-56,.1],[124,166],topPlane=[178.5,math.tan(math.radians(35))],surfaceBand=3,publishedAngleDegrees=35))
        for depth,z,projection in [(25,126,55),(20,86,47),(10,49,35),(8,20,30)]:
            if projection<55:
                c['bodyCuts'].append(dict(kind='profileVoid',xRange=[x-54,x+54],profileYZ=[[-100,z-15],[-projection,z-15],[-projection,z+15],[-100,z+15]],blend=3,rim=3))
            c['pockets'].append(pocket(f'edge-{depth:02}mm-{side}',x,z,96,20,depth,projection,refs=['P1','I1']))
    # Jug columns: left-of-centre and far right, not mirrored about the origin.
    for side,x in [('left',-140),('right',270)]:
        c['pockets'].append(pocket(f'jug-{side}',x,130,100,38,39,55,kind='incut jug',published=False,floorSlopeZ=-.18,refs=['P1','I1']))
        c['bodyCuts'].append(dict(kind='profileVoid',xRange=[x-57,x+57],profileYZ=[[-100,0],[-35,0],[-35,48],[-45,55],[-45,91],[-100,91]],blend=3,rim=3))
        c['pockets'].append(pocket(f'edge-15mm-{side}',x,74,100,23,15,45,refs=['P1','I1']))
    # Centre holds are broad open ledges, with an upper undercut jug.
    c['bodyCuts'].append(dict(kind='archedUndercut',x=0,xRange=[-73,73],baseZ=133,
        archRadius=18,bottomZ=111,floorY=-23,sideRound=2,floorRound=2,rim=2.5,
        evidenceRefs=['MOON-ASH-PHOTO-V2'],classification='photo-derived display profile; unmeasured radii'))
    c['surfaceContacts'].append(surface('jug-centre','Central rolled upper lip with arched underside',
        [-61,61],[-56,.1],[128,166],archBoundary=dict(baseZ=133,radius=18,band=4),
        profileEvidenceRefs=['MOON-ASH-PHOTO-V2'],profileClassification='photo-derived curvature and undercut estimates'))
    # The Ash photo shows uninterrupted open ledges at centre, not capsule pockets.
    c['bodyCuts'].append(dict(kind='profileVoid',xRange=[-73,73],blend=2,rim=1.5,
        profileYZ=[[-100,-10],[-36,-10],[-36,17],[-33,20],[-18,20],[-18,61],
                   [-41,66],[-44,70],[-44,78],[-41,82],[-22,82],[-22,117],
                   [-55,129],[-55,170],[-100,170]],evidenceRefs=['MOON-ASH-PHOTO-V2']))
    c['surfaceContacts'] += [
        surface('edge-22mm-centre','22 mm central open shelf',[-72,72],[-45,-20],[76,87],
                publishedDepthMm=22,depthClassification='manufacturer nominal',profileEvidenceRefs=['MOON-ASH-PHOTO-V2']),
        surface('edge-18mm-centre','18 mm central open shelf',[-72,72],[-37,-16],[15,25],
                publishedDepthMm=18,depthClassification='manufacturer nominal',profileEvidenceRefs=['MOON-ASH-PHOTO-V2'])]
    c['limitations'].append('Central 22/18 mm contacts are continuous open shelves. Tier Z positions, lip rounding and rear projection are photo-derived display estimates.')
    c['verificationRays']=[
      dict(feature='central arch clearance',originMm=[0,-65,142],direction=[0,1,0],expectedHitMm=[0,-23,142]),
      dict(feature='central jug lateral lip remains',originMm=[35,-65,142],direction=[0,1,0],expectedHitMm=[35,-55,142]),
      dict(feature='open middle shelf vertical access',originMm=[0,-33,100],direction=[0,0,-1],expectedHitMm=[0,-33,82]),
      dict(feature='open lower shelf vertical access',originMm=[0,-25,40],direction=[0,0,-1],expectedHitMm=[0,-25,20]),
      dict(feature='no false cap above lower shelf',originMm=[0,-65,55],direction=[0,1,0],expectedHitMm=[0,-18,55]),
      dict(feature='no false cap above middle shelf',originMm=[0,-65,110],direction=[0,1,0],expectedHitMm=[0,-22,110])]

    for side,x2,x1 in [('left',-164,-109),('right',292,236)]:
        c['pockets'].append(pocket(f'two-finger-22mm-{side}',x2,23,42,24,22,35,kind='two-finger pocket',refs=['P1','I1']))
        c['pockets'].append(pocket(f'one-finger-22mm-{side}',x1,23,19,24,22,35,kind='one-finger pocket',refs=['P1','I1','MOON-ASH-PHOTO-V2'],throughOpening=True,lipRound=1.5))
    return c


def linebreaker():
    c=dict(slug='target10a-linebreaker-base',name='target10a Linebreaker BASE',revision='talbBASE00000 / EAN 4260501621043',
        material='Yellow poplar; neutral untextured approximation',dimensionsMm=[580,150,55],
        dimensionsClassification=['manufacturer','manufacturer','manufacturer'],
        color=[.65,.58,.36],cornerRadiusMm=16,rimRadiusMm=3.5,targetTriangles=46000,voxelMm=.8,
        outlineXZ=[[-272,0],[272,0],[286,10],[290,26],[285,43],[278,52],[286,66],[290,95],[286,124],[275,143],[265,150],[185,150],[180,132],[83,132],[78,142],[-78,142],[-83,132],[-180,132],[-185,150],[-265,150],[-275,143],[-286,124],[-290,95],[-286,66],[-278,52],[-285,43],[-290,26],[-286,10]],
        surfaceContacts=[surface('top-jug-left','Upper outer jug, left',[-280,-181],[-56,.1],[126,151]),
            surface('top-jug-right','Upper outer jug, right',[181,280],[-56,.1],[126,151]),
            surface('top-sloper-left','Upper intermediate sloper, left',[-179,-83],[-56,.1],[99,143]),
            surface('top-sloper-right','Upper intermediate sloper, right',[83,179],[-56,.1],[105,143])],
        bodyCuts=[dict(kind='planePatch',xRange=[-180,-81],intercept=132,slope=math.tan(math.radians(32.5)),blend=3,rim=2),
                  dict(kind='planePatch',xRange=[81,180],intercept=132,slope=math.tan(math.radians(22.5)),blend=3,rim=2),
                  dict(kind='profileVoid',xRange=[-176,176],profileYZ=[[-100,0],[-36,0],[-36,37],[-42,45],[-55,53],[-100,53]],blend=4,rim=3)],
        pockets=[],mounts=[dict(x=x,z=z,radius=2.5) for x,z in [(-233,116),(233,116),(-40,116),(40,116),(-201,26),(201,26)]],
        publishedDepthFamiliesMm={'fourFinger':[16,20,37],'threeFinger':[18,28,45],'twoFinger':[24,30,50]},
        publishedTopSloperAnglesDegrees=[32.5,22.5],
        limitations=['The physical inventory is 19 front recesses plus four upper contacts: 23, not the unsupported earlier 24-contact count.',
          'The manufacturer publishes depth families but no inspected source binds every family member to a numbered pocket. Positions are photo-supported; per-position depth assignments are explicitly authored estimates.',
          'The two upper sloper angles are published as 32.5 and 22.5 degrees, but their handed assignment is not independently established. Left/right assignments here are display choices, not manufacturer claims.',
          'The central 35-degree bar has an authored sloping cavity floor; its nominal 35 mm grip length is not certified as a 35 mm curved contact arc.',
          'Tier relief, rear plane, local radii and hole centres are estimates. The 55 cm depth in a retailer listing is rejected as inconsistent with the manufacturer 55 mm value.'])
    for side,sg in [('left',-1),('right',1)]:
        # Explicit contact topology follows the inspected front photograph.
        c['pockets'].append(pocket(f'upper-four-finger-{side}',sg*233,116,82,25,37,55,published=False,kind='four-finger pocket'))
        c['pockets'].append(pocket(f'upper-three-finger-{side}',sg*40,116,61,25,45,55,published=False,kind='three-finger pocket'))
        c['pockets'].append(pocket(f'middle-four-finger-{side}',sg*233,81,84,23,20,55,published=False,kind='four-finger pocket'))
        c['pockets'].append(pocket(f'middle-three-finger-{side}',sg*153,81,61,23,28,55,published=False,kind='three-finger pocket'))
        c['pockets'].append(pocket(f'middle-two-finger-{side}',sg*93,81,43,23,30,55,published=False,kind='two-finger pocket'))
        c['pockets'].append(pocket(f'lower-outer-two-finger-{side}',sg*255,26,42,24,24,55,published=False,kind='two-finger pocket'))
        c['pockets'].append(pocket(f'lower-inner-two-finger-{side}',sg*201,26,42,24,50,55,published=False,kind='two-finger pocket'))
        c['pockets'].append(pocket(f'lower-four-finger-{side}',sg*112,26,81,24,16,36,published=False,kind='four-finger pocket'))
        c['pockets'].append(pocket(f'lower-three-finger-{side}',sg*35,26,60,24,18,36,published=False,kind='three-finger pocket'))
    c['pockets'].append(pocket('central-35deg-sloper-bar',0,81,122,23,35,55,published=False,kind='35 degree sloper bar',floorSlopeZ=math.tan(math.radians(35)),publishedAngleDegrees=35))
    return c

CONFIG_FUNCTIONS=[woodbord,escape,metolius,moon,linebreaker]
def get(slug):
    for f in CONFIG_FUNCTIONS:
        c=f()
        if c['slug']==slug:return c
    raise KeyError(slug)
