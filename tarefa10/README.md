# Tarefa 10: Mecanismos de Sincronização com OpenMP

## Objetivo

Comparar cinco mecanismos de sincronização do OpenMP no contexto do estimador Monte Carlo de π com `rand_r()`: contador compartilhado protegido por `critical` e `atomic`, contador privado acumulado com `critical` e `atomic`, e a cláusula `reduction`. Propor um roteiro de quando usar cada mecanismo.

---

## Ambiente

| Item            | Valor                              |
|-----------------|------------------------------------|
| CPU             | AMD Ryzen 5 5600G (4 núcleos)      |
| Threads         | 4                                  |
| N               | 100.000.000 pontos                 |
| Compilador      | GCC `-O2 -fopenmp`                 |

---

## Implementação

Todas as versões usam `rand_r()` com seed privada por thread para eliminar contenção no RNG. A única variável que muda é o mecanismo de sincronização do contador de acertos.

### V1 — contador compartilhado + `#pragma omp critical`

```c
long hits = 0;
#pragma omp parallel
{
    unsigned seed = SEED ^ (unsigned)omp_get_thread_num();
    #pragma omp for
    for (long i = 0; i < N; i++) {
        double x = rand_r(&seed) / (double)RAND_MAX;
        double y = rand_r(&seed) / (double)RAND_MAX;
        if (x*x + y*y <= 1.0) {
            #pragma omp critical   /* ~78M aquisições de mutex */
            hits++;
        }
    }
}
```

### V2 — contador compartilhado + `#pragma omp atomic`

```c
if (x*x + y*y <= 1.0) {
    #pragma omp atomic   /* ~78M operações atômicas de hardware */
    hits++;
}
```

### V3 — contador privado + `#pragma omp critical`

```c
long local = 0;
for (long i = 0; i < N/4; i++) { ... if (...) local++; }
#pragma omp critical   /* 4 aquisições no total */
hits += local;
```

### V4 — contador privado + `#pragma omp atomic`

```c
long local = 0;
for (long i = 0; i < N/4; i++) { ... if (...) local++; }
#pragma omp atomic     /* 4 operações atômicas no total */
hits += local;
```

### V5 — `reduction`

```c
long hits = 0;
#pragma omp parallel for reduction(+:hits)
for (long i = 0; i < N; i++) {
    unsigned seed = SEED ^ ((unsigned)omp_get_thread_num() * 2654435761u + (unsigned)i);
    ...
    if (x*x + y*y <= 1.0) hits++;
}
```

O OpenMP gera internamente contadores privados por thread e realiza a redução final — zero sincronização visível ao programador.

---

## Resultados

| Versão                  | π estimado   | Tempo (s) | Sync/iter     |
|-------------------------|--------------|-----------|---------------|
| V1 shared + critical    | 3,14159932   | 6,45      | ~78M mutex    |
| V2 shared + atomic      | 3,14159932   | 1,10      | ~78M atomic   |
| V3 private + critical   | 3,14159932   | 0,27      | 4 mutex       |
| V4 private + atomic     | 3,14159932   | 0,26      | 4 atomic      |
| V5 reduction            | 3,14159396   | 0,21      | 0 (interno)   |

---

## Análise

### V1 vs V2 — critical vs atomic no caminho quente

Ambas sincronizam a cada acerto (~78M vezes). A diferença de desempenho é drástica: **6,45 s vs 1,10 s** (5,9×).

- `#pragma omp critical` usa um mutex do sistema operacional: `lock → incremento → unlock`. Cada aquisição pode envolver uma syscall, uma barreira de memória completa e contenção entre as 4 threads.
- `#pragma omp atomic` emite uma instrução `LOCK XADD` (ou equivalente): lock-free, executada inteiramente em hardware, sem entrar no kernel. Ainda assim, invalida a cache line de `hits` em todos os núcleos a cada operação.

Conclusão: `atomic` é muito mais rápido que `critical` para operações simples de alta frequência, mas **ambas são péssimas** quando a sincronização ocorre em quase toda iteração.

### V3 vs V4 — critical vs atomic raramente

Com contadores privados, a sincronização cai para **4 operações** (uma por thread ao final). Nesse cenário, V3 (0,27 s) e V4 (0,26 s) são praticamente iguais — o custo de 4 mutex vs 4 operações atômicas é desprezível na escala total. O gargalo passou a ser o próprio cálculo matemático.

### V3/V4 vs V1/V2 — o impacto da frequência de sincronização

A diferença entre V2 e V4 (0,26 s vs 1,10 s, 4,2×) ilustra a lição central: **a frequência de sincronização importa mais do que o tipo de sincronização**. Trocar `atomic` por `critical` em V1 custou 5,9×; trocar sincronização frequente por rara custou 4,2× — com o mesmo mecanismo.

### V5 — reduction como abstração ótima

V5 (0,21 s) é a mais rápida e a mais simples. O compilador/runtime implementa exatamente o padrão de V3/V4 (acumulador local + redução final) sem nenhum código de sincronização explícito. Além de mais rápido, é mais legível e portável.

---

## Roteiro de decisão

```
Precisa agregar um valor em um loop paralelo?
└─► USE reduction — mais rápido, mais legível, primeira escolha sempre.

A expressão a proteger é simples (++, +=, *=, &=, |=)?
└─► Frequência alta (todo ou quase todo loop): use atomic.
    Frequência baixa (poucas vezes por thread): critical ou atomic — indiferente.
    Melhor ainda: acumule localmente e use atomic/reduction no final.

A seção crítica é complexa (múltiplas instruções, chamadas de função)?
├─► Recurso único compartilhado: #pragma omp critical (sem nome).
├─► Recursos distintos que podem ser acessados em paralelo: #pragma omp critical(nome).
│   → Cada nome é um mutex independente; inserção em lista A não bloqueia lista B.
└─► Número de recursos definido em tempo de execução (M dinâmico):
    → #pragma omp critical(nome) requer identificador fixo no código-fonte.
    → USE omp_lock_t: alocável dinamicamente, indexável por variável.
       Também necessário quando: trylock, seções longas, hierarquia de locks.
```

| Mecanismo               | Granularidade | Frequência ideal | Complexidade da seção |
|-------------------------|---------------|------------------|-----------------------|
| `reduction`             | loop inteiro  | implícita        | só agregação          |
| `atomic`                | instrução     | alta             | 1 operação simples    |
| `critical` (unnamed)    | bloco         | baixa            | qualquer              |
| `critical(nome)`        | bloco         | baixa            | qualquer (M fixo)     |
| `omp_lock_t`            | runtime       | qualquer         | qualquer (M dinâmico) |
