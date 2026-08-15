from __future__ import annotations

from collections import Counter
import copy
import hashlib
import json
import math
from pathlib import Path
import struct
import sys

REPO_ROOT = Path(__file__).resolve().parents[3]
WORKBENCH_ROOT = REPO_ROOT / "Tools" / "HangboardWorkbench"
PACKAGE_ROOT = REPO_ROOT / "Hangboards" / "metolius-project"
sys.path.insert(0, str(WORKBENCH_ROOT))

import board_package  # noqa: E402
from board_geometry import display_path_for_shape  # noqa: E402
from board_package import load_board_package  # noqa: E402


SUPPORTED_HOLD_KINDS = frozenset({"jug", "edge", "pocket", "pinch", "sloper"})
EXPECTED_PRIMARY_PNG_SHA256 = (
    "656ee451c5abf01933740468966f26d78af13a8c2ab99d968239c189ba7908ce"
)
AUTHORIZED_CANONICAL_PIECES = frozenset(
    {
        ("pocket-45-three-left", 0),
        ("pocket-45-three-right", 0),
        ("edge-30-left", 0),
        ("edge-30-right", 0),
        ("pocket-40-two-left", 0),
        ("pocket-40-two-right", 0),
        ("pocket-22-three-left", 0),
        ("pocket-22-three-right", 0),
        ("pocket-22-two-left", 0),
        ("pocket-22-two-right", 0),
        ("edge-39-center", 0),
        ("edge-16-center", 0),
    }
)
EXPECTED_SOURCE_PIECE_SHA256 = {
    ("jug-left", 0): "560476d06f75e6052cbf6b204002a5f454ec44acfaf04c9e5609ccb4c4316e42",
    ("jug-left", 1): "91b5fe16c4900e3a10fddfad9a735791a59f320d724b1e782361ec44b395bd36",
    ("jug-left", 2): "a4d396aa2c72c4e130555689d1cc5258a3a34b43712604a2f2f601c0f0f62d61",
    ("jug-left", 3): "cb573cfa6e569cc84b0c9d9a87da6613d5b3689d51cf0a5ceb457c23e6f556f5",
    ("jug-right", 0): "749528c949d7b2203bc3f62cbec8680c7a2cf24aeb6326098d85390ce952b3be",
    ("jug-right", 1): "36c149e332bca839af96c0e2dada1f1b330eb71e07073d01acd49638b31ead2c",
    ("jug-right", 2): "5619ea8ed4677606a332e660b1c9f969c0d15079dc6e03555ac8b2473ba63044",
    ("jug-right", 3): "ec805571d08d301079124163562fa00a7793e9a2647d97de3c0f0bf0360de945",
    ("sloper-flat-left", 0): "5c83be60331c428ba6b01e2ef460264c39f3bb788d266b7143bf64a1a38b6dbc",
    ("sloper-flat-right", 0): "1aaf269c07e9de8e0eed9dc8c49f5cdf8ff959f3f915d4d64cc49f336d4bb1d0",
    ("pocket-45-three-left", 0): "17ed6c06d2f1c3de8c117904a58a93abfa548170998a7856fd2737a94ff51a8d",
    ("pocket-45-three-right", 0): "62cdb92665aa28f6079e4194e256e65deb8b93604888eaedab6ea4348f91a3a6",
    ("edge-30-left", 0): "e4dece64e18de7e1013d53434df0f01148f0687b69e91b7e9e50e828356602c7",
    ("edge-30-right", 0): "2bcf9ffc1b9a747ed9a9fea091a5cd39ffa51b91a6a6f293ef7360a03ebccbd1",
    ("pocket-40-two-left", 0): "35c8c34801ad680e7e932382984a055b0a8aa559385b16d1a6699a5f9b679de8",
    ("pocket-40-two-right", 0): "b236ffd5839de3bebba1a74edb34e10e40f93ace3acc60f71eb51ef61b3b5077",
    ("pocket-22-three-left", 0): "e3ebf11442bcd64eaa6b5bd2b6a6e8cfd137c4b5bb2c1ab46e9b31b2e3421b56",
    ("pocket-22-three-right", 0): "9098be503a17040067414f666b34c1e895aa5e02dd0a8fad9b92f9db48d326c2",
    ("pocket-22-two-left", 0): "161b4ba9002f3005b445dbcf312f20e167cda7d0461474e9850aa87eecac0823",
    ("pocket-22-two-right", 0): "ff57fc7a7aec85407fd52669e65150d5fb10036569ce447fb534b71b6edd2169",
    ("sloper-round-center", 0): "eea6fce349e61960c58928e67d6986c82f2e9ab0fe97d1c535a63859308934ad",
    ("edge-39-center", 0): "8c9c250da69efb62aa4cfc496bd8bac82a92df3e3ebcf6dd2eb4bd24acda4ab6",
    ("edge-16-center", 0): "9920e32aebc5b9feb8dfb0db67bae198ff49d79f065229086c50e336a0fd540d",
}
EXPECTED_SEMANTIC_PROJECTION_SHA256 = (
    "5b4ce25af96bd033995f316b3b5c95c7f2ae116d7c202ec8e189e73bb77260dc"
)
EXPECTED_ABSOLUTE_PATHS = (
    (
        "jug-left",
        0,
        "M 91.6208006679 292.250000026 C 80.000000646 277.455000005 80.000000646 247.864999964 126.483200734 235.759999947 C "
        "184.587200843 224.999999932 268.838001002 224.999999932 318.226401095 233.069999943 C 353.088801161 239.794999953 "
        "364.709601183 264.004999987 370.520001194 292.250000026 C 283.36400103 281.490000011 172.966400821 281.490000011 "
        "91.6208006679 292.250000026 Z",
    ),
    (
        "jug-left",
        1,
        "M 89.366720646 280.382353368 C 81.170840646 297.471765123 80.000000646 325.242059225 84.683360646 347.671912154 C "
        "89.366720646 367.965588613 112.198100646 382.918823899 138.542000646 387.191176838 L 138.542000646 280.382353368 C "
        "119.808560646 288.927059246 102.245960646 288.927059246 89.366720646 280.382353368 Z",
    ),
    (
        "jug-left",
        2,
        "M 314.029999412 280.382353368 L 361.481599419 280.382353368 C 369.39019942 299.607941593 370.51999942 329.514412164 "
        "366.000799419 353.012353328 C 358.092199418 370.101765083 335.496199415 382.918823899 314.029999412 387.191176838 C "
        "325.327999414 350.876176858 325.327999414 310.28882394 314.029999412 280.382353368 Z",
    ),
    (
        "jug-left",
        3,
        "M 136.490000654 341.698529246 C 179.099600782 350.797058587 264.318801037 350.797058587 314.030001186 341.698529246 "
        "C 303.377601154 363.534999664 282.07280109 379.002499544 257.217201016 387.191175951 L 179.099600782 387.191175951 "
        "C 154.244000707 379.002499544 140.040800665 362.62514673 136.490000654 341.698529246 Z",
    ),
    (
        "jug-right",
        0,
        "M 1682.37919933 292.250000026 C 1693.99999935 277.455000005 1693.99999935 247.864999964 1647.51679927 235.759999947 "
        "C 1589.41279916 224.999999932 1505.161999 224.999999932 1455.7735989 233.069999943 C 1420.91119884 239.794999953 "
        "1409.29039882 264.004999987 1403.47999881 292.250000026 C 1490.63599897 281.490000011 1601.03359918 281.490000011 "
        "1682.37919933 292.250000026 Z",
    ),
    (
        "jug-right",
        1,
        "M 1684.63327935 280.382353368 C 1692.82915935 297.471765123 1693.99999935 325.242059225 1689.31663935 347.671912154 "
        "C 1684.63327935 367.965588613 1661.80189935 382.918823899 1635.45799935 387.191176838 L 1635.45799935 280.382353368 "
        "C 1654.19143935 288.927059246 1671.75403935 288.927059246 1684.63327935 280.382353368 Z",
    ),
    (
        "jug-right",
        2,
        "M 1459.97000059 280.382353368 L 1412.51840058 280.382353368 C 1404.60980058 299.607941593 1403.48000058 "
        "329.514412164 1407.99920058 353.012353328 C 1415.90780058 370.101765083 1438.50380058 382.918823899 1459.97000059 "
        "387.191176838 C 1448.67200059 350.876176858 1448.67200059 310.28882394 1459.97000059 280.382353368 Z",
    ),
    (
        "jug-right",
        3,
        "M 1637.50999935 341.698529246 C 1594.90039922 350.797058587 1509.68119896 350.797058587 1459.96999881 341.698529246 "
        "C 1470.62239885 363.534999664 1491.92719891 379.002499544 1516.78279898 387.191175951 L 1594.90039922 387.191175951 "
        "C 1619.75599929 379.002499544 1633.95919934 362.62514673 1637.50999935 341.698529246 Z",
    ),
    (
        "sloper-flat-left",
        0,
        "M 370.520001194 283.388823121 C 403.445601138 270.729999606 441.858801072 265.666470199 485.759600997 265.666470199 "
        "C 557.098400876 263.134705496 611.974400782 260.602940793 644.900000726 260.602940793 L 644.900000726 387.191175951 "
        "L 370.520001194 387.191175951 C 378.75140118 346.6829407 378.75140118 308.706470153 370.520001194 283.388823121 Z",
    ),
    (
        "sloper-flat-right",
        0,
        "M 1403.47999881 283.388823121 C 1370.55439886 270.729999606 1332.14119893 265.666470199 1288.240399 265.666470199 C "
        "1216.90159912 263.134705496 1162.02559922 260.602940793 1129.09999927 260.602940793 L 1129.09999927 387.191175951 L "
        "1403.47999881 387.191175951 C 1395.24859882 346.6829407 1395.24859882 308.706470153 1403.47999881 283.388823121 Z",
    ),
    (
        "pocket-45-three-left",
        0,
        "M 162.798199507 294.860882752 C 146.819599459 299.449706292 139.717999438 309.774559257 139.717999438 318.952206337 "
        "C 139.717999438 330.424265187 153.921199481 340.749118152 171.675199534 344.190735807 C 214.284799661 347.632353462 "
        "274.648399842 344.764338749 292.402399896 339.601912267 C 311.931799954 331.571471072 317.25799997 318.952206337 "
        "310.156399949 308.627353372 C 303.054799927 298.302500407 274.648399842 293.140073925 242.691199747 292.566470982 C "
        "210.733999651 290.845662155 182.327599566 291.419265097 162.798199507 294.860882752 Z",
    ),
    (
        "pocket-45-three-right",
        0,
        "M 1611.20180049 294.860882752 C 1627.18040054 299.449706292 1634.28200056 309.774559257 1634.28200056 318.952206337 "
        "C 1634.28200056 330.424265187 1620.07880052 340.749118152 1602.32480047 344.190735807 C 1559.71520034 347.632353462 "
        "1499.35160016 344.764338749 1481.5976001 339.601912267 C 1462.06820005 331.571471072 1456.74200003 318.952206337 "
        "1463.84360005 308.627353372 C 1470.94520007 298.302500407 1499.35160016 293.140073925 1531.30880025 292.566470982 C "
        "1563.26600035 290.845662155 1591.67240043 291.419265097 1611.20180049 294.860882752 Z",
    ),
    (
        "edge-30-left",
        0,
        "M 211.541000003 402.342205868 C 199.436000039 409.66058821 194.594000054 422.101838192 199.436000039 431.615735237 "
        "C 204.278000025 445.520661688 226.06699996 455.034558733 252.69799988 457.96191167 C 310.801999706 462.352941075 "
        "383.431999488 456.498235201 412.483999401 446.252499922 C 431.851999343 436.738602877 436.693999328 420.638161724 "
        "424.588999364 408.928749976 C 412.483999401 396.487499994 368.905999531 392.096470589 320.485999676 392.828308823 C "
        "267.223999836 392.096470589 228.487999952 395.75566176 211.541000003 402.342205868 Z",
    ),
    (
        "edge-30-right",
        0,
        "M 1562.459 402.342205868 C 1574.56399996 409.66058821 1579.40599995 422.101838192 1574.56399996 431.615735237 C "
        "1569.72199998 445.520661688 1547.93300004 455.034558733 1521.30200012 457.96191167 C 1463.19800029 462.352941075 "
        "1390.56800051 456.498235201 1361.5160006 446.252499922 C 1342.14800066 436.738602877 1337.30600067 420.638161724 "
        "1349.41100064 408.928749976 C 1361.5160006 396.487499994 1405.09400047 392.096470589 1453.51400032 392.828308823 C "
        "1506.77600016 392.096470589 1545.51200005 395.75566176 1562.459 402.342205868 Z",
    ),
    (
        "pocket-40-two-left",
        0,
        "M 494.798000857 394.015073179 C 482.208800756 398.603896719 475.430000702 409.502352626 475.430000702 419.827205591 "
        "C 475.430000702 432.446470326 485.114000779 442.771323291 498.671600888 446.786543889 C 519.976401058 448.507352716 "
        "546.123201267 447.360146831 558.712401368 440.476911521 C 570.333201461 433.020073269 572.270001476 418.679999706 "
        "566.45960143 408.355146741 C 559.680801375 396.883087891 535.470801182 392.294264351 514.166001012 392.867867294 C "
        "506.41880095 392.294264351 499.640000896 392.294264351 494.798000857 394.015073179 Z",
    ),
    (
        "pocket-40-two-right",
        0,
        "M 1279.20199914 394.015073179 C 1291.79119924 398.603896719 1298.5699993 409.502352626 1298.5699993 419.827205591 C "
        "1298.5699993 432.446470326 1288.88599922 442.771323291 1275.32839911 446.786543889 C 1254.02359894 448.507352716 "
        "1227.87679873 447.360146831 1215.28759863 440.476911521 C 1203.66679854 433.020073269 1201.72999852 418.679999706 "
        "1207.54039857 408.355146741 C 1214.31919862 396.883087891 1238.52919882 392.294264351 1259.83399899 392.867867294 C "
        "1267.58119905 392.294264351 1274.3599991 392.294264351 1279.20199914 394.015073179 Z",
    ),
    (
        "pocket-22-three-left",
        0,
        "M 276.004160538 516.54852949 C 259.735040599 523.2735295 254.31200062 538.06852952 257.927360606 548.828529536 C "
        "261.542720593 562.278529554 279.619520524 571.021029567 303.119360435 573.71102957 C 342.888320285 577.073529575 "
        "395.311040086 571.693529567 415.195520011 562.278529554 C 431.46463995 552.863529541 435.079999936 538.06852952 "
        "426.04159997 527.981029506 C 415.195520011 516.54852949 380.849600141 511.841029484 344.696000278 512.513529485 C "
        "313.965440394 511.841029484 288.65792049 513.186029486 276.004160538 516.54852949 Z",
    ),
    (
        "pocket-22-three-right",
        0,
        "M 1497.99583946 516.54852949 C 1514.2649594 523.2735295 1519.68799938 538.06852952 1516.07263939 548.828529536 C "
        "1512.45727941 562.278529554 1494.38047948 571.021029567 1470.88063956 573.71102957 C 1431.11167972 577.073529575 "
        "1378.68895991 571.693529567 1358.80447999 562.278529554 C 1342.53536005 552.863529541 1338.92000006 538.06852952 "
        "1347.95840003 527.981029506 C 1358.80447999 516.54852949 1393.15039986 511.841029484 1429.30399972 512.513529485 C "
        "1460.03455961 511.841029484 1485.34207951 513.186029486 1497.99583946 516.54852949 Z",
    ),
    (
        "pocket-22-two-left",
        0,
        "M 494.798000857 508.933455804 C 482.208800756 513.838749945 475.430000702 525.488823531 475.430000702 536.525735349 "
        "C 475.430000702 550.015294237 485.114000779 561.052206054 498.671600888 565.344338428 C 519.976401058 567.183823731 "
        "546.123201267 565.957500196 558.712401368 558.599558984 C 570.333201461 550.628456004 572.270001476 535.299411813 "
        "566.45960143 524.262499995 C 559.680801375 511.999264643 535.470801182 507.093970501 514.166001012 507.707132269 C "
        "506.41880095 507.093970501 499.640000896 507.093970501 494.798000857 508.933455804 Z",
    ),
    (
        "pocket-22-two-right",
        0,
        "M 1279.20199914 508.933455804 C 1291.79119924 513.838749945 1298.5699993 525.488823531 1298.5699993 536.525735349 "
        "C 1298.5699993 550.015294237 1288.88599922 561.052206054 1275.32839911 565.344338428 C 1254.02359894 567.183823731 "
        "1227.87679873 565.957500196 1215.28759863 558.599558984 C 1203.66679854 550.628456004 1201.72999852 535.299411813 "
        "1207.54039857 524.262499995 C 1214.31919862 511.999264643 1238.52919882 507.093970501 1259.83399899 507.707132269 C "
        "1267.58119905 507.093970501 1274.3599991 507.093970501 1279.20199914 508.933455804 Z",
    ),
    (
        "sloper-round-center",
        0,
        "M 644.900000726 260.563382695 C 765.950000363 256.647059165 1008.04999964 256.647059165 1129.09999927 260.563382695 "
        "L 1129.09999927 387.191176838 C 1008.04999964 379.358529778 765.950000363 379.358529778 644.900000726 387.191176838 "
        "C 654.584000697 345.417059183 654.584000697 295.810294467 644.900000726 260.563382695 Z",
    ),
    (
        "edge-39-center",
        0,
        "M 618.672499962 394.944705751 C 610.198999961 405.48713225 604.54999996 419.273382287 607.37449996 429.815808786 C "
        "610.198999961 447.656838246 624.321499963 459.010220629 644.092999966 462.254044167 C 796.615999987 466.30882359 "
        "977.384000013 466.30882359 1129.90700003 462.254044167 C 1149.67850004 459.010220629 1163.80100004 447.656838246 "
        "1166.62550004 429.815808786 C 1169.45000004 419.273382287 1163.80100004 405.48713225 1155.32750004 394.944705751 C "
        "999.980000016 388.457058675 774.019999984 388.457058675 618.672499962 394.944705751 Z",
    ),
    (
        "edge-16-center",
        0,
        "M 618.672499962 506.975293751 C 610.198999961 516.746323217 604.54999996 529.523823288 607.37449996 539.294852754 C "
        "610.198999961 555.830441081 624.321499963 566.353088199 644.092999966 569.359558804 C 796.615999987 573.11764706 "
        "977.384000013 573.11764706 1129.90700003 569.359558804 C 1149.67850004 566.353088199 1163.80100004 555.830441081 "
        "1166.62550004 539.294852754 C 1169.45000004 529.523823288 1163.80100004 516.746323217 1155.32750004 506.975293751 C "
        "999.980000016 500.962352541 774.019999984 500.962352541 618.672499962 506.975293751 Z",
    ),
)
EXPECTED_BOARD_METADATA = {
    "schemaVersion": 1,
    "id": "metolius.project",
    "manufacturer": "Metolius",
    "name": "Project Training Board",
    "subtitle": "Symmetric training board with pockets, edges, jugs, and slopers.",
    "productURL": "https://www.metoliusclimbing.com/products/project-training-board",
    "dimensions": "622 × 152 mm",
    "aspectRatio": 2.0,
    "presentation": {"assetPath": "assets/primary.png"},
}
EXPECTED_HOLD_METADATA = (
    {"id": "jug-left", "name": "Left outer jug", "kind": "jug", "features": ["jug"]},
    {"id": "jug-right", "name": "Right outer jug", "kind": "jug", "features": ["jug"]},
    {
        "id": "sloper-flat-left",
        "name": "Left 55 mm flat sloper",
        "kind": "sloper",
        "sizeMillimeters": 55,
        "gripType": "sloper",
    },
    {
        "id": "sloper-flat-right",
        "name": "Right 55 mm flat sloper",
        "kind": "sloper",
        "sizeMillimeters": 55,
        "gripType": "sloper",
    },
    {
        "id": "pocket-45-three-left",
        "name": "Left 45 mm three-finger pocket",
        "kind": "pocket",
        "sizeMillimeters": 45,
        "fingerCapacity": 3,
        "gripType": "threeFingerPocket",
        "features": ["pocket", "threeFingerPocket"],
    },
    {
        "id": "pocket-45-three-right",
        "name": "Right 45 mm three-finger pocket",
        "kind": "pocket",
        "sizeMillimeters": 45,
        "fingerCapacity": 3,
        "gripType": "threeFingerPocket",
        "features": ["pocket", "threeFingerPocket"],
    },
    {"id": "edge-30-left", "name": "Left 30 mm edge", "kind": "edge", "sizeMillimeters": 30},
    {"id": "edge-30-right", "name": "Right 30 mm edge", "kind": "edge", "sizeMillimeters": 30},
    {
        "id": "pocket-40-two-left",
        "name": "Left 40 mm two-finger pocket",
        "kind": "pocket",
        "sizeMillimeters": 40,
        "fingerCapacity": 2,
        "gripType": "twoFingerPocket",
        "features": ["pocket", "twoFingerPocket"],
    },
    {
        "id": "pocket-40-two-right",
        "name": "Right 40 mm two-finger pocket",
        "kind": "pocket",
        "sizeMillimeters": 40,
        "fingerCapacity": 2,
        "gripType": "twoFingerPocket",
        "features": ["pocket", "twoFingerPocket"],
    },
    {
        "id": "pocket-22-three-left",
        "name": "Left 22 mm three-finger pocket",
        "kind": "pocket",
        "sizeMillimeters": 22,
        "fingerCapacity": 3,
        "gripType": "threeFingerPocket",
        "features": ["pocket", "threeFingerPocket"],
    },
    {
        "id": "pocket-22-three-right",
        "name": "Right 22 mm three-finger pocket",
        "kind": "pocket",
        "sizeMillimeters": 22,
        "fingerCapacity": 3,
        "gripType": "threeFingerPocket",
        "features": ["pocket", "threeFingerPocket"],
    },
    {
        "id": "pocket-22-two-left",
        "name": "Left 22 mm two-finger pocket",
        "kind": "pocket",
        "sizeMillimeters": 22,
        "fingerCapacity": 2,
        "gripType": "twoFingerPocket",
        "features": ["pocket", "twoFingerPocket"],
    },
    {
        "id": "pocket-22-two-right",
        "name": "Right 22 mm two-finger pocket",
        "kind": "pocket",
        "sizeMillimeters": 22,
        "fingerCapacity": 2,
        "gripType": "twoFingerPocket",
        "features": ["pocket", "twoFingerPocket"],
    },
    {
        "id": "sloper-round-center",
        "name": "Center 53 mm round sloper",
        "kind": "sloper",
        "sizeMillimeters": 53,
        "gripType": "sloper",
        "features": ["roundSloper"],
    },
    {"id": "edge-39-center", "name": "Center 39 mm edge", "kind": "edge", "sizeMillimeters": 39},
    {"id": "edge-16-center", "name": "Center 16 mm edge", "kind": "edge", "sizeMillimeters": 16},
)
EXPECTED_TREATMENTS = (
    ("jug-left", 0, {"type": "surface"}),
    ("jug-left", 1, {"type": "surface"}),
    ("jug-left", 2, {"type": "surface"}),
    ("jug-left", 3, {"type": "surface"}),
    ("jug-right", 0, {"type": "surface"}),
    ("jug-right", 1, {"type": "surface"}),
    ("jug-right", 2, {"type": "surface"}),
    ("jug-right", 3, {"type": "surface"}),
    ("sloper-flat-left", 0, {"type": "surface"}),
    ("sloper-flat-right", 0, {"type": "surface"}),
    ("pocket-45-three-left", 0, {"type": "recess", "rimInsetFraction": 0.12, "depth": "deep"}),
    ("pocket-45-three-right", 0, {"type": "recess", "rimInsetFraction": 0.12, "depth": "deep"}),
    ("edge-30-left", 0, {"type": "recess", "rimInsetFraction": 0.1, "depth": "deep"}),
    ("edge-30-right", 0, {"type": "recess", "rimInsetFraction": 0.1, "depth": "deep"}),
    ("pocket-40-two-left", 0, {"type": "recess", "rimInsetFraction": 0.12, "depth": "deep"}),
    ("pocket-40-two-right", 0, {"type": "recess", "rimInsetFraction": 0.12, "depth": "deep"}),
    ("pocket-22-three-left", 0, {"type": "recess", "rimInsetFraction": 0.1, "depth": "shallow"}),
    ("pocket-22-three-right", 0, {"type": "recess", "rimInsetFraction": 0.1, "depth": "shallow"}),
    ("pocket-22-two-left", 0, {"type": "recess", "rimInsetFraction": 0.1, "depth": "shallow"}),
    ("pocket-22-two-right", 0, {"type": "recess", "rimInsetFraction": 0.1, "depth": "shallow"}),
    ("sloper-round-center", 0, {"type": "surface"}),
    ("edge-39-center", 0, {"type": "recess", "rimInsetFraction": 0.08, "depth": "deep"}),
    ("edge-16-center", 0, {"type": "recess", "rimInsetFraction": 0.08, "depth": "shallow"}),
)
EXPECTED_HOLDS = (
    ("jug-left", "jug", None, None),
    ("jug-right", "jug", None, None),
    ("sloper-flat-left", "sloper", 55, None),
    ("sloper-flat-right", "sloper", 55, None),
    ("pocket-45-three-left", "pocket", 45, 3),
    ("pocket-45-three-right", "pocket", 45, 3),
    ("edge-30-left", "edge", 30, None),
    ("edge-30-right", "edge", 30, None),
    ("pocket-40-two-left", "pocket", 40, 2),
    ("pocket-40-two-right", "pocket", 40, 2),
    ("pocket-22-three-left", "pocket", 22, 3),
    ("pocket-22-three-right", "pocket", 22, 3),
    ("pocket-22-two-left", "pocket", 22, 2),
    ("pocket-22-two-right", "pocket", 22, 2),
    ("sloper-round-center", "sloper", 53, None),
    ("edge-39-center", "edge", 39, None),
    ("edge-16-center", "edge", 16, None),
)
MIRRORED_PAIRS = (
    ("jug-left", "jug-right"),
    ("sloper-flat-left", "sloper-flat-right"),
    ("pocket-45-three-left", "pocket-45-three-right"),
    ("edge-30-left", "edge-30-right"),
    ("pocket-40-two-left", "pocket-40-two-right"),
    ("pocket-22-three-left", "pocket-22-three-right"),
    ("pocket-22-two-left", "pocket-22-two-right"),
)
EXPECTED_PIXEL_FRAMES = {
    "jug-left": (
        (80.0, 225.0, 290.52, 67.25),
        (80.0, 280.382353, 58.542, 106.808824),
        (314.03, 280.382353, 56.49, 106.808824),
        (136.49, 341.698529, 177.54, 45.492647),
    ),
    "jug-right": (
        (1403.48, 225.0, 290.52, 67.25),
        (1635.458, 280.382353, 58.542, 106.808824),
        (1403.48, 280.382353, 56.49, 106.808824),
        (1459.97, 341.698529, 177.54, 45.492647),
    ),
    "sloper-flat-left": ((370.52, 260.602941, 274.38, 126.588235),),
    "sloper-flat-right": ((1129.10, 260.602941, 274.38, 126.588235),),
    "pocket-45-three-left": ((139.718, 290.845662, 177.54, 56.786691),),
    "pocket-45-three-right": ((1456.742, 290.845662, 177.54, 56.786691),),
    "edge-30-left": ((194.594, 392.096471, 242.10, 70.256470),),
    "edge-30-right": ((1337.306, 392.096471, 242.10, 70.256470),),
    "pocket-40-two-left": ((475.43, 392.294264, 96.84, 56.213088),),
    "pocket-40-two-right": ((1201.73, 392.294264, 96.84, 56.213088),),
    "pocket-22-three-left": ((254.312, 511.841029, 180.768, 65.232500),),
    "pocket-22-three-right": ((1338.92, 511.841029, 180.768, 65.232500),),
    "pocket-22-two-left": ((475.43, 507.093971, 96.84, 60.089853),),
    "pocket-22-two-right": ((1201.73, 507.093971, 96.84, 60.089853),),
    "sloper-round-center": ((644.90, 256.647059, 484.20, 130.544118),),
    "edge-39-center": ((604.55, 388.457059, 564.90, 77.851765),),
    "edge-16-center": ((604.55, 500.962353, 564.90, 72.155295),),
}


def _png_dimensions(path: Path) -> tuple[int, int]:
    payload = path.read_bytes()
    assert payload[:8] == b"\x89PNG\r\n\x1a\n"
    assert payload[12:16] == b"IHDR"
    return struct.unpack(">II", payload[16:24])


def _points(command: dict[str, object]) -> tuple[tuple[float, float], ...]:
    return tuple(
        tuple(point)
        for key in ("to", "control", "control1", "control2")
        if (point := command.get(key)) is not None
    )


def _json_sha256(value: object) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    return hashlib.sha256(payload).hexdigest()


def _absolute_paths(
    document: dict[str, object], width: int, height: int
) -> tuple[tuple[str, int, str], ...]:
    paths: list[tuple[str, int, str]] = []
    for hold in document["holds"]:
        for piece_index, piece in enumerate(hold["geometry"]):
            label = f'{hold["id"]}.geometry[{piece_index}]'
            path = display_path_for_shape(
                piece["frame"], piece["shape"], width, height, label=label
            )
            paths.append((hold["id"], piece_index, path.data))
    return tuple(paths)


def _raw_piece_hashes(document: dict[str, object]) -> dict[tuple[str, int], str]:
    return {
        (hold["id"], piece_index): _json_sha256(piece)
        for hold in document["holds"]
        for piece_index, piece in enumerate(hold["geometry"])
    }


def _semantic_projection(
    document: dict[str, object], paths: tuple[tuple[str, int, str], ...]
) -> dict[str, object]:
    projection = copy.deepcopy(document)
    absolute_paths = {(hold_id, piece_index): path for hold_id, piece_index, path in paths}
    for hold in projection["holds"]:
        for piece_index, piece in enumerate(hold["geometry"]):
            replacement = {
                key: value
                for key, value in piece.items()
                if key not in {"frame", "shape"}
            }
            replacement["absolutePath"] = absolute_paths[(hold["id"], piece_index)]
            hold["geometry"][piece_index] = replacement
    return projection


def test_metolius_project_preserves_audited_inventory_and_mirrored_contacts() -> None:
    package = load_board_package(PACKAGE_ROOT)
    board = package.board
    holds = {hold["id"]: hold for hold in board["holds"]}
    raw_document = json.loads((PACKAGE_ROOT / "board.json").read_text())
    presentation_size = _png_dimensions(PACKAGE_ROOT / "assets" / "primary.png")
    absolute_paths = _absolute_paths(raw_document, *presentation_size)
    raw_piece_hashes = _raw_piece_hashes(raw_document)

    assert absolute_paths == EXPECTED_ABSOLUTE_PATHS
    assert raw_piece_hashes.keys() == EXPECTED_SOURCE_PIECE_SHA256.keys()
    changed_piece_keys = frozenset(
        key
        for key, source_hash in EXPECTED_SOURCE_PIECE_SHA256.items()
        if raw_piece_hashes[key] != source_hash
    )
    assert len(changed_piece_keys) == 12
    assert changed_piece_keys == AUTHORIZED_CANONICAL_PIECES
    assert {key: value for key, value in raw_document.items() if key != "holds"} == (
        EXPECTED_BOARD_METADATA
    )
    assert tuple(
        {key: value for key, value in hold.items() if key != "geometry"}
        for hold in raw_document["holds"]
    ) == EXPECTED_HOLD_METADATA
    assert tuple(
        (hold["id"], piece_index, piece.get("treatment"))
        for hold in raw_document["holds"]
        for piece_index, piece in enumerate(hold["geometry"])
    ) == EXPECTED_TREATMENTS
    assert (
        _json_sha256(_semantic_projection(raw_document, absolute_paths))
        == EXPECTED_SEMANTIC_PROJECTION_SHA256
    )

    assert (
        hashlib.sha256(
            (PACKAGE_ROOT / "assets" / "primary.png").read_bytes()
        ).hexdigest()
        == EXPECTED_PRIMARY_PNG_SHA256
    )
    assert {path.name for path in PACKAGE_ROOT.iterdir()} == {"board.json", "assets"}
    assert {path.name for path in (PACKAGE_ROOT / "assets").iterdir()} == {"primary.png"}
    assert board["id"] == "metolius.project"
    assert board["manufacturer"] == "Metolius"
    assert board["name"] == "Project Training Board"
    assert board["dimensions"] == "622 × 152 mm"
    assert board["aspectRatio"] == 2.0
    assert board["presentation"] == {"assetPath": "assets/primary.png"}
    assert presentation_size == (1774, 887)
    assert math.isclose(
        presentation_size[0] / presentation_size[1],
        board["aspectRatio"],
        rel_tol=0.001,
    )
    assert tuple(
        (
            hold["id"],
            hold["kind"],
            hold.get("sizeMillimeters"),
            hold.get("fingerCapacity"),
        )
        for hold in board["holds"]
    ) == EXPECTED_HOLDS
    assert board_package._HOLD_KINDS == SUPPORTED_HOLD_KINDS
    assert Counter(hold["kind"] for hold in board["holds"]) == {
        "pocket": 8,
        "edge": 4,
        "sloper": 3,
        "jug": 2,
    }

    for hold in board["holds"]:
        for piece in hold["geometry"]:
            frame = piece["frame"]
            commands = piece["shape"]["commands"]
            assert piece["shape"]["type"] == "path"
            assert commands[0]["command"] == "move"
            assert commands[-1]["command"] == "close"
            assert any(command["command"] == "curve" for command in commands)
            assert 0 <= frame["x"] < frame["x"] + frame["width"] <= 1
            assert 0 <= frame["y"] < frame["y"] + frame["height"] <= 1
            assert frame["width"] * frame["height"] > 0
            points = [point for command in commands for point in _points(command)]
            assert math.isclose(min(point[0] for point in points), 0.0, abs_tol=5e-7)
            assert math.isclose(min(point[1] for point in points), 0.0, abs_tol=5e-7)
            assert math.isclose(max(point[0] for point in points), 1.0, abs_tol=5e-7)
            assert math.isclose(max(point[1] for point in points), 1.0, abs_tol=5e-7)

        # Canonical Workbench coordinates are normalized to the complete
        # presentation image, including its intentional padding. A cropped
        # inner-board coordinate system would shift every path on package open.
        for piece, expected in zip(
            hold["geometry"],
            EXPECTED_PIXEL_FRAMES[hold["id"]],
            strict=True,
        ):
            frame = piece["frame"]
            actual = (
                frame["x"] * presentation_size[0],
                frame["y"] * presentation_size[1],
                frame["width"] * presentation_size[0],
                frame["height"] * presentation_size[1],
            )
            assert all(
                math.isclose(value, target, abs_tol=0.001)
                for value, target in zip(actual, expected, strict=True)
            )

    for left_id, right_id in MIRRORED_PAIRS:
        left_pieces = holds[left_id]["geometry"]
        right_pieces = holds[right_id]["geometry"]
        assert len(left_pieces) == len(right_pieces)
        for left, right in zip(left_pieces, right_pieces, strict=True):
            left_frame = left["frame"]
            right_frame = right["frame"]
            assert math.isclose(
                right_frame["x"],
                1 - left_frame["x"] - left_frame["width"],
                abs_tol=5e-10,
            )
            assert math.isclose(right_frame["y"], left_frame["y"], abs_tol=5e-10)
            assert math.isclose(
                right_frame["width"], left_frame["width"], abs_tol=5e-10
            )
            assert math.isclose(
                right_frame["height"], left_frame["height"], abs_tol=5e-10
            )
            assert right.get("treatment") == left.get("treatment")
            for left_command, right_command in zip(
                left["shape"]["commands"], right["shape"]["commands"], strict=True
            ):
                assert left_command["command"] == right_command["command"]
                for (left_x, left_y), (right_x, right_y) in zip(
                    _points(left_command), _points(right_command), strict=True
                ):
                    assert math.isclose(right_x, 1 - left_x, abs_tol=5e-10)
                    assert math.isclose(right_y, left_y, abs_tol=5e-10)

    assert len(holds["jug-left"]["geometry"]) == 4
    assert len(holds["jug-right"]["geometry"]) == 4
    assert all(len(holds[hold_id]["geometry"]) == 1 for hold_id in (
        "sloper-flat-left", "sloper-flat-right", "sloper-round-center",
        "pocket-45-three-left", "pocket-45-three-right",
        "edge-30-left", "edge-30-right",
        "pocket-40-two-left", "pocket-40-two-right",
        "pocket-22-three-left", "pocket-22-three-right",
        "pocket-22-two-left", "pocket-22-two-right",
        "edge-39-center", "edge-16-center",
    ))

    top_ids = (
        "jug-left", "sloper-flat-left", "sloper-round-center",
        "sloper-flat-right", "jug-right",
    )
    for left_id, right_id in zip(top_ids, top_ids[1:]):
        left_frame = package.hold_frame(left_id)
        right_frame = package.hold_frame(right_id)
        assert math.isclose(
            left_frame.x + left_frame.width,
            right_frame.x,
            abs_tol=1e-12,
        )

    assert holds["jug-left"]["features"] == ["jug"]
    assert holds["jug-right"]["features"] == ["jug"]
    assert holds["sloper-round-center"]["features"] == ["roundSloper"]
    assert all(holds[hold_id]["gripType"] == "sloper" for hold_id in (
        "sloper-flat-left", "sloper-flat-right", "sloper-round-center",
    ))
    assert all("depthRangeMillimeters" not in hold for hold in board["holds"])

    forbidden_keys = {"cueStyle", "semantics", "evidence", "claims", "ui"}

    def keys(value: object) -> set[str]:
        if isinstance(value, dict):
            return set(value).union(*(keys(item) for item in value.values()))
        if isinstance(value, list):
            return set().union(*(keys(item) for item in value))
        return set()

    assert forbidden_keys.isdisjoint(keys(raw_document))
