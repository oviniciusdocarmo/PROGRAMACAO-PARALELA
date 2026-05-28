#define _POSIX_C_SOURCE 199309L
#include <stdio.h>
#include <time.h>

#define N        32000000
#define BILLION  1000000000.0

static double v[N];

static double elapsed(struct timespec a, struct timespec b) {
    return (b.tv_sec - a.tv_sec) + (b.tv_nsec - a.tv_nsec) / BILLION;
}

/* Loop 1: inicializa vetor — sem dependência entre iterações (ILP-friendly) */
void loop_init(void) {
    for (int i = 0; i < N; i++)
        v[i] = (double)i * 3.14159265 + 2.71828182;
}

/* Loop 2: soma acumulativa — dependência verdadeira (RAW) entre iterações */
double loop_soma_dep(void) {
    double soma = 0.0;
    for (int i = 0; i < N; i++)
        soma += v[i];
    return soma;
}

/* Loop 3: quebra a dependência com 4 acumuladores independentes */
double loop_soma_nodep(void) {
    double s0 = 0.0, s1 = 0.0, s2 = 0.0, s3 = 0.0;
    for (int i = 0; i < N; i += 4) {
        s0 += v[i];
        s1 += v[i + 1];
        s2 += v[i + 2];
        s3 += v[i + 3];
    }
    return s0 + s1 + s2 + s3;
}

int main(void) {
    struct timespec ini, fim;
    volatile double res;
    double t;

    clock_gettime(CLOCK_MONOTONIC, &ini);
    loop_init();
    clock_gettime(CLOCK_MONOTONIC, &fim);
    t = elapsed(ini, fim);
    printf("Loop 1 (init):        %.6f s\n", t);

    clock_gettime(CLOCK_MONOTONIC, &ini);
    res = loop_soma_dep();
    clock_gettime(CLOCK_MONOTONIC, &fim);
    t = elapsed(ini, fim);
    printf("Loop 2 (soma dep):    %.6f s  (res = %.2f)\n", t, res);

    clock_gettime(CLOCK_MONOTONIC, &ini);
    res = loop_soma_nodep();
    clock_gettime(CLOCK_MONOTONIC, &fim);
    t = elapsed(ini, fim);
    printf("Loop 3 (soma nodep):  %.6f s  (res = %.2f)\n", t, res);

    return 0;
}
