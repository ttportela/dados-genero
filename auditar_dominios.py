#!/usr/bin/env python3
"""
Auditoria de domínios — verifica quantos links em cada inventário
pertencem aos domínios permitidos da cidade e quantos não pertencem.

Uso:
    python auditar_dominios.py <cidade>
    python auditar_dominios.py araruna
    python auditar_dominios.py --todas

Lê:
  - cidades.json (domínios permitidos)
  - resultados/{cidade}/checkpoint_visited.json  (links processados pelo crawler)
  - resultados/{cidade}/inventario_links.xlsx    (arquivos encontrados)

Para cada fonte, classifica cada URL usando is_valid_domain() (a versão
corrigida que respeita limites de rótulo de domínio) e imprime um resumo.
"""

import sys
import json
from pathlib import Path
from urllib.parse import urlparse

import pandas as pd

DIR_RAIZ = Path(__file__).parent
ARQUIVO_CIDADES = DIR_RAIZ / "cidades.json"
DIR_RESULTADOS = DIR_RAIZ / "resultados"


def is_valid_domain(netloc: str, dominios: list[str]) -> bool:
    """
    Verifica se o netloc pertence a um dos domínios válidos.
    Usa correspondência exata ou subdomínio (prefixo com ponto).
    """
    netloc = netloc.lower()
    return any(
        netloc == d.lower() or netloc.endswith("." + d.lower())
        for d in dominios
    )


def carregar_dominios(cidade: str) -> list[str]:
    with open(ARQUIVO_CIDADES, encoding="utf-8") as f:
        dados = json.load(f)
    if cidade not in dados:
        raise ValueError(f"Cidade '{cidade}' não encontrada em cidades.json")
    return dados[cidade]["dominios"]


def _classificar_urls(urls: list[str], dominios: list[str]) -> tuple[int, int, dict[str, int]]:
    """Classifica uma lista de URLs em válidas/inválidas por domínio."""
    validos = 0
    invalidos = 0
    dominios_invalidos: dict[str, int] = {}

    for url in urls:
        try:
            netloc = urlparse(str(url)).netloc.lower()
        except Exception:
            netloc = ""

        if is_valid_domain(netloc, dominios):
            validos += 1
        else:
            invalidos += 1
            dominios_invalidos[netloc] = dominios_invalidos.get(netloc, 0) + 1

    return validos, invalidos, dominios_invalidos


def _imprimir_resumo(label: str, total: int, validos: int, invalidos: int, dominios_invalidos: dict[str, int]):
    if total == 0:
        print(f"  [{label}] Arquivo vazio (0 registros).")
        print()
        return

    print(f"  [{label}] Total: {total}")
    print(f"  [{label}] Domínios válidos:   {validos} ({validos / total * 100:.1f}%)")
    print(f"  [{label}] Domínios inválidos: {invalidos} ({invalidos / total * 100:.1f}%)")

    if invalidos > 0:
        print(f"  [{label}] Top 10 domínios inválidos:")
        for dom, count in sorted(dominios_invalidos.items(), key=lambda x: -x[1])[:10]:
            print(f"    {count:>6}  {dom}")

    print()


def auditar_xlsx(caminho: Path, dominios: list[str], label: str):
    if not caminho.exists():
        print(f"  [{label}] Arquivo não encontrado: {caminho.name}")
        print()
        return

    df = pd.read_excel(caminho)
    col_url = "url_encontrada" if "url_encontrada" in df.columns else None
    if col_url is None:
        print(f"  [{label}] Coluna 'url_encontrada' não encontrada.")
        print()
        return

    urls = df[col_url].tolist()
    validos, invalidos, dom_inv = _classificar_urls(urls, dominios)
    _imprimir_resumo(label, len(urls), validos, invalidos, dom_inv)


def auditar_json(caminho: Path, dominios: list[str], label: str):
    if not caminho.exists():
        print(f"  [{label}] Arquivo não encontrado: {caminho.name}")
        print()
        return

    with open(caminho, encoding="utf-8") as f:
        urls = json.load(f)

    validos, invalidos, dom_inv = _classificar_urls(urls, dominios)
    _imprimir_resumo(label, len(urls), validos, invalidos, dom_inv)


def auditar_cidade(cidade: str):
    print(f"\n{'='*60}")
    print(f"  Auditoria de domínios: {cidade.upper()}")
    print(f"{'='*60}")

    dominios = carregar_dominios(cidade)
    print(f"  Domínios permitidos: {', '.join(dominios)}")
    print()

    dir_cidade = DIR_RESULTADOS / cidade

    auditar_json(
        dir_cidade / "checkpoint_visited.json",
        dominios,
        "Links processados",
    )
    auditar_xlsx(
        dir_cidade / "inventario_links.xlsx",
        dominios,
        "Inventário (arquivos)",
    )


def listar_cidades() -> list[str]:
    with open(ARQUIVO_CIDADES, encoding="utf-8") as f:
        dados = json.load(f)
    return sorted(k for k in dados if not k.startswith("_"))


def main():
    args = sys.argv[1:]
    if not args:
        print("Uso: python auditar_dominios.py <cidade> | --todas")
        sys.exit(1)

    if args[0] == "--todas":
        for cidade in listar_cidades():
            dir_cidade = DIR_RESULTADOS / cidade
            if not dir_cidade.exists():
                continue
            auditar_cidade(cidade)
    else:
        auditar_cidade(args[0])


if __name__ == "__main__":
    main()
