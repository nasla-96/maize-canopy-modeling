# Maize Canopy Modeling

Code and example data for the paper: *"Towards smart canopies: Algorithmic design of maize canopy architectures that maximize light use efficiency"* ([arXiv:2512.06064](https://arxiv.org/abs/2512.06064))

This repository contains the codebase and example assets used for procedural 3D maize canopy modeling, field construction, Helios-based light simulation, and genetic algorithm optimization of canopy architecture for light-use efficiency.

## Overview

The workflow in this repository is organized around four main stages:

1. **Geometry generation**  
   A maize plant model is loaded from JSON/NURBS control points and modified by changing leaf traits such as length, width, inclination, and azimuth.

2. **Field construction**  
   A single modified plant is exported to OBJ and replicated into a cropped field layout with configurable plant spacing and row spacing.

3. **Helios simulation**  
   The generated field OBJ is passed to a C++ Helios-based executable (`par_parallel`) that computes PAR over the canopy using location-aware solar geometry.

4. **Optimization**  
   A GA searches over canopy trait combinations and evaluates each candidate by running the geometry → field → Helios pipeline.

## Repository Structure

```text
maize-canopy-modeling/
├── README.md
├── .gitignore
├── requirements.txt
├── environment.yml
│
├── data/
│   └── plant_models/
│
├── src/
│   ├── python/
│   │   ├── geometry/
│   │   │   ├── load_plant.py
│   │   │   ├── modify_leaf_traits.py
│   │   │   └── build_field.py
│   │   ├── pipeline/
│   │   │   ├── prepare_configs.py
│   │   │   ├── run_simulation.py
│   │   │   └── postprocess_results.py
│   │   ├── optimization/
│   │   │   ├── chromosome_utils.py
│   │   │   ├── fitness.py
│   │   │   └── ga_optimize.py
│   │   └── utils/
│   │
│   └── cpp/
│       └── par_parallel/
│           ├── CMakeLists.txt
│           ├── parallel.cpp
│           └── configs/
│
├── scripts/
│   └── run_ga.sh
│
├── slurm/
│   ├── run_4gpu.slurm
│   └── run_single_gpu.slurm
│
├── notebooks/
├── results/
└── docs/
```

## Core Components

### `src/python/geometry/`
Geometry utilities for loading a plant model, modifying leaf traits, and constructing field-scale canopies.

- `load_plant.py`: load and export plant surface containers
- `modify_leaf_traits.py`: scale leaf length/width and apply rotations
- `build_field.py`: tile a plant mesh into a cropped field representation

### `src/python/pipeline/`
Functions for preparing Helios config files, launching simulations, and parsing outputs.

- `prepare_configs.py`: writes simulation-specific config files
- `run_simulation.py`: runs the full plant → field → Helios pipeline
- `postprocess_results.py`: reads Helios output CSV files and summary values

### `src/python/optimization/`
GA-based search over canopy architectural traits.

- `chromosome_utils.py`: chromosome layout and bounds
- `fitness.py`: evaluates a chromosome by calling the simulation pipeline
- `ga_optimize.py`: PyGAD driver for full optimization runs

### `src/cpp/par_parallel/`
C++ Helios simulation entry point.

- `parallel.cpp`: reads a config file, loads a field OBJ, computes PAR, and writes per-run CSV outputs
- `configs/`: GPU-specific sample config files
- `CMakeLists.txt`: build configuration for the Helios simulation executable

## Environment Setup

Two environment files are included:

- `environment.yml`: fuller Conda environment reflecting the working Nova `nurbs` environment
- `requirements.txt`: lighter-weight list of the core Python dependencies needed for the main Python workflow

### Option 1: Conda environment

```bash
conda env create -f environment.yml
conda activate nurbs
```

### Option 2: pip environment

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## External Dependencies

This repository includes the Python workflow and the `par_parallel` C++ entry point, but the Helios build still depends on an external C++/HPC environment.

Typical requirements include:

- a C++ compiler
- CMake
- Boost
- Helios libraries and plugins
- cluster-specific module loads when running on HPC

On Nova or similar systems, module loading may still be required before running the compiled executable.

## Building the C++ Simulation Code

From the `src/cpp/par_parallel/` directory:

```bash
mkdir -p build
cd build
cmake ..
make -j
```

This should produce the `par_parallel` executable inside the build directory.

## Running a Single Simulation

The pipeline can generate a plant, build a field, write a Helios config, and run the compiled executable.

Example:

```bash
python -m src.python.pipeline.run_simulation \
  --base-plant-json data/plant_models/B73_manually_copy_12leaves.json \
  --lengths "40,42,44,46,48,50,52,54,56,58,60,62" \
  --widths "4,4.2,4.5,4.8,5,5.2,5.4,5.6,5.8,6,6.2,6.4" \
  --theta "10,12,14,16,18,20,22,24,26,28,30,32" \
  --phi "0,5,10,15,20,25,30,35,40,45,50,55" \
  --plant-obj-output results/sample_outputs/plant.obj \
  --field-obj-output results/sample_outputs/field_cropped.obj \
  --row-spacing-m 0.762 \
  --plant-spacing-m 0.1524 \
  --helios-ini-template src/cpp/par_parallel/configs/helios_config_gpu0.ini \
  --helios-ini-output results/sample_outputs/run.ini \
  --helios-build-dir src/cpp/par_parallel/build \
  --latitude 57.13 \
  --longitude 117.28 \
  --utc-offset 5
```

## Running GA Optimization

Example local command:

```bash
python -m src.python.optimization.ga_optimize \
  --base-plant-json data/plant_models/B73_manually_copy_12leaves.json \
  --helios-ini-template src/cpp/par_parallel/configs/helios_config_gpu0.ini \
  --helios-build-dir src/cpp/par_parallel/build \
  --work-dir results/ga_runs/intermediate \
  --output-dir results/ga_runs/final \
  --row-spacing-m 0.762 \
  --plant-spacing-m 0.1524 \
  --latitude 57.13 \
  --longitude 117.28 \
  --utc-offset 5 \
  --num-generations 100 \
  --num-parents-mating 50 \
  --sol-per-pop 100 \
  --mutation-percent-genes 5 \
  --random-seed 42 \
  --n-parallel-processes 8 \
  --n-gpus 4 \
  --slots-per-gpu 2
```

For cluster runs, use the launcher scripts under `scripts/` and `slurm/`.

## Outputs

The pipeline produces several intermediate and final artifacts, including:

- single-plant OBJ files
- cropped field OBJ files
- Helios `.ini` config files
- per-simulation CSV logs written by `par_parallel`
- GA summaries and best-solution records

`parallel.cpp` writes simulation logs into a `helios_logs/` folder next to the generated field OBJ.

## Current Status

This repository is an actively cleaned and reorganized research codebase. It is intended to provide a shareable, structured version of the project workflow rather than a finalized software release.

Some scripts and paths may still reflect HPC-oriented workflows, and certain pieces are tailored to the Helios simulation environment used during development.

## Notes

- Sample and reference plant models are included under `data/plant_models/`.
- The Python environment can be reproduced from `environment.yml`, while `requirements.txt` lists the core Python packages for a lighter install path.
- The repository currently focuses on canopy light interception / PAR evaluation; downstream photosynthesis extensions can be integrated on top of the same geometry and field-generation pipeline.

## Citation

If you use this repository, please cite:

> Saleem, N., et al. *Towards smart canopies: Algorithmic design of maize canopy architectures that maximize light use efficiency*. arXiv:2512.06064.

## Author

**Nasla Saleem**  
Ph.D. Candidate, Mechanical Engineering  
Iowa State University  
AI Institute for Resilient Agriculture
