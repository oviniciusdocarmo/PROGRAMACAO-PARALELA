"""Gráficos do produto matriz-vetor (menor tempo total das 3 repetições)."""
import csv
import matplotlib.pyplot as plt

melhor = {}                                    # (N, processos) -> linha
for r in csv.DictReader(open("resultados.csv")):
    k = (int(r["N"]), int(r["processos"]))
    if k not in melhor or float(r["tempo_total_s"]) < float(melhor[k]["tempo_total_s"]):
        melhor[k] = r
ns = sorted({n for n, _ in melhor})
ps = sorted({p for _, p in melhor})
T = lambda n, p, c="tempo_total_s": float(melhor[n, p][c])

for n in ns:
    print(f"N = {n}")
    for p in ps:
        print(f"  p={p:>3}  total {T(n,p)*1e3:8.3f} ms  distrib {T(n,p,'distribuicao_s')*1e3:8.3f}"
              f"  calculo {T(n,p,'calculo_s')*1e3:8.3f}  coleta {T(n,p,'coleta_s')*1e3:7.3f}"
              f"  speedup {T(n,1)/T(n,p):5.2f}")

fig, (a1, a2, a3) = plt.subplots(1, 3, figsize=(16, 4.5))
for n in ns:
    a1.loglog(ps, [T(n, p) * 1e3 for p in ps], "o-", label=f"{n}×{n}")
    a2.loglog(ps, [T(n, 1, "calculo_s") / T(n, p, "calculo_s") for p in ps], "o-", label=f"{n}×{n}")
a2.loglog(ps, ps, "k:", label="ideal")
a1.set(xlabel="processos", ylabel="tempo total (ms)", title="Tempo total (Scatter + Bcast + cálculo + Gather)")
a2.set(xlabel="processos", ylabel="speedup", title="Speedup só do cálculo")

n = ns[-1]
x = range(len(ps))
base = [0] * len(ps)
for col, nome in (("distribuicao_s", "Scatter + Bcast"), ("calculo_s", "cálculo"), ("coleta_s", "Gather")):
    v = [T(n, p, col) * 1e3 for p in ps]
    a3.bar(x, v, bottom=base, label=nome)
    base = [b + vi for b, vi in zip(base, v)]
a3.set_xticks(list(x), [str(p) for p in ps])
a3.set(xlabel="processos", ylabel="tempo (ms)", title=f"Composição do tempo ({n}×{n})")
for a in (a1, a2, a3):
    a.legend(); a.grid(True, which="both", alpha=.3)
for a in (a1, a2):
    a.set_xticks(ps, [str(p) for p in ps])
fig.tight_layout()
fig.savefig("img/tempos.png", dpi=120)
