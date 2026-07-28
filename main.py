# =============================================================================
# main.py — Orquestrador do Pipeline
# TCC: Mapeamento de Dados Públicos no Paraná — Perspectivas de Gênero
# UTFPR — Adriana Sarturi
# =============================================================================
#
# Este script conecta os 3 módulos em sequência para uma cidade:
#
#   Etapa 1 — Crawler  : navega o site e anota arquivos encontrados
#   Etapa 2 — Downloader: baixa os arquivos
#   Etapa 3 — Analisador: detecta recorte de gênero nos arquivos baixados
#
# Como usar:
#   venv\Scripts\python main.py maringa           → roda as 3 etapas
#   venv\Scripts\python main.py maringa --etapa 1 → só o Crawler
#   venv\Scripts\python main.py maringa --etapa 2 → só o Downloader
#   venv\Scripts\python main.py maringa --etapa 3 → só o Analisador
# =============================================================================

import argparse
import sys

# Força UTF-8 no terminal do Windows — evita UnicodeEncodeError com emojis
# e caracteres especiais nos prints. Necessário pois o Windows usa cp1252 por padrão.
sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

from src.config import CIDADES


def listar_cidades():
    """Lista todas as cidades configuradas em cidades.json."""
    print(f"\n{'='*60}")
    print(f"  Cidades configuradas ({len(CIDADES)} municípios)")
    print(f"{'='*60}")
    for nome, config in CIDADES.items():
        sementes = config.get("sementes", [])
        dominios = config.get("dominios", [])
        url_principal = sementes[0] if sementes else "(sem semente)"
        qtd_dominios = len(dominios)
        print(f"  {nome:<40} {url_principal}")
    print(f"\n  Total: {len(CIDADES)} cidades configuradas.")
    print(f"{'='*60}\n")


def etapa_crawler(
    cidade: str,
    sem_limite: bool = False,
    reprocessar_erros: bool = False,
    max_paginas: int | None = None,
    max_profundidade: int | None = None,
):
    from src.crawler import CrawlerUrbano
    crawler = CrawlerUrbano(
        cidade,
        reprocessar_erros=reprocessar_erros,
        max_paginas=max_paginas,
        max_profundidade=max_profundidade,
    )
    crawler.iniciar_varredura(sem_limite=sem_limite)


def etapa_downloader(cidade: str, **_):
    from src.downloader import DownloaderUrbano
    downloader = DownloaderUrbano(cidade)
    downloader.realizar_downloads()


def etapa_analisador(cidade: str, **_):
    from src.analisador import AnalisadorGenero
    analisador = AnalisadorGenero(cidade)
    analisador.analisar()


def main():
    parser = argparse.ArgumentParser(
        description="Pipeline de coleta de dados públicos - TCC UTFPR",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "cidade",
        choices=list(CIDADES.keys()),
        nargs="?",
        default=None,
        help="Município a processar (use --listar para ver todos)",
    )
    parser.add_argument(
        "--listar",
        action="store_true",
        default=False,
        help="Lista todas as cidades configuradas em cidades.json",
    )
    parser.add_argument(
        "--etapa",
        type=int,
        choices=[1, 2, 3],
        default=None,
        help=(
            "Etapa a executar (omitir = todas):\n"
            "  1 = Crawler     (navega e anota arquivos)\n"
            "  2 = Downloader  (baixa os arquivos anotados)\n"
            "  3 = Analisador  (detecta recorte de gênero)"
        ),
    )
    parser.add_argument(
        "--sem-limite",
        action="store_true",
        default=False,
        help=(
            "Remove o limite de páginas do Crawler (MAX_PAGES).\n"
            "Usado para a varredura oficial completa."
        ),
    )
    parser.add_argument(
        "--reprocessar-erros",
        action="store_true",
        default=False,
        help=(
            "Re-enfileira URLs com erros transitórios (TIMEOUT, 403, 500, CAPTCHA)\n"
            "para nova tentativa. Erros permanentes (404, CAPTCHA não resolvido)\n"
            "são ignorados. Só funciona com a Etapa 1 (Crawler)."
        ),
    )
    parser.add_argument(
        "--max-paginas",
        type=int,
        default=None,
        help=(
            "Sobrescreve MAX_PAGES do config.py — limite de páginas processadas.\n"
            "Só funciona com a Etapa 1 (Crawler)."
        ),
    )
    parser.add_argument(
        "--max-profundidade",
        type=int,
        default=None,
        help=(
            "Sobrescreve MAX_DEPTH do config.py — profundidade máxima da BFS.\n"
            "Só funciona com a Etapa 1 (Crawler)."
        ),
    )

    args = parser.parse_args()

    if args.listar:
        listar_cidades()
        return

    if args.cidade is None:
        parser.error("cidade é obrigatória (ou use --listar para ver as opções)")

    cidade = args.cidade
    sem_limite = args.sem_limite
    reprocessar_erros = args.reprocessar_erros
    max_paginas = args.max_paginas
    max_profundidade = args.max_profundidade

    print(f"\n{'='*60}")
    print(f"  TCC - Pipeline de Dados Publicos | {cidade.upper()}")
    print(f"{'='*60}")

    if args.etapa is None:
        print(" Modo: Pipeline completo (Etapas 1 -> 2 -> 3)\n")
        etapa_crawler(cidade, sem_limite=sem_limite, reprocessar_erros=reprocessar_erros,
                      max_paginas=max_paginas, max_profundidade=max_profundidade)
        etapa_downloader(cidade)
        etapa_analisador(cidade)
    elif args.etapa == 1:
        print(" Modo: Somente Etapa 1 - Crawler\n")
        etapa_crawler(cidade, sem_limite=sem_limite, reprocessar_erros=reprocessar_erros,
                      max_paginas=max_paginas, max_profundidade=max_profundidade)
    elif args.etapa == 2:
        print(" Modo: Somente Etapa 2 - Downloader\n")
        etapa_downloader(cidade)
    elif args.etapa == 3:
        print(" Modo: Somente Etapa 3 - Analisador\n")
        etapa_analisador(cidade)

    print(f"\n Pipeline encerrado. Resultados em: resultados/{cidade}/")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
