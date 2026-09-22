#!/bin/bash
#SBATCH --job-name=ns-pascal
#SBATCH --partition=amd-512
#SBATCH --nodes=1
#SBATCH --exclusive
#SBATCH --hint=compute_bound
#SBATCH --time=0-5:00
#SBATCH --output=slurm-pascal-%j.out
#
# Tarefa 12 — sweep de escalabilidade com o PaScal Analyzer.
#
# Diferente de job_escalabilidade.sh, que percorre à mão duas linhas do espaço
# de configurações (problema fixo / trabalho por thread fixo), aqui roda-se o
# **produto cartesiano** de núcleos × tamanhos de entrada. É esse mapa 2D que o
# PaScal Viewer consome: a escalabilidade forte se lê ao longo de uma linha
# (mesmo tamanho, mais núcleos), a fraca ao longo da diagonal (tamanho e
# núcleos crescendo juntos) e a eficiência paralela no mapa de calor inteiro.

set -euo pipefail

module purge
module load compilers/gnu/14.2.0

# env.sh põe pascalanalyzer no PATH e libmpascalops no caminho do linker.
# Dois cuidados: ele monta os caminhos a partir de `$(pwd)`, então precisa ser
# carregado de dentro do próprio diretório; e faz `export X=$X:...` em
# variáveis que podem não existir, o que abortaria o script sob `set -u`.
PASCAL_DIR="$HOME/pascal/pascal-releases-master"
set +u
cd "$PASCAL_DIR" && source ./env.sh
set -u
cd "$SLURM_SUBMIT_DIR"
command -v pascalanalyzer >/dev/null || { echo "pascalanalyzer não encontrado"; exit 1; }

echo "=== Nó: $(hostname) ==="
lscpu | grep -E '^(Model name|Socket|Core|Thread|NUMA node\(s\))' || true
echo

# Recompila no nó de computação: os binários são gerados com -march=native e o
# nó de login é de outra arquitetura, então reaproveitar um build feito lá
# renderia código errado para este processador (ou nem executaria).
make clean && make pascal

CORES=1,2,4,8,16,32,64,128

# Um tamanho para cada contagem de núcleos, com n = 2048·√p — ou seja, 2048²
# células por thread. Casar as duas escalas assim faz a **diagonal** do mapa
# ser exatamente a escalabilidade fraca (trabalho por thread constante),
# enquanto cada **linha** continua sendo uma escalabilidade forte (problema
# fixo, núcleos crescendo). Um ladder geométrico qualquer daria o mapa, mas
# não a diagonal.
INPUTS='"2048","2896","4096","5793","8192","11585","16384","23170"'
REPS=3

# Nenhum OMP_PROC_BIND/OMP_PLACES é exportado aqui de propósito: quem decide
# quais núcleos ficam ativos em cada execução é o próprio analyzer (ele habilita
# e desabilita CPUs). Fixar afinidade por fora entraria em conflito com isso.

for v in 1 2 3 4; do
  echo ">>> PaScal Analyzer — versão v$v"
  eval pascalanalyzer "./pascal_fluid_v$v" \
      --inst man \
      --cors "$CORES" \
      --ipts "$INPUTS" \
      --rpts "$REPS" \
      --verb INFO \
      --outp "pascal_v$v.json"
  echo
done

echo "=== Concluído ==="
ls -la pascal_v*.json
