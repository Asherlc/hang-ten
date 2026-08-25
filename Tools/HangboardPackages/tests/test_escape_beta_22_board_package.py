from __future__ import annotations

from collections import Counter
from pathlib import Path

import pytest
from PIL import Image

from hangboard_packages.board_catalog import load_board_package
from _board_package_helpers import presentation_frame, serialize_geometry


REPO_ROOT = Path(__file__).resolve().parents[3]
PACKAGE_ROOT = REPO_ROOT / "Hangboards" / "escape-beta-22"
EXPECTED_HOLDS = (
    *(
        (f"hold-{family:02d}-{side}", kind)
        for family, kind in (
            (1, "pinch"),
            (2, "pinch"),
            (3, "jug"),
            (4, "jug"),
            (5, "edge"),
            (6, "edge"),
            (7, "edge"),
            (8, "edge"),
        )
        for side in ("left", "right")
    ),
    ("hold-09-center", "sloper"),
    ("hold-11-center", "sloper"),
)
EXPECTED_SIZES = {
    **{
        f"hold-{family:02d}-{side}": size
        for family, size in (
            (1, None),
            (2, None),
            (3, 38),
            (4, 29),
            (5, 12),
            (6, 38),
            (7, 29),
            (8, 12),
        )
        for side in ("left", "right")
    },
    "hold-09-center": None,
    "hold-11-center": None,
}
CENTER_HOLDS = ("hold-09-center", "hold-11-center")
DIRECT_MIRRORED_PAIRS = tuple(
    (f"hold-{family:02d}-left", f"hold-{family:02d}-right")
    for family in range(1, 9)
)
DIRECT_MIRRORED_RIGHT_IDS = frozenset(right_id for _, right_id in DIRECT_MIRRORED_PAIRS)


def _mirror_point(point: tuple[float, float]) -> tuple[float, float]:
    return (1 - point[0], point[1])


def _mirrored_geometry(geometry: tuple[dict[str, object], ...]) -> tuple[dict[str, object], ...]:
    mirrored_pieces: list[dict[str, object]] = []
    for piece in geometry:
        frame = piece["frame"]
        assert isinstance(frame, dict)
        mirrored_frame = dict(frame)
        mirrored_frame["x"] = 1 - frame["x"] - frame["width"]
        commands = []
        for command in piece["commands"]:
            mirrored_command = {"command": command["command"]}
            for field in ("to", "control", "control1", "control2"):
                if field in command:
                    mirrored_command[field] = _mirror_point(command[field])
            commands.append(mirrored_command)
        mirrored_pieces.append({"frame": mirrored_frame, "commands": tuple(commands)})
    return tuple(mirrored_pieces)


EXPECTED_GEOMETRY = {
    "hold-01-left": (
        {
            "frame": {"x": 0.03771872322, "y": 0.220082794416, "width": 0.072931958749, "height": 0.233581365482},
            "commands": (
                {"command": "move", "to": (0.0, 0.83342488576)},
                {"command": "curve", "control1": (0.128583113961, 0.738943314115), "control2": (0.158256138155, 0.225871574789), "to": (0.540796271124, 0.0)},
                {"command": "line", "to": (1.0, 0.354185866254)},
                {"command": "curve", "control1": (0.771017361273, 0.386947523737), "control2": (0.764833405819, 0.592435686222), "to": (0.828137517763, 1.0)},
                {"command": "close"},
            ),
        },
    ),
    "hold-01-right": (
        {
            "frame": {"x": 0.8747731204258151, "y": 0.16229441624365487, "width": 0.09872095808383231, "height": 0.3353989847715734},
            "commands": (
                {"command": "move", "to": (1.0, 0.7752808988764045)},
                {"command": "curve", "control1": (1.0, 0.561797752808989), "control2": (1.0, 0.15730337078651685), "to": (0.7173913043478262, 0.0)},
                {"command": "curve", "control1": (0.47826086956521746, 0.0), "control2": (0.2173913043478261, 0.0), "to": (0.0, 0.12359550561797752)},
                {"command": "curve", "control1": (0.30434782608695654, 0.31460674157303375), "control2": (0.4130434782608697, 0.6853932584269665), "to": (0.32608695652173914, 1.0)},
                {"command": "curve", "control1": (0.6521739130434783, 1.0), "control2": (0.9130434782608695, 1.0), "to": (1.0, 0.7752808988764045)},
                {"command": "close"},
            ),
        },
    ),
    "hold-02-left": (
        {
            "frame": {"x": 0.010590351963, "y": 0.547856738579, "width": 0.111413480373, "height": 0.166104309645},
            "commands": (
                {"command": "move", "to": (0.075170801213, 0.0)},
                {"command": "line", "to": (0.962481136887, 0.130655331894)},
                {"command": "curve", "control1": (0.998154543043, 0.003249105074), "control2": (0.861989971112, 0.642187868677), "to": (1.0, 0.873358872501)},
                {"command": "line", "to": (0.0, 1.0)},
                {"command": "quad", "control": (0.005211822933, 0.483433136581), "to": (0.075170801213, 0.0)},
                {"command": "close"},
            ),
        },
    ),
    "hold-02-right": (
        {
            "frame": {"x": 0.8594846573519628, "y": 0.5152105583756345, "width": 0.12104047904191627, "height": 0.34764020304568516},
            "commands": (
                {"command": "move", "to": (1.0, 0.0681818181818187)},
                {"command": "curve", "control1": (0.7234042553191486, 0.22727272727272751), "control2": (0.4361702127659569, 0.20454545454545447), "to": (0.0, 0.0)},
                {"command": "curve", "control1": (0.14893617021276587, 0.3863636363636363), "control2": (0.23404255319148912, 0.727272727272727), "to": (0.13829787234042606, 1.0)},
                {"command": "curve", "control1": (0.38297872340425493, 1.0), "control2": (0.8191489361702126, 1.0), "to": (0.9574468085106379, 0.8863636363636367)},
                {"command": "curve", "control1": (1.0, 0.6477272727272725), "control2": (1.0, 0.3068181818181819), "to": (1.0, 0.0681818181818187)},
                {"command": "close"},
            ),
        },
    ),
    "hold-03-left": (
        {
            "frame": {"x": 0.090626300732, "y": 0.089476329949, "width": 0.1334937332, "height": 0.169538530457},
            "commands": (
                {"command": "move", "to": (0.0, 0.588895302404)},
                {"command": "curve", "control1": (0.23062615477, 0.068677319222), "control2": (0.712767097781, 0.0), "to": (1.0, 0.0)},
                {"command": "line", "to": (0.944358802572, 0.642421610253)},
                {"command": "line", "to": (0.064845349393, 1.0)},
                {"command": "line", "to": (0.0, 0.588895302404)},
                {"command": "close"},
            ),
        },
    ),
    "hold-03-right": (
        {
            "frame": {"x": 0.7780756353958751, "y": 0.15208040609137063, "width": 0.12050927950311953, "height": 0.10624649746192878},
            "commands": (
                {"command": "move", "to": (0.999998194106936, 0.7260273972602742)},
                {"command": "curve", "control1": (0.8522711881593207, 0.10958904109589007), "control2": (0.3181812435794805, 0.0), "to": (0.0, 0.0)},
                {"command": "curve", "control1": (0.0, 0.17808219178082085), "control2": (0.0, 0.49315068493150627), "to": (0.022727231684248676, 0.6301369863013692)},
                {"command": "curve", "control1": (0.3181812435794805, 0.31506849315068397), "control2": (0.7840894931065744, 0.6849315068493148), "to": (0.999998194106936, 1.0)},
                {"command": "curve", "control1": (1.0, 0.9452054794520545), "control2": (1.0, 0.8219178082191779), "to": (0.999998194106936, 0.7260273972602742)},
                {"command": "close"},
            ),
        },
    ),
    "hold-04-left": (
        {
            "frame": {"x": 0.107815515635, "y": 0.371383563452, "width": 0.113314491018, "height": 0.191289827411},
            "commands": (
                {"command": "move", "to": (0.0, 0.436126635491)},
                {"command": "curve", "control1": (0.187484645798, 0.328184879372), "control2": (0.681087838485, 0.07912104353), "to": (0.935862408262, 0.0)},
                {"command": "line", "to": (1.0, 0.683946829984)},
                {"command": "line", "to": (0.030461915472, 1.0)},
                {"command": "line", "to": (0.0, 0.436126635491)},
                {"command": "close"},
            ),
        },
    ),
    "hold-04-right": (
        {
            "frame": {"x": 0.7677743180306056, "y": 0.4298598984771574, "width": 0.11975281437125755, "height": 0.07984081218274112},
            "commands": (
                {"command": "move", "to": (1.0, 0.3125)},
                {"command": "curve", "control1": (0.7849462365591402, 0.06250000000000001), "control2": (0.23655913978494625, 0.0), "to": (0.0, 0.0)},
                {"command": "curve", "control1": (0.0, 0.20312500000000008), "control2": (0.0, 0.6562500000000001), "to": (0.053763440860215055, 0.90625)},
                {"command": "curve", "control1": (0.2903225806451612, 1.0), "control2": (0.8172043010752689, 1.0), "to": (0.9892473118279571, 0.9999999999999999)},
                {"command": "curve", "control1": (1.0, 0.7812500000000001), "control2": (1.0, 0.5156250000000002), "to": (1.0, 0.3125)},
                {"command": "close"},
            ),
        },
    ),
    "hold-05-left": (
        {
            "frame": {"x": 0.118612112442, "y": 0.645576454315, "width": 0.106572015968, "height": 0.164450550761},
            "commands": (
                {"command": "move", "to": (1.0, 0.783878902576)},
                {"command": "line", "to": (0.0, 1.0)},
                {"command": "line", "to": (0.016013810658, 0.366780769132)},
                {"command": "quad", "control": (0.503695569684, 0.208490580933), "to": (0.986300680731, 0.0)},
                {"command": "close"},
            ),
        },
    ),
    "hold-05-right": (
        {
            "frame": {"x": 0.7579124417831006, "y": 0.7040527918781726, "width": 0.12504656592074959, "height": 0.1055187817258883},
            "commands": (
                {"command": "move", "to": (0.9999998479401506, 0.19999999999999987)},
                {"command": "curve", "control1": (0.7934781402133805, 0.0), "control2": (0.29347821624330506, 0.0), "to": (0.0, 0.0)},
                {"command": "curve", "control1": (0.0, 0.28571428571428564), "control2": (0.0, 0.7142857142857144), "to": (0.11956519921023542, 1.0)},
                {"command": "curve", "control1": (0.40217385188897364, 1.0), "control2": (0.8260868309070812, 1.0), "to": (0.989130284375584, 0.9)},
                {"command": "curve", "control1": (1.0, 0.6714285714285715), "control2": (1.0, 0.3571428571428571), "to": (0.9999998479401506, 0.19999999999999987)},
                {"command": "close"},
            ),
        },
    ),
    "hold-06-left": (
        {
            "frame": {"x": 0.244610948104, "y": 0.034720614424, "width": 0.133948393214, "height": 0.146263268825},
            "commands": (
                {"command": "move", "to": (0.008167761653, 0.264672796729)},
                {"command": "curve", "control1": (0.102594377081, 0.387485395036), "control2": (0.754330864011, -0.031130727307), "to": (1.0, 0.001794134883)},
                {"command": "line", "to": (0.926577491699, 0.710992249703)},
                {"command": "line", "to": (0.0, 1.0)},
                {"command": "close"},
            ),
        },
    ),
    "hold-06-right": (
        {
            "frame": {"x": 0.6164226214238189, "y": 0.08107614213197989, "width": 0.13592015968063872, "height": 0.07926903553299493},
            "commands": (
                {"command": "move", "to": (1.0, 0.31147540983606536)},
                {"command": "curve", "control1": (0.8631578947368423, 0.0), "control2": (0.24210526315789482, 0.0), "to": (0.0, 0.0)},
                {"command": "curve", "control1": (0.0, 0.2786885245901637), "control2": (0.0, 0.6557377049180328), "to": (0.07368421052631581, 0.9180327868852459)},
                {"command": "curve", "control1": (0.3263157894736842, 1.0), "control2": (0.8210526315789475, 1.0), "to": (0.9894736842105264, 0.9999999999999999)},
                {"command": "curve", "control1": (1.0, 0.7704918032786885), "control2": (1.0, 0.5081967213114752), "to": (1.0, 0.31147540983606536)},
                {"command": "close"},
            ),
        },
    ),
    "hold-07-left": (
        {
            "frame": {"x": 0.246414155689, "y": 0.294501675127, "width": 0.114218510978, "height": 0.126550852792},
            "commands": (
                {"command": "move", "to": (0.986589477831, 0.0)},
                {"command": "line", "to": (1.0, 0.699198408152)},
                {"command": "line", "to": (0.0, 1.0)},
                {"command": "line", "to": (0.031501116715, 0.340660330443)},
                {"command": "quad", "control": (0.509045297273, 0.12684050528), "to": (0.986589477831, 0.0)},
                {"command": "close"},
            ),
        },
    ),
    "hold-07-right": (
        {
            "frame": {"x": 0.6256202262142382, "y": 0.3265762436548222, "width": 0.12488303393213572, "height": 0.07451289340101527},
            "commands": (
                {"command": "move", "to": (1.0, 0.22950819672131137)},
                {"command": "curve", "control1": (0.8085106382978725, 0.0), "control2": (0.21276595744680857, 0.0), "to": (0.0, 0.0)},
                {"command": "curve", "control1": (0.0, 0.29508196721311464), "control2": (0.0, 0.704918032786885), "to": (0.07446808510638298, 0.9672131147540985)},
                {"command": "curve", "control1": (0.34042553191489366, 1.0), "control2": (0.8191489361702128, 1.0), "to": (0.9893617021276595, 0.9999999999999999)},
                {"command": "curve", "control1": (1.0, 0.7377049180327867), "control2": (1.0, 0.42622950819672123), "to": (1.0, 0.22950819672131137)},
                {"command": "close"},
            ),
        },
    ),
    "hold-08-left": (
        {
            "frame": {"x": 0.244829820359, "y": 0.545558233503, "width": 0.114658560213, "height": 0.130594175127},
            "commands": (
                {"command": "move", "to": (0.999267598967, 0.0)},
                {"command": "line", "to": (1.0, 0.905177827891)},
                {"command": "line", "to": (0.0, 1.0)},
                {"command": "line", "to": (0.038524435906, 0.117371101878)},
                {"command": "quad", "control": (0.086357611412, 0.343152096417), "to": (0.999267598967, 0.0)},
                {"command": "close"},
            ),
        },
    ),
    "hold-08-right": (
        {
            "frame": {"x": 0.6265604258150366, "y": 0.5957790862944158, "width": 0.12296175648702592, "height": 0.114771355398115},
            "commands": (
                {"command": "move", "to": (1.0, 0.18749969305479597)},
                {"command": "curve", "control1": (0.8085106382978724, 0.0), "control2": (0.2553191489361704, 0.0), "to": (0.0, 0.0)},
                {"command": "curve", "control1": (0.0, 0.2656245651609607), "control2": (0.0, 0.7031238489554842), "to": (0.1063829787234043, 0.9999983629589115)},
                {"command": "curve", "control1": (0.3936170212765958, 1.0), "control2": (0.8085106382978724, 1.0), "to": (0.9787234042553192, 0.9999983629589115)},
                {"command": "curve", "control1": (1.0, 0.7499987722191835), "control2": (1.0, 0.3593744116883588), "to": (1.0, 0.18749969305479597)},
                {"command": "close"},
            ),
        },
    ),
    "hold-09-center": (
        {
            "frame": {"x": 0.380146330672, "y": 0.04339135533, "width": 0.117524993347, "height": 0.189075649746},
            "commands": (
                {"command": "move", "to": (0.0, 0.002428593094)},
                {"command": "curve", "control1": (0.227366056506, 0.0), "control2": (0.709626748609, 0.0), "to": (0.996930990713, 0.0)},
                {"command": "line", "to": (1.0, 1.0)},
                {"command": "curve", "control1": (0.712695757896, 1.0), "control2": (0.199652468425, 1.0), "to": (0.014956884215, 0.886597642826)},
                {"command": "close"},
            ),
        },
        {
            "frame": {"x": 0.497671324019, "y": 0.07847715736, "width": 0.120590818363, "height": 0.153989847716},
            "commands": (
                {"command": "move", "to": (1.0, 0.253164556962)},
                {"command": "curve", "control1": (0.75, 0.0), "control2": (0.28, 0.0), "to": (0.0, 0.0)},
                {"command": "line", "to": (0.0, 1.0)},
                {"command": "curve", "control1": (0.28, 1.0), "control2": (0.78, 1.0), "to": (0.96, 0.860759493671)},
                {"command": "curve", "control1": (1.0, 0.683544303797), "control2": (1.0, 0.430379746835), "to": (1.0, 0.253164556962)},
                {"command": "close"},
            ),
        },
    ),
    "hold-11-center": (
        {
            "frame": {"x": 0.356457431803, "y": 0.699634517766, "width": 0.141213892216, "height": 0.124751269036},
            "commands": (
                {"command": "move", "to": (0.0, 0.15)},
                {"command": "curve", "control1": (0.214285714286, 0.0), "control2": (0.714285714286, 0.0), "to": (1.0, 0.0)},
                {"command": "line", "to": (1.0, 1.0)},
                {"command": "curve", "control1": (0.69387755102, 1.0), "control2": (0.204081632653, 1.0), "to": (0.020408163265, 0.85)},
                {"command": "curve", "control1": (-1.64188e-07, 0.6375), "control2": (-1.64188e-07, 0.3125), "to": (0.0, 0.15)},
                {"command": "close"},
            ),
        },
        {
            "frame": {"x": 0.497671324019, "y": 0.699634517766, "width": 0.141213892216, "height": 0.124751269036},
            "commands": (
                {"command": "move", "to": (1.0, 0.15)},
                {"command": "curve", "control1": (0.785714285714, 0.0), "control2": (0.285714285714, 0.0), "to": (0.0, 0.0)},
                {"command": "line", "to": (0.0, 1.0)},
                {"command": "curve", "control1": (0.30612244898, 1.0), "control2": (0.795918367347, 1.0), "to": (0.979591836735, 0.85)},
                {"command": "curve", "control1": (1.000000164188, 0.6375), "control2": (1.000000164188, 0.3125), "to": (1.0, 0.15)},
                {"command": "close"},
            ),
        },
    ),
}

EXPECTED_GEOMETRY.update(
    {
        right_id: _mirrored_geometry(EXPECTED_GEOMETRY[left_id])
        for left_id, right_id in DIRECT_MIRRORED_PAIRS
    }
)


def _frame_seam_x(left: object, right: object) -> float:
    assert left.frame.x + left.frame.width <= right.frame.x
    return left.frame.x + left.frame.width


def test_escape_beta_22_audited_inventory_geometry_and_symmetry() -> None:
    board = load_board_package(PACKAGE_ROOT).board
    holds = {hold.id: hold for hold in board.holds}
    with Image.open(PACKAGE_ROOT / board.presentation_asset_path) as image:
        presentation_size = image.size

    assert board.id == "escape-beta-22"
    assert tuple((hold.id, hold.kind) for hold in board.holds) == EXPECTED_HOLDS
    assert Counter(hold.kind for hold in board.holds) == {
        "pinch": 4,
        "jug": 4,
        "edge": 8,
        "sloper": 2,
    }
    assert sum(len(hold.geometry) for hold in board.holds) == 20

    for hold in board.holds:
        expected_piece_count = 2 if hold.id.endswith("-center") else 1
        assert len(hold.geometry) == expected_piece_count
        for piece in hold.geometry:
            assert piece.shape.type == "path"
            assert piece.shape.commands[0].command == "move"
            assert piece.shape.commands[-1].command == "close"
            assert len(piece.shape.commands) >= 5
            assert 0 <= piece.frame.x < piece.frame.x + piece.frame.width <= 1
            assert 0 <= piece.frame.y < piece.frame.y + piece.frame.height <= 1

    actual_geometry = {hold.id: serialize_geometry(hold) for hold in board.holds}
    assert {
        hold_id: geometry
        for hold_id, geometry in actual_geometry.items()
        if hold_id not in DIRECT_MIRRORED_RIGHT_IDS
    } == {
        hold_id: geometry
        for hold_id, geometry in EXPECTED_GEOMETRY.items()
        if hold_id not in DIRECT_MIRRORED_RIGHT_IDS
    }

    for family in range(1, 9):
        left = holds[f"hold-{family:02d}-left"]
        right = holds[f"hold-{family:02d}-right"]
        assert left.kind == right.kind
        assert left.size_millimeters == right.size_millimeters
        left_x, _, left_width, _ = presentation_frame(left.frame, presentation_size)
        right_x, _, _, _ = presentation_frame(right.frame, presentation_size)
        assert left_x + left_width <= right_x

    seam_x: float | None = None
    for hold_id in CENTER_HOLDS:
        left, right = holds[hold_id].geometry
        pair_seam_x = _frame_seam_x(left, right)
        if seam_x is None:
            seam_x = pair_seam_x
        else:
            assert pair_seam_x == pytest.approx(seam_x, abs=1e-9)

    assert seam_x is not None
    assert 0 < seam_x < 1

    for hold in board.holds:
        assert hold.size_millimeters == EXPECTED_SIZES[hold.id]
        assert hold.grip_type is None
        assert hold.finger_capacity is None
        assert hold.features is None
        assert hold.depth_range_millimeters is None
