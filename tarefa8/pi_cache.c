#define _POSIX_C_SOURCE 199309L
#include <stdio.h>
#include <stdlib.h>
#include <math.h>
#include <time.h>
#include <omp.h>

#define N        100000000L
#define NTHREADS 4
#define SEED     42u
#define PI_REF   3.14159265358979323846
#define BILLION  1000000000.0

static double elapsed(struct timespec a, struct timespec b) {
    return (b.tv_sec - a.tv_sec) + (b.tv_nsec - a.tv_nsec) / BILLION;
}

/* ── V1: rand() + #pragma omp critical ────────────────────────────────────
   rand() usa estado global protegido por mutex no glibc → todas as threads
   concorrem num mesmo lock a cada chamada (2× por ponto = 200M locks).
   O critical é executado apenas 4 vezes (uma por thread) — custo desprezível
   comparado à contenção no rand().                                         */
static double v1_rand_critical(void) {
    long total = 0;
    #pragma omp parallel num_threads(NTHREADS)
    {
        long local = 0;
        for (long i = 0; i < N / NTHREADS; i++) {
            double x = rand() / (double)RAND_MAX;
            double y = rand() / (double)RAND_MAX;
            if (x*x + y*y <= 1.0) local++;
        }
        #pragma omp critical
        total += local;
    }
    return 4.0 * total / N;
}

/* ── V2: rand() + vetor compartilhado (falso compartilhamento) ────────────
   hits[NTHREADS]: 4 × 8 bytes = 32 bytes → cabe em UMA cache line de 64 B.
   Toda escrita em hits[tid] invalida a cache line inteira para as outras
   threads, forçando recargas constantes (false sharing).
   Somado à contenção no rand(), torna esta versão a mais lenta.            */
static double v2_rand_vetor(void) {
    long hits[NTHREADS];
    for (int t = 0; t < NTHREADS; t++) hits[t] = 0;

    #pragma omp parallel num_threads(NTHREADS)
    {
        int tid = omp_get_thread_num();
        for (long i = 0; i < N / NTHREADS; i++) {
            double x = rand() / (double)RAND_MAX;
            double y = rand() / (double)RAND_MAX;
            if (x*x + y*y <= 1.0) hits[tid]++;   /* false sharing */
        }
    }

    long total = 0;
    for (int t = 0; t < NTHREADS; t++) total += hits[t];
    return 4.0 * total / N;
}

/* ── V3: rand_r() + #pragma omp critical ──────────────────────────────────
   rand_r() recebe a seed por ponteiro → cada thread tem sua própria seed
   (privada, na pilha) → zero contenção no RNG.
   O critical continua sendo executado apenas 4 vezes → custo desprezível.
   Resultado: a versão mais rápida.                                         */
static double v3_randr_critical(void) {
    long total = 0;
    #pragma omp parallel num_threads(NTHREADS)
    {
        unsigned seed = SEED ^ (unsigned)omp_get_thread_num();
        long local = 0;
        for (long i = 0; i < N / NTHREADS; i++) {
            double x = rand_r(&seed) / (double)RAND_MAX;
            double y = rand_r(&seed) / (double)RAND_MAX;
            if (x*x + y*y <= 1.0) local++;
        }
        #pragma omp critical
        total += local;
    }
    return 4.0 * total / N;
}

/* ── V4: rand_r() + vetor compartilhado (falso compartilhamento) ──────────
   RNG sem contenção, mas hits[NTHREADS] ainda cabe em uma cache line.
   A cada incremento de hits[tid], a cache line é invalidada para os outros
   núcleos, que precisam buscá-la novamente antes da próxima escrita.
   Com 100M iterações por thread, isso gera ~25M invalidações por núcleo.
   Resultado: pode ser mais LENTO que V3, onde o critical roda só 4 vezes. */
static double v4_randr_vetor(void) {
    long hits[NTHREADS];
    for (int t = 0; t < NTHREADS; t++) hits[t] = 0;

    #pragma omp parallel num_threads(NTHREADS)
    {
        int tid = omp_get_thread_num();
        unsigned seed = SEED ^ (unsigned)tid;
        for (long i = 0; i < N / NTHREADS; i++) {
            double x = rand_r(&seed) / (double)RAND_MAX;
            double y = rand_r(&seed) / (double)RAND_MAX;
            if (x*x + y*y <= 1.0) hits[tid]++;   /* false sharing */
        }
    }

    long total = 0;
    for (int t = 0; t < NTHREADS; t++) total += hits[t];
    return 4.0 * total / N;
}

int main(void) {
    struct timespec ini, fim;

    printf("Estimativa de π — Monte Carlo  (N=%ldM, %d threads, cache line=%d B)\n\n",
           N / 1000000L, NTHREADS, 64);
    printf("%-28s  %-6s  %-11s  %-10s  %-8s\n",
           "Versão", "RNG", "Acumulação", "Tempo(s)", "π");
    printf("%-28s  %-6s  %-11s  %-10s  %-8s\n",
           "----------------------------", "------", "-----------", "----------", "--------");

#define MEDIR(label, rng, acum, expr) \
    clock_gettime(CLOCK_MONOTONIC, &ini); \
    double pi_##label = (expr); \
    clock_gettime(CLOCK_MONOTONIC, &fim); \
    printf("%-28s  %-6s  %-11s  %-10.4f  %.6f\n", \
           #label, rng, acum, elapsed(ini, fim), pi_##label);

    MEDIR(V1_rand_critical,  "rand()",  "critical", v1_rand_critical())
    MEDIR(V2_rand_vetor,     "rand()",  "vetor",    v2_rand_vetor())
    MEDIR(V3_randr_critical, "rand_r()", "critical", v3_randr_critical())
    MEDIR(V4_randr_vetor,    "rand_r()", "vetor",    v4_randr_vetor())

    printf("\nπ referência: %.6f\n", PI_REF);
    return 0;
}
