#!/usr/bin/env python3
"""Tarefa 12 — leitura dos JSONs do PaScal Analyzer.

O PaScal Viewer é uma aplicação web; este script faz a mesma leitura dos dados
localmente, para que os números apareçam no relatório sem depender do navegador
e para conferir que o que o Viewer mostra bate com a medição independente de
analise.py.

Produz:
  - tabelas markdown (stdout): eficiência paralela, escalabilidade forte e a
    diagonal de escalabilidade fraca, por versão
  - img/pascal_mapa_eficiencia.png: os quatro mapas de calor lado a lado, no
    mesmo formato do Viewer

Uso: python3 pascal_analise.py [diretorio_com_os_json]
"""

import json
import re
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

DIR = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
IMG = DIR / "img"

VERSOES = ["v1", "v2", "v3", "v4"]
ROTULO = {
    "v1": "v1 · memcpy serial",
    "v2": "v2 · double buffering",
    "v3": "v3 · first touch NUMA",
    "v4": "v4 · região paralela única",
}
REGIAO_INIT = "1"        # marcada com pascal_start(1)/pascal_stop(1)
REGIAO_CALCULO = "2"     # marcada com pascal_start(2)/pascal_stop(2)

BASE = 2048              # células por thread: n = BASE·√p


def ordem_das_entradas(config):
    """Recupera a ordem das entradas a que o índice do dado se refere.

    Armadilha do formato: `config.arguments` vem **embaralhado** (ordem
    diferente em cada JSON), mas o índice na chave de `data` segue a ordem
    original da linha de comando. Usar `arguments` produziria um mapa
    silenciosamente errado — os tempos por configuração ficam certos, mas
    colados no tamanho de problema errado.

    A ordem original sobrevive em `config.command`, que guarda a linha de
    comando inteira, inclusive o `--ipts` como foi digitado.
    """
    m = re.search(r"--?i(?:pts)?\s+(\S+)", config["command"])
    if m:
        return [int(x.strip(" \"'")) for x in m.group(1).split(",")]
    # sem o comando, resta assumir que as entradas eram crescentes
    return sorted(int(a) for a in config["arguments"])


def carrega(versao):
    """Devolve (calc, init) com calc[nucleos][n] = tempo mediano em segundos."""
    with open(DIR / f"pascal_{versao}.json") as f:
        j = json.load(f)

    entradas = ordem_das_entradas(j["config"])
    n_de_indice = dict(enumerate(entradas))

    bruto = {}
    for chave, reg in j["data"].items():
        nucleos, ipt, _rep = (int(x) for x in chave.split(";"))
        n = n_de_indice[ipt]
        marcas = reg["regions"]
        # a instrumentação está fora das regiões paralelas: uma marcação só
        calc = max(m[1] - m[0] for m in marcas[REGIAO_CALCULO])
        init = max(m[1] - m[0] for m in marcas[REGIAO_INIT])
        bruto.setdefault((nucleos, n), {"calc": [], "init": []})
        bruto[(nucleos, n)]["calc"].append(calc)
        bruto[(nucleos, n)]["init"].append(init)

    calc, init = {}, {}
    for (nucleos, n), v in bruto.items():
        calc.setdefault(nucleos, {})[n] = float(np.median(v["calc"]))
        init.setdefault(nucleos, {})[n] = float(np.median(v["init"]))

    # Trava contra o mapeamento errado: com um núcleo só, o tempo tem de
    # crescer com n. Se não crescer, o índice foi associado ao tamanho errado e
    # todo o resto da análise seria ficção plausível.
    tempos = [calc[1][n] for n in sorted(calc[1])]
    if any(b <= a for a, b in zip(tempos, tempos[1:])):
        sys.exit(f"pascal_{versao}.json: tempo de 1 núcleo não cresce com n "
                 f"({tempos}) — mapeamento entrada→tamanho suspeito")
    return calc, init


def tabela(titulo, cabecalho, linhas):
    print(f"\n### {titulo}\n")
    print("| " + " | ".join(cabecalho) + " |")
    print("|" + "|".join("---" for _ in cabecalho) + "|")
    for l in linhas:
        print("| " + " | ".join(l) + " |")


def mlups(n, tempo, passos=50):
    """Milhões de células atualizadas por segundo — a taxa de trabalho útil,
    comparável entre tamanhos de problema diferentes."""
    return (n - 2) ** 2 * passos / tempo / 1e6


def main():
    dados, nucleos_lista, tamanhos = {}, None, None
    for v in VERSOES:
        try:
            dados[v] = carrega(v)
        except FileNotFoundError:
            print(f"[aviso] pascal_{v}.json ausente — pulando", file=sys.stderr)
    if not dados:
        sys.exit("nenhum JSON do PaScal encontrado")

    calc0 = next(iter(dados.values()))[0]
    nucleos_lista = sorted(calc0.keys())
    tamanhos = sorted(calc0[nucleos_lista[0]].keys())

    # Pares da diagonal: p núcleos ↔ n = BASE·√p (trabalho por thread constante)
    diagonal = []
    for p in nucleos_lista:
        alvo = round(BASE * p ** 0.5)
        n = min(tamanhos, key=lambda x: abs(x - alvo))
        if abs(n - alvo) <= 2:
            diagonal.append((p, n))

    # ── Diagonal: escalabilidade fraca ───────────────────────────────────
    tabela(
        "PaScal — diagonal do mapa = escalabilidade fraca (região de cálculo)",
        ["núcleos", "n"] + [ROTULO[v] for v in dados],
        [[str(p), f"{n}²"] + [f"{dados[v][0][p][n]:.3f} s" for v in dados]
         for p, n in diagonal],
    )

    p0, n0 = diagonal[0]
    tabela(
        "PaScal — eficiência fraca na diagonal, E = T(1, 2048²)/T(p, nₚ)",
        ["núcleos"] + [ROTULO[v] for v in dados],
        [[str(p)] + [f"{dados[v][0][p0][n0] / dados[v][0][p][n] * 100:.0f}%"
                     for v in dados]
         for p, n in diagonal],
    )

    tabela(
        "PaScal — vazão na diagonal (MLUPS)",
        ["núcleos", "n"] + [ROTULO[v] for v in dados],
        [[str(p), f"{n}²"] + [f"{mlups(n, dados[v][0][p][n]):.0f}" for v in dados]
         for p, n in diagonal],
    )

    # ── Linhas: escalabilidade forte, por tamanho ────────────────────────
    for v in dados:
        calc = dados[v][0]
        tabela(
            f"PaScal — eficiência paralela E(p) = T(1)/(p·T(p)) · {ROTULO[v]}",
            ["núcleos"] + [f"n={n}" for n in tamanhos],
            [[str(p)] + [f"{calc[1][n] / (p * calc[p][n]) * 100:.0f}%"
                         if n in calc.get(p, {}) else "—" for n in tamanhos]
             for p in nucleos_lista],
        )

    # ── Custo da inicialização (região 1) ────────────────────────────────
    # É aqui que v3/v4 pagam o first touch paralelo; vale mostrar que o que se
    # ganha na região 2 não foi só empurrado para a região 1.
    maior = tamanhos[-1]
    tabela(
        f"PaScal — região 1 (inicialização) vs região 2 (cálculo), n={maior}²",
        ["núcleos"] + [f"{ROTULO[v]}: init / calc" for v in dados],
        [[str(p)] + [f"{dados[v][1][p][maior]:.2f} / {dados[v][0][p][maior]:.2f} s"
                     for v in dados]
         for p in nucleos_lista],
    )

    # ── Mapa de calor, no formato do Viewer ──────────────────────────────
    fig, axes = plt.subplots(1, len(dados), figsize=(4.3 * len(dados), 4.6),
                             sharey=True)
    if len(dados) == 1:
        axes = [axes]
    for ax, v in zip(axes, dados):
        calc = dados[v][0]
        m = np.full((len(nucleos_lista), len(tamanhos)), np.nan)
        for li, p in enumerate(nucleos_lista):
            for ci, n in enumerate(tamanhos):
                if n in calc.get(p, {}) and n in calc.get(1, {}):
                    m[li, ci] = calc[1][n] / (p * calc[p][n]) * 100
        im = ax.imshow(m, vmin=0, vmax=100, cmap="RdYlGn", aspect="auto",
                       origin="lower")
        ax.set_xticks(range(len(tamanhos)))
        ax.set_xticklabels([str(n) for n in tamanhos], rotation=45,
                           ha="right", fontsize=8)
        ax.set_yticks(range(len(nucleos_lista)))
        ax.set_yticklabels([str(p) for p in nucleos_lista], fontsize=8)
        ax.set_title(ROTULO[v], fontsize=10)
        ax.set_xlabel("tamanho da entrada n")
        for li in range(m.shape[0]):
            for ci in range(m.shape[1]):
                if not np.isnan(m[li, ci]):
                    ax.text(ci, li, f"{m[li, ci]:.0f}", ha="center",
                            va="center", fontsize=6.5)
        dx = [tamanhos.index(n) for _, n in diagonal]
        dy = [nucleos_lista.index(p) for p, _ in diagonal]
        ax.plot(dx, dy, color="#111", lw=1.4, ls=":",
                label="diagonal = esc. fraca")
    axes[0].set_ylabel("núcleos")
    axes[0].legend(fontsize=7, loc="upper left", frameon=True)
    fig.colorbar(im, ax=axes, label="eficiência paralela [%]", shrink=0.85)
    fig.suptitle("PaScal — mapa de eficiência paralela (NPAD, amd-512)",
                 fontsize=12)
    IMG.mkdir(exist_ok=True)
    fig.savefig(IMG / "pascal_mapa_eficiencia.png", dpi=140, bbox_inches="tight")
    print("\n[gravado] img/pascal_mapa_eficiencia.png")


if __name__ == "__main__":
    main()
