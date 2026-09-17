/* Tarefa 11 — Particionamento de dados e balanceamento de carga
 *
 * Navier-Stokes considerando apenas a viscosidade (sem pressão nem forças
 * externas), o que reduz a equação à difusão:  ∂u/∂t = ν ∇²u
 *
 * Espaço discretizado por diferenças finitas (stencil de 5 pontos) e tempo
 * por Euler explícito. Contorno de Dirichlet: u = 0 nas bordas, que nunca
 * são atualizadas.
 *
 * Fase 1 valida a física; fase 2 mede schedule e collapse do OpenMP.
 */

#define _POSIX_C_SOURCE 199309L
#include <stdio.h>
#include <stdlib.h>
#include <math.h>
#include <string.h>
#include <time.h>
#include <omp.h>

#define NX 512          /* células em x */
#define NY 512          /* células em y */
#define NU 0.1          /* viscosidade cinemática ν */
#define DX 1.0          /* espaçamento espacial */
#define DT 0.1          /* passo de tempo */

/* r = ν·Δt/Δx² = 0.01 ≤ 0.25 → esquema explícito estável */
#define R (NU * DT / (DX * DX))

#define NT_VAL 2000     /* passos da validação */
#define NT     1000     /* passos do benchmark */
#define REPS   3        /* repetições por versão, para tirar a mediana */

#define AMPLITUDE 10.0  /* pico da perturbação gaussiana */
#define SIGMA0    5.0   /* largura inicial da perturbação */

typedef double (*grid)[NY];

static grid aloca(void) {
    grid g = calloc(NX, sizeof *g);
    if (!g) { perror("calloc"); exit(EXIT_FAILURE); }
    return g;
}

/* ── Stencil de difusão ──────────────────────────────────────────────── */

static inline void atualiza_linha(const double u[NX][NY],
                                  double u_new[NX][NY], int i) {
    for (int j = 1; j < NY - 1; j++)
        u_new[i][j] = u[i][j] + R * (u[i+1][j] + u[i-1][j]
                                   + u[i][j+1] + u[i][j-1] - 4.0 * u[i][j]);
}

static void passo_seq(const double u[NX][NY], double u_new[NX][NY]) {
    for (int i = 1; i < NX - 1; i++)
        atualiza_linha(u, u_new, i);
}

/* schedule(runtime): a política é escolhida em tempo de execução por
   omp_set_schedule(), o que permite comparar static/dynamic/guided
   com um único corpo de código. */
static void passo_omp(const double u[NX][NY], double u_new[NX][NY]) {
    #pragma omp parallel for schedule(runtime)
    for (int i = 1; i < NX - 1; i++)
        atualiza_linha(u, u_new, i);
}

/* collapse(2) funde os dois laços num espaço único de (NX-2)·(NY-2)
   iterações, distribuído entre as threads como uma lista só. */
static void passo_collapse(const double u[NX][NY], double u_new[NX][NY]) {
    #pragma omp parallel for schedule(runtime) collapse(2)
    for (int i = 1; i < NX - 1; i++)
        for (int j = 1; j < NY - 1; j++)
            u_new[i][j] = u[i][j] + R * (u[i+1][j] + u[i-1][j]
                                       + u[i][j+1] + u[i][j-1] - 4.0 * u[i][j]);
}

/* ── Evolução temporal ───────────────────────────────────────────────── */

typedef void (*passo_fn)(const double[NX][NY], double[NX][NY]);

/* Recebe os grids por endereço para trocar os ponteiros a cada passo
   (double buffering). O resultado fica sempre em *u. Retorna o tempo. */
static double evoluir(grid *u, grid *u_new, passo_fn passo, int nt) {
    struct timespec ini, fim;
    clock_gettime(CLOCK_MONOTONIC, &ini);

    for (int t = 0; t < nt; t++) {
        passo(*u, *u_new);
        grid tmp = *u; *u = *u_new; *u_new = tmp;
    }

    clock_gettime(CLOCK_MONOTONIC, &fim);
    return (fim.tv_sec - ini.tv_sec) + (fim.tv_nsec - ini.tv_nsec) / 1e9;
}

/* ── Condições iniciais ──────────────────────────────────────────────── */

static void inicia_uniforme(double u[NX][NY], double valor) {
    memset(u, 0, NX * NY * sizeof(double));
    for (int i = 1; i < NX - 1; i++)
        for (int j = 1; j < NY - 1; j++)
            u[i][j] = valor;
}

static void inicia_perturbacao(double u[NX][NY], double amp, double sigma) {
    memset(u, 0, NX * NY * sizeof(double));
    int ci = NX / 2, cj = NY / 2;
    for (int i = 1; i < NX - 1; i++)
        for (int j = 1; j < NY - 1; j++) {
            double di = i - ci, dj = j - cj;
            u[i][j] = amp * exp(-(di*di + dj*dj) / (2.0 * sigma * sigma));
        }
}

/* ── Medidas de validação ────────────────────────────────────────────── */

typedef struct {
    double maximo;   /* pico do campo */
    double minimo;   /* < 0 denunciaria oscilação numérica */
    double massa;    /* Σ u — conservada enquanto a perturbação não toca a borda */
    double sigma;    /* largura efetiva: <r²> = 2σ² para uma gaussiana 2D */
} Perfil;

static Perfil mede(const double u[NX][NY]) {
    Perfil p = { -INFINITY, INFINITY, 0.0, 0.0 };
    double soma_r2 = 0.0;
    int ci = NX / 2, cj = NY / 2;

    for (int i = 0; i < NX; i++)
        for (int j = 0; j < NY; j++) {
            double v = u[i][j];
            if (v > p.maximo) p.maximo = v;
            if (v < p.minimo) p.minimo = v;
            p.massa += v;
            double di = i - ci, dj = j - cj;
            soma_r2 += (di*di + dj*dj) * v;
        }

    p.sigma = sqrt(soma_r2 / (2.0 * p.massa));
    return p;
}

/* Maior desvio em relação ao valor esperado no quarto central da grade,
   região distante o bastante das bordas Dirichlet. */
static double max_desvio_centro(const double u[NX][NY], double esperado) {
    double d = 0.0;
    for (int i = NX/4; i < 3*NX/4; i++)
        for (int j = NY/4; j < 3*NY/4; j++) {
            double diff = fabs(u[i][j] - esperado);
            if (diff > d) d = diff;
        }
    return d;
}

/* ── Benchmark ───────────────────────────────────────────────────────── */

static int compara(const void *a, const void *b) {
    double x = *(const double *)a, y = *(const double *)b;
    return (x > y) - (x < y);
}

static double mediana(double v[], int n) {
    qsort(v, n, sizeof *v, compara);
    return v[n / 2];
}

/* ── main ────────────────────────────────────────────────────────────── */

int main(void) {
    grid u = aloca(), u_new = aloca();

    printf("Difusão viscosa (Navier-Stokes só com viscosidade)\n");
    printf("Grade %d×%d | r = ν·Δt/Δx² = %.4f (limite de estabilidade: 0.25)\n\n",
           NX, NY, R);

    /* ── Fase 1: validação ──────────────────────────────────────────── */
    printf("=== Fase 1: validação (%d passos, t = %.1f) ===\n\n",
           NT_VAL, NT_VAL * DT);

    /* A) Campo uniforme deve permanecer estável. As bordas fixas em zero
          drenam a periferia, mas o interior não pode se mover. */
    inicia_uniforme(u, 1.0);
    evoluir(&u, &u_new, passo_seq, NT_VAL);
    printf("A) Campo uniforme u = 1.0\n");
    printf("   max|u - 1.0| no quarto central: %.2e  (esperado: ~0)\n\n",
           max_desvio_centro(u, 1.0));

    /* B) Uma perturbação gaussiana deve se espalhar suavemente: o pico cai,
          a largura cresce como σ(t) = sqrt(σ0² + 2νt) e nada oscila. */
    inicia_perturbacao(u, AMPLITUDE, SIGMA0);
    Perfil antes = mede(u);
    evoluir(&u, &u_new, passo_seq, NT_VAL);
    Perfil depois = mede(u);
    double sigma_teorico = sqrt(SIGMA0*SIGMA0 + 2.0 * NU * (NT_VAL * DT));

    printf("B) Perturbação gaussiana (amplitude %.1f, σ0 = %.1f)\n", AMPLITUDE, SIGMA0);
    printf("   pico:    %8.4f → %8.4f   (deve cair)\n", antes.maximo, depois.maximo);
    printf("   largura: %8.4f → %8.4f   (analítico: %.4f)\n",
           antes.sigma, depois.sigma, sigma_teorico);
    printf("   massa Σu: %.6e → %.6e   (deve se conservar)\n",
           antes.massa, depois.massa);
    printf("   mínimo final: %.2e  (≥ 0 → difusão suave, sem oscilação)\n\n",
           depois.minimo);

    /* ── Fase 2: schedule e collapse ────────────────────────────────── */
    printf("=== Fase 2: desempenho (%d passos, %d threads, mediana de %d execuções) ===\n\n",
           NT, omp_get_max_threads(), REPS);

    struct { const char *nome; passo_fn passo; omp_sched_t sched; int chunk; }
    versoes[] = {
        { "Sequencial",           passo_seq,      omp_sched_static,  0  },
        { "static",               passo_omp,      omp_sched_static,  0  },
        { "static, chunk=32",     passo_omp,      omp_sched_static,  32 },
        { "dynamic, chunk=16",    passo_omp,      omp_sched_dynamic, 16 },
        { "guided",               passo_omp,      omp_sched_guided,  0  },
        { "collapse(2) + static", passo_collapse, omp_sched_static,  0  },
    };
    int nv = sizeof versoes / sizeof *versoes;
    double t_seq = 0.0;

    printf("%-22s  %10s  %8s\n", "Versão", "Tempo(s)", "Speedup");
    printf("%-22s  %10s  %8s\n", "----------------------", "----------", "--------");

    for (int v = 0; v < nv; v++) {
        omp_set_schedule(versoes[v].sched, versoes[v].chunk);

        double tempos[REPS];
        for (int r = 0; r < REPS; r++) {
            inicia_perturbacao(u, AMPLITUDE, SIGMA0);
            tempos[r] = evoluir(&u, &u_new, versoes[v].passo, NT);
        }

        double t = mediana(tempos, REPS);
        if (v == 0) t_seq = t;
        printf("%-22s  %10.4f  %8.2f\n", versoes[v].nome, t, t_seq / t);
    }

    free(u);
    free(u_new);
    return 0;
}
