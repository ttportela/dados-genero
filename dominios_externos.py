#!/usr/bin/env python3
"""
Imprime os domínios únicos dos links externos de uma cidade.

Uso:
    python dominios_externos.py <cidade>
    python dominios_externos.py abatia
"""

import sys
from pathlib import Path
from urllib.parse import urlparse

import pandas as pd


def main():
    if len(sys.argv) < 2:
        print("Uso: python dominios_externos.py <cidade>")
        sys.exit(1)

    cidade = sys.argv[1].lower()
    caminho = Path("resultados") / cidade / "inventario_externos.xlsx"

    if not caminho.exists():
        print(f"Arquivo não encontrado: {caminho}")
        sys.exit(1)

    df = pd.read_excel(caminho)

    if df.empty:
        print("Nenhum link externo registrado.")
        return

    if "dominio_encontrado" not in df.columns:
        print("Coluna 'dominio_encontrado' não encontrada no arquivo.")
        return

    dominios = df["dominio_encontrado"].dropna().value_counts()

    print(f"\nDomínios externos únicos — {cidade.upper()}")
    print(f"Total de links externos: {len(df)}")
    print(f"Domínios únicos: {len(dominios)}\n")
    print(f"{'Domínio':<50} {'Links':>6}")
    print("-" * 58)
    for dominio, qtd in dominios.items():
        print(f"{dominio:<50} {qtd:>6}")

    # Busca possíveis portais da transparência entre os links externos
    print(f"\n{'='*70}")
    print("Possíveis portais da transparência")
    print(f"{'='*70}\n")

    palavras_chave = ["transparencia", "transparencia-publica", "portaltransparencia",
                      "portal-da-transparencia", "transparencia.gov", "open-data",
                      "dadosabertos", "dados-abertos", "licitacoes", "transp"]

    if "url_encontrada" not in df.columns:
        print("  Coluna 'url_encontrada' não encontrada no arquivo.")
        return

    candidatos = df[df["url_encontrada"].str.lower().str.contains(
        "|".join(palavras_chave), case=False, na=False
    )]["url_encontrada"].dropna().unique()

    if len(candidatos) == 0:
        print("  Nenhum link com palavras-chave de transparência encontrado.")
        return

    # Conjunto de URLs já registradas no inventário_externos
    urls_inventario = set(df["url_encontrada"].dropna().str.rstrip("/").str.lower())

    # Deduplica por domínio: mantém apenas a URL mais curta de cada domínio
    por_dominio: dict[str, str] = {}
    for url in candidatos:
        dominio = urlparse(url).netloc
        if dominio not in por_dominio or len(url) < len(por_dominio[dominio]):
            por_dominio[dominio] = url

    print(f"{'Domínio':<45} {'URL mais curta'}")
    print("-" * 70)
    for dominio in sorted(por_dominio):
        url_curta = por_dominio[dominio]
        no_inventario = url_curta.rstrip("/").lower() in urls_inventario
        marcador = " ★" if no_inventario else "  "
        print(f"{marcador}{dominio:<43} {url_curta}")

    print(f"\n  ★ = URL já presente no inventario_externos da cidade")
    print(f"  Total: {len(por_dominio)} domínio(s) único(s)")


if __name__ == "__main__":
    main()
