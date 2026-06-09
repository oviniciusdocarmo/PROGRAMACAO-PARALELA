#define _POSIX_C_SOURCE 199309L
#include <stdio.h>
#include <stdlib.h>
#include <math.h>
#include <time.h>
#include <omp.h>

#define N        100000000L
#define SEED     12345u
#define PI_REF   3.14159265358979323846
#define BILLION  1000000000.0
#define NTHREADS 4

static double elapsed(struct timespec a, struct timespec b) {
    return (b.tv_sec - a.tv_sec) + (b.tv_nsec - a.tv_nsec) / BILLION;
}

/* ── 1. Versão sequencial ──────────────────────────────────────────────── */
static double pi_sequencial(void) {
    long dentro = 0;
    unsigned seed = SEED;
    for (long i = 0; i < N; i++) {
        double x = rand_r(&seed) / (double)RAND_MAX;
        double y = rand_r(&seed) / (double)RAND_MAX;
        if (x*x + y*y <= 1.0) dentro++;
    }
    return 4.0 * dentro / N;
}

/* ── 2. Paralela ingênua: #pragma omp parallel for sem proteção ─────────
   Problemas:
     a) dentro++ não é atômico → race condition → resultado errado
     b) seed compartilhada  → race condition no próprio RNG             */
static double pi_ingenua(void) {
    long dentro = 0;
    unsigned seed = SEED;
    omp_set_num_threads(NTHREADS);
    #pragma omp parallel for
    for (long i = 0; i < N; i++) {
        double x = rand_r(&seed) / (double)RAND_MAX;
        double y = rand_r(&seed) / (double)RAND_MAX;
        if (x*x + y*y <= 1.0)
            dentro++;               /* RACE CONDITION */
    }
    return 4.0 * dentro / N;
}

/* ── 3. Com #pragma omp critical ──────────────────────────────────────────
   Correto, mas serializa todo incremento → lento.                       */
static double pi_critical(void) {
    long dentro = 0;
    omp_set_num_threads(NTHREADS);
    #pragma omp parallel for
    for (long i = 0; i < N; i++) {
        unsigned seed = SEED ^ (unsigned)(i * 2654435761u);   /* seed por iter */
        double x = rand_r(&seed) / (double)RAND_MAX;
        double y = rand_r(&seed) / (double)RAND_MAX;
        if (x*x + y*y <= 1.0) {
            #pragma omp critical
            dentro++;
        }
    }
    return 4.0 * dentro / N;
}

/* ── 4. Com #pragma omp parallel + for + cláusulas ───────────────────────
   Demonstra: shared, firstprivate, private, lastprivate, default(none).

   shared(dentro, seed_last)  — variáveis visíveis a todos os threads;
                                dentro protegida por critical.
   firstprivate(seed_master)  — cada thread recebe cópia *inicializada*
                                com o valor do master thread (SEED).
                                Depois deriva seed única via XOR com o
                                thread ID para evitar sequências iguais.
   private(local)             — cada thread tem cópia *não-inicializada*;
                                inicializada explicitamente logo abaixo.
   lastprivate(seed_last)     — ao fim, a variável recebe o valor do
                                thread que executou a última iteração
                                lógica (útil para continuar a sequência).
   default(none)              — o compilador rejeita qualquer variável não
                                declarada explicitamente; força o programador
                                a raciocinar sobre o escopo de cada variável,
                                evitando sharing acidental em código complexo. */
static double pi_clausulas(unsigned *seed_last_out) {
    long dentro = 0;
    long local;                  /* declarada no escopo externo para private() */
    unsigned seed_master = SEED;
    unsigned seed_last   = 0;

    omp_set_num_threads(NTHREADS);

    #pragma omp parallel default(none) \
        shared(dentro, seed_last) \
        firstprivate(seed_master) \
        private(local)
    {
        /* firstprivate: seed_master copiado do master; derivar seed única */
        unsigned seed = seed_master ^ (unsigned)omp_get_thread_num();
        local = 0;

        #pragma omp for lastprivate(seed_last)
        for (long i = 0; i < N; i++) {
            double x = rand_r(&seed) / (double)RAND_MAX;
            double y = rand_r(&seed) / (double)RAND_MAX;
            if (x*x + y*y <= 1.0) local++;
            /* lastprivate captura o seed da última iteração lógica (i == N-1) */
            seed_last = seed;
        }

        #pragma omp critical
        dentro += local;
    }

    if (seed_last_out) *seed_last_out = seed_last;
    return 4.0 * dentro / N;
}

/* ── 5. Com reduction (idiomático) ───────────────────────────────────────
   reduction(+:dentro) cria cópia local por thread, acumula em paralelo
   e soma os parciais ao final — sem critical, sem corrida, máxima efic. */
static double pi_reduction(void) {
    long dentro = 0;
    unsigned seed_master = SEED;

    omp_set_num_threads(NTHREADS);

    #pragma omp parallel for default(none) \
        shared(seed_master) \
        reduction(+:dentro)
    for (long i = 0; i < N; i++) {
        unsigned seed = seed_master ^ (unsigned)(omp_get_thread_num() * 2654435761u + (unsigned)i);
        double x = rand_r(&seed) / (double)RAND_MAX;
        double y = rand_r(&seed) / (double)RAND_MAX;
        if (x*x + y*y <= 1.0) dentro++;
    }
    return 4.0 * dentro / N;
}

/* ── main ─────────────────────────────────────────────────────────────── */
int main(void) {
    struct timespec ini, fim;

    printf("Estimativa de π — Monte Carlo  (N = %ldM, %d threads)\n\n",
           N / 1000000L, NTHREADS);
    printf("%-32s  %-12s  %-10s  %-8s\n",
           "Versão", "π estimado", "Tempo(s)", "Correto?");
    printf("%-32s  %-12s  %-10s  %-8s\n",
           "--------------------------------", "------------", "----------", "--------");

    double pi, t;

#define MEDIR(label, expr, correto) \
    clock_gettime(CLOCK_MONOTONIC, &ini); \
    pi = (expr); \
    clock_gettime(CLOCK_MONOTONIC, &fim); \
    t = elapsed(ini, fim); \
    printf("%-32s  %-12.8f  %-10.4f  %-8s\n", \
           (label), pi, t, (correto) ? "sim" : "NAO");

    MEDIR("Sequencial",                pi_sequencial(),    1)
    MEDIR("Ingênua (race condition)",  pi_ingenua(),       fabs(pi - PI_REF) < 0.01)
    MEDIR("Com omp critical",          pi_critical(),      1)

    unsigned seed_final;
    clock_gettime(CLOCK_MONOTONIC, &ini);
    pi = pi_clausulas(&seed_final);
    clock_gettime(CLOCK_MONOTONIC, &fim);
    t = elapsed(ini, fim);
    printf("%-32s  %-12.8f  %-10.4f  %-8s  (seed_last=%u)\n",
           "parallel+for+cláusulas", pi, t, "sim", seed_final);

    MEDIR("Com reduction",             pi_reduction(),     1)

    printf("\nπ referência: %.8f\n", PI_REF);
    return 0;
}
