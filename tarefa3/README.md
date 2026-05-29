# Tarefa 3: Implementação e Análise de Convergência para o Cálculo de π

Implemente um programa em C que calcule uma aproximação de π usando uma série matemática, variando o número de iterações e medindo o tempo de execução. Compare os valores obtidos com o valor real de π e analise como a acurácia melhora com mais processamento. Reflita sobre como esse comportamento se repete em aplicações reais que demandam resultados cada vez mais precisos, como simulações físicas e inteligência artificial.

Lembrete: Pessoal, não se esqueçam de incluir o código em todos os relatórios.

# Como compilar

```bash
make all   # ou apenas: make
```

# Como executar

```bash
make run

# Ou diretamente:
./pi
```

# Série utilizada

O programa usa a **Série de Leibniz**:

```
π/4 = 1 − 1/3 + 1/5 − 1/7 + 1/9 − ...
```

Cada termo adicional melhora a aproximação em uma casa decimal a cada ordem de magnitude de iterações.

# Código

```c
#define _POSIX_C_SOURCE 199309L
#include <stdio.h>
#include <math.h>
#include <time.h>

#define PI_REF  3.14159265358979323846
#define BILLION 1000000000.0

static double elapsed(struct timespec a, struct timespec b) {
    return (b.tv_sec - a.tv_sec) + (b.tv_nsec - a.tv_nsec) / BILLION;
}

/* Série de Leibniz: π/4 = 1 - 1/3 + 1/5 - 1/7 + ... */
static double calcular_pi(long long n) {
    double soma = 0.0;
    for (long long i = 0; i < n; i++) {
        double termo = 1.0 / (2 * i + 1);
        if (i % 2 == 0)
            soma += termo;
        else
            soma -= termo;
    }
    return 4.0 * soma;
}

int main(void) {
    long long iteracoes[] = {
        100LL, 1000LL, 10000LL, 100000LL,
        1000000LL, 10000000LL, 100000000LL, 1000000000LL
    };
    int n_casos = sizeof(iteracoes) / sizeof(iteracoes[0]);

    printf("%-15s  %-22s  %-12s  %-12s\n",
           "Iterações", "π aproximado", "Erro absoluto", "Tempo (s)");
    printf("%-15s  %-22s  %-12s  %-12s\n",
           "---------------", "----------------------", "------------", "------------");

    for (int k = 0; k < n_casos; k++) {
        struct timespec ini, fim;
        long long n = iteracoes[k];

        clock_gettime(CLOCK_MONOTONIC, &ini);
        double pi_aprox = calcular_pi(n);
        clock_gettime(CLOCK_MONOTONIC, &fim);

        double t    = elapsed(ini, fim);
        double erro = fabs(pi_aprox - PI_REF);

        printf("%-15lld  %.20f  %-12.2e  %.6f\n", n, pi_aprox, erro, t);
    }

    return 0;
}
```

# Resultados obtidos

```
Iterações        π aproximado            Erro absoluto  Tempo (s)
---------------  ----------------------  ------------  ------------
100              3.13159290355855368659  1.00e-02      0.000000
1000             3.14059265383979413500  1.00e-03      0.000001
10000            3.14149265359003448950  1.00e-04      0.000013
100000           3.14158265358971977577  1.00e-05      0.000128
1000000          3.14159165358977432447  1.00e-06      0.001096
10000000         3.14159255358979150330  1.00e-07      0.010606
100000000        3.14159264358932599492  1.00e-08      0.102906
1000000000       3.14159265258805042720  1.00e-09      1.029611
```

# Análise

## Convergência

A série de Leibniz converge de forma previsível, mas lenta: para ganhar **uma casa decimal a mais de precisão**, são necessárias **10× mais iterações**. Isso é uma convergência linear em escala logarítmica — o erro absoluto cai proporcionalmente a `1/N`.

| Fator de N | Melhoria no erro |
|------------|-----------------|
| ×10        | ÷10 (uma casa decimal) |
| ×100       | ÷100 (duas casas decimais) |
| ×1.000.000 | ÷1.000.000 (seis casas decimais) |

## Custo computacional

O tempo de execução também escala linearmente com N. Para atingir 9 casas decimais de precisão (1 bilhão de iterações), o programa leva cerca de **1 segundo** em modo sequencial. Para alcançar 12 casas decimais (1 trilhão de iterações), o tempo estimado seria de **~17 minutos** — em uma única thread.

## Por que precisamos de programação paralela?

Este experimento evidencia um padrão recorrente em computação de alto desempenho:

> **Mais precisão exige mais iterações, que exigem mais tempo.**

Aplicações reais como simulações de dinâmica de fluidos, redes neurais profundas e previsão do tempo precisam de respostas em tempo hábil, não horas depois. A solução é **dividir o trabalho entre múltiplos núcleos (ou máquinas)**:

- Com **P threads**, o loop pode ser particionado em P blocos independentes;
- Cada thread calcula sua fatia da soma parcial;
- As somas parciais são combinadas ao final (redução);
- O tempo cai para aproximadamente `T_sequencial / P`.

Ou seja, o mesmo cálculo que leva 1 s em 1 núcleo poderia levar ~0,125 s em 8 núcleos — mantendo a mesma precisão. Essa é a **motivação central da programação paralela**: não aumentar o que um núcleo faz, mas fazer mais núcleos trabalharem juntos.
