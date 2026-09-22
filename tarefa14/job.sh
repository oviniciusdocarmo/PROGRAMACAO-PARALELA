#!/bin/bash
#SBATCH --job-name=pingpong
#SBATCH --partition=amd-512
#SBATCH --nodes=2
#SBATCH --ntasks-per-node=1
#SBATCH --exclusive
#SBATCH --time=0-0:15
#SBATCH --output=slurm-%j.out
#
# Um processo em cada nó: a mensagem atravessa a rede do cluster.

set -euo pipefail
module purge
module load compilers/gnu/14.2.0 libraries/openmpi/5.0.10-gnu14-ucxmt

echo "Nós: $(scontrol show hostnames "$SLURM_JOB_NODELIST" | tr '\n' ' ')"
mpicc -O2 -o pingpong pingpong.c
mpirun -np 2 ./pingpong | tee resultados.csv
