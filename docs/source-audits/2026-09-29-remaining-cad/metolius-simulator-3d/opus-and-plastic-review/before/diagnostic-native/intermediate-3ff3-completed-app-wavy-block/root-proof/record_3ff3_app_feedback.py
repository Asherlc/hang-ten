from pathlib import Path
import hashlib
import json

root = Path.cwd()
review = root / '.context/placid-badger/metolius-simulator-3d-plastic-review'
identity = {
    'sourceSHA256': '3ff3a89170bf35daa24a19f2f3e2226390d47359dcbcf9bdadcd1eed0330af6d',
    'modelSHA256': '78fd9fa2c09bea9905bcf47ccd71b77389c5e2999a5dace5994a2867f622ff6a',
    'descriptorSHA256': 'e93ca8f6f13d2e30b3de7eadad91b0ba8bd05f6f282e21ce9b250304500115df',
    'builtBinarySHA256': 'afb082de5c7b86d611136c0805afa82bc2e28f8e7051d243e0b0a15086829d29',
}
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
images = {}
phase_checks = {}
for phase, expected in [('after', 8), ('finish-checks', 4), ('grasp-checks', 4)]:
    folder = review / 'ios' / (phase + '-captures')
    validation = json.loads((folder / 'validation.json').read_text())
    for key, value in identity.items():
        assert validation[key] == value, (phase, key)
    assert validation['surfaceFinish'] == 'plastic'
    frames = list(folder.glob('*.png'))
    assert len(frames) == expected
    for path in frames:
        images[str(path.relative_to(root))] = sha(path)
    phase_checks[phase] = {
        'validationSHA256': sha(folder / 'validation.json'),
        'frameCount': len(frames),
        'actualDragCount': sum(command[3:4] == ['swipe'] for command in validation['commands']),
        'verifiedOrbitFrames': sum(bool(check.get('actualDragOrbit')) for check in validation['checks']),
    }
data = {
    'owner': 'placid-badger', 'boardID': 'metolius.simulator-3d',
    'status': 'requires-geometry-correction', **identity,
    'latestHumanFeedback': 'why does it look kind of... wavy?',
    'humanGeometryAcceptance': 'pending review #8',
    'wholeImagesReviewedByRoot': images,
    'phases': phase_checks,
    'blockers': [{
        'cause': 'Inherited ContinuousFrontRelief repeatedly resets its front-depth slope to zero at each row, creating unsupported full-width curvature bands.',
        'evidence': '.context/placid-badger/metolius-simulator-3d-wavy-diagnosis/diagnosis.json',
        'evidenceSHA256': sha(root / '.context/placid-badger/metolius-simulator-3d-wavy-diagnosis/diagnosis.json'),
        'requestedCorrection': 'Fair the native lower front taper while preserving current top grips, localized pocket rims, all 30 contacts and 27 published depths.',
    }],
    'passingAppearanceObservations': [
        'Whole board surfaces use the mint runtime plastic finish.',
        'Switching from the outer jug to the flat sloper restores mint on the formerly selected jug in the same instance.',
        'Flat and round sloper bands reach the front, and the flat sloper has a rolled front edge.',
        'The center jug has a smooth transverse crest and rear fall, without the former front-to-back ridge.',
        'The jug cap highlight excludes pocket #15; the dome face has no former shelf or horizontal groove.',
        'The back is visually uniform in the rear-leaning frame.',
    ],
    'nonblockingLimits': [
        'Small teeth remain at some selected cap/sloper contact boundaries.',
        'Faint saddle/front shading creases and inherited outer-jug faceting remain.',
        'Whole-frame board views are small; subpixel flicker is not excluded.',
        'Thickness, profile, rolls and rear jug slope remain display estimates; mint is the app palette.',
    ],
    'opusResponse': 'opus-waviness-review.md',
    'opusResponseSHA256': sha(review / 'opus-waviness-review.md'),
    'technicalProofDisposition': 'Native/export identity and geometry validations remain valid for 3ff3. Their pass does not imply manufacturer shape fidelity or human acceptance.',
    'previousFeedbackRecordSHA256': sha(review / '3ff3-app-visual-feedback.json'),
    'bookkeepingCorrection': 'Count actual recorded swipe commands for each phase; actualDragChecks only enumerates the six grasp-phase swipes. Source, image observations and verdict are unchanged.',
}
assert [phase_checks[p]['actualDragCount'] for p in ['after', 'finish-checks', 'grasp-checks']] == [3, 1, 6]
path = review / '3ff3-app-visual-feedback-v2.json'
assert not path.exists(), 'keep the first feedback record immutable'
path.write_text(json.dumps(data, indent=2) + '\n')
print(json.dumps({'status': data['status'], 'wholeFrames': len(images), 'fileSHA256': sha(path)}))
