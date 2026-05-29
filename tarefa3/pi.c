#define _POSIX_C_SOURCE 199309L
#include <stdio.h>
#include <math.h>
#include <time.h>

#define PI_REF  3.14159265358979323846
#define BILLION 1000000000.0

static double elapsed(struct timespec a, struct timespec b) {
    return (b.tv_sec - a.tv_sec) + (b.tv_nsec - a.tv_nsec) / BILLION;
}

/* Série de Leibniz: π/4 = 1 - 1/3 + 1/5 - 1/7 + ... */
static double calcular_pi(long long n) {
    double soma = 0.0;
    for (long long i = 0; i < n; i++) {
        double termo = 1.0 / (2 * i + 1);
        if (i % 2 == 0)
            soma += termo;
        else
            soma -= termo;
    }
    return 4.0 * soma;
}

int main(void) {
    long long iteracoes[] = {
        100LL,
        1000LL,
        10000LL,
        100000LL,
        1000000LL,
        10000000LL,
        100000000LL,
        1000000000LL
    };
    int n_casos = sizeof(iteracoes) / sizeof(iteracoes[0]);

    printf("%-15s  %-22s  %-12s  %-12s\n",
           "Iterações", "π aproximado", "Erro absoluto", "Tempo (s)");
    printf("%-15s  %-22s  %-12s  %-12s\n",
           "---------------", "----------------------", "------------", "------------");

    for (int k = 0; k < n_casos; k++) {
        struct timespec ini, fim;
        long long n = iteracoes[k];

        clock_gettime(CLOCK_MONOTONIC, &ini);
        double pi_aprox = calcular_pi(n);
        clock_gettime(CLOCK_MONOTONIC, &fim);

        double t    = elapsed(ini, fim);
        double erro = fabs(pi_aprox - PI_REF);

        printf("%-15lld  %.20f  %-12.2e  %.6f\n", n, pi_aprox, erro, t);
    }

    return 0;
}
