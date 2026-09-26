#!/bin/bash
#SBATCH --job-name=diag-afin
#SBATCH --partition=amd-512
#SBATCH --nodes=1
#SBATCH --exclusive
#SBATCH --hint=compute_bound
#SBATCH --time=0-0:10
#SBATCH --output=diag-%j.out
module purge; module load compilers/gnu/14.2.0
hostname
gcc -O3 -march=native -fopenmp -o fluid fluid.c
export OMP_PLACES=cores OMP_NUM_THREADS=128 OMP_AFFINITY_FORMAT='%n %A'
for b in close spread; do
  echo "== $b"; OMP_PROC_BIND=$b OMP_DISPLAY_AFFINITY=true ./fluid 4096 100 | sort -n | uniq -c | head -8
  for r in 1 2 3; do OMP_PROC_BIND=$b ./fluid 4096 100; done
done
