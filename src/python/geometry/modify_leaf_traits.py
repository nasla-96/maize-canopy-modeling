from __future__ import annotations

from pathlib import Path
from typing import Iterable, Sequence, Union
import copy

from geomdl import BSpline, operations, utilities, multi
from geomdl.operations import rotate

try:
    from .load_plant import export_surface_container_obj
except ImportError:  # allows running the file directly during early refactoring
    from load_plant import export_surface_container_obj

PathLike = Union[str, Path]


# These defaults reflect the control-point layout used in your notebook.
DEFAULT_LENGTH_ANCHORS = (0, 6, 12)
DEFAULT_WIDTH_ANCHORS = (1,)



def calculate_curve_length(ctrlpts: Sequence[Sequence[float]]) -> float:
    """Length of the degree-3 midrib control-point curve."""
    curve = BSpline.Curve()
    curve.degree = 3
    curve.ctrlpts = [list(pt) for pt in ctrlpts]
    curve.knotvector = utilities.generate_knot_vector(curve.degree, curve.ctrlpts_size)
    curve.delta = 0.01
    return operations.length_curve(curve)



def calculate_curve_width(ctrlpts: Sequence[Sequence[float]]) -> float:
    """Length of the degree-2 width control-point curve."""
    curve = BSpline.Curve()
    curve.degree = 2
    curve.ctrlpts = [list(pt) for pt in ctrlpts]
    curve.knotvector = utilities.generate_knot_vector(curve.degree, curve.ctrlpts_size)
    curve.delta = 0.01
    return operations.length_curve(curve)



def scale_length(
    points: Sequence[Sequence[float]],
    multiplier: float,
    exclude_indices: Iterable[int] = DEFAULT_LENGTH_ANCHORS,
    inplace: bool = False,
):
    """Scale leaf length by stretching x coordinates except anchor points."""
    exclude_indices = set(exclude_indices)
    pts = points if inplace else copy.deepcopy(list(points))

    for idx, pt in enumerate(pts):
        if idx not in exclude_indices:
            pt[0] *= multiplier
    return pts



def scale_width(
    points: Sequence[Sequence[float]],
    multiplier: float,
    exclude_indices: Iterable[int] = DEFAULT_WIDTH_ANCHORS,
    inplace: bool = False,
):
    """Scale leaf width by stretching y coordinates except anchor points."""
    exclude_indices = set(exclude_indices)
    pts = points if inplace else copy.deepcopy(list(points))

    for idx, pt in enumerate(pts):
        if idx not in exclude_indices:
            pt[1] *= multiplier
    return pts



def _reshape_ctrlpts_into_v_sets(ctrlpts, n_ctrlpts_per_row: int = 6):
    return [ctrlpts[i : i + n_ctrlpts_per_row] for i in range(0, len(ctrlpts), n_ctrlpts_per_row)]



def modify_leaf_surface(
    surface_data,
    target_length: float,
    target_width: float,
    z_rotation_deg: float,
    y_rotation_deg: float,
):
    """
    Apply the same per-leaf logic you used in the notebook:
    1. estimate current length from ctrlpts[6:12]
    2. scale length
    3. estimate current width from the j=2 cross-section
    4. scale width across j=1..4 cross-sections
    5. rotate about y and z
    """
    initial_len = calculate_curve_length(surface_data.ctrlpts[6:12])
    length_scale = target_length / initial_len
    surface_data.ctrlpts = scale_length(surface_data.ctrlpts, length_scale, inplace=False)

    v_dir_sets = _reshape_ctrlpts_into_v_sets(surface_data.ctrlpts, n_ctrlpts_per_row=6)
    initial_width = calculate_curve_width([v_dir_set[2] for v_dir_set in v_dir_sets])
    width_scale = target_width / initial_width

    for j in range(1, 5):
        curve_control_points = [v_dir_set[j] for v_dir_set in v_dir_sets]
        scaled_width_ctrlpts = scale_width(curve_control_points, width_scale, inplace=False)

        for k, v_dir_set in enumerate(v_dir_sets):
            v_dir_set[j] = scaled_width_ctrlpts[k]

    rotate(surface_data, angle=y_rotation_deg, axis=1, inplace=True)
    rotate(surface_data, angle=z_rotation_deg, axis=2, inplace=True)
    return surface_data



def apply_leaf_traits_to_plant(
    surface_container: multi.SurfaceContainer,
    lengths: Sequence[float],
    widths: Sequence[float],
    theta: Sequence[float],
    phi: Sequence[float],
    skip_stalk: bool = True,
):
    """Modify each leaf surface in a plant surface container."""
    leaf_surfaces = list(surface_container[1:] if skip_stalk else surface_container)

    n_leaves = len(leaf_surfaces)
    for name, arr in {
        "lengths": lengths,
        "widths": widths,
        "theta": theta,
        "phi": phi,
    }.items():
        if len(arr) != n_leaves:
            raise ValueError(f"Expected {n_leaves} values for {name}, got {len(arr)}")

    for idx, surface_data in enumerate(leaf_surfaces):
        modify_leaf_surface(
            surface_data=surface_data,
            target_length=float(lengths[idx]),
            target_width=float(widths[idx]),
            z_rotation_deg=float(theta[idx]),
            y_rotation_deg=float(phi[idx]),
        )

    return surface_container



def create_modified_plant_obj(
    surface_container: multi.SurfaceContainer,
    lengths: Sequence[float],
    widths: Sequence[float],
    theta: Sequence[float],
    phi: Sequence[float],
    output_path: PathLike,
    skip_stalk: bool = True,
):
    """Apply leaf traits and export the resulting plant to OBJ."""
    apply_leaf_traits_to_plant(
        surface_container=surface_container,
        lengths=lengths,
        widths=widths,
        theta=theta,
        phi=phi,
        skip_stalk=skip_stalk,
    )
    return export_surface_container_obj(surface_container, output_path)
