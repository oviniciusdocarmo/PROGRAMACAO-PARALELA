#!/usr/bin/env python3
"""Gera o relatório da Tarefa 13 em PDF, no mesmo formato das tarefas anteriores.

Uso: python3 grafico.py && python3 gera_relatorio.py
Saída: Tarefa13_Afinidade_Threads.pdf
"""

import csv
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas
from reportlab.platypus import (Image, KeepTogether, PageBreak, Paragraph,
                                SimpleDocTemplate, Spacer, Table, TableStyle)

DIR = Path(__file__).parent
SAIDA = DIR / "Tarefa13_Afinidade_Threads.pdf"

AZUL = colors.HexColor("#1f3864")
CINZA = colors.HexColor("#f2f2f2")
BORDA = colors.HexColor("#b0b0b0")

ss = getSampleStyleSheet()
S = {
    "titulo": ParagraphStyle("titulo", parent=ss["Title"], fontSize=15,
                             leading=19, spaceAfter=2, textColor=AZUL),
    "subtitulo": ParagraphStyle("subtitulo", parent=ss["Title"], fontSize=11.5,
                                leading=15, spaceAfter=10,
                                textColor=colors.HexColor("#444444")),
    "cabecalho": ParagraphStyle("cabecalho", parent=ss["Normal"], fontSize=10,
                                leading=13, alignment=TA_CENTER,
                                fontName="Helvetica-Bold"),
    "autoria": ParagraphStyle("autoria", parent=ss["Normal"], fontSize=10,
                              leading=14, alignment=TA_CENTER, spaceAfter=14),
    "h": ParagraphStyle("h", parent=ss["Heading2"], fontSize=12, leading=15,
                        spaceBefore=12, spaceAfter=5, textColor=AZUL),
    "p": ParagraphStyle("p", parent=ss["Normal"], fontSize=9.7, leading=13.4,
                        alignment=TA_JUSTIFY, spaceAfter=6),
    "leg": ParagraphStyle("leg", parent=ss["Normal"], fontSize=8.5,
                          leading=11, alignment=TA_CENTER, spaceBefore=3,
                          spaceAfter=10, textColor=colors.HexColor("#555555")),
    "cel": ParagraphStyle("cel", parent=ss["Normal"], fontSize=8.6, leading=11),
}


def P(txt, estilo="p"):
    return Paragraph(txt, S[estilo])


def C(txt):
    return f"<font face='Courier'>{txt}</font>"


def tabela(dados, larguras):
    """Tabela com cabeçalho azul e zebrado, como nos relatórios anteriores."""
    corpo = [[Paragraph(f"<b>{c}</b>" if i == 0 else c, S["cel"])
              for c in linha] for i, linha in enumerate(dados)]
    t = Table(corpo, colWidths=larguras, hAlign="LEFT", repeatRows=1)
    estilo = [
        ("BACKGROUND", (0, 0), (-1, 0), AZUL),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.4, BORDA),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("FONTNAME", (0, 1), (0, -1), "Helvetica-Bold"),
    ]
    estilo += [("BACKGROUND", (0, i), (-1, i), CINZA)
               for i in range(2, len(corpo), 2)]
    t.setStyle(TableStyle(estilo))
    return t


def figura(caminho, legenda, largura=16 * cm):
    px_w, px_h = ImageReader(str(caminho)).getSize()
    img = Image(str(caminho), width=largura, height=largura * px_h / px_w)
    return KeepTogether([img, P(legenda, "leg")])


class NumeradoCanvas(canvas.Canvas):
    """Rodapé "Página X de N", como nos relatórios anteriores."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._paginas = []

    def showPage(self):
        self._paginas.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        total = len(self._paginas)
        for estado in self._paginas:
            self.__dict__.update(estado)
            self.setFont("Helvetica", 8)
            self.setFillColor(colors.HexColor("#666666"))
            self.drawCentredString(A4[0] / 2, 1.2 * cm,
                                   f"Página {self._pageNumber} de {total}")
            super().showPage()
        super().save()


def num(x, casas):
    return f"{x:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def conteudo():
    melhor = {}                                  # (afinidade, threads) -> tempo
    for r in csv.DictReader(open(DIR / "resultados.csv")):
        k = (r["afinidade"], int(r["threads"]))
        melhor[k] = min(melhor.get(k, 1e9), float(r["tempo_s"]))
    binds = ["false", "true", "master", "close", "spread"]
    ps = sorted({p for _, p in melhor})
    t1 = min(melhor[b, 1] for b in binds)

    def S(b, p):
        return t1 / melhor[b, p]

    e = []
    e.append(P("UNIVERSIDADE FEDERAL DO RIO GRANDE DO NORTE", "cabecalho"))
    e.append(P("DEPARTAMENTO DE ENGENHARIA DE COMPUTAÇÃO E AUTOMAÇÃO",
               "cabecalho"))
    e.append(Spacer(1, 14))
    e.append(P("Tarefa 13: Escalabilidade com Afinidade de Threads", "titulo"))
    e.append(P("Navier-Stokes com OMP_PROC_BIND e OMP_PLACES em um nó do NPAD",
               "subtitulo"))
    e.append(P("Professor: Samuel Xavier de Souza<br/>"
               "Aluno: Vinícius Silva do Carmo<br/>"
               "Setembro de 2026", "autoria"))

    e.append(P("1. Objetivo", "h"))
    e.append(P(
        "Avaliar como a escalabilidade do código de Navier-Stokes muda ao "
        "utilizar os diversos tipos de afinidade de threads suportados pelo "
        "sistema operacional e pelo OpenMP, no mesmo tipo de nó de computação "
        "do NPAD utilizado na Tarefa 12."))

    e.append(P("2. Ambiente de Execução", "h"))
    e.append(tabela([
        ["Item", "Valor"],
        ["Máquina", "Supercomputador NPAD/UFRN, partição amd-512, nó exclusivo"],
        ["Nó", "r2n09 (o r2n21 da Tarefa 12 estava em manutenção; mesmo hardware)"],
        ["Processador", "2 × AMD EPYC 7713 (Milan), 128 núcleos"],
        ["NUMA", "8 domínios de 16 núcleos (0–15 no domínio 0, 16–31 no 1, …)"],
        ["Compilador", "GCC 14.2.0, " + C("-O3 -march=native -fopenmp")],
        ["Job", "SLURM 2127798 (conferência de afinidade: 2127837)"],
    ], [3.3 * cm, 12.7 * cm]))

    e.append(P("3. Metodologia", "h"))
    e.append(P(
        "O código é a versão final (v4) da Tarefa 12: difusão viscosa com "
        "stencil de 5 pontos, inicialização paralela (first touch) e uma só "
        "região paralela envolvendo o laço do tempo. O cálculo não foi "
        "alterado; a afinidade é escolhida apenas por variáveis de ambiente, "
        "como no slide:"))
    e.append(P(
        "• " + C("OMP_PROC_BIND=false") + ": sem afinidade; o <b>sistema "
        "operacional</b> decide onde cada thread roda e pode migrá-la (o " +
        C("OMP_PLACES") + " é ignorado).<br/>"
        "• " + C("OMP_PROC_BIND=true, master, close, spread") + " com " +
        C("OMP_PLACES=cores") + ": cada thread fica presa a um núcleo "
        "físico, escolhido pela política do <b>OpenMP</b>."))
    e.append(P(
        "O problema é o da escalabilidade forte da Tarefa 12: grade "
        "4096×4096 (duas grades de 134 MB) e 100 passos, com 1, 2, 4, …, 128 "
        "threads. Cada caso rodou 3 vezes e foi usado o menor tempo. O "
        "speedup é calculado em relação ao melhor tempo com 1 thread (" +
        num(t1, 2) + " s)."))

    tab = [["Threads", "false (SO)", "true", "master", "close", "spread"]]
    for p in ps:
        tab.append([str(p)] + [num(melhor[b, p], 3) + " (" +
                               num(S(b, p), 2 if S(b, p) < 0.1 else 1) + "×)"
                               for b in binds])
    e.append(KeepTogether([
        P("4. Resultados", "h"),
        P("Tempo em segundos e, entre parênteses, o speedup:"),
        tabela(tab, [1.6 * cm] + [2.88 * cm] * 5),
        Spacer(1, 8)]))
    e.append(figura(DIR / "img" / "afinidade.png",
                    "Figura 1 — Tempo (esquerda) e speedup (direita) para cada "
                    "política de " + C("OMP_PROC_BIND") + ". A curva de true "
                    "(tracejada) coincide com a de close."))

    e.append(P("5. Análise", "h"))
    e.append(P(
        "<b>spread é a melhor política em todos os casos</b> (" +
        num(S("spread", 16), 1) + "× com 16 threads e " +
        num(S("spread", 128), 1) + "× com 128). Com " + C("OMP_PLACES=cores") +
        " as threads ficam espalhadas pelo nó: com 8 threads há uma em cada "
        "domínio NUMA. Como o stencil é limitado pela banda de memória, cada "
        "thread usa um controlador de memória diferente, e o first touch "
        "deixa as linhas de cada thread na memória do seu domínio. Com 8 e 16 "
        "threads o speedup passa do ideal, porque as threads espalhadas "
        "somam o cache L3 de vários CCDs e as grades passam a caber quase "
        "inteiras em cache."))
    e.append(P(
        "<b>close quase não escala até 16 threads</b> (" +
        num(S("close", 4), 1) + "× a " + num(S("close", 16), 1) + "×): as "
        "threads ficam em núcleos vizinhos (0, 1, 2, …), ou seja, todas no "
        "domínio NUMA 0, disputando a banda de memória de um só domínio. O "
        "ganho só aparece quando as threads chegam a outros domínios: " +
        num(S("close", 32), 1) + "× com 32 (2 domínios) e " +
        num(S("close", 64), 0) + "× com 64 (um socket inteiro). Com 128 "
        "threads, close e spread colocam a thread i no núcleo i (conferido "
        "com " + C("OMP_DISPLAY_AFFINITY") + " no job 2127837); a diferença "
        "restante (" + num(melhor["close", 128], 3) + " s contra " +
        num(melhor["spread", 128], 3) + " s) vem da variação entre execuções "
        "tão curtas: no job de conferência, close variou de 0,016 a 0,031 s."))
    e.append(P(
        "<b>true dá os mesmos tempos que close</b>: no GCC (libgomp), " +
        C("true") + " usa a mesma distribuição de " + C("close") + "."))
    e.append(P(
        "<b>master piora com mais threads</b>: todas as threads ficam no "
        "núcleo da thread 0 e dividem um único núcleo, e cada thread a mais "
        "só acrescenta troca de contexto e sincronização (" +
        num(melhor["master", 128], 1) + " s com 128 threads, " +
        num(melhor["master", 128] / melhor["master", 1], 0) + "× mais lento "
        "que com 1)."))
    e.append(P(
        "<b>false (sistema operacional) fica perto de spread até 32 "
        "threads</b>, porque o escalonador do Linux distribui as threads "
        "pelos núcleos livres. Com 64 e 128 threads fica pior (" +
        num(S("false", 64), 1) + "× e " + num(S("false", 128), 1) + "×, contra " +
        num(S("spread", 64), 1) + "× e " + num(S("spread", 128), 1) + "× de "
        "spread): sem afinidade, as threads podem migrar e se afastar da "
        "memória onde fizeram o first touch, e o SO também pode colocar duas "
        "threads nos dois hyperthreads de um mesmo núcleo (o nó expõe 256 "
        "CPUs lógicas)."))
    e.append(P(
        "Na Tarefa 12, que usou spread + cores, a mesma versão chegou a "
        "0,011 s (106,9×) com 128 threads no r2n21. Aqui foram " +
        num(melhor["spread", 128], 3) + " s no r2n09 e 0,013–0,015 s no job "
        "de conferência: com 128 threads cada execução dura só ~15 ms e varia "
        "bastante entre execuções e entre nós."))

    e.append(P("6. Conclusão", "h"))
    e.append(P(
        "Com o mesmo código e o mesmo tipo de nó, só a afinidade muda o "
        "speedup com 16 threads de " + num(S("master", 16), 1) + "× (master) "
        "a " + num(S("close", 16), 1) + "× (close) e " +
        num(S("spread", 16), 1) + "× (spread). Como o Navier-Stokes é "
        "limitado pela banda de memória, a melhor escolha no nó NUMA do NPAD "
        "é espalhar as threads (" + C("OMP_PROC_BIND=spread") + ", " +
        C("OMP_PLACES=cores") + "): todos os controladores de memória são "
        "usados desde poucas threads e o first touch continua valendo. "
        "Deixar o sistema operacional decidir funciona bem até 32 threads, "
        "mas perde desempenho com o nó cheio, e close/true só se aproximam "
        "de spread quando todos os núcleos estão em uso."))

    code = DIR / "img" / "code.png"
    if code.exists():
        e.append(PageBreak())
        e.append(P("7. Código-Fonte", "h"))
        e.append(figura(code, "Figura 2 — " + C("fluid.c") + ".",
                        largura=15 * cm))
    return e


def main():
    doc = SimpleDocTemplate(str(SAIDA), pagesize=A4,
                            leftMargin=2.5 * cm, rightMargin=2.5 * cm,
                            topMargin=2.0 * cm, bottomMargin=2.0 * cm,
                            title="Tarefa 13 - Afinidade de Threads",
                            author="Vinícius Silva do Carmo")
    doc.build(conteudo(), canvasmaker=NumeradoCanvas)
    print(f"gerado: {SAIDA.name}")


if __name__ == "__main__":
    main()
