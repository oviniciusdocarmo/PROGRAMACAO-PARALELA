#define _POSIX_C_SOURCE 199309L
#include <stdio.h>
#include <math.h>
#include <time.h>
#include <omp.h>

#define N       10000000
#define BILLION 1000000000.0

static double elapsed(struct timespec a, struct timespec b) {
    return (b.tv_sec - a.tv_sec) + (b.tv_nsec - a.tv_nsec) / BILLION;
}

static int is_prime(int n) {
    if (n < 2) return 0;
    if (n == 2) return 1;
    if (n % 2 == 0) return 0;
    int lim = (int)sqrt((double)n);
    for (int d = 3; d <= lim; d += 2)
        if (n % d == 0) return 0;
    return 1;
}

/* ── Versão sequencial ─────────────────────────────────────────────────── */
static long contar_sequencial(void) {
    long count = 0;
    for (int i = 2; i <= N; i++)
        if (is_prime(i))
            count++;
    return count;
}

/* ── Versão paralela INGÊNUA — lógica original inalterada ──────────────
   Problema 1: condição de corrida em count++ (read-modify-write não atômico)
   Problema 2: schedule(static) distribui blocos contíguos, mas verificar
               primalidade de números grandes custa mais → últimas threads
               recebem carga desproporcional.                               */
static long contar_paralelo_ingnuo(int n_threads) {
    long count = 0;
    omp_set_num_threads(n_threads);
    #pragma omp parallel for
    for (int i = 2; i <= N; i++)
        if (is_prime(i))
            count++;   /* RACE CONDITION */
    return count;
}

int main(void) {
    struct timespec ini, fim;

    /* sequencial */
    clock_gettime(CLOCK_MONOTONIC, &ini);
    long seq = contar_sequencial();
    clock_gettime(CLOCK_MONOTONIC, &fim);
    double t_seq = elapsed(ini, fim);

    printf("Contagem de primos entre 2 e %d\n\n", N);
    printf("%-25s  %-10s  %-10s  %-8s\n",
           "Versão", "Primos", "Tempo(s)", "Correto?");
    printf("%-25s  %-10s  %-10s  %-8s\n",
           "-------------------------", "----------", "----------", "--------");
    printf("%-25s  %-10ld  %-10.4f  %-8s\n",
           "Sequencial", seq, t_seq, "sim");

    int threads[] = {2, 4, 8};
    for (int k = 0; k < 3; k++) {
        int t = threads[k];
        char label[32];
        snprintf(label, sizeof(label), "Paralela ingênua (%d thr)", t);

        clock_gettime(CLOCK_MONOTONIC, &ini);
        long par = contar_paralelo_ingnuo(t);
        clock_gettime(CLOCK_MONOTONIC, &fim);
        double t_par = elapsed(ini, fim);

        printf("%-25s  %-10ld  %-10.4f  %-8s\n",
               label, par, t_par, par == seq ? "sim" : "NAO");
    }

    return 0;
}
