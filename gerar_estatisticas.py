# =============================================================================
# gerar_estatisticas_tcc.py — Gerador de Estatísticas para o TCC
# TCC: Mapeamento de Dados Públicos no Paraná — Perspectivas de Gênero
# UTFPR — Adriana Sarturi
# =============================================================================
#
# Este script lê os resultados do crawler e gera as estatísticas necessárias
# para análise.
#
# Como usar:
#   venv\Scripts\python gerar_estatisticas_tcc.py
# =============================================================================

import os
import json
import pandas as pd
from src.config import CIDADES as CIDADES_CONFIG, DIR_RESULTADOS, SUFIXO_PASTA

# Lista ordenada das cidades — derivada do dicionário central em config.py
CIDADES = list(CIDADES_CONFIG.keys())

# Extensões consideradas malformadas (artefatos de parsing de URL)
EXTENSOES_MALFORMADAS = {".pd", ".0", ".pdf]", '.pdf""', ".html>", ".url}}", ".ht", ".2022", ".do", ".", ""}


def normalizar_extensao(ext) -> str:
    """Normaliza a extensão para comparação."""
    return str(ext).lower().strip()


def carregar_inventario(cidade: str) -> pd.DataFrame | None:
    caminho = DIR_RESULTADOS / (cidade + SUFIXO_PASTA) / "inventario_links.xlsx"
    if not caminho.exists():
        print(f"  [AVISO] inventario_links.xlsx não encontrado para {cidade}.")
        return None
    return pd.read_excel(caminho)


def carregar_erros(cidade: str) -> pd.DataFrame | None:
    caminho = DIR_RESULTADOS / (cidade + SUFIXO_PASTA) / "erros_varredura.xlsx"
    if not caminho.exists():
        return None
    return pd.read_excel(caminho)


def carregar_visited(cidade: str) -> int:
    caminho = DIR_RESULTADOS / (cidade + SUFIXO_PASTA) / "checkpoint_visited.json"
    if not caminho.exists():
        return 0
    with open(caminho, encoding="utf-8") as f:
        return len(json.load(f))


def separador(titulo: str):
    print(f"\n{'='*60}")
    print(f"  {titulo}")
    print(f"{'='*60}")


def imprimir_tabela2_panorama():
    """Tabela 2 — Panorama geral da coleta por município."""
    separador("TABELA 2 — Panorama Geral da Coleta")
    print(f"{'Município':<12} {'Páginas':>15} {'Prof. Máx':>10} {'Arquivos':>10} {'Erros':>8}")
    print("-" * 60)

    for cidade in CIDADES:
        paginas   = carregar_visited(cidade)
        inv       = carregar_inventario(cidade)
        erros_df  = carregar_erros(cidade)
        arquivos  = len(inv) if inv is not None else "N/D"
        erros     = len(erros_df) if erros_df is not None else "N/D"
        prof      = inv["profundidade"].max() if (inv is not None and "profundidade" in inv.columns) else "N/D"

        print(f"{cidade.capitalize():<12} {paginas:>15,} {str(prof):>10} {str(arquivos):>10} {str(erros):>8}")


def imprimir_tabela3_tipos():
    """Tabela 3 — Todas as extensões encontradas por município, sem agrupar."""
    separador("TABELA 3 — Distribuição por Tipo de Arquivo (todas as extensões)")

    # Carrega inventários e coleta extensões por cidade
    inventarios = {}
    for cidade in CIDADES:
        inv = carregar_inventario(cidade)
        inventarios[cidade] = inv

    # Coleta todas as extensões únicas válidas
    todas_extensoes: dict[str, dict[str, int]] = {}  # ext -> {cidade: count}
    malformadas: dict[str, dict[str, int]] = {}

    for cidade in CIDADES:
        inv = inventarios[cidade]
        if inv is None:
            continue
        contagem = inv["tipo_arquivo"].value_counts().to_dict()
        for ext, count in contagem.items():
            ext_norm = normalizar_extensao(ext)
            destino = malformadas if ext_norm in EXTENSOES_MALFORMADAS else todas_extensoes
            if ext_norm not in destino:
                destino[ext_norm] = {c: 0 for c in CIDADES}
            destino[ext_norm][cidade] = count

    # Ordena por total decrescente
    def total(d): return sum(d.values())
    extensoes_ordenadas = sorted(todas_extensoes.items(), key=lambda x: total(x[1]), reverse=True)

    # Cabeçalho
    header = f"{'Extensão':<14}" + "".join(f"{c.capitalize():>12}" for c in CIDADES) + f"{'TOTAL':>10}"
    print(header)
    print("-" * (14 + 12 * len(CIDADES) + 10))

    totais = {c: 0 for c in CIDADES}
    for ext, contagem in extensoes_ordenadas:
        linha = f"{ext:<14}" + "".join(f"{contagem.get(c, 0):>12,}" for c in CIDADES)
        linha += f"{total(contagem):>10,}"
        print(linha)
        for c in CIDADES:
            totais[c] += contagem.get(c, 0)

    print("-" * (14 + 12 * len(CIDADES) + 10))
    total_linha = f"{'TOTAL':<14}" + "".join(f"{totais[c]:>12,}" for c in CIDADES)
    total_linha += f"{sum(totais.values()):>10,}"
    print(total_linha)

    # Exibe malformadas separadamente
    if malformadas:
        print(f"\n  [URLs malformadas — excluídas da tabela principal]")
        mal_ord = sorted(malformadas.items(), key=lambda x: total(x[1]), reverse=True)
        for ext, contagem in mal_ord:
            linha = f"  {ext:<12}" + "".join(f"{contagem.get(c, 0):>12,}" for c in CIDADES)
            print(linha)


def imprimir_tabela4_genero():
    """Tabela 4 — Arquivos com termos de gênero (etapa 3)."""
    separador("TABELA 4 — Análise de Gênero (preencher após etapa 3)")

    for cidade in CIDADES:
        caminho = DIR_RESULTADOS / (cidade + SUFIXO_PASTA) / "relatorio_genero.xlsx"
        if caminho.exists():
            df = pd.read_excel(caminho)
            total = len(df)
            
            # Determina a coluna correta
            col_busca = "tem_recorte_genero" if "tem_recorte_genero" in df.columns else ("tem_genero" if "tem_genero" in df.columns else None)
            
            if col_busca:
                if col_busca == "tem_recorte_genero":
                    com_genero = (df[col_busca] == "Sim").sum()
                else:
                    com_genero = df[col_busca].sum()
                
                pct = f"{com_genero/total*100:.1f}%" if total > 0 else "0.0%"
                print(f"  {cidade.capitalize():<12}: {total:>8} analisados | {com_genero:>8} com recorte de gênero ({pct})")
            else:
                print(f"  {cidade.capitalize():<12}: [coluna inválida no relatório]")
        else:
            print(f"  {cidade.capitalize():<12}: [aguardando etapa 3]")


def main():
    print("\n" + "="*60)
    print("  GERADOR DE ESTATÍSTICAS — TCC Adriana Sarturi")
    print("  Mapeamento de Dados Públicos no PR — Perspectivas de Gênero")
    print("="*60)

    imprimir_tabela2_panorama()
    imprimir_tabela3_tipos()
    imprimir_tabela4_genero()

    print("\n" + "="*60)
    print("  Estatísticas geradas com sucesso!")
    print("  Copie os valores acima para as tabelas do TCC.")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()
