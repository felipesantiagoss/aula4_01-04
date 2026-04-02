from __future__ import annotations

from dataclasses import dataclass
from typing import BinaryIO, List, Tuple


@dataclass(frozen=True)
class HeaderPPM:
    tipo: bytes
    largura: int
    altura: int
    valor_maximo: int
    offset_dados: int

    @property
    def bytes_por_linha(self) -> int:
        return self.largura * 3

    @property
    def total_bytes_pixels(self) -> int:
        return self.bytes_por_linha * self.altura


def ler_header_ppm(arquivo: BinaryIO) -> HeaderPPM:
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

    return HeaderPPM(
        tipo=tipo,
        largura=largura,
        altura=altura,
        valor_maximo=valor_maximo,
        offset_dados=arquivo.tell(),
    )


def criar_header_ppm(largura: int, altura: int, valor_maximo: int = 255) -> bytes:
    return f"P6\n{largura} {altura}\n{valor_maximo}\n".encode("ascii")


def particionar_linhas(altura: int, partes: int) -> List[Tuple[int, int]]:
    if partes <= 0:
        raise ValueError("O número de partes deve ser maior que zero.")

    partes = min(partes, altura)
    base = altura // partes
    resto = altura % partes

    fatias: List[Tuple[int, int]] = []
    inicio = 0
    for indice in range(partes):
        extra = 1 if indice < resto else 0
        fim = inicio + base + extra
        fatias.append((inicio, fim))
        inicio = fim

    return fatias


def formatar_tamanho(total_bytes: int) -> str:
    unidades = ["B", "KiB", "MiB", "GiB", "TiB"]
    valor = float(total_bytes)
    for unidade in unidades:
        if valor < 1024 or unidade == unidades[-1]:
            return f"{valor:.2f} {unidade}"
        valor /= 1024
    return f"{valor:.2f} TiB"

