"""Gráficos do ping-pong e ajuste do modelo t(n) = L + n/B (tempo de ida)."""
import csv
import matplotlib.pyplot as plt

rows = list(csv.DictReader(open("resultados.csv")))
n = [int(r["bytes"]) for r in rows]
t = [float(r["tempo_por_troca_us"]) / 2 for r in rows]   # ida = metade da troca
bw = [float(r["banda_MBps"]) / 1000 for r in rows]        # GB/s

L = t[0]                              # latência: menor mensagem
B = n[-1] / (t[-1] - L) / 1e3         # banda (GB/s): maior mensagem
corte = L * B * 1e3                   # n em que n/B == L
print(f"latência L = {L:.2f} us | banda B = {B:.2f} GB/s | corte n* = {corte/1024:.1f} KiB")

fig, (a1, a2) = plt.subplots(1, 2, figsize=(12, 4.5))
a1.loglog(n, t, "o-", label="medido")
a1.loglog(n, [L + x / B / 1e3 for x in n], "--", label=f"modelo L + n/B")
a1.axvline(corte, color="gray", ls=":")
a1.text(corte * 1.2, L * 1.3, f"n* ≈ {corte/1024:.0f} KiB", color="gray")
a1.text(10, L * 3, "latência domina", fontsize=11)
a1.text(2e5, L * 3, "banda domina", fontsize=11)
a1.set(xlabel="tamanho da mensagem (bytes)", ylabel="tempo de ida (µs)",
       title="Tempo × tamanho")
a1.legend(); a1.grid(True, which="both", alpha=.3)

a2.semilogx(n, bw, "o-")
a2.axhline(B, color="gray", ls=":", label=f"B ≈ {B:.1f} GB/s")
a2.axvline(corte, color="gray", ls=":")
a2.set(xlabel="tamanho da mensagem (bytes)", ylabel="banda efetiva (GB/s)",
       title="Banda efetiva × tamanho")
a2.legend(); a2.grid(True, which="both", alpha=.3)

fig.tight_layout()
fig.savefig("pingpong.png", dpi=120)
