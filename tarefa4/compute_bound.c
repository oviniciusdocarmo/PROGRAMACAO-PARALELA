#define _POSIX_C_SOURCE 199309L
#include <stdio.h>
#include <stdlib.h>
#include <math.h>
#include <time.h>
#include <omp.h>

/* Cada iteração executa várias operações de ponto flutuante pesadas,
   tornando o gargalo o hardware de FPU, não a memória. */
#define N        10000000L    /* 10M elementos — dados cabem no cache */
#define ROUNDS   20           /* repetições de sin/cos/log/exp por elemento */
#define BILLION  1000000000.0

static double elapsed(struct timespec a, struct timespec b) {
    return (b.tv_sec - a.tv_sec) + (b.tv_nsec - a.tv_nsec) / BILLION;
}

static double calcular(double x) {
    double r = x;
    for (int j = 0; j < ROUNDS; j++) {
        r = sin(r) + cos(r * 1.1);
        r = log(fabs(r) + 1.0) + exp(-fabs(r) * 0.01);
        r = sqrt(fabs(r) + 1e-9);
    }
    return r;
}

int main(void) {
    double *v = malloc(N * sizeof(double));
    double *u = malloc(N * sizeof(double));
    if (!v || !u) { fprintf(stderr, "malloc falhou\n"); return 1; }

    for (long i = 0; i < N; i++) v[i] = (double)(i + 1);

    int threads[] = {1, 2, 4, 8, 16};
    int n_casos   = sizeof(threads) / sizeof(threads[0]);

    printf("Compute-bound: %d operações FP pesadas por elemento, %ldM elementos\n\n",
           ROUNDS * 4, N / 1000000L);
    printf("%-8s  %-14s  %-10s  %-10s\n",
           "Threads", "Checksum", "Tempo(s)", "Speedup");
    printf("%-8s  %-14s  %-10s  %-10s\n",
           "--------", "--------------", "----------", "----------");

    double t_base = 0.0;
    for (int k = 0; k < n_casos; k++) {
        int t = threads[k];
        omp_set_num_threads(t);

        struct timespec ini, fim;
        double checksum = 0.0;

        clock_gettime(CLOCK_MONOTONIC, &ini);
        #pragma omp parallel for reduction(+:checksum) schedule(static)
        for (long i = 0; i < N; i++) {
            u[i] = calcular(v[i]);
            checksum += u[i];
        }
        clock_gettime(CLOCK_MONOTONIC, &fim);

        double tempo = elapsed(ini, fim);
        if (k == 0) t_base = tempo;

        printf("%-8d  %-14.6f  %-10.4f  %-10.4f\n",
               t, checksum, tempo, t_base / tempo);
    }

    free(v);
    free(u);
    return 0;
}
