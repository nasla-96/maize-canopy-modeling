from __future__ import annotations

from pathlib import Path
from typing import Iterable, Union
import copy

from geomdl import exchange, multi

PathLike = Union[str, Path]


def load_surface_container(json_path: PathLike) -> multi.SurfaceContainer:
    """Load a maize plant stored as a geomdl JSON surface container."""
    json_path = Path(json_path)
    if not json_path.exists():
        raise FileNotFoundError(f"Plant JSON not found: {json_path}")

    data = exchange.import_json(str(json_path))
    return multi.SurfaceContainer(data)



def clone_surface_container(surface_container: multi.SurfaceContainer) -> multi.SurfaceContainer:
    """Return a deep copy so downstream geometry edits do not mutate the base plant."""
    return copy.deepcopy(surface_container)



def get_leaf_surfaces(
    surface_container: multi.SurfaceContainer,
    skip_stalk: bool = True,
):
    """
    Return plant surfaces as a list.

    By default, surface 0 is treated as the stalk and skipped.
    """
    if skip_stalk:
        return list(surface_container[1:])
    return list(surface_container)



def export_surface_container_obj(
    surface_container: multi.SurfaceContainer,
    output_path: PathLike,
    make_parents: bool = True,
) -> Path:
    """Export a geomdl surface container to OBJ."""
    output_path = Path(output_path)
    if make_parents:
        output_path.parent.mkdir(parents=True, exist_ok=True)

    exchange.export_obj(surface_container, str(output_path))
    return output_path
