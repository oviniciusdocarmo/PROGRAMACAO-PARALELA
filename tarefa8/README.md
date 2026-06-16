# Tarefa 8: Falso Compartilhamento e Coerência de Cache

## Objetivo

Implementar a estimativa Monte Carlo de π em quatro versões combinando dois eixos — gerador de números aleatórios (`rand()` vs `rand_r()`) e estratégia de acumulação (`#pragma omp critical` vs vetor compartilhado) — e explicar o desempenho de cada uma com base em coerência de cache e falso compartilhamento.

---

## Ambiente

| Item              | Valor                              |
|-------------------|------------------------------------|
| CPU               | AMD Ryzen 5 5600G                  |
| Núcleos físicos   | 4                                  |
| Cache line        | 64 bytes                           |
| Compilador        | GCC com `-O2 -fopenmp`             |
| N                 | 100.000.000 pontos                 |
| Threads           | 4                                  |

---

## Implementação

### V1 — `rand()` + `#pragma omp critical`

```c
long total = 0;
#pragma omp parallel num_threads(4)
{
    long local = 0;
    for (long i = 0; i < N/4; i++) {
        double x = rand() / (double)RAND_MAX;
        double y = rand() / (double)RAND_MAX;
        if (x*x + y*y <= 1.0) local++;
    }
    #pragma omp critical
    total += local;   /* executado apenas 4 vezes */
}
```

### V2 — `rand()` + vetor compartilhado

```c
long hits[4] = {0};   /* 4×8 = 32 bytes → UMA cache line de 64 B */
#pragma omp parallel num_threads(4)
{
    int tid = omp_get_thread_num();
    for (long i = 0; i < N/4; i++) {
        double x = rand() / (double)RAND_MAX;
        double y = rand() / (double)RAND_MAX;
        if (x*x + y*y <= 1.0) hits[tid]++;   /* false sharing */
    }
}
long total = 0;
for (int t = 0; t < 4; t++) total += hits[t];
```

### V3 — `rand_r()` + `#pragma omp critical`

```c
long total = 0;
#pragma omp parallel num_threads(4)
{
    unsigned seed = 42u ^ (unsigned)omp_get_thread_num(); /* seed privada */
    long local = 0;
    for (long i = 0; i < N/4; i++) {
        double x = rand_r(&seed) / (double)RAND_MAX;
        double y = rand_r(&seed) / (double)RAND_MAX;
        if (x*x + y*y <= 1.0) local++;
    }
    #pragma omp critical
    total += local;
}
```

### V4 — `rand_r()` + vetor compartilhado

```c
long hits[4] = {0};
#pragma omp parallel num_threads(4)
{
    int tid = omp_get_thread_num();
    unsigned seed = 42u ^ (unsigned)tid;
    for (long i = 0; i < N/4; i++) {
        double x = rand_r(&seed) / (double)RAND_MAX;
        double y = rand_r(&seed) / (double)RAND_MAX;
        if (x*x + y*y <= 1.0) hits[tid]++;   /* false sharing */
    }
}
long total = 0;
for (int t = 0; t < 4; t++) total += hits[t];
```

---

## Resultados

| Versão              | RNG       | Acumulação | Tempo (s) | π estimado |
|---------------------|-----------|------------|-----------|------------|
| V1 `rand` + critical  | rand()  | critical   | 3,89      | 3,141724   |
| V2 `rand` + vetor     | rand()  | vetor      | 4,84      | 3,141485   |
| V3 `rand_r` + critical | rand_r()| critical  | 0,28      | 3,141599   |
| V4 `rand_r` + vetor   | rand_r()| vetor      | 0,59      | 3,141599   |

---

## Análise

### Coerência de cache: contenção no `rand()`

`rand()` no glibc mantém um estado global protegido por mutex. Com 4 threads gerando 2 números por ponto (200 milhões de chamadas no total), **cada chamada adquire e libera o mesmo lock**. As threads passam a maior parte do tempo esperando umas pelas outras para acessar o RNG — a paralelização é ilusória.

Isso explica a diferença de ~14× entre V1 (3,89 s) e V3 (0,28 s): ambas usam `critical` para acumulação (custo fixo de 4 operações), mas a V3 usa `rand_r()` com seed privada na pilha — sem nenhuma contenção inter-thread.

### Falso compartilhamento: vetor compacto

`long hits[4]` ocupa 4 × 8 = **32 bytes** — metade de uma cache line de 64 bytes. Todos os 4 elementos cabem na mesma linha.

Quando a thread 0 incrementa `hits[0]`, o processador marca a cache line inteira como modificada (protocolo MESI: estado **Modified**). Antes que a thread 1 possa ler ou escrever `hits[1]` — em outro núcleo — ela precisa obter a linha atualizada, que está no cache do núcleo 0. O controlador de coerência invalida a cópia local da thread 1 e força uma transferência da linha entre caches.

Isso acontece a cada incremento: ~25 milhões de vezes por thread. O resultado é **V4 (0,59 s) mais lenta que V3 (0,28 s)**, mesmo sem nenhum `critical`. O `critical` em V3 é executado apenas 4 vezes — um custo irrisório comparado a 100 milhões de invalidações de cache em V4.

A V2 é a pior das versões: acumula a contenção do mutex do `rand()` com o falso compartilhamento do vetor (4,84 s).

### Resumo dos gargalos

| Versão | Gargalo principal                                          | Tempo |
|--------|------------------------------------------------------------|-------|
| V1     | Mutex do `rand()` (200M aquisições)                        | 3,89s |
| V2     | Mutex do `rand()` + false sharing em `hits[]`              | 4,84s |
| V3     | Nenhum significativo (critical roda 4×)                    | 0,28s |
| V4     | False sharing em `hits[]` (~100M invalidações de cache)    | 0,59s |

### Lição central

Eliminar o `critical` da acumulação (V3→V4) **piorou** o desempenho em 2× porque o verdadeiro problema não era o `critical` — eram os 100 milhões de escritas concorrentes em posições adjacentes de memória. Um `critical` executado 4 vezes custa infinitamente menos do que 100 milhões de invalidações de cache line.

Para corrigir o falso compartilhamento em V4 seria necessário **padear** cada elemento do vetor até o tamanho da cache line:

```c
typedef struct { long val; char pad[56]; } padded_t;  /* 64 B por elemento */
padded_t hits[4];
```

Cada `hits[tid].val` ficaria em sua própria cache line, eliminando as invalidações cruzadas.
