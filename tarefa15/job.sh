#!/bin/bash
#SBATCH --job-name=calor
#SBATCH --partition=amd-512
#SBATCH --nodes=2
#SBATCH --ntasks-per-node=8
#SBATCH --exclusive
#SBATCH --time=0-0:30
#SBATCH --output=slurm-%j.out
#
# 16 processos distribuídos alternadamente entre os 2 nós (--map-by node):
# processos vizinhos ficam em nós diferentes, então toda troca de borda passa pela rede.
# Trabalho total fixo: pontos por processo x passos = 10^9.

set -euo pipefail
module purge
module load compilers/gnu/14.2.0 libraries/openmpi/5.0.10-gnu14-ucxmt

echo "Nós: $(scontrol show hostnames "$SLURM_JOB_NODELIST" | tr '\n' ' ')"
mpicc -O2 -Wall -Wextra -o calor calor.c
echo "versao,processos,pontos,passos,tempo_s,u_n" > resultados.csv
for rep in 1 2 3; do
  for n in 100 1000 10000 100000 1000000; do
    for v in 1 2 3; do
      mpirun -np 16 --map-by node ./calor $v $n $((1000000000 / n)) | tee -a resultados.csv
    done
  done
done
