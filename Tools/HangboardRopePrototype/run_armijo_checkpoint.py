#!/usr/bin/env python3
"""One fixed stricter-line-search screen, with original physical gates."""
import argparse,hashlib,json,os,signal,sys
from pathlib import Path
sys.dont_write_bytecode=True
sys.path.insert(0,str(Path(__file__).resolve().parent))
from run_native_contact_screen import OwnedCommands,REPO
from run_live_speed_screen import NAMES
from armijo.snapshot import solver_source
parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--label',required=True)
parser.add_argument('--full-merit',action='store_true')
parser.add_argument('--fixtures-only',action='store_true')
parser.add_argument('--trajectory',action='store_true')
parser.add_argument('--step-rate',type=int,choices=[240,120])
parser.add_argument('--composed-step',action='store_true')
parser.add_argument('--mass-only',action='store_true')
parser.add_argument('--arrival-stop',action='store_true')
parser.add_argument('--arrival-checkpoint',type=int,choices=[109,140],default=109)
parser.add_argument('--lagged-reaction',action='store_true')
parser.add_argument('--planar-regions',action='store_true')
parser.add_argument('--region-queries',action='store_true')
parser.add_argument('--clipped-regions',action='store_true')
parser.add_argument('--region-profile',action='store_true')
parser.add_argument('--planar-rows',action='store_true')
parser.add_argument('--scaled-merit',action='store_true')
parser.add_argument('--spectral-step',action='store_true')
parser.add_argument('--geometry-hints',action='store_true')
parser.add_argument('--clearance-bounds',action='store_true')
parser.add_argument('--bounds-profile',action='store_true')
parser.add_argument('--axis-bounds',action='store_true')
parser.add_argument('--free-balls',action='store_true')
parser.add_argument('--plane-reuse',action='store_true')
parser.add_argument('--neighborhoods',action='store_true')
parser.add_argument('--geometry-profile',action='store_true')
parser.add_argument('--spectral-trajectory',action='store_true')
parser.add_argument('--spectral-checkpoint',type=int,choices=[109,140],default=109)
parser.add_argument('--preflight',action='store_true');args=parser.parse_args()
if args.arrival_stop and (args.full_merit or args.trajectory or args.step_rate==120 or args.composed_step or args.mass_only or args.planar_regions or args.spectral_step or args.clearance_bounds or args.scaled_merit or args.geometry_hints or args.lagged_reaction):parser.error('--arrival-stop is isolated')
if args.planar_regions and (args.clearance_bounds or args.full_merit or args.trajectory or args.step_rate or args.spectral_step or args.scaled_merit or args.geometry_hints):parser.error('--planar-regions is isolated')
if args.clipped_regions and not args.planar_regions:parser.error('--clipped-regions requires --planar-regions')
if args.region_profile and (not args.region_queries or not args.clipped_regions):parser.error('--region-profile requires clipped region queries')
if args.planar_rows and (not args.planar_regions or args.region_queries or args.clipped_regions or args.region_profile):parser.error('--planar-rows requires isolated --planar-regions')
if args.region_queries and not args.planar_regions:parser.error('--region-queries requires --planar-regions')
if args.mass_only and (args.step_rate!=240 or not args.preflight or args.composed_step or args.clearance_bounds or args.spectral_step or args.scaled_merit):parser.error('--mass-only requires isolated --step-rate 240 --preflight')
if args.lagged_reaction and (args.step_rate or args.mass_only or args.composed_step or args.planar_regions or args.clearance_bounds or args.full_merit or args.trajectory or args.spectral_step or args.scaled_merit or args.geometry_hints):parser.error('--lagged-reaction is isolated')
if args.bounds_profile and not args.clearance_bounds:parser.error('--bounds-profile requires --clearance-bounds')
if args.axis_bounds and not args.clearance_bounds:parser.error('--axis-bounds requires --clearance-bounds')
if args.free_balls and (not args.clearance_bounds or args.axis_bounds or args.bounds_profile):parser.error('--free-balls requires isolated --clearance-bounds')
if args.neighborhoods and (not args.free_balls or args.plane_reuse):parser.error('--neighborhoods requires free-balls and excludes plane-reuse')
if args.plane_reuse and not args.free_balls:parser.error('--plane-reuse requires --free-balls')
if args.clearance_bounds and (args.geometry_hints or args.geometry_profile or args.spectral_step or args.scaled_merit or args.full_merit or args.trajectory or args.step_rate or args.composed_step):parser.error('--clearance-bounds is an isolated checkpoint')
if args.geometry_profile and not args.geometry_hints:parser.error('--geometry-profile requires --geometry-hints')
if args.geometry_hints and (args.spectral_step or args.scaled_merit or args.full_merit or args.trajectory or args.step_rate or args.composed_step):parser.error('--geometry-hints is an isolated checkpoint')
if args.spectral_trajectory and not args.spectral_step:parser.error('--spectral-trajectory requires --spectral-step')
if args.spectral_step and (args.scaled_merit or args.full_merit or args.trajectory or args.step_rate or args.composed_step):parser.error('--spectral-step is an isolated original-rate checkpoint')
if args.scaled_merit and (args.full_merit or args.trajectory or args.step_rate or args.composed_step):parser.error('--scaled-merit is an isolated original-rate checkpoint')
if args.trajectory and args.fixtures_only:parser.error('--trajectory and --fixtures-only conflict')
if args.step_rate and (args.full_merit or args.trajectory or args.fixtures_only):parser.error('--step-rate uses the original solver only')
if args.composed_step and not args.step_rate:parser.error('--composed-step requires --step-rate')
if args.preflight and args.step_rate!=240:parser.error('--preflight requires --step-rate 240')
if args.trajectory and not args.full_merit:parser.error('--trajectory requires --full-merit')
if args.full_merit:
    from armijo.full_snapshot import solver_source,collider_source
assert args.label and all(c in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.label)
assert Path(os.environ.get('PASEO_WORKTREE_PATH',REPO)).resolve()==REPO and REPO.name=='strong-owl-live-physics'
tool=Path(__file__).resolve().parent
root=REPO/'.context'/f'{REPO.name}-armijo-{args.label}';root.mkdir();stage=root/'native';stage.mkdir();sources=stage/'sources';sources.mkdir()
for name in NAMES:
    text=(REPO/'HangTen/Models'/name).read_text()
    if args.full_merit and name=='RopeTriangleCollider.swift':text=collider_source(text)
    if args.planar_regions and name=='RopeTriangleCollider.swift':
        from planar_regions.snapshot import collider_source as region_collider
        text=region_collider(text)
        if args.region_profile:
            from planar_regions.profile import collider_source as profile_collider
            text=profile_collider(text)
        if args.planar_rows:
            from planar_regions.rows_snapshot import collider_source as rows_collider
            text=rows_collider(text)
    if args.geometry_hints and name=='RopeTriangleCollider.swift':
        from geometry_hints.snapshot import collider_source as hint_collider
        text=hint_collider(text)
    if args.clearance_bounds and name in ['RopeTriangleCollider.swift','RopeSimulationMetrics.swift']:
        from clearance_bounds.snapshot import collider_source as bound_collider,metrics_source as bound_metrics
        text=bound_collider(text) if name=='RopeTriangleCollider.swift' else bound_metrics(text)
        if args.axis_bounds and name=='RopeTriangleCollider.swift':
            from clearance_bounds.axis_snapshot import collider_source as axis_collider
            text=axis_collider(text)
        if args.free_balls and name=='RopeTriangleCollider.swift':
            from free_balls.snapshot import collider_source as free_collider
            text=free_collider(text)
        if args.neighborhoods and name=='RopeTriangleCollider.swift':
            from neighborhoods.snapshot import collider_source as neighborhood_collider
            text=neighborhood_collider(text)
        if args.plane_reuse and name=='RopeTriangleCollider.swift':
            from plane_reuse.snapshot import collider_source as plane_collider
            text=plane_collider(text)
    if name=='RopeDynamicsSolver.swift':
        text=solver_source(text).replace('private extension SIMD4','extension SIMD4')
        text+='\n'+(tool/'stock_chain/CheckpointAdapter.swift').read_text()+'\n'+(tool/'contact_bundle/CheckpointExtras.swift').read_text()
        if args.arrival_stop:
            from arrival_stop.snapshot import solver_source as arrival_solver
            text=arrival_solver(text)
        if args.lagged_reaction:
            from lagged_reaction.snapshot import solver_source as lagged_solver
            text=lagged_solver(text)
        if args.planar_rows:
            from planar_regions.rows_snapshot import solver_source as rows_solver
            text=rows_solver(text)
        if args.clearance_bounds:
            from clearance_bounds.snapshot import solver_source as bound_solver
            text=bound_solver(text)
            if args.axis_bounds:
                from clearance_bounds.axis_snapshot import solver_source as axis_solver
                text=axis_solver(text)
            if args.free_balls:
                from free_balls.snapshot import solver_source as free_solver
                text=free_solver(text)
            if args.neighborhoods:
                from neighborhoods.snapshot import solver_source as neighborhood_solver
                text=neighborhood_solver(text)
            if args.plane_reuse:
                from plane_reuse.snapshot import solver_source as plane_solver
                text=plane_solver(text)
            if args.bounds_profile:
                from clearance_bounds.snapshot import profile_solver
                text=profile_solver(text)
        if args.geometry_hints:
            from geometry_hints.snapshot import solver_source as hint_solver
            text=hint_solver(text)
            if args.geometry_profile:
                from geometry_hints.snapshot import profile_solver
                text=profile_solver(text)
        if args.spectral_step:
            from spectral_step.snapshot import solver_source as spectral_solver
            text=spectral_solver(text)
        if args.scaled_merit:
            from scaled_merit.snapshot import solver_source as scaled_solver
            text=scaled_solver(text)
        if args.mass_only:
            from mass_only.snapshot import solver_source as mass_solver
            text=mass_solver(text)
        if args.composed_step:
            from composed_step.snapshot import solver_source as composed_solver
            text=composed_solver(text)
    if name=='RopeBandedSystem.swift':text=text.replace('        try RopeBandedFactorization(size:size','        return try RopeBandedFactorization(size:size')
    (sources/name).write_text(text)
for name in ['Math.swift','Trace.swift','main.swift']:
    text=(tool/'armijo'/('StepRateMain.swift' if (args.step_rate or args.spectral_trajectory) and name=='main.swift' else 'TrajectoryMain.swift' if args.trajectory and name=='main.swift' else name)).read_text()
    if name=='main.swift' and not args.full_merit:
        text=text.replace('    ArmijoTrace.collectOracleBranches=x.verifyArmijoDerivative\n','')
    if name=='main.swift' and args.arrival_stop:
        from arrival_stop.snapshot import driver_source as arrival_driver,trajectory_source as arrival_trajectory
        text=arrival_trajectory(text) if args.step_rate else arrival_driver(text,args.arrival_checkpoint)
    if name=='main.swift' and args.lagged_reaction:
        from lagged_reaction.snapshot import driver_source as lagged_driver
        text=lagged_driver(text)
    if name=='main.swift' and args.planar_regions:
        from planar_regions.snapshot import driver_source as region_driver
        text=region_driver(text,args.clipped_regions)
        if args.planar_rows:
            from planar_regions.rows_snapshot import driver_source as rows_driver
            text=rows_driver(text)
        if args.region_queries:
            from planar_regions.snapshot import query_driver
            text=query_driver(text,args.clipped_regions)
            if args.region_profile:
                from planar_regions.profile import driver_source as profile_driver
                text=profile_driver(text)
    if name=='main.swift' and args.geometry_hints:
        from geometry_hints.snapshot import driver_source as hint_driver
        text=hint_driver(text)
        if args.geometry_profile:
            from geometry_hints.snapshot import profile_driver
            text=profile_driver(text)
    if name=='main.swift' and args.clearance_bounds:
        if args.free_balls:
            from free_balls.snapshot import driver_source as bound_driver
        else:
            from clearance_bounds.snapshot import driver_source as bound_driver
        text=bound_driver(text)
        if args.neighborhoods:
            from neighborhoods.snapshot import driver_source as neighborhood_driver
            text=neighborhood_driver(text)
        if args.plane_reuse:
            from plane_reuse.snapshot import driver_source as plane_driver
            text=plane_driver(text)
        if args.axis_bounds:
            from clearance_bounds.axis_snapshot import driver_source as axis_driver
            text=axis_driver(text)
        if args.bounds_profile:
            from clearance_bounds.snapshot import profile_driver
            text=profile_driver(text)
    if name=='main.swift' and args.spectral_step:
        from spectral_step.snapshot import driver_source as spectral_driver, trajectory_source
        text=trajectory_source(text) if args.spectral_trajectory else spectral_driver(text,args.spectral_checkpoint)
    if name=='main.swift' and args.scaled_merit:
        from scaled_merit.snapshot import driver_source as scaled_driver
        text=scaled_driver(text)
    if name=='main.swift' and args.mass_only:
        from mass_only.snapshot import driver_source as mass_driver
        text=mass_driver(text)
    if name=='main.swift' and args.composed_step:
        from composed_step.snapshot import driver_source
        text=driver_source(text)
    if args.full_merit and name=='main.swift' and not args.trajectory:
        text=text.replace('candidate.armijoExperiment=true','candidate.armijoExperiment=true;candidate.verifyArmijoDerivative=true')
        text=text.replace('"step":109]','"step":109,"fullMeritDerivative":true]')
        text=text.replace('    // One-sided abs derivative', '''    guard RopeArmijo.hingeSlope(argument:0,rate:2)==2,RopeArmijo.hingeSlope(argument:0,rate:-2)==0,
          RopeArmijo.hingeSlope(argument:1,rate:-2)==(-2),RopeArmijo.hingeSlope(argument:-1,rate:2)==0 else {
        throw RopePhysicsError.invalid("hinge derivative")
    }
    let h=1e-7,rates=[-0.3,0.2]
    let maxSlope=([1+h*rates[0],1+h*rates[1]].max()!-1)/h
    guard abs(maxSlope-rates.max()!)<1e-8 else {throw RopePhysicsError.invalid("tied-max directional derivative")}
    // One-sided abs derivative''')
        text=text.replace('    try fixtures();result["fixturesPass"]=true','    try ambiguityFixtures();try fixtures();result["fixturesPass"]=true')
    if name=='Trace.swift' and args.planar_rows:
        from armijo.snapshot import once
        text=once(text,'    static var collectDerivatives=false','    static var collectDerivatives=false\n    static var collectPlanarBindings=false')
    (sources/name).write_text(text)
if args.geometry_hints:(sources/'GeometryHintMath.swift').write_bytes((tool/'geometry_hints/Math.swift').read_bytes())
if args.clearance_bounds:(sources/'ClearanceBoundMath.swift').write_bytes((tool/'clearance_bounds/Math.swift').read_bytes())
if args.axis_bounds:(sources/'AxisBoundMath.swift').write_bytes((tool/'clearance_bounds/Axis.swift').read_bytes())
if args.free_balls:(sources/'FreeBallMath.swift').write_bytes((tool/'free_balls/Math.swift').read_bytes())
if args.neighborhoods:(sources/'NeighborhoodMath.swift').write_bytes((tool/'neighborhoods/Math.swift').read_bytes())
if args.plane_reuse:
    from plane_reuse.atlas import generate
    atlas,metadata=generate(REPO/'Hangboards/clavellium-training-block/assets/primary.physics.json')
    (sources/'PlaneAtlas.swift').write_text(atlas)
    (sources/'PlaneCacheMath.swift').write_bytes((tool/'plane_reuse/Math.swift').read_bytes())
    (stage/'atlas.json').write_text(json.dumps(metadata,indent=2)+'\n')
if args.spectral_step:(sources/'SpectralStepMath.swift').write_bytes((tool/'spectral_step/Math.swift').read_bytes())
if args.scaled_merit:(sources/'ScaledMeritMath.swift').write_bytes((tool/'scaled_merit/Math.swift').read_bytes())
if args.full_merit:(sources/'AmbiguityFixtures.swift').write_bytes((tool/'armijo/AmbiguityFixtures.swift').read_bytes())
if args.planar_regions:
    from census_planar_regions import generate_regions
    atlas,metadata=generate_regions(REPO/'Hangboards/clavellium-training-block/assets/primary.physics.json')
    (sources/'PlanarAtlas.swift').write_text(atlas)
    region_math=(tool/'planar_regions/Math.swift').read_text()
    if args.region_profile:
        from planar_regions.profile import math_source,profile_source
        region_math=math_source(region_math)
        (sources/'PlanarProfile.swift').write_text(profile_source())
    (sources/'PlanarMath.swift').write_text(region_math)
    (stage/'region-topology.json').write_text(json.dumps(metadata,indent=2)+'\n')
if args.mass_only:(sources/'MassOnlyMath.swift').write_bytes((tool/'mass_only/Math.swift').read_bytes())
if args.lagged_reaction:(sources/'LaggedReactionMath.swift').write_bytes((tool/'lagged_reaction/Math.swift').read_bytes())
if args.composed_step:
    for name in ['Math.swift','Fixtures.swift']:(sources/('Composed'+name)).write_bytes((tool/'composed_step'/name).read_bytes())
(sources/'ExactCheckpointJSON.swift').write_bytes((tool/'native_contact/ExactCheckpointJSON.swift').read_bytes())
files=sorted(sources.glob('*.swift'));binary=stage/f'{REPO.name}-armijo'
command=['xcrun','swiftc','-O','-D','DEBUG','-whole-module-optimization','-Xcc','-DACCELERATE_NEW_LAPACK',
    '-module-cache-path',str(stage/'module-cache'),*map(str,files),'-o',str(binary)]
prior=REPO/'.context/strong-owl-live-physics-current-diagnostic-trajectory/native/result.json'
inputs=[*files,*(REPO/'HangTen/Models'/n for n in NAMES),Path(__file__),*list((tool/'armijo').glob('*.*')),
    tool/'stock_chain/CheckpointAdapter.swift',tool/'contact_bundle/CheckpointExtras.swift',prior,
    REPO/'Hangboards/clavellium-training-block/assets/primary.physics.json']
if args.geometry_hints:inputs += list((tool/'geometry_hints').glob('*.*'))
if args.clearance_bounds:inputs += list((tool/'clearance_bounds').glob('*.*'))
if args.free_balls:inputs += list((tool/'free_balls').glob('*.*'))
if args.neighborhoods:inputs += list((tool/'neighborhoods').glob('*.*'))
if args.plane_reuse:inputs += [*list((tool/'plane_reuse').glob('*.*')),stage/'atlas.json']
if args.spectral_step:inputs += list((tool/'spectral_step').glob('*.*'))
if args.scaled_merit:inputs += list((tool/'scaled_merit').glob('*.*'))
if args.region_queries or args.planar_rows:inputs += [REPO/'.context/strong-owl-live-physics-coplanar-query-5a12d1ee2-chronological-corpus/native/result.json']
if args.planar_regions:inputs += [*list((tool/'planar_regions').glob('*.*')),tool/'census_planar_regions.py',stage/'region-topology.json']
if args.arrival_stop:inputs += list((tool/'arrival_stop').glob('*.*'))
if args.mass_only:inputs += list((tool/'mass_only').glob('*.*'))
if args.lagged_reaction:inputs += list((tool/'lagged_reaction').glob('*.*'))
if args.composed_step:inputs += list((tool/'composed_step').glob('*.*'))
(stage/'provenance.json').write_text(json.dumps({'owner':REPO.name,'command':command,
    'hashes':{str(p.relative_to(REPO)):hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}},indent=2))
owner=OwnedCommands(REPO.name,stage)
for sig in [signal.SIGINT,signal.SIGTERM]:signal.signal(sig,owner.interrupted)
env=dict(os.environ);env['HANGTEN_REVIEW_PHYSICAL_CONVERGENCE']='1'
try:
    status=owner.run('compile',['perl','-e','alarm 150;exec @ARGV',*command],stage/'compile.log',env)
    if not status:status=owner.run('run',['perl','-e','alarm 300;exec @ARGV' if not args.trajectory else 'alarm 600;exec @ARGV',str(binary),str(stage),str(prior),*(['--fixtures-only'] if args.fixtures_only else []),*(['--candidate-hz',str(args.step_rate or 240)] if args.step_rate or args.spectral_trajectory else []),*(['--preflight'] if args.preflight else [])],stage/'run.log',env)
    print((stage/('run.log' if (stage/'run.log').exists() else 'compile.log')).read_text())
    if args.plane_reuse and (stage/'plane-unions.json').exists():
        from plane_reuse.proof import validate
        validate(stage/'plane-unions.json',stage/'plane-union-proof.json')
finally:owner.cleanup()
raise SystemExit(status)
