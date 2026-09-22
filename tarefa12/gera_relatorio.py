#!/usr/bin/env python3
"""Gera o relatório da Tarefa 12 em PDF, no mesmo formato das tarefas anteriores.

Uso: python3 gera_relatorio.py
Saída: Tarefa12_Desempenho_Escalabilidade.pdf
"""

import os
import tempfile
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas
from reportlab.platypus import (BaseDocTemplate, Frame, Image, KeepTogether,
                                PageBreak,
                                PageTemplate, Paragraph, Spacer, Table,
                                TableStyle)

DIR = Path(__file__).parent
SAIDA = DIR / "Tarefa12_Desempenho_Escalabilidade.pdf"

AZUL = colors.HexColor("#1f3864")
CINZA = colors.HexColor("#f2f2f2")
BORDA = colors.HexColor("#b0b0b0")

# ── Estilos ──────────────────────────────────────────────────────────────
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
    "h3": ParagraphStyle("h3", parent=ss["Heading3"], fontSize=10.5,
                         leading=13, spaceBefore=8, spaceAfter=3,
                         textColor=colors.HexColor("#333333")),
    "p": ParagraphStyle("p", parent=ss["Normal"], fontSize=9.7, leading=13.4,
                        alignment=TA_JUSTIFY, spaceAfter=6),
    "leg": ParagraphStyle("leg", parent=ss["Normal"], fontSize=8.5,
                          leading=11, alignment=TA_CENTER, spaceBefore=3,
                          spaceAfter=10,
                          textColor=colors.HexColor("#555555")),
    "cel": ParagraphStyle("cel", parent=ss["Normal"], fontSize=8.6, leading=11),
}


def P(txt, estilo="p"):
    return Paragraph(txt, S[estilo])


def tabela(dados, larguras, destaque_col0=True):
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
    ]
    for i in range(1, len(corpo)):
        if i % 2 == 0:
            estilo.append(("BACKGROUND", (0, i), (-1, i), CINZA))
    if destaque_col0:
        estilo.append(("FONTNAME", (0, 1), (0, -1), "Helvetica-Bold"))
    t.setStyle(TableStyle(estilo))
    return t


def fatias_codigo(arquivo, n=3):
    """Corta a captura do código em n pedaços que caibam na altura da página.

    A imagem tem proporção de cerca de 1:4,4 — a 15,5 cm de largura daria
    68 cm de altura. O corte não pode cair em qualquer linha: procura-se a
    linha horizontal com menos pixels de texto perto de cada divisão, que é o
    vão entre duas linhas de código, para não partir nenhuma ao meio.

    As fatias são temporárias; a fonte da verdade continua sendo o .png.
    """
    import numpy as np
    from PIL import Image as PILImage

    origem = DIR / "img" / arquivo
    im = PILImage.open(origem).convert("RGB")
    a = np.asarray(im, dtype=int)
    altura, largura_px, _ = a.shape

    fundo = np.array([18, 19, 20])          # cor de fundo do editor
    margem = 40                             # ignora bordas da janela
    conteudo_por_linha = (
        np.abs(a - fundo).sum(axis=2) > 30
    )[:, margem:largura_px - margem].sum(axis=1)

    cortes = [0]
    for k in range(1, n):
        alvo = altura * k // n
        janela = np.arange(max(0, alvo - 60), min(altura, alvo + 60))
        cortes.append(int(janela[np.argmin(conteudo_por_linha[janela])]))
    cortes.append(altura)

    destino = Path(tempfile.mkdtemp(prefix="codigo_"))
    caminhos = []
    for i in range(n):
        pedaco = im.crop((0, cortes[i], largura_px, cortes[i + 1]))
        p = destino / f"parte{i + 1}.png"
        pedaco.save(p)
        caminhos.append(str(p))
    return caminhos


def figura(arquivo, legenda, largura=15.5 * cm):
    """Figura ajustada à largura do texto, com a proporção preservada.

    As dimensões vão no construtor: atribuir drawWidth/drawHeight depois não
    redimensiona nada, e a imagem sai no tamanho natural (aqui, 37 cm de
    largura) transbordando a página.
    """
    caminho = arquivo if os.path.isabs(arquivo) else str(DIR / "img" / arquivo)
    px_w, px_h = ImageReader(caminho).getSize()
    img = Image(caminho, width=largura, height=largura * px_h / px_w)
    img.hAlign = "CENTER"
    # KeepTogether mantém a legenda na mesma página da figura
    return [KeepTogether([img, P(legenda, "leg")])]


class NumeradoCanvas(canvas.Canvas):
    """Rodapé "Página X de N", como nos relatórios anteriores.

    O total só é conhecido depois de paginar tudo, então as páginas ficam
    guardadas e são escritas no final, quando N já existe.
    """

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


# ── Conteúdo ─────────────────────────────────────────────────────────────
def conteudo():
    e = []

    e.append(P("UNIVERSIDADE FEDERAL DO RIO GRANDE DO NORTE", "cabecalho"))
    e.append(P("DEPARTAMENTO DE ENGENHARIA DE COMPUTAÇÃO E AUTOMAÇÃO",
               "cabecalho"))
    e.append(Spacer(1, 14))
    e.append(P("Tarefa 12: Desempenho vs. Escalabilidade", "titulo"))
    e.append(P("Avaliação de escalabilidade de Navier-Stokes com OpenMP "
               "no supercomputador do NPAD", "subtitulo"))
    e.append(P("Professor: Samuel Xavier de Souza<br/>"
               "Aluno: Vinícius Silva do Carmo<br/>"
               "Setembro de 2026", "autoria"))

    # 1 ─────────────────────────────────────────────────────────────────
    e.append(P("1. Objetivo", "h"))
    e.append(P(
        "Avaliar a escalabilidade do código de Navier-Stokes em um nó de "
        "computação do NPAD, identificar os gargalos de escalabilidade e "
        "reportar o progresso em versões sucessivas do código otimizado, "
        "comentando a escalabilidade, a escalabilidade fraca e a "
        "escalabilidade forte de cada versão."))
    e.append(P(
        "O núcleo numérico é o da Tarefa 11 — difusão viscosa "
        "&part;u/&part;t = &nu;&nabla;&sup2;u, resolvida por um stencil de 5 "
        "pontos com Euler explícito e r = &nu;&middot;&Delta;t/&Delta;x&sup2; "
        "= 0,01 &lt;&lt; 0,25 —, agora com a grade dimensionada em tempo de "
        "execução, pré-requisito para medir escalabilidade fraca."))

    # 2 ─────────────────────────────────────────────────────────────────
    e.append(P("2. Ambiente de Execução", "h"))
    e.append(tabela([
        ["Item", "Valor"],
        ["Máquina", "Supercomputador NPAD/UFRN, partição amd-512, nó exclusivo"],
        ["Processador", "2 × AMD EPYC 7713 (Milan), 64 núcleos por socket"],
        ["Núcleos físicos", "128 (SMT desativado via <font face='Courier'>--hint=compute_bound</font>)"],
        ["Domínios NUMA", "8 (16 núcleos cada)"],
        ["Memória", "512 GB DDR4-3200, 8 canais por socket (~409 GB/s de pico)"],
        ["Cache L3", "32 MB por CCD; 512 MB agregados no nó"],
        ["Compilador", "GCC 14.2.0, <font face='Courier'>-O3 -march=native -fopenmp</font>"],
        ["Afinidade", "<font face='Courier'>OMP_PLACES=cores</font>, <font face='Courier'>OMP_PROC_BIND=spread</font>"],
    ], [3.3 * cm, 12.2 * cm]))
    e.append(Spacer(1, 6))
    e.append(P(
        "A reserva exclusiva do nó não é detalhe de conforto: medir "
        "escalabilidade em nó compartilhado mistura o comportamento do código "
        "com a disputa de banda de memória de outros jobs — e a banda é "
        "justamente a grandeza sob investigação."))

    # 3 ─────────────────────────────────────────────────────────────────
    e.append(P("3. Versões do Código", "h"))
    e.append(P(
        "Cinco versões do mesmo cálculo, cada uma removendo um gargalo da "
        "anterior. Todas estão em um único arquivo, selecionadas por argumento "
        "de linha de comando."))
    e.append(tabela([
        ["Versão", "O que muda", "Gargalo removido"],
        ["v0", "Referência sequencial de 1 thread", "—"],
        ["v1", "<font face='Courier'>omp parallel for</font> + <font face='Courier'>memcpy</font> do grid a cada passo", "— (versão ingênua)"],
        ["v2", "Troca de ponteiros no lugar da cópia", "Trecho serial (Amdahl)"],
        ["v3", "Inicialização paralela com a mesma partição do cálculo", "Localidade NUMA"],
        ["v4", "Um só <font face='Courier'>omp parallel</font> em torno do laço do tempo", "Fork/join por passo"],
    ], [1.6 * cm, 8.4 * cm, 5.5 * cm], destaque_col0=True))

    # 4 ─────────────────────────────────────────────────────────────────
    e.append(P("4. Validação", "h"))
    e.append(P(
        "Otimização que muda o resultado não é otimização. As cinco versões "
        "foram executadas sobre a mesma condição inicial e o campo final "
        "comparado por checksum, com 128 threads:"))
    e.append(tabela([
        ["Versão", "Checksum &Sigma;u", "Pico", "Resultado"],
        ["v0-sequencial", "1,570796326795e+03", "8,630114", "(referência)"],
        ["v1-memcpy", "1,570796326795e+03", "8,630114", "idêntico"],
        ["v2-doublebuf", "1,570796326795e+03", "8,630114", "idêntico"],
        ["v3-firsttouch", "1,570796326795e+03", "8,630114", "idêntico"],
        ["v4-regiao-unica", "1,570796326795e+03", "8,630114", "idêntico"],
    ], [3.6 * cm, 5.2 * cm, 2.4 * cm, 4.3 * cm]))
    e.append(Spacer(1, 6))
    e.append(P(
        "Os checksums coincidem <b>bit a bit</b>, o que era esperado: o stencil "
        "é determinístico por célula e não há redução em ponto flutuante, "
        "então a ordem das threads não altera o resultado. A massa medida "
        "(1,570796e+03) coincide com a integral analítica da gaussiana "
        "2&pi;&sigma;&#8320;&sup2;A, confirmando que a física permanece correta "
        "com 128 threads."))

    # 5 ─────────────────────────────────────────────────────────────────
    e.append(P("5. Escalabilidade Forte", "h"))
    e.append(P(
        "Grade fixa de 4096 × 4096 (134 MB por grid), 100 passos, mediana de 3 "
        "execuções. Referência sequencial: <b>1,171 s</b>."))
    e.append(tabela([
        ["Threads", "v1 (speedup)", "v2", "v3", "v4", "Ideal"],
        ["1", "0,6×", "1,0×", "1,0×", "1,0×", "1×"],
        ["2", "0,7×", "1,7×", "2,1×", "2,2×", "2×"],
        ["4", "0,7×", "3,0×", "4,4×", "4,3×", "4×"],
        ["8", "0,7×", "8,1×", "10,1×", "11,3×", "8×"],
        ["16", "0,6×", "16,8×", "22,4×", "23,4×", "16×"],
        ["32", "0,8×", "25,6×", "43,0×", "47,0×", "32×"],
        ["64", "0,5×", "27,2×", "52,0×", "78,3×", "64×"],
        ["128", "0,2×", "24,9×", "52,3×", "<b>106,9×</b>", "128×"],
    ], [1.9 * cm, 2.9 * cm, 2.4 * cm, 2.4 * cm, 2.6 * cm, 2.2 * cm]))
    e.append(Spacer(1, 8))
    e.extend(figura("escalabilidade_forte.png",
                    "Figura 1 — Speedup com problema fixo. A v1 nunca supera "
                    "1×; cada versão seguinte desloca o joelho da curva para a "
                    "direita."))

    # 6 ─────────────────────────────────────────────────────────────────
    e.append(P("6. Escalabilidade Fraca", "h"))
    e.append(P(
        "Trabalho por thread constante: 2048&sup2; células por thread, ou seja "
        "n = 2048&middot;&radic;p. 50 passos, mediana de 3 execuções. O ideal "
        "é tempo constante, isto é, eficiência de 100%."))
    e.append(tabela([
        ["Threads", "Grade", "v1", "v2", "v3", "v4", "MLUPS (v4)"],
        ["1", "2048²", "100%", "100%", "100%", "100%", "1709"],
        ["2", "2896²", "36%", "76%", "91%", "87%", "2979"],
        ["4", "4096²", "24%", "60%", "81%", "93%", "6352"],
        ["8", "5793²", "12%", "41%", "69%", "76%", "10460"],
        ["16", "8192²", "5%", "24%", "63%", "65%", "17689"],
        ["32", "11585²", "4%", "14%", "29%", "30%", "16437"],
        ["64", "16384²", "2%", "6%", "12%", "12%", "13557"],
        ["128", "23170²", "1%", "6%", "6%", "<b>6%</b>", "<b>13294</b>"],
    ], [1.8 * cm, 2.3 * cm, 1.8 * cm, 1.8 * cm, 1.8 * cm, 1.8 * cm, 2.6 * cm]))
    e.append(Spacer(1, 8))
    e.extend(figura("escalabilidade_fraca.png",
                    "Figura 2 — Eficiência fraca. A queda comum a todas as "
                    "versões a partir de 32 threads é o teto de banda de "
                    "memória do nó, não um defeito do código."))

    # 7 ─────────────────────────────────────────────────────────────────
    e.append(P("7. Análise dos Gargalos", "h"))

    e.append(P("7.1 Trecho serial — Amdahl (v1 &rarr; v2)", "h3"))
    e.append(P(
        "A v1 calcula o grid novo em paralelo e copia tudo de volta com "
        "<font face='Courier'>memcpy</font>. Essa cópia move a mesma "
        "quantidade de bytes que o próprio stencil: cerca de metade do "
        "trabalho ficou serial, e por Amdahl o speedup satura em 2×. A "
        "medição é pior que a previsão — a v1 <b>nunca ultrapassa 0,8×</b> e "
        "com 128 threads chega a 5,0 s contra 1,17 s da sequencial. Amdahl "
        "supõe overhead zero; aqui, abrir e fechar um time de 128 threads a "
        "cada passo custa mais do que o paralelismo rende. Um trecho serial "
        "não apenas limita o ganho: em escala suficiente, ele o inverte. A "
        "correção não otimiza a cópia, elimina-a — trocam-se dois ponteiros."))

    e.append(P("7.2 Localidade NUMA — first touch (v2 &rarr; v3)", "h3"))
    e.append(P(
        "A v2 escala até 16 threads e então empaca. No Linux a página física é "
        "escolhida no primeiro acesso e nasce no domínio NUMA da thread que a "
        "tocou; alocar e zerar em serial coloca os 268 MB em um dos 8 domínios "
        "do nó. Quando o time se espalha pelos dois sockets, 7/8 dos acessos "
        "viram tráfego remoto e um único controlador de memória vira o gargalo "
        "da máquina inteira. A v3 não muda uma linha do stencil: apenas "
        "inicializa em paralelo com a mesma partição <font face='Courier'>"
        "static</font> do laço de cálculo, de modo que a thread que atualiza a "
        "linha i seja a que instancia suas páginas. Com 128 threads isso "
        "<b>dobra</b> o resultado: 24,9× &rarr; 52,3×."))

    e.append(P("7.3 Fork/join por passo (v3 &rarr; v4)", "h3"))
    e.append(P(
        "A v3 satura em ~52×. A v4 abre uma única região paralela em torno de "
        "todo o laço do tempo, com cada thread deduzindo os buffers pela "
        "paridade do passo e a barreira implícita do <font face='Courier'>"
        "omp for</font> como único ponto de sincronização. A diferença de "
        "tempo por passo entre v3 e v4 isola o custo do fork/join:"))
    e.append(tabela([
        ["Threads", "16", "32", "64", "128"],
        ["(T<sub>v3</sub> − T<sub>v4</sub>) por passo", "21 µs", "23 µs",
         "76 µs", "<b>114 µs</b>"],
    ], [6.0 * cm, 2.3 * cm, 2.3 * cm, 2.3 * cm, 2.6 * cm],
        destaque_col0=True))
    e.append(Spacer(1, 6))
    e.append(P(
        "O custo <b>cresce com o número de threads</b>, como se espera de uma "
        "operação que acorda e recolhe p threads. Com 128 threads o passo da "
        "v3 leva 224 µs e o da v4, 110 µs: metade do tempo da v3 era "
        "fork/join, não cálculo. Daí o salto de 52,3× para 106,9×. É o gargalo "
        "mais insidioso dos três, porque seu peso é absoluto por passo e não "
        "proporcional ao trabalho — invisível num grid grande, dominante num "
        "pequeno."))

    e.append(P("7.4 Eficiência acima de 100%", "h3"))
    e.append(P(
        "As tabelas mostram eficiência de até 147%, o que parece impossível. A "
        "explicação não é mérito do paralelismo: o conjunto de trabalho da "
        "escalabilidade forte são 268 MB, e enquanto uma thread sozinha "
        "enxerga os 32 MB de L3 do seu CCD, 128 threads espalhadas enxergam os "
        "512 MB agregados do nó — o problema inteiro passa a caber em cache. O "
        "speedup superlinear mede a transição de DRAM para cache. Esse é o "
        "enunciado em estado puro: a v4 tem <b>desempenho</b> excelente nesse "
        "ponto, mas a <b>eficiência</b> está contaminada por uma mudança de "
        "regime de memória que não se repetiria num problema maior."))

    e.append(P("7.5 O teto restante — banda de memória", "h3"))
    e.append(P(
        "A escalabilidade fraca revela o limite real. A vazão cresce quase "
        "linearmente até 16 threads e então estabiliza em ~13300 MLUPS, "
        "aproximadamente 210 GB/s — cerca de metade do pico teórico do nó, "
        "valor típico para acesso de streaming. Um único núcleo já entrega "
        "~1700 MLUPS. <b>A razão é 8×, não 128×.</b> Num kernel memory-bound o "
        "recurso que escala é a banda de memória, e ela cresce muito mais "
        "devagar que a contagem de núcleos. Nenhuma otimização de código "
        "atravessa esse teto; só mudaria o algoritmo, com temporal blocking."))

    # 8 ─────────────────────────────────────────────────────────────────
    e.append(P("8. Avaliação com o PaScal Suite", "h"))
    e.append(P(
        "O experimento foi repetido com o <b>PaScal Analyzer</b> (LAPPS/IMD-"
        "UFRN), que varre o produto cartesiano de configurações e grava o JSON "
        "consumido pelo <b>PaScal Viewer</b>. O binário instrumentado usa o "
        "mesmo núcleo numérico, com duas regiões marcadas: região 1 "
        "(inicialização) e região 2 (cálculo)."))
    e.append(P(
        "Os oito tamanhos foram casados às contagens de núcleos "
        "(n = 2048&middot;&radic;p), de modo que cada linha do mapa é uma "
        "escalabilidade forte e a diagonal é exatamente a escalabilidade "
        "fraca. As duas medições concordam: para n = 2048 com 1 núcleo, o "
        "sweep próprio mede 0,1763 s na v1 e o PaScal, 0,1763 s. Dois "
        "instrumentos independentes chegando ao mesmo teto é o que permite "
        "atribuí-lo à máquina, e não ao método."))
    e.append(P(
        "As Figuras 3 a 6 são os diagramas do próprio PaScal Viewer, um por "
        "versão. Em todos, o eixo vertical vai de 2 a 128 núcleos (de cima "
        "para baixo) e o horizontal percorre os oito tamanhos, i1 a i8, em "
        "ordem crescente (2048 a 23170)."))
    e.append(P(
        "A progressão aparece como cor: o painel de eficiência vai de quase "
        "inteiramente amarelo na v1 — eficiência perto de zero em quase todo o "
        "espaço de configurações — a majoritariamente escuro na v3 e na v4. As "
        "duas últimas são quase indistinguíveis entre si, o que confirma o "
        "resultado da diagonal: o ganho da região paralela única aparece "
        "quando o passo de tempo é curto em relação ao custo de fork/join, e "
        "nesses tamanhos de problema a inicialização e o cálculo dominam. Nos "
        "mapas de v3 e v4 a região de alta eficiência fica à esquerda (i1–i4, "
        "os menores n), exatamente onde as tabelas registram os 135–145% de "
        "eficiência superlinear por residência em cache."))
    e.append(Spacer(1, 4))
    e.extend(figura("pascal-viewer-v1.png",
                    "Figura 3 — v1 · memcpy serial. O painel de eficiência "
                    "(superior esquerdo) é quase todo amarelo: fora da faixa "
                    "de 2 núcleos, praticamente nada do recurso vira trabalho.",
                    largura=14.0 * cm))
    e.extend(figura("pascal-viewer-v2.png",
                    "Figura 4 — v2 · double buffering. Removido o trecho "
                    "serial, a faixa escura desce até cerca de 16 núcleos e "
                    "então se dissolve.",
                    largura=14.0 * cm))
    e.extend(figura("pascal-viewer-v3.png",
                    "Figura 5 — v3 · first touch NUMA. A região escura se "
                    "estende por boa parte do mapa; o degrau vertical por "
                    "volta de i4–i5 marca onde o problema deixa de caber no "
                    "cache agregado.",
                    largura=14.0 * cm))
    e.extend(figura("pascal-viewer-v4.png",
                    "Figura 6 — v4 · região paralela única. Praticamente "
                    "idêntica à v3 na visão do programa inteiro, onde o custo "
                    "de fork/join é pequeno diante da inicialização.",
                    largura=14.0 * cm))

    e.append(P("8.1 O que só as regiões mostram", "h3"))
    e.append(P(
        "Separar inicialização de cálculo revelou o efeito mais direto de todo "
        "o trabalho. Tempo da região 1 com o maior problema (n = 23170&sup2;):"))
    e.append(tabela([
        ["Threads", "v1", "v2", "v3", "v4"],
        ["1", "13,73 s", "13,72 s", "14,14 s", "14,15 s"],
        ["8", "13,72 s", "13,72 s", "1,82 s", "1,83 s"],
        ["32", "13,73 s", "13,73 s", "0,48 s", "0,48 s"],
        ["128", "13,72 s", "13,73 s", "<b>0,19 s</b>", "<b>0,19 s</b>"],
    ], [2.4 * cm, 3.2 * cm, 3.2 * cm, 3.2 * cm, 3.2 * cm]))
    e.append(Spacer(1, 6))
    e.append(P(
        "A inicialização de v1 e v2 custa 13,7 s <b>em qualquer número de "
        "núcleos</b> — é serial por construção, e é exatamente ali que todas "
        "as páginas nascem em um único domínio NUMA. Em v3/v4 ela cai de "
        "14,15 s para 0,19 s (74×). Isso responde a uma objeção que as tabelas "
        "de tempo de cálculo sozinhas não respondem: o ganho da v3 foi real ou "
        "apenas empurrado para fora da região medida? Foi real — a região 1 "
        "não engordou, encolheu 74×."))
    e.append(P(
        "Vale notar que os diagramas do Viewer medem o <i>programa inteiro</i>, "
        "incluindo a região 1, e por isso são mais severos com v1 e v2 do que "
        "as tabelas das seções 5 e 6, restritas ao cálculo. Não é conflito, é "
        "escopo: o recorte do cálculo isola o efeito de cada otimização no "
        "laço; o do programa inteiro diz quanto disso o usuário final recebe."))

    # 9 ─────────────────────────────────────────────────────────────────
    e.append(P("9. Conclusão", "h"))
    e.append(P(
        "Aplicando as definições do material à melhor versão (v4):"))
    e.append(tabela([
        ["Pergunta", "Resposta"],
        ["É escalável?",
         "<b>Sim.</b> A perda de eficiência causada pelo aumento de recursos é "
         "compensada pelo aumento do problema: de 1 para 128 threads a vazão "
         "sustentada sobe de 1,7 para 13,3 GLUPS."],
        ["É fracamente escalável?",
         "<b>Não</b> — e nenhum código deste tipo poderia ser neste hardware. "
         "Exigiria que a banda de memória crescesse proporcionalmente aos "
         "núcleos; no EPYC 7713 ela cresce ~8× enquanto os núcleos crescem "
         "128×. O limite é arquitetural, não de implementação."],
        ["É fortemente escalável?",
         "<b>Na faixa medida, sim</b>: 106,9× com 128 threads (84% de "
         "eficiência) sem aumentar o problema. Com a ressalva da seção 7.4 — "
         "parte do resultado vem de a grade passar a caber no L3 agregado."],
    ], [4.2 * cm, 11.3 * cm]))
    e.append(Spacer(1, 8))
    # KeepTogether evita o subtítulo órfão no rodapé de uma página com a
    # tabela na seguinte.
    e.append(KeepTogether([P("Progressão em uma linha:", "h3"), tabela([
        ["Versão", "Speedup em 128 threads", "Gargalo removido"],
        ["v1 · memcpy serial", "0,2×", "—"],
        ["v2 · double buffering", "24,9×", "Trecho serial (Amdahl)"],
        ["v3 · first touch NUMA", "52,3×", "Localidade de memória"],
        ["v4 · região única", "<b>106,9×</b>", "Fork/join por passo"],
        ["teto restante", "—", "Banda de memória (exigiria mudar o algoritmo)"],
    ], [4.6 * cm, 4.2 * cm, 6.7 * cm])]))
    e.append(Spacer(1, 8))
    e.append(P(
        "A lição que atravessa as quatro versões é a do enunciado: "
        "<b>desempenho e escalabilidade são grandezas diferentes</b>. A v1 com "
        "128 threads tem péssimo desempenho e péssima escalabilidade. A v4 na "
        "escalabilidade forte tem ótimo desempenho e ótima eficiência aparente "
        "— mas a escalabilidade fraca revela que boa parte disso era o "
        "problema ter encolhido para dentro do cache. Só medir os dois regimes "
        "distingue um código que escala de um código que apenas ficou rápido."))

    # 10 ────────────────────────────────────────────────────────────────
    e.append(PageBreak())
    e.append(P("10. Código-Fonte", "h"))
    e.append(P(
        "O arquivo <font face='Courier'>stencil.h</font> reproduzido a seguir "
        "concentra todo o desenvolvimento discutido neste relatório: os "
        "parâmetros físicos, as duas estratégias de alocação que distinguem a "
        "v2 da v3, o stencil de 5 pontos e as cinco funções "
        "<font face='Courier'>roda_v0</font> … <font face='Courier'>roda_v4</font>, "
        "onde se acompanha o <font face='Courier'>memcpy</font> desaparecer na "
        "v2 e a região paralela subir para fora do laço do tempo na v4."))
    e.append(P(
        "Ficam de fora apenas os dois arquivos de infraestrutura de medição — "
        "<font face='Courier'>fluid_scale.c</font>, com os modos de validação e "
        "de benchmark, e <font face='Courier'>pascal_fluid.c</font>, com as "
        "marcações do PaScal —, que não contêm lógica do cálculo."))
    partes = fatias_codigo("code.png", 4)
    for i, caminho in enumerate(partes, start=1):
        e.append(PageBreak() if i > 1 else Spacer(1, 4))
        e.extend(figura(
            caminho,
            f"Figura {6 + i} — <font face='Courier'>stencil.h</font>, "
            f"parte {i} de {len(partes)}.",
            largura=15.5 * cm))

    return e


def main():
    doc = BaseDocTemplate(str(SAIDA), pagesize=A4,
                          leftMargin=2.5 * cm, rightMargin=2.5 * cm,
                          topMargin=2.0 * cm, bottomMargin=2.0 * cm,
                          title="Tarefa 12 - Desempenho vs. Escalabilidade",
                          author="Vinícius Silva do Carmo")
    quadro = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height,
                   id="normal")
    doc.addPageTemplates([PageTemplate(id="pag", frames=[quadro])])
    doc.build(conteudo(), canvasmaker=NumeradoCanvas)
    print(f"gerado: {SAIDA.name}")


if __name__ == "__main__":
    main()
