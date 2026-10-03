# Guarded inverse-secant experiment

User authorizes all isolated experiments. Native-only, original240Hz integration,
merit/unit floor, material/model, all triangle inequalities, trust, convergence,
CCD and physical acceptance. No Armijo/scaled-merit/composed integration combination.

Measured step109 has near-two-cycle full corrections ~4.4um followed eventually by
half-step and tiny full correction. Prior AA was census-closed because full affine
signatures never stayed unchanged, before any acceleration was measured. This
screen permits a new guarded inverse-secant start alpha without stable signatures.

Matching coordinates: free-particle positions and boardHeight once. Supports and
attachments excluded from coordinate vector because boardHeight represents their
coupled motion and QP particle corrections for attachments are zero. Let s be the
actual accepted displacement from previous pre-correction point to current point,
y=current raw QP correction minus previous raw QP correction. Omega=-dot(s,y)/dot(y,y)
minimizes norm(s+omega*y)^2. Only finite0<omega<1 eligible, only if below original
trust alpha. No fitted factor. Activate from correction3 onward. Following any
spectral trial, the next correction uses original trust alpha and ordinary original
backtracking. lastCorrectionFullStep reflects actual accepted alpha; full arrival
probe still required. Only accepted states enter history. Reset every advance/retry.

Evolving curvature and contacts mean no fixed-map convergence theorem. Fresh
original merit, QP and physical/strict checks are required. Failure closes this
formula without step-factor/activation tuning.

Scalar RED/GREEN: overshooting d=-2.5x gives omega.4; undefined, nonfinite and wrong
sign cases produce no candidate. First checkpoint109 from exact108prefix:<=5QPs,
zero caps/retries, full original mesh/material, strict/current<=50um. Seven paired
median ratio<=.8. Pass permits unchanged two-QP140 check, then full540 trajectory,
first20 and sampled strict checks, both tails/false-settle, p95<4ms/total<2.25s,
then mandatory actualsimulator/frame checks and normal-speed video.

Astra validated formula/units, history and attachment coordinate requirements.

109 checkpointPASS4vs11QP, strict0.243um, sevenpairedmedian.38327. Before
140 timing, register overhead ratio<=1.10, candidate<=2QP, exact state/control
decisions (activationfrom3 guaranteesnoarithmeticpathchange at2 corrections).
Full540 usesfirst20/every10 strict references and unchangedreference50um/physical.

Full540accuracyPASS,maxprop27.151um/strict5.936um,caps/retries0,tailsPASS.
StandalonecostFAIL1603vs1657QP,medianpaired1.00126,p9538.073ms under
CPUcontention. Noapp/videoadoption; trajectoryauditretained.
