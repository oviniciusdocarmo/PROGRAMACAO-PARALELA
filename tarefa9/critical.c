#include <stdio.h>
#include <stdlib.h>
#include <omp.h>

#define N        1000
#define NTHREADS 4
#define M_PADRAO 5

/* ── Lista encadeada ──────────────────────────────────────────────────── */
typedef struct no { int val; struct no *next; } no_t;

static void inserir(no_t **head, int val) {
    no_t *n = malloc(sizeof(no_t));
    n->val = val;
    n->next = *head;
    *head = n;
}

static int tamanho(const no_t *h) {
    int c = 0;
    while (h) { c++; h = h->next; }
    return c;
}

static void liberar(no_t *h) {
    while (h) { no_t *t = h->next; free(h); h = t; }
}

/* ── Parte 1: 2 listas — #pragma omp critical nomeado ────────────────────
   Cada lista tem seu próprio nome de seção crítica: critical(lista0) e
   critical(lista1) são locks distintos no runtime do OpenMP.
   Inserções em listas diferentes podem ocorrer em paralelo.               */
static void parte1(void) {
    no_t *lista0 = NULL, *lista1 = NULL;

    #pragma omp parallel num_threads(NTHREADS)
    #pragma omp single
    {
        for (int i = 0; i < N; i++) {
            #pragma omp task firstprivate(i)
            {
                unsigned seed = (unsigned)i * 2654435761u;
                int escolha = (int)(rand_r(&seed) % 2);

                if (escolha == 0) {
                    #pragma omp critical(lista0)
                    inserir(&lista0, i);
                } else {
                    #pragma omp critical(lista1)
                    inserir(&lista1, i);
                }
            }
        }
    }

    int t0 = tamanho(lista0), t1 = tamanho(lista1);
    printf("=== Parte 1: 2 listas, critical nomeado (%d threads) ===\n", NTHREADS);
    printf("  Lista 0: %d elementos\n", t0);
    printf("  Lista 1: %d elementos\n", t1);
    printf("  Total  : %d %s\n\n", t0 + t1,
           t0 + t1 == N ? "(correto)" : "(ERRO)");

    liberar(lista0);
    liberar(lista1);
}

/* ── Parte 2: M listas — omp_lock_t explícito ────────────────────────────
   Com M definido em tempo de execução, não é possível usar critical nomeado:
   o nome precisa ser um identificador C fixo no código-fonte.
   Tentar escrever `#pragma omp critical(locks[i])` é erro de sintaxe.

   A solução é alocar um vetor de omp_lock_t — um lock por lista —
   e usar omp_set_lock / omp_unset_lock em tempo de execução.              */
static void parte2(int M) {
    no_t  **listas = calloc(M, sizeof(no_t *));
    omp_lock_t *locks = malloc(M * sizeof(omp_lock_t));
    for (int i = 0; i < M; i++) omp_init_lock(&locks[i]);

    #pragma omp parallel num_threads(NTHREADS)
    #pragma omp single
    {
        for (int i = 0; i < N; i++) {
            #pragma omp task firstprivate(i)
            {
                unsigned seed = (unsigned)i * 2654435761u;
                int escolha = (int)(rand_r(&seed) % M);

                omp_set_lock(&locks[escolha]);
                inserir(&listas[escolha], i);
                omp_unset_lock(&locks[escolha]);
            }
        }
    }

    printf("=== Parte 2: %d listas, omp_lock_t (%d threads) ===\n", M, NTHREADS);
    int total = 0;
    for (int i = 0; i < M; i++) {
        int t = tamanho(listas[i]);
        printf("  Lista %d: %d elementos\n", i, t);
        total += t;
        liberar(listas[i]);
    }
    printf("  Total  : %d %s\n", total,
           total == N ? "(correto)" : "(ERRO)");

    for (int i = 0; i < M; i++) omp_destroy_lock(&locks[i]);
    free(locks);
    free(listas);
}

int main(int argc, char *argv[]) {
    int M = (argc > 1) ? atoi(argv[1]) : M_PADRAO;
    if (M < 2) { fprintf(stderr, "M deve ser >= 2\n"); return 1; }

    parte1();
    parte2(M);
    return 0;
}
