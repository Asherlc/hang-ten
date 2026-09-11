"""Focused non-Blender regressions for deterministic USD spec copying."""

from __future__ import annotations

from dataclasses import dataclass, field

import compile_model_package as compiler


@dataclass
class Spec:
    name: str
    path: str
    properties: list["Spec"] = field(default_factory=list)
    nameChildren: list["Spec"] = field(default_factory=list)
    variantSets: dict[str, "VariantSet"] = field(default_factory=dict)

    def ListInfoKeys(self) -> list[str]:
        return []


@dataclass
class Variant:
    name: str
    primSpec: Spec


@dataclass
class VariantSet:
    name: str
    variants: dict[str, Variant]


class DestinationLayer:
    def __init__(self) -> None:
        self.prims: dict[str, Spec] = {}
        self.properties: set[str] = set()


class FakeSdf:
    @staticmethod
    def CreatePrimInLayer(layer: DestinationLayer, path: str) -> Spec:
        prim = Spec(path.rsplit("/", 1)[-1], path)
        layer.prims[path] = prim
        return prim

    @staticmethod
    def CreateVariantInLayer(
        layer: DestinationLayer,
        prim_path: str,
        variant_set_name: str,
        variant_name: str,
    ) -> Variant:
        path = f"{prim_path}{{{variant_set_name}={variant_name}}}"
        prim = Spec(variant_name, path)
        layer.prims[path] = prim
        return Variant(variant_name, prim)

    @staticmethod
    def CopySpec(
        _source_layer: object,
        source_path: str,
        destination_layer: DestinationLayer,
        destination_path: str,
    ) -> bool:
        assert source_path == destination_path
        destination_layer.properties.add(destination_path)
        return True


def test_sorted_usd_copy_preserves_variant_contents() -> None:
    """Catches retaining a variant declaration while dropping its authored specs."""
    variant_path = "/Board{finish=wood}"
    variant_prim = Spec(
        "wood",
        variant_path,
        properties=[Spec("roughness", f"{variant_path}.roughness")],
        nameChildren=[Spec("Inset", f"{variant_path}/Inset")],
    )
    board = Spec(
        "Board",
        "/Board",
        variantSets={
            "finish": VariantSet(
                "finish", {"wood": Variant("wood", variant_prim)}
            )
        },
    )
    destination = DestinationLayer()

    compiler._copy_usd_specs_sorted(FakeSdf, object(), destination, [board])

    assert sorted(destination.prims) == [
        "/Board",
        "/Board{finish=wood}",
        "/Board{finish=wood}/Inset",
    ]
    assert destination.properties == {"/Board{finish=wood}.roughness"}
