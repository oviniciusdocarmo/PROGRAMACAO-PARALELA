/* Produto matriz-vetor y = A.x com MPI: A dividida por colunas (MPI_Scatter com
 * tipo derivado), x dividido em pedaços (MPI_Scatter) e as contribuições
 * parciais de y somadas no processo 0 (MPI_Reduce com MPI_SUM).
 * Uso: mpirun -np P ./mxv <M> <N>   (N deve ser múltiplo de P)
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
    int colunas = n / size;                         /* colunas por processo */

    /* uma coluna: m doubles separados por n; extent de 1 double para que a
     * próxima coluna comece logo no elemento seguinte */
    MPI_Datatype col, coluna;
    MPI_Type_vector(m, 1, n, MPI_DOUBLE, &col);
    MPI_Type_create_resized(col, 0, sizeof(double), &coluna);
    MPI_Type_commit(&coluna);

    double *A = NULL, *x = NULL, *y = NULL;
    double *a = malloc((size_t)m * colunas * sizeof(double)); /* colunas locais */
    double *xl = malloc(colunas * sizeof(double));
    double *yl = calloc(m, sizeof(double));         /* contribuição parcial */

    if (rank == 0) {                                /* A[i][j] = i + j, x = 1 */
        A = malloc((size_t)m * n * sizeof(double));
        x = malloc(n * sizeof(double));
        y = malloc(m * sizeof(double));
        for (int i = 0; i < m; i++)
            for (int j = 0; j < n; j++) A[(size_t)i * n + j] = i + j;
        for (int j = 0; j < n; j++) x[j] = 1.0;
    }

    double t0 = MPI_Wtime();
    /* cada processo recebe as suas colunas uma após a outra: a[j*m + i] */
    MPI_Scatter(A, colunas, coluna, a, m * colunas, MPI_DOUBLE, 0, MPI_COMM_WORLD);
    MPI_Scatter(x, colunas, MPI_DOUBLE, xl, colunas, MPI_DOUBLE, 0, MPI_COMM_WORLD);
    double t1 = MPI_Wtime();

    for (int j = 0; j < colunas; j++)
        for (int i = 0; i < m; i++) yl[i] += a[(size_t)j * m + i] * xl[j];
    double t2 = MPI_Wtime();

    MPI_Reduce(yl, y, m, MPI_DOUBLE, MPI_SUM, 0, MPI_COMM_WORLD);
    double t3 = MPI_Wtime();

    if (rank == 0) {                                /* y[i] = n*i + n(n-1)/2 */
        int erros = 0;
        for (int i = 0; i < m; i++)
            if (y[i] != (double)n * i + (double)n * (n - 1) / 2) erros++;
        printf("%d,%d,%d,%.6f,%.6f,%.6f,%.6f,%d\n", m, n, size,
               t3 - t0, t1 - t0, t2 - t1, t3 - t2, erros);
        free(A);
        free(x);
        free(y);
    }
    free(a);
    free(xl);
    free(yl);
    MPI_Finalize();
    return 0;
}
