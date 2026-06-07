#define _POSIX_C_SOURCE 199309L
#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#include <omp.h>

#define N        100000000L   /* 100M doubles = ~800 MB, não cabe no cache */
#define BILLION  1000000000.0

static double elapsed(struct timespec a, struct timespec b) {
    return (b.tv_sec - a.tv_sec) + (b.tv_nsec - a.tv_nsec) / BILLION;
}

int main(void) {
    double *v = malloc(N * sizeof(double));
    if (!v) { fprintf(stderr, "malloc falhou\n"); return 1; }

    for (long i = 0; i < N; i++) v[i] = (double)i * 0.5;

    int threads[] = {1, 2, 4, 8, 16};
    int n_casos   = sizeof(threads) / sizeof(threads[0]);

    printf("Memory-bound: soma de vetor com %ldM elementos\n\n", N / 1000000L);
    printf("%-8s  %-14s  %-10s  %-10s\n",
           "Threads", "Soma", "Tempo(s)", "Speedup");
    printf("%-8s  %-14s  %-10s  %-10s\n",
           "--------", "--------------", "----------", "----------");

    double t_base = 0.0;
    for (int k = 0; k < n_casos; k++) {
        int t = threads[k];
        omp_set_num_threads(t);

        struct timespec ini, fim;
        double soma = 0.0;

        clock_gettime(CLOCK_MONOTONIC, &ini);
        #pragma omp parallel for reduction(+:soma) schedule(static)
        for (long i = 0; i < N; i++)
            soma += v[i];
        clock_gettime(CLOCK_MONOTONIC, &fim);

        double tempo = elapsed(ini, fim);
        if (k == 0) t_base = tempo;

        printf("%-8d  %-14.2e  %-10.4f  %-10.4f\n",
               t, soma, tempo, t_base / tempo);
    }

    free(v);
    return 0;
}
