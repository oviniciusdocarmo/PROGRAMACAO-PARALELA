#include <stdio.h>
#include <time.h>

#define MAXN 2000
#define BILLION 1000000000.0

int A[MAXN][MAXN];
int x[MAXN];
int y[MAXN];

void init(int N){
    for(int i=0;i<N;i++){
        x[i] = 1;
        for(int j=0;j<N;j++)
            A[i][j] = 1;
    }
}

/* Acesso por LINHAS */
void mxv_linhas(int N){
    for(int i=0;i<N;i++){
        y[i] = 0;
        for(int j=0;j<N;j++)
            y[i] += A[i][j] * x[j];
    }
}

/* Acesso por COLUNAS */
void mxv_colunas(int N){
    for(int i=0;i<N;i++)
        y[i] = 0;

    for(int j=0;j<N;j++)
        for(int i=0;i<N;i++)
            y[i] += A[i][j] * x[j];
}

/* Medição de tempo */
double medir(void (*func)(int), int N){
    struct timespec ini, fim;
    clock_gettime(CLOCK_MONOTONIC, &ini);

    func(N);

    clock_gettime(CLOCK_MONOTONIC, &fim);

    return (fim.tv_sec - ini.tv_sec) +
           (fim.tv_nsec - ini.tv_nsec) / BILLION;
}

int main(){
    printf("N\tLinhas(s)\tColunas(s)\n");

    for(int N=100; N<=2000; N+=100){
        init(N);

        double t1 = medir(mxv_linhas, N);
        double t2 = medir(mxv_colunas, N);

        printf("%d\t%.6f\t%.6f\n", N, t1, t2);
    }

    return 0;
}