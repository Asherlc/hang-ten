from copy import deepcopy
import pytest
from conftest import load_board_catalog_module


def cord():
    return {"type": "cadRoutedCord", "bodyNodeID": "wood",
            "strands": [{"id": "visible-lead", "kind": "lead", "restLength": .4,
                         "radius": .002, "material": "neutralRope", "provenance": "displayEstimate"}],
            "anchor": {"offsetFromBoardBounds": [0, .2, 0], "visibility": "invisible", "provenance": "displayEstimate"},
            "canonicalPoses": {"primary": {"rotation": [0,0,0,1], "translation": [0,0,0],
                 "camera": {"viewDirection": [0,0,-1], "fitPadding": .08},
                 "wrappedRoutes": {"visible-lead": [[0,1,.004], [0,.99,.004], [0,.98,.004]]}}}}


def test_native_route_does_not_require_an_unevidenced_second_loop():
    module = load_board_catalog_module()
    result = module._load_model_suspension(cord(), "cord")
    assert len(result.strands) == 1
    assert result.strands[0].kind == "lead"
    assert result.body_node_id == "wood"


@pytest.mark.parametrize("mutation", ["missing-cache", "extra-cache", "duplicate-strand", "unknown-kind"])
def test_native_route_rejects_inconsistent_cache_topology(mutation):
    value = cord()
    if mutation == "missing-cache": del value["canonicalPoses"]["primary"]["wrappedRoutes"]
    elif mutation == "extra-cache": value["canonicalPoses"]["primary"]["wrappedRoutes"]["invented"] = [[0,0,0],[0,1,0],[0,2,0]]
    elif mutation == "duplicate-strand": value["strands"].append(deepcopy(value["strands"][0]))
    else: value["strands"][0]["kind"] = "hidden-channel"
    with pytest.raises(ValueError):
        load_board_catalog_module()._load_model_suspension(value, "cord")
