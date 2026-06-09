# Tarefa 6: Estimativa de π com Monte Carlo e OpenMP

## Objetivo

Implementar a estimativa estocástica de π (método Monte Carlo) e paralelizá-la progressivamente com OpenMP, expondo a condição de corrida, corrigindo-a com `#pragma omp critical` e reestruturando o código com `#pragma omp parallel` + `#pragma omp for` usando as cláusulas `private`, `firstprivate`, `lastprivate`, `shared` e `default(none)`.

---

## Algoritmo Monte Carlo

Gerar N pontos aleatórios (x, y) ∈ [0,1)². A probabilidade de um ponto cair dentro do quarto de círculo unitário é π/4. Logo:

```
π ≈ 4 × (pontos dentro do círculo) / N
```

---

## Ambiente

| Item            | Valor                              |
|-----------------|------------------------------------|
| CPU             | AMD Ryzen 5 5600G                  |
| Núcleos físicos | 4 (8 threads com SMT)              |
| Compilador      | GCC com `-O2 -fopenmp`             |
| N               | 100.000.000 pontos                 |
| Threads         | 4                                  |

---

## Versões implementadas

### 1. Sequencial

```c
long dentro = 0;
unsigned seed = SEED;
for (long i = 0; i < N; i++) {
    double x = rand_r(&seed) / (double)RAND_MAX;
    double y = rand_r(&seed) / (double)RAND_MAX;
    if (x*x + y*y <= 1.0) dentro++;
}
```

Baseline correto. `rand_r` é reentrante (recebe a seed por ponteiro), o que permite uso seguro por thread depois.

---

### 2. Paralela ingênua — `#pragma omp parallel for` sem proteção

```c
long dentro = 0;
unsigned seed = SEED;
#pragma omp parallel for
for (long i = 0; i < N; i++) {
    double x = rand_r(&seed) / (double)RAND_MAX;
    double y = rand_r(&seed) / (double)RAND_MAX;
    if (x*x + y*y <= 1.0)
        dentro++;               /* RACE CONDITION */
}
```

Dois problemas simultâneos:
- `dentro++` expande para `LOAD → ADD → STORE`, que múltiplas threads intercalam → incrementos são perdidos.
- `seed` é compartilhada: threads concorrem no próprio RNG, corrompendo a geração.

---

### 3. Com `#pragma omp critical`

```c
if (x*x + y*y <= 1.0) {
    #pragma omp critical
    dentro++;
}
```

Correto: apenas uma thread por vez executa o incremento. Mas **serializa 100% dos writes** — cada ponto que cai dentro do círculo adquire um lock global, tornando a versão mais lenta que a sequencial.

---

### 4. Com `#pragma omp parallel` + `#pragma omp for` + cláusulas

```c
long dentro = 0;
long local;
unsigned seed_master = SEED;
unsigned seed_last   = 0;

#pragma omp parallel default(none)       \
    shared(dentro, seed_last)             \
    firstprivate(seed_master)             \
    private(local)
{
    unsigned seed = seed_master ^ (unsigned)omp_get_thread_num();
    local = 0;

    #pragma omp for lastprivate(seed_last)
    for (long i = 0; i < N; i++) {
        double x = rand_r(&seed) / (double)RAND_MAX;
        double y = rand_r(&seed) / (double)RAND_MAX;
        if (x*x + y*y <= 1.0) local++;
        seed_last = seed;
    }

    #pragma omp critical
    dentro += local;    /* uma única operação crítica por thread */
}
```

O `#pragma omp critical` aqui executa apenas uma vez por thread (ao somar o acumulador local), em vez de uma vez por ponto — custo fixo, não proporcional a N.

---

### 5. Com `reduction` (idiomático)

```c
#pragma omp parallel for default(none) shared(seed_master) reduction(+:dentro)
for (long i = 0; i < N; i++) { ... }
```

O OpenMP cria uma cópia privada de `dentro` por thread, acumula em paralelo e soma os parciais ao final, sem necessidade de `critical` explícito.

---

## Resultados

| Versão                        | π estimado   | Tempo (s) | Correto? |
|-------------------------------|--------------|-----------|----------|
| Sequencial                    | 3,14153268   | 0,94      | sim      |
| Ingênua (race condition) — 1  | 2,42180700   | 1,73      | **NÃO** |
| Ingênua (race condition) — 2  | 2,56800936   | 1,91      | **NÃO** |
| Ingênua (race condition) — 3  | 1,38720932   | 2,77      | **NÃO** |
| Com `omp critical`            | 3,14158028   | 6,10      | sim      |
| `parallel+for+cláusulas`      | 3,14139304   | 0,25      | sim      |
| Com `reduction`               | 3,14159384   | 0,21      | sim      |

As três linhas da versão ingênua são execuções consecutivas do mesmo binário, mostrando que o resultado varia a cada execução — comportamento típico de condição de corrida.

---

## Análise das cláusulas OpenMP

### `shared(dentro, seed_last)`

Declara que `dentro` e `seed_last` são compartilhadas entre todas as threads. O acesso a `dentro` é protegido por `#pragma omp critical`; `seed_last` é atualizada pela cláusula `lastprivate`.

### `firstprivate(seed_master)`

Cada thread recebe uma **cópia inicializada** com o valor de `seed_master` do master thread (SEED = 12345). Em seguida, cada thread deriva sua própria seed com XOR do thread ID (`seed ^ thread_num`), garantindo sequências independentes. Sem isso, todas as threads gerariam os mesmos números aleatórios.

Contraposição com `private`: se fosse `private(seed_master)`, cada thread receberia a variável **não-inicializada** — comportamento indefinido.

### `private(local)`

Cada thread tem sua própria cópia de `local` sem valor inicial definido pelo OpenMP. O programador inicializa explicitamente (`local = 0`) logo após entrar na região paralela. Serve para acumular a contagem parcial de cada thread sem disputa.

### `lastprivate(seed_last)`

Ao fim do `#pragma omp for`, a variável `seed_last` recebe o valor que ela tinha no thread que executou a **última iteração lógica** (i = N−1). É útil quando se quer continuar uma sequência numérica em chamadas subsequentes — neste programa, mostra o estado final do RNG.

### `default(none)`

Sem essa cláusula, variáveis não declaradas nas cláusulas herdam escopo padrão (geralmente `shared`). Com `default(none)`, o compilador exige declaração explícita de cada variável. Qualquer omissão vira erro de compilação, forçando o programador a raciocinar sobre o compartilhamento de cada dado — especialmente valioso em regiões paralelas complexas com muitas variáveis.

---

## Conclusões

| Versão               | Correto? | Desempenho | Motivo                                      |
|----------------------|----------|------------|---------------------------------------------|
| Sequencial           | sim      | base       | —                                           |
| Ingênua              | **não**  | pior       | Race condition + contenção de cache         |
| `omp critical` total | sim      | pior ainda | Lock por ponto → serializa toda a operação  |
| `parallel+for`       | sim      | ~4× melhor | Critical apenas uma vez por thread          |
| `reduction`          | sim      | ~4× melhor | Forma idiomática e mais eficiente           |

A versão com `omp critical` em cada ponto é **mais lenta que a sequencial** porque adquire um lock global por iteração — demonstrando que sincronização excessiva é tão problemática quanto a ausência dela. A solução correta é minimizar o escopo crítico: acumular localmente e sincronizar apenas uma vez por thread.
