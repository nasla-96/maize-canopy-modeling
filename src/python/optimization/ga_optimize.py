from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional, Union
import argparse
import json
import time

import numpy as np
import pandas as pd

try:
    import pygad
except ImportError as exc:  # pragma: no cover
    raise ImportError("pygad is required for ga_optimize.py") from exc

try:
    from .chromosome_utils import DEFAULT_N_LEAVES, gene_labels, make_gene_space
    from .fitness import FitnessConfig, HeliosFitnessEvaluator
except ImportError:  # pragma: no cover
    from chromosome_utils import DEFAULT_N_LEAVES, gene_labels, make_gene_space
    from fitness import FitnessConfig, HeliosFitnessEvaluator

PathLike = Union[str, Path]


@dataclass
class GAConfig:
    num_generations: int = 100
    num_parents_mating: int = 50
    sol_per_pop: int = 100
    mutation_percent_genes: int = 5
    random_seed: int = 42
    n_parallel_processes: int = 8
    stop_criteria: tuple[str, ...] = ("saturate_15",)
    n_leaves: int = DEFAULT_N_LEAVES
    keep_parents: int = 0
    keep_elitism: Optional[int] = None


class GenerationLogger:
    def __init__(self):
        self.last_fitness = 0.0

    def __call__(self, ga_instance):
        print(f"Generation = {ga_instance.generations_completed}")
        pop_fitness = np.nan_to_num(ga_instance.last_generation_fitness, nan=0.0)
        if pop_fitness.size > 0:
            _, best_solution_fitness, _ = ga_instance.best_solution(pop_fitness=pop_fitness)
            print(f"Fitness    = {best_solution_fitness}")
            print(f"Change     = {best_solution_fitness - self.last_fitness}")
            self.last_fitness = float(best_solution_fitness)
        else:
            print("Warning: Population fitness array is empty!")
            self.last_fitness = 0.0



def build_ga_instance(ga_config: GAConfig, evaluator: HeliosFitnessEvaluator) -> pygad.GA:
    kwargs = dict(
        sol_per_pop=ga_config.sol_per_pop,
        num_genes=4 * ga_config.n_leaves,
        gene_type=float,
        num_generations=ga_config.num_generations,
        num_parents_mating=ga_config.num_parents_mating,
        fitness_func=evaluator,
        parent_selection_type="tournament",
        K_tournament=3,
        keep_parents=ga_config.keep_parents,
        crossover_type="uniform",
        mutation_type="random",
        mutation_percent_genes=ga_config.mutation_percent_genes,
        mutation_by_replacement=True,
        gene_space=make_gene_space(n_leaves=ga_config.n_leaves),
        on_generation=GenerationLogger(),
        save_best_solutions=True,
        save_solutions=True,
        parallel_processing=["process", ga_config.n_parallel_processes],
        stop_criteria=list(ga_config.stop_criteria),
        random_seed=ga_config.random_seed,
    )
    if ga_config.keep_elitism is not None:
        kwargs["keep_elitism"] = ga_config.keep_elitism
    return pygad.GA(**kwargs)



def save_ga_outputs(
    ga_instance: pygad.GA,
    output_dir: PathLike,
    ga_config: GAConfig,
    fitness_config: FitnessConfig,
) -> dict[str, Path]:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    paths = {
        "best_solutions_csv": output_dir / "best_solutions.csv",
        "solutions_csv": output_dir / "solutions.csv",
        "best_fitness_csv": output_dir / "best_solutions_fitness.csv",
        "best_solution_json": output_dir / "best_solution.json",
        "ga_instance_file": output_dir / "ga_instance",
        "fitness_plot_png": output_dir / "fitness.png",
        "run_config_json": output_dir / "run_config.json",
    }

    pd.DataFrame(ga_instance.best_solutions, columns=gene_labels(ga_config.n_leaves)).to_csv(paths["best_solutions_csv"], index=False)
    pd.DataFrame(ga_instance.solutions, columns=gene_labels(ga_config.n_leaves)).to_csv(paths["solutions_csv"], index=False)
    pd.DataFrame({"fitness": ga_instance.best_solutions_fitness}).to_csv(paths["best_fitness_csv"], index=False)

    solution, solution_fitness, solution_idx = ga_instance.best_solution(ga_instance.last_generation_fitness)
    best_payload = {
        "solution_idx": int(solution_idx) if solution_idx is not None else None,
        "solution_fitness": float(solution_fitness),
        "solution": [float(x) for x in solution],
    }
    paths["best_solution_json"].write_text(json.dumps(best_payload, indent=2), encoding="utf-8")

    ga_instance.save(filename=str(paths["ga_instance_file"]))

    try:
        ga_instance.plot_fitness(save_dir=str(output_dir))
    except Exception as exc:
        print(f"Warning: could not save fitness plot: {exc}")

    config_payload = {
        "ga_config": asdict(ga_config),
        "fitness_config": {
            "base_plant_json": str(fitness_config.base_plant_json),
            "helios_ini_template": str(fitness_config.helios_ini_template),
            "helios_build_dir": str(fitness_config.helios_build_dir),
            "work_dir": str(fitness_config.work_dir),
            "row_spacing_m": fitness_config.row_spacing_m,
            "plant_spacing_m": fitness_config.plant_spacing_m,
            "latitude": fitness_config.latitude,
            "longitude": fitness_config.longitude,
            "utc_offset": fitness_config.utc_offset,
            "executable_name": fitness_config.executable_name,
            "shell_command_prefix": fitness_config.shell_command_prefix,
            "n_leaves": fitness_config.n_leaves,
            "n_parallel_slots": fitness_config.n_parallel_slots,
            "n_gpus": fitness_config.n_gpus,
            "slots_per_gpu": fitness_config.slots_per_gpu,
            "fail_fitness": fitness_config.fail_fitness,
        },
    }
    paths["run_config_json"].write_text(json.dumps(config_payload, indent=2), encoding="utf-8")
    return paths



def run_ga_optimization(
    ga_config: GAConfig,
    fitness_config: FitnessConfig,
    output_dir: PathLike,
) -> dict[str, object]:
    evaluator = HeliosFitnessEvaluator(fitness_config)
    ga_instance = build_ga_instance(ga_config, evaluator)

    t1 = time.time()
    ga_instance.run()
    t2 = time.time()

    output_paths = save_ga_outputs(
        ga_instance=ga_instance,
        output_dir=output_dir,
        ga_config=ga_config,
        fitness_config=fitness_config,
    )

    solution, solution_fitness, solution_idx = ga_instance.best_solution(ga_instance.last_generation_fitness)
    return {
        "runtime_seconds": t2 - t1,
        "best_solution": solution,
        "best_solution_fitness": solution_fitness,
        "best_solution_idx": solution_idx,
        "output_paths": output_paths,
    }



def main():
    parser = argparse.ArgumentParser(description="Run GA optimization for maize canopy PAR using Helios.")
    parser.add_argument("--base-plant-json", required=True)
    parser.add_argument("--helios-ini-template", required=True)
    parser.add_argument("--helios-build-dir", required=True)
    parser.add_argument("--work-dir", required=True, help="Intermediate files for per-evaluation OBJs/INIs/logs.")
    parser.add_argument("--output-dir", required=True, help="Final GA outputs: CSVs, plots, saved GA instance.")
    parser.add_argument("--row-spacing-m", type=float, default=0.762)
    parser.add_argument("--plant-spacing-m", type=float, default=0.1524)
    parser.add_argument("--latitude", type=float)
    parser.add_argument("--longitude", type=float)
    parser.add_argument("--utc-offset", type=int)
    parser.add_argument("--num-generations", type=int, default=100)
    parser.add_argument("--num-parents-mating", type=int, default=50)
    parser.add_argument("--sol-per-pop", type=int, default=100)
    parser.add_argument("--mutation-percent-genes", type=int, default=5)
    parser.add_argument("--random-seed", type=int, default=42)
    parser.add_argument("--n-parallel-processes", type=int, default=8)
    parser.add_argument("--n-leaves", type=int, default=DEFAULT_N_LEAVES)
    parser.add_argument("--n-gpus", type=int, default=4)
    parser.add_argument("--slots-per-gpu", type=int, default=2)
    parser.add_argument("--shell-command-prefix")
    parser.add_argument("--keep-elitism", type=int)

    args = parser.parse_args()

    ga_config = GAConfig(
        num_generations=args.num_generations,
        num_parents_mating=args.num_parents_mating,
        sol_per_pop=args.sol_per_pop,
        mutation_percent_genes=args.mutation_percent_genes,
        random_seed=args.random_seed,
        n_parallel_processes=args.n_parallel_processes,
        n_leaves=args.n_leaves,
        keep_elitism=args.keep_elitism,
    )
    fitness_config = FitnessConfig(
        base_plant_json=args.base_plant_json,
        helios_ini_template=args.helios_ini_template,
        helios_build_dir=args.helios_build_dir,
        work_dir=args.work_dir,
        row_spacing_m=args.row_spacing_m,
        plant_spacing_m=args.plant_spacing_m,
        latitude=args.latitude,
        longitude=args.longitude,
        utc_offset=args.utc_offset,
        n_leaves=args.n_leaves,
        n_parallel_slots=args.n_parallel_processes,
        n_gpus=args.n_gpus,
        slots_per_gpu=args.slots_per_gpu,
        shell_command_prefix=args.shell_command_prefix,
    )

    result = run_ga_optimization(
        ga_config=ga_config,
        fitness_config=fitness_config,
        output_dir=args.output_dir,
    )

    print(f"Runtime (s): {result['runtime_seconds']:.2f}")
    print(f"Best fitness: {result['best_solution_fitness']}")
    print(f"Best solution index: {result['best_solution_idx']}")
    for name, path in result["output_paths"].items():
        print(f"{name}: {path}")


if __name__ == "__main__":
    main()
