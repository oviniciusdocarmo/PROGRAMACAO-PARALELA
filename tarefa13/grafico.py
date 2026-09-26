"""Gráfico de tempo e speedup por política de afinidade (menor tempo das 3 repetições)."""
import csv
import matplotlib.pyplot as plt

melhor = {}                                    # (afinidade, threads) -> tempo
for r in csv.DictReader(open("resultados.csv")):
    k = (r["afinidade"], int(r["threads"]))
    melhor[k] = min(melhor.get(k, 1e9), float(r["tempo_s"]))
binds = list(dict.fromkeys(b for b, _ in melhor))
ps = sorted({p for _, p in melhor})
t1 = min(melhor[b, 1] for b in binds)          # referência: melhor tempo com 1 thread

for b in binds:
    print(b, "  ".join(f"{p}:{melhor[b, p]:.4f}s({t1 / melhor[b, p]:.1f}x)" for p in ps))

fig, (a1, a2) = plt.subplots(1, 2, figsize=(12, 4.5))
for b in binds:
    est = "s--" if b == "true" else "o-"       # true coincide com close
    a1.loglog(ps, [melhor[b, p] for p in ps], est, label=b)
    a2.loglog(ps, [t1 / melhor[b, p] for p in ps], est, label=b)
a2.loglog(ps, ps, "k:", label="ideal")
a1.set(xlabel="threads", ylabel="tempo (s)", title="Tempo (4096×4096, 100 passos)")
a2.set(xlabel="threads", ylabel="speedup", title="Speedup")
for a in (a1, a2):
    a.set_xticks(ps, [str(p) for p in ps])
    a.legend(title="OMP_PROC_BIND"); a.grid(True, which="both", alpha=.3)
fig.tight_layout()
fig.savefig("img/afinidade.png", dpi=120)
