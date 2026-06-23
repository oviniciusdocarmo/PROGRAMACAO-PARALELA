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

/* ── V1: contador compartilhado + #pragma omp critical ────────────────────*/
static double v1_shared_critical(void) {
    long hits = 0;
    omp_set_num_threads(NTHREADS);
    #pragma omp parallel
    {
        unsigned seed = SEED ^ (unsigned)omp_get_thread_num();
        #pragma omp for
        for (long i = 0; i < N; i++) {
            double x = rand_r(&seed) / (double)RAND_MAX;
            double y = rand_r(&seed) / (double)RAND_MAX;
            if (x*x + y*y <= 1.0) {
                #pragma omp critical
                hits++;
            }
        }
    }
    return 4.0 * hits / N;
}

/* ── V2: contador compartilhado + #pragma omp atomic ─────────────────────*/
static double v2_shared_atomic(void) {
    long hits = 0;
    omp_set_num_threads(NTHREADS);
    #pragma omp parallel
    {
        unsigned seed = SEED ^ (unsigned)omp_get_thread_num();
        #pragma omp for
        for (long i = 0; i < N; i++) {
            double x = rand_r(&seed) / (double)RAND_MAX;
            double y = rand_r(&seed) / (double)RAND_MAX;
            if (x*x + y*y <= 1.0) {
                #pragma omp atomic
                hits++;
            }
        }
    }
    return 4.0 * hits / N;
}

/* ── V3: contador privado + #pragma omp critical ─────────────────────────*/
static double v3_private_critical(void) {
    long hits = 0;
    omp_set_num_threads(NTHREADS);
    #pragma omp parallel
    {
        unsigned seed = SEED ^ (unsigned)omp_get_thread_num();
        long local = 0;
        for (long i = 0; i < N / NTHREADS; i++) {
            double x = rand_r(&seed) / (double)RAND_MAX;
            double y = rand_r(&seed) / (double)RAND_MAX;
            if (x*x + y*y <= 1.0) local++;
        }
        #pragma omp critical
        hits += local;
    }
    return 4.0 * hits / N;
}

/* ── V4: contador privado + #pragma omp atomic ───────────────────────────*/
static double v4_private_atomic(void) {
    long hits = 0;
    omp_set_num_threads(NTHREADS);
    #pragma omp parallel
    {
        unsigned seed = SEED ^ (unsigned)omp_get_thread_num();
        long local = 0;
        for (long i = 0; i < N / NTHREADS; i++) {
            double x = rand_r(&seed) / (double)RAND_MAX;
            double y = rand_r(&seed) / (double)RAND_MAX;
            if (x*x + y*y <= 1.0) local++;
        }
        #pragma omp atomic
        hits += local;
    }
    return 4.0 * hits / N;
}

/* ── V5: reduction ────────────────────────────────────────────────────────*/
static double v5_reduction(void) {
    long hits = 0;
    omp_set_num_threads(NTHREADS);
    #pragma omp parallel for reduction(+:hits)
    for (long i = 0; i < N; i++) {
        unsigned seed = SEED ^ ((unsigned)omp_get_thread_num() * 2654435761u
                                + (unsigned)i);
        double x = rand_r(&seed) / (double)RAND_MAX;
        double y = rand_r(&seed) / (double)RAND_MAX;
        if (x*x + y*y <= 1.0) hits++;
    }
    return 4.0 * hits / N;
}

int main(void) {
    struct timespec ini, fim;

    printf("Estimativa de π — Monte Carlo  (N=%ldM, %d threads)\n\n",
           N / 1000000L, NTHREADS);
    printf("%-30s  %-14s  %-10s  %-10s\n",
           "Versão", "π estimado", "Tempo(s)", "Sync/iter");
    printf("%-30s  %-14s  %-10s  %-10s\n",
           "------------------------------", "--------------",
           "----------", "----------");

#define MEDIR(label, sync_desc, expr) \
    do { \
        clock_gettime(CLOCK_MONOTONIC, &ini); \
        double pi_r = (expr); \
        clock_gettime(CLOCK_MONOTONIC, &fim); \
        printf("%-30s  %-14.8f  %-10.4f  %s\n", \
               (label), pi_r, elapsed(ini, fim), (sync_desc)); \
    } while (0);

    MEDIR("V1 shared+critical",   "~78M mutex",   v1_shared_critical())
    MEDIR("V2 shared+atomic",     "~78M atomic",  v2_shared_atomic())
    MEDIR("V3 private+critical",  "4 mutex",      v3_private_critical())
    MEDIR("V4 private+atomic",    "4 atomic",     v4_private_atomic())
    MEDIR("V5 reduction",         "0 (impl.)",    v5_reduction())

    printf("\nπ referência: %.8f\n", PI_REF);
    return 0;
}
