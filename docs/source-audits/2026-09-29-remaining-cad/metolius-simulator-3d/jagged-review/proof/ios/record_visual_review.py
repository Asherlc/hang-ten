from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

root = Path.cwd()
scratch = root / '.context/placid-badger/metolius-simulator-3d-jagged'
ios = scratch / 'ios'
capture = json.loads((ios / 'after-captures/validation.json').read_text())
assert capture['sourceSHA256'] == '8fa07c203943d849101ba80926fb6c1d69c2ace7dff982a68f6e8a6476f618f7'
paths = [ios / 'after-captures' / row['image'] for row in capture['checks']]
assert len(paths) == 8
paths += [ios / 'before-captures/jug-left-orbit.png']
paths += [scratch / 'native-author/review' / ('comparison-' + view + '.png')
          for view in ('front', 'side', 'top')]
paths += [root / 'docs/source-audits/2026-09-29-remaining-cad/metolius-simulator-3d/sources/product-01.jpg']
report = {
    'reviewedAtUTC': datetime.now(timezone.utc).isoformat(),
    'owner': root.name,
    'reviewer': 'root agent, direct inspection of complete images',
    'sourceSHA256': capture['sourceSHA256'],
    'modelSHA256': capture['modelSHA256'],
    'descriptorSHA256': capture['descriptorSHA256'],
    'status': 'ready for revised human review #8',
    'observations': [
        'The former angular lower/outer corners read as rounded in the actual app.',
        'The former abrupt triangular shoulder height steps are replaced by continuous transitions.',
        'CPU comparison shading has polygon bands; those bands do not appear as visible gaps or slivers in the actual app frames.',
        'The outer jug, flat sloper, combined round shoulder, shallow edge and deep pocket highlights appear on their intended representative surfaces.',
        'Selections remain attached through all three actual drag orbits.',
    ],
    'limits': [
        'Image review uses full frames without cropping, registration, tracing or pixel measurements.',
        'Eight frames cover five representative IDs and three real drags, not every contact or subpixel flicker.',
        'Estimated rounding, loft transitions and 94.1183246265 mm thickness are not manufacturing dimensions.',
        'Roof transitions retain small direction changes up to 6.77 degrees; global G1/C1 continuity is not claimed.',
        'Human acceptance remains pending; the first seven approvals are unchanged.',
    ],
    'imageSHA256': {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
                    for p in paths},
}
(ios / 'after-visual-review.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({'status': report['status'], 'fullAfterAppFramesViewed': 8,
                  'comparisonViewsViewed': ['front', 'side', 'top']}, indent=2))
