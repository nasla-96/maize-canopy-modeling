#!/usr/bin/env bash
set -euo pipefail

# Run from anywhere; resolve repo root relative to this script.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${REPO_ROOT}"

export PYTHONPATH="${REPO_ROOT}:${PYTHONPATH:-}"

# -------- User-tunable paths --------
BASE_PLANT_JSON="${BASE_PLANT_JSON:-data/plant_models/sample_maize_plant.json}"
HELIOS_INI_TEMPLATE="${HELIOS_INI_TEMPLATE:-src/cpp/par_parallel/configs/helios_config_gpu0.ini}"
HELIOS_BUILD_DIR="${HELIOS_BUILD_DIR:-src/cpp/par_parallel/build}"
WORK_DIR="${WORK_DIR:-results/ga_runs/intermediate}"
OUTPUT_DIR="${OUTPUT_DIR:-results/ga_runs/final}"
LOG_DIR="${LOG_DIR:-logs}"

# -------- Canopy / location settings --------
ROW_SPACING_M="${ROW_SPACING_M:-0.762}"
PLANT_SPACING_M="${PLANT_SPACING_M:-0.1524}"
LATITUDE="${LATITUDE:-57.13}"
LONGITUDE="${LONGITUDE:-117.28}"
UTC_OFFSET="${UTC_OFFSET:-5}"

# -------- GA settings from notebook --------
NUM_GENERATIONS="${NUM_GENERATIONS:-100}"
NUM_PARENTS_MATING="${NUM_PARENTS_MATING:-50}"
SOL_PER_POP="${SOL_PER_POP:-100}"
MUTATION_PERCENT_GENES="${MUTATION_PERCENT_GENES:-5}"
RANDOM_SEED="${RANDOM_SEED:-42}"
N_PARALLEL_PROCESSES="${N_PARALLEL_PROCESSES:-8}"
N_GPUS="${N_GPUS:-4}"
SLOTS_PER_GPU="${SLOTS_PER_GPU:-2}"

# Optional: pass cluster module loads / environment setup before ./par_parallel.
# Example:
#   export SHELL_COMMAND_PREFIX='module load mesa-glu && module load boost/1.86.0-gvbpdbb &&'
SHELL_COMMAND_PREFIX="${SHELL_COMMAND_PREFIX:-}"

mkdir -p "${WORK_DIR}" "${OUTPUT_DIR}" "${LOG_DIR}"

CMD=(
  python -m src.python.optimization.ga_optimize
  --base-plant-json "${BASE_PLANT_JSON}"
  --helios-ini-template "${HELIOS_INI_TEMPLATE}"
  --helios-build-dir "${HELIOS_BUILD_DIR}"
  --work-dir "${WORK_DIR}"
  --output-dir "${OUTPUT_DIR}"
  --row-spacing-m "${ROW_SPACING_M}"
  --plant-spacing-m "${PLANT_SPACING_M}"
  --latitude "${LATITUDE}"
  --longitude "${LONGITUDE}"
  --utc-offset "${UTC_OFFSET}"
  --num-generations "${NUM_GENERATIONS}"
  --num-parents-mating "${NUM_PARENTS_MATING}"
  --sol-per-pop "${SOL_PER_POP}"
  --mutation-percent-genes "${MUTATION_PERCENT_GENES}"
  --random-seed "${RANDOM_SEED}"
  --n-parallel-processes "${N_PARALLEL_PROCESSES}"
  --n-gpus "${N_GPUS}"
  --slots-per-gpu "${SLOTS_PER_GPU}"
)

if [[ -n "${SHELL_COMMAND_PREFIX}" ]]; then
  CMD+=(--shell-command-prefix "${SHELL_COMMAND_PREFIX}")
fi

printf 'Running command:\n%s\n' "${CMD[*]}"
"${CMD[@]}"
