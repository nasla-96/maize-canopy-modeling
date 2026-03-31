#!/bin/bash
#SBATCH --job-name=maize_ga_1gpu
#SBATCH --partition=nova
#SBATCH --account=baskargroup-a100gpu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --gres=gpu:a100:1
#SBATCH --mem=96G
#SBATCH --time=2-00:00:00
#SBATCH --output=logs/slurm.%x.%j.out
#SBATCH --error=logs/slurm.%x.%j.err

set -euo pipefail

REPO_ROOT="${SLURM_SUBMIT_DIR}"
cd "${REPO_ROOT}"
mkdir -p logs results/ga_runs/intermediate results/ga_runs/final

source ~/.bashrc
conda activate nurbs

export PYTHONPATH="${REPO_ROOT}:${PYTHONPATH:-}"
export OMP_NUM_THREADS=1
export MKL_NUM_THREADS=1
export SHELL_COMMAND_PREFIX='module load mesa-glu && module load boost/1.86.0-gvbpdbb &&'

export BASE_PLANT_JSON="${BASE_PLANT_JSON:-data/plant_models/sample_maize_plant.json}"
export HELIOS_INI_TEMPLATE="${HELIOS_INI_TEMPLATE:-src/cpp/par_parallel/configs/helios_config_gpu0.ini}"
export HELIOS_BUILD_DIR="${HELIOS_BUILD_DIR:-src/cpp/par_parallel/build}"
export WORK_DIR="${WORK_DIR:-results/ga_runs/intermediate/${SLURM_JOB_ID}}"
export OUTPUT_DIR="${OUTPUT_DIR:-results/ga_runs/final/${SLURM_JOB_ID}}"
export N_PARALLEL_PROCESSES="${N_PARALLEL_PROCESSES:-2}"
export N_GPUS="${N_GPUS:-1}"
export SLOTS_PER_GPU="${SLOTS_PER_GPU:-2}"
export NUM_GENERATIONS="${NUM_GENERATIONS:-10}"
export NUM_PARENTS_MATING="${NUM_PARENTS_MATING:-10}"
export SOL_PER_POP="${SOL_PER_POP:-20}"
export MUTATION_PERCENT_GENES="${MUTATION_PERCENT_GENES:-5}"
export RANDOM_SEED="${RANDOM_SEED:-42}"

bash scripts/run_ga.sh
