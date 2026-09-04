from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from PIL import Image

from conftest import load_board_catalog_module


REPO_ROOT = Path(__file__).resolve().parents[3]
HANGBOARDS_ROOT = REPO_ROOT / "Hangboards"
COMPACT_ROOT = HANGBOARDS_ROOT / "metolius-wood-grips-compact-ii"
DELUXE_ROOT = HANGBOARDS_ROOT / "metolius-wood-grips-deluxe-ii"
FOUNDRY_ROOT = HANGBOARDS_ROOT / "metolius-foundry"
PRIME_RIB_ROOT = HANGBOARDS_ROOT / "metolius-prime-rib"
FLASH_BOARD_ROOT = HANGBOARDS_ROOT / "tension-flash-board"
LIGHT_RAIL_ROOT = HANGBOARDS_ROOT / "metolius-light-rail-2"
ROCK_RINGS_ROOT = HANGBOARDS_ROOT / "metolius-rock-rings-3d"
YY_TRAVELBOARD_ROOT = HANGBOARDS_ROOT / "yy-travelboard"
YY_BAGUETTE_ROOT = HANGBOARDS_ROOT / "yy-baguette"
YY_BAGUETTE_EVO_ROOT = HANGBOARDS_ROOT / "yy-baguette-evo"
YY_PENTA_EVO_ROOT = HANGBOARDS_ROOT / "yy-penta-evo"
TRAINING_TILES_ROOT = HANGBOARDS_ROOT / "soill-training-tiles"
MAMMUT_DIAMOND_ROOT = HANGBOARDS_ROOT / "mammut-diamond-finger"
PIVOT_ROOT = HANGBOARDS_ROOT / "trango-rock-prodigy-pivot"


def test_pivot_is_one_catalog_board_with_orientation_presentations() -> None:
    """A Pivot orientation added as another direct child is a duplicate product."""
    pivot_package_roots = sorted(
        path.parent
        for path in HANGBOARDS_ROOT.glob("trango-rock-prodigy-pivot*/board.json")
    )

    assert pivot_package_roots == [PIVOT_ROOT]


def _global_path_segment_signatures(
    geometry: dict[str, object], *, mirror_horizontally: bool = False
) -> list[tuple[object, ...]]:
    """Return canonical global segments, independent of traversal direction."""
    frame = geometry["frame"]
    commands = geometry["shape"]["commands"]

    def global_point(local: list[float]) -> tuple[float, float]:
        x = frame["x"] + local[0] * frame["width"]
        if mirror_horizontally:
            x = 1 - x
        y = frame["y"] + local[1] * frame["height"]
        return (round(x, 12), round(y, 12))

    def line_signature(
        start: tuple[float, float], end: tuple[float, float]
    ) -> tuple[object, ...]:
        ordered = min((start, end), (end, start))
        return ("line", *ordered)

    def curve_signature(
        start: tuple[float, float],
        control1: tuple[float, float],
        control2: tuple[float, float],
        end: tuple[float, float],
    ) -> tuple[object, ...]:
        forward = (start, control1, control2, end)
        reverse = (end, control2, control1, start)
        return ("curve", *min(forward, reverse))

    start: tuple[float, float] | None = None
    current: tuple[float, float] | None = None
    segments: list[tuple[object, ...]] = []
    for command in commands:
        operation = command["command"]
        if operation == "move":
            start = current = global_point(command["to"])
        elif operation == "line":
            assert current is not None
            end = global_point(command["to"])
            segments.append(line_signature(current, end))
            current = end
        elif operation == "curve":
            assert current is not None
            end = global_point(command["to"])
            segments.append(
                curve_signature(
                    current,
                    global_point(command["control1"]),
                    global_point(command["control2"]),
                    end,
                )
            )
            current = end
        else:
            assert operation == "close"
            assert current is not None and start is not None
            if current != start:
                segments.append(line_signature(current, start))
            current = start
    return sorted(segments)


def _assert_global_paths_are_horizontal_mirrors(
    left: dict[str, object], right: dict[str, object]
) -> None:
    assert _global_path_segment_signatures(
        left, mirror_horizontally=True
    ) == _global_path_segment_signatures(right)


PRIME_RIB_HOLDS = (
    ("edge-38", "38 mm edge", "edge", 38),
    ("edge-23", "23 mm edge", "edge", 23),
    ("edge-15", "15 mm edge", "edge", 15),
)
FOUNDRY_HOLDS = (
    ("pinch-1-left", "Left #1 variable pinch", "pinch", None, None),
    ("jug-2-left", "Left #2 outer jug", "jug", None, None),
    ("pocket-3-left", "Left #3 32 mm 4-finger pocket", "pocket", 32, 4),
    ("pocket-4-left", "Left #4 22 mm 3-finger pocket", "pocket", 22, 3),
    ("pocket-5-left", "Left #5 30 mm 2-finger pocket", "pocket", 30, 2),
    ("pocket-6-left", "Left #6 15 mm 3-finger pocket", "pocket", 15, 3),
    ("pocket-7-left", "Left #7 21 mm 2-finger pocket", "pocket", 21, 2),
    ("sloper-8-center", "Center #8 53 mm flat sloper", "sloper", None, None),
    ("edge-9-center", "Center #9 16 mm edge", "edge", 16, None),
    ("edge-10-center", "Center #10 30 mm edge", "edge", 30, None),
    ("edge-11-center", "Center #11 23 mm edge", "edge", 23, None),
    ("pocket-7-right", "Right #7 21 mm 2-finger pocket", "pocket", 21, 2),
    ("pocket-6-right", "Right #6 15 mm 3-finger pocket", "pocket", 15, 3),
    ("pocket-5-right", "Right #5 30 mm 2-finger pocket", "pocket", 30, 2),
    ("pocket-4-right", "Right #4 22 mm 3-finger pocket", "pocket", 22, 3),
    ("pocket-3-right", "Right #3 32 mm 4-finger pocket", "pocket", 32, 4),
    ("jug-2-right", "Right #2 outer jug", "jug", None, None),
    ("pinch-1-right", "Right #1 variable pinch", "pinch", None, None),
)
COMPACT_HOLDS = (
    ("jug-left", "Left outer jug"),
    ("sloper-flat-left", "Left 56 mm flat sloper"),
    ("sloper-round-center", "Center 56 mm round sloper"),
    ("sloper-flat-right", "Right 56 mm flat sloper"),
    ("jug-right", "Right outer jug"),
    ("edge-29-left", "Left 29 mm edge"),
    ("pocket-29-three-left", "Left 29 mm three-finger pocket"),
    ("pocket-29-two-left", "Left 29 mm two-finger pocket"),
    ("pocket-29-four-center", "Center 29 mm four-finger pocket"),
    ("pocket-29-two-right", "Right 29 mm two-finger pocket"),
    ("pocket-29-three-right", "Right 29 mm three-finger pocket"),
    ("edge-29-right", "Right 29 mm edge"),
    ("edge-19-left", "Left 19 mm edge"),
    ("pocket-19-three-left", "Left 19 mm three-finger pocket"),
    ("pocket-19-three-right", "Right 19 mm three-finger pocket"),
    ("pocket-19-two-left", "Left 19 mm two-finger pocket"),
    ("pocket-19-two-right", "Right 19 mm two-finger pocket"),
    ("pocket-19-four-center", "Center 19 mm four-finger pocket"),
    ("edge-19-right", "Right 19 mm edge"),
)

COMPACT_HOLD_BOUNDS = {
    "jug-left": (0.037438760543, 0.033340176927, 0.151177566966, 0.147356834014),
    "sloper-flat-left": (0.18823738106, 0.074170080963, 0.15100319053, 0.11883253391699998),
    "sloper-round-center": (0.335872142052, 0.067902866521, 0.331604864713, 0.130400487965),
    "sloper-flat-right": (0.664804328636, 0.086104452954, 0.14671776268299996, 0.104897986871),
    "jug-right": (0.808482115558, 0.046999221007, 0.151953933142, 0.151461838074),
    "edge-29-left": (0.04569001522, 0.241975420131, 0.155448063257, 0.268655293217),
    "pocket-29-three-left": (0.222529936866, 0.379677032823, 0.09641943799299998, 0.13582318380699998),
    "pocket-29-two-left": (0.336854291432, 0.368749890591, 0.07201019391199998, 0.14699999999999996),
    "pocket-29-four-center": (0.429756544532, 0.363488129103, 0.14120829988700007, 0.14951187089700002),
    "pocket-29-two-right": (0.593146998873, 0.36768849453, 0.06636609752, 0.14931150547),
    "pocket-29-three-right": (0.67935078805, 0.376089225383, 0.09864743292, 0.13691077461700002),
    "edge-29-right": (0.801012246904, 0.224094693654, 0.15223071138200006, 0.2847073807439999),
    "edge-19-left": (0.06299286133, 0.622153352298, 0.15250864614100001, 0.22923483588600002),
    "pocket-19-three-left": (0.236610587937, 0.705497606127, 0.09380289007899997, 0.14),
    "pocket-19-three-right": (0.66583022097, 0.708559829322, 0.09482928974100002, 0.129437122538),
    "pocket-19-two-left": (0.342440808906, 0.705497606127, 0.07299134385599998, 0.14),
    "pocket-19-two-right": (0.584559191094, 0.704247496718, 0.06692861217599999, 0.14),
    "pocket-19-four-center": (0.429830606539, 0.705497606127, 0.13696056256999994, 0.14),
    "edge-19-right": (0.785154857012, 0.640384105033, 0.14809514298799997, 0.20808716411399997),
}

# Each value is (source-backed kind, scalar depth, capacity, structural pocket
# grip, feature set). Sloper descriptors are not scalar depths, non-pocket
# capacities are not published, and the manufacturer publishes no package
# feature tags.
COMPACT_HOLD_SOURCE_FACTS = {
    "jug-left": ("jug", None, None, None, ()),
    "sloper-flat-left": ("sloper", None, None, None, ()),
    "sloper-round-center": ("sloper", None, None, None, ()),
    "sloper-flat-right": ("sloper", None, None, None, ()),
    "jug-right": ("jug", None, None, None, ()),
    "edge-29-left": ("edge", 29, None, None, ()),
    "pocket-29-three-left": ("pocket", 29, 3, "threeFingerPocket", ()),
    "pocket-29-two-left": ("pocket", 29, 2, "twoFingerPocket", ()),
    "pocket-29-four-center": ("pocket", 29, 4, "fourFingerPocket", ()),
    "pocket-29-two-right": ("pocket", 29, 2, "twoFingerPocket", ()),
    "pocket-29-three-right": ("pocket", 29, 3, "threeFingerPocket", ()),
    "edge-29-right": ("edge", 29, None, None, ()),
    "edge-19-left": ("edge", 19, None, None, ()),
    "pocket-19-three-left": ("pocket", 19, 3, "threeFingerPocket", ()),
    "pocket-19-three-right": ("pocket", 19, 3, "threeFingerPocket", ()),
    "pocket-19-two-left": ("pocket", 19, 2, "twoFingerPocket", ()),
    "pocket-19-two-right": ("pocket", 19, 2, "twoFingerPocket", ()),
    "pocket-19-four-center": ("pocket", 19, 4, "fourFingerPocket", ()),
    "edge-19-right": ("edge", 19, None, None, ()),
}

def _embedded_geometry_bounds(
    geometry: object,
) -> tuple[float, float, float, float] | None:
    if not isinstance(geometry, list) or not geometry:
        return None
    frames = [piece["frame"] for piece in geometry]
    min_x = min(frame["x"] for frame in frames)
    min_y = min(frame["y"] for frame in frames)
    max_x = max(frame["x"] + frame["width"] for frame in frames)
    max_y = max(frame["y"] + frame["height"] for frame in frames)
    return (min_x, min_y, max_x - min_x, max_y - min_y)


def test_direct_discovery_finds_the_exact_complete_inventory_without_drafts() -> None:
    inventory = load_board_catalog_module().discover_board_packages(HANGBOARDS_ROOT)

    discovered = {(package.board.id, package.root.name) for package in inventory.packages}

    expected_packages = {
        ("metolius.wood-grips-compact-ii", "metolius-wood-grips-compact-ii"),
        ("metolius.wood-grips-deluxe-ii", "metolius-wood-grips-deluxe-ii"),
        ("beastmaker-1000", "beastmaker-1000"),
        ("beastmaker-2000", "beastmaker-2000"),
        ("dewoodstok-woodbord", "dewoodstok-woodbord"),
        ("owl-climb.poker", "owl-climb-poker"),
        ("escape-beta-22", "escape-beta-22"),
        ("escape.unlimited", "escape-unlimited"),
        ("evolv-kilter-basic-long", "evolv-kilter-basic-long"),
        ("frictitious.doormount-pro-7", "frictitious-doormount-pro-7"),
        ("frictitious.megalith", "frictitious-megalith"),
        ("frictitious.port-a-board", "frictitious-port-a-board"),
        ("lattice-triple-rung", "lattice-triple-rung"),
        ("mammut.diamond-finger", "mammut-diamond-finger"),
        ("metolius.climbers-edge", "metolius-climbers-edge"),
        ("metolius.contact", "metolius-contact"),
        ("metolius.foundry", "metolius-foundry"),
        ("metolius.light-rail-2", "metolius-light-rail-2"),
        ("metolius.rock-rings-3d", "metolius-rock-rings-3d"),
        ("metolius.prime-rib", "metolius-prime-rib"),
        ("metolius.project", "metolius-project"),
        ("metolius.simulator-3d", "metolius-simulator-3d"),
        ("moon.armstrong", "moon-armstrong"),
        ("nature.stoak-board-iii", "nature-stoak-board-iii"),
        ("soill.iron-palm-2", "soill-iron-palm-2"),
        ("soill.split-palm", "soill-split-palm"),
        ("soill.training-tiles", "soill-training-tiles"),
        ("target10a.linebreaker-base", "target10a-linebreaker-base"),
        ("the-hangboard.the-hangboard", "the-hangboard"),
        ("trango.rock-prodigy-forge", "trango-rock-prodigy-forge"),
        ("trango.rock-prodigy-natural", "trango-rock-prodigy-natural"),
        ("trango.rock-prodigy-pivot", "trango-rock-prodigy-pivot"),
        (
            "trango.rock-prodigy-training-center",
            "trango-rock-prodigy-training-center",
        ),
        ("tension.grindstone", "tension-grindstone"),
        ("tension.grindstone-original", "tension-grindstone-original"),
        ("tension.grindstone-pro", "tension-grindstone-pro"),
        ("tension.flash-board", "tension-flash-board"),
        ("tension.honestone", "tension-honestone"),
        ("tension.whetstone", "tension-whetstone"),
        ("yy.verticalboard-evo", "yy-verticalboard-evo"),
        ("yy.verticalboard-first", "yy-verticalboard-first"),
        ("yy.verticalboard-light", "yy-verticalboard-light"),
        ("yy.verticalboard-one", "yy-verticalboard-one"),
        ("yy.travelboard", "yy-travelboard"),
        ("yy.baguette", "yy-baguette"),
        ("yy.baguette-evo", "yy-baguette-evo"),
        ("yy.penta-evo", "yy-penta-evo"),
        ("zlagboard.evo", "zlagboard-evo"),
        ("zlagboard.pro", "zlagboard-pro"),
        ("aelith.cyclops-011", "aelith-cyclops-011"),
        ("captain-fingerfood.dual", "captain-fingerfood-dual"),
        ("captain-fingerfood.pocket", "captain-fingerfood-pocket"),
        ("captain-fingerfood.unlevel", "captain-fingerfood-unlevel"),
        ("crimptonite.helium-mobile", "crimptonite-helium-mobile"),
        ("frictitious.nug", "frictitious-nug"),
        ("lattice.mini-bar", "lattice-mini-bar"),
        ("lattice.mxedge-lift-small", "lattice-mxedge-lift-small"),
        ("lattice.mxedge-lift-large", "lattice-mxedge-lift-large"),
        ("nature.stone-hanger-mini", "nature-stone-hanger-mini"),
        ("nature.stone-hanger-mini-karma8a", "nature-stone-hanger-mini-karma8a"),
        ("plateau.lifting-edge", "plateau-lifting-edge"),
    }
    assert discovered == expected_packages
    assert inventory.drafts == ()
    assert not (HANGBOARDS_ROOT / "catalog.json").exists()


def test_every_approved_board_uses_the_unversioned_presentation_shape() -> None:
    for board_path in HANGBOARDS_ROOT.glob("*/board.json"):
        document = json.loads(board_path.read_text(encoding="utf-8"))

        assert "schemaVersion" not in document
        assert "presentation" not in document

        presentations = document["presentations"]
        assert sum(presentation.get("default") is True for presentation in presentations) == 1
        presentation_ids = {presentation["id"] for presentation in presentations}
        assert all(
            hold["presentationID"] in presentation_ids for hold in document["holds"]
        )


def test_approved_packages_declare_their_complete_presentation_asset_set() -> None:
    inventory = load_board_catalog_module().discover_board_packages(HANGBOARDS_ROOT)

    for package in inventory.packages:
        document = json.loads((package.root / "board.json").read_text(encoding="utf-8"))
        actual_assets = {
            path.relative_to(package.root).as_posix()
            for path in (package.root / "assets").rglob("*")
            if path.is_file()
        }
        assert "schemaVersion" not in document
        assert "presentation" not in document
        assert all(
            isinstance(presentation["aspectRatio"], (int, float))
            and not isinstance(presentation["aspectRatio"], bool)
            and presentation["aspectRatio"] > 0
            for presentation in document["presentations"]
        )
        assert actual_assets == {
            presentation["assetPath"] for presentation in document["presentations"]
        }


def test_compact_finished_package_has_exactly_one_document_and_primary_asset() -> None:
    relative_paths = {
        path.relative_to(COMPACT_ROOT).as_posix()
        for path in COMPACT_ROOT.rglob("*")
    }

    assert relative_paths == {"assets", "assets/primary.png", "board.json"}


def test_mammut_diamond_freezes_the_documented_21_contact_inventory() -> None:
    board = json.loads((MAMMUT_DIAMOND_ROOT / "board.json").read_text(encoding="utf-8"))

    assert board["id"] == "mammut.diamond-finger"
    assert [(hold["id"], hold["kind"], hold.get("sizeMillimeters"), hold.get("fingerCapacity"), hold.get("gripType")) for hold in board["holds"]] == [
        ("jug-left", "jug", None, None, None),
        ("sloper-45-left", "sloper", None, None, None),
        ("pocket-30-four-left", "pocket", 30, 4, "fourFingerPocket"),
        ("pocket-16-two-left", "pocket", 16, 2, "twoFingerPocket"),
        ("pocket-16-three-left", "pocket", 16, 3, "threeFingerPocket"),
        ("pocket-20-eight-left", "pocket", 20, 4, "fourFingerPocket"),
        ("pocket-20-four-left", "pocket", 20, 4, "fourFingerPocket"),
        ("pocket-10-four-left", "pocket", 10, 4, "fourFingerPocket"),
        ("sloper-48-center", "sloper", None, None, None),
        ("pocket-30-eight-center", "pocket", 30, 4, "fourFingerPocket"),
        ("pocket-18-eight-center", "pocket", 18, 4, "fourFingerPocket"),
        ("pocket-10-four-right", "pocket", 10, 4, "fourFingerPocket"),
        ("pocket-20-four-right", "pocket", 20, 4, "fourFingerPocket"),
        ("pocket-20-eight-right", "pocket", 20, 4, "fourFingerPocket"),
        ("pocket-16-three-right", "pocket", 16, 3, "threeFingerPocket"),
        ("pocket-16-two-right", "pocket", 16, 2, "twoFingerPocket"),
        ("pocket-30-four-right", "pocket", 30, 4, "fourFingerPocket"),
        ("sloper-45-right", "sloper", None, None, None),
        ("jug-right", "jug", None, None, None),
        ("sloper-30-left", "sloper", None, None, None),
        ("sloper-30-right", "sloper", None, None, None),
    ]

    holds = {hold["id"]: hold for hold in board["holds"]}
    assert all(
        "treatment" not in piece
        for hold in board["holds"]
        for piece in hold["geometry"]
    )
    for left_id, right_id in (
        ("jug-left", "jug-right"),
        ("sloper-45-left", "sloper-45-right"),
        ("sloper-30-left", "sloper-30-right"),
        ("pocket-30-four-left", "pocket-30-four-right"),
        ("pocket-16-two-left", "pocket-16-two-right"),
        ("pocket-16-three-left", "pocket-16-three-right"),
        ("pocket-20-eight-left", "pocket-20-eight-right"),
        ("pocket-20-four-left", "pocket-20-four-right"),
        ("pocket-10-four-left", "pocket-10-four-right"),
    ):
        left_piece = holds[left_id]["geometry"][0]
        right_piece = holds[right_id]["geometry"][0]
        left_frame = left_piece["frame"]
        right_frame = right_piece["frame"]
        assert right_frame["x"] == pytest.approx(
            1 - left_frame["x"] - left_frame["width"], abs=1e-12
        )
        assert right_frame["y"] == left_frame["y"]
        assert right_frame["width"] == left_frame["width"]
        assert right_frame["height"] == left_frame["height"]
        assert right_piece.get("shapeConstraint") == left_piece.get("shapeConstraint")

    _assert_global_paths_are_horizontal_mirrors(
        holds["jug-left"]["geometry"][0], holds["jug-right"]["geometry"][0]
    )


def test_foundry_package_freezes_the_official_numbered_inventory() -> None:
    board = json.loads((FOUNDRY_ROOT / "board.json").read_text(encoding="utf-8"))

    assert board["id"] == "metolius.foundry"
    assert board["presentations"] == [
        {
            "id": "front",
            "name": "Front",
            "assetPath": "assets/primary.png",
            "aspectRatio": 2.0,
            "default": True,
        }
    ]
    assert tuple(
        (
            hold["id"],
            hold["name"],
            hold["kind"],
            hold.get("sizeMillimeters"),
            hold.get("fingerCapacity"),
        )
        for hold in board["holds"]
    ) == FOUNDRY_HOLDS
    assert all(hold["presentationID"] == "front" for hold in board["holds"])
    assert all(hold["geometry"] for hold in board["holds"])


def test_foundry_paired_contacts_use_exact_horizontal_mirrors() -> None:
    board = json.loads((FOUNDRY_ROOT / "board.json").read_text(encoding="utf-8"))
    holds = {hold["id"]: hold for hold in board["holds"]}

    for position in range(1, 8):
        prefix = "pinch" if position == 1 else "jug" if position == 2 else "pocket"
        left = holds[f"{prefix}-{position}-left"]["geometry"][0]
        right = holds[f"{prefix}-{position}-right"]["geometry"][0]
        left_frame = left["frame"]
        right_frame = right["frame"]

        assert right_frame["x"] == pytest.approx(
            1 - left_frame["x"] - left_frame["width"]
        )
        assert right_frame["y"] == left_frame["y"]
        assert right_frame["width"] == left_frame["width"]
        assert right_frame["height"] == left_frame["height"]
        assert right.get("shapeConstraint") == left.get("shapeConstraint")

        left_commands = left["shape"]["commands"]
        right_commands = right["shape"]["commands"]
        if position >= 3:
            # These regular paths are themselves horizontally symmetric.
            assert right_commands == left_commands
            continue

        assert len(right_commands) == len(left_commands)
        for left_command, right_command in zip(left_commands, right_commands, strict=True):
            assert right_command["command"] == left_command["command"]
            for point_key in ("to", "control", "control1", "control2"):
                if point_key not in left_command:
                    assert point_key not in right_command
                    continue
                assert right_command[point_key][0] == pytest.approx(
                    1 - left_command[point_key][0]
                )
                assert right_command[point_key][1] == left_command[point_key][1]


def test_prime_rib_package_freezes_the_official_three_edge_inventory() -> None:
    board = json.loads((PRIME_RIB_ROOT / "board.json").read_text(encoding="utf-8"))

    assert board["id"] == "metolius.prime-rib"
    assert board["dimensions"] == "20 × 4.2 × 1.5 in"
    assert board["presentations"] == [
        {
            "id": "front",
            "name": "Front",
            "assetPath": "assets/primary.png",
            "aspectRatio": 1704 / 923,
            "default": True,
        }
    ]
    assert tuple(
        (
            hold["id"],
            hold["name"],
            hold["kind"],
            hold.get("sizeMillimeters"),
        )
        for hold in board["holds"]
    ) == PRIME_RIB_HOLDS
    assert all(hold["presentationID"] == "front" for hold in board["holds"])
    assert all(len(hold["geometry"]) == 1 for hold in board["holds"])
    assert all(
        hold["geometry"][0]["shape"]["type"] == "path"
        for hold in board["holds"]
    )


def test_flash_board_package_freezes_the_official_surface_inventories() -> None:
    board = json.loads((FLASH_BOARD_ROOT / "board.json").read_text(encoding="utf-8"))

    assert board["id"] == "tension.flash-board"
    assert "dimensions" not in board
    assert board["presentations"] == [
        {
            "id": "three-edge-upright",
            "name": "Three-edge surface — right side up",
            "assetPath": "assets/primary.png",
            "aspectRatio": 1.5,
            "default": True,
        },
        {
            "id": "three-edge-inverted",
            "name": "Three-edge surface — upside down",
            "assetPath": "assets/three-edge-inverted.png",
            "aspectRatio": 1.5,
            "default": False,
            "sourcePresentationID": "three-edge-upright",
            "isInverted": True,
        },
        {
            "id": "two-edge-upright",
            "name": "Two-edge surface — right side up",
            "assetPath": "assets/two-edge-surface.png",
            "aspectRatio": 2.0,
            "default": False,
        },
        {
            "id": "two-edge-inverted",
            "name": "Two-edge surface — upside down",
            "assetPath": "assets/two-edge-inverted.png",
            "aspectRatio": 2.0,
            "default": False,
            "sourcePresentationID": "two-edge-upright",
            "isInverted": True,
        },
    ]

    holds_by_presentation = {
        presentation_id: tuple(
            hold["id"]
            for hold in board["holds"]
            if hold["presentationID"] == presentation_id
        )
        for presentation_id in ("three-edge-upright", "two-edge-upright")
    }
    assert holds_by_presentation == {
        "three-edge-upright": (
            "three-edge-left",
            "three-edge-center",
            "three-edge-right",
        ),
        "two-edge-upright": (
            "two-edge-left",
            "two-edge-right",
            "small-crimp-left",
            "small-crimp-right",
        ),
    }
    assert all(hold["kind"] == "edge" for hold in board["holds"])
    assert all("sizeMillimeters" not in hold for hold in board["holds"])
    assert all(len(hold["geometry"]) == 1 for hold in board["holds"])
    assert all(hold["geometry"][0]["shape"]["type"] == "path" for hold in board["holds"])

    expected_sizes = {
        "assets/primary.png": (1536, 1024),
        "assets/three-edge-inverted.png": (1536, 1024),
        "assets/two-edge-surface.png": (1774, 887),
        "assets/two-edge-inverted.png": (1774, 887),
    }
    for asset_path, expected_size in expected_sizes.items():
        with Image.open(FLASH_BOARD_ROOT / asset_path) as image:
            assert image.format == "PNG"
            assert image.size == expected_size


def test_light_rail_package_freezes_the_official_reversible_inventory() -> None:
    board = json.loads((LIGHT_RAIL_ROOT / "board.json").read_text(encoding="utf-8"))

    assert board["id"] == "metolius.light-rail-2"
    assert board["dimensions"] == "18 × 3 × 1.5 in"
    assert board["presentations"] == [
        {
            "id": "20mm-side",
            "name": "40 mm jug and 20 mm edge",
            "assetPath": "assets/primary.png",
            "aspectRatio": 1.5,
            "default": True,
        },
        {
            "id": "15mm-side",
            "name": "40 mm jug and 15 mm edge",
            "assetPath": "assets/15mm-surface.png",
            "aspectRatio": 1.5,
            "default": False,
        },
    ]

    assert tuple(
        (
            hold["id"],
            hold["name"],
            hold["kind"],
            hold["sizeMillimeters"],
            hold["presentationID"],
        )
        for hold in board["holds"]
    ) == (
        (
            "jug-40-20mm-side",
            "40 mm rounded jug on 20 mm side",
            "jug",
            40,
            "20mm-side",
        ),
        ("edge-20", "20 mm edge", "edge", 20, "20mm-side"),
        (
            "jug-40-15mm-side",
            "40 mm rounded jug on 15 mm side",
            "jug",
            40,
            "15mm-side",
        ),
        ("edge-15", "15 mm edge", "edge", 15, "15mm-side"),
    )
    assert all(len(hold["geometry"]) == 1 for hold in board["holds"])
    assert all(
        hold["geometry"][0]["shapeConstraint"] == {
            "shape": "roundedRectangle",
            "rotationDegrees": 0,
        }
        for hold in board["holds"]
    )

    for asset_path, expected_size in {
        "assets/primary.png": (1536, 1024),
        "assets/15mm-surface.png": (1536, 1024),
    }.items():
        with Image.open(LIGHT_RAIL_ROOT / asset_path) as image:
            assert image.format == "PNG"
            assert image.size == expected_size


def test_rock_rings_package_freezes_the_official_two_unit_inventory() -> None:
    board = json.loads((ROCK_RINGS_ROOT / "board.json").read_text(encoding="utf-8"))

    assert board["id"] == "metolius.rock-rings-3d"
    assert board["dimensions"] == "184 × 146 × 57 mm"
    assert board["presentations"] == [
        {
            "id": "front-pair",
            "name": "Front pair",
            "assetPath": "assets/primary.png",
            "aspectRatio": 1.5,
            "default": True,
        }
    ]

    assert tuple(
        (
            hold["id"],
            hold["name"],
            hold["kind"],
            hold.get("sizeMillimeters"),
            hold.get("fingerCapacity"),
            hold["presentationID"],
        )
        for hold in board["holds"]
    ) == (
        ("jug-left", "Left unit jug", "jug", None, None, "front-pair"),
        (
            "pocket-40-four-left",
            "Left unit 40 mm four-finger pocket",
            "pocket",
            40,
            4,
            "front-pair",
        ),
        (
            "pocket-32-three-left",
            "Left unit 32 mm three-finger pocket",
            "pocket",
            32,
            3,
            "front-pair",
        ),
        (
            "pocket-25-two-left",
            "Left unit 25 mm two-finger pocket",
            "pocket",
            25,
            2,
            "front-pair",
        ),
        ("jug-right", "Right unit jug", "jug", None, None, "front-pair"),
        (
            "pocket-40-four-right",
            "Right unit 40 mm four-finger pocket",
            "pocket",
            40,
            4,
            "front-pair",
        ),
        (
            "pocket-32-three-right",
            "Right unit 32 mm three-finger pocket",
            "pocket",
            32,
            3,
            "front-pair",
        ),
        (
            "pocket-25-two-right",
            "Right unit 25 mm two-finger pocket",
            "pocket",
            25,
            2,
            "front-pair",
        ),
    )
    assert all(len(hold["geometry"]) == 1 for hold in board["holds"])
    assert all(hold["geometry"][0]["shape"]["type"] == "path" for hold in board["holds"])
    assert all(
        hold["geometry"][0]["shapeConstraint"]
        == {"shape": "roundedRectangle", "rotationDegrees": 0}
        for hold in board["holds"]
        if hold["kind"] == "pocket"
    )

    with Image.open(ROCK_RINGS_ROOT / "assets" / "primary.png") as image:
        assert image.format == "PNG"
        assert image.size == (1536, 1024)


def test_rock_rings_paired_contacts_use_exact_horizontal_mirrors() -> None:
    board = json.loads((ROCK_RINGS_ROOT / "board.json").read_text(encoding="utf-8"))
    holds = {hold["id"]: hold for hold in board["holds"]}

    for left_id, right_id in (
        ("jug-left", "jug-right"),
        ("pocket-40-four-left", "pocket-40-four-right"),
        ("pocket-32-three-left", "pocket-32-three-right"),
        ("pocket-25-two-left", "pocket-25-two-right"),
    ):
        left = holds[left_id]["geometry"][0]
        right = holds[right_id]["geometry"][0]
        left_frame = left["frame"]
        right_frame = right["frame"]

        assert right_frame["x"] == pytest.approx(
            1 - left_frame["x"] - left_frame["width"]
        )
        assert right_frame["y"] == left_frame["y"]
        assert right_frame["width"] == left_frame["width"]
        assert right_frame["height"] == left_frame["height"]
        assert right["shape"]["type"] == left["shape"]["type"] == "path"
        _assert_global_paths_are_horizontal_mirrors(left, right)
        assert [
            command.get("bendable") for command in right["shape"]["commands"]
        ] == [command.get("bendable") for command in left["shape"]["commands"]]
        assert right.get("shapeConstraint") == left.get("shapeConstraint")


def test_deluxe_package_freezes_the_independent_official_inventory() -> None:
    board = json.loads((DELUXE_ROOT / "board.json").read_text(encoding="utf-8"))

    assert board["id"] == "metolius.wood-grips-deluxe-ii"
    assert board["dimensions"] == "24 × 8.5 in"
    assert board["presentations"] == [
        {
            "id": "front",
            "name": "Front",
            "assetPath": "assets/primary.png",
            "aspectRatio": 2.0,
            "default": True,
        }
    ]
    assert {
        (
            hold["id"],
            hold["kind"],
            hold.get("sizeMillimeters"),
            hold.get("fingerCapacity"),
            hold.get("gripType"),
        )
        for hold in board["holds"]
    } == {
        ("jug-1-left", "jug", None, None, None),
        ("jug-1-right", "jug", None, None, None),
        ("sloper-2-flat-left", "sloper", None, None, None),
        ("sloper-2-flat-right", "sloper", None, None, None),
        ("sloper-12-round-center", "sloper", None, None, None),
        ("edge-3-31-left", "edge", 31, None, None),
        ("edge-3-31-right", "edge", 31, None, None),
        ("pocket-4-32-three-left", "pocket", 32, 3, "threeFingerPocket"),
        ("pocket-4-32-three-right", "pocket", 32, 3, "threeFingerPocket"),
        ("pocket-5-38-two-left", "pocket", 38, 2, "twoFingerPocket"),
        ("pocket-5-38-two-right", "pocket", 38, 2, "twoFingerPocket"),
        ("pocket-13-32-four-center", "pocket", 32, 4, "fourFingerPocket"),
        ("edge-6-25-left", "edge", 25, None, None),
        ("edge-6-25-right", "edge", 25, None, None),
        ("pocket-7-25-three-left", "pocket", 25, 3, "threeFingerPocket"),
        ("pocket-7-25-three-right", "pocket", 25, 3, "threeFingerPocket"),
        ("pocket-8-28-two-left", "pocket", 28, 2, "twoFingerPocket"),
        ("pocket-8-28-two-right", "pocket", 28, 2, "twoFingerPocket"),
        ("pocket-14-25-four-center", "pocket", 25, 4, "fourFingerPocket"),
        ("edge-9-19-left", "edge", 19, None, None),
        ("edge-9-19-right", "edge", 19, None, None),
        ("pocket-10-19-three-left", "pocket", 19, 3, "threeFingerPocket"),
        ("pocket-10-19-three-right", "pocket", 19, 3, "threeFingerPocket"),
        ("pocket-11-19-two-left", "pocket", 19, 2, "twoFingerPocket"),
        ("pocket-11-19-two-right", "pocket", 19, 2, "twoFingerPocket"),
        ("pocket-15-19-four-center", "pocket", 19, 4, "fourFingerPocket"),
    }
    assert len(board["holds"]) == 26
    assert all(hold["presentationID"] == "front" for hold in board["holds"])
    assert all(len(hold["geometry"]) == 1 for hold in board["holds"])
    assert all(hold["geometry"][0]["shape"]["type"] == "path" for hold in board["holds"])

    compact = json.loads((COMPACT_ROOT / "board.json").read_text(encoding="utf-8"))
    assert board["dimensions"] != compact["dimensions"]
    assert len(board["holds"]) != len(compact["holds"])


def test_deluxe_paired_contacts_use_exact_horizontal_frame_mirrors() -> None:
    board = json.loads((DELUXE_ROOT / "board.json").read_text(encoding="utf-8"))
    holds = {hold["id"]: hold for hold in board["holds"]}
    pairs = (
        ("jug-1-left", "jug-1-right"),
        ("sloper-2-flat-left", "sloper-2-flat-right"),
        ("edge-3-31-left", "edge-3-31-right"),
        ("pocket-4-32-three-left", "pocket-4-32-three-right"),
        ("pocket-5-38-two-left", "pocket-5-38-two-right"),
        ("edge-6-25-left", "edge-6-25-right"),
        ("pocket-7-25-three-left", "pocket-7-25-three-right"),
        ("pocket-8-28-two-left", "pocket-8-28-two-right"),
        ("edge-9-19-left", "edge-9-19-right"),
        ("pocket-10-19-three-left", "pocket-10-19-three-right"),
        ("pocket-11-19-two-left", "pocket-11-19-two-right"),
    )

    for left_id, right_id in pairs:
        left = holds[left_id]["geometry"][0]["frame"]
        right = holds[right_id]["geometry"][0]["frame"]
        assert right["x"] == pytest.approx(1 - left["x"] - left["width"])
        assert right["y"] == left["y"]
        assert right["width"] == left["width"]
        assert right["height"] == left["height"]


def test_compact_board_keeps_the_literal_hold_inventory_with_embedded_geometry() -> None:
    board = json.loads((COMPACT_ROOT / "board.json").read_text(encoding="utf-8"))
    holds = board["holds"]
    hold_ids = [hold["id"] for hold in holds]

    assert board["id"] == "metolius.wood-grips-compact-ii"
    assert tuple((hold["id"], hold["name"]) for hold in holds) == COMPACT_HOLDS
    assert len(hold_ids) == len(set(hold_ids))
    assert all(hold.get("geometry") for hold in holds)


def test_training_tiles_freezes_source_limited_adapted_contact_model() -> None:
    board = json.loads((TRAINING_TILES_ROOT / "board.json").read_text(encoding="utf-8"))

    assert board["id"] == "soill.training-tiles"
    assert tuple((hold["id"], hold["name"], hold["kind"]) for hold in board["holds"]) == (
        ("upper-sloper-outer-left", "Outer left upper sloper", "sloper"),
        ("upper-sloper-outer-right", "Outer right upper sloper", "sloper"),
        ("upper-sloper-inner-left", "Inner left upper sloper", "sloper"),
        ("upper-sloper-inner-right", "Inner right upper sloper", "sloper"),
        ("middle-edge-outer-left", "Outer left middle edge", "edge"),
        ("middle-edge-outer-right", "Outer right middle edge", "edge"),
        ("middle-edge-inner-left", "Inner left middle edge", "edge"),
        ("middle-edge-inner-right", "Inner right middle edge", "edge"),
        ("bottom-edge-center-left", "Center left bottom edge", "edge"),
        ("bottom-edge-center-right", "Center right bottom edge", "edge"),
        ("top-pocket-outer-left", "Outer left top pocket", "pocket"),
        ("top-pocket-outer-right", "Outer right top pocket", "pocket"),
        ("bottom-edge-inner-left", "Inner left bottom edge", "edge"),
        ("bottom-edge-inner-right", "Inner right bottom edge", "edge"),
        ("bottom-edge-outer-left", "Outer left bottom edge", "edge"),
        ("bottom-edge-outer-right", "Outer right bottom edge", "edge"),
        ("top-pocket-inner-left", "Inner left top pocket", "pocket"),
        ("top-pocket-inner-right", "Inner right top pocket", "pocket"),
        ("top-jug-left", "Left top jug", "jug"),
        ("top-jug-right", "Right top jug", "jug"),
    )


def test_compact_hold_records_keep_only_source_audited_physical_facts() -> None:
    board = json.loads((COMPACT_ROOT / "board.json").read_text(encoding="utf-8"))
    holds = board["holds"]
    retired_fields = {"frame", "shortLabel", "detail", "cueStyle"}
    supported_fields = {
        "id",
        "name",
        "kind",
        "geometry",
        "sizeMillimeters",
        "depthRangeMillimeters",
        "fingerCapacity",
        "handCapacity",
        "equipmentObjectID",
        "gripType",
        "features",
        "sloper",
        "presentationID",
    }

    assert all(not (set(hold) & retired_fields) for hold in holds)
    assert all({"id", "name", "kind", "geometry"} <= set(hold) for hold in holds)
    assert all(set(hold) <= supported_fields for hold in holds)
    assert {hold.get("equipmentObjectID") for hold in holds} == {"primary"}
    assert all("depthRangeMillimeters" not in hold for hold in holds)
    expected_pocket_grips = {
        2: "twoFingerPocket",
        3: "threeFingerPocket",
        4: "fourFingerPocket",
    }
    assert all(
        hold.get("gripType") == expected_pocket_grips[hold["fingerCapacity"]]
        for hold in holds
        if hold["kind"] == "pocket"
    )
    assert all(
        "gripType" not in hold
        for hold in holds
        if hold["kind"] != "pocket"
    )
    assert {
        hold["id"]: (
            hold.get("kind"),
            hold.get("sizeMillimeters"),
            hold.get("fingerCapacity"),
            hold.get("gripType"),
            tuple(hold.get("features", ())),
        )
        for hold in holds
    } == COMPACT_HOLD_SOURCE_FACTS


def test_compact_hold_bounds_are_derived_from_embedded_piece_unions() -> None:
    board = json.loads((COMPACT_ROOT / "board.json").read_text(encoding="utf-8"))
    bounds_by_hold = {
        hold["id"]: _embedded_geometry_bounds(hold.get("geometry"))
        for hold in board["holds"]
    }

    assert set(bounds_by_hold) == set(COMPACT_HOLD_BOUNDS)
    for hold_id, expected_bounds in COMPACT_HOLD_BOUNDS.items():
        assert bounds_by_hold[hold_id] == pytest.approx(expected_bounds)


def test_compact_package_loader_preserves_identity_inventory_and_bounds() -> None:
    module = load_board_catalog_module()
    package = module.load_board_package(COMPACT_ROOT)

    assert tuple((hold.id, hold.name) for hold in package.board.holds) == COMPACT_HOLDS
    assert package.board.facts == {
        "manufacturer": "Metolius",
        "name": "Wood Grips Compact II",
        "subtitle": "FSC-certified wood training board.",
        "productURL": "https://www.metoliusclimbing.com/products/wood-grips-ii-training-boards",
        "dimensions": '24" × 6.2"',
        "aspectRatio": 3.88,
    }
    assert package.board.presentation_asset_path == "assets/primary.png"
    for hold in package.board.holds:
        actual = (hold.frame.x, hold.frame.y, hold.frame.width, hold.frame.height)
        assert actual == pytest.approx(COMPACT_HOLD_BOUNDS[hold.id])


def test_compact_screwless_asset_is_the_single_generated_presentation() -> None:
    repaired_path = COMPACT_ROOT / "assets" / "primary.png"
    repaired = Image.open(repaired_path).convert("RGB")

    assert repaired.size == (1774, 457)
    assert hashlib.sha256(repaired_path.read_bytes()).hexdigest() == "87ba30f259840deeb0559dd1d7e4cb3f18be3ee16e85f81f5be985557791e13e"


def test_yy_travelboard_freezes_the_official_six_grip_inventory() -> None:
    board = json.loads((YY_TRAVELBOARD_ROOT / "board.json").read_text(encoding="utf-8"))

    assert board["id"] == "yy.travelboard"
    assert board["dimensions"] == "34 × 10 × 3 cm"
    assert [(item["id"], item["assetPath"]) for item in board["presentations"]] == [
        ("front-25-15", "assets/primary.png"),
        ("reverse-10", "assets/reverse.png"),
    ]
    assert {
        (
            hold["id"],
            hold["kind"],
            hold.get("sizeMillimeters"),
            hold.get("fingerCapacity"),
            hold["presentationID"],
        )
        for hold in board["holds"]
    } == {
        ("tray", "jug", None, None, "front-25-15"),
        ("edge-25", "edge", 25, None, "front-25-15"),
        ("edge-15", "edge", 15, None, "front-25-15"),
        ("mono-left", "pocket", None, 1, "front-25-15"),
        ("mono-right", "pocket", None, 1, "front-25-15"),
        ("edge-10", "edge", 10, None, "reverse-10"),
    }


def test_yy_baguette_freezes_six_documented_grips_across_two_faces() -> None:
    board = json.loads((YY_BAGUETTE_ROOT / "board.json").read_text(encoding="utf-8"))

    assert board["id"] == "yy.baguette"
    assert board["dimensions"] == "47 × 4 × 4 cm"
    assert board["presentations"] == [
        {
            "id": "stepped-face",
            "name": "30 / 25 / 20 mm and tray face",
            "assetPath": "assets/primary.png",
            "aspectRatio": 1.5,
            "default": True,
        },
        {
            "id": "reverse-face",
            "name": "15 / 10 mm face",
            "assetPath": "assets/reverse.png",
            "aspectRatio": 1.5,
            "default": False,
        },
    ]
    assert {
        (hold["id"], hold["kind"], hold.get("sizeMillimeters"))
        for hold in board["holds"]
    } == {
        ("tray", "jug", None),
        ("edge-30", "edge", 30),
        ("edge-25", "edge", 25),
        ("edge-20", "edge", 20),
        ("edge-15", "edge", 15),
        ("edge-10", "edge", 10),
    }
    assert [(hold["id"], hold["presentationID"]) for hold in board["holds"]] == [
        ("edge-30", "stepped-face"),
        ("tray", "stepped-face"),
        ("edge-20", "stepped-face"),
        ("edge-25", "stepped-face"),
        ("edge-15", "reverse-face"),
        ("edge-10", "reverse-face"),
    ]


def test_yy_baguette_evo_freezes_twelve_grip_types_as_nineteen_contacts() -> None:
    board = json.loads((YY_BAGUETTE_EVO_ROOT / "board.json").read_text(encoding="utf-8"))

    assert board["id"] == "yy.baguette-evo"
    assert board["dimensions"] == "52 × 5 × 5 cm"
    assert board["presentations"] == [
        {
            "id": "paired-25-20-15-10",
            "name": "25 / 20 / 15 / 10 mm paired edges",
            "assetPath": "assets/primary.png",
            "aspectRatio": 2.0,
            "default": True,
        },
        {
            "id": "paired-12-8-6",
            "name": "12 / 8 / 6 mm paired edges",
            "assetPath": "assets/shallow-pairs.png",
            "aspectRatio": 2.0,
            "default": False,
        },
        {
            "id": "central-30-25",
            "name": "30 / 25 mm central edges",
            "assetPath": "assets/central-30-25.png",
            "aspectRatio": 2.0,
            "default": False,
        },
        {
            "id": "central-20-6",
            "name": "20 / 6 mm central edges",
            "assetPath": "assets/central-20-6.png",
            "aspectRatio": 2.0,
            "default": False,
        },
        {
            "id": "rounded-tray",
            "name": "Rounded tray",
            "assetPath": "assets/tray.png",
            "aspectRatio": 2.0,
            "default": False,
        },
    ]
    assert len(board["holds"]) == 19
    assert sorted(
        hold["sizeMillimeters"]
        for hold in board["holds"]
        if not hold["id"].startswith("edge-central") and hold["kind"] == "edge"
    ) == [6, 6, 8, 8, 10, 10, 12, 12, 15, 15, 20, 20, 25, 25]
    assert {
        (hold["id"], hold.get("sizeMillimeters"))
        for hold in board["holds"]
        if hold["id"].startswith("edge-central")
    } == {
        ("edge-central-30", 30),
        ("edge-central-25", 25),
        ("edge-central-20", 20),
        ("edge-central-6", 6),
    }
    assert [(hold["id"], hold["kind"]) for hold in board["holds"] if hold["kind"] == "jug"] == [
        ("rounded-tray", "jug")
    ]
    assert [(hold["id"], hold["presentationID"]) for hold in board["holds"]] == [
        ("edge-20-left", "paired-25-20-15-10"),
        ("edge-10-left", "paired-25-20-15-10"),
        ("edge-25-left", "paired-25-20-15-10"),
        ("edge-15-left", "paired-25-20-15-10"),
        ("edge-15-right", "paired-25-20-15-10"),
        ("edge-25-right", "paired-25-20-15-10"),
        ("edge-10-right", "paired-25-20-15-10"),
        ("edge-20-right", "paired-25-20-15-10"),
        ("edge-12-left", "paired-12-8-6"),
        ("edge-12-right", "paired-12-8-6"),
        ("edge-8-left", "paired-12-8-6"),
        ("edge-8-right", "paired-12-8-6"),
        ("edge-6-upper", "paired-12-8-6"),
        ("edge-6-lower", "paired-12-8-6"),
        ("edge-central-30", "central-30-25"),
        ("edge-central-25", "central-30-25"),
        ("edge-central-20", "central-20-6"),
        ("edge-central-6", "central-20-6"),
        ("rounded-tray", "rounded-tray"),
    ]


def test_yy_baguette_evo_central_30_25_paths_match_the_centered_recess() -> None:
    board = json.loads((YY_BAGUETTE_EVO_ROOT / "board.json").read_text(encoding="utf-8"))
    holds = {hold["id"]: hold for hold in board["holds"]}

    assert holds["edge-central-30"]["geometry"][0]["frame"] == {
        "x": 0.423,
        "y": 0.455,
        "width": 0.154,
        "height": 0.033,
    }
    assert holds["edge-central-25"]["geometry"][0]["frame"] == {
        "x": 0.423,
        "y": 0.543,
        "width": 0.154,
        "height": 0.030,
    }


def test_yy_baguette_evo_explicit_pairs_use_exact_horizontal_path_mirrors() -> None:
    board = json.loads((YY_BAGUETTE_EVO_ROOT / "board.json").read_text(encoding="utf-8"))
    holds = {hold["id"]: hold for hold in board["holds"]}

    for size in (25, 20, 15, 12, 10, 8):
        left = holds[f"edge-{size}-left"]["geometry"][0]
        right = holds[f"edge-{size}-right"]["geometry"][0]
        _assert_global_paths_are_horizontal_mirrors(left, right)


def test_yy_penta_evo_freezes_seven_contacts_per_official_pair_unit() -> None:
    board = json.loads((YY_PENTA_EVO_ROOT / "board.json").read_text(encoding="utf-8"))

    assert board["id"] == "yy.penta-evo"
    assert board["dimensions"] == "Not published by YY Vertical"
    assert len(board["presentations"]) == 1
    assert len(board["holds"]) == 14
    assert sorted(
        (hold["kind"], hold.get("sizeMillimeters"), hold.get("fingerCapacity"))
        for hold in board["holds"]
    ) == sorted(
        2
        * [
            ("edge", 25, None),
            ("edge", 20, None),
            ("edge", 15, None),
            ("edge", 10, None),
            ("pocket", None, 1),
            ("pocket", None, 2),
            ("jug", None, None),
        ]
    )
    assert all(hold["presentationID"] == "front-pair" for hold in board["holds"])

    holds = {hold["id"]: hold for hold in board["holds"]}
    assert holds["edge-25-left"]["geometry"][0]["frame"] == {
        "x": 0.116,
        "y": 0.350,
        "width": 0.121,
        "height": 0.122,
    }
    assert holds["edge-20-left"]["geometry"][0]["frame"] == {
        "x": 0.280,
        "y": 0.350,
        "width": 0.116,
        "height": 0.122,
    }


def test_yy_penta_evo_pair_uses_exact_horizontal_path_mirrors() -> None:
    board = json.loads((YY_PENTA_EVO_ROOT / "board.json").read_text(encoding="utf-8"))
    holds = {hold["id"]: hold for hold in board["holds"]}

    for prefix in ("edge-25", "edge-20", "edge-15", "edge-10", "mono", "duo", "tray"):
        left = holds[f"{prefix}-left"]["geometry"][0]
        right = holds[f"{prefix}-right"]["geometry"][0]
        _assert_global_paths_are_horizontal_mirrors(left, right)
