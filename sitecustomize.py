from __future__ import annotations

import builtins
import os
from pathlib import Path
from typing import BinaryIO


def ler_header_ppm(arquivo: BinaryIO):
    tipo = arquivo.readline().strip()
    if tipo != b"P6":
        raise ValueError("Formato não suportado. Esperado PPM P6.")

    linha = arquivo.readline().strip()
    while linha.startswith(b"#"):
        linha = arquivo.readline().strip()

    largura, altura = map(int, linha.split())

    linha = arquivo.readline().strip()
    while linha.startswith(b"#"):
        linha = arquivo.readline().strip()

    valor_maximo = int(linha)
    if valor_maximo != 255:
        raise ValueError("Somente PPM com max=255 suportado.")

    return largura, altura, valor_maximo, arquivo.tell()


def criar_header_ppm(largura: int, altura: int, valor_maximo: int = 255) -> bytes:
    return f"P6\n{largura} {altura}\n{valor_maximo}\n".encode("ascii")


class VirtualPPMInput:
    def __init__(self, caminho_real: str, linha_inicial: int, quantidade_linhas: int, open_original):
        self._arquivo_real = open_original(caminho_real, "rb")
        largura, altura, valor_maximo, offset_dados = ler_header_ppm(self._arquivo_real)

        if linha_inicial < 0 or quantidade_linhas <= 0:
            raise ValueError("A fatia configurada é inválida.")
        if linha_inicial + quantidade_linhas > altura:
            raise ValueError("A fatia ultrapassa a altura da imagem original.")

        self._largura = largura
        self._altura = altura
        self._valor_maximo = valor_maximo
        self._offset_dados = offset_dados
        self._linha_inicial = linha_inicial
        self._quantidade_linhas = quantidade_linhas
        self._bytes_por_linha = largura * 3
        self._inicio_pixels = offset_dados + linha_inicial * self._bytes_por_linha
        self._total_bytes_pixels = quantidade_linhas * self._bytes_por_linha
        self._header_virtual = criar_header_ppm(largura, quantidade_linhas, valor_maximo)
        self._posicao = 0
        self.closed = False

    def _tamanho_virtual(self) -> int:
        return len(self._header_virtual) + self._total_bytes_pixels

    def tell(self) -> int:
        return self._posicao

    def seek(self, offset: int, whence: int = 0) -> int:
        if whence == 0:
            nova_posicao = offset
        elif whence == 1:
            nova_posicao = self._posicao + offset
        elif whence == 2:
            nova_posicao = self._tamanho_virtual() + offset
        else:
            raise ValueError("whence inválido.")

        if nova_posicao < 0:
            raise ValueError("Posição negativa não é permitida.")

        self._posicao = min(nova_posicao, self._tamanho_virtual())
        return self._posicao

    def readline(self, limite: int = -1) -> bytes:
        if self._posicao >= len(self._header_virtual):
            return b""

        restante_header = self._header_virtual[self._posicao:]
        quebra_linha = restante_header.find(b"\n")
        if quebra_linha == -1:
            quebra_linha = len(restante_header) - 1

        quantidade = quebra_linha + 1
        if limite >= 0:
            quantidade = min(quantidade, limite)

        dados = restante_header[:quantidade]
        self._posicao += len(dados)
        return dados

    def read(self, quantidade: int = -1) -> bytes:
        if quantidade == 0:
            return b""

        tamanho_virtual = self._tamanho_virtual()
        if self._posicao >= tamanho_virtual:
            return b""

        if quantidade < 0:
            quantidade = tamanho_virtual - self._posicao
        else:
            quantidade = min(quantidade, tamanho_virtual - self._posicao)

        partes = []
        if self._posicao < len(self._header_virtual):
            dados_header = self._header_virtual[self._posicao:self._posicao + quantidade]
            partes.append(dados_header)
            self._posicao += len(dados_header)
            quantidade -= len(dados_header)

        if quantidade > 0:
            offset_pixels = self._posicao - len(self._header_virtual)
            self._arquivo_real.seek(self._inicio_pixels + offset_pixels)
            dados_pixels = self._arquivo_real.read(quantidade)
            partes.append(dados_pixels)
            self._posicao += len(dados_pixels)

        return b"".join(partes)

    def close(self) -> None:
        if not self.closed:
            self._arquivo_real.close()
            self.closed = True

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()
        return False


class VirtualPPMOutput:
    def __init__(
        self,
        caminho_final: str,
        largura: int,
        altura_total: int,
        valor_maximo: int,
        linha_inicial: int,
        quantidade_linhas: int,
        open_original,
    ):
        self._arquivo_real = open_original(caminho_final, "r+b")
        self._header_total = criar_header_ppm(largura, altura_total, valor_maximo)
        self._header_fatia = criar_header_ppm(largura, quantidade_linhas, valor_maximo)
        self._consumido_header = 0
        self._bytes_por_linha = largura * 3
        self._offset_pixels = len(self._header_total) + linha_inicial * self._bytes_por_linha
        self._total_bytes_pixels = quantidade_linhas * self._bytes_por_linha
        self._escritos_pixels = 0
        self.closed = False

    def write(self, dados: bytes) -> int:
        total_recebido = len(dados)
        restante = dados

        if self._consumido_header < len(self._header_fatia):
            faltando_header = len(self._header_fatia) - self._consumido_header
            parte_header = restante[:faltando_header]
            esperado = self._header_fatia[self._consumido_header:self._consumido_header + len(parte_header)]
            if parte_header != esperado:
                raise ValueError("Cabeçalho da fatia não corresponde ao esperado.")
            self._consumido_header += len(parte_header)
            restante = restante[len(parte_header):]

        if restante:
            if self._escritos_pixels + len(restante) > self._total_bytes_pixels:
                raise ValueError("A escrita excedeu o tamanho esperado da fatia.")

            self._arquivo_real.seek(self._offset_pixels + self._escritos_pixels)
            self._arquivo_real.write(restante)
            self._escritos_pixels += len(restante)

        return total_recebido

    def flush(self) -> None:
        self._arquivo_real.flush()

    def close(self) -> None:
        if not self.closed:
            self._arquivo_real.flush()
            self._arquivo_real.close()
            self.closed = True

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()
        return False


def ativar_slice_virtual():
    if os.environ.get("PPM_SLICE_ENABLED") != "1":
        return

    caminho_input = Path(os.environ["PPM_SLICE_INPUT_PATH"]).resolve()
    caminho_output = Path(os.environ["PPM_SLICE_OUTPUT_PATH"]).resolve()
    linha_inicial = int(os.environ["PPM_SLICE_START_ROW"])
    quantidade_linhas = int(os.environ["PPM_SLICE_ROW_COUNT"])
    altura_total = int(os.environ["PPM_SLICE_FULL_HEIGHT"])

    open_original = builtins.open

    with open_original(caminho_input, "rb") as arquivo:
        largura, altura_real, valor_maximo, _ = ler_header_ppm(arquivo)

    if altura_real != altura_total:
        raise ValueError("Altura total divergente entre o ambiente e a imagem.")

    def open_interceptado(arquivo, modo="r", *args, **kwargs):
        caminho_resolvido = Path(arquivo).resolve()

        if caminho_resolvido == caminho_input and modo == "rb":
            return VirtualPPMInput(
                caminho_real=str(caminho_input),
                linha_inicial=linha_inicial,
                quantidade_linhas=quantidade_linhas,
                open_original=open_original,
            )

        if caminho_resolvido == caminho_output and modo == "wb":
            return VirtualPPMOutput(
                caminho_final=str(caminho_output),
                largura=largura,
                altura_total=altura_total,
                valor_maximo=valor_maximo,
                linha_inicial=linha_inicial,
                quantidade_linhas=quantidade_linhas,
                open_original=open_original,
            )

        return open_original(arquivo, modo, *args, **kwargs)

    builtins.open = open_interceptado


ativar_slice_virtual()

