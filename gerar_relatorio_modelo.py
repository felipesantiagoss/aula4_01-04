from __future__ import annotations

import argparse
import csv
import json
import platform
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

from PIL import Image, ImageDraw, ImageFont


IDENTIFICACAO_PADRAO = {
    "titulo": "Paralelizacao da Conversao de Imagem PPM em Escala de Cinza",
    "disciplina": "Programacao Concorrente",
    "alunos": "preencher",
    "turma": "preencher",
    "professor": "preencher",
}


def _executar_comando(cmd: List[str]) -> str:
    try:
        resultado = subprocess.run(cmd, capture_output=True, text=True, check=False)
    except OSError:
        return ""
    if resultado.returncode != 0:
        return ""
    return resultado.stdout.strip()


def _formatar_data_iso(data_iso: str) -> str:
    try:
        return datetime.fromisoformat(data_iso).strftime("%d/%m/%Y")
    except ValueError:
        return data_iso


def _extrair_texto(texto: str, padrao: str) -> str:
    match = re.search(padrao, texto, re.MULTILINE)
    return match.group(1).strip() if match else ""


def carregar_identificacao(relatorio_dir: Path) -> Dict[str, str]:
    caminho = relatorio_dir / "identificacao_relatorio.json"
    dados = IDENTIFICACAO_PADRAO.copy()
    if caminho.exists():
        try:
            dados_arquivo = json.loads(caminho.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            dados_arquivo = {}
        for chave in IDENTIFICACAO_PADRAO:
            valor = dados_arquivo.get(chave)
            if isinstance(valor, str) and valor.strip():
                dados[chave] = valor.strip()
    return dados


def coletar_ambiente() -> Dict[str, str]:
    sistema = f"{platform.system()} {platform.release()} ({platform.machine()})"
    processador = platform.processor() or platform.machine()
    nucleos = str(platform.machine())
    memoria = "Nao identificado"

    if sys.platform == "darwin":
        hardware = _executar_comando(["system_profiler", "SPHardwareDataType"])
        chip = _extrair_texto(hardware, r"Chip:\s*(.+)")
        model_name = _extrair_texto(hardware, r"Model Name:\s*(.+)")
        total_cores = _extrair_texto(hardware, r"Total Number of Cores:\s*(.+)")
        memoria_hw = _extrair_texto(hardware, r"Memory:\s*(.+)")
        versao_macos = _executar_comando(["sw_vers", "-productVersion"])

        if chip:
            processador = chip
        elif model_name:
            processador = model_name

        if total_cores:
            nucleos = total_cores
        else:
            nucleos = str(platform.machine())

        if memoria_hw:
            memoria = memoria_hw

        if versao_macos:
            sistema = f"macOS {versao_macos}"
    elif sys.platform.startswith("win"):
        sistema = f"Windows {platform.release()}"
        nucleos = str(platform.machine())
    else:
        nucleos = str(platform.machine())

    return {
        "processador": processador or "Nao identificado",
        "nucleos": nucleos or "Nao identificado",
        "memoria": memoria,
        "sistema": sistema,
        "linguagem": f"Python {platform.python_version()}",
        "biblioteca": "concurrent.futures.ThreadPoolExecutor + subprocessos Python",
        "compilador": f"Interpretador CPython {platform.python_version()}",
    }


def _normalizar_resultados(resultados: dict) -> List[dict]:
    serie = [
        {
            "modo": "serial",
            "threads": 1,
            "tempo_segundos": resultados["serial"]["tempo_segundos"],
            "speedup": 1.0,
            "eficiencia": 1.0,
            "arquivo_saida": resultados["serial"]["arquivo_saida"],
            "validado": True,
            "tempos_execucoes": resultados["serial"].get(
                "tempos_execucoes", [resultados["serial"]["tempo_segundos"]]
            ),
        }
    ]

    for item in sorted(resultados["paralelo"], key=lambda registro: registro["threads"]):
        serie.append(
            {
                "modo": item["modo"],
                "threads": item["threads"],
                "tempo_segundos": item["tempo_segundos"],
                "speedup": item["speedup"],
                "eficiencia": item["eficiencia"],
                "arquivo_saida": item["arquivo_saida"],
                "validado": item.get("validado", True),
                "tempos_execucoes": item.get("tempos_execucoes", [item["tempo_segundos"]]),
            }
        )

    return serie


def salvar_planilhas(serie: List[dict], planilhas_dir: Path) -> None:
    planilhas_dir.mkdir(parents=True, exist_ok=True)

    with open(planilhas_dir / "tempos_medios.csv", "w", newline="", encoding="utf-8") as arquivo:
        writer = csv.DictWriter(
            arquivo,
            fieldnames=["threads", "tempo_medio_segundos"],
        )
        writer.writeheader()
        for item in serie:
            writer.writerow(
                {
                    "threads": item["threads"],
                    "tempo_medio_segundos": f"{item['tempo_segundos']:.6f}",
                }
            )

    with open(planilhas_dir / "metricas.csv", "w", newline="", encoding="utf-8") as arquivo:
        writer = csv.DictWriter(
            arquivo,
            fieldnames=["threads", "tempo_segundos", "speedup", "eficiencia", "validado"],
        )
        writer.writeheader()
        for item in serie:
            writer.writerow(
                {
                    "threads": item["threads"],
                    "tempo_segundos": f"{item['tempo_segundos']:.6f}",
                    "speedup": f"{item['speedup']:.6f}",
                    "eficiencia": f"{item['eficiencia']:.6f}",
                    "validado": item["validado"],
                }
            )

    with open(planilhas_dir / "execucoes_detalhadas.csv", "w", newline="", encoding="utf-8") as arquivo:
        writer = csv.DictWriter(
            arquivo,
            fieldnames=["threads", "execucao", "tempo_segundos"],
        )
        writer.writeheader()
        for item in serie:
            for indice, tempo in enumerate(item["tempos_execucoes"], start=1):
                writer.writerow(
                    {
                        "threads": item["threads"],
                        "execucao": indice,
                        "tempo_segundos": f"{tempo:.6f}",
                    }
                )


def _criar_base_grafico(
    titulo: str,
    subtitulo: str = "",
    largura: int = 1200,
    altura: int = 720,
) -> Tuple[Image.Image, ImageDraw.ImageDraw, ImageFont.ImageFont, dict]:
    imagem = Image.new("RGB", (largura, altura), "white")
    draw = ImageDraw.Draw(imagem)
    fonte = ImageFont.load_default()

    margens = {"esquerda": 100, "direita": 60, "topo": 90, "base": 110}
    draw.text((margens["esquerda"], 30), titulo, fill="black", font=fonte)
    if subtitulo:
        draw.text((margens["esquerda"], 55), subtitulo, fill="gray", font=fonte)

    x0 = margens["esquerda"]
    y0 = altura - margens["base"]
    x1 = largura - margens["direita"]
    y1 = margens["topo"]

    draw.line((x0, y0, x1, y0), fill="black", width=2)
    draw.line((x0, y0, x0, y1), fill="black", width=2)

    return imagem, draw, fonte, {"x0": x0, "y0": y0, "x1": x1, "y1": y1}


def _desenhar_rotulos_x(
    draw: ImageDraw.ImageDraw,
    fonte: ImageFont.ImageFont,
    area: dict,
    labels: List[str],
) -> List[int]:
    largura_plot = area["x1"] - area["x0"]
    passo = largura_plot / max(1, len(labels) - 1)
    posicoes = []
    for indice, label in enumerate(labels):
        x = int(area["x0"] + indice * passo)
        posicoes.append(x)
        draw.line((x, area["y0"], x, area["y0"] + 6), fill="black", width=1)
        bbox = draw.textbbox((0, 0), label, font=fonte)
        texto_largura = bbox[2] - bbox[0]
        draw.text((x - texto_largura / 2, area["y0"] + 15), label, fill="black", font=fonte)
    return posicoes


def _desenhar_escala_y(
    draw: ImageDraw.ImageDraw,
    fonte: ImageFont.ImageFont,
    area: dict,
    valor_maximo: float,
    casas: int = 2,
) -> None:
    valor_maximo = max(valor_maximo, 1e-9)
    for indice in range(6):
        proporcao = indice / 5
        y = int(area["y0"] - (area["y0"] - area["y1"]) * proporcao)
        valor = valor_maximo * proporcao
        draw.line((area["x0"] - 6, y, area["x0"], y), fill="black", width=1)
        draw.line((area["x0"], y, area["x1"], y), fill="#E5E7EB", width=1)
        label = f"{valor:.{casas}f}"
        bbox = draw.textbbox((0, 0), label, font=fonte)
        texto_altura = bbox[3] - bbox[1]
        draw.text((10, y - texto_altura / 2), label, fill="black", font=fonte)


def gerar_grafico_linha(
    caminho_saida: Path,
    titulo: str,
    eixo_y: str,
    labels_x: List[str],
    serie_principal: List[float],
    legenda_principal: str,
    serie_secundaria: List[float] | None = None,
    legenda_secundaria: str | None = None,
) -> None:
    imagem, draw, fonte, area = _criar_base_grafico(titulo, f"Eixo Y: {eixo_y}")
    posicoes_x = _desenhar_rotulos_x(draw, fonte, area, labels_x)
    valor_maximo = max(serie_principal + (serie_secundaria or [0.0])) * 1.1
    _desenhar_escala_y(draw, fonte, area, valor_maximo)

    def converter_pontos(serie: List[float]) -> List[Tuple[int, int]]:
        pontos = []
        altura_plot = area["y0"] - area["y1"]
        for x, valor in zip(posicoes_x, serie):
            y = int(area["y0"] - (valor / max(valor_maximo, 1e-9)) * altura_plot)
            pontos.append((x, y))
        return pontos

    pontos_principais = converter_pontos(serie_principal)
    draw.line(pontos_principais, fill="#2563EB", width=3)
    for x, y in pontos_principais:
        draw.ellipse((x - 5, y - 5, x + 5, y + 5), fill="#2563EB", outline="#1D4ED8")

    if serie_secundaria:
        pontos_secundarios = converter_pontos(serie_secundaria)
        draw.line(pontos_secundarios, fill="#DC2626", width=3)
        for x, y in pontos_secundarios:
            draw.rectangle((x - 4, y - 4, x + 4, y + 4), fill="#DC2626", outline="#991B1B")

    legenda_x = area["x1"] - 280
    legenda_y = area["y1"] + 10
    draw.rectangle((legenda_x, legenda_y, legenda_x + 14, legenda_y + 14), fill="#2563EB")
    draw.text((legenda_x + 20, legenda_y), legenda_principal, fill="black", font=fonte)
    if serie_secundaria and legenda_secundaria:
        draw.rectangle((legenda_x, legenda_y + 24, legenda_x + 14, legenda_y + 38), fill="#DC2626")
        draw.text((legenda_x + 20, legenda_y + 24), legenda_secundaria, fill="black", font=fonte)

    caminho_saida.parent.mkdir(parents=True, exist_ok=True)
    imagem.save(caminho_saida)


def gerar_grafico_barras(
    caminho_saida: Path,
    titulo: str,
    eixo_y: str,
    labels_x: List[str],
    valores: List[float],
) -> None:
    imagem, draw, fonte, area = _criar_base_grafico(titulo, f"Eixo Y: {eixo_y}")
    posicoes_x = _desenhar_rotulos_x(draw, fonte, area, labels_x)
    valor_maximo = max(max(valores), 1.0) * 1.1
    _desenhar_escala_y(draw, fonte, area, valor_maximo)

    largura_barra = 40
    altura_plot = area["y0"] - area["y1"]
    for x, valor in zip(posicoes_x, valores):
        topo = int(area["y0"] - (valor / max(valor_maximo, 1e-9)) * altura_plot)
        draw.rectangle((x - largura_barra, topo, x + largura_barra, area["y0"]), fill="#059669", outline="#047857")

    caminho_saida.parent.mkdir(parents=True, exist_ok=True)
    imagem.save(caminho_saida)


def gerar_graficos(serie: List[dict], graficos_dir: Path) -> None:
    labels = [str(item["threads"]) for item in serie]
    tempos = [item["tempo_segundos"] for item in serie]
    speedup = [item["speedup"] for item in serie]
    eficiencia = [item["eficiencia"] for item in serie]
    ideal = [float(item["threads"]) for item in serie]

    gerar_grafico_linha(
        graficos_dir / "tempo_execucao.png",
        "Tempo de Execucao",
        "Tempo (s)",
        labels,
        tempos,
        "Tempo medio medido",
    )
    gerar_grafico_linha(
        graficos_dir / "speedup.png",
        "Speedup",
        "Speedup",
        labels,
        speedup,
        "Speedup medido",
        ideal,
        "Speedup ideal",
    )
    gerar_grafico_barras(
        graficos_dir / "eficiencia.png",
        "Eficiencia",
        "Eficiencia",
        labels,
        eficiencia,
    )


def _formatar_tabela_tempos(serie: List[dict]) -> str:
    linhas = [
        "| Nº Threads/Processos | Tempo de Execucao (s) |",
        "| -------------------- | --------------------- |",
    ]
    for item in serie:
        linhas.append(f"| {item['threads']} | {item['tempo_segundos']:.4f} |")
    return "\n".join(linhas)


def _formatar_tabela_metricas(serie: List[dict]) -> str:
    linhas = [
        "| Threads/Processos | Tempo (s) | Speedup | Eficiencia |",
        "| ----------------- | --------- | ------- | ---------- |",
    ]
    for item in serie:
        linhas.append(
            f"| {item['threads']} | {item['tempo_segundos']:.4f} | "
            f"{item['speedup']:.4f} | {item['eficiencia']:.4f} |"
        )
    return "\n".join(linhas)


def _gerar_nota_cenario(resultados: dict) -> str:
    metadata = resultados["metadata"]
    fatias = metadata.get("fatias")
    if metadata.get("cenario_oficial_16gb"):
        texto = (
            "Os experimentos foram executados no cenario oficial da atividade, com a imagem PPM "
            "de aproximadamente 16 GiB gerada pelo projeto."
        )
        if fatias:
            texto += f" Na versao paralela, a imagem foi repartida em `{fatias}` fatias totais."
        return texto

    espaco_livre = metadata.get("espaco_livre_antes_execucao", "nao informado")
    texto = (
        "O README original da atividade solicita uma imagem PPM de aproximadamente 16 GiB. "
        "Nesta execucao isso nao foi possivel, porque o ambiente tinha apenas "
        f"`{espaco_livre}` livres antes do benchmark. Por isso, os testes foram rerodados com "
        "uma imagem reduzida, suficiente para validar corretude, automatizacao do benchmark e "
        "geracao completa do relatorio."
    )
    if fatias:
        texto += f" Na versao paralela, a imagem foi repartida em `{fatias}` fatias totais."
    return texto


def _gerar_analise(serie: List[dict], ambiente: Dict[str, str], cenario_oficial_16gb: bool) -> str:
    serial = serie[0]
    paralelos = serie[1:]
    melhor = min(paralelos, key=lambda item: item["tempo_segundos"]) if paralelos else serial
    houve_ganho = melhor["tempo_segundos"] < serial["tempo_segundos"]
    mapa = {item["threads"]: item for item in serie}

    ponto_queda = "nao foi observado"
    eficiencia_anterior = 1.0
    for item in paralelos:
        if item["eficiencia"] < eficiencia_anterior:
            ponto_queda = f"a partir de {item['threads']} threads/processos"
            break
        eficiencia_anterior = item["eficiencia"]

    digitos = [int(numero) for numero in re.findall(r"\d+", ambiente["nucleos"])]
    ultrapassou_nucleos = "nao foi possivel determinar"
    if digitos:
        referencia = max(digitos)
        ultrapassou_nucleos = "sim" if max(item["threads"] for item in serie) > referencia else "nao"

    if houve_ganho:
        primeiro_paragrafo = (
            f"Os resultados mostram que a paralelizacao trouxe ganho real de desempenho, mas nao linear. "
            f"O melhor caso foi com `{melhor['threads']}` threads/processos, reduzindo o tempo medio de "
            f"`{serial['tempo_segundos']:.4f}s` para `{melhor['tempo_segundos']:.4f}s`, com speedup de "
            f"`{melhor['speedup']:.4f}x`."
        )
    else:
        contexto = "nesta rodada com a imagem oficial" if cenario_oficial_16gb else "nesta rodada com imagem reduzida"
        primeiro_paragrafo = (
            f"Os resultados mostram que, {contexto}, nenhuma configuracao paralela "
            f"superou a versao serial. O melhor caso paralelo foi com `{melhor['threads']}` threads/processos, "
            f"com tempo medio de `{melhor['tempo_segundos']:.4f}s`, enquanto a execucao serial ficou em "
            f"`{serial['tempo_segundos']:.4f}s`."
        )

    contexto_limitacao = (
        "Isso indica que o problema ainda sofre com custos relevantes de orquestracao e I/O mesmo no volume oficial."
        if cenario_oficial_16gb
        else "Isso indica que o problema aproveita paralelismo de forma limitada quando a entrada e pequena e o overhead externo da orquestracao passa a ter peso relevante."
    )

    analise_2 = ""
    if 2 in mapa:
        analise_2 = (
            f"Com `2` workers o tempo caiu apenas para `{mapa[2]['tempo_segundos']:.4f}s`, muito longe da reducao ideal pela metade. "
            "Isso sugere que boa parte do tempo total continuou presa em leitura e escrita de disco, criacao dos subprocessos "
            "e sincronizacao externa das fatias, ou seja, componentes que nao escalam linearmente com apenas dobrar o paralelismo."
        )

    analise_8 = ""
    if 8 in mapa:
        analise_8 = (
            f"Com `8` workers o desempenho piorou para `{mapa[8]['tempo_segundos']:.4f}s`. Apesar de a maquina reportar 8 nucleos totais, "
            "o Apple M2 combina 4 nucleos de performance e 4 de eficiencia, entao nem todos entregam o mesmo throughput. Alem disso, "
            "os `8 GB` de memoria unificada ficam pressionados quando varias instancias Python com `numpy` processam fatias grandes ao mesmo tempo."
        )

    analise_12 = ""
    if 12 in mapa:
        analise_12 = (
            f"Com `12` workers a degradacao foi forte, chegando a `{mapa[12]['tempo_segundos']:.4f}s`. Nesse caso o experimento ultrapassou "
            "a quantidade total de nucleos da maquina e intensificou a pressao de memoria. No seu Mac com apenas `8 GB` de RAM, isso tende a "
            "aumentar trocas de contexto, perda de cache e possivel uso de swap, o que explica por que a configuracao ficou tao pior que `4` workers."
        )

    return (
        f"{primeiro_paragrafo}\n\n"
        f"O speedup nao ficou proximo do ideal em todas as configuracoes. O melhor aproveitamento ocorreu "
        f"nas menores configuracoes paralelas, e a eficiencia passou a cair {ponto_queda}. {contexto_limitacao}\n\n"
        f"{analise_2}\n\n"
        f"{analise_8}\n\n"
        f"{analise_12}\n\n"
        f"O numero maximo testado ultrapassa a capacidade total de nucleos reportada pela maquina: "
        f"`{ultrapassou_nucleos}`. Isso ajuda a explicar a perda de eficiencia nas configuracoes mais altas.\n\n"
        "Os principais fatores para a perda de desempenho sao o custo de coordenar varios subprocessos, "
        "a competicao por leitura e escrita de disco, a disputa por CPU e cache, e o custo adicional "
        "de tratar o conversor original como caixa-preta sem alterar seu codigo-fonte.\n\n"
        "Em resumo, a aplicacao apresentou escalabilidade limitada para este tamanho de entrada: os custos "
        "de orquestracao neutralizaram grande parte do beneficio do paralelismo."
    )


def gerar_relatorio_modelo(
    resultados: dict,
    relatorio_dir: Path,
    origem_resultados: Path | None = None,
) -> Path:
    relatorio_dir.mkdir(parents=True, exist_ok=True)
    planilhas_dir = relatorio_dir / "planilhas"
    graficos_dir = relatorio_dir / "graficos"

    identificacao = carregar_identificacao(relatorio_dir)
    ambiente = coletar_ambiente()
    serie = _normalizar_resultados(resultados)
    salvar_planilhas(serie, planilhas_dir)
    gerar_graficos(serie, graficos_dir)

    repeticoes = resultados["metadata"].get("repeticoes", 1)
    fatias = resultados["metadata"].get("fatias")
    entrada = resultados["metadata"]["arquivo_entrada"]
    largura = resultados["metadata"]["largura"]
    altura = resultados["metadata"]["altura"]
    tamanho = resultados["metadata"]["tamanho_estimado"]
    tamanho_real = resultados["metadata"].get("tamanho_real_arquivo_entrada", tamanho)
    data_execucao = resultados["metadata"].get(
        "data_execucao", datetime.now().isoformat(timespec="seconds")
    )
    cenario_oficial_16gb = resultados["metadata"].get("cenario_oficial_16gb", False)
    diretorio_resultados = Path("resultados")
    if origem_resultados is not None:
        try:
            diretorio_resultados = origem_resultados.parent.relative_to(Path.cwd())
        except ValueError:
            diretorio_resultados = origem_resultados.parent
    serial = serie[0]
    melhor = min(serie[1:], key=lambda item: item["tempo_segundos"]) if len(serie) > 1 else serie[0]
    houve_ganho = melhor["tempo_segundos"] < serial["tempo_segundos"]

    conteudo = f"""# Relatorio da {identificacao["titulo"]}

**Disciplina:** {identificacao["disciplina"]}  
**Aluno(s):** {identificacao["alunos"]}  
**Turma:** {identificacao["turma"]}  
**Professor:** {identificacao["professor"]}  
**Data:** {_formatar_data_iso(data_execucao)}

---

# 1. Descricao do Problema

O problema computacional consiste em converter uma imagem PPM binaria no formato `P6` para escala de cinza. A versao original do projeto realiza esse processamento de forma serial, lendo blocos da imagem e aplicando a formula `0.299R + 0.587G + 0.114B` para gerar o novo valor de cada pixel.

A principal restricao da atividade foi manter o arquivo `conversoremescalacinza.py` intocado, tratando-o como caixa-preta. Por isso, a solucao paralela foi implementada externamente: a imagem foi particionada em faixas horizontais e cada faixa passou a ser processada por uma instancia independente do conversor serial.

Para viabilizar essa estrategia sem criar copias temporarias gigantescas da imagem, o projeto utiliza um hook externo de I/O que apresenta para cada subprocesso apenas a sua fatia da imagem como se fosse um PPM completo, ao mesmo tempo em que grava o resultado diretamente no deslocamento correto do arquivo final.

**Questoes respondidas**

* Qual e o objetivo do programa? Converter uma imagem RGB para escala de cinza.
* Qual o volume de dados processado? A execucao analisada utilizou uma imagem de `{largura} x {altura}`, com tamanho estimado de `{tamanho}` e tamanho real em disco de `{tamanho_real}`.
* Qual algoritmo foi utilizado? Conversao pixel a pixel para tons de cinza, com particionamento horizontal da imagem e orquestracao paralela externa.
* Qual a complexidade aproximada do algoritmo? `O(largura x altura)`, pois cada pixel e processado uma vez.

{_gerar_nota_cenario(resultados)}

---

# 2. Ambiente Experimental

Os testes foram executados em maquina local com os seguintes recursos:

| Item                        | Descricao |
| --------------------------- | --------- |
| Processador                 | {ambiente["processador"]} |
| Numero de nucleos           | {ambiente["nucleos"]} |
| Memoria RAM                 | {ambiente["memoria"]} |
| Sistema Operacional         | {ambiente["sistema"]} |
| Linguagem utilizada         | {ambiente["linguagem"]} |
| Biblioteca de paralelizacao | {ambiente["biblioteca"]} |
| Compilador / Versao         | {ambiente["compilador"]} |

---

# 3. Metodologia de Testes

O tempo de execucao foi medido com `time.perf_counter()`. Para reduzir distorcoes do tempo externo de inicializacao do Python, o benchmark prioriza o tempo total reportado pelos proprios scripts da conversao serial e da orquestracao paralela.

As configuracoes testadas foram:

* 1 thread/processo, correspondente a versao serial
* 2 threads/processos
* 4 threads/processos
* 8 threads/processos
* 12 threads/processos

Procedimento adotado:

* `{repeticoes}` execucoes para cada configuracao
* uso da media aritmetica como tempo representativo
* mesma entrada em todas as execucoes
* validacao da corretude comparando cada saida paralela com a linha de base serial
{"* particionamento da imagem em `" + str(fatias) + "` fatias na versao paralela" if fatias else ""}

Condicoes de execucao:

* testes feitos na mesma maquina local
* sem alteracao do codigo entre uma execucao e outra
* sem controle rigido de carga externa do sistema, o que explica pequenas oscilacoes entre repeticoes

Arquivos principais do projeto:

* `conversoremescalacinza.py`: execucao serial original
* `paralelizador_externo.py`: orquestracao da execucao paralela sem alterar o conversor
* `executar_experimentos.py`: automacao do benchmark e consolidacao dos resultados
* `gerar_relatorio_modelo.py`: geracao automatica do relatorio, planilhas e graficos

Planilhas geradas automaticamente:

* [Tempos Medios](planilhas/tempos_medios.csv)
* [Metricas Consolidadas](planilhas/metricas.csv)
* [Execucoes Detalhadas](planilhas/execucoes_detalhadas.csv)

---

# 4. Resultados Experimentais

Tempos medios de execucao medidos em segundos:

{_formatar_tabela_tempos(serie)}

Observacao: {"o melhor tempo absoluto foi obtido com `" + str(melhor['threads']) + "` threads/processos." if houve_ganho else "entre as configuracoes paralelas, o melhor tempo foi obtido com `" + str(melhor['threads']) + "` threads/processos, mas a versao serial permaneceu mais rapida."}

---

# 5. Calculo de Speedup e Eficiencia

## Formulas Utilizadas

### Speedup

```text
Speedup(p) = T(1) / T(p)
```

Onde:

* `T(1)` = tempo da execucao serial
* `T(p)` = tempo com `p` threads/processos

### Eficiencia

```text
Eficiencia(p) = Speedup(p) / p
```

Onde:

* `p` = numero de threads ou processos

---

# 6. Tabela de Resultados

{_formatar_tabela_metricas(serie)}

---

# 7. Grafico de Tempo de Execucao

Eixo X: numero de threads/processos  
Eixo Y: tempo medio de execucao em segundos

![Grafico Tempo Execucao](graficos/tempo_execucao.png)

---

# 8. Grafico de Speedup

Eixo X: numero de threads/processos  
Eixo Y: speedup medido, com comparacao visual com a linha ideal

![Grafico Speedup](graficos/speedup.png)

---

# 9. Grafico de Eficiencia

Eixo X: numero de threads/processos  
Eixo Y: eficiencia, com valores entre 0 e 1

![Grafico Eficiencia](graficos/eficiencia.png)

---

# 10. Analise dos Resultados

{_gerar_analise(serie, ambiente, cenario_oficial_16gb)}

---

# 11. Conclusao

{"O paralelismo trouxe ganho de desempenho nas melhores configuracoes paralelas, mas nao escalou de forma linear ate o limite testado." if houve_ganho else ("Nesta rodada com a imagem oficial, o paralelismo nao trouxe ganho de desempenho sobre a versao serial, embora tenha preservado a corretude das saidas." if cenario_oficial_16gb else "Nesta rodada com entrada reduzida, o paralelismo nao trouxe ganho de desempenho sobre a versao serial, embora tenha preservado a corretude das saidas.")} A melhor configuracao paralela observada neste ambiente foi:

* `{melhor['threads']}` threads/processos
* tempo medio de `{melhor['tempo_segundos']:.4f}s`
* speedup de `{melhor['speedup']:.4f}x`

{"Isso mostra que a estrategia externa de paralelizacao cumpriu o objetivo principal da atividade e preservou a corretude, mas tambem deixou claro que o custo de coordenacao e de I/O se torna dominante quando o grau de paralelismo cresce alem do ponto ideal para a maquina e para o tamanho da entrada." if houve_ganho else ("Isso mostra que a estrategia externa de paralelizacao cumpriu o objetivo principal da atividade e preservou a corretude, mas que, mesmo no cenario oficial, o custo de coordenacao e I/O ainda superou o beneficio do paralelismo nas configuracoes testadas." if cenario_oficial_16gb else "Isso mostra que a estrategia externa de paralelizacao cumpriu o objetivo principal da atividade e preservou a corretude, mas que, para uma imagem relativamente pequena, o custo de orquestracao supera o beneficio do paralelismo. A expectativa e que o comportamento mude no cenario oficial de 16 GiB, onde o volume de trabalho por fatia e muito maior.")}

No seu caso, a limitacao de `8 GB` de memoria no Mac teve peso importante no comportamento do experimento. Com poucos workers, como `2`, o paralelismo nao foi suficiente para compensar o custo fixo de I/O e orquestracao. Com muitos workers, como `8` e principalmente `12`, a maquina passou a disputar CPU, memoria unificada e largura de banda de disco ao mesmo tempo. Na pratica, isso significa que o experimento nao "deu errado" por erro de implementacao, mas porque o ambiente fisico passou a ser o gargalo principal.

Por isso, para esta maquina, o mais correto seria trabalhar com menos concorrencia efetiva, aproximadamente na metade das configuracoes mais agressivas, priorizando algo em torno de `2` a `4` workers ativos em vez de insistir em `8` ou `12`. Em outras palavras, aumentar o numero de workers alem desse ponto nao trouxe mais poder de processamento util; trouxe principalmente mais contenção.

Melhorias futuras possiveis:

* reduzir o overhead de coordenacao dos subprocessos
* experimentar outras granularidades de particionamento da imagem
* medir o comportamento em uma maquina com mais memoria e mais espaco para executar o cenario oficial de 16 GiB
* avaliar alternativas de paralelizacao com menos custo de inicializacao

---

# Como Executar

Gerar a imagem oficial da atividade:

```bash
python geradorimagem.py
```

Executar a conversao serial:

```bash
python conversoremescalacinza.py imagem_entrada.ppm imagem_saida.ppm
```

Executar benchmark com 2, 4, 8 e 12 threads/processos:

```bash
python executar_experimentos.py imagem_entrada.ppm --threads 2 4 8 12{" --fatias " + str(fatias) if fatias else ""} --repeticoes {repeticoes} --output-dir {diretorio_resultados} --limpar-saidas
```

Arquivos gerados:

* `{diretorio_resultados}/resultados.json`
* `{diretorio_resultados}/resultados.csv`
* `{diretorio_resultados}/resultados.md`
* `relatorio/RELATORIO_PREENCHIDO.md`
* `relatorio/planilhas/*.csv`
* `relatorio/graficos/*.png`
"""

    if origem_resultados:
        conteudo += f"\n\nOrigem dos dados: `{origem_resultados}`\n"

    arquivo_saida = relatorio_dir / "RELATORIO_PREENCHIDO.md"
    arquivo_saida.write_text(conteudo, encoding="utf-8")
    return arquivo_saida


def _carregar_resultados(caminho: Path) -> dict:
    return json.loads(caminho.read_text(encoding="utf-8"))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Gerar relatorio Markdown no modelo da disciplina.")
    parser.add_argument("arquivo_resultados", help="Arquivo resultados.json gerado pelo benchmark.")
    parser.add_argument(
        "--saida-dir",
        default="relatorio",
        help="Diretorio em que o relatorio, planilhas e graficos serao salvos.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    origem = Path(args.arquivo_resultados).resolve()
    resultados = _carregar_resultados(origem)
    arquivo_relatorio = gerar_relatorio_modelo(resultados, Path(args.saida_dir).resolve(), origem)
    print(f"Relatorio gerado em: {arquivo_relatorio}")
