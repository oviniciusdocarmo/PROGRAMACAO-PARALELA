# Tarefa 4: Programas memory-bound vs Programas compute-bound

## Objetivo

Implementar dois programas paralelos em C com OpenMP: um limitado por memória (_memory-bound_) e outro limitado por CPU (_compute-bound_). Ambos são paralelizados com `#pragma omp parallel for` e medem o tempo de execução variando o número de threads, permitindo observar quando o desempenho melhora, estabiliza ou piora.

---

## Ambiente

| Item              | Valor                              |
|-------------------|------------------------------------|
| CPU               | AMD Ryzen 5 5600G                  |
| Núcleos físicos   | 4 (8 threads com SMT/Hyperthreading) |
| Compilador        | GCC com `-O2 -fopenmp`             |
| OS                | Linux (WSL2)                       |

---

## Implementação

### `memory_bound.c` — limitado por memória

Realiza a soma de redução de um vetor de **100 milhões de `double`s (~800 MB)**, tamanho deliberadamente superior à cache L3 do processador. A operação por elemento é trivial (`soma += v[i]`), portanto o gargalo é a largura de banda do barramento de memória, não o poder de cálculo das unidades de ponto flutuante.

```c
#pragma omp parallel for reduction(+:soma) schedule(static)
for (long i = 0; i < N; i++)
    soma += v[i];
```

### `compute_bound.c` — limitado por CPU

Aplica **80 operações de ponto flutuante pesadas** por elemento (`sin`, `cos`, `log`, `exp`, `sqrt` encadeados em 20 rodadas) sobre um vetor de 10 milhões de elementos. Os dados cabem na cache; o gargalo é a unidade de ponto flutuante (FPU) do processador.

```c
static double calcular(double x) {
    double r = x;
    for (int j = 0; j < ROUNDS; j++) {
        r = sin(r) + cos(r * 1.1);
        r = log(fabs(r) + 1.0) + exp(-fabs(r) * 0.01);
        r = sqrt(fabs(r) + 1e-9);
    }
    return r;
}
```

---

## Resultados

### Memory-bound

| Threads | Tempo (s) | Speedup |
|---------|-----------|---------|
| 1       | 0,0709    | 1,00    |
| 2       | 0,0372    | 1,91    |
| 4       | 0,0199    | 3,56    |
| 8       | 0,0226    | 3,14    |
| 16      | 0,0229    | 3,10    |

### Compute-bound

| Threads | Tempo (s) | Speedup |
|---------|-----------|---------|
| 1       | 7,0275    | 1,00    |
| 2       | 3,5750    | 1,97    |
| 4       | 1,8604    | 3,78    |
| 8       | 1,8434    | 3,81    |
| 16      | 1,8384    | 3,82    |

---

## Análise

### Memory-bound: satura antes dos núcleos físicos

O speedup cresce de 1 para 4 threads (1,00 → 3,56×), mas **cai ao aumentar para 8 threads** (3,14×) e não melhora com 16. Isso acontece porque a largura de banda do barramento de memória é um recurso único e compartilhado: ao saturá-lo com 4 threads, acrescentar mais threads apenas aumenta a disputa sem aumentar a taxa de transferência. O speedup super-linear parcialmente observado em 4 threads reflete que múltiplas threads geram acessos mais contínuos, permitindo que o controlador de memória realize prefetching mais eficaz — mas esse ganho se esgota rapidamente.

O hardware multithreading (SMT) **pode ajudar levemente** nesse caso ao esconder latências de acesso à memória enquanto uma thread aguarda dados, mas o ganho é marginal quando o barramento já está saturado.

### Compute-bound: hyperthreading não ajuda

O speedup escala bem de 1 para 4 threads (1,00 → 3,78×), próximo ao ideal para 4 núcleos físicos. A partir de 8 threads, o ganho é praticamente nulo (3,81× com 8, 3,82× com 16).

Isso demonstra a **limitação fundamental do hyperthreading para cargas compute-bound**: dois threads lógicos no mesmo núcleo físico compartilham a mesma FPU. Ao saturar a unidade de ponto flutuante com o primeiro thread lógico, o segundo thread fica parado aguardando o mesmo recurso. O SMT foi projetado para esconder latências de memória, não para dobrar capacidade de cálculo.

### Resumo das limitações

| Situação                        | Causa                                  | Efeito                                      |
|---------------------------------|----------------------------------------|---------------------------------------------|
| Memory-bound > 4 threads        | Saturação da largura de banda de memória | Speedup para de crescer e pode piorar       |
| Compute-bound > 4 threads (SMT) | FPU compartilhada entre threads lógicos  | Hyperthreading não traz ganho real          |
| Memory-bound com SMT            | Latência de memória encoberta            | Pequena melhora até saturar o barramento    |
