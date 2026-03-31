#!/bin/bash
#SBATCH --job-name=maize_ga_4gpu
#SBATCH --partition=nova
#SBATCH --account=baskargroup-a100gpu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=16
#SBATCH --gres=gpu:a100:4
#SBATCH --mem=369G
#SBATCH --time=6-00:00:00
#SBATCH --output=logs/slurm.%x.%j.out
#SBATCH --error=logs/slurm.%x.%j.err
#SBATCH --mail-user=nasla@iastate.edu
#SBATCH --mail-type=BEGIN,END,FAIL

set -euo pipefail

REPO_ROOT="${SLURM_SUBMIT_DIR}"
cd "${REPO_ROOT}"
mkdir -p logs results/ga_runs/intermediate results/ga_runs/final

source ~/.bashrc
conda activate nurbs

export PYTHONPATH="${REPO_ROOT}:${PYTHONPATH:-}"
export OMP_NUM_THREADS=1
export MKL_NUM_THREADS=1

# par_parallel-side module loads. Keep the trailing && so run_ga.sh can prepend ./par_parallel.
export SHELL_COMMAND_PREFIX='module load mesa-glu && module load boost/1.86.0-gvbpdbb &&'

# Defaults aligned to the extracted notebook workflow.
export BASE_PLANT_JSON="${BASE_PLANT_JSON:-data/plant_models/sample_maize_plant.json}"
export HELIOS_INI_TEMPLATE="${HELIOS_INI_TEMPLATE:-src/cpp/par_parallel/configs/helios_config_gpu0.ini}"
export HELIOS_BUILD_DIR="${HELIOS_BUILD_DIR:-src/cpp/par_parallel/build}"
export WORK_DIR="${WORK_DIR:-results/ga_runs/intermediate/${SLURM_JOB_ID}}"
export OUTPUT_DIR="${OUTPUT_DIR:-results/ga_runs/final/${SLURM_JOB_ID}}"
export N_PARALLEL_PROCESSES="${N_PARALLEL_PROCESSES:-8}"
export N_GPUS="${N_GPUS:-4}"
export SLOTS_PER_GPU="${SLOTS_PER_GPU:-2}"
export NUM_GENERATIONS="${NUM_GENERATIONS:-100}"
export NUM_PARENTS_MATING="${NUM_PARENTS_MATING:-50}"
export SOL_PER_POP="${SOL_PER_POP:-100}"
export MUTATION_PERCENT_GENES="${MUTATION_PERCENT_GENES:-5}"
export RANDOM_SEED="${RANDOM_SEED:-42}"

bash scripts/run_ga.sh
