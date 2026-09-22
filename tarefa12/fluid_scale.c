/* Tarefa 12 — Desempenho vs. escalabilidade
 *
 * Mesmo núcleo numérico da Tarefa 11 (Navier-Stokes só com viscosidade,
 * ∂u/∂t = ν∇²u, stencil de 5 pontos + Euler explícito), agora com o grid
 * dimensionado em tempo de execução para permitir escalabilidade fraca.
 *
 * Cinco versões do mesmo cálculo, em ordem de evolução. Cada uma remove um
 * gargalo de escalabilidade da anterior:
 *
 *   v0  sequencial          — referência para speedup
 *   v1  paralela ingênua    — memcpy serial do grid a cada passo (Amdahl)
 *   v2  double buffering    — troca de ponteiros; memória ainda é alocada e
 *                             inicializada pela thread mestre (first touch
 *                             concentra todas as páginas em um nó NUMA)
 *   v3  first touch paralelo— cada thread inicializa as linhas que vai
 *                             calcular; páginas ficam locais ao seu socket
 *   v4  região única        — um só `omp parallel` envolve todo o laço do
 *                             tempo, eliminando fork/join por passo
 *
 * As cinco produzem o mesmo campo bit a bit (o stencil é determinístico por
 * célula, sem redução), o que o modo `valida` confere pelo checksum.
 *
 * Uso:
 *   ./fluid_scale valida [n]
 *   ./fluid_scale bench <versao 0..4> <n> <passos> <repeticoes>
 *
 * `bench` imprime uma linha CSV por repetição-mediana em stdout.
 */

#include "stencil.h"

/* Só o benchmark próprio precisa de mediana; o binário do PaScal roda uma vez
   por configuração e deixa as repetições a cargo do analyzer (--rpts). */
static int cmp(const void *a, const void *b) {
    double x = *(const double *)a, y = *(const double *)b;
    return (x > y) - (x < y);
}

int main(int argc, char **argv) {
    if (argc < 2) {
        fprintf(stderr,
            "uso: %s valida [n]\n"
            "     %s bench <versao 0..%d> <n> <passos> <repeticoes>\n",
            argv[0], argv[0], NVER - 1);
        return EXIT_FAILURE;
    }

    /* ── Modo validação: as 5 versões têm de dar o mesmo campo ──────────── */
    if (!strcmp(argv[1], "valida")) {
        size_t n = (argc > 2) ? strtoul(argv[2], NULL, 10) : 512;
        int nt = 200;
        double ref = 0.0, ref_pico = 0.0;

        printf("Validação — grade %zu×%zu, %d passos, %d threads\n",
               n, n, nt, omp_get_max_threads());
        printf("r = ν·Δt/Δx² = %.4f (limite de estabilidade: 0.25)\n\n", R);
        printf("%-18s  %20s  %12s  %s\n", "versão", "checksum Σu", "pico", "");

        for (int v = 0; v < NVER; v++) {
            double *u  = VERSOES[v].first_touch ? aloca_first_touch(n) : aloca_serial(n);
            double *un = VERSOES[v].first_touch ? aloca_first_touch(n) : aloca_serial(n);
            inicia_perturbacao(u, n, VERSOES[v].first_touch);

            VERSOES[v].fn(u, un, n, nt);
            const double *res = resultado(v, u, un, nt);

            double cs = checksum(res, n), pico = 0.0;
            for (size_t k = 0; k < n * n; k++) if (res[k] > pico) pico = res[k];

            if (v == 0) { ref = cs; ref_pico = pico; }
            printf("%-18s  %20.12e  %12.6f  %s\n", VERSOES[v].nome, cs, pico,
                   v == 0 ? "(referência)"
                          : (cs == ref && pico == ref_pico ? "✓ idêntico"
                                                           : "✗ DIVERGIU"));
            free(u); free(un);
        }

        /* A massa Σu se conserva enquanto a perturbação não alcança a borda:
           é o mesmo teste analítico da Tarefa 11, repetido aqui para garantir
           que as otimizações não mexeram na física. */
        double massa_ini = 2.0 * M_PI * SIGMA0 * SIGMA0 * AMPLITUDE;
        printf("\nmassa Σu analítica (2πσ₀²A): %.6e\n", massa_ini);
        printf("massa Σu medida:             %.6e   (deve se conservar)\n", ref);
        return EXIT_SUCCESS;
    }

    /* ── Modo benchmark ─────────────────────────────────────────────────── */
    if (strcmp(argv[1], "bench") || argc != 6) {
        fprintf(stderr, "argumentos inválidos\n");
        return EXIT_FAILURE;
    }

    int    v    = atoi(argv[2]);
    size_t n    = strtoul(argv[3], NULL, 10);
    int    nt   = atoi(argv[4]);
    int    reps = atoi(argv[5]);
    if (v < 0 || v >= NVER || n < 8 || nt < 1 || reps < 1) {
        fprintf(stderr, "argumentos fora de faixa\n");
        return EXIT_FAILURE;
    }

    double *u  = VERSOES[v].first_touch ? aloca_first_touch(n) : aloca_serial(n);
    double *un = VERSOES[v].first_touch ? aloca_first_touch(n) : aloca_serial(n);

    double *tempos = malloc(reps * sizeof *tempos);
    for (int r = 0; r < reps; r++) {
        inicia_perturbacao(u, n, VERSOES[v].first_touch);
        tempos[r] = VERSOES[v].fn(u, un, n, nt);
    }
    qsort(tempos, reps, sizeof *tempos, cmp);
    double t = tempos[reps / 2];

    /* MLUPS = milhões de células atualizadas por segundo: a taxa de trabalho
       útil, independente do tamanho do problema — é ela que se compara na
       escalabilidade fraca, onde o problema muda junto com os recursos. */
    double celulas = (double)(n - 2) * (double)(n - 2) * nt;
    double mlups = celulas / t / 1e6;

    /* versao,threads,n,passos,tempo_s,mlups,checksum */
    printf("%s,%d,%zu,%d,%.6f,%.3f,%.12e\n",
           VERSOES[v].nome, omp_get_max_threads(), n, nt, t, mlups,
           checksum(resultado(v, u, un, nt), n));

    free(tempos); free(u); free(un);
    return EXIT_SUCCESS;
}
