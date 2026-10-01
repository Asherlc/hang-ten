"""Rock Ring threading must remain one continuous loop per displayed instance."""
import copy
import json
from pathlib import Path

import pytest

from hangboard_packages.board_catalog import _load_model_suspension, load_board_package

PACKAGE = Path(__file__).resolve().parents[3] / 'Hangboards' / 'metolius-rock-rings-3d'


def setup():
    return json.loads((PACKAGE / 'suspension.json').read_text())['instanceSuspensions']['left-ring']


def test_two_separate_instances_share_one_ring_asset_and_each_have_one_loop():
    board = load_board_package(PACKAGE).board
    media = board.presentations[0].media
    left, right = media.instances
    assert left.base_transform.translation[0] < right.base_transform.translation[0]
    assert len(left.suspension.branches) == len(right.suspension.branches) == 1
    for instance in media.instances:
        cord = instance.suspension
        assert len(cord.passages.left) == 2
        assert not cord.passages.right
        branch = cord.branches[0]
        route = cord.internal_loop_channel_points_by_branch_id[branch.id]
        assert route[0] == cord.passages.left[0].point_in_model
        assert route[-1] == cord.passages.left[-1].point_in_model
        assert min(point[2] for point in route) < 0  # Return travels behind the upper pocket.
        assert max(abs(point[0]) for point in route) > .065  # Both side recesses.


@pytest.mark.parametrize('mutation', ['missing_channel', 'wrong_length', 'wrong_mouth', 'missing_pose_cache', 'duplicate_point', 'extra_branch'])
def test_malformed_connected_loop_is_rejected(mutation):
    data = copy.deepcopy(setup())
    loop = data['internalLoop']
    branch_id = data['branches'][0]['id']
    if mutation == 'missing_channel':
        del loop['channelPointsByBranchID']
    elif mutation == 'wrong_length':
        loop['channelLengthByBranchID'][branch_id] += .01
    elif mutation == 'wrong_mouth':
        loop['channelPointsByBranchID'][branch_id][0][0] += .001
    elif mutation == 'missing_pose_cache':
        del data['canonicalPoses']['primary']['cordContactPoints']
    elif mutation == 'duplicate_point':
        loop['channelPointsByBranchID'][branch_id].insert(1, loop['channelPointsByBranchID'][branch_id][0])
    else:
        data['branches'].append(copy.deepcopy(data['branches'][0]))
    with pytest.raises(ValueError):
        _load_model_suspension(data, 'rock-ring-test')
