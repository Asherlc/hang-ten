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
    if slug == 'trango-rock-prodigy-forge':
        # The concurrent native migration authors the complete physical pair.
        # Keep conservation checks for that editable source; a template-only
        # assertion would require discarding it for Main's prior mesh import.
        assert source.is_file()
        assert descriptor['schemaVersion'] == 1
        assert 'instances' not in media
        assert descriptor['modelSHA256'] == hashlib.sha256((package / media['assetPath']).read_bytes()).hexdigest()
        contacts = {c['id']: c for c in board['contacts']}
        assert len(contacts) == 2 * count
        assert set(descriptor['contacts']) == set(contacts)
        equipment_ids = {item['id'] for item in board['equipmentObjects']}
        assert equipment_ids == {'primary'}
        left = {cid for cid in contacts if cid.endswith('-left')}
        right = {cid for cid in contacts if cid.endswith('-right')}
        assert len(left) == len(right) == count
        assert {cid.removesuffix('-left') for cid in left} == {cid.removesuffix('-right') for cid in right}
        assert left | right == set(contacts)
        assert all(c['equipmentObjectID'] in equipment_ids for c in contacts.values())
        nodes_by_contact = {cid: {n['nodeID'] for n in descriptor['nodes']
            if n.get('role') == 'contact' and n.get('contactID') == cid} for cid in contacts}
        assert all(nodes_by_contact.values())
        assert all(set(descriptor['contacts'][cid]['nodeIDs']) == nodes_by_contact[cid] for cid in contacts)
        assert any(n.get('role') == 'body' for n in descriptor['nodes'])
        assert descriptor['modelBounds']['min'][0] < 0 < descriptor['modelBounds']['max'][0]
        return
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
