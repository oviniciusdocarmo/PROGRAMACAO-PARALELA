#!/bin/bash
#SBATCH --job-name=afinidade
#SBATCH --partition=amd-512
#SBATCH --nodes=1
#SBATCH --exclusive
#SBATCH --hint=compute_bound
#SBATCH --time=0-1:00
#SBATCH --output=slurm-%j.out
#
# Escalabilidade forte do Navier-Stokes (grade 4096x4096, 100 passos, como na
# Tarefa 12) com cada política de OMP_PROC_BIND, de 1 a 128 threads, 3 repetições.
# Com OMP_PROC_BIND=false o OMP_PLACES é ignorado e quem decide é o SO.

set -eu
module purge
module load compilers/gnu/14.2.0

echo "Nó: $(hostname)  CPUs visíveis: $(nproc)"
lscpu | grep -E '^(Model name|Socket|Core|Thread|NUMA)'

gcc -O3 -march=native -fopenmp -Wall -Wextra -o fluid fluid.c

export OMP_PLACES=cores
echo "afinidade,threads,tempo_s" > resultados.csv
for rep in 1 2 3; do
  for bind in false true master close spread; do
    for p in 1 2 4 8 16 32 64 128; do
      echo "$bind,$(OMP_PROC_BIND=$bind OMP_NUM_THREADS=$p ./fluid 4096 100)" | tee -a resultados.csv
    done
  done
done
