from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Sequence, Union
import hashlib

import numpy as np

try:
    from ..pipeline.run_simulation import run_full_pipeline
    from .chromosome_utils import decode_chromosome
except ImportError:  # pragma: no cover
    from pipeline.run_simulation import run_full_pipeline
    from chromosome_utils import decode_chromosome

PathLike = Union[str, Path]


@dataclass
class FitnessConfig:
    base_plant_json: PathLike
    helios_ini_template: PathLike
    helios_build_dir: PathLike
    work_dir: PathLike
    row_spacing_m: float = 0.762
    plant_spacing_m: float = 0.1524
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    utc_offset: Optional[int] = None
    executable_name: str = "par_parallel"
    shell_command_prefix: Optional[str] = None
    n_leaves: int = 12
    n_parallel_slots: int = 8
    n_gpus: int = 4
    slots_per_gpu: int = 2
    fail_fitness: float = 0.0

    def __post_init__(self):
        self.base_plant_json = Path(self.base_plant_json)
        self.helios_ini_template = Path(self.helios_ini_template)
        self.helios_build_dir = Path(self.helios_build_dir)
        self.work_dir = Path(self.work_dir)
        self.work_dir.mkdir(parents=True, exist_ok=True)



def _slot_id_from_chromosome_index(chromosome_idx: int, n_parallel_slots: int) -> int:
    if n_parallel_slots <= 0:
        raise ValueError("n_parallel_slots must be >= 1")
    return chromosome_idx % n_parallel_slots



def _gpu_id_from_slot_id(slot_id: int, n_gpus: int, slots_per_gpu: int) -> int:
    if n_gpus <= 0:
        raise ValueError("n_gpus must be >= 1")
    if slots_per_gpu <= 0:
        raise ValueError("slots_per_gpu must be >= 1")
    return min(slot_id // slots_per_gpu, n_gpus - 1)



def _unique_eval_stem(ga_instance, chromosome_idx: int, chromosome: Sequence[float]) -> str:
    generation = getattr(ga_instance, "generations_completed", 0)
    digest = hashlib.sha1(np.asarray(chromosome, dtype=np.float64).tobytes()).hexdigest()[:10]
    return f"chromosome_{generation}_{chromosome_idx}_{digest}"



def evaluate_chromosome(
    ga_instance,
    chromosome: Sequence[float],
    chromosome_idx: int,
    config: FitnessConfig,
) -> float:
    try:
        traits = decode_chromosome(chromosome, n_leaves=config.n_leaves)
        slot_id = _slot_id_from_chromosome_index(chromosome_idx, config.n_parallel_slots)
        gpu_id = _gpu_id_from_slot_id(slot_id, config.n_gpus, config.slots_per_gpu)
        eval_stem = _unique_eval_stem(ga_instance, chromosome_idx, chromosome)

        eval_dir = config.work_dir / f"slot_{slot_id}"
        meshes_dir = eval_dir / "meshes"
        configs_dir = eval_dir / "configs"
        meshes_dir.mkdir(parents=True, exist_ok=True)
        configs_dir.mkdir(parents=True, exist_ok=True)

        plant_obj_output = meshes_dir / f"{eval_stem}.obj"
        field_obj_output = meshes_dir / f"{eval_stem}_field_cropped.obj"
        helios_ini_output = configs_dir / f"{eval_stem}.ini"
        rotation_log_csv = eval_dir / "rotation_info.csv"

        result = run_full_pipeline(
            base_plant_json=config.base_plant_json,
            lengths=traits["lengths"],
            widths=traits["widths"],
            theta=traits["theta"],
            phi=traits["phi"],
            plant_obj_output=plant_obj_output,
            field_obj_output=field_obj_output,
            row_spacing_m=config.row_spacing_m,
            plant_spacing_m=config.plant_spacing_m,
            helios_ini_template=config.helios_ini_template,
            helios_ini_output=helios_ini_output,
            helios_build_dir=config.helios_build_dir,
            latitude=config.latitude,
            longitude=config.longitude,
            utc_offset=config.utc_offset,
            rotation_log_csv=rotation_log_csv,
            executable_name=config.executable_name,
            cuda_visible_device=gpu_id,
            shell_command_prefix=config.shell_command_prefix,
        )

        par_value = result["par_value_stdout"]
        print(f"Chromosome Index: {chromosome_idx}, PAR Value: {par_value}, GPU: {gpu_id}")

        if par_value is None:
            print(f"Chromosome Index: {chromosome_idx}, PAR is None, returning {config.fail_fitness}")
            return float(config.fail_fitness)
        if np.isnan(par_value):
            print(f"PAR is NaN for chromosome index {chromosome_idx}, returning {config.fail_fitness}")
            return float(config.fail_fitness)
        return float(par_value)

    except Exception as exc:
        print(f"Error in fitness function for chromosome index {chromosome_idx}: {exc}")
        return float(config.fail_fitness)


class HeliosFitnessEvaluator:
    def __init__(self, config: FitnessConfig):
        self.config = config

    def __call__(self, ga_instance, chromosome, chromosome_idx) -> float:
        return evaluate_chromosome(
            ga_instance=ga_instance,
            chromosome=chromosome,
            chromosome_idx=chromosome_idx,
            config=self.config,
        )
