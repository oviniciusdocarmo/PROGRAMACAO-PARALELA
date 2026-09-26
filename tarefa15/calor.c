/* Difusão de calor numa barra 1D dividida entre processos MPI.
 * Uso: mpirun -np P ./calor <versao> <pontos por processo> <passos>
 *   versao 1: MPI_Send/MPI_Recv
 *   versao 2: MPI_Isend/MPI_Irecv + MPI_Wait
 *   versao 3: MPI_Isend/MPI_Irecv + MPI_Test (atualiza o interior enquanto espera) */
#include <mpi.h>
#include <stdio.h>
#include <stdlib.h>

#define K 0.25     /* alfa*dt/dx^2 (estável se <= 0,5) */
#define BLOCO 256  /* pontos atualizados entre dois MPI_Test */

/* Atualiza os pontos i = a .. b-1. */
static void atualiza(double *u, double *v, int a, int b) {
    for (int i = a; i < b; i++)
        v[i] = u[i] + K * (u[i - 1] - 2 * u[i] + u[i + 1]);
}

/* 1 quando todas as requisições terminaram. */
static int pronto(MPI_Request *req, int nr) {
    int ok = 1, f;
    for (int k = 0; k < nr; k++) {
        MPI_Test(&req[k], &f, MPI_STATUS_IGNORE);
        ok = ok && f;
    }
    return ok;
}

int main(int argc, char **argv) {
    int rank, size;
    MPI_Init(&argc, &argv);
    MPI_Comm_rank(MPI_COMM_WORLD, &rank);
    MPI_Comm_size(MPI_COMM_WORLD, &size);

    int versao = atoi(argv[1]), n = atoi(argv[2]), passos = atoi(argv[3]);
    int esq = rank - 1, dir = rank + 1;             /* vizinhos */

    /* u[1..n]: trecho do processo; u[0] e u[n+1]: células extras (bordas) */
    double *u = calloc(n + 2, sizeof(double));
    double *v = calloc(n + 2, sizeof(double));
    if (rank == 0) u[0] = v[0] = 100.0;             /* ponta esquerda quente */

    double t0 = MPI_Wtime();
    for (int p = 0; p < passos; p++) {
        if (versao == 1) {
            /* pares enviam primeiro e ímpares recebem, depois invertem */
            for (int f = 0; f < 2; f++) {
                if ((rank + f) % 2 == 0) {
                    if (esq >= 0)   MPI_Send(&u[1], 1, MPI_DOUBLE, esq, 0, MPI_COMM_WORLD);
                    if (dir < size) MPI_Send(&u[n], 1, MPI_DOUBLE, dir, 0, MPI_COMM_WORLD);
                } else {
                    if (esq >= 0)   MPI_Recv(&u[0], 1, MPI_DOUBLE, esq, 0, MPI_COMM_WORLD, MPI_STATUS_IGNORE);
                    if (dir < size) MPI_Recv(&u[n + 1], 1, MPI_DOUBLE, dir, 0, MPI_COMM_WORLD, MPI_STATUS_IGNORE);
                }
            }
            atualiza(u, v, 1, n + 1);
        } else {
            MPI_Request req[4];
            int nr = 0;
            if (esq >= 0) {
                MPI_Irecv(&u[0], 1, MPI_DOUBLE, esq, 0, MPI_COMM_WORLD, &req[nr++]);
                MPI_Isend(&u[1], 1, MPI_DOUBLE, esq, 0, MPI_COMM_WORLD, &req[nr++]);
            }
            if (dir < size) {
                MPI_Irecv(&u[n + 1], 1, MPI_DOUBLE, dir, 0, MPI_COMM_WORLD, &req[nr++]);
                MPI_Isend(&u[n], 1, MPI_DOUBLE, dir, 0, MPI_COMM_WORLD, &req[nr++]);
            }
            if (versao == 2) {
                atualiza(u, v, 2, n);               /* interior não usa as bordas */
                for (int k = 0; k < nr; k++) MPI_Wait(&req[k], MPI_STATUS_IGNORE);
            } else {
                int i = 2;
                while (!pronto(req, nr) && i < n) { /* um bloco por teste */
                    int fim = i + BLOCO < n ? i + BLOCO : n;
                    atualiza(u, v, i, fim);
                    i = fim;
                }
                atualiza(u, v, i, n);               /* restante do interior */
                while (!pronto(req, nr)) {}         /* interior pronto: só espera */
            }
            atualiza(u, v, 1, 2);                   /* bordas, com as células extras */
            atualiza(u, v, n, n + 1);
        }
        double *t = u; u = v; v = t;
    }
    double t = MPI_Wtime() - t0;

    if (rank == 0)   /* versao,processos,pontos por processo,passos,tempo,u[n] */
        printf("%d,%d,%d,%d,%.6f,%.10f\n", versao, size, n, passos, t, u[n]);
    free(u);
    free(v);
    MPI_Finalize();
    return 0;
}
