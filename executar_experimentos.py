from __future__ import annotations

import argparse
import csv
import json
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from statistics import mean
from typing import List

from comparar_arquivos import calcular_hash_arquivo, comparar_arquivos
from gerar_relatorio_modelo import gerar_relatorio_modelo
from ppm_utils import HeaderPPM, formatar_tamanho, ler_header_ppm


def extrair_tempo_reportado(stdout: str) -> float | None:
    correspondencias = re.findall(r"Tempo total:\s*([0-9]+(?:\.[0-9]+)?)\s+segundos", stdout)
    if not correspondencias:
        return None
    return float(correspondencias[-1])


def executar_comando(comando: List[str], descricao: str, repeticoes: int) -> dict:
    print(f"\nExecutando: {descricao}")
    print(" ".join(comando))

    tempos = []
    for indice in range(1, repeticoes + 1):
        if repeticoes > 1:
            print(f"\nRepetição {indice}/{repeticoes}")

        inicio = time.perf_counter()
        resultado = subprocess.run(comando, capture_output=True, text=True)
        duracao = time.perf_counter() - inicio

        if resultado.stdout:
            print(resultado.stdout)

        if resultado.returncode != 0:
            raise RuntimeError(
                f"Falha em '{descricao}'.\nSTDOUT:\n{resultado.stdout}\nSTDERR:\n{resultado.stderr}"
            )

        tempos.append(extrair_tempo_reportado(resultado.stdout) or duracao)

    tempo_medio = mean(tempos)
    print(f"Tempo médio de {descricao}: {tempo_medio:.4f} s")
    return {
        "tempo_segundos": tempo_medio,
        "tempos_execucoes": tempos,
    }


def carregar_header(caminho: Path) -> HeaderPPM:
    with open(caminho, "rb") as arquivo:
        return ler_header_ppm(arquivo)


def salvar_resultados(base_dir: Path, resultados: dict) -> None:
    json_path = base_dir / "resultados.json"
    csv_path = base_dir / "resultados.csv"
    md_path = base_dir / "resultados.md"

    json_path.write_text(
        json.dumps(resultados, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    with open(csv_path, "w", newline="", encoding="utf-8") as arquivo_csv:
        writer = csv.DictWriter(
            arquivo_csv,
            fieldnames=[
                "modo",
                "threads",
                "tempo_segundos",
                "speedup",
                "eficiencia",
                "arquivo_saida",
                "validado",
            ],
            extrasaction="ignore",
        )
        writer.writeheader()
        writer.writerow(
            {
                "modo": "serial",
                "threads": 1,
                "tempo_segundos": resultados["serial"]["tempo_segundos"],
                "speedup": 1.0,
                "eficiencia": 1.0,
                "arquivo_saida": resultados["serial"]["arquivo_saida"],
                "validado": True,
                "tempos_execucoes": resultados["serial"].get("tempos_execucoes", []),
            }
        )
        for execucao in resultados["paralelo"]:
            writer.writerow(execucao)

    linhas = [
        "# Resultados do Experimento",
        "",
        f"- Data: {resultados['metadata']['data_execucao']}",
        f"- Arquivo de entrada: `{resultados['metadata']['arquivo_entrada']}`",
        f"- Dimensões: `{resultados['metadata']['largura']} x {resultados['metadata']['altura']}`",
        f"- Tamanho estimado: `{resultados['metadata']['tamanho_estimado']}`",
        "",
        "| Modo | Threads | Tempo (s) | Speedup | Eficiência | Saída |",
        "| --- | ---: | ---: | ---: | ---: | --- |",
        (
            f"| Serial | 1 | {resultados['serial']['tempo_segundos']:.4f} | "
            f"1.0000 | 1.0000 | `{resultados['serial']['arquivo_saida']}` |"
        ),
    ]

    for execucao in resultados["paralelo"]:
        linhas.append(
            f"| Paralelo | {execucao['threads']} | {execucao['tempo_segundos']:.4f} | "
            f"{execucao['speedup']:.4f} | {execucao['eficiencia']:.4f} | "
            f"`{execucao['arquivo_saida']}` |"
        )

    md_path.write_text("\n".join(linhas) + "\n", encoding="utf-8")


def remover_arquivo(caminho: Path) -> None:
    if caminho.exists():
        caminho.unlink()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Executar benchmark serial e paralelo.")
    parser.add_argument("arquivo_entrada", help="Imagem PPM de entrada.")
    parser.add_argument(
        "--threads",
        nargs="+",
        type=int,
        default=[2, 4, 8, 12],
        help="Lista de threads externas a serem testadas.",
    )
    parser.add_argument(
        "--python",
        dest="python_exec",
        default=sys.executable,
        help="Interpretador Python usado para chamar os scripts.",
    )
    parser.add_argument(
        "--conversor",
        default="conversoremescalacinza.py",
        help="Script serial original.",
    )
    parser.add_argument(
        "--paralelo",
        default="paralelizador_externo.py",
        help="Script que orquestra a execução paralela.",
    )
    parser.add_argument(
        "--output-dir",
        default="resultados",
        help="Diretório que receberá relatórios e saídas.",
    )
    parser.add_argument(
        "--limpar-saidas",
        action="store_true",
        help="Remove as imagens geradas após validar os resultados.",
    )
    parser.add_argument(
        "--nao-validar",
        action="store_true",
        help="Não compara a saída paralela com a saída serial.",
    )
    parser.add_argument(
        "--repeticoes",
        type=int,
        default=1,
        help="Quantidade de execuções por configuração para cálculo da média.",
    )
    parser.add_argument(
        "--fatias",
        type=int,
        default=None,
        help="Quantidade total de fatias usada na versão paralela.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    argumentos = parse_args()

    entrada = Path(argumentos.arquivo_entrada).resolve()
    output_dir = Path(argumentos.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    uso_disco = shutil.disk_usage(output_dir)

    header = carregar_header(entrada)
    serial_saida = output_dir / "imagem_serial.ppm"

    resultado_serial = executar_comando(
        [argumentos.python_exec, argumentos.conversor, str(entrada), str(serial_saida)],
        "Conversão serial",
        argumentos.repeticoes,
    )
    hash_serial = calcular_hash_arquivo(serial_saida)
    if argumentos.limpar_saidas:
        remover_arquivo(serial_saida)

    resultados_paralelos = []
    for threads in argumentos.threads:
        arquivo_saida = output_dir / f"imagem_paralela_{threads}.ppm"
        resultado_paralelo = executar_comando(
            [
                argumentos.python_exec,
                argumentos.paralelo,
                str(entrada),
                str(arquivo_saida),
                "--threads",
                str(threads),
                "--fatias",
                str(argumentos.fatias or threads),
                "--python",
                argumentos.python_exec,
                "--conversor",
                argumentos.conversor,
            ],
            f"Conversão paralela com {threads} threads",
            argumentos.repeticoes,
        )

        validado = True
        if not argumentos.nao_validar:
            if serial_saida.exists():
                validado = comparar_arquivos(serial_saida, arquivo_saida)
            else:
                validado = calcular_hash_arquivo(arquivo_saida) == hash_serial
            if not validado:
                raise RuntimeError(
                    f"A saída paralela com {threads} threads difere da saída serial."
                )

        tempo_paralelo = resultado_paralelo["tempo_segundos"]
        speedup = resultado_serial["tempo_segundos"] / tempo_paralelo if tempo_paralelo else 0.0
        eficiencia = speedup / threads if threads else 0.0

        resultados_paralelos.append(
            {
                "modo": "paralelo",
                "threads": threads,
                "tempo_segundos": tempo_paralelo,
                "tempos_execucoes": resultado_paralelo["tempos_execucoes"],
                "speedup": speedup,
                "eficiencia": eficiencia,
                "arquivo_saida": str(arquivo_saida),
                "validado": validado,
            }
        )

        if argumentos.limpar_saidas:
            remover_arquivo(arquivo_saida)

    resultados = {
        "metadata": {
            "data_execucao": datetime.now().isoformat(timespec="seconds"),
            "arquivo_entrada": str(entrada),
            "largura": header.largura,
            "altura": header.altura,
            "tamanho_estimado": formatar_tamanho(header.offset_dados + header.total_bytes_pixels),
            "tamanho_real_arquivo_entrada": formatar_tamanho(entrada.stat().st_size),
            "espaco_livre_antes_execucao": formatar_tamanho(uso_disco.free),
            "cenario_oficial_16gb": header.largura == 75672 and header.altura == 75672,
            "repeticoes": argumentos.repeticoes,
            "fatias": argumentos.fatias or None,
            "hash_serial_sha256": hash_serial,
        },
        "serial": {
            "arquivo_saida": str(serial_saida),
            "tempo_segundos": resultado_serial["tempo_segundos"],
            "tempos_execucoes": resultado_serial["tempos_execucoes"],
        },
        "paralelo": resultados_paralelos,
    }

    salvar_resultados(output_dir, resultados)
    arquivo_relatorio = gerar_relatorio_modelo(
        resultados=resultados,
        relatorio_dir=Path("relatorio").resolve(),
        origem_resultados=output_dir / "resultados.json",
    )

    if argumentos.limpar_saidas and serial_saida.exists():
        remover_arquivo(serial_saida)

    print("\nBenchmark finalizado com sucesso.")
    print(f"Resultados salvos em: {output_dir}")
    print(f"Relatório atualizado em: {arquivo_relatorio}")
