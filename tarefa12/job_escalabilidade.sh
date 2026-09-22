#!/bin/bash
#SBATCH --job-name=ns-escalabilidade
#SBATCH --partition=amd-512
#SBATCH --nodes=1
#SBATCH --exclusive
#SBATCH --hint=compute_bound
#SBATCH --time=0-2:00
#SBATCH --output=slurm-%j.out
#
# Avaliação de escalabilidade do código de Navier-Stokes (Tarefa 12).
#
# --exclusive é essencial aqui: medir escalabilidade num nó compartilhado
# mistura a variação do próprio código com a interferência de outros jobs na
# banda de memória. --hint=compute_bound faz o Slurm contar cada core como um
# processador (e não as duas threads de hardware), para que 128 threads
# ocupem 128 cores físicos e não 64 cores com SMT.

set -euo pipefail

module purge
module load compilers/gnu/14.2.0

echo "=== Nó: $(hostname) ==="
lscpu | grep -E '^(Model name|Socket|Core|Thread|NUMA)' || true
echo

make clean && make

# OMP_PLACES=cores + OMP_PROC_BIND=spread: cada thread fica presa a um core e
# o time é espalhado pelos sockets/NUMA antes de adensar. Sem isso o SO migra
# threads entre sockets e a memória local conquistada pelo first touch (v3/v4)
# deixa de ser local no meio da execução.
export OMP_PLACES=cores
export OMP_PROC_BIND=spread

THREADS="1 2 4 8 16 32 64 128"
REPS=3

FORTE=resultados_forte.csv
FRACA=resultados_fraca.csv
CAB="versao,threads,n,passos,tempo_s,mlups,checksum"

# ── Escalabilidade forte ────────────────────────────────────────────────
# Problema fixo (4096², 134 MB por grid — muito acima de qualquer cache),
# recursos crescentes. Responde: "mais núcleos resolvem *este* problema mais
# rápido?"
N_FORTE=4096
NT_FORTE=100

echo "$CAB" > "$FORTE"
echo ">>> Escalabilidade forte: n=$N_FORTE, $NT_FORTE passos"

OMP_NUM_THREADS=1 ./fluid_scale bench 0 $N_FORTE $NT_FORTE $REPS >> "$FORTE"
for p in $THREADS; do
  for v in 1 2 3 4; do
    OMP_NUM_THREADS=$p ./fluid_scale bench $v $N_FORTE $NT_FORTE $REPS >> "$FORTE"
  done
  echo "    forte: $p threads concluído"
done

# ── Escalabilidade fraca ────────────────────────────────────────────────
# Trabalho por thread constante: 2048² células cada, ou seja n = 2048·√p.
# 2048² × 8 B × 2 grids = 67 MB por thread, acima dos 32 MB de L3 por CCD —
# garante que mesmo o ponto de 1 thread seja memory-bound, e não um artefato
# de cache que faria a escalabilidade fraca parecer pior do que é.
BASE=2048
NT_FRACA=50

echo "$CAB" > "$FRACA"
echo ">>> Escalabilidade fraca: base ${BASE}² células/thread, $NT_FRACA passos"

OMP_NUM_THREADS=1 ./fluid_scale bench 0 $BASE $NT_FRACA $REPS >> "$FRACA"
for p in $THREADS; do
  n=$(awk -v b=$BASE -v p=$p 'BEGIN{printf "%d", int(b*sqrt(p)+0.5)}')
  for v in 1 2 3 4; do
    OMP_NUM_THREADS=$p ./fluid_scale bench $v "$n" $NT_FRACA $REPS >> "$FRACA"
  done
  echo "    fraca: $p threads (n=$n) concluído"
done

# ── Validação numérica ──────────────────────────────────────────────────
# Otimização que muda o resultado não é otimização. Rodada por último para não
# competir por banda com as medições.
echo
echo ">>> Validação (as 5 versões devem coincidir bit a bit)"
OMP_NUM_THREADS=128 ./fluid_scale valida 1024 | tee validacao.txt

echo
echo "=== Concluído ==="
