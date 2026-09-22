#!/usr/bin/env python3
"""Gera o relatório da Tarefa 14 em PDF, no mesmo formato das tarefas anteriores.

Uso: python3 grafico.py && python3 gera_relatorio.py
Saída: Tarefa14_Ping_Pong_MPI.pdf
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
from reportlab.platypus import (Image, KeepTogether, Paragraph,
                                SimpleDocTemplate, Spacer, Table, TableStyle)

DIR = Path(__file__).parent
SAIDA = DIR / "Tarefa14_Ping_Pong_MPI.pdf"

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


def tamanho(b):
    for unid, fator in (("MB", 1 << 20), ("KB", 1 << 10)):
        if b >= fator:
            return f"{b // fator} {unid}"
    return f"{b} B"


def num(x, casas):
    return f"{x:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def conteudo():
    linhas = list(csv.DictReader(open(DIR / "resultados.csv")))
    n = [int(r["bytes"]) for r in linhas]
    ida = [float(r["tempo_por_troca_us"]) / 2 for r in linhas]
    L = ida[0]
    B = n[-1] / (ida[-1] - L) / 1e3            # GB/s
    corte = L * B * 1e3                        # bytes

    e = []
    e.append(P("UNIVERSIDADE FEDERAL DO RIO GRANDE DO NORTE", "cabecalho"))
    e.append(P("DEPARTAMENTO DE ENGENHARIA DE COMPUTAÇÃO E AUTOMAÇÃO",
               "cabecalho"))
    e.append(Spacer(1, 14))
    e.append(P("Tarefa 14: Comunicação Ponto-a-Ponto em MPI", "titulo"))
    e.append(P("Latência e largura de banda medidas com ping-pong "
               "no supercomputador do NPAD", "subtitulo"))
    e.append(P("Professor: Samuel Xavier de Souza<br/>"
               "Aluno: Vinícius Silva do Carmo<br/>"
               "Setembro de 2026", "autoria"))

    e.append(P("1. Objetivo", "h"))
    e.append(P(
        "Implementar um programa MPI com exatamente dois processos, em que o "
        "processo 0 envia uma mensagem ao processo 1 e este a devolve "
        "imediatamente (ping-pong). Medir com " + C("MPI_Wtime") + " o tempo "
        "de várias trocas consecutivas para tamanhos de 8 bytes a 16 MB, "
        "analisar graficamente o tempo em função do tamanho e identificar os "
        "regimes dominados pela latência e pela largura de banda."))

    e.append(P("2. Ambiente de Execução", "h"))
    e.append(tabela([
        ["Item", "Valor"],
        ["Máquina", "Supercomputador NPAD/UFRN, partição amd-512, nós exclusivos"],
        ["Nós", "r2n03 e r2n04 — um processo por nó (a mensagem atravessa a rede)"],
        ["Processador", "2 × AMD EPYC 7713 (Milan) por nó"],
        ["MPI", "OpenMPI 5.0.10 (" + C("libraries/openmpi/5.0.10-gnu14-ucxmt") + ")"],
        ["Compilador", "GCC 14.2.0 via " + C("mpicc -O2")],
        ["Job", "SLURM 2117758"],
    ], [3.3 * cm, 12.7 * cm]))

    e.append(P("3. Metodologia", "h"))
    e.append(P(
        "Uma <b>troca</b> é uma ida (" + C("MPI_Send") + " de 0 para 1) e uma "
        "volta (" + C("MPI_Send") + " de 1 para 0), cada uma casada com um "
        + C("MPI_Recv") + ". Para cada tamanho, o programa faz 10 trocas de "
        "aquecimento (que também sincronizam os dois processos) e mede o tempo "
        "total de 10 000 trocas (até 64 KB) ou 200 trocas (acima disso). O "
        "tempo de ida é metade do tempo por troca, e a banda efetiva é "
        "2n / tempo por troca."))
    e.append(P(
        "Os dados são comparados ao modelo linear de comunicação "
        "<b>t(n) = L + n/B</b>, com a latência L estimada pela menor mensagem "
        "(8 B) e a banda B pela maior (16 MB)."))

    e.append(P("4. Resultados", "h"))
    tab = [["Tamanho", "Trocas", "Tempo total (s)", "Tempo de ida (µs)",
            "Banda efetiva (GB/s)"]]
    for r in linhas:
        tab.append([tamanho(int(r["bytes"])), r["trocas"],
                    num(float(r["tempo_total_s"]), 4),
                    num(float(r["tempo_por_troca_us"]) / 2, 2),
                    num(float(r["banda_MBps"]) / 1000, 3)])
    e.append(tabela(tab, [2.6 * cm, 2.2 * cm, 3.4 * cm, 3.6 * cm, 4.2 * cm]))
    e.append(Spacer(1, 8))
    e.append(figura(DIR / "img" / "pingpong.png",
                    "Figura 1 — Tempo de ida (esquerda, escala log-log) e banda "
                    "efetiva (direita) em função do tamanho da mensagem."))

    e.append(P("5. Análise", "h"))
    e.append(tabela([
        ["Parâmetro", "Valor", "Significado"],
        ["Latência L", f"{num(L, 2)} µs",
         "Custo fixo de qualquer mensagem, mesmo vazia"],
        ["Banda B", f"{num(B, 1)} GB/s",
         "Taxa máxima de transferência entre os nós"],
        ["Corte n* = L·B", f"≈ {corte / 1024:.0f} KB",
         "Tamanho em que latência e transferência pesam igual"],
    ], [3.6 * cm, 3.2 * cm, 9.2 * cm]))
    e.append(Spacer(1, 6))
    e.append(P(
        "<b>Regime de latência (até ~1 KB).</b> O tempo de ida fica "
        "praticamente constante, entre 1,3 e 2 µs, enquanto o tamanho cresce "
        "128×. Enviar 8 B ou 512 B custa quase o mesmo e a banda efetiva é "
        "ínfima. Nesse regime, a forma de ganhar desempenho é enviar "
        "<i>menos</i> mensagens, agrupando dados pequenos em uma só."))
    e.append(P(
        "<b>Transição (~1 KB a ~1 MB).</b> O tempo passa a crescer com n e a "
        "banda efetiva sobe rapidamente, atingindo metade do máximo por volta "
        "de 64 KB. Nessa faixa o tempo medido fica acima do modelo linear, "
        "por custos que ele não representa: cópias para buffers internos e a "
        "mudança do protocolo <i>eager</i> para <i>rendezvous</i>, que "
        "acrescenta um handshake antes de mensagens grandes."))
    e.append(P(
        "<b>Regime de largura de banda (acima de ~1 MB).</b> O tempo cresce "
        "linearmente com n — dobrar a mensagem dobra o tempo — e a banda "
        f"efetiva se estabiliza em ≈ {num(B, 1)} GB/s, compatível com um "
        "enlace InfiniBand de 100 Gb/s. A latência fixa representa menos de "
        "1% do tempo a partir de 1 MB; aqui só reduzir o volume de dados "
        "enviados melhora o desempenho."))

    e.append(P("6. Conclusão", "h"))
    e.append(P(
        f"A comunicação ponto-a-ponto entre dois nós do NPAD é descrita bem "
        f"pelo modelo t(n) = L + n/B, com L ≈ {num(L, 1)} µs e "
        f"B ≈ {num(B, 1)} GB/s. Mensagens menores que ~{corte / 1024:.0f} KB "
        "são dominadas pela latência e maiores que isso pela largura de "
        "banda. Para programas MPI, isso significa que muitas mensagens "
        "pequenas desperdiçam a rede e que vale agregar dados antes de "
        "comunicar."))

    e.append(P("7. Código-Fonte", "h"))
    e.append(figura(DIR / "img" / "code.png",
                    "Figura 2 — " + C("pingpong.c") + ".", largura=15 * cm))
    return e


def main():
    doc = SimpleDocTemplate(str(SAIDA), pagesize=A4,
                            leftMargin=2.5 * cm, rightMargin=2.5 * cm,
                            topMargin=2.0 * cm, bottomMargin=2.0 * cm,
                            title="Tarefa 14 - Comunicação Ponto-a-Ponto em MPI",
                            author="Vinícius Silva do Carmo")
    doc.build(conteudo(), canvasmaker=NumeradoCanvas)
    print(f"gerado: {SAIDA.name}")


if __name__ == "__main__":
    main()
