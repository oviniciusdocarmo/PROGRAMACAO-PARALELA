#define _POSIX_C_SOURCE 199309L
#include <stdio.h>
#include <stdlib.h>
#include <math.h>
#include <string.h>
#include <time.h>
#include <omp.h>

/* ── Parâmetros da simulação ──────────────────────────────────────────── */
#define NX       512     /* células na direção x */
#define NY       512     /* células na direção y */
#define NT       1000    /* passos de tempo para benchmark */
#define NT_VAL   200     /* passos para validação */
#define NU       0.1     /* viscosidade cinemática */
#define DX       1.0     /* espaçamento espacial */
#define DT       0.1     /* passo de tempo */
#define NTHREADS 4

/* r = ν·Δt/Δx² = 0.1 × 0.1 / 1.0 = 0.01  ≤  0.25  → estável */
#define R  (NU * DT / (DX * DX))

#define BILLION 1000000000.0

static double elapsed(struct timespec a, struct timespec b) {
    return (b.tv_sec - a.tv_sec) + (b.tv_nsec - a.tv_nsec) / BILLION;
}

/* ── Utilidades de grade ──────────────────────────────────────────────── */

static double (*alloc_grid(void))[NY] {
    return calloc(NX, NY * sizeof(double));
}

static void copy_grid(double dst[NX][NY], const double src[NX][NY]) {
    memcpy(dst, src, NX * NY * sizeof(double));
}

/* Energia total: Σ u[i][j]² */
static double energia(const double u[NX][NY]) {
    double e = 0.0;
    for (int i = 0; i < NX; i++)
        for (int j = 0; j < NY; j++)
            e += u[i][j] * u[i][j];
    return e;
}

/* Desvio máximo no quarto central da grade (longe das bordas Dirichlet) */
static double max_delta_centro(const double u[NX][NY], double esperado) {
    double d = 0.0;
    int i0 = NX/4, i1 = 3*NX/4;
    int j0 = NY/4, j1 = 3*NY/4;
    for (int i = i0; i < i1; i++)
        for (int j = j0; j < j1; j++) {
            double diff = fabs(u[i][j] - esperado);
            if (diff > d) d = diff;
        }
    return d;
}

/* Perturbação gaussiana centrada na grade */
static void gaussiana(double u[NX][NY], double amplitude, double sigma) {
    int ci = NX / 2, cj = NY / 2;
    for (int i = 0; i < NX; i++)
        for (int j = 0; j < NY; j++) {
            double di = i - ci, dj = j - cj;
            u[i][j] += amplitude * exp(-(di*di + dj*dj) / (2.0 * sigma * sigma));
        }
}

/* ── Stencil de difusão: um passo de tempo ───────────────────────────── */
/* Condição de contorno: Dirichlet u=0 nas bordas (implícito: não atualiza bordas). */

/* Versão sequencial */
static void passo_seq(const double u[NX][NY], double u_new[NX][NY]) {
    for (int i = 1; i < NX-1; i++)
        for (int j = 1; j < NY-1; j++)
            u_new[i][j] = u[i][j] + R*(u[i+1][j] + u[i-1][j]
                                      + u[i][j+1] + u[i][j-1]
                                      - 4.0*u[i][j]);
}

/* schedule(static) */
static void passo_static(const double u[NX][NY], double u_new[NX][NY]) {
    #pragma omp parallel for num_threads(NTHREADS) schedule(static)
    for (int i = 1; i < NX-1; i++)
        for (int j = 1; j < NY-1; j++)
            u_new[i][j] = u[i][j] + R*(u[i+1][j] + u[i-1][j]
                                      + u[i][j+1] + u[i][j-1]
                                      - 4.0*u[i][j]);
}

/* schedule(static, chunk) — chunk explícito */
static void passo_static_chunk(const double u[NX][NY], double u_new[NX][NY]) {
    #pragma omp parallel for num_threads(NTHREADS) schedule(static, NX/NTHREADS)
    for (int i = 1; i < NX-1; i++)
        for (int j = 1; j < NY-1; j++)
            u_new[i][j] = u[i][j] + R*(u[i+1][j] + u[i-1][j]
                                      + u[i][j+1] + u[i][j-1]
                                      - 4.0*u[i][j]);
}

/* schedule(dynamic, 16) */
static void passo_dynamic(const double u[NX][NY], double u_new[NX][NY]) {
    #pragma omp parallel for num_threads(NTHREADS) schedule(dynamic, 16)
    for (int i = 1; i < NX-1; i++)
        for (int j = 1; j < NY-1; j++)
            u_new[i][j] = u[i][j] + R*(u[i+1][j] + u[i-1][j]
                                      + u[i][j+1] + u[i][j-1]
                                      - 4.0*u[i][j]);
}

/* schedule(guided) */
static void passo_guided(const double u[NX][NY], double u_new[NX][NY]) {
    #pragma omp parallel for num_threads(NTHREADS) schedule(guided)
    for (int i = 1; i < NX-1; i++)
        for (int j = 1; j < NY-1; j++)
            u_new[i][j] = u[i][j] + R*(u[i+1][j] + u[i-1][j]
                                      + u[i][j+1] + u[i][j-1]
                                      - 4.0*u[i][j]);
}

/* collapse(2) + static — colapsa os dois loops em um espaço de iterações único */
static void passo_collapse(const double u[NX][NY], double u_new[NX][NY]) {
    #pragma omp parallel for num_threads(NTHREADS) schedule(static) collapse(2)
    for (int i = 1; i < NX-1; i++)
        for (int j = 1; j < NY-1; j++)
            u_new[i][j] = u[i][j] + R*(u[i+1][j] + u[i-1][j]
                                      + u[i][j+1] + u[i][j-1]
                                      - 4.0*u[i][j]);
}

/* ── Evolução temporal genérica ───────────────────────────────────────── */

typedef void (*passo_fn)(const double[NX][NY], double[NX][NY]);

static double evoluir(double u[NX][NY], double u_new[NX][NY],
                      passo_fn fn, int nt) {
    struct timespec ini, fim;
    clock_gettime(CLOCK_MONOTONIC, &ini);
    for (int t = 0; t < nt; t++) {
        fn(u, u_new);
        double (*tmp)[NY] = u;
        /* troca ponteiros — não permitido com arrays estáticos; copiar */
        memcpy((void *)u, u_new, NX * NY * sizeof(double));
        (void)tmp;
    }
    clock_gettime(CLOCK_MONOTONIC, &fim);
    return elapsed(ini, fim);
}

/* ── main ─────────────────────────────────────────────────────────────── */

int main(void) {
    double (*u)[NY]     = alloc_grid();
    double (*u_new)[NY] = alloc_grid();
    double (*base)[NY]  = alloc_grid();

    printf("Simulação de difusão viscosa (Navier-Stokes simplificado)\n");
    printf("Grade: %d×%d  |  r = ν·Δt/Δx² = %.4f  (limite estabilidade: 0.25)\n\n",
           NX, NY, R);

    /* ── Fase 1: validação ─────────────────────────────────────────────── */
    printf("=== Fase 1: Validação (%d passos) ===\n\n", NT_VAL);

    /* Teste A: campo uniforme — bordas fixas em 0 drenam a solução lentamente;
       mas o interior longe das bordas deve permanecer muito próximo de 1.0     */
    for (int i = 1; i < NX-1; i++)
        for (int j = 1; j < NY-1; j++)
            u[i][j] = 1.0;
    double e_ini = energia(u);
    evoluir(u, u_new, passo_seq, NT_VAL);
    printf("Teste A — campo uniforme (interior):\n");
    printf("  Energia inicial: %.6e\n", e_ini);
    printf("  Energia final:   %.6e\n", energia(u));
    printf("  max|u[i][j] - 1.0| no quarto central: %.2e  (bordas Dirichlet=0 afetam apenas a periferia)\n\n",
           max_delta_centro(u, 1.0));

    /* Teste B: perturbação gaussiana sobre campo nulo */
    memset(u, 0, NX * NY * sizeof(double));
    gaussiana(u, 10.0, 20.0);
    e_ini = energia(u);
    copy_grid(base, u);   /* salva estado inicial */
    evoluir(u, u_new, passo_seq, NT_VAL);
    printf("Teste B — perturbação gaussiana (difusão suave):\n");
    printf("  Energia inicial: %.6e\n", e_ini);
    printf("  Energia final:   %.6e  (decaiu por difusão + bordas)\n\n",
           energia(u));

    /* ── Fase 2: benchmark schedule/collapse ───────────────────────────── */
    printf("=== Fase 2: Desempenho (%d×%d, %d passos, %d threads) ===\n\n",
           NX, NY, NT, NTHREADS);
    printf("%-28s  %-10s  %-8s\n", "Versão", "Tempo(s)", "Speedup");
    printf("%-28s  %-10s  %-8s\n",
           "----------------------------", "----------", "--------");

    struct { const char *nome; passo_fn fn; } versoes[] = {
        { "Sequencial",          passo_seq          },
        { "static",              passo_static       },
        { "static,chunk=NX/4",  passo_static_chunk  },
        { "dynamic,chunk=16",   passo_dynamic       },
        { "guided",              passo_guided       },
        { "collapse(2)+static", passo_collapse      },
    };
    int nv = sizeof(versoes) / sizeof(versoes[0]);
    double t_base = 0.0;

    for (int v = 0; v < nv; v++) {
        /* reinicia com perturbação gaussiana a cada versão */
        memset(u, 0, NX * NY * sizeof(double));
        gaussiana(u, 10.0, 20.0);

        double t = evoluir(u, u_new, versoes[v].fn, NT);
        if (v == 0) t_base = t;
        printf("%-28s  %-10.4f  %.4f\n",
               versoes[v].nome, t, t_base / t);
    }

    free(u);
    free(u_new);
    free(base);
    return 0;
}
