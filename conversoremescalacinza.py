import argparse
import time

import numpy as np


def ler_header_ppm(f):
    tipo = f.readline().strip()
    if tipo != b'P6':
        raise ValueError("Formato não suportado. Esperado PPM P6.")

    linha = f.readline().strip()
    while linha.startswith(b'#'):
        linha = f.readline().strip()

    largura, altura = map(int, linha.split())

    linha = f.readline().strip()
    while linha.startswith(b'#'):
        linha = f.readline().strip()

    valor_maximo = int(linha)
    if valor_maximo != 255:
        raise ValueError("Somente PPM com max=255 suportado.")

    offset_dados = f.tell()
    return largura, altura, valor_maximo, offset_dados


def converter_para_cinza_serial(
    arquivo_entrada,
    arquivo_saida,
    linhas_por_bloco=256
):
    with open(arquivo_entrada, "rb") as fin:
        largura, altura, valor_maximo, offset_dados = ler_header_ppm(fin)

        print(f"Imagem: {largura}x{altura}")
        print("Iniciando processamento SERIAL...")

        inicio_total = time.time()

        with open(arquivo_saida, "wb") as fout:
            header = f"P6\n{largura} {altura}\n{valor_maximo}\n".encode("ascii")
            fout.write(header)

            fin.seek(offset_dados)

            for y in range(0, altura, linhas_por_bloco):
                bloco_altura = min(linhas_por_bloco, altura - y)
                quantidade_bytes = bloco_altura * largura * 3

                dados = fin.read(quantidade_bytes)
                if len(dados) != quantidade_bytes:
                    raise IOError("Erro ao ler dados.")

                bloco = np.frombuffer(dados, dtype=np.uint8)
                bloco = bloco.reshape((bloco_altura, largura, 3))

                cinza = (
                    0.299 * bloco[:, :, 0] +
                    0.587 * bloco[:, :, 1] +
                    0.114 * bloco[:, :, 2]
                ).astype(np.uint8)

                bloco_cinza = np.stack((cinza, cinza, cinza), axis=2)
                fout.write(bloco_cinza.tobytes())

                progresso = ((y + bloco_altura) / altura) * 100
                print(f"Progresso: {progresso:6.2f}%")

        fim_total = time.time()
        tempo_total = fim_total - inicio_total

        print("\n✅ Processamento concluído!")
        print(f"⏱️ Tempo total: {tempo_total:.2f} segundos")
        print(f"⏱️ Tempo total: {tempo_total/60:.2f} minutos")

        return tempo_total


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Converter imagem para escala de cinza")

    parser.add_argument("arquivo_entrada", help="Caminho do arquivo de entrada")
    parser.add_argument("arquivo_saida", help="Caminho do arquivo de saída")

    args = parser.parse_args()

    converter_para_cinza_serial(
        arquivo_entrada=args.arquivo_entrada,
        arquivo_saida=args.arquivo_saida,
        linhas_por_bloco=256
    )

