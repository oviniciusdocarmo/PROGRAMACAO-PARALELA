#include <stdio.h>
#include <stdlib.h>
#include <omp.h>

#define NTHREADS 4

typedef struct no { const char *nome; struct no *next; } no_t;

static const char *nomes[] = {
    "relatorio_jan.txt", "vendas_q1.csv",   "backup_2024.tar.gz",
    "log_sistema.log",   "config.yaml",     "notas_reuniao.docx",
    "planilha_rh.xlsx",  "imagem_disk.iso", "script_deploy.sh",
    "dados_clientes.db"
};
#define NNOS (int)(sizeof(nomes) / sizeof(nomes[0]))

static no_t *criar_lista(void) {
    no_t *head = NULL, *tail = NULL;
    for (int i = 0; i < NNOS; i++) {
        no_t *n = malloc(sizeof(no_t));
        n->nome = nomes[i];
        n->next = NULL;
        if (!tail) head = tail = n;
        else { tail->next = n; tail = n; }
    }
    return head;
}

static void liberar_lista(no_t *head) {
    while (head) { no_t *t = head->next; free(head); head = t; }
}

static void processar(const no_t *n) {
    printf("[thread %d] %s\n", omp_get_thread_num(), n->nome);
}

/* ── Versão 1: problemática ────────────────────────────────────────────────
   Todos os threads percorrem a lista independentemente e cada um cria
   uma tarefa para cada nó.
   Resultado: NTHREADS × NNOS tarefas → cada arquivo processado NTHREADS vezes. */
static void versao_problematica(no_t *head) {
    #pragma omp parallel num_threads(NTHREADS)
    {
        no_t *p = head;
        while (p) {
            #pragma omp task firstprivate(p)
            processar(p);
            p = p->next;
        }
        #pragma omp taskwait
    }
}

/* ── Versão 2: correta ─────────────────────────────────────────────────────
   #pragma omp single garante que apenas UMA thread percorre a lista e
   cria as tarefas. As demais ficam disponíveis para executá-las.
   firstprivate(p): cada tarefa captura o valor corrente de p no momento
   da criação — sem isso, p seria shared e poderia já ter avançado antes
   da tarefa executar.
   O taskwait implícito no final do single aguarda todas as tarefas.       */
static void versao_correta(no_t *head) {
    #pragma omp parallel num_threads(NTHREADS)
    {
        #pragma omp single
        {
            no_t *p = head;
            while (p) {
                #pragma omp task firstprivate(p)
                processar(p);
                p = p->next;
            }
        }
    }
}

int main(void) {
    no_t *lista = criar_lista();

    printf("=== Versão problemática (%d threads, %d nós → esperado %d linhas) ===\n",
           NTHREADS, NNOS, NTHREADS * NNOS);
    versao_problematica(lista);

    printf("\n=== Versão correta (%d threads, %d nós → esperado %d linhas) ===\n",
           NTHREADS, NNOS, NNOS);
    versao_correta(lista);

    liberar_lista(lista);
    return 0;
}
