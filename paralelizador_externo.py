from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Tuple

from ppm_utils import criar_header_ppm, formatar_tamanho, ler_header_ppm, particionar_linhas


def preparar_arquivo_saida(caminho_saida: Path, largura: int, altura: int, valor_maximo: int) -> None:
    header = criar_header_ppm(largura, altura, valor_maximo)
    tamanho_total = len(header) + largura * altura * 3

    with open(caminho_saida, "wb") as arquivo_saida:
        arquivo_saida.write(header)
        arquivo_saida.truncate(tamanho_total)


def executar_fatia(
    arquivo_entrada: Path,
    arquivo_saida: Path,
    conversor: Path,
    python_exec: str,
    altura_total: int,
    fatia: Tuple[int, int],
    hook_dir: Path,
) -> dict:
    linha_inicial, linha_final = fatia
    quantidade_linhas = linha_final - linha_inicial

    env = os.environ.copy()
    pythonpath_atual = env.get("PYTHONPATH")
    env["PYTHONPATH"] = (
        str(hook_dir)
        if not pythonpath_atual
        else f"{hook_dir}{os.pathsep}{pythonpath_atual}"
    )
    env["PPM_SLICE_ENABLED"] = "1"
    env["PPM_SLICE_INPUT_PATH"] = str(arquivo_entrada.resolve())
    env["PPM_SLICE_OUTPUT_PATH"] = str(arquivo_saida.resolve())
    env["PPM_SLICE_START_ROW"] = str(linha_inicial)
    env["PPM_SLICE_ROW_COUNT"] = str(quantidade_linhas)
    env["PPM_SLICE_FULL_HEIGHT"] = str(altura_total)

    inicio = time.perf_counter()
    resultado = subprocess.run(
        [python_exec, str(conversor), str(arquivo_entrada), str(arquivo_saida)],
        capture_output=True,
        text=True,
        env=env,
    )
    duracao = time.perf_counter() - inicio

    if resultado.returncode != 0:
        raise RuntimeError(
            "Falha ao processar a fatia "
            f"{linha_inicial}:{linha_final}\n"
            f"STDOUT:\n{resultado.stdout}\n"
            f"STDERR:\n{resultado.stderr}"
        )

    return {
        "linha_inicial": linha_inicial,
        "linha_final": linha_final,
        "duracao": duracao,
        "stdout": resultado.stdout,
    }


def converter_para_cinza_paralelo(
    arquivo_entrada: str,
    arquivo_saida: str,
    threads: int,
    fatias: int | None = None,
    conversor: str | None = None,
    python_exec: str | None = None,
) -> float:
    if threads <= 0:
        raise ValueError("O número de threads deve ser maior que zero.")

    caminho_entrada = Path(arquivo_entrada).resolve()
    caminho_saida = Path(arquivo_saida).resolve()
    caminho_conversor = (
        Path(conversor).resolve()
        if conversor
        else Path(__file__).resolve().with_name("conversoremescalacinza.py")
    )
    python_exec = python_exec or sys.executable
    hook_dir = Path(__file__).resolve().with_name("runtime_hooks")

    with open(caminho_entrada, "rb") as arquivo:
        header = ler_header_ppm(arquivo)

    quantidade_fatias = fatias or threads
    if quantidade_fatias <= 0:
        raise ValueError("O número de fatias deve ser maior que zero.")

    particoes = particionar_linhas(header.altura, quantidade_fatias)
    preparar_arquivo_saida(caminho_saida, header.largura, header.altura, header.valor_maximo)

    print(f"Imagem: {header.largura}x{header.altura}")
    print(f"Entrada: {caminho_entrada}")
    print(f"Saída:   {caminho_saida}")
    print(f"Conversor tratado como caixa-preta: {caminho_conversor}")
    print(f"Workers externos: {threads}")
    print(f"Fatias totais: {len(particoes)}")
    print(f"Tamanho estimado da imagem: {formatar_tamanho(header.offset_dados + header.total_bytes_pixels)}")
    print("Iniciando processamento PARALELO...")

    inicio_total = time.perf_counter()
    concluidas = 0

    with ThreadPoolExecutor(max_workers=threads) as executor:
        futuros = [
            executor.submit(
                executar_fatia,
                caminho_entrada,
                caminho_saida,
                caminho_conversor,
                python_exec,
                header.altura,
                fatia,
                hook_dir,
            )
            for fatia in particoes
        ]

        for futuro in as_completed(futuros):
            resultado = futuro.result()
            concluidas += 1
            progresso = concluidas / len(particoes) * 100
            print(
                "Fatia concluída: "
                f"{resultado['linha_inicial']}:{resultado['linha_final']} "
                f"em {resultado['duracao']:.2f}s "
                f"({progresso:6.2f}% do total)"
            )

    tempo_total = time.perf_counter() - inicio_total

    print("\n✅ Processamento paralelo concluído!")
    print(f"⏱️ Tempo total: {tempo_total:.2f} segundos")
    print(f"⏱️ Tempo total: {tempo_total / 60:.2f} minutos")

    return tempo_total


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Paralelizador externo para o conversor em escala de cinza. "
            "O script original não é modificado."
        )
    )
    parser.add_argument("arquivo_entrada", help="Imagem PPM de entrada.")
    parser.add_argument("arquivo_saida", help="Imagem PPM final em escala de cinza.")
    parser.add_argument(
        "--threads",
        type=int,
        required=True,
        help="Quantidade de workers externos ativos simultaneamente.",
    )
    parser.add_argument(
        "--fatias",
        type=int,
        default=None,
        help="Quantidade total de fatias em que a imagem será particionada.",
    )
    parser.add_argument(
        "--conversor",
        default=None,
        help="Caminho do conversor serial original.",
    )
    parser.add_argument(
        "--python",
        dest="python_exec",
        default=sys.executable,
        help="Interpretador Python usado para executar o conversor original.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    argumentos = parse_args()
    converter_para_cinza_paralelo(
        arquivo_entrada=argumentos.arquivo_entrada,
        arquivo_saida=argumentos.arquivo_saida,
        threads=argumentos.threads,
        fatias=argumentos.fatias,
        conversor=argumentos.conversor,
        python_exec=argumentos.python_exec,
    )
