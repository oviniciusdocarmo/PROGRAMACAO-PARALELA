/* Núcleo numérico compartilhado da Tarefa 12 — difusão viscosa.
 *
 * Usado por fluid_scale.c (benchmark próprio, saída CSV) e por
 * pascal_fluid.c (binário instrumentado para o PaScal Analyzer). Uma única
 * definição da física garante que as duas medições descrevem o mesmo código.
 */

#ifndef STENCIL_H
#define STENCIL_H

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <omp.h>

#define NU 0.1          /* viscosidade cinemática ν */
#define DX 1.0          /* espaçamento espacial */
#define DT 0.1          /* passo de tempo */
#define R (NU * DT / (DX * DX))   /* = 0.01 ≤ 0.25 → explícito estável */

#define AMPLITUDE 10.0
#define SIGMA0    5.0

/* ── Alocação ────────────────────────────────────────────────────────────
 *
 * As duas rotinas devolvem a mesma coisa do ponto de vista do programa; o que
 * muda é *qual thread toca cada página primeiro*. No Linux a página física só
 * é escolhida no primeiro acesso (first touch), e ela nasce no nó NUMA da
 * thread que a tocou. Alocar e zerar em serial coloca o grid inteiro na
 * memória de um socket só — as threads do outro socket passam a ler tudo pelo
 * interconnect. Esse é o gargalo que separa v2 de v3.
 */

static double *aloca_serial(size_t n) {
    double *g = malloc(n * n * sizeof *g);
    if (!g) { perror("malloc"); exit(EXIT_FAILURE); }
    memset(g, 0, n * n * sizeof *g);          /* toque serial: tudo num nó */
    return g;
}

static double *aloca_first_touch(size_t n) {
    double *g = malloc(n * n * sizeof *g);
    if (!g) { perror("malloc"); exit(EXIT_FAILURE); }
    /* Mesma partição estática do laço de cálculo: a thread que vai atualizar
       a linha i é a que instancia as páginas da linha i. */
    #pragma omp parallel for schedule(static)
    for (size_t i = 0; i < n; i++)
        memset(&g[i * n], 0, n * sizeof *g);
    return g;
}

/* ── Condição inicial ────────────────────────────────────────────────────
 * Gaussiana no centro. `paralelo` preserva o first touch de aloca_first_touch
 * (mesma distribuição de linhas), então não desfaz a localidade NUMA.
 */
static void inicia_perturbacao(double *u, size_t n, int paralelo) {
    double ci = n / 2.0, cj = n / 2.0;
    #pragma omp parallel for schedule(static) if (paralelo)
    for (size_t i = 0; i < n; i++)
        for (size_t j = 0; j < n; j++) {
            if (i == 0 || j == 0 || i == n - 1 || j == n - 1) {
                u[i * n + j] = 0.0;           /* Dirichlet: borda fixa em 0 */
                continue;
            }
            double di = (double)i - ci, dj = (double)j - cj;
            u[i * n + j] = AMPLITUDE * exp(-(di*di + dj*dj)
                                           / (2.0 * SIGMA0 * SIGMA0));
        }
}

/* ── Stencil ─────────────────────────────────────────────────────────────
 * Uma linha interior do grid. Escrita contígua, cinco leituras vizinhas:
 * ~6 flops para ~48 bytes de tráfego → o kernel é memory-bound, e é isso que
 * define o teto de escalabilidade das versões já otimizadas.
 */
static inline void linha(const double *u, double *un, size_t i, size_t n) {
    const double *c = &u[i * n], *ci = &u[(i + 1) * n], *cd = &u[(i - 1) * n];
    double *o = &un[i * n];
    for (size_t j = 1; j < n - 1; j++)
        o[j] = c[j] + R * (ci[j] + cd[j] + c[j+1] + c[j-1] - 4.0 * c[j]);
}

/* ── v0: sequencial ──────────────────────────────────────────────────── */
static double roda_v0(double *u, double *un, size_t n, int nt) {
    double t0 = omp_get_wtime();
    for (int t = 0; t < nt; t++) {
        for (size_t i = 1; i < n - 1; i++) linha(u, un, i, n);
        double *tmp = u; u = un; un = tmp;
    }
    return omp_get_wtime() - t0;
}

/* ── v1: paralela ingênua ────────────────────────────────────────────────
 * O laço espacial é paralelo, mas o grid novo é copiado de volta sobre o
 * antigo em serial. A cópia move exatamente a mesma quantidade de bytes que o
 * próprio stencil — ou seja, ~50% do trabalho ficou serial. Por Amdahl o
 * speedup satura perto de 2×, não importa quantos núcleos se acrescente.
 */
static double roda_v1(double *u, double *un, size_t n, int nt) {
    double t0 = omp_get_wtime();
    for (int t = 0; t < nt; t++) {
        #pragma omp parallel for schedule(static)
        for (size_t i = 1; i < n - 1; i++) linha(u, un, i, n);
        memcpy(u, un, n * n * sizeof *u);      /* trecho serial */
    }
    return omp_get_wtime() - t0;
}

/* ── v2: double buffering ────────────────────────────────────────────────
 * A cópia vira uma troca de ponteiros: o trecho serial desaparece. Resta o
 * fato de a memória ter sido tocada em serial (ver aloca_serial).
 */
static double roda_v2(double *u, double *un, size_t n, int nt) {
    double t0 = omp_get_wtime();
    for (int t = 0; t < nt; t++) {
        #pragma omp parallel for schedule(static)
        for (size_t i = 1; i < n - 1; i++) linha(u, un, i, n);
        double *tmp = u; u = un; un = tmp;
    }
    return omp_get_wtime() - t0;
}

/* ── v3: v2 + first touch paralelo ───────────────────────────────────────
 * O laço é idêntico ao da v2. A diferença está fora da região medida: os
 * grids vêm de aloca_first_touch, então cada thread lê e escreve páginas da
 * memória do seu próprio socket. Em um nó de 2 sockets isso é a diferença
 * entre usar a banda local e disputar o interconnect.
 */
static double roda_v3(double *u, double *un, size_t n, int nt) {
    return roda_v2(u, un, n, nt);
}

/* ── v4: uma única região paralela ───────────────────────────────────────
 * v3 abre e fecha um time de threads a cada passo de tempo. Com 128 threads,
 * esse fork/join custa dezenas de microssegundos — desprezível diante de um
 * passo de 25 ms na escalabilidade forte, mas comparável ao passo quando o
 * grid por thread é pequeno. Aqui o `omp parallel` envolve o laço do tempo e
 * cada thread deduz os buffers a partir da paridade de t; a barreira implícita
 * do `omp for` é o único ponto de sincronização por passo.
 */
static double roda_v4(double *u, double *un, size_t n, int nt) {
    double t0 = omp_get_wtime();
    #pragma omp parallel
    {
        for (int t = 0; t < nt; t++) {
            const double *src = (t % 2 == 0) ? u  : un;
            double       *dst = (t % 2 == 0) ? un : u;
            #pragma omp for schedule(static)
            for (size_t i = 1; i < n - 1; i++) linha(src, dst, i, n);
            /* barreira implícita do `omp for` fecha o passo */
        }
    }
    return omp_get_wtime() - t0;
}

/* ── Infraestrutura de medição ──────────────────────────────────────────── */

typedef double (*roda_fn)(double *, double *, size_t, int);

static const struct { const char *nome; roda_fn fn; int first_touch; } VERSOES[] = {
    { "v0-sequencial",   roda_v0, 0 },
    { "v1-memcpy",       roda_v1, 0 },
    { "v2-doublebuf",    roda_v2, 0 },
    { "v3-firsttouch",   roda_v3, 1 },
    { "v4-regiao-unica", roda_v4, 1 },
};
#define NVER ((int)(sizeof VERSOES / sizeof *VERSOES))

static double checksum(const double *u, size_t n) {
    double s = 0.0;                            /* soma serial → determinística */
    for (size_t k = 0; k < n * n; k++) s += u[k];
    return s;
}

/* Depois de nt passos o campo final está ora em `u`, ora em `un`: toda versão
   que alterna buffers termina em `un` para nt ímpar. A v1 é a exceção — ela
   copia o resultado de volta para `u` a cada passo. */
static const double *resultado(int v, const double *u, const double *un, int nt) {
    if (v == 1) return u;
    return (nt % 2) ? un : u;
}

#endif /* STENCIL_H */
