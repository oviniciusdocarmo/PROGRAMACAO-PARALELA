/* Tarefa 12 — binário instrumentado para o PaScal Analyzer.
 *
 * Mesmo núcleo numérico de fluid_scale.c (stencil.h), reempacotado no formato
 * que o PaScal Analyzer espera: um executável que recebe *o tamanho do
 * problema* como argumento e roda uma vez. Quem varia núcleos, tamanhos e
 * repetições é o próprio analyzer (flags --cors, --ipts, --rpts), e não um
 * laço dentro do programa.
 *
 * A versão do código é escolhida em tempo de compilação (-DVERSAO=k), porque
 * cada versão precisa ser um executável distinto para o analyzer comparar.
 *
 *   make pascal        → pascal_fluid_v1 .. pascal_fluid_v4
 *   ./pascal_fluid_v4 4096
 *
 * Instrumentação manual (-t man): duas regiões marcadas.
 *
 *   região 1 — inicialização: alocação, first touch e condição inicial
 *   região 2 — cálculo:       o laço do tempo
 *
 * Separar as duas importa para a análise: o que distingue a v3 da v2 está na
 * região 1 (quem toca a memória primeiro), mas o efeito aparece na região 2
 * (onde o stencil lê essa memória). Marcando as duas, o PaScal Viewer mostra
 * a causa e a consequência lado a lado, em vez de um número agregado só.
 */

#include "stencil.h"
#include <pascalops.h>

#ifndef VERSAO
#define VERSAO 4
#endif

#ifndef NT
#define NT 50           /* passos de tempo; fixo para que o único parâmetro
                           livre seja o tamanho do problema, como o analyzer
                           pressupõe */
#endif

int main(int argc, char **argv) {
    if (argc != 2) {
        fprintf(stderr, "uso: %s <n>   (grade n×n, versão %d)\n", argv[0], VERSAO);
        return EXIT_FAILURE;
    }
    size_t n = strtoul(argv[1], NULL, 10);
    if (n < 8) { fprintf(stderr, "n muito pequeno\n"); return EXIT_FAILURE; }

    const int ft = VERSOES[VERSAO].first_touch;

    pascal_start(1);                                   /* ── inicialização ── */
    double *u  = ft ? aloca_first_touch(n) : aloca_serial(n);
    double *un = ft ? aloca_first_touch(n) : aloca_serial(n);
    inicia_perturbacao(u, n, ft);
    pascal_stop(1);

    pascal_start(2);                                   /* ── cálculo ──────── */
    double t = VERSOES[VERSAO].fn(u, un, n, NT);
    pascal_stop(2);

    /* Vai para stderr, e não stdout, porque o analyzer captura o stdout do
       processo filho. Pelo stderr a linha chega ao log do job, o que permite
       conferir duas coisas que invalidariam o estudo inteiro se estivessem
       erradas: que o checksum não mudou, e que o número de threads realmente
       acompanha o `-c` do analyzer (e não ficou no default do nó, o que
       significaria 128 threads disputando os cores de uma execução de 1). */
    fprintf(stderr, "%s n=%zu passos=%d threads=%d tempo=%.6f checksum=%.12e\n",
            VERSOES[VERSAO].nome, n, NT, omp_get_max_threads(), t,
            checksum(resultado(VERSAO, u, un, NT), n));

    free(u); free(un);
    return EXIT_SUCCESS;
}
