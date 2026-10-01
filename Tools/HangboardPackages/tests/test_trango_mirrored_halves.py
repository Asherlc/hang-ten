"""Split Rock Prodigy models retain two physical contact inventories on one mesh."""
import hashlib
import json
from pathlib import Path

import pytest
from hangboard_packages.cad_source import load_board

ROOT = Path(__file__).resolve().parents[3] / 'Hangboards'

@pytest.mark.parametrize('slug,count', [
    ('trango-rock-prodigy-forge', 10),
    ('trango-rock-prodigy-natural', 7),
    ('trango-rock-prodigy-training-center', 12),
])
def test_single_half_maps_every_physical_contact_once(slug, count):
    package = ROOT / slug
    source = package / f'{slug}.FCStd'
    board = load_board(source) if source.exists() else json.loads((package / 'board.json').read_text())
    media = board['presentations'][0]['media']
    descriptor = json.loads((package / media['descriptorPath']).read_text())
    assert descriptor['schemaVersion'] == 2
    assert len(descriptor['contactSlots']) == count
    assert descriptor['modelSHA256'] == hashlib.sha256((package / media['assetPath']).read_bytes()).hexdigest()
    assert all('right' not in n['nodeID'] for n in descriptor['nodes'])
    instances = media['instances']
    assert len(instances) == 2
    assert [i['baseTransform'].get('reflection') for i in instances] == [None, 'x']
    contacts = {c['id']: c for c in board['contacts']}
    mapped = []
    for side, instance in zip(('left', 'right'), instances):
        assert set(instance['contactIDsBySlotID']) == set(descriptor['contactSlots'])
        for slot, contact_id in instance['contactIDsBySlotID'].items():
            assert contact_id == f'{slot}-{side}'
            assert contacts[contact_id]['equipmentObjectID'] == instance['equipmentObjectID']
            mapped.append(contact_id)
    assert len(mapped) == len(set(mapped)) == 2 * count
    assert set(mapped) == set(contacts)
    bounds = descriptor['modelBounds']
    center_x = (bounds['min'][0] + bounds['max'][0]) / 2
    assert bounds['max'][0] < 0  # Only the left half is stored.
    assert instances[0]['baseTransform']['translation'] == [0, 0, 0]
    assert abs(instances[1]['baseTransform']['translation'][0] + 2 * center_x) < 1e-8
