#!/bin/bash
#SBATCH --job-name=mxv
#SBATCH --partition=amd-512
#SBATCH --nodes=1
#SBATCH --ntasks=128
#SBATCH --exclusive
#SBATCH --time=0-0:30
#SBATCH --output=slurm-%j.out
#
# Um nó (128 núcleos). Matrizes quadradas de 1024 a 16384, de 1 a 128 processos, 3 repetições.

set -euo pipefail
module purge
module load compilers/gnu/14.2.0 libraries/openmpi/5.0.10-gnu14-ucxmt

echo "Nó: $SLURM_JOB_NODELIST"
mpicc -O2 -Wall -Wextra -o mxv mxv.c
echo "M,N,processos,tempo_total_s,distribuicao_s,calculo_s,coleta_s,erros" > resultados.csv
for rep in 1 2 3; do
  for n in 1024 4096 16384; do
    for p in 1 2 4 8 16 32 64 128; do
      mpirun -np $p ./mxv $n $n | tee -a resultados.csv
    done
  done
done
