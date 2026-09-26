# Tarefa 15: Comunicação não bloqueante em MPI

## Objetivo
Implemente uma simulação da difusão de calor em uma barra 1D, dividida entre dois ou mais processos MPI. Cada processo deve simular um trecho da barra com células extras para troca de bordas com vizinhos. Implemente três versões: uma com MPI_Send/MPI_Recv, outra com MPI_Isend/MPI_Irecv e MPI_Wait, e uma terceira usando MPI_Test para atualizar os pontos internos enquanto aguarda a comunicação. Compare os tempos de execução e discuta os ganhos com sobreposição de comunicação e computação.

---
## Arquivos

| Arquivo | Conteúdo |
|---|---|
| `calor.c` | Difusão de calor 1D; a versão (1, 2 ou 3) é escolhida na linha de comando |
| `job.sh` | Job SLURM: 2 nós `amd-512`, 16 processos alternados entre os nós |
| `resultados.csv` | Medições (3 repetições de cada caso) |
| `slurm-2127428.out` | Saída do job usado no relatório |
| `grafico.py` | Gera `img/tempos.png` (menor tempo das 3 repetições) |
| `gera_relatorio.py` | Gera o relatório `Tarefa15_Difusao_Calor_MPI.pdf` |
| `img/code.png` | Captura do `calor.c` usada no relatório |

```bash
mpirun -np 16 ./calor <versao> <pontos por processo> <passos>
sbatch job.sh                                    # no NPAD
python3 grafico.py && python3 gera_relatorio.py  # local
```

## Implementação

Cada processo guarda seu trecho em `u[1..n]` e usa `u[0]` e `u[n+1]` como células extras para as bordas dos vizinhos. A cada passo, `v[i] = u[i] + K·(u[i-1] - 2u[i] + u[i+1])`, com K = 0,25. A ponta esquerda da barra fica em 100 e a direita em 0.

| Versão | Troca de bordas | Atualização |
|---|---|---|
| v1 | `MPI_Send`/`MPI_Recv`: pares enviam enquanto ímpares recebem, depois invertem (evita impasse) | Todos os pontos, depois da troca |
| v2 | `MPI_Irecv`/`MPI_Isend` com os dois vizinhos (um `MPI_Request` por operação) | Pontos internos, `MPI_Wait`, depois os pontos 1 e n |
| v3 | Igual à v2 | Pontos internos em blocos de 256, com `MPI_Test` entre os blocos; depois os pontos 1 e n |

Os pontos internos não dependem das células extras, por isso podem ser calculados enquanto as mensagens estão em trânsito. As três versões produzem o mesmo resultado.

## Ambiente e metodologia

- NPAD/UFRN, partição `amd-512`, nós `r2n01` e `r2n02` (job 2127428), 2 × AMD EPYC 7713 por nó.
- OpenMPI 5.0.10 e GCC 14.2.0 (`mpicc -O2`).
- 16 processos, 8 por nó, distribuídos com `--map-by node`: vizinhos ficam em nós diferentes, então toda troca de borda passa pela rede.
- Trabalho total fixo (pontos × passos = 10⁹), com 100 a 1 000 000 pontos por processo. Tempo medido com `MPI_Wtime` no processo 0; foi usado o menor tempo de 3 repetições.

## Resultados

![tempos](img/tempos.png)

| Pontos/processo | v1 (µs/passo) | v2 (µs/passo) | v3 (µs/passo) | Ganho v2 | Ganho v3 |
|---|---|---|---|---|---|
| 100 | 2,86 | 1,46 | 1,48 | 1,96× | 1,93× |
| 1 000 | 3,74 | 2,01 | 1,98 | 1,86× | 1,89× |
| 10 000 | 11,4 | 9,37 | 10,2 | 1,22× | 1,12× |
| 100 000 | 113 | 87,5 | 93,2 | 1,29× | 1,21× |
| 1 000 000 | 2955 | 2995 | 3206 | 0,99× | 0,92× |

Ganho = tempo da v1 / tempo da versão.

## Análise

- **Trechos pequenos: a comunicação domina.** As versões não bloqueantes são ~2× mais rápidas. Na v1 a troca acontece em duas fases (duas latências por passo); na v2 e na v3 as quatro mensagens ficam em trânsito juntas (uma latência). O ganho vem de não serializar a comunicação, não da sobreposição.
- **Trechos médios: a sobreposição aparece.** Com 1 000 pontos a conta (~0,9 µs) é da ordem da latência, e parte da espera fica escondida atrás dos pontos internos (2,0 µs medidos contra ~2,3 µs sem sobreposição). O ganho cai para ~1,2–1,3× à medida que a conta domina.
- **Trechos grandes: a computação domina** (~3 ms de conta por passo contra poucos µs de comunicação) e as três versões empatam.
- **v2 × v3:** desempenho parecido. As mensagens têm 8 bytes, vão em modo *eager* e progridem sozinhas, então o `MPI_Test` não tem o que adiantar e ainda custa as chamadas extras.
- Entre 10 000 e 100 000 pontos os tempos variaram até ~50% entre as repetições; nessa faixa, diferenças pequenas não são conclusivas.

## Conclusão

A comunicação não bloqueante reduziu o tempo por passo à metade quando a troca de bordas domina e escondeu parte da latência quando a conta tem a mesma ordem dela. Quando a conta domina, as três versões se equivalem. Entre `MPI_Wait` e `MPI_Test` não houve diferença relevante para mensagens pequenas, e a versão com `MPI_Wait` é a mais simples.
