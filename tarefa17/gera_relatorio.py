#!/usr/bin/env python3
"""Gera o relatório da Tarefa 17 em PDF, no mesmo formato das tarefas anteriores.

Uso: python3 grafico.py && python3 gera_relatorio.py
Saída: Tarefa17_Matriz_Vetor_Colunas_MPI.pdf
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
SAIDA = DIR / "Tarefa17_Matriz_Vetor_Colunas_MPI.pdf"

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


def ms(x):
    return num(x, 3 if x < 0.1 else 2 if x < 10 else 1 if x < 1000 else 0)


def conteudo():
    melhor = {}                                  # (versao, N, processos) -> linha
    for r in csv.DictReader(open(DIR / "resultados.csv")):
        k = (r["versao"], int(r["N"]), int(r["processos"]))
        if k not in melhor or float(r["tempo_total_s"]) < float(melhor[k]["tempo_total_s"]):
            melhor[k] = r
    ns = sorted({n for _, n, _ in melhor})
    ps = sorted({p for _, _, p in melhor})

    def T(v, n, p, c="tempo_total_s"):
        return float(melhor[v, n, p][c]) * 1e3   # ms

    def razao(n, p, c="distribuicao_s"):
        return T("colunas", n, p, c) / T("linhas", n, p, c)

    g, pm = ns[-1], ps[-1]
    MB = g * g * 8 / 1e6

    e = []
    e.append(P("UNIVERSIDADE FEDERAL DO RIO GRANDE DO NORTE", "cabecalho"))
    e.append(P("DEPARTAMENTO DE ENGENHARIA DE COMPUTAÇÃO E AUTOMAÇÃO",
               "cabecalho"))
    e.append(Spacer(1, 14))
    e.append(P("Tarefa 17: Tipos Derivados em MPI", "titulo"))
    e.append(P("Produto matriz-vetor com a matriz distribuída por colunas",
               "subtitulo"))
    e.append(P("Professor: Samuel Xavier de Souza<br/>"
               "Aluno: Vinícius Silva do Carmo<br/>"
               "Setembro de 2026", "autoria"))

    e.append(P("1. Objetivo", "h"))
    e.append(P(
        "Reimplementar a tarefa 16 (y = A·x), agora distribuindo as colunas "
        "de A entre os processos. Usar " + C("MPI_Type_vector") + " e " +
        C("MPI_Type_create_resized") + " para definir um tipo derivado que "
        "represente colunas da matriz, " + C("MPI_Scatter") + " com esse tipo "
        "para distribuir blocos de colunas e " + C("MPI_Scatter") + " para "
        "enviar os segmentos correspondentes de x. Cada processo calcula uma "
        "contribuição parcial para todos os elementos de y, e " +
        C("MPI_Reduce") + " com " + C("MPI_SUM") + " soma os vetores parciais "
        "no processo 0. Discutir as diferenças de acesso à memória e de "
        "desempenho em relação à distribuição por linhas."))

    e.append(P("2. Ambiente de Execução", "h"))
    e.append(tabela([
        ["Item", "Valor"],
        ["Máquina", "Supercomputador NPAD/UFRN, partição amd-512"],
        ["Nó", "r2n16 — 64 núcleos físicos reservados, de 1 a 64 processos no mesmo nó"],
        ["Processador", "2 × AMD EPYC 7713 (Milan)"],
        ["MPI", "OpenMPI 5.0.10 (" + C("libraries/openmpi/5.0.10-gnu14-ucxmt") + ")"],
        ["Compilador", "GCC 14.2.0 via " + C("mpicc -O2")],
        ["Job", "SLURM 2135226"],
    ], [3.3 * cm, 12.7 * cm]))
    e.append(P(
        "O job não usou o nó com exclusividade (a fila para o nó inteiro "
        "estava em dias); por isso foi até 64 processos, e outros jobs podiam "
        "estar rodando nos demais núcleos. A versão por linhas da tarefa 16 "
        "rodou no mesmo job, para a comparação ser feita no mesmo nó."))

    e.append(P("3. Implementação", "h"))
    e.append(P(
        "A matriz continua armazenada por linhas no processo 0 (A[i][j] = "
        "i + j, x com todos os valores iguais a 1). Uma coluna é um tipo "
        "derivado: " + C("MPI_Type_vector(M, 1, N, MPI_DOUBLE)") + " descreve "
        "M blocos de 1 elemento separados por N elementos. O extent desse "
        "tipo vai do primeiro ao último elemento da coluna, então a " +
        C("MPI_Type_create_resized") + " o reduz para 1 " + C("double") +
        ": assim, a coluna seguinte começa no elemento seguinte, e o " +
        C("MPI_Scatter") + " com contagem N/P entrega N/P colunas "
        "consecutivas a cada processo (N deve ser múltiplo de P)."))
    e.append(P(
        "Cada processo recebe as suas colunas como M·N/P " + C("double") +
        "s contíguos, uma coluna após a outra, e o segmento correspondente "
        "de x (N/P valores) por outro " + C("MPI_Scatter") + ". O cálculo "
        "percorre as colunas locais somando a[·][j]·x[j] num vetor parcial de "
        "tamanho M, e o " + C("MPI_Reduce") + " com " + C("MPI_SUM") +
        " soma esses vetores no processo 0, que confere cada y[i] com o valor "
        "exato N·i + N(N−1)/2; todas as execuções deram 0 erros."))
    e.append(P(
        "O processo 0 mede com " + C("MPI_Wtime") + " a <b>distribuição</b> "
        "(os dois " + C("MPI_Scatter") + "), o <b>cálculo</b> e a "
        "<b>coleta</b> (" + C("MPI_Reduce") + "); na versão por linhas, "
        "distribuição é " + C("MPI_Scatter") + " + " + C("MPI_Bcast") +
        " e coleta é " + C("MPI_Gather") + ". Foram usadas matrizes quadradas "
        "de 1024, 4096 e 16384 com 1, 2, 4, …, 64 processos, 3 repetições de "
        "cada caso, ficando a de menor tempo total."))

    for i, n in enumerate(ns):
        tab = [["Proc.", "Total col.", "Total lin.", "Distrib. col.", "Distrib. lin.",
                "Cálculo col.", "Cálculo lin.", "Coleta col.", "Coleta lin."]]
        for p in ps:
            tab.append([str(p)] + [ms(T(v, n, p, c)) for c in
                                   ("tempo_total_s", "distribuicao_s", "calculo_s", "coleta_s")
                                   for v in ("colunas", "linhas")])
        e.append(KeepTogether([P("4. Resultados", "h"),
                               P("Tempos em ms; “col.” é a distribuição por "
                                 "colunas (esta tarefa) e “lin.” a por linhas "
                                 "(tarefa 16).")] * (i == 0) + [
            P(f"<b>Matriz {n} × {n}</b>", "p"),
            tabela(tab, [1.2 * cm] + [1.85 * cm] * 8),
            Spacer(1, 8)]))
    e.append(figura(DIR / "img" / "tempos.png",
                    "Figura 1 — Tempo total, distribuição, cálculo e coleta em "
                    "função do número de processos. Linhas cheias: distribuição "
                    "por colunas; tracejadas: por linhas."))

    e.append(P("5. Análise", "h"))
    e.append(P(
        "<b>Distribuir colunas de uma matriz armazenada por linhas é muito "
        "mais caro.</b> Na matriz de " f"{g}×{g} ({num(g * g * 8 / 2**30, 0)} GB), o " +
        C("MPI_Scatter") + " por colunas leva " +
        num(T("colunas", g, 1, "distribuicao_s") / 1e3, 1) + " s com 1 "
        "processo, contra " + ms(T("linhas", g, 1, "distribuicao_s")) + " ms "
        "por linhas (" + num(razao(g, 1), 0) + "× mais lento), e com " f"{pm} "
        "processos a diferença chega a " + num(razao(g, pm), 0) + "×. Na de " +
        f"{ns[1]}×{ns[1]}" " a razão fica entre " +
        num(min(razao(ns[1], p) for p in ps), 0) + " e " +
        num(max(razao(ns[1], p) for p in ps), 0) + "×, e na de " +
        f"{ns[0]}×{ns[0]}" " entre " + num(min(razao(ns[0], p) for p in ps), 0) +
        " e " + num(max(razao(ns[0], p) for p in ps), 0) + "×. A distribuição "
        "passa a ser praticamente todo o tempo, e o tempo total não cai com "
        "mais processos."))
    e.append(P(
        "<b>O motivo é o acesso à memória.</b> Por linhas, o bloco de cada "
        "processo é um trecho contíguo de A e o " + C("MPI_Scatter") + " é "
        "uma cópia sequencial, que aproveita cada linha de cache inteira. Por "
        "colunas, os elementos de uma coluna estão separados por N " +
        C("double") + "s (" + num(g * 8 / 1024, 0) + " KB na maior matriz): o "
        "MPI empacota elemento por elemento, e cada leitura cai numa linha de "
        "cache (e, na maior matriz, numa página de memória) diferente, da "
        "qual só 8 dos 64 bytes são usados naquele momento. O tipo derivado "
        "evita escrever esse laço no programa, mas o laço continua existindo "
        "dentro do MPI. Na maior matriz, isso dá uns " +
        num(MB / T("colunas", g, 1, "distribuicao_s") * 1e3, 0) + " MB/s de "
        "empacotamento, contra uns " +
        num(MB / T("linhas", g, 1, "distribuicao_s"), 1) + " GB/s da "
        "cópia contígua. Além disso, o empacotamento é feito pelo processo 0 "
        "para todos os destinos, por isso não fica mais rápido com mais "
        "processos (por linhas, as cópias contíguas acontecem em paralelo), "
        "e com " f"{pm}" " processos ainda piorou."))
    e.append(P(
        "<b>O cálculo local ficou até mais rápido.</b> Como cada processo "
        "recebe as colunas já contíguas, o laço percorre a memória em ordem "
        "nas duas versões, e o tempo de cálculo é praticamente o mesmo a "
        "partir de 8 processos. Com poucos processos, a versão por colunas "
        "chega a ser " + num(T("linhas", g, 1, "calculo_s") /
                             T("colunas", g, 1, "calculo_s"), 1) +
        "× mais rápida: ela atualiza y[i] += a·x[j] com iterações "
        "independentes, que o compilador consegue vetorizar, enquanto o "
        "produto escalar da versão por linhas acumula tudo numa única soma, "
        "que sem " + C("-ffast-math") + " não pode ser reordenada."))
    e.append(P(
        "<b>Troca de x inteiro por y inteiro.</b> Por colunas, cada processo "
        "recebe só N/P valores de x, mas guarda um y parcial de M valores, e "
        "o " + C("MPI_Reduce") + " combina P vetores de tamanho M, enquanto o " +
        C("MPI_Gather") + " junta só M valores no total. Mesmo assim a coleta "
        "fica em poucos milissegundos (" + ms(T("colunas", g, pm, "coleta_s")) +
        " ms contra " + ms(T("linhas", g, pm, "coleta_s")) + " ms na maior "
        "matriz com " f"{pm}" " processos) e é irrelevante perto da "
        "distribuição."))

    e.append(P("6. Conclusão", "h"))
    e.append(P(
        "Com " + C("MPI_Type_vector") + " e " + C("MPI_Type_create_resized") +
        " foi possível distribuir colunas com um único " + C("MPI_Scatter") +
        ", como se fossem blocos contíguos, e o " + C("MPI_Reduce") + " com " +
        C("MPI_SUM") + " montou o resultado correto. O desempenho, porém, é "
        "muito pior que o da distribuição por linhas: a matriz está "
        "armazenada por linhas, e ler colunas dela é um acesso espaçado, que "
        "desperdiça a cache e é feito só pelo processo 0. O cálculo e a "
        "coleta são parecidos nas duas versões; o que decide é a distribuição. "
        "A divisão por colunas só compensaria se a matriz já estivesse "
        "armazenada por colunas, ou se cada processo gerasse as suas próprias "
        "colunas."))

    code = DIR / "img" / "code.png"
    if code.exists():
        e.append(PageBreak())
        e.append(P("7. Código-Fonte", "h"))
        e.append(figura(code, "Figura 2 — " + C("mxv.c") + ".",
                        largura=12.5 * cm))
    return e


def main():
    doc = SimpleDocTemplate(str(SAIDA), pagesize=A4,
                            leftMargin=2.5 * cm, rightMargin=2.5 * cm,
                            topMargin=2.0 * cm, bottomMargin=2.0 * cm,
                            title="Tarefa 17 - Tipos Derivados em MPI",
                            author="Vinícius Silva do Carmo")
    doc.build(conteudo(), canvasmaker=NumeradoCanvas)
    print(f"gerado: {SAIDA.name}")


if __name__ == "__main__":
    main()
