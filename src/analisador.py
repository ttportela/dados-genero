# =============================================================================
# analisador.py — Classe AnalisadorGenero (Módulo 3 do Pipeline)
# TCC: Mapeamento de Dados Públicos no Paraná — Perspectivas de Gênero
# UTFPR — Adriana Sarturi
# =============================================================================
#
# Responsabilidade: varrer os arquivos baixados pelo Downloader e identificar
# quais contêm dados com recorte de gênero, usando a lista PALAVRAS_GENERO
# do config.py como dicionário de busca.
#
# O Analisador não faz download nem acessa a internet — trabalha 100% offline
# sobre os arquivos já salvos na pasta resultados/{cidade}_oficial/downloads/.
#
# O analisador lê o arquivo completo (todas as abas e todas as linhas).
# Indicadores de gênero aparecem tipicamente nos cabeçalhos, mas a leitura
# total garante que nenhum registro seja perdido.
#
# =============================================================================

import hashlib
import re
import zipfile
from pathlib import Path

import pandas as pd
# pyrefly: ignore [missing-import]
import rarfile

from src.config import DIR_RESULTADOS, PALAVRAS_GENERO, SUFIXO_PASTA, UNRAR_TOOL

# Caminho para o UnRAR configurado em src/config.py
rarfile.UNRAR_TOOL = UNRAR_TOOL

# Extensões que o Analisador sabe processar nativamente (planilhas diretas)
EXTENSOES_SUPORTADAS = {".xlsx", ".xls", ".xlsm", ".ods"}

# Extensões compactadas que o Analisador sabe abrir para inspecionar o conteúdo
# .rar usa a lib rarfile + UnRAR.exe — caminho configurado em src/config.py (UNRAR_TOOL)
EXTENSOES_COMPACTADAS = {".zip"}
EXTENSOES_RAR         = {".rar"}
EXTENSOES_TEXTO       = {".txt"}


class AnalisadorGenero:
    """
    Analisador de recorte de gênero em arquivos de dados estruturados.

    Uso:
        analisador = AnalisadorGenero("maringa")
        analisador.analisar()

    Entrada:  resultados/{cidade}_oficial/downloads/    (arquivos baixados)
    Saída:    resultados/{cidade}_oficial/relatorio_genero.xlsx
    """

    def __init__(self, nome_cidade: str):
        self.nome_cidade   = nome_cidade
        self.dir_cidade    = DIR_RESULTADOS / (nome_cidade + SUFIXO_PASTA)
        self.dir_downloads = self.dir_cidade / "downloads"
        self.arquivo_relatorio = self.dir_cidade / "relatorio_genero.xlsx"
        self.arquivo_resumo_md = self.dir_cidade / "resumo_analise.md"
        # Raiz do projeto — usada para gerar caminhos relativos no relatório
        self.dir_projeto   = DIR_RESULTADOS.parent

        # Mapa {nome_arquivo_em_disco → url_de_origem} montado a partir do
        # inventario_links.xlsx (coluna status_download = "BAIXADO → nome.xlsx")
        self._url_por_arquivo: dict[str, str] = self._carregar_mapa_urls()

    def _carregar_mapa_urls(self) -> dict[str, str]:
        """
        Lê o inventario_links.xlsx e monta um dicionário
        {nome_do_arquivo_salvo: url_de_origem}.

        O Downloader grava o nome salvo na coluna status_download no formato
        "BAIXADO → nome_arquivo.xlsx" — basta remover o prefixo para obter
        o nome e cruzar com a coluna url_encontrada.
        """
        mapa: dict[str, str] = {}
        inventario = self.dir_cidade / "inventario_links.xlsx"
        if not inventario.exists():
            return mapa
        try:
            df_inv = pd.read_excel(inventario, usecols=["url_encontrada", "status_download"])
            for _, row in df_inv.iterrows():
                status = str(row.get("status_download", ""))
                if status.startswith("BAIXADO → "):
                    nome = status.replace("BAIXADO → ", "").strip()
                    mapa[nome] = str(row.get("url_encontrada", ""))
        except Exception as e:
            print(f"Aviso: não foi possível carregar URLs do inventário: {e}")
        return mapa

    # =========================================================================
    # LEITURA DE ARQUIVO
    # =========================================================================

    def _ler_arquivo(self, caminho: Path) -> pd.DataFrame | None:
        """
        Lê um arquivo de planilha completo e retorna como DataFrame.

        Suporta .xlsx, .xls, .xlsm e .ods.
        Retorna None se o arquivo não puder ser lido.

        Lê todas as linhas do arquivo para garantir que nenhum indicador
        de gênero seja perdido.
        """
        extensao = caminho.suffix.lower()
        try:
            if extensao in {".xlsx", ".xls", ".xlsm"}:
                # sheet_name=None retorna todas as abas como dict {nome: DataFrame}
                # Necessário para arquivos com multiplas abas.
                try:
                    todas_abas = pd.read_excel(
                        caminho,
                        sheet_name=None,    # todas as abas
                    )
                except Exception:
                    # Fallback: tenta o engine calamine, mais tolerante com XML
                    # inválido gerado por sistemas de prefeituras
                    try:
                        todas_abas = pd.read_excel(
                            caminho,
                            sheet_name=None,
                            engine="calamine",
                        )
                    except Exception as e2:
                        print(f"Erro ao ler {caminho.name} (openpyxl + calamine): {type(e2).__name__}: {e2}")
                        return None
                if not todas_abas:
                    return None
                # Concatena todas as abas em um único DataFrame para análise unificada
                return pd.concat(todas_abas.values(), ignore_index=True)

            elif extensao == ".ods":
                # ODS também pode ter múltiplas abas
                todas_abas = pd.read_excel(
                    caminho,
                    sheet_name=None,
                    engine="odf",
                )
                if not todas_abas:
                    return None
                return pd.concat(todas_abas.values(), ignore_index=True)

        except Exception as e:
            print(f"Erro ao ler {caminho.name}: {type(e).__name__}: {e}")
            return None

    def _analisar_zip(self, caminho: Path) -> dict:
        """
        Extrai apenas os arquivos elegíveis do .zip para extraidos.
        Analisa cada arquivo extraído com _ler_arquivo() — lógica padrão.

        Retorna:
          - tem_recorte_genero : "Sim" / "Não" / "SEM_ARQUIVOS_ELEGIVEIS" / "ERRO_LEITURA"
          - termos_encontrados : termos encontrados em qualquer arquivo interno
          - total_colunas      : soma das colunas de todos os arquivos internos lidos
        """
        todos_termos: set[str] = set()
        total_colunas = 0
        planilhas_encontradas = 0

        base_extraidos = self.dir_cidade / "extraidos"
        # Inclui a extensão no nome da pasta para evitar colisão entre .zip e .rar homônimos
        nome_pasta = f"{caminho.stem}_{caminho.suffix.lstrip('.')}"
        dir_candidato = base_extraidos / nome_pasta
        dir_extracao = dir_candidato if len(str(dir_candidato)) <= 200 else base_extraidos / hashlib.md5(caminho.name.encode()).hexdigest()[:12]

        try:
            with zipfile.ZipFile(caminho, "r") as zf:
                for item in zf.infolist():
                    ext = Path(item.filename).suffix.lower()
                    if ext not in EXTENSOES_SUPORTADAS:
                        continue  # extrai somente arquivos elegíveis

                    planilhas_encontradas += 1
                    # Cria a pasta só quando há arquivo elegível para extrair
                    if not dir_extracao.exists():
                        dir_extracao.mkdir(parents=True, exist_ok=True)
                        (dir_extracao / "origem.txt").write_text(
                            caminho.name, encoding="utf-8"
                        )
                    # Usa o nome original; recorre ao hash só se o caminho for longo demais
                    nome_base = Path(item.filename).name 
                    destino_candidato = dir_extracao / nome_base
                    if len(str(destino_candidato)) > 240:
                        nome_base = hashlib.md5(item.filename.encode()).hexdigest()[:12] + ext
                    destino = dir_extracao / nome_base
                    try:
                        with zf.open(item) as src, open(destino, "wb") as dst:
                            dst.write(src.read())
                        df = self._ler_arquivo(destino)
                        if df is not None:
                            termos = self._buscar_termos(df)
                            todos_termos.update(termos)
                            total_colunas += len(df.columns)
                    except Exception as e:
                        print(f"Erro ao extrair/ler '{item.filename}': {e}")
                        continue

        except zipfile.BadZipFile:
            return {
                "tem_recorte_genero": "ERRO_LEITURA",
                "termos_encontrados": "",
                "total_colunas": 0,
            }
        except Exception as e:
            print(f"Erro ao abrir ZIP {caminho.name}: {type(e).__name__}: {e}")
            return {
                "tem_recorte_genero": "ERRO_LEITURA",
                "termos_encontrados": "",
                "total_colunas": 0,
            }

        if planilhas_encontradas == 0:
            return {
                "tem_recorte_genero": "SEM_ARQUIVOS_ELEGIVEIS",
                "termos_encontrados": "",
                "total_colunas": 0,
            }

        tem_recorte = "Sim" if todos_termos else "Não"
        return {
            "tem_recorte_genero": tem_recorte,
            "termos_encontrados": ", ".join(sorted(todos_termos)),
            "total_colunas": total_colunas,
        }

    def _analisar_rar(self, caminho: Path) -> dict:
        """
        Extrai apenas os arquivos elegíveis do .rar para extraidos.
        Analisa cada arquivo extraído com _ler_arquivo() — lógica padrão.

        Retorna:
          - tem_recorte_genero : "Sim" / "Não" / "SEM_ARQUIVOS_ELEGIVEIS" / "ERRO_LEITURA"
          - termos_encontrados : termos encontrados em qualquer arquivo interno
          - total_colunas      : soma das colunas de todos os arquivos internos lidos
        """
        todos_termos: set[str] = set()
        total_colunas = 0
        planilhas_encontradas = 0

        base_extraidos = self.dir_cidade / "extraidos"
        # Inclui a extensão no nome da pasta para evitar colisão entre .zip e .rar homônimos
        nome_pasta = f"{caminho.stem}_{caminho.suffix.lstrip('.')}"
        dir_candidato = base_extraidos / nome_pasta
        dir_extracao = dir_candidato if len(str(dir_candidato)) <= 200 else base_extraidos / hashlib.md5(caminho.name.encode()).hexdigest()[:12]

        try:
            with rarfile.RarFile(caminho, "r") as rf:
                for item in rf.infolist():
                    ext = Path(item.filename).suffix.lower()
                    if ext not in EXTENSOES_SUPORTADAS:
                        continue  # extrai somente arquivos elegíveis

                    planilhas_encontradas += 1
                    # Cria a pasta só quando há arquivo elegível para extrair
                    if not dir_extracao.exists():
                        dir_extracao.mkdir(parents=True, exist_ok=True)
                        (dir_extracao / "origem.txt").write_text(
                            caminho.name, encoding="utf-8"
                        )
                    # Usa o nome original; recorre ao hash só se o caminho for longo demais
                    nome_base = Path(item.filename).name
                    destino_candidato = dir_extracao / nome_base
                    if len(str(destino_candidato)) > 240:
                        nome_base = hashlib.md5(item.filename.encode()).hexdigest()[:12] + ext
                    destino = dir_extracao / nome_base
                    try:
                        with rf.open(item) as src, open(destino, "wb") as dst:
                            dst.write(src.read())
                        df = self._ler_arquivo(destino)
                        if df is not None:
                            termos = self._buscar_termos(df)
                            todos_termos.update(termos)
                            total_colunas += len(df.columns)
                    except Exception as e:
                        print(f"Erro ao extrair/ler '{item.filename}': {e}")
                        continue

        except rarfile.BadRarFile:
            return {
                "tem_recorte_genero": "ERRO_LEITURA",
                "termos_encontrados": "",
                "total_colunas": 0,
            }
        except Exception as e:
            print(f"Erro ao abrir RAR {caminho.name}: {type(e).__name__}: {e}")
            return {
                "tem_recorte_genero": "ERRO_LEITURA",
                "termos_encontrados": "",
                "total_colunas": 0,
            }

        if planilhas_encontradas == 0:
            return {
                "tem_recorte_genero": "SEM_ARQUIVOS_ELEGIVEIS",
                "termos_encontrados": "",
                "total_colunas": 0,
            }

        tem_recorte = "Sim" if todos_termos else "Não"
        return {
            "tem_recorte_genero": tem_recorte,
            "termos_encontrados": ", ".join(sorted(todos_termos)),
            "total_colunas": total_colunas,
        }

    def _analisar_txt(self, caminho: Path) -> dict:
        """
        Analisa um arquivo .txt detectando seu tipo real pelos magic bytes:
          - Se começa com PK (50 4B): é docx/xlsx disfarçado → trata como ZIP
          - Caso contrário: lê o conteúdo completo como texto e busca termos

        Lê o arquivo inteiro, pois termos de gênero podem aparecer em qualquer posição.
        """
        # Detecta magic bytes para identificar arquivos disfarçados
        try:
            with open(caminho, "rb") as f:
                magic = f.read(2)
        except Exception as e:
            print(f"Erro ao ler magic bytes de {caminho.name}: {e}")
            return {"tem_recorte_genero": "ERRO_LEITURA", "termos_encontrados": "", "total_colunas": 0}

        if magic == b"PK":
            # Magic bytes PK: pode ser um xlsx/xls standalone com extensão .txt errada
            # OU um arquivo .zip contendo planilhas. Testa como planilha primeiro.
            print(f"[AVISO] Magic bytes PK em .txt — tentando leitura como planilha...")
            try:
                todas_abas = pd.read_excel(caminho, sheet_name=None)
                if todas_abas:
                    df_concat = pd.concat(todas_abas.values(), ignore_index=True)
                    termos = self._buscar_termos(df_concat)
                    tem_recorte = "Sim" if termos else "Não"
                    print(f"[AVISO] Lido como planilha (xlsx/xls disfarçado de .txt)")
                    return {
                        "tem_recorte_genero": tem_recorte,
                        "termos_encontrados": ", ".join(sorted(termos)),
                        "total_colunas": len(df_concat.columns),
                    }
            except Exception:
                pass
            # Fallback: trata como ZIP container com planilhas internas
            print(f"[AVISO] Não lido como planilha — tratando como ZIP container")
            return self._analisar_zip(caminho)

        # Texto puro: tenta utf-8, fallback latin-1
        conteudo = None
        for enc in ("utf-8", "latin-1"):
            try:
                conteudo = caminho.read_text(encoding=enc)
                break
            except Exception:
                continue

        if conteudo is None:
            return {"tem_recorte_genero": "ERRO_LEITURA", "termos_encontrados": "", "total_colunas": 0}

        # Busca termos diretamente no texto bruto (arquivo inteiro)
        termos: set[str] = set()
        texto_lower = conteudo.lower()
        for termo in PALAVRAS_GENERO:
            padrao = r"\b" + re.escape(termo.lower()) + r"\b"
            if re.search(padrao, texto_lower):
                termos.add(termo)

        tem_recorte = "Sim" if termos else "Não"
        return {
            "tem_recorte_genero": tem_recorte,
            "termos_encontrados": ", ".join(sorted(termos)),
            "total_colunas": 0,  # não aplicável para texto puro
        }

    # =========================================================================
    # BUSCA DE TERMOS DE GÊNERO
    # =========================================================================

    def _buscar_termos(self, df: pd.DataFrame) -> list[str]:
        """
        Varre o DataFrame em busca de termos de gênero e retorna os encontrados.

        Estratégia em duas camadas:
          1. Nomes de colunas — campo mais confiável; ex: coluna "sexo" ou "gênero"
          2. Células de todas as linhas -- para cabeçalhos em células e metadados

        Busca usa limite de palavra (\b) via regex para evitar falsos positivos:
          - "men" não casa com "documentos", "orçamento", "fundamentos"
          - "sex" não casa com "sexta-feira"
          - "man" não casa com "comando", "manual", "programação"
        Falsos positivos residuais (ex: "man" como sigla de empresa) são
        tratados na curadoria manual.
        """
        termos_encontrados = set()

        def _contem_termo(texto: str, termo: str) -> bool:
            """Busca case-insensitive com limite de palavra."""
            padrao = r"\b" + re.escape(termo.lower()) + r"\b"
            return bool(re.search(padrao, texto.lower()))

        # Camada 1: nomes de colunas
        nomes_colunas = " ".join(str(col) for col in df.columns).lower()
        for termo in PALAVRAS_GENERO:
            if _contem_termo(nomes_colunas, termo):
                termos_encontrados.add(termo)

        # Camada 2: células de todas as linhas
        for _, linha in df.iterrows():
            texto_linha = " ".join(str(cell) for cell in linha.values).lower()
            for termo in PALAVRAS_GENERO:
                if _contem_termo(texto_linha, termo):
                    termos_encontrados.add(termo)

        return sorted(termos_encontrados)

    # =========================================================================
    # GERAÇÃO DO RESUMO .md
    # =========================================================================

    def _gerar_resumo_colunas(self, df: pd.DataFrame) -> list[dict]:
        """
        Gera estatísticas descritivas para cada coluna do DataFrame.

        Retorna uma lista de dicts, um por coluna, com:
          - coluna, tipo, unicos, unicos_pct, faltantes, faltantes_pct
        """
        total_linhas = len(df)
        resumo = []
        for col in df.columns:
            serie = df[col]
            unicos = serie.nunique(dropna=True)
            faltantes = serie.isna().sum()
            resumo.append({
                "coluna": str(col),
                "tipo": str(serie.dtype),
                "unicos": unicos,
                "unicos_pct": f"{(unicos / total_linhas * 100):.1f}%" if total_linhas else "—",
                "faltantes": int(faltantes),
                "faltantes_pct": f"{(faltantes / total_linhas * 100):.1f}%" if total_linhas else "—",
            })
        return resumo

    def _gerar_md_final(self, resumos: list[dict], stats_finais: dict):
        """
        Escreve o arquivo resumo_analise.md com:
          - Para cada arquivo lido: head(10) + resumo descritivo das colunas
          - Resumo estatístico final (tipos de dados, recorte de gênero, etc.)
        """
        linhas: list[str] = []
        linhas.append(f"# Resumo da Análise — {self.nome_cidade.upper()}\n")

        # --- Seção por arquivo ---
        for r in resumos:
            linhas.append(f"## Arquivo: `{r['nome_arquivo']}`\n")
            if r.get("url_origem"):
                linhas.append(f"- **URL de origem:** {r['url_origem']}")
            linhas.append(f"- **Extensão:** {r['extensao']}")
            linhas.append(f"- **Linhas:** {r['total_linhas']} | **Colunas:** {r['total_colunas']}")
            linhas.append(f"- **Recorte de gênero:** {r['tem_recorte']}")
            if r.get("termos"):
                linhas.append(f"- **Termos encontrados:** {r['termos']}")
            linhas.append("")

            # head(10)
            linhas.append("### Primeiras 10 linhas\n")
            if r.get("head_md"):
                linhas.append(r["head_md"])
            else:
                linhas.append("_(não disponível)_")
            linhas.append("")

            # Resumo das colunas
            linhas.append("### Resumo das colunas\n")
            linhas.append("| Coluna | Tipo | Únicos | % Únicos | Faltantes | % Faltantes |")
            linhas.append("|--------|------|--------|----------|-----------|-------------|")
            for c in r.get("colunas", []):
                linhas.append(
                    f"| {c['coluna']} | {c['tipo']} | {c['unicos']} | {c['unicos_pct']} | {c['faltantes']} | {c['faltantes_pct']} |"
                )
            linhas.append("\n---\n")

        # --- Resumo estatístico final ---
        linhas.append("## Resumo Estatístico Final\n")

        linhas.append("### Arquivos analisados\n")
        linhas.append(f"- **Total de arquivos:** {stats_finais['total_arquivos']}")
        linhas.append(f"- **Lidos com sucesso:** {stats_finais['lidos']}")
        linhas.append(f"- **Erros de leitura:** {stats_finais['erros']}")
        linhas.append(f"- **Compactados sem elegíveis:** {stats_finais['sem_elegiveis']}")
        linhas.append("")

        linhas.append("### Recorte de gênero\n")
        com_genero = stats_finais['com_genero']
        sem_genero = stats_finais['sem_genero']
        pct_genero = f"{(com_genero / stats_finais['lidos'] * 100):.1f}%" if stats_finais['lidos'] else "—"
        linhas.append(f"- **Com recorte de gênero:** {com_genero} ({pct_genero} dos lidos)")
        linhas.append(f"- **Sem recorte de gênero:** {sem_genero}")
        linhas.append("")

        linhas.append("### Tipos de dados (colunas de todos os arquivos lidos)\n")
        linhas.append("| Tipo | Quantidade de colunas | % |")
        linhas.append("|------|----------------------|---|")
        total_cols = sum(stats_finais['tipos_dados'].values())
        for tipo, qtd in sorted(stats_finais['tipos_dados'].items(), key=lambda x: -x[1]):
            pct = f"{(qtd / total_cols * 100):.1f}%" if total_cols else "—"
            linhas.append(f"| {tipo} | {qtd} | {pct} |")
        linhas.append("")

        linhas.append("### Estatísticas gerais\n")
        linhas.append(f"- **Total de colunas (soma):** {total_cols}")
        linhas.append(f"- **Média de colunas por arquivo:** {stats_finais['media_colunas']:.1f}")
        if stats_finais.get('arquivo_mais_colunas'):
            linhas.append(f"- **Arquivo com mais colunas:** `{stats_finais['arquivo_mais_colunas']}` ({stats_finais['max_colunas']} colunas)")
        linhas.append(f"- **Total de linhas (soma):** {stats_finais['total_linhas']}")
        linhas.append("")

        self.arquivo_resumo_md.write_text("\n".join(linhas), encoding="utf-8")
        print(f"  Resumo markdown salvo: {self.arquivo_resumo_md}")

    # =========================================================================
    # ANÁLISE PRINCIPAL
    # =========================================================================

    def analisar(self):
        """
        Varre todos os arquivos da pasta de downloads e gera o relatório de gênero.

        Cada linha do relatório representa um arquivo analisado, com:
          - nome_arquivo           : nome do arquivo em disco
          - extensao               : tipo do arquivo
          - tem_recorte_genero     : Sim / Não / SEM_ARQUIVOS_ELEGIVEIS / ERRO_LEITURA
          - termos_encontrados     : lista dos termos detectados
          - total_colunas          : número de colunas do arquivo (proxy de riqueza)
          - curadoria_relevancia   : Sim / Não / Aguardando (preenchido manualmente)
          - curadoria_justificativa: texto livre com a justificativa da curadoria
          - caminho_relativo       : caminho relativo à raiz do projeto para localização
        """
        if not self.dir_downloads.exists():
            print(f"Pasta de downloads não encontrada: {self.dir_downloads}")
            print("Execute o Downloader primeiro.")
            return

        arquivos = [
            f for f in self.dir_downloads.iterdir()
            if f.is_file() and f.suffix.lower() in (
                EXTENSOES_SUPORTADAS | EXTENSOES_COMPACTADAS | EXTENSOES_RAR | EXTENSOES_TEXTO
            )
        ]

        if not arquivos:
            print(f"Nenhum arquivo elegível encontrado em: {self.dir_downloads}")
            return

        print(f"\n{'='*60}")
        print(f"  Analisador iniciado: {self.nome_cidade.upper()}")
        print(f"  Arquivos para analisar: {len(arquivos)}")
        print(f"  Termos de gênero no dicionário: {len(PALAVRAS_GENERO)}")
        print(f"{'='*60}\n")

        registros = []
        self._resumos_md: list[dict] = []  # dados para o resumo .md

        for arquivo in sorted(arquivos):
            print(f"Analisando: {arquivo.name}")
            extensao = arquivo.suffix.lower()

            # --- Arquivos compactados ZIP: inspeciona planilhas internas ---
            if extensao in EXTENSOES_COMPACTADAS:
                resultado = self._analisar_zip(arquivo)
                icone = "✅" if resultado["tem_recorte_genero"] == "Sim" else "➖"
                print(f"  {icone} {resultado['tem_recorte_genero']} | termos: {resultado['termos_encontrados'] or '—'}")
                tem_recorte = resultado["tem_recorte_genero"]
                registros.append({
                    "cidade":                 self.nome_cidade,
                    "nome_arquivo":           arquivo.name,
                    "extensao":               extensao,
                    "url_origem":             self._url_por_arquivo.get(arquivo.name, ""),
                    "tem_recorte_genero":     tem_recorte,
                    "termos_encontrados":     resultado["termos_encontrados"],
                    "total_colunas":          resultado["total_colunas"],
                    "curadoria_relevancia":   "Aguardando" if tem_recorte == "Sim" else "",
                    "curadoria_justificativa": "",
                    "caminho_relativo":       str(arquivo.relative_to(self.dir_projeto)),
                })
                if tem_recorte in ("Sim", "Não"):
                    self._resumos_md.append({
                        "nome_arquivo":   arquivo.name,
                        "extensao":       extensao,
                        "url_origem":     self._url_por_arquivo.get(arquivo.name, ""),
                        "tem_recorte":    tem_recorte,
                        "termos":         resultado["termos_encontrados"],
                        "total_linhas":   0,
                        "total_colunas":  resultado["total_colunas"],
                        "head_md":        "_(arquivo compactado — conteúdo extraído em extraidos/)_",
                        "colunas":        [],
                    })
                continue

            # --- Arquivos compactados RAR: inspeciona planilhas internas ---
            if extensao in EXTENSOES_RAR:
                resultado = self._analisar_rar(arquivo)
                icone = "✅" if resultado["tem_recorte_genero"] == "Sim" else "➖"
                print(f"  {icone} {resultado['tem_recorte_genero']} | termos: {resultado['termos_encontrados'] or '—'}")
                tem_recorte = resultado["tem_recorte_genero"]
                registros.append({
                    "cidade":                 self.nome_cidade,
                    "nome_arquivo":           arquivo.name,
                    "extensao":               extensao,
                    "url_origem":             self._url_por_arquivo.get(arquivo.name, ""),
                    "tem_recorte_genero":     tem_recorte,
                    "termos_encontrados":     resultado["termos_encontrados"],
                    "total_colunas":          resultado["total_colunas"],
                    "curadoria_relevancia":   "Aguardando" if tem_recorte == "Sim" else "",
                    "curadoria_justificativa": "",
                    "caminho_relativo":       str(arquivo.relative_to(self.dir_projeto)),
                })
                if tem_recorte in ("Sim", "Não"):
                    self._resumos_md.append({
                        "nome_arquivo":   arquivo.name,
                        "extensao":       extensao,
                        "url_origem":     self._url_por_arquivo.get(arquivo.name, ""),
                        "tem_recorte":    tem_recorte,
                        "termos":         resultado["termos_encontrados"],
                        "total_linhas":   0,
                        "total_colunas":  resultado["total_colunas"],
                        "head_md":        "_(arquivo compactado — conteúdo extraído em extraidos/)_",
                        "colunas":        [],
                    })
                continue

            # --- Arquivos de texto .txt: detecta tipo por magic bytes ---
            if extensao in EXTENSOES_TEXTO:
                resultado = self._analisar_txt(arquivo)
                icone = "✅" if resultado["tem_recorte_genero"] == "Sim" else "➖"
                print(f"  {icone} {resultado['tem_recorte_genero']} | termos: {resultado['termos_encontrados'] or '—'}")
                tem_recorte = resultado["tem_recorte_genero"]
                registros.append({
                    "cidade":                 self.nome_cidade,
                    "nome_arquivo":           arquivo.name,
                    "extensao":               extensao,
                    "url_origem":             self._url_por_arquivo.get(arquivo.name, ""),
                    "tem_recorte_genero":     tem_recorte,
                    "termos_encontrados":     resultado["termos_encontrados"],
                    "total_colunas":          resultado["total_colunas"],
                    "curadoria_relevancia":   "Aguardando" if tem_recorte == "Sim" else "",
                    "curadoria_justificativa": "",
                    "caminho_relativo":       str(arquivo.relative_to(self.dir_projeto)),
                })
                continue

            # --- Planilhas diretas ---
            df = self._ler_arquivo(arquivo)

            if df is None:
                registros.append({
                    "cidade":                 self.nome_cidade,
                    "nome_arquivo":           arquivo.name,
                    "extensao":               extensao,
                    "url_origem":             self._url_por_arquivo.get(arquivo.name, ""),
                    "tem_recorte_genero":     "ERRO_LEITURA",
                    "termos_encontrados":     "",
                    "total_colunas":          0,
                    "curadoria_relevancia":   "",
                    "curadoria_justificativa": "",
                    "caminho_relativo":       str(arquivo.relative_to(self.dir_projeto)),
                })
                continue

            termos = self._buscar_termos(df)
            tem_recorte = "Sim" if termos else "Não"

            icone = "✅" if termos else "➖"
            print(f"  {icone} {tem_recorte} | colunas: {len(df.columns)} | termos: {termos if termos else '—'}")

            registros.append({
                "cidade":                 self.nome_cidade,
                "nome_arquivo":           arquivo.name,
                "extensao":               extensao,
                "url_origem":             self._url_por_arquivo.get(arquivo.name, ""),
                "tem_recorte_genero":     tem_recorte,
                "termos_encontrados":     ", ".join(termos),
                "total_colunas":          len(df.columns),
                "curadoria_relevancia":   "Aguardando" if termos else "",
                "curadoria_justificativa": "",
                "caminho_relativo":       str(arquivo.relative_to(self.dir_projeto)),
            })

            # Coleta resumo para o .md
            try:
                head_md = df.head(10).to_markdown(index=False)
            except Exception:
                linhas_txt = []
                for i, (_, linha) in enumerate(df.head(10).iterrows()):
                    valores = " | ".join(str(v) for v in linha.values)
                    linhas_txt.append(f"{i+1}. {valores}")
                head_md = "\n".join(linhas_txt) if linhas_txt else "_(arquivo vazio)_"
            self._resumos_md.append({
                "nome_arquivo":   arquivo.name,
                "extensao":       extensao,
                "url_origem":     self._url_por_arquivo.get(arquivo.name, ""),
                "tem_recorte":    tem_recorte,
                "termos":         ", ".join(termos),
                "total_linhas":   len(df),
                "total_colunas":  len(df.columns),
                "head_md":        head_md,
                "colunas":        self._gerar_resumo_colunas(df),
            })

        # Gera relatório final
        df_relatorio = pd.DataFrame(registros)

        # Ordena: arquivos COM recorte de gênero primeiro
        df_relatorio = df_relatorio.sort_values(
            by="tem_recorte_genero",
            key=lambda col: col.map({"Sim": 0, "Não": 1, "SEM_ARQUIVOS_ELEGIVEIS": 2, "ERRO_LEITURA": 3}),
        )

        df_relatorio.to_excel(self.arquivo_relatorio, index=False)

        # Resumo
        total_sim      = (df_relatorio["tem_recorte_genero"] == "Sim").sum()
        total_nao      = (df_relatorio["tem_recorte_genero"] == "Não").sum()
        total_erro     = (df_relatorio["tem_recorte_genero"] == "ERRO_LEITURA").sum()
        total_sem_plan = (df_relatorio["tem_recorte_genero"] == "SEM_ARQUIVOS_ELEGIVEIS").sum()

        print(f"\n{'='*60}")
        print(f"  Análise concluída: {self.nome_cidade.upper()}")
        print(f"  Com recorte de gênero          : {total_sim}")
        print(f"  Sem recorte de gênero          : {total_nao}")
        print(f"  ZIPs/RARs sem arq. elegíveis   : {total_sem_plan}")
        print(f"  Erros de leitura               : {total_erro}")
        print(f"  Relatório salvo                : {self.arquivo_relatorio}")

        # Gera o resumo .md com head(10) + resumo das colunas + estatísticas finais
        tipos_dados: dict[str, int] = {}
        total_linhas_soma = 0
        total_colunas_soma = 0
        max_colunas = 0
        arquivo_mais_colunas = ""
        for r in self._resumos_md:
            for c in r.get("colunas", []):
                t = c["tipo"]
                tipos_dados[t] = tipos_dados.get(t, 0) + 1
            total_linhas_soma += r["total_linhas"]
            total_colunas_soma += r["total_colunas"]
            if r["total_colunas"] > max_colunas:
                max_colunas = r["total_colunas"]
                arquivo_mais_colunas = r["nome_arquivo"]

        lidos = total_sim + total_nao
        stats_finais = {
            "total_arquivos":       len(arquivos),
            "lidos":                lidos,
            "erros":                total_erro,
            "sem_elegiveis":        total_sem_plan,
            "com_genero":           total_sim,
            "sem_genero":           total_nao,
            "tipos_dados":          tipos_dados,
            "media_colunas":        total_colunas_soma / lidos if lidos else 0,
            "max_colunas":          max_colunas,
            "arquivo_mais_colunas": arquivo_mais_colunas,
            "total_linhas":         total_linhas_soma,
        }
        self._gerar_md_final(self._resumos_md, stats_finais)

        print(f"{'='*60}\n")
