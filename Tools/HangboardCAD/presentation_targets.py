"""Resolve the asset pairs authored in a native board's embedded manifest."""
from pathlib import PurePosixPath


def model_targets(board: dict) -> dict[str, tuple[str, str]]:
    targets = {}
    output_names = set()
    for presentation in board.get("presentations", []):
        media = presentation.get("media", {})
        if media.get("type") != "model":
            continue
        names = []
        for key, suffix in (("assetPath", ".usdz"), ("descriptorPath", ".model.json")):
            value = media.get(key)
            path = PurePosixPath(value) if isinstance(value, str) else None
            if path is None or path.as_posix() != value or "\\" in value or "\x00" in value or ":" in value \
                    or len(path.parts) != 2 or path.parts[0] != "assets" or not path.name.endswith(suffix):
                raise ValueError(f"{key} must name a file directly inside assets/")
            if path.name in output_names:
                raise ValueError("native model presentations must have unique output files")
            output_names.add(path.name)
            names.append(path.name)
        identifier = presentation.get("id")
        if not isinstance(identifier, str) or not identifier or identifier in targets:
            raise ValueError("model presentations must have unique IDs")
        targets[identifier] = tuple(names)
    if not targets:
        raise ValueError("native board declares no model presentations")
    return targets


def source_targets(source):
    import use_hangboard_packages  # noqa: F401
    from hangboard_packages import cad_source
    # Select build targets before exports or the generated suspension artifact exist.
    # Staging separately validates and merges descriptor-bound suspension data.
    return model_targets(cad_source.load_board(source))
