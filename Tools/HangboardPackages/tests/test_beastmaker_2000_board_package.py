from __future__ import annotations

from collections import Counter
from pathlib import Path

import pytest
from PIL import Image

from hangboard_packages.board_catalog import load_board_package
from _board_package_helpers import presentation_frame


REPO_ROOT = Path(__file__).resolve().parents[3]
PACKAGE_ROOT = REPO_ROOT / "Hangboards" / "beastmaker-2000"
EXPECTED_HOLDS = (
    *(f"top-sloper-{index}" for index in range(1, 5)),
    *(f"front-upper-{index}" for index in range(1, 3)),
    *(f"front-middle-{index}" for index in range(1, 10)),
    *(f"front-lower-{index}" for index in range(1, 10)),
    "hold-26",
    "hold-27",
    "hold-28",
)
EXPECTED_KINDS = {
    **{f"top-sloper-{index}": "sloper" for index in range(1, 5)},
    "front-upper-1": "pocket",
    "front-upper-2": "pocket",
    "front-middle-1": "pocket",
    "front-middle-2": "pocket",
    "front-middle-3": "pocket",
    "front-middle-4": "pocket",
    "front-middle-5": "pocket",
    "front-middle-6": "pocket",
    "front-middle-7": "pocket",
    "front-middle-8": "pocket",
    "front-middle-9": "pocket",
    "front-lower-1": "edge",
    "front-lower-2": "pocket",
    "front-lower-3": "pocket",
    "front-lower-4": "pocket",
    "front-lower-5": "pocket",
    "front-lower-6": "pocket",
    "front-lower-7": "pocket",
    "front-lower-8": "pocket",
    "front-lower-9": "pocket",
    "hold-26": "pocket",
    "hold-27": "pocket",
    "hold-28": "sloper",
}
MIRRORED_PAIRS = (
    ("front-upper-1", "front-upper-2"),
    ("front-middle-1", "front-middle-9"),
    ("front-middle-3", "front-middle-7"),
    ("front-middle-4", "front-middle-6"),
    *((f"front-lower-{left}", f"front-lower-{10 - left}") for left in range(1, 5)),
)
EXPECTED_CENTERED_HOLDS = ("front-middle-5", "front-lower-5")
EXPECTED_GEOMETRY = {
    "top-sloper-1": (
        {
            "frame": {"x": 0.014629589102, "y": 0.047655822695, "width": 0.172863552774, "height": 0.274613035461},
            "commands": (
                {"command": "move", "to": (0.028979607547, 0.295207314029)},
                {"command": "line", "to": (0.0, 1.0)},
                {"command": "line", "to": (0.958346130114, 1.0)},
                {"command": "curve", "control1": (0.981483757254, 0.658141102381), "control2": (0.990741878627, 0.328834032043), "to": (1.0, 0.029251289719)},
                {"command": "curve", "control1": (0.817766227674, 0.010330442285), "control2": (0.410408856015, 0.0), "to": (0.206730171606, 0.0)},
                {"command": "quad", "control": (0.040189540897, 0.047458418471), "to": (0.028979607547, 0.295207314029)},
                {"command": "close"},
            ),
        },
    ),
    "top-sloper-2": (
        {
            "frame": {"x": 0.187023215513, "y": 0.050057242908, "width": 0.162238559647, "height": 0.178935179078},
            "commands": (
                {"command": "move", "to": (0.939532052574, 0.09213210961)},
                {"command": "line", "to": (1.0, 0.985345004041)},
                {"command": "line", "to": (0.0, 1.0)},
                {"command": "curve", "control1": (0.00376946019, 0.719387080236), "control2": (0.024901084316, 0.273467339162), "to": (0.02362166629, 0.0)},
                {"command": "close"},
            ),
        },
    ),
    "top-sloper-3": (
        {
            "frame": {"x": 0.349578893471, "y": 0.04670416844, "width": 0.303753336279, "height": 0.130851707447},
            "commands": (
                {"command": "move", "to": (0.0, 0.0)},
                {"command": "line", "to": (1.0, 0.0)},
                {"command": "line", "to": (1.0, 1.0)},
                {"command": "line", "to": (0.0, 1.0)},
                {"command": "close"},
            ),
        },
    ),
    "top-sloper-4": (
        {
            "frame": {"x": 0.654208482081, "y": 0.055499205674, "width": 0.160575659794, "height": 0.167778682624},
            "commands": (
                {"command": "move", "to": (0.985193071569, 0.004033418433)},
                {"command": "curve", "control1": (0.989880548176, 0.186278683977), "control2": (1.0, 0.651262300681), "to": (1.0, 1.0)},
                {"command": "line", "to": (0.0, 1.0)},
                {"command": "line", "to": (0.034839841495, 0.0)},
                {"command": "close"},
            ),
        },
    ),
    "front-upper-1": (
        {
            "frame": {"x": 0.381443579774, "y": 0.198581716312, "width": 0.102110656848, "height": 0.15248287234},
            "commands": (
                {"command": "move", "to": (0.20673217493, 0.0)},
                {"command": "line", "to": (0.79326782507, 0.0)},
                {"command": "curve", "control1": (0.907442851953, 0.0), "control2": (1.0, 0.223857626609), "to": (1.0, 0.5)},
                {"command": "curve", "control1": (1.0, 0.776142373391), "control2": (0.907442851953, 1.0), "to": (0.79326782507, 1.0)},
                {"command": "line", "to": (0.20673217493, 1.0)},
                {"command": "curve", "control1": (0.092557148047, 1.0), "control2": (0.0, 0.776142373391), "to": (0.0, 0.5)},
                {"command": "curve", "control1": (0.0, 0.223857626609), "control2": (0.092557148047, 0.0), "to": (0.20673217493, 0.0)},
                {"command": "close"},
            ),
        },
    ),
    "front-upper-2": (
        {
            "frame": {"x": 0.519882189494, "y": 0.198581716312, "width": 0.102110656848, "height": 0.15248287234},
            "commands": (
                {"command": "move", "to": (0.20673217493, 0.0)},
                {"command": "line", "to": (0.79326782507, 0.0)},
                {"command": "curve", "control1": (0.907442851953, 0.0), "control2": (1.0, 0.223857626609), "to": (1.0, 0.5)},
                {"command": "curve", "control1": (1.0, 0.776142373391), "control2": (0.907442851953, 1.0), "to": (0.79326782507, 1.0)},
                {"command": "line", "to": (0.20673217493, 1.0)},
                {"command": "curve", "control1": (0.092557148047, 1.0), "control2": (0.0, 0.776142373391), "to": (0.0, 0.5)},
                {"command": "curve", "control1": (0.0, 0.223857626609), "control2": (0.092557148047, 0.0), "to": (0.20673217493, 0.0)},
                {"command": "close"},
            ),
        },
    ),
    "front-middle-1": (
        {
            "frame": {"x": 0.027737058419, "y": 0.423758553191, "width": 0.136229290133, "height": 0.140070893617},
            "commands": (
                {"command": "move", "to": (0.142342793632, 0.0)},
                {"command": "line", "to": (0.857657206368, 0.0)},
                {"command": "curve", "control1": (0.936270959818, 0.0), "control2": (1.0, 0.223857627617), "to": (1.0, 0.5)},
                {"command": "curve", "control1": (1.0, 0.776142372383), "control2": (0.936270959818, 1.0), "to": (0.857657206368, 1.0)},
                {"command": "line", "to": (0.142342793632, 1.0)},
                {"command": "curve", "control1": (0.063729040182, 1.0), "control2": (0.0, 0.776142372383), "to": (0.0, 0.5)},
                {"command": "curve", "control1": (0.0, 0.223857627617), "control2": (0.063729040182, 0.0), "to": (0.142342793632, 0.0)},
                {"command": "close"},
            ),
        },
    ),
    "front-middle-2": (
        {
            "frame": {"x": 0.178015699067, "y": 0.401338083333, "width": 0.037622596465, "height": 0.135881611702},
            "commands": (
                {"command": "move", "to": (0.499999993476, 0.0)},
                {"command": "curve", "control1": (0.77614237592, 0.0), "control2": (1.0, 0.22385762408), "to": (1.0, 0.500000006524)},
                {"command": "curve", "control1": (1.0, 0.77614237592), "control2": (0.77614237592, 1.0), "to": (0.499999993476, 1.0)},
                {"command": "curve", "control1": (0.22385762408, 1.0), "control2": (0.0, 0.77614237592), "to": (0.0, 0.500000006524)},
                {"command": "curve", "control1": (0.0, 0.22385762408), "control2": (0.22385762408, 0.0), "to": (0.499999993476, 0.0)},
                {"command": "close"},
            ),
        },
    ),
    "front-middle-3": (
        {
            "frame": {"x": 0.231958372116, "y": 0.420213007092, "width": 0.080264836524, "height": 0.141843666667},
            "commands": (
                {"command": "move", "to": (0.244648582107, 0.0)},
                {"command": "line", "to": (0.755351417893, 0.0)},
                {"command": "curve", "control1": (0.89046709582, 0.0), "control2": (1.0, 0.223857631294), "to": (1.0, 0.5)},
                {"command": "curve", "control1": (1.0, 0.776142368706), "control2": (0.89046709582, 1.0), "to": (0.755351417893, 1.0)},
                {"command": "line", "to": (0.244648582107, 1.0)},
                {"command": "curve", "control1": (0.10953290418, 1.0), "control2": (0.0, 0.776142368706), "to": (0.0, 0.5)},
                {"command": "curve", "control1": (0.0, 0.223857631294), "control2": (0.10953290418, 0.0), "to": (0.244648582107, 0.0)},
                {"command": "close"},
            ),
        },
    ),
    "front-middle-4": (
        {
            "frame": {"x": 0.33186077565, "y": 0.421985780142, "width": 0.076582992636, "height": 0.141843666667},
            "commands": (
                {"command": "move", "to": (0.256410434912, 0.0)},
                {"command": "line", "to": (0.743589565088, 0.0)},
                {"command": "curve", "control1": (0.885201134803, 0.0), "control2": (1.0, 0.223857631294), "to": (1.0, 0.5)},
                {"command": "curve", "control1": (1.0, 0.776142368706), "control2": (0.885201134803, 1.0), "to": (0.743589565088, 1.0)},
                {"command": "line", "to": (0.256410434912, 1.0)},
                {"command": "curve", "control1": (0.114798865197, 1.0), "control2": (0.0, 0.776142368706), "to": (0.0, 0.5)},
                {"command": "curve", "control1": (0.0, 0.223857631294), "control2": (0.114798865197, 0.0), "to": (0.256410434912, 0.0)},
                {"command": "close"},
            ),
        },
    ),
    "front-middle-5": (
        {
            "frame": {"x": 0.429552793324, "y": 0.423758553191, "width": 0.144329773196, "height": 0.140070893617},
            "commands": (
                {"command": "move", "to": (0.134353829446, 0.0)},
                {"command": "line", "to": (0.865646170554, 0.0)},
                {"command": "curve", "control1": (0.939847740958, 0.0), "control2": (1.0, 0.223857627617), "to": (1.0, 0.5)},
                {"command": "curve", "control1": (1.0, 0.776142372383), "control2": (0.939847740958, 1.0), "to": (0.865646170554, 1.0)},
                {"command": "line", "to": (0.134353829446, 1.0)},
                {"command": "curve", "control1": (0.060152259042, 1.0), "control2": (0.0, 0.776142372383), "to": (0.0, 0.5)},
                {"command": "curve", "control1": (0.0, 0.223857627617), "control2": (0.060152259042, 0.0), "to": (0.134353829446, 0.0)},
                {"command": "close"},
            ),
        },
    ),
    "front-middle-6": (
        {
            "frame": {"x": 0.59499265783, "y": 0.421985780142, "width": 0.076582992636, "height": 0.141843666667},
            "commands": (
                {"command": "move", "to": (0.256410434912, 0.0)},
                {"command": "line", "to": (0.743589565088, 0.0)},
                {"command": "curve", "control1": (0.885201134803, 0.0), "control2": (1.0, 0.223857631294), "to": (1.0, 0.5)},
                {"command": "curve", "control1": (1.0, 0.776142368706), "control2": (0.885201134803, 1.0), "to": (0.743589565088, 1.0)},
                {"command": "line", "to": (0.256410434912, 1.0)},
                {"command": "curve", "control1": (0.114798865197, 1.0), "control2": (0.0, 0.776142368706), "to": (0.0, 0.5)},
                {"command": "curve", "control1": (0.0, 0.223857631294), "control2": (0.114798865197, 0.0), "to": (0.256410434912, 0.0)},
                {"command": "close"},
            ),
        },
    ),
    "front-middle-7": (
        {
            "frame": {"x": 0.691213217477, "y": 0.420213007092, "width": 0.080264836524, "height": 0.141843666667},
            "commands": (
                {"command": "move", "to": (0.244648582107, 0.0)},
                {"command": "line", "to": (0.755351417893, 0.0)},
                {"command": "curve", "control1": (0.89046709582, 0.0), "control2": (1.0, 0.223857631294), "to": (1.0, 0.5)},
                {"command": "curve", "control1": (1.0, 0.776142368706), "control2": (0.89046709582, 1.0), "to": (0.755351417893, 1.0)},
                {"command": "line", "to": (0.244648582107, 1.0)},
                {"command": "curve", "control1": (0.10953290418, 1.0), "control2": (0.0, 0.776142368706), "to": (0.0, 0.5)},
                {"command": "curve", "control1": (0.0, 0.223857631294), "control2": (0.10953290418, 0.0), "to": (0.244648582107, 0.0)},
                {"command": "close"},
            ),
        },
    ),
    "front-middle-8": (
        {
            "frame": {"x": 0.783717668139, "y": 0.39566208156, "width": 0.039417755032, "height": 0.142365189716},
            "commands": (
                {"command": "move", "to": (0.500000006227, 0.0)},
                {"command": "curve", "control1": (0.776142384396, 0.0), "control2": (1.0, 0.223857628058), "to": (1.0, 0.500000006227)},
                {"command": "curve", "control1": (1.0, 0.776142384396), "control2": (0.776142384396, 1.0), "to": (0.500000006227, 1.0)},
                {"command": "curve", "control1": (0.223857628058, 1.0), "control2": (0.0, 0.776142384396), "to": (0.0, 0.500000006227)},
                {"command": "curve", "control1": (0.0, 0.223857628058), "control2": (0.223857628058, 0.0), "to": (0.500000006227, 0.0)},
                {"command": "close"},
            ),
        },
    ),
    "front-middle-9": (
        {
            "frame": {"x": 0.839470077565, "y": 0.423758553191, "width": 0.136229290133, "height": 0.140070893617},
            "commands": (
                {"command": "move", "to": (0.142342793632, 0.0)},
                {"command": "line", "to": (0.857657206368, 0.0)},
                {"command": "curve", "control1": (0.936270959818, 0.0), "control2": (1.0, 0.223857627617), "to": (1.0, 0.5)},
                {"command": "curve", "control1": (1.0, 0.776142372383), "control2": (0.936270959818, 1.0), "to": (0.857657206368, 1.0)},
                {"command": "line", "to": (0.142342793632, 1.0)},
                {"command": "curve", "control1": (0.063729040182, 1.0), "control2": (0.0, 0.776142372383), "to": (0.0, 0.5)},
                {"command": "curve", "control1": (0.0, 0.223857627617), "control2": (0.063729040182, 0.0), "to": (0.142342793632, 0.0)},
                {"command": "close"},
            ),
        },
    ),
    "front-lower-1": (
        {
            "frame": {"x": 0.030191621011, "y": 0.702127567376, "width": 0.137702880707, "height": 0.13297851773},
            "commands": (
                {"command": "move", "to": (0.133689266762, 0.0)},
                {"command": "line", "to": (0.866310733238, 0.0)},
                {"command": "curve", "control1": (0.94014527618, 0.0), "control2": (1.0, 0.223857626233), "to": (1.0, 0.5)},
                {"command": "curve", "control1": (1.0, 0.776142373767), "control2": (0.94014527618, 1.0), "to": (0.866310733238, 1.0)},
                {"command": "line", "to": (0.133689266762, 1.0)},
                {"command": "curve", "control1": (0.05985472382, 1.0), "control2": (0.0, 0.776142373767), "to": (0.0, 0.5)},
                {"command": "curve", "control1": (0.0, 0.223857626233), "control2": (0.05985472382, 0.0), "to": (0.133689266762, 0.0)},
                {"command": "close"},
            ),
        },
    ),
    "front-lower-2": (
        {
            "frame": {"x": 0.181394595974, "y": 0.699025535461, "width": 0.039027758468, "height": 0.140956638298},
            "commands": (
                {"command": "move", "to": (0.5, 0.0)},
                {"command": "curve", "control1": (0.776142376364, 0.0), "control2": (1.0, 0.223857623636), "to": (1.0, 0.5)},
                {"command": "curve", "control1": (1.0, 0.776142376364), "control2": (0.776142376364, 1.0), "to": (0.5, 1.0)},
                {"command": "curve", "control1": (0.223857623636, 1.0), "control2": (0.0, 0.776142376364), "to": (0.0, 0.5)},
                {"command": "curve", "control1": (0.0, 0.223857623636), "control2": (0.223857623636, 0.0), "to": (0.5, 0.0)},
                {"command": "close"},
            ),
        },
    ),
    "front-lower-3": (
        {
            "frame": {"x": 0.233922448699, "y": 0.702127567376, "width": 0.078547069219, "height": 0.136525347518},
            "commands": (
                {"command": "move", "to": (0.240625353515, 0.0)},
                {"command": "line", "to": (0.759374646485, 0.0)},
                {"command": "curve", "control1": (0.892268362113, 0.0), "control2": (1.0, 0.223857619976), "to": (1.0, 0.5)},
                {"command": "curve", "control1": (1.0, 0.776142380024), "control2": (0.892268362113, 1.0), "to": (0.759374646485, 1.0)},
                {"command": "line", "to": (0.240625353515, 1.0)},
                {"command": "curve", "control1": (0.107731637887, 1.0), "control2": (0.0, 0.776142380024), "to": (0.0, 0.5)},
                {"command": "curve", "control1": (0.0, 0.223857619976), "control2": (0.107731637887, 0.0), "to": (0.240625353515, 0.0)},
                {"command": "close"},
            ),
        },
    ),
    "front-lower-4": (
        {
            "frame": {"x": 0.327196893471, "y": 0.703900340426, "width": 0.075847263623, "height": 0.131205744681},
            "commands": (
                {"command": "move", "to": (0.239480972263, 0.0)},
                {"command": "line", "to": (0.760519027737, 0.0)},
                {"command": "curve", "control1": (0.892780717955, 0.0), "control2": (1.0, 0.223857622239), "to": (1.0, 0.5)},
                {"command": "curve", "control1": (1.0, 0.776142377761), "control2": (0.892780717955, 1.0), "to": (0.760519027737, 1.0)},
                {"command": "line", "to": (0.239480972263, 1.0)},
                {"command": "curve", "control1": (0.107219282045, 1.0), "control2": (0.0, 0.776142377761), "to": (0.0, 0.5)},
                {"command": "curve", "control1": (0.0, 0.223857622239), "control2": (0.107219282045, 0.0), "to": (0.239480972263, 0.0)},
                {"command": "close"},
            ),
        },
    ),
    "front-lower-5": (
        {
            "frame": {"x": 0.416299008346, "y": 0.695035191489, "width": 0.1708394757, "height": 0.148936042553},
            "commands": (
                {"command": "move", "to": (0.120689547562, 0.0)},
                {"command": "line", "to": (0.879310452438, 0.0)},
                {"command": "curve", "control1": (0.945965450139, 0.0), "control2": (1.0, 0.223857620449), "to": (1.0, 0.5)},
                {"command": "curve", "control1": (1.0, 0.776142379551), "control2": (0.945965450139, 1.0), "to": (0.879310452438, 1.0)},
                {"command": "line", "to": (0.120689547562, 1.0)},
                {"command": "curve", "control1": (0.054034549861, 1.0), "control2": (0.0, 0.776142379551), "to": (0.0, 0.5)},
                {"command": "curve", "control1": (0.0, 0.223857620449), "control2": (0.054034549861, 0.0), "to": (0.120689547562, 0.0)},
                {"command": "close"},
            ),
        },
    ),
    "front-lower-6": (
        {
            "frame": {"x": 0.600392269023, "y": 0.703900340426, "width": 0.075847263623, "height": 0.131205744681},
            "commands": (
                {"command": "move", "to": (0.239480972263, 0.0)},
                {"command": "line", "to": (0.760519027737, 0.0)},
                {"command": "curve", "control1": (0.892780717955, 0.0), "control2": (1.0, 0.223857622239), "to": (1.0, 0.5)},
                {"command": "curve", "control1": (1.0, 0.776142377761), "control2": (0.892780717955, 1.0), "to": (0.760519027737, 1.0)},
                {"command": "line", "to": (0.239480972263, 1.0)},
                {"command": "curve", "control1": (0.107219282045, 1.0), "control2": (0.0, 0.776142377761), "to": (0.0, 0.5)},
                {"command": "curve", "control1": (0.0, 0.223857622239), "control2": (0.107219282045, 0.0), "to": (0.239480972263, 0.0)},
                {"command": "close"},
            ),
        },
    ),
    "front-lower-7": (
        {
            "frame": {"x": 0.690966908198, "y": 0.702127567376, "width": 0.078547069219, "height": 0.136525347518},
            "commands": (
                {"command": "move", "to": (0.240625353515, 0.0)},
                {"command": "line", "to": (0.759374646485, 0.0)},
                {"command": "curve", "control1": (0.892268362113, 0.0), "control2": (1.0, 0.223857619976), "to": (1.0, 0.5)},
                {"command": "curve", "control1": (1.0, 0.776142380024), "control2": (0.892268362113, 1.0), "to": (0.759374646485, 1.0)},
                {"command": "line", "to": (0.240625353515, 1.0)},
                {"command": "curve", "control1": (0.107731637887, 1.0), "control2": (0.0, 0.776142380024), "to": (0.0, 0.5)},
                {"command": "curve", "control1": (0.0, 0.223857619976), "control2": (0.107731637887, 0.0), "to": (0.240625353515, 0.0)},
                {"command": "close"},
            ),
        },
    ),
    "front-lower-8": (
        {
            "frame": {"x": 0.783014071674, "y": 0.699025535461, "width": 0.039027758468, "height": 0.140956638298},
            "commands": (
                {"command": "move", "to": (0.5, 0.0)},
                {"command": "curve", "control1": (0.776142376364, 0.0), "control2": (1.0, 0.223857623636), "to": (1.0, 0.5)},
                {"command": "curve", "control1": (1.0, 0.776142376364), "control2": (0.776142376364, 1.0), "to": (0.5, 1.0)},
                {"command": "curve", "control1": (0.223857623636, 1.0), "control2": (0.0, 0.776142376364), "to": (0.0, 0.5)},
                {"command": "curve", "control1": (0.0, 0.223857623636), "control2": (0.223857623636, 0.0), "to": (0.5, 0.0)},
                {"command": "close"},
            ),
        },
    ),
    "front-lower-9": (
        {
            "frame": {"x": 0.835541924399, "y": 0.702127567376, "width": 0.137702880707, "height": 0.13297851773},
            "commands": (
                {"command": "move", "to": (0.133689266762, 0.0)},
                {"command": "line", "to": (0.866310733238, 0.0)},
                {"command": "curve", "control1": (0.94014527618, 0.0), "control2": (1.0, 0.223857626233), "to": (1.0, 0.5)},
                {"command": "curve", "control1": (1.0, 0.776142373767), "control2": (0.94014527618, 1.0), "to": (0.866310733238, 1.0)},
                {"command": "line", "to": (0.133689266762, 1.0)},
                {"command": "curve", "control1": (0.05985472382, 1.0), "control2": (0.0, 0.776142373767), "to": (0.0, 0.5)},
                {"command": "curve", "control1": (0.0, 0.223857626233), "control2": (0.05985472382, 0.0), "to": (0.133689266762, 0.0)},
                {"command": "close"},
            ),
        },
    ),
    "hold-26": (
        {
            "frame": {"x": 0.272901686303, "y": 0.433486560284, "width": 0.035999528228, "height": 0.130019572695},
            "commands": (
                {"command": "move", "to": (0.499999993182, 0.0)},
                {"command": "curve", "control1": (0.77614236449, 0.0), "control2": (1.0, 0.223857621873), "to": (1.0, 0.499999993182)},
                {"command": "curve", "control1": (1.0, 0.77614236449), "control2": (0.77614236449, 1.0), "to": (0.499999993182, 1.0)},
                {"command": "curve", "control1": (0.223857621873, 1.0), "control2": (0.0, 0.77614236449), "to": (0.0, 0.499999993182)},
                {"command": "curve", "control1": (0.0, 0.223857621873), "control2": (0.223857621873, 0.0), "to": (0.499999993182, 0.0)},
                {"command": "close"},
            ),
        },
    ),
    "hold-27": (
        {
            "frame": {"x": 0.689424222386, "y": 0.419279948582, "width": 0.03870462052, "height": 0.139789560284},
            "commands": (
                {"command": "move", "to": (0.5, 0.0)},
                {"command": "curve", "control1": (0.776142373176, 0.0), "control2": (1.0, 0.223857626824), "to": (1.0, 0.5)},
                {"command": "curve", "control1": (1.0, 0.776142373176), "control2": (0.776142373176, 1.0), "to": (0.5, 1.0)},
                {"command": "curve", "control1": (0.223857626824, 1.0), "control2": (0.0, 0.776142373176), "to": (0.0, 0.5)},
                {"command": "curve", "control1": (0.0, 0.223857626824), "control2": (0.223857626824, 0.0), "to": (0.5, 0.0)},
                {"command": "close"},
            ),
        },
    ),
    "hold-28": (
        {
            "frame": {"x": 0.812506858125, "y": 0.047655822695, "width": 0.172863552774, "height": 0.274613035461},
            "commands": (
                {"command": "move", "to": (0.971020392453, 0.295207314029)},
                {"command": "line", "to": (1.0, 1.0)},
                {"command": "line", "to": (0.041653869886, 1.0)},
                {"command": "curve", "control1": (0.018516242746, 0.658141102381), "control2": (0.009258121373, 0.328834032043), "to": (0.0, 0.029251289719)},
                {"command": "curve", "control1": (0.182233772326, 0.010330442285), "control2": (0.589591143985, 0.0), "to": (0.793269828394, 0.0)},
                {"command": "quad", "control": (0.959810459103, 0.047458418471), "to": (0.971020392453, 0.295207314029)},
                {"command": "close"},
            ),
        },
    ),
}


def _serialize_geometry(hold: object) -> tuple[dict[str, object], ...]:
    return tuple(_serialize_piece(piece) for piece in hold.geometry)


def _serialize_piece(piece: object) -> dict[str, object]:
    return {
        "frame": {
            "x": piece.frame.x,
            "y": piece.frame.y,
            "width": piece.frame.width,
            "height": piece.frame.height,
        },
        "commands": tuple(_serialize_command(command) for command in piece.shape.commands),
    }


def _serialize_shape(piece: object) -> tuple[dict[str, object], ...]:
    return tuple(_serialize_command(command) for command in piece.shape.commands)


def _serialize_command(command: object) -> dict[str, object]:
    serialized: dict[str, object] = {"command": command.command}
    for key in ("to", "control", "control1", "control2"):
        value = getattr(command, key)
        if value is not None:
            serialized[key] = tuple(value)
    return serialized


def test_beastmaker_2000_inventory_shapes_and_symmetry() -> None:
    board = load_board_package(PACKAGE_ROOT).board
    holds = {hold.id: hold for hold in board.holds}
    with Image.open(PACKAGE_ROOT / board.presentation_asset_path) as image:
        presentation_size = image.size

    assert tuple(holds) == EXPECTED_HOLDS
    assert {hold_id: hold.kind for hold_id, hold in holds.items()} == EXPECTED_KINDS
    assert Counter(hold.kind for hold in holds.values()) == {
        "sloper": 5,
        "edge": 1,
        "pocket": 21,
    }

    rounded_rect_holds = {
        hold.id
        for hold in holds.values()
        if hold.geometry[0].shape.type == "roundedRect"
    }
    assert rounded_rect_holds == set()

    for hold in holds.values():
        assert len(hold.geometry) == 1
        piece = hold.geometry[0]
        assert piece.shape.type == "path"
        assert piece.shape.commands[0].command == "move"
        assert piece.shape.commands[-1].command == "close"
        assert len(piece.shape.commands) >= 5
        assert 0 <= piece.frame.x < piece.frame.x + piece.frame.width <= 1
        assert 0 <= piece.frame.y < piece.frame.y + piece.frame.height <= 1

    assert {hold.id: _serialize_geometry(hold) for hold in board.holds} == EXPECTED_GEOMETRY

    symmetry_axis_x: float | None = None
    for left_id, right_id in MIRRORED_PAIRS:
        left_x, left_y, left_width, left_height = presentation_frame(
            holds[left_id].frame, presentation_size
        )
        right_x, right_y, right_width, right_height = presentation_frame(
            holds[right_id].frame, presentation_size
        )
        assert right_y == pytest.approx(left_y, abs=1e-6)
        assert right_width == pytest.approx(left_width, abs=1e-6)
        assert right_height == pytest.approx(left_height, abs=1e-6)
        assert _serialize_shape(holds[left_id].geometry[0]) == _serialize_shape(
            holds[right_id].geometry[0]
        )
        pair_axis_x = (left_x + left_width + right_x) / 2
        if symmetry_axis_x is None:
            symmetry_axis_x = pair_axis_x
        else:
            assert pair_axis_x == pytest.approx(symmetry_axis_x, abs=1e-6)

    assert symmetry_axis_x is not None
    for hold_id in EXPECTED_CENTERED_HOLDS:
        hold_x, _, hold_width, _ = presentation_frame(holds[hold_id].frame, presentation_size)
        hold_axis_x = hold_x + hold_width / 2
        assert hold_axis_x == pytest.approx(symmetry_axis_x, abs=2e-3)
    assert 0 < symmetry_axis_x < presentation_size[0]
