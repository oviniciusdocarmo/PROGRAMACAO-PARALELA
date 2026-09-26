#!/usr/bin/env python3
"""Gera o relatório da Tarefa 16 em PDF, no mesmo formato das tarefas anteriores.

Uso: python3 grafico.py && python3 gera_relatorio.py
Saída: Tarefa16_Matriz_Vetor_MPI.pdf
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
SAIDA = DIR / "Tarefa16_Matriz_Vetor_MPI.pdf"

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
    melhor = {}                                  # (N, processos) -> linha
    for r in csv.DictReader(open(DIR / "resultados.csv")):
        k = (int(r["N"]), int(r["processos"]))
        if k not in melhor or float(r["tempo_total_s"]) < float(melhor[k]["tempo_total_s"]):
            melhor[k] = r
    ns = sorted({n for n, _ in melhor})
    ps = sorted({p for _, p in melhor})

    def T(n, p, c="tempo_total_s"):
        return float(melhor[n, p][c]) * 1e3      # ms

    grande = ns[-1]
    pmelhor = min(ps, key=lambda p: T(grande, p))

    e = []
    e.append(P("UNIVERSIDADE FEDERAL DO RIO GRANDE DO NORTE", "cabecalho"))
    e.append(P("DEPARTAMENTO DE ENGENHARIA DE COMPUTAÇÃO E AUTOMAÇÃO",
               "cabecalho"))
    e.append(Spacer(1, 14))
    e.append(P("Tarefa 16: Produto Matriz-Vetor Usando MPI", "titulo"))
    e.append(P("Distribuição com MPI_Scatter e MPI_Bcast e coleta com "
               "MPI_Gather", "subtitulo"))
    e.append(P("Professor: Samuel Xavier de Souza<br/>"
               "Aluno: Vinícius Silva do Carmo<br/>"
               "Setembro de 2026", "autoria"))

    e.append(P("1. Objetivo", "h"))
    e.append(P(
        "Implementar um programa MPI que calcule o produto y = A·x, em que A "
        "é uma matriz M×N e x é um vetor de tamanho N. A matriz A deve ser "
        "dividida por linhas entre os processos com " + C("MPI_Scatter") +
        " e o vetor x distribuído inteiro com " + C("MPI_Bcast") + ". Cada "
        "processo calcula os elementos de y correspondentes às suas linhas e "
        "os envia de volta ao processo 0 com " + C("MPI_Gather") + ". "
        "Comparar os tempos com diferentes tamanhos de matriz e números de "
        "processos."))

    e.append(P("2. Ambiente de Execução", "h"))
    e.append(tabela([
        ["Item", "Valor"],
        ["Máquina", "Supercomputador NPAD/UFRN, partição amd-512, nó exclusivo"],
        ["Nó", "r2n09 — 128 núcleos, de 1 a 128 processos no mesmo nó"],
        ["Processador", "2 × AMD EPYC 7713 (Milan)"],
        ["MPI", "OpenMPI 5.0.10 (" + C("libraries/openmpi/5.0.10-gnu14-ucxmt") + ")"],
        ["Compilador", "GCC 14.2.0 via " + C("mpicc -O2")],
        ["Job", "SLURM 2127793"],
    ], [3.3 * cm, 12.7 * cm]))

    e.append(P("3. Implementação", "h"))
    e.append(P(
        "O processo 0 cria A (com A[i][j] = i + j) e x (com todos os valores "
        "iguais a 1). Com P processos, cada um recebe M/P linhas consecutivas "
        "de A por " + C("MPI_Scatter") + " (por isso M deve ser múltiplo de "
        "P) e o vetor x inteiro por " + C("MPI_Bcast") + ". Cada processo "
        "calcula as M/P posições de y das suas linhas, e o " +
        C("MPI_Gather") + " junta esses pedaços, na ordem dos processos, no "
        "vetor y do processo 0."))
    e.append(P(
        "O processo 0 mede com " + C("MPI_Wtime") + " três trechos: "
        "<b>distribuição</b> (" + C("MPI_Scatter") + " + " + C("MPI_Bcast") +
        "), <b>cálculo</b> das suas linhas e <b>coleta</b> (" +
        C("MPI_Gather") + "). Ao final, ele confere cada y[i] com o valor "
        "exato N·i + N(N−1)/2; todas as execuções deram 0 erros."))
    e.append(P(
        "Foram usadas matrizes quadradas de 1024, 4096 e 16384 (8 MB, 128 MB "
        "e 2 GB) com 1, 2, 4, …, 128 processos. Cada caso rodou 3 vezes e foi "
        "usada a execução de menor tempo total; a variação entre repetições "
        "foi pequena."))

    for i, n in enumerate(ns):
        tab = [["Processos", "Total (ms)", "Distribuição (ms)", "Cálculo (ms)",
                "Coleta (ms)", "Speedup total", "Speedup cálculo"]]
        for p in ps:
            tab.append([str(p), num(T(n, p), 2), num(T(n, p, "distribuicao_s"), 2),
                        num(T(n, p, "calculo_s"), 3), num(T(n, p, "coleta_s"), 3),
                        num(T(n, 1) / T(n, p), 2) + "×",
                        num(T(n, 1, "calculo_s") / T(n, p, "calculo_s"), 1) + "×"])
        e.append(KeepTogether([P("4. Resultados", "h")] * (i == 0) + [
            P(f"<b>Matriz {n} × {n}</b>", "p"),
            tabela(tab, [2.0 * cm, 2.2 * cm, 2.8 * cm, 2.3 * cm, 2.2 * cm,
                         2.3 * cm, 2.2 * cm]),
            Spacer(1, 8)]))
    e.append(figura(DIR / "img" / "tempos.png",
                    "Figura 1 — Tempo total (esquerda), speedup só do cálculo "
                    f"(centro) e composição do tempo para a matriz {grande}×{grande} "
                    "(direita), em função do número de processos."))

    e.append(P("5. Análise", "h"))
    e.append(P(
        "<b>O cálculo escala bem.</b> Na matriz de " f"{grande}×{grande}, o "
        "cálculo cai de " + num(T(grande, 1, "calculo_s"), 0) + " ms com 1 "
        "processo para " + num(T(grande, 128, "calculo_s"), 1) + " ms com 128 "
        "(speedup de " + num(T(grande, 1, "calculo_s") / T(grande, 128, "calculo_s"), 0) +
        "×), e na de " f"{ns[0]}×{ns[0]}" " o speedup do cálculo fica "
        "próximo do ideal. Cada processo trabalha só nas suas linhas, sem depender dos "
        "outros. Entre 8 e 16 processos o cálculo do processo 0 quase não "
        "caiu nas duas matrizes maiores; como o laço é limitado pela memória, "
        "isso provavelmente vem da forma como os processos foram "
        "posicionados nos domínios NUMA (não foi investigado)."))
    e.append(P(
        "<b>A distribuição domina o tempo total.</b> O produto faz só 2 "
        "operações por elemento de A, mas cada elemento precisa sair do "
        "processo 0 pelo " + C("MPI_Scatter") + ". Na matriz de "
        f"{grande}×{grande}, a distribuição é " +
        num(100 * T(grande, 1, "distribuicao_s") / T(grande, 1), 0) + "% do "
        "tempo com 1 processo e " +
        num(100 * T(grande, 128, "distribuicao_s") / T(grande, 128), 0) +
        "% com 128. Por isso o speedup total é bem menor que o do cálculo: "
        "no máximo " + num(T(grande, 1) / T(grande, pmelhor), 2) + f"× (com {pmelhor} "
        "processos). Enviar os dados custa mais que calcular com eles."))
    e.append(P(
        "O tempo de distribuição ainda cai de ~" +
        num(T(grande, 4, "distribuicao_s"), 0) + " ms (4 processos) para ~" +
        num(T(grande, 64, "distribuicao_s"), 0) + " ms (64): no mesmo nó, cada "
        "processo copia o seu bloco da memória do processo 0 e escreve no "
        "seu próprio vetor, e essas cópias (e o primeiro acesso às páginas "
        "novas) acontecem em paralelo. Com 1 processo, a “distribuição” é só "
        "a cópia da matriz inteira para o vetor local."))
    e.append(P(
        "<b>Matrizes pequenas não compensam.</b> Na matriz de 1024×1024 o "
        "cálculo leva ~1 ms e o custo fixo das operações coletivas é da mesma "
        "ordem: com 2 a 8 processos o programa fica mais lento que com 1, e o "
        "melhor caso (16 processos) é só " +
        num(T(ns[0], 1) / min(T(ns[0], p) for p in ps), 1) + "× mais rápido. "
        "Na de 4096×4096 o ganho máximo é " +
        num(T(ns[1], 1) / min(T(ns[1], p) for p in ps), 1) + "×."))
    e.append(P(
        "<b>Com 128 processos o tempo volta a subir</b> nos três tamanhos: o "
        "cálculo por processo já é pequeno, e a distribuição e a coleta, com "
        "mais participantes, ficam mais caras. Ainda assim a coleta é sempre "
        "pequena (no máximo ~1 ms), porque y tem só M valores."))

    e.append(P("6. Conclusão", "h"))
    e.append(P(
        "A divisão por linhas com " + C("MPI_Scatter") + ", " + C("MPI_Bcast") +
        " e " + C("MPI_Gather") + " dá o resultado correto e o cálculo escala "
        "quase linearmente com o número de processos. O tempo total, porém, é "
        "dominado por espalhar a matriz a partir do processo 0, porque o "
        "produto matriz-vetor faz pouca conta por dado transferido. O ganho "
        "só aparece em matrizes grandes e com um número moderado de "
        f"processos (até {num(T(grande, 1) / T(grande, pmelhor), 1)}× com "
        f"{pmelhor} processos na maior matriz). Na prática, compensaria cada "
        "processo gerar ou ler as suas próprias linhas, em vez de recebê-las "
        "do processo 0."))

    code = DIR / "img" / "code.png"
    if code.exists():
        e.append(PageBreak())
        e.append(P("7. Código-Fonte", "h"))
        e.append(figura(code, "Figura 2 — " + C("mxv.c") + ".",
                        largura=15 * cm))
    return e


def main():
    doc = SimpleDocTemplate(str(SAIDA), pagesize=A4,
                            leftMargin=2.5 * cm, rightMargin=2.5 * cm,
                            topMargin=2.0 * cm, bottomMargin=2.0 * cm,
                            title="Tarefa 16 - Produto Matriz-Vetor Usando MPI",
                            author="Vinícius Silva do Carmo")
    doc.build(conteudo(), canvasmaker=NumeradoCanvas)
    print(f"gerado: {SAIDA.name}")


if __name__ == "__main__":
    main()
