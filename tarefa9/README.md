# Tarefa 9: Regiões críticas nomeadas vs locks explícitos

## Objetivo

Implementar inserções paralelas em listas encadeadas usando `#pragma omp task`, garantindo integridade sem condição de corrida. Demonstrar que regiões críticas nomeadas permitem paralelismo entre listas distintas quando o número é fixo, e explicar por que locks explícitos (`omp_lock_t`) se tornam necessários quando o número de listas é definido em tempo de execução.

---

## Ambiente

| Item            | Valor              |
|-----------------|--------------------|
| CPU             | AMD Ryzen 5 5600G  |
| Threads         | 4                  |
| N               | 1000 inserções     |
| Compilador      | GCC `-O2 -fopenmp` |

---

## Implementação

### Lista encadeada

Inserção no início da lista (`O(1)`):

```c
typedef struct no { int val; struct no *next; } no_t;

static void inserir(no_t **head, int val) {
    no_t *n = malloc(sizeof(no_t));
    n->val = val; n->next = *head; *head = n;
}
```

### Parte 1 — 2 listas com `#pragma omp critical` nomeado

```c
#pragma omp parallel num_threads(4)
#pragma omp single
{
    for (int i = 0; i < N; i++) {
        #pragma omp task firstprivate(i)
        {
            unsigned seed = (unsigned)i * 2654435761u;
            int escolha = rand_r(&seed) % 2;

            if (escolha == 0) {
                #pragma omp critical(lista0)   /* lock A */
                inserir(&lista0, i);
            } else {
                #pragma omp critical(lista1)   /* lock B — independente de A */
                inserir(&lista1, i);
            }
        }
    }
}
```

`#pragma omp critical(lista0)` e `#pragma omp critical(lista1)` são **mutexes distintos** no runtime do OpenMP. Uma thread inserindo na lista 0 não bloqueia outra inserindo na lista 1 — as inserções nas duas listas podem ocorrer em paralelo.

### Parte 2 — M listas com `omp_lock_t` explícito

```c
omp_lock_t *locks = malloc(M * sizeof(omp_lock_t));
for (int i = 0; i < M; i++) omp_init_lock(&locks[i]);

#pragma omp parallel num_threads(4)
#pragma omp single
{
    for (int i = 0; i < N; i++) {
        #pragma omp task firstprivate(i)
        {
            unsigned seed = (unsigned)i * 2654435761u;
            int escolha = rand_r(&seed) % M;

            omp_set_lock(&locks[escolha]);
            inserir(&listas[escolha], i);
            omp_unset_lock(&locks[escolha]);
        }
    }
}

for (int i = 0; i < M; i++) omp_destroy_lock(&locks[i]);
```

---

## Resultados

### Parte 1 — 2 listas, critical nomeado

```
Lista 0: 500 elementos
Lista 1: 500 elementos
Total  : 1000 (correto)
```

### Parte 2 — 5 listas, omp_lock_t

```
Lista 0: 189 elementos
Lista 1: 206 elementos
Lista 2: 208 elementos
Lista 3: 203 elementos
Lista 4: 194 elementos
Total  : 1000 (correto)
```

### Parte 2 — 8 listas, omp_lock_t (`./critical 8`)

```
Lista 0..7: 125 elementos cada
Total  : 1000 (correto)
```

---

## Por que critical nomeado não é suficiente para M dinâmico

### O problema de compilação

O nome em `#pragma omp critical(nome)` deve ser um **identificador C** válido, fixo no código-fonte em tempo de compilação. Não é possível usar uma variável ou expressão como nome:

```c
/* ERRO DE SINTAXE — o compilador rejeita */
#pragma omp critical(locks[i])
inserir(&listas[i], val);
```

Para M = 5, seria necessário escrever à mão cinco blocos com nomes diferentes (`lista0` … `lista4`). Para M arbitrário (lido de `argv`), isso é **estruturalmente impossível**.

### A solução: `omp_lock_t`

`omp_lock_t` é um objeto de sincronização do OpenMP gerenciado em **tempo de execução**. Pode ser alocado dinamicamente, armazenado em vetores e indexado por variáveis:

```c
omp_init_lock(&locks[i]);    /* inicializa o i-ésimo lock */
omp_set_lock(&locks[i]);     /* adquire  */
omp_unset_lock(&locks[i]);   /* libera   */
omp_destroy_lock(&locks[i]); /* destrói  */
```

Cada elemento `locks[i]` é um mutex independente — semanticamente equivalente a um `critical` nomeado único, mas criado e selecionado em runtime. Isso permite M listas com M locks, onde M é qualquer valor definido pelo usuário, sem alterar o código-fonte.

### Resumo

| Recurso                     | Nome/índice | Criação   | M dinâmico |
|-----------------------------|-------------|-----------|------------|
| `#pragma omp critical(nome)`| identificador fixo | compilação | impossível |
| `omp_lock_t`                | variável/índice    | runtime    | sim        |
