import argparse

import numpy as np

from ppm_utils import formatar_tamanho


def gerar_imagem_ppm(
    caminho_saida="imagem_entrada.ppm",
    largura=75672,
    altura=75672,
    linhas_por_bloco=256,
    seed=42
):
    rng = np.random.default_rng(seed)

    header = f"P6\n{largura} {altura}\n255\n".encode("ascii")
    total_bytes_pixels = largura * altura * 3
    total_bytes_estimado = len(header) + total_bytes_pixels

    print(f"Gerando arquivo: {caminho_saida}")
    print(f"Dimensões: {largura} x {altura}")
    print(f"Tamanho estimado: {formatar_tamanho(total_bytes_estimado)}")

    with open(caminho_saida, "wb") as arquivo_saida:
        arquivo_saida.write(header)

        for y in range(0, altura, linhas_por_bloco):
            bloco_altura = min(linhas_por_bloco, altura - y)
            bloco = rng.integers(
                0,
                256,
                size=(bloco_altura, largura, 3),
                dtype=np.uint8,
            )

            arquivo_saida.write(bloco.tobytes())

            progresso = (y + bloco_altura) / altura * 100
            print(f"Progresso: {progresso:6.2f}%")

    print("Concluído com sucesso!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Gerar uma imagem PPM aleatória.")
    parser.add_argument(
        "--saida",
        default="imagem_entrada.ppm",
        help="Arquivo PPM de saída.",
    )
    parser.add_argument(
        "--largura",
        type=int,
        default=75672,
        help="Largura da imagem. O padrão gera aproximadamente 16 GiB.",
    )
    parser.add_argument(
        "--altura",
        type=int,
        default=75672,
        help="Altura da imagem. O padrão gera aproximadamente 16 GiB.",
    )
    parser.add_argument(
        "--linhas-por-bloco",
        type=int,
        default=256,
        help="Quantidade de linhas escritas por iteração.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Seed do gerador pseudoaleatório.",
    )

    argumentos = parser.parse_args()

    gerar_imagem_ppm(
        caminho_saida=argumentos.saida,
        largura=argumentos.largura,
        altura=argumentos.altura,
        linhas_por_bloco=argumentos.linhas_por_bloco,
        seed=argumentos.seed,
    )

