"""Rock Prodigy pairs preserve their authored native or reusable mirror contracts."""
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

import pytest
from hangboard_packages.cad_source import load_board, read_document_xml

ROOT = Path(__file__).resolve().parents[3] / 'Hangboards'

@pytest.mark.parametrize('slug,count', [
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


FORGE_CONTACT_STEMS = {
    'sloper-30', 'sloper-40', 'large-flat-edge', 'slopey-crimper',
    'variable-edge-rail', 'closed-crimp', 'mr-deep', 'mr-shallow',
    'im-deep', 'im-shallow',
}


def test_native_forge_full_pair_maps_every_physical_contact_and_mirrored_frame():
    package = ROOT / 'trango-rock-prodigy-forge'
    board = load_board(package / 'trango-rock-prodigy-forge.FCStd')
    assert not (package / 'board.json').exists()
    assert board['equipmentObjects'] == [{'id': 'primary'}]
    assert len(board['presentations']) == 1
    media = board['presentations'][0]['media']
    assert 'instances' not in media
    descriptor = json.loads((package / media['descriptorPath']).read_text())
    assert descriptor['schemaVersion'] == 1
    assert 'contactSlots' not in descriptor
    assert descriptor['modelSHA256'] == hashlib.sha256((package / media['assetPath']).read_bytes()).hexdigest()

    expected = {f'{stem}-{side}' for stem in FORGE_CONTACT_STEMS for side in ('left', 'right')}
    contacts = {contact['id']: contact for contact in board['contacts']}
    assert len(board['contacts']) == len(contacts) == 20
    assert set(contacts) == set(descriptor['contacts']) == expected
    assert all(contact['equipmentObjectID'] == 'primary' for contact in contacts.values())
    nodes = {node['nodeID']: node for node in descriptor['nodes']}
    assert len(nodes) == len(descriptor['nodes']) == 21
    assert [node for node in nodes.values() if node['role'] == 'body'] == [
        {'nodeID': 'body_board_001', 'role': 'body'},
    ]
    contact_nodes = [node for node in nodes.values() if node['role'] == 'contact']
    assert len(contact_nodes) == 20
    assert {node['contactID'] for node in contact_nodes} == expected
    for contact_id, contact in descriptor['contacts'].items():
        assert len(contact['nodeIDs']) == 1
        assert nodes[contact['nodeIDs'][0]] == {
            'nodeID': contact['nodeIDs'][0], 'role': 'contact', 'contactID': contact_id,
        }

    bounds = descriptor['modelBounds']
    assert bounds['min'][0] < 0 < bounds['max'][0]
    assert bounds['min'][0] == pytest.approx(-bounds['max'][0], abs=1e-9)
    for stem in FORGE_CONTACT_STEMS:
        left_id, right_id = f'{stem}-left', f'{stem}-right'
        assert {key: value for key, value in contacts[left_id].items() if key not in ('id', 'name')} == {
            key: value for key, value in contacts[right_id].items() if key not in ('id', 'name')
        }
        left, right = descriptor['contacts'][left_id], descriptor['contacts'][right_id]
        left_bounds, right_bounds = left['facePlaneAABB'], right['facePlaneAABB']
        assert left_bounds['max'][0] < 0.5 < right_bounds['min'][0]
        assert left_bounds['min'] == pytest.approx(
            [1 - right_bounds['max'][0], right_bounds['min'][1]], abs=2e-9)
        assert left_bounds['max'] == pytest.approx(
            [1 - right_bounds['min'][0], right_bounds['max'][1]], abs=2e-9)
        assert left['center'] == pytest.approx([1 - right['center'][0], right['center'][1]], abs=2e-9)


def test_native_forge_mirrors_one_authored_right_wing_and_all_contact_surfaces():
    source = ROOT / 'trango-rock-prodigy-forge' / 'trango-rock-prodigy-forge.FCStd'
    document = ET.fromstring(read_document_xml(source))
    types = {obj.get('name'): obj.get('type') for obj in document.findall('./Objects/Object')}
    objects = {obj.get('name'): obj for obj in document.findall('./ObjectData/Object')}

    def property_element(name, field):
        prop = objects[name].find(f"./Properties/Property[@name='{field}']")
        assert prop is not None, (name, field)
        return next(iter(prop))

    def string(name, field):
        return property_element(name, field).get('value')

    def assert_mirror(name, authored_source):
        assert types[name] == 'Part::Mirroring'
        assert string(name, 'Source') == authored_source
        for field, expected in [('Base', (0, 0, 0)), ('Normal', (1, 0, 0))]:
            vector = property_element(name, field)
            assert tuple(float(vector.get(f'value{axis}')) for axis in 'XYZ') == expected

    assert types['RightFrontSilhouette'] == 'Sketcher::SketchObject'
    assert types['RightWingWithIMRSeam'] == 'Part::MultiFuse'
    assert_mirror('LeftPocketedWing', 'RightWingWithIMRSeam')
    assert types['BodySolid'] == 'Part::MultiFuse'
    assert string('BodySolid', 'NodeID') == 'body_board_001'
    assert string('BodySolid', 'NodeRole') == 'body'
    assert {link.get('value') for link in property_element('BodySolid', 'Shapes')} == {
        'RightWingWithIMRSeam', 'LeftPocketedWing',
    }
    assert not any('left' in name.lower() for name, kind in types.items() if kind == 'Sketcher::SketchObject')

    native_contacts = {}
    for stem in FORGE_CONTACT_STEMS:
        object_stem = stem.replace('-', '_')
        right, left = f'Contact_{object_stem}_right', f'Contact_{object_stem}_left'
        assert types[right] in {'PartDesign::SubShapeBinder', 'Part::Common'}
        assert_mirror(left, right)
        for name, side in [(left, 'left'), (right, 'right')]:
            assert string(name, 'NodeRole') == 'contact'
            contact_id = f'{stem}-{side}'
            assert string(name, 'ContactID') == contact_id
            native_contacts[contact_id] = string(name, 'NodeID')
    descriptor = json.loads((source.parent / 'assets/primary.model.json').read_text())
    assert native_contacts == {
        contact_id: contact['nodeIDs'][0] for contact_id, contact in descriptor['contacts'].items()
    }
