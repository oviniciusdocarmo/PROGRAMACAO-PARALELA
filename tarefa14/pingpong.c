/* Ping-pong MPI: processo 0 envia, processo 1 devolve a mesma mensagem.
 * Saída CSV: bytes,trocas,tempo_total_s,tempo_por_troca_us,banda_MBps */
#include <mpi.h>
#include <stdio.h>
#include <stdlib.h>

/* Uma troca = ida (0 -> 1) + volta (1 -> 0). */
static void troca(char *buf, int n, int rank) {
    if (rank == 0) {
        MPI_Send(buf, n, MPI_CHAR, 1, 0, MPI_COMM_WORLD);
        MPI_Recv(buf, n, MPI_CHAR, 1, 0, MPI_COMM_WORLD, MPI_STATUS_IGNORE);
    } else {
        MPI_Recv(buf, n, MPI_CHAR, 0, 0, MPI_COMM_WORLD, MPI_STATUS_IGNORE);
        MPI_Send(buf, n, MPI_CHAR, 0, 0, MPI_COMM_WORLD);
    }
}

int main(int argc, char **argv) {
    int rank, size;
    MPI_Init(&argc, &argv);
    MPI_Comm_rank(MPI_COMM_WORLD, &rank);
    MPI_Comm_size(MPI_COMM_WORLD, &size);
    if (size != 2) {
        if (rank == 0) fprintf(stderr, "Use exatamente 2 processos.\n");
        MPI_Finalize();
        return 1;
    }

    const int max = 16 << 20;                     /* 8 B até 16 MB */
    char *buf = calloc(max, 1);
    if (rank == 0) printf("bytes,trocas,tempo_total_s,tempo_por_troca_us,banda_MBps\n");

    for (int n = 8; n <= max; n *= 2) {
        int trocas = n <= 65536 ? 10000 : 200;

        for (int i = 0; i < 10; i++) troca(buf, n, rank);   /* aquecimento */

        double t0 = MPI_Wtime();
        for (int i = 0; i < trocas; i++) troca(buf, n, rank);
        double t = MPI_Wtime() - t0;

        if (rank == 0) {
            double rtt = t / trocas;              /* ida e volta */
            printf("%d,%d,%.6f,%.3f,%.1f\n", n, trocas, t, rtt * 1e6,
                   2.0 * n / rtt / 1e6);          /* 2n bytes por troca */
        }
    }
    free(buf);
    MPI_Finalize();
    return 0;
}
