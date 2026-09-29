#!/bin/bash
#SBATCH --job-name=mxv-col
#SBATCH --partition=amd-512
#SBATCH --nodes=1
#SBATCH --ntasks=64
#SBATCH --hint=compute_bound
#SBATCH --time=0-0:40
#SBATCH --output=slurm-%j.out
#
# Meio nó (64 núcleos físicos). Matrizes quadradas de 1024 a 16384, de 1 a 64 processos,
# 3 repetições. Roda a versão por colunas (esta tarefa) e a por linhas (tarefa 16).

set -euo pipefail
module purge
module load compilers/gnu/14.2.0 libraries/openmpi/5.0.10-gnu14-ucxmt

echo "Nó: $SLURM_JOB_NODELIST"
mpicc -O2 -Wall -Wextra -o mxv mxv.c
mpicc -O2 -Wall -Wextra -o mxv_linhas ../tarefa16/mxv.c
echo "versao,M,N,processos,tempo_total_s,distribuicao_s,calculo_s,coleta_s,erros" > resultados.csv
for rep in 1 2 3; do
  for n in 1024 4096 16384; do
    for p in 1 2 4 8 16 32 64; do
      mpirun -np $p ./mxv $n $n | sed 's/^/colunas,/' | tee -a resultados.csv
      mpirun -np $p ./mxv_linhas $n $n | sed 's/^/linhas,/' | tee -a resultados.csv
    done
  done
done
