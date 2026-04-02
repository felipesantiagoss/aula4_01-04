from __future__ import annotations

import argparse
import hashlib
from pathlib import Path


def comparar_arquivos(arquivo_a: Path, arquivo_b: Path, tamanho_bloco: int = 1024 * 1024) -> bool:
    if arquivo_a.stat().st_size != arquivo_b.stat().st_size:
        return False

    with open(arquivo_a, "rb") as a, open(arquivo_b, "rb") as b:
        while True:
            bloco_a = a.read(tamanho_bloco)
            bloco_b = b.read(tamanho_bloco)
            if bloco_a != bloco_b:
                return False
            if not bloco_a:
                return True


def calcular_hash_arquivo(arquivo: Path, tamanho_bloco: int = 1024 * 1024) -> str:
    hasher = hashlib.sha256()
    with open(arquivo, "rb") as handle:
        while True:
            bloco = handle.read(tamanho_bloco)
            if not bloco:
                break
            hasher.update(bloco)
    return hasher.hexdigest()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Comparar dois arquivos binários.")
    parser.add_argument("arquivo_a", help="Primeiro arquivo.")
    parser.add_argument("arquivo_b", help="Segundo arquivo.")
    args = parser.parse_args()

    iguais = comparar_arquivos(Path(args.arquivo_a), Path(args.arquivo_b))
    if iguais:
        print("Arquivos idênticos.")
    else:
        print("Arquivos diferentes.")
        raise SystemExit(1)
