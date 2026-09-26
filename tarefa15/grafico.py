"""Gráfico do tempo por passo das três versões (menor tempo das 3 repetições)."""
import csv
import matplotlib.pyplot as plt

nomes = {1: "v1: Send/Recv", 2: "v2: Isend/Irecv + Wait", 3: "v3: Isend/Irecv + Test"}
melhor = {}
for r in csv.DictReader(open("resultados.csv")):
    k = (int(r["versao"]), int(r["pontos"]))
    us = float(r["tempo_s"]) / int(r["passos"]) * 1e6       # µs por passo
    melhor[k] = min(melhor.get(k, us), us)

ns = sorted({n for _, n in melhor})
print("pontos  " + "  ".join(f"v{v} (us/passo)" for v in nomes))
for n in ns:
    print(f"{n:>7} " + "  ".join(f"{melhor[v, n]:14.3f}" for v in nomes))

fig, (a1, a2) = plt.subplots(1, 2, figsize=(12, 4.5))
for v, nome in nomes.items():
    a1.loglog(ns, [melhor[v, n] for n in ns], "o-", label=nome)
    a2.semilogx(ns, [melhor[1, n] / melhor[v, n] for n in ns], "o-", label=nome)
a1.set(xlabel="pontos por processo", ylabel="tempo por passo (µs)",
       title="Tempo por passo")
a2.set(xlabel="pontos por processo", ylabel="ganho em relação à v1",
       title="Ganho (tempo v1 / tempo da versão)")
for a in (a1, a2):
    a.legend(); a.grid(True, which="both", alpha=.3)
fig.tight_layout()
fig.savefig("img/tempos.png", dpi=120)
