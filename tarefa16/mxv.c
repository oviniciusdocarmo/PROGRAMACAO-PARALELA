/* Produto matriz-vetor y = A.x com MPI: A dividida por linhas (MPI_Scatter),
 * x inteiro para todos (MPI_Bcast) e y juntado no processo 0 (MPI_Gather).
 * Uso: mpirun -np P ./mxv <M> <N>   (M deve ser múltiplo de P)
 * Saída: M,N,processos,tempo_total_s,distribuicao_s,calculo_s,coleta_s,erros */
#include <mpi.h>
#include <stdio.h>
#include <stdlib.h>

int main(int argc, char **argv) {
    int rank, size;
    MPI_Init(&argc, &argv);
    MPI_Comm_rank(MPI_COMM_WORLD, &rank);
    MPI_Comm_size(MPI_COMM_WORLD, &size);

    int m = atoi(argv[1]), n = atoi(argv[2]);
    int linhas = m / size;                          /* linhas por processo */

    double *A = NULL, *y = NULL;
    double *x = malloc(n * sizeof(double));
    double *a = malloc((size_t)linhas * n * sizeof(double));  /* linhas locais */
    double *yl = malloc(linhas * sizeof(double));

    if (rank == 0) {                                /* A[i][j] = i + j, x = 1 */
        A = malloc((size_t)m * n * sizeof(double));
        y = malloc(m * sizeof(double));
        for (int i = 0; i < m; i++)
            for (int j = 0; j < n; j++) A[(size_t)i * n + j] = i + j;
        for (int j = 0; j < n; j++) x[j] = 1.0;
    }

    double t0 = MPI_Wtime();
    MPI_Scatter(A, linhas * n, MPI_DOUBLE, a, linhas * n, MPI_DOUBLE, 0, MPI_COMM_WORLD);
    MPI_Bcast(x, n, MPI_DOUBLE, 0, MPI_COMM_WORLD);
    double t1 = MPI_Wtime();

    for (int i = 0; i < linhas; i++) {
        double s = 0.0;
        for (int j = 0; j < n; j++) s += a[(size_t)i * n + j] * x[j];
        yl[i] = s;
    }
    double t2 = MPI_Wtime();

    MPI_Gather(yl, linhas, MPI_DOUBLE, y, linhas, MPI_DOUBLE, 0, MPI_COMM_WORLD);
    double t3 = MPI_Wtime();

    if (rank == 0) {                                /* y[i] = n*i + n(n-1)/2 */
        int erros = 0;
        for (int i = 0; i < m; i++)
            if (y[i] != (double)n * i + (double)n * (n - 1) / 2) erros++;
        printf("%d,%d,%d,%.6f,%.6f,%.6f,%.6f,%d\n", m, n, size,
               t3 - t0, t1 - t0, t2 - t1, t3 - t2, erros);
        free(A);
        free(y);
    }
    free(x);
    free(a);
    free(yl);
    MPI_Finalize();
    return 0;
}
