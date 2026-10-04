"""Retain the scoped granite-seat correction; prior review packets remain history."""
from pathlib import Path
import hashlib
import json
import shutil

ROOT = Path.cwd()
BASE = ROOT / '.context/placid-badger/nature-stone-review9/granite-seat-correction'
AUDIT = ROOT / 'docs/source-audits/2026-09-29-remaining-cad/nature-stone-hanger'
PACKET = AUDIT / 'granite-seat-review'
PACKET.mkdir(exist_ok=True)

def retain(src, relative):
    target = PACKET / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(BASE / src, target)

for name in ['native-front-side-top.png', 'native-oblique.png', 'native-center-section.png']:
    retain('native-author/' + name, name)
for view in ['front', 'side', 'top', 'oblique']:
    retain('export-previews/comparison-' + view + '.png', 'export-' + view + '.png')
for name in ['baseline.json', 'canonical-promotion.json', 'compile-primary.json',
             'compile-repro.json', 'independent-native-check.json',
             'independent-export-check.json', 'cord-recertification.json']:
    retain(name, name)
for name in ['green-native-report.json', 'reopened-verification.json',
             'red-regression.json', 'envelope-diagnostic.json', 'native-sections.json']:
    retain('native-author/' + name, 'raw/native/' + name)
for name in ['author_granite_seat.py', 'verify_reopened.py', 'inspect_envelope.py',
             'render_native.py', 'run_owned.py']:
    retain('native-author/' + name, 'raw/native/' + name)
for name in ['check_native.py', 'check_export_mesh.py', 'export_collision.py',
             'recertify_cord.py', 'render_export_comparison.py', 'run_owned_job.py',
             'run_package_checks.py', 'export-overlap-diagnostic.json']:
    retain(name, 'raw/root/' + name)
for path in sorted(BASE.glob('placid-badger-*.json')):
    retain(path.name, 'raw/root/' + path.name)
for path in sorted(BASE.glob('placid-badger-*.log')):
    retain(path.name, 'raw/root/' + path.name)
for path in sorted((BASE / 'native-author').glob('placid-badger-*')):
    if path.is_file():
        retain('native-author/' + path.name, 'raw/native/' + path.name)
for path in sorted((BASE / 'package-checks').iterdir()):
    if path.is_file():
        retain('package-checks/' + path.name, 'raw/package-checks/' + path.name)

source_register = json.loads((AUDIT / 'source-register.json').read_text())
selected = {name: item for item in source_register['sources']
            for name in ['Stone_Hanger_Granite_1.jpg', 'Stone_Hanger_Granite_3.jpg',
                         'Stone_Hanger_Granite_4.jpg', 'StonehangerTechDrawing_Draft1.jpg']
            if item['path'].endswith('/' + name)}
mapping = {
    'feedback': 'The granite is overlapping with wood, look at photos',
    'sourceSet': '../source-register.json',
    'wholePrimaryEvidenceReviewed': list(selected.values()),
    'facts': {
        'graniteInWoodSeat': ['Stone_Hanger_Granite_1.jpg', 'Stone_Hanger_Granite_4.jpg'],
        'straightLowerOpeningSidesAndCleanBottomSeam': [
            'Stone_Hanger_Granite_4.jpg', 'StonehangerTechDrawing_Draft1.jpg'],
        'graniteTwentyMMContactDepth': ['StonehangerTechDrawing_Draft1.jpg'],
        'sideCordFeaturesPreserved': ['Stone_Hanger_Granite_3.jpg'],
    },
    'displayEstimates': ['80 mm insert width', '13 mm insert height',
                         '2.4 mm local rounds', 'precise wood pocket profile',
                         'generic runtime granite/wood texture'],
    'method': 'Direct native authoring and whole-image visual review. No tracing, crops, pixel measurements, registration, masks or image-derived contours.',
    'sourceApproval': source_register['approval'],
}
(PACKET / 'source-mapping.json').write_text(json.dumps(mapping, indent=2) + '\n')
(PACKET / 'independent-visual-review.md').write_text(
    'The exported correction passes visual and numeric review. Front and oblique views '
    'show a seated insert with a clean lower boundary, consistent with the retained '
    'manufacturer front, close-up and technical drawing. Side and top show no unintended '
    'change. The native granite contact remains 20 mm deep; the other seven contacts '
    'are unchanged. No remaining source-supported granite overlap defect is evident. '
    'Reviewer: Astra subagent stone_insert_photo_review; exact source 44a08197 and '
    'model 3bf45b56. App review is recorded separately; this judgment does not accept '
    'the board for the user. Corner radii and texture remain display estimates.\n')
(PACKET / 'review.md').write_text(
    '# Stone Hanger #9: fitted granite insert\n\n'
    'The previous granite bar intersected the wooden body and floated across the '
    'rounded lower opening. The retained manufacturer close-up shows an insert fitted '
    'into the wood, with straight sides and a clean bottom seam. The native source now '
    'cuts a real wood seat, fits the lower opening to the insert, and assigns the granite '
    'contact only to exposed stone.\n\n'
    'Native wood/stone interpenetration is zero (previously 4332.251475 mm³). '
    'The exported wood and granite triangle footprints also have zero overlap. '
    'Two separate native compiles produced byte-identical unbound assets. '
    'The other seven contacts and all factual metadata are unchanged.\n\n'
    'All eight existing solver-generated cord poses (16 branches) were re-certified '
    'against the new native solid. Routes and hanging translations were preserved; '
    'this is a fresh collision/clearance/guide/bore/length/reaction check, not new route '
    'generation. The sidecar changes only the source and model identity hashes.\n\n'
    'The whole native and exported front/side/top comparisons use the exact prior '
    'committed source and assets from 8141b633. Historical review packets remain '
    'unchanged. Runtime wood/granite shaders supply the finishes; the USDZ contains '
    'no materials or textures. Dimensions other than documented grip depths and '
    'the precise pocket/round profile remain display estimates.\n\n'
    'Fresh iOS screenshots, installed parity, focused tests and resource cleanup '
    'are recorded in runtime-validation.json. Human acceptance of #9 remains pending.\n')
print(json.dumps({'packet': str(PACKET.relative_to(ROOT)), 'files': sum(p.is_file() for p in PACKET.rglob('*'))}))
