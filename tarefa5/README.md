# Tarefa 5: Desafios iniciais da Programação Paralela

## Objetivo

Contar quantos números primos existem entre 2 e N, primeiro de forma sequencial e depois paralelizando o laço principal com `#pragma omp parallel for` **sem alterar a lógica original**. O objetivo é observar os dois desafios clássicos da programação paralela: **correção** (condição de corrida) e **distribuição de carga** (desbalanceamento).

---

## Ambiente

| Item            | Valor                              |
|-----------------|------------------------------------|
| CPU             | AMD Ryzen 5 5600G                  |
| Núcleos físicos | 4 (8 threads com SMT)              |
| Compilador      | GCC com `-O2 -fopenmp`             |
| N               | 10.000.000                         |

---

## Implementação

### Versão sequencial

```c
long count = 0;
for (int i = 2; i <= N; i++)
    if (is_prime(i))
        count++;
```

### Versão paralela ingênua — lógica inalterada

```c
long count = 0;
#pragma omp parallel for          /* única mudança */
for (int i = 2; i <= N; i++)
    if (is_prime(i))
        count++;                  /* RACE CONDITION */
```

A única alteração foi inserir a diretiva OpenMP. O `count++` não foi protegido, conforme solicitado.

---

## Resultados

Os três blocos abaixo são execuções consecutivas do mesmo binário, mostrando a **não-determinismo** da versão paralela.

**Execução 1**

| Versão                   | Primos  | Tempo (s) | Correto? |
|--------------------------|---------|-----------|----------|
| Sequencial               | 664.579 | 1,2323    | sim      |
| Paralela ingênua (2 thr) | 661.667 | 0,7741    | **NÃO** |
| Paralela ingênua (4 thr) | 661.978 | 0,4686    | **NÃO** |
| Paralela ingênua (8 thr) | 662.020 | 0,4364    | **NÃO** |

**Execução 2**

| Versão                   | Primos  | Tempo (s) | Correto? |
|--------------------------|---------|-----------|----------|
| Sequencial               | 664.579 | 1,2348    | sim      |
| Paralela ingênua (2 thr) | 661.629 | 0,7945    | **NÃO** |
| Paralela ingênua (4 thr) | 661.655 | 0,4504    | **NÃO** |
| Paralela ingênua (8 thr) | 662.471 | 0,3546    | **NÃO** |

**Execução 3**

| Versão                   | Primos  | Tempo (s) | Correto? |
|--------------------------|---------|-----------|----------|
| Sequencial               | 664.579 | 1,2390    | sim      |
| Paralela ingênua (2 thr) | 661.809 | 0,8369    | **NÃO** |
| Paralela ingênua (4 thr) | 661.956 | 0,4463    | **NÃO** |
| Paralela ingênua (8 thr) | 661.851 | 0,4351    | **NÃO** |

---

## Análise dos desafios

### Desafio 1: Correção — condição de corrida

A instrução `count++` expande para três operações de máquina:

```
LOAD  count → reg
ADD   reg, 1
STORE reg → count
```

Quando múltiplas threads executam esse trecho simultaneamente, uma thread pode sobrescrever o resultado escrito por outra (**lost update**). O efeito é que o contador final é sempre **menor** do que o valor correto — incrementos são simplesmente perdidos.

O valor correto é sempre **664.579**, mas a versão paralela retorna valores como 661.629 ou 662.471 — e esses valores mudam a cada execução, pois a ordem das operações de threads é não-determinística. Esse é o comportamento clássico de uma condição de corrida.

### Desafio 2: Distribuição de carga — desbalanceamento

O `schedule(static)` padrão divide o intervalo `[2, N]` em blocos contíguos de tamanho aproximadamente igual. Porém, verificar a primalidade de um número `n` custa `O(√n)` — números maiores são progressivamente mais caros de testar.

As threads que recebem os blocos finais (números grandes) trabalham muito mais do que as que recebem os blocos iniciais. O resultado é que o speedup estagna entre 4 e 8 threads: ao passar de 4 para 8 threads, o tempo quase não muda (≈0,44 s nos dois casos), mesmo havendo mais threads disponíveis. As últimas threads viram gargalo e as primeiras ficam ociosas.

### Resumo

| Desafio               | Causa                                    | Sintoma observado                              |
|-----------------------|------------------------------------------|------------------------------------------------|
| Condição de corrida   | `count++` não é atômico                 | Resultado errado e não-determinístico          |
| Desbalanceamento      | Custo de `is_prime` cresce com o índice  | Speedup estagna ao aumentar threads além de 4  |
