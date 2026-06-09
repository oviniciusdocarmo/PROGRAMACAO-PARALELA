# Tarefa 7: omp tasks com lista encadeada

## Objetivo

Criar uma lista encadeada de nomes de arquivo fictícios e processá-la em paralelo com `#pragma omp task`, observando os problemas da abordagem ingênua e como corrigi-los com `#pragma omp single` e `firstprivate`.

---

## Ambiente

| Item            | Valor                              |
|-----------------|------------------------------------|
| CPU             | AMD Ryzen 5 5600G                  |
| Núcleos físicos | 4                                  |
| Compilador      | GCC com `-O2 -fopenmp`             |
| Nós na lista    | 10                                 |
| Threads         | 4                                  |

---

## Implementação

### Estrutura da lista

```c
typedef struct no { const char *nome; struct no *next; } no_t;
```

10 nós com nomes: `relatorio_jan.txt`, `vendas_q1.csv`, `backup_2024.tar.gz`, `log_sistema.log`, `config.yaml`, `notas_reuniao.docx`, `planilha_rh.xlsx`, `imagem_disk.iso`, `script_deploy.sh`, `dados_clientes.db`.

---

### Versão 1 — Problemática

```c
#pragma omp parallel num_threads(4)
{
    no_t *p = head;         /* cada thread inicia do topo */
    while (p) {
        #pragma omp task firstprivate(p)
        processar(p);       /* tarefa criada por TODOS os threads */
        p = p->next;
    }
    #pragma omp taskwait
}
```

Todos os 4 threads percorrem a lista inteira de forma independente. Cada thread cria 10 tarefas → **40 tarefas no total** → cada arquivo é processado 4 vezes.

---

### Versão 2 — Correta

```c
#pragma omp parallel num_threads(4)
{
    #pragma omp single             /* apenas UMA thread percorre a lista */
    {
        no_t *p = head;
        while (p) {
            #pragma omp task firstprivate(p)   /* captura p por valor */
            processar(p);
            p = p->next;
        }
    }                              /* taskwait implícito ao sair do single */
}
```

Apenas uma thread cria as 10 tarefas; as 4 threads as executam. Cada arquivo é processado exatamente uma vez.

---

## Resultados

### Versão problemática — execuções consecutivas

**Execução 1 (40 linhas — cada arquivo 4×, ordem variável):**
```
[thread 3] dados_clientes.db
[thread 3] script_deploy.sh
... (40 linhas)
[thread 0] notas_reuniao.docx
```

**Execução 2 (40 linhas, distribuição de threads diferente):**
```
[thread 0] dados_clientes.db
[thread 0] script_deploy.sh
... (40 linhas)
[thread 1] dados_clientes.db
```

**Execução 3 (40 linhas, nova distribuição):**
```
[thread 0] relatorio_jan.txt
...
[thread 3] dados_clientes.db
```

### Versão correta — execuções consecutivas

**Execução 1 (10 linhas — cada arquivo 1×):**
```
[thread 3] relatorio_jan.txt
[thread 2] log_sistema.log
[thread 1] vendas_q1.csv
[thread 1] notas_reuniao.docx
[thread 3] planilha_rh.xlsx
[thread 2] script_deploy.sh
[thread 2] dados_clientes.db
[thread 0] backup_2024.tar.gz
[thread 1] imagem_disk.iso
[thread 2] config.yaml
```

**Execução 2 (10 linhas, threads diferentes):**
```
[thread 2] relatorio_jan.txt
[thread 0] vendas_q1.csv
[thread 3] backup_2024.tar.gz
...
```

---

## Análise

### Todos os nós foram processados?

**Versão problemática:** sim, todos os nós foram processados — mas 4 vezes cada. Nenhum foi ignorado porque todos os 4 threads chegaram ao fim da lista.

**Versão correta:** sim, todos os 10 nós foram processados exatamente uma vez.

### Algum foi processado mais de uma vez?

**Versão problemática:** sim, todos. Com 4 threads percorrendo a lista independentemente, cada nó gera 4 tarefas. A contagem total é sempre `nthreads × nnós = 40` — determinística. O que muda entre execuções é apenas qual thread executa qual tarefa e em que ordem.

**Versão correta:** não. `#pragma omp single` garante que somente uma thread percorre a lista e cria as tarefas.

### O comportamento muda entre execuções?

**Versão problemática:** a contagem (40 linhas) não muda, mas a ordem e a atribuição de threads às tarefas variam — o escalonador de tarefas do OpenMP não é determinístico.

**Versão correta:** a ordem das impressões muda a cada execução (as 4 threads competem para executar as 10 tarefas), mas o conjunto de arquivos processados é sempre o mesmo e cada um aparece exatamente uma vez.

### Como garantir que cada nó seja processado uma única vez?

Dois mecanismos combinados:

1. **`#pragma omp single`**: restringe a criação de tarefas a uma única thread. Sem isso, cada thread percorre a lista e cria tarefas duplicadas.

2. **`firstprivate(p)`**: quando a tarefa é *criada*, o valor corrente do ponteiro `p` é copiado para dentro da tarefa. Sem isso, `p` seria *shared* — e como o loop continua avançando, a tarefa poderia receber um ponteiro já modificado (para o próximo nó ou NULL) no momento da execução.

3. **`taskwait` implícito no `single`**: ao sair do bloco `single`, o OpenMP aguarda todas as tarefas criadas dentro dele terminarem antes de liberar as threads. Garante que nenhum nó seja "esquecido".
