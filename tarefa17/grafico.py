"""Gráficos: colunas (tarefa 17) x linhas (tarefa 16), menor tempo total das 3 repetições."""
import csv
import matplotlib.pyplot as plt

melhor = {}                                    # (versao, N, processos) -> linha
for r in csv.DictReader(open("resultados.csv")):
    k = (r["versao"], int(r["N"]), int(r["processos"]))
    if k not in melhor or float(r["tempo_total_s"]) < float(melhor[k]["tempo_total_s"]):
        melhor[k] = r
ns = sorted({n for _, n, _ in melhor})
ps = sorted({p for _, _, p in melhor})
T = lambda v, n, p, c="tempo_total_s": float(melhor[v, n, p][c])

for n in ns:
    print(f"N = {n}")
    for p in ps:
        print(f"  p={p:>3}", "  ".join(
            f"{v[:3]}: tot {T(v,n,p)*1e3:8.3f} dist {T(v,n,p,'distribuicao_s')*1e3:8.3f}"
            f" calc {T(v,n,p,'calculo_s')*1e3:7.3f} col {T(v,n,p,'coleta_s')*1e3:6.3f}"
            for v in ("colunas", "linhas")))

fig, ax = plt.subplots(2, 2, figsize=(13, 9))
titulos = {"tempo_total_s": "Tempo total", "distribuicao_s": "Distribuição (Scatter / Scatter + Bcast)",
           "calculo_s": "Cálculo (processo 0)", "coleta_s": "Coleta (Reduce / Gather)"}
for a, (col, tit) in zip(ax.flat, titulos.items()):
    for k, n in enumerate(ns):
        for v, estilo in (("colunas", "o-"), ("linhas", "s--")):
            a.loglog(ps, [T(v, n, p, col) * 1e3 for p in ps], estilo, color=f"C{k}",
                     label=f"{v} {n}×{n}")
    a.set(xlabel="processos", ylabel="tempo (ms)", title=tit)
    a.set_xticks(ps, [str(p) for p in ps])
    a.grid(True, which="both", alpha=.3)
ax[1, 1].legend(fontsize=8, loc="upper left")
fig.tight_layout()
fig.savefig("img/tempos.png", dpi=120)
