#!/usr/bin/env python3
"""Gera o relatório da Tarefa 15 em PDF, no mesmo formato das tarefas anteriores.

Uso: python3 grafico.py && python3 gera_relatorio.py
Saída: Tarefa15_Difusao_Calor_MPI.pdf
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
SAIDA = DIR / "Tarefa15_Difusao_Calor_MPI.pdf"

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
    melhor = {}                                  # (versao, pontos) -> µs/passo
    for r in csv.DictReader(open(DIR / "resultados.csv")):
        k = (int(r["versao"]), int(r["pontos"]))
        us = float(r["tempo_s"]) / int(r["passos"]) * 1e6
        melhor[k] = min(melhor.get(k, us), us)
    ns = sorted({n for _, n in melhor})

    e = []
    e.append(P("UNIVERSIDADE FEDERAL DO RIO GRANDE DO NORTE", "cabecalho"))
    e.append(P("DEPARTAMENTO DE ENGENHARIA DE COMPUTAÇÃO E AUTOMAÇÃO",
               "cabecalho"))
    e.append(Spacer(1, 14))
    e.append(P("Tarefa 15: Comunicação Não Bloqueante em MPI", "titulo"))
    e.append(P("Difusão de calor em uma barra 1D com sobreposição de "
               "computação e comunicação", "subtitulo"))
    e.append(P("Professor: Samuel Xavier de Souza<br/>"
               "Aluno: Vinícius Silva do Carmo<br/>"
               "Setembro de 2026", "autoria"))

    e.append(P("1. Objetivo", "h"))
    e.append(P(
        "Implementar uma simulação da difusão de calor em uma barra 1D, "
        "dividida entre dois ou mais processos MPI, em que cada processo "
        "simula um trecho da barra com células extras para a troca de bordas "
        "com os vizinhos. Implementar três versões — com " + C("MPI_Send") +
        "/" + C("MPI_Recv") + ", com " + C("MPI_Isend") + "/" + C("MPI_Irecv") +
        " e " + C("MPI_Wait") + ", e com " + C("MPI_Test") + " para atualizar "
        "os pontos internos enquanto a comunicação não termina — comparar os "
        "tempos de execução e discutir os ganhos com a sobreposição de "
        "comunicação e computação."))

    e.append(P("2. Ambiente de Execução", "h"))
    e.append(tabela([
        ["Item", "Valor"],
        ["Máquina", "Supercomputador NPAD/UFRN, partição amd-512, nós exclusivos"],
        ["Nós", "r2n01 e r2n02 — 16 processos, 8 por nó, distribuídos "
                "alternadamente (" + C("--map-by node") + ")"],
        ["Processador", "2 × AMD EPYC 7713 (Milan) por nó"],
        ["MPI", "OpenMPI 5.0.10 (" + C("libraries/openmpi/5.0.10-gnu14-ucxmt") + ")"],
        ["Compilador", "GCC 14.2.0 via " + C("mpicc -O2")],
        ["Job", "SLURM 2127428"],
    ], [3.3 * cm, 12.7 * cm]))

    e.append(P("3. Implementação", "h"))
    e.append(P(
        "A barra é dividida em trechos de n pontos, um por processo. Cada "
        "processo guarda seu trecho em " + C("u[1..n]") + " e duas células "
        "extras, " + C("u[0]") + " e " + C("u[n+1]") + ", que recebem o valor "
        "da borda dos vizinhos. A cada passo, o novo valor de cada ponto é "
        + C("v[i] = u[i] + K·(u[i-1] - 2u[i] + u[i+1])") + ", com K = 0,25 "
        "(estável). A ponta esquerda da barra é mantida em 100 e a direita "
        "em 0; nas pontas, a célula extra não é trocada e guarda esse valor."))
    e.append(tabela([
        ["Versão", "Troca de bordas", "Atualização"],
        ["v1", C("MPI_Send") + "/" + C("MPI_Recv") + ". Processos pares "
               "enviam enquanto ímpares recebem e depois invertem, para não "
               "haver impasse",
         "Depois da troca, todos os pontos"],
        ["v2", C("MPI_Irecv") + " e " + C("MPI_Isend") + " com os dois "
               "vizinhos, guardando um " + C("MPI_Request") + " por operação",
         "Pontos internos (2 a n-1), " + C("MPI_Wait") + " nas requisições e, "
         "por fim, os pontos 1 e n"],
        ["v3", "Igual à v2",
         "Pontos internos em blocos de 256, chamando " + C("MPI_Test") +
         " entre os blocos até a comunicação terminar; depois os pontos 1 e n"],
    ], [1.6 * cm, 7.2 * cm, 7.2 * cm]))
    e.append(Spacer(1, 6))
    e.append(P(
        "Os pontos internos não dependem das células extras, então podem ser "
        "calculados enquanto as mensagens estão em trânsito; só os pontos 1 "
        "e n precisam esperar. As três versões produzem o mesmo resultado "
        "(o valor final de " + C("u[n]") + " no processo 0 é idêntico)."))
    e.append(P(
        "O trabalho total foi mantido fixo (n × passos = 10<super>9</super>) "
        "e n variou de 100 a 1 000 000 pontos por processo. Os processos "
        "vizinhos ficam em nós diferentes, então toda troca de borda passa "
        "pela rede. Cada caso rodou 3 vezes e foi usado o menor tempo, "
        "medido com " + C("MPI_Wtime") + " no processo 0."))

    e.append(P("4. Resultados", "h"))
    tab = [["Pontos por processo", "Passos", "v1 (µs/passo)",
            "v2 (µs/passo)", "v3 (µs/passo)", "Ganho v2", "Ganho v3"]]
    for n in ns:
        tab.append([f"{n:,}".replace(",", "."), f"{10**9 // n:,}".replace(",", "."),
                    num(melhor[1, n], 2), num(melhor[2, n], 2),
                    num(melhor[3, n], 2),
                    num(melhor[1, n] / melhor[2, n], 2) + "×",
                    num(melhor[1, n] / melhor[3, n], 2) + "×"])
    e.append(tabela(tab, [2.8 * cm, 2.2 * cm, 2.3 * cm, 2.3 * cm, 2.3 * cm,
                          2.05 * cm, 2.05 * cm]))
    e.append(Spacer(1, 8))
    e.append(figura(DIR / "img" / "tempos.png",
                    "Figura 1 — Tempo por passo (esquerda) e ganho em relação "
                    "à versão bloqueante (direita) em função do número de "
                    "pontos por processo."))

    e.append(P("5. Análise", "h"))
    e.append(P(
        "<b>Trechos pequenos (100 pontos): a comunicação domina.</b> A conta "
        "leva poucas dezenas de nanossegundos e o passo custa praticamente só "
        "a troca de bordas. A v1 leva " + num(melhor[1, 100], 1) + " µs por "
        "passo e as versões não bloqueantes, " + num(melhor[2, 100], 1) +
        " µs: metade. Com " + C("MPI_Send") + "/" + C("MPI_Recv") + " as "
        "trocas acontecem em duas fases (pares enviam, depois ímpares), ou "
        "seja, duas latências de rede por passo; com " + C("MPI_Isend") + "/"
        + C("MPI_Irecv") + " as quatro mensagens de cada processo ficam em "
        "trânsito ao mesmo tempo e o passo paga uma latência só. Aqui o ganho "
        "vem de não serializar a comunicação, não da sobreposição, porque "
        "quase não há conta para esconder a espera."))
    e.append(P(
        "<b>Trechos médios (1 000 a 100 000 pontos): a sobreposição aparece.</b> "
        "Com 1 000 pontos a conta (~" + num(melhor[1, 1000] - melhor[1, 100], 1) +
        " µs) tem a mesma ordem da latência. Se não houvesse sobreposição, a "
        "v2 levaria cerca de " + num(melhor[2, 100] + melhor[1, 1000] - melhor[1, 100], 1) +
        " µs (comunicação + conta); ela leva " + num(melhor[2, 1000], 1) +
        " µs, porque parte da latência fica escondida atrás dos pontos "
        "internos. O ganho sobre a v1 cai de ~1,9× para ~1,2–1,3× à medida "
        "que a conta passa a dominar, pois a latência (alguns µs) economizada "
        "vira uma fração cada vez menor do passo."))
    e.append(P(
        "<b>Trechos grandes (1 000 000 de pontos): a computação domina.</b> "
        "Cada passo leva ~3 ms de conta contra poucos µs de comunicação; as "
        "três versões ficam empatadas dentro da variação entre execuções, "
        "já que não há quase nada para esconder."))
    e.append(P(
        "<b>v2 × v3.</b> As duas têm desempenho parecido. Como as mensagens "
        "têm só 8 bytes, o OpenMPI as envia em modo <i>eager</i> e a rede "
        "progride sozinha enquanto o processo calcula; por isso o "
        + C("MPI_Wait") + " depois da conta já encontra a comunicação quase "
        "pronta e o " + C("MPI_Test") + " não tem o que adiantar. A v3 ainda "
        "paga o custo das chamadas a " + C("MPI_Test") + " e do laço em "
        "blocos, o que a deixa um pouco mais lenta nos trechos grandes. O "
        + C("MPI_Test") + " vale mais quando a biblioteca só avança a "
        "comunicação dentro das chamadas MPI (mensagens grandes, protocolo "
        "<i>rendezvous</i>)."))
    e.append(P(
        "Entre as repetições, os tempos variaram até ~50% nos trechos de "
        "10 000 a 100 000 pontos (ruído de rede e de sincronização entre "
        "processos), por isso as diferenças pequenas nessa faixa não são "
        "conclusivas; os ganhos de ~2× nos trechos pequenos se repetiram em "
        "todas as execuções."))

    e.append(P("6. Conclusão", "h"))
    e.append(P(
        "A comunicação não bloqueante reduziu o tempo por passo à metade "
        "quando a troca de bordas domina, ao permitir que as mensagens com "
        "os dois vizinhos fiquem em trânsito juntas, e escondeu parte da "
        "latência atrás da atualização dos pontos internos quando a conta tem "
        "a mesma ordem da latência. Quando a conta domina, as três versões se "
        "equivalem. Entre " + C("MPI_Wait") + " e " + C("MPI_Test") + " não "
        "houve diferença relevante para mensagens pequenas, e a versão com "
        + C("MPI_Wait") + " é a mais simples."))

    code = DIR / "img" / "code.png"
    if code.exists():
        e.append(PageBreak())
        e.append(P("7. Código-Fonte", "h"))
        e.append(figura(code, "Figura 2 — " + C("calor.c") + ".",
                        largura=12.5 * cm))
    return e


def main():
    doc = SimpleDocTemplate(str(SAIDA), pagesize=A4,
                            leftMargin=2.5 * cm, rightMargin=2.5 * cm,
                            topMargin=2.0 * cm, bottomMargin=2.0 * cm,
                            title="Tarefa 15 - Comunicação Não Bloqueante em MPI",
                            author="Vinícius Silva do Carmo")
    doc.build(conteudo(), canvasmaker=NumeradoCanvas)
    print(f"gerado: {SAIDA.name}")


if __name__ == "__main__":
    main()
