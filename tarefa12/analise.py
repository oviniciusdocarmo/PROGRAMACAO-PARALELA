#!/usr/bin/env python3
"""Tarefa 12 — tabelas e gráficos de escalabilidade.

Lê os CSVs produzidos por job_escalabilidade.sh e emite:
  - tabelas markdown (stdout) de speedup e eficiência
  - img/escalabilidade_forte.png  e  img/escalabilidade_fraca.png

Uso: python3 analise.py [diretorio_com_os_csv]
"""

import csv
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

DIR = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
IMG = DIR / "img"

VERSOES = ["v1-memcpy", "v2-doublebuf", "v3-firsttouch", "v4-regiao-unica"]
ROTULO = {
    "v1-memcpy":       "v1 · memcpy serial",
    "v2-doublebuf":    "v2 · double buffering",
    "v3-firsttouch":   "v3 · first touch NUMA",
    "v4-regiao-unica": "v4 · região paralela única",
}
COR = {
    "v1-memcpy":       "#c44e52",
    "v2-doublebuf":    "#dd8452",
    "v3-firsttouch":   "#55a868",
    "v4-regiao-unica": "#4c72b0",
}


def carrega(nome):
    """{versao: {threads: linha}}, mais a linha do sequencial."""
    dados, seq = {}, None
    with open(DIR / nome, newline="") as f:
        for r in csv.DictReader(f):
            r["threads"] = int(r["threads"])
            r["n"] = int(r["n"])
            r["tempo_s"] = float(r["tempo_s"])
            r["mlups"] = float(r["mlups"])
            if r["versao"] == "v0-sequencial":
                seq = r
            else:
                dados.setdefault(r["versao"], {})[r["threads"]] = r
    return dados, seq


def tabela(titulo, cabecalho, linhas):
    print(f"\n### {titulo}\n")
    print("| " + " | ".join(cabecalho) + " |")
    print("|" + "|".join("---" for _ in cabecalho) + "|")
    for l in linhas:
        print("| " + " | ".join(l) + " |")


def relatorio_forte(dados, seq):
    """Speedup S(p) = T_seq/T(p) e eficiência E(p) = S(p)/p, problema fixo."""
    ps = sorted(next(iter(dados.values())).keys())

    tabela(
        f"Escalabilidade forte — tempo (s), grade {seq['n']}×{seq['n']}, "
        f"{seq['passos']} passos",
        ["threads"] + [ROTULO[v] for v in VERSOES],
        [[str(p)] + [f"{dados[v][p]['tempo_s']:.3f}" for v in VERSOES] for p in ps],
    )
    print(f"\nReferência sequencial (v0): **{seq['tempo_s']:.3f} s** "
          f"({seq['mlups']:.0f} MLUPS)")

    tabela(
        "Escalabilidade forte — speedup S(p) = T(1 thread, sequencial) / T(p)",
        ["threads"] + [ROTULO[v] for v in VERSOES] + ["ideal"],
        [[str(p)] + [f"{seq['tempo_s'] / dados[v][p]['tempo_s']:.1f}×"
                     for v in VERSOES] + [f"{p}×"] for p in ps],
    )

    tabela(
        "Escalabilidade forte — eficiência E(p) = S(p)/p",
        ["threads"] + [ROTULO[v] for v in VERSOES],
        [[str(p)] + [f"{seq['tempo_s'] / dados[v][p]['tempo_s'] / p * 100:.0f}%"
                     for v in VERSOES] for p in ps],
    )
    return ps


def relatorio_fraca(dados, seq):
    """Trabalho por thread constante: a eficiência fraca é T(1)/T(p) — o tempo
    deveria ficar *igual*, já que problema e recursos crescem juntos."""
    ps = sorted(next(iter(dados.values())).keys())

    tabela(
        f"Escalabilidade fraca — tempo (s), {seq['n']}² células por thread, "
        f"{seq['passos']} passos",
        ["threads", "grade"] + [ROTULO[v] for v in VERSOES],
        [[str(p), f"{dados[VERSOES[0]][p]['n']}²"]
         + [f"{dados[v][p]['tempo_s']:.3f}" for v in VERSOES] for p in ps],
    )

    tabela(
        "Escalabilidade fraca — eficiência E(p) = T(1)/T(p) (ideal: 100%)",
        ["threads"] + [ROTULO[v] for v in VERSOES],
        [[str(p)] + [f"{dados[v][1]['tempo_s'] / dados[v][p]['tempo_s'] * 100:.0f}%"
                     for v in VERSOES] for p in ps],
    )

    tabela(
        "Escalabilidade fraca — vazão (MLUPS): células atualizadas por segundo",
        ["threads"] + [ROTULO[v] for v in VERSOES],
        [[str(p)] + [f"{dados[v][p]['mlups']:.0f}" for v in VERSOES] for p in ps],
    )
    return ps


def grafico(arquivo, titulo, ps, series, ideal, ylabel, log2y):
    fig, ax = plt.subplots(figsize=(7.5, 5))
    ax.plot(ps, ideal, "--", color="#888", lw=1.4, label="ideal", zorder=1)
    for v, ys in series.items():
        ax.plot(ps, ys, "o-", color=COR[v], lw=2, ms=5, label=ROTULO[v])
    ax.set_xscale("log", base=2)
    if log2y:
        ax.set_yscale("log", base=2)
    ax.set_xticks(ps)
    ax.set_xticklabels([str(p) for p in ps])
    ax.set_xlabel("threads (cores físicos)")
    ax.set_ylabel(ylabel)
    ax.set_title(titulo)
    ax.grid(alpha=0.3, which="both")
    ax.legend(frameon=False, fontsize=9)
    fig.tight_layout()
    IMG.mkdir(exist_ok=True)
    fig.savefig(IMG / arquivo, dpi=140)
    print(f"\n[gravado] img/{arquivo}")


def main():
    forte, seq_f = carrega("resultados_forte.csv")
    fraca, seq_w = carrega("resultados_fraca.csv")

    ps = relatorio_forte(forte, seq_f)
    grafico(
        "escalabilidade_forte.png",
        f"Escalabilidade forte — grade {seq_f['n']}×{seq_f['n']} fixa (NPAD, amd-512)",
        ps,
        {v: [seq_f["tempo_s"] / forte[v][p]["tempo_s"] for p in ps] for v in VERSOES},
        ps, "speedup S(p)", True,
    )

    ps = relatorio_fraca(fraca, seq_w)
    grafico(
        "escalabilidade_fraca.png",
        f"Escalabilidade fraca — {seq_w['n']}² células por thread (NPAD, amd-512)",
        ps,
        {v: [fraca[v][1]["tempo_s"] / fraca[v][p]["tempo_s"] * 100 for p in ps]
         for v in VERSOES},
        [100] * len(ps), "eficiência E(p) = T(1)/T(p)  [%]", False,
    )


if __name__ == "__main__":
    main()
