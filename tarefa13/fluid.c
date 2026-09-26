/* Tarefa 13: Navier-Stokes (difusão viscosa, stencil de 5 pontos) da Tarefa 12,
 * versão final (v4). A afinidade é escolhida por OMP_PROC_BIND e OMP_PLACES.
 * Uso: ./fluid <n> <passos>   ->  imprime "threads,tempo_s" */
#include <stdio.h>
#include <stdlib.h>
#include <omp.h>

#define R 0.01 /* nu*dt/dx^2 */

int main(int argc, char **argv) {
    if (argc != 3) return 1;
    int n = atoi(argv[1]), passos = atoi(argv[2]);
    double *u = malloc(sizeof(double) * n * n);
    double *v = malloc(sizeof(double) * n * n);

    /* first touch: cada thread inicializa as linhas que vai calcular */
    #pragma omp parallel for schedule(static)
    for (int i = 0; i < n; i++)
        for (int j = 0; j < n; j++) {
            u[i * n + j] = (i == n / 2 && j == n / 2) ? 1.0 : 0.0;
            v[i * n + j] = 0.0;
        }

    double t0 = omp_get_wtime();
    #pragma omp parallel
    for (int t = 0; t < passos; t++) {
        double *a = (t % 2 == 0) ? u : v;
        double *b = (t % 2 == 0) ? v : u;
        #pragma omp for schedule(static)
        for (int i = 1; i < n - 1; i++)
            for (int j = 1; j < n - 1; j++)
                b[i * n + j] = a[i * n + j] + R * (a[(i + 1) * n + j] + a[(i - 1) * n + j]
                             + a[i * n + j + 1] + a[i * n + j - 1] - 4 * a[i * n + j]);
    }
    printf("%d,%f\n", omp_get_max_threads(), omp_get_wtime() - t0);

    free(u);
    free(v);
    return 0;
}
