# Tarefa 2:

Implemente três laços em C para investigar os efeitos do paralelismo ao nível de instrução (ILP): 
1) inicialize um vetor com um cálculo simples;
2) some seus elementos de forma acumulativa, criando dependência entre as iterações; e
3) quebre essa dependência utilizando múltiplas variáveis.
Compare o tempo de execução das versões compiladas com diferentes níveis de otimização (O0, O2, O3) e analise como o estilo do código e as dependências influenciam o desempenho.

# Como compilar

```bash
# Compila as três versões (O0, O2, O3) de uma vez
make all

# Compila individualmente
make ilp_O0
make ilp_O2
make ilp_O3
```

# Como executar

```bash
# Roda as três versões em sequência e exibe os tempos
make run

# Ou individualmente
./ilp_O0
./ilp_O2
./ilp_O3
```

# Descrição dos laços

| Laço | Descrição | Efeito no ILP |
|------|-----------|---------------|
| Loop 1 – `loop_init` | Inicializa cada `v[i]` com `i * π + e` | Sem dependência entre iterações — o compilador/CPU pode executar várias iterações em paralelo |
| Loop 2 – `loop_soma_dep` | Soma acumulativa em uma única variável `soma` | Dependência RAW (*read-after-write*): cada iteração precisa do resultado da anterior, impedindo ILP |
| Loop 3 – `loop_soma_nodep` | Soma com 4 acumuladores independentes (`s0..s3`) | Quebra a cadeia de dependências; o pipeline da CPU pode sobrepor as 4 somas em paralelo |
