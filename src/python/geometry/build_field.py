from __future__ import annotations

from pathlib import Path
from typing import Optional, Tuple, Union
import copy
import csv
import random

import numpy as np
import open3d as o3d

PathLike = Union[str, Path]



def build_field(
    plant_obj_path: PathLike,
    row_spacing_m: float,
    plant_spacing_m: float,
    grid_shape: Tuple[int, int] = (6, 6),
    rotation_range_deg: Tuple[float, float] = (-10.0, 10.0),
    crop_half_width_rows: int = 2,
    crop_half_width_plants: int = 2,
    unit_scale_to_m: float = 0.01,
    center_single_plant: bool = True,
    seed: Optional[int] = 42,
    rotation_log_csv: Optional[PathLike] = None,
    overwrite_input_obj: bool = True,
    output_path: Optional[PathLike] = None,
):
    """
    Tile a single plant OBJ into a field, apply small random z-rotations,
    and crop the central region.

    This preserves your current notebook behavior but moves the hard-coded
    paths into parameters.
    """
    plant_obj_path = Path(plant_obj_path)
    if not plant_obj_path.exists():
        raise FileNotFoundError(f"Plant OBJ not found: {plant_obj_path}")

    rng = random.Random(seed)
    mesh = o3d.io.read_triangle_mesh(str(plant_obj_path))
    if mesh.is_empty():
        raise ValueError(f"Could not read mesh from {plant_obj_path}")

    mesh.scale(unit_scale_to_m, center=mesh.get_center())
    if center_single_plant:
        mesh.translate(-mesh.get_center())
    if overwrite_input_obj:
        o3d.io.write_triangle_mesh(str(plant_obj_path), mesh)

    n_rows, n_plants = grid_shape
    row_offsets = range(-(n_rows // 2), n_rows // 2)
    plant_offsets = range(-(n_plants // 2), n_plants // 2)

    field = o3d.geometry.TriangleMesh()
    rotation_angles = []

    for i in plant_offsets:
        for j in row_offsets:
            cloned_mesh = copy.deepcopy(mesh)
            rotation_angle = rng.uniform(*rotation_range_deg)
            rotation_radians = np.radians(rotation_angle)
            rotation_matrix = cloned_mesh.get_rotation_matrix_from_axis_angle(
                [0.0, 0.0, rotation_radians]
            )
            cloned_mesh.rotate(rotation_matrix, center=(0.0, 0.0, 0.0))
            cloned_mesh.translate(np.array([i * plant_spacing_m, j * row_spacing_m, 0.0]), relative=True)
            field += cloned_mesh
            rotation_angles.append(rotation_angle)

    field.translate((-0.5 * plant_spacing_m, 0.5 * row_spacing_m, 0.0))

    cropped_field = field.crop(
        o3d.geometry.AxisAlignedBoundingBox(
            min_bound=(-crop_half_width_plants * plant_spacing_m, -crop_half_width_rows * row_spacing_m, -np.inf),
            max_bound=(crop_half_width_plants * plant_spacing_m, crop_half_width_rows * row_spacing_m, np.inf),
        )
    )

    if rotation_log_csv is not None:
        rotation_log_csv = Path(rotation_log_csv)
        rotation_log_csv.parent.mkdir(parents=True, exist_ok=True)
        with open(rotation_log_csv, mode="a", newline="") as csv_file:
            csv.writer(csv_file).writerow([str(plant_obj_path)] + rotation_angles)

    if output_path is None:
        output_path = plant_obj_path.with_name(f"{plant_obj_path.stem}_field_cropped.obj")
    else:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

    o3d.io.write_triangle_mesh(str(output_path), cropped_field)
    return output_path


# Example usage
# file_path = "GA_rotate30/meshes/chromosome_97_64.obj"
# row_spacing = 0.00762
# plant_spacing = 0.001524
# output_filepath = create_field(file_path, row_spacing, plant_spacing)

# output_filepath