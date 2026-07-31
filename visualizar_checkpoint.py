# =============================================================================
# visualizar_checkpoint.py — Visualizador de Checkpoint do Crawler
# TCC: Mapeamento de Dados Públicos no Paraná — Perspectivas de Gênero
# UTFPR — Adriana Sarturi
# =============================================================================
#
# App Streamlit para inspecionar o estado do crawler após ou durante a
# execução: URLs visitadas, fila pendente, erros e inventário de arquivos.
#
# Como usar:
#   streamlit run visualizar_checkpoint.py
#
# Dependências:
#   pip install streamlit pandas openpyxl
# =============================================================================

import json
from pathlib import Path
from urllib.parse import urlparse

import pandas as pd
import streamlit as st
from streamlit_autorefresh import st_autorefresh

from src.config import CIDADES, DIR_RESULTADOS, MAX_DEPTH, SUFIXO_PASTA


def _is_valid_domain(netloc: str, dominios: list[str]) -> bool:
    """Verifica se o netloc pertence a um dos domínios válidos (respeita limites de rótulo)."""
    netloc = netloc.lower()
    return any(
        netloc == d.lower() or netloc.endswith("." + d.lower())
        for d in dominios
    )


# =============================================================================
# CARREGAMENTO DE DADOS (com cache)
# =============================================================================

# --- Funções base (sem cache) ---

def _carregar_visited_raw(caminho_str: str) -> list[str]:
    """Carrega o checkpoint de URLs visitadas."""
    caminho = Path(caminho_str)
    if not caminho.exists():
        return []
    with open(caminho, encoding="utf-8") as f:
        return json.load(f)


def _carregar_queue_raw(caminho_str: str) -> list[dict]:
    """Carrega o checkpoint de URLs na fila (lista de {url, depth})."""
    caminho = Path(caminho_str)
    if not caminho.exists():
        return []
    with open(caminho, encoding="utf-8") as f:
        return json.load(f)


def _carregar_excel_raw(caminho_str: str) -> pd.DataFrame | None:
    """Carrega um arquivo Excel (.xlsx) como DataFrame."""
    caminho = Path(caminho_str)
    if not caminho.exists():
        return None
    try:
        return pd.read_excel(caminho)
    except Exception:
        return None


# --- Wrappers com cache (apenas para cidades 100% completas) ---

@st.cache_data(show_spinner=False)
def carregar_visited(caminho_str: str) -> list[str]:
    return _carregar_visited_raw(caminho_str)


@st.cache_data(show_spinner=False)
def carregar_queue(caminho_str: str) -> list[dict]:
    return _carregar_queue_raw(caminho_str)


@st.cache_data(show_spinner=False)
def carregar_excel(caminho_str: str) -> pd.DataFrame | None:
    return _carregar_excel_raw(caminho_str)


def _cidade_completa(dir_cidade: Path) -> bool:
    """Verifica se a cidade terminou (fila vazia ou inexistente)."""
    caminho_queue = dir_cidade / "checkpoint_queue.json"
    if not caminho_queue.exists():
        return True
    queue = _carregar_queue_raw(str(caminho_queue))
    return len(queue) == 0


# =============================================================================
# FUNÇÃO: CARREGAR MÉTRICAS DE UMA CIDADE
# =============================================================================

def carregar_metricas_cidade(cidade: str, usar_oficial: bool) -> dict | None:
    """Carrega métricas resumidas de uma cidade para o dashboard.

    Cidades 100% completas (fila vazia) usam cache permanente.
    Cidades em execução recarregam dados sem cache a cada chamada.
    """
    pasta = cidade + (SUFIXO_PASTA if usar_oficial else "")
    dir_c = DIR_RESULTADOS / pasta

    if not dir_c.exists():
        return None

    # Cidades completas → cache; em execução → sem cache (dados frescos)
    completa = _cidade_completa(dir_c)
    if completa:
        visited = carregar_visited(str(dir_c / "checkpoint_visited.json"))
        queue = carregar_queue(str(dir_c / "checkpoint_queue.json"))
        df_err = carregar_excel(str(dir_c / "erros_varredura.xlsx"))
        df_inv = carregar_excel(str(dir_c / "inventario_links.xlsx"))
        df_ext = carregar_excel(str(dir_c / "inventario_externos.xlsx"))
    else:
        visited = _carregar_visited_raw(str(dir_c / "checkpoint_visited.json"))
        queue = _carregar_queue_raw(str(dir_c / "checkpoint_queue.json"))
        df_err = _carregar_excel_raw(str(dir_c / "erros_varredura.xlsx"))
        df_inv = _carregar_excel_raw(str(dir_c / "inventario_links.xlsx"))
        df_ext = _carregar_excel_raw(str(dir_c / "inventario_externos.xlsx"))

    total_vis = len(visited)
    total_q = len(queue)
    total_err = len(df_err) if df_err is not None else 0
    total_inv = len(df_inv) if df_inv is not None else 0
    total_ext = len(df_ext) if df_ext is not None else 0
    total_urls = total_vis + total_q
    progresso = (total_vis / total_urls) if total_urls > 0 else 0.0

    ultimo_nivel = 0
    if df_inv is not None and total_inv > 0 and "profundidade" in df_inv.columns:
        ultimo_nivel = int(df_inv["profundidade"].max())

    return {
        "cidade": cidade,
        "pasta": str(dir_c),
        "paginas_visitadas": total_vis,
        "urls_na_fila": total_q,
        "arquivos": total_inv,
        "erros": total_err,
        "externos": total_ext,
        "ultimo_nivel_arquivos": ultimo_nivel,
        "progresso": progresso,
        "total_urls": total_urls,
        "completa": completa,
    }


# =============================================================================
# MÉTRICAS FILTRADAS POR DOMÍNIO (modo Resultados)
# =============================================================================

def carregar_metricas_filtradas(cidade: str, usar_oficial: bool) -> dict | None:
    """Carrega métricas de uma cidade filtrando apenas URLs de domínios permitidos."""
    pasta = cidade + (SUFIXO_PASTA if usar_oficial else "")
    dir_c = DIR_RESULTADOS / pasta

    if not dir_c.exists():
        return None

    dominios = CIDADES[cidade]["dominios"]

    completa = _cidade_completa(dir_c)
    if completa:
        visited = carregar_visited(str(dir_c / "checkpoint_visited.json"))
        queue = carregar_queue(str(dir_c / "checkpoint_queue.json"))
        df_err = carregar_excel(str(dir_c / "erros_varredura.xlsx"))
        df_inv = carregar_excel(str(dir_c / "inventario_links.xlsx"))
        df_ext = carregar_excel(str(dir_c / "inventario_externos.xlsx"))
    else:
        visited = _carregar_visited_raw(str(dir_c / "checkpoint_visited.json"))
        queue = _carregar_queue_raw(str(dir_c / "checkpoint_queue.json"))
        df_err = _carregar_excel_raw(str(dir_c / "erros_varredura.xlsx"))
        df_inv = _carregar_excel_raw(str(dir_c / "inventario_links.xlsx"))
        df_ext = _carregar_excel_raw(str(dir_c / "inventario_externos.xlsx"))

    # Filtra visited por domínio
    visited_validos = 0
    visited_fora = 0
    for url in visited:
        netloc = urlparse(url).netloc.lower()
        if _is_valid_domain(netloc, dominios):
            visited_validos += 1
        else:
            visited_fora += 1

    # Filtra queue por domínio e calcula maior nível
    queue_validos = 0
    max_depth = 0
    for item in queue:
        url = item.get("url", "")
        depth = item.get("depth", 0)
        if depth > max_depth:
            max_depth = depth
        netloc = urlparse(url).netloc.lower()
        if _is_valid_domain(netloc, dominios):
            queue_validos += 1

    # Filtra inventário por domínio
    arquivos_validos = 0
    if df_inv is not None and len(df_inv) > 0 and "url_encontrada" in df_inv.columns:
        for url in df_inv["url_encontrada"]:
            netloc = urlparse(str(url)).netloc.lower()
            if _is_valid_domain(netloc, dominios):
                arquivos_validos += 1

    total_erros = len(df_err) if df_err is not None else 0
    total_ext = len(df_ext) if df_ext is not None else 0

    # Maior nível: da fila, ou do inventário se fila vazia
    if max_depth == 0 and df_inv is not None and len(df_inv) > 0 and "profundidade" in df_inv.columns:
        max_depth = int(df_inv["profundidade"].max())

    total_urls_validas = visited_validos + queue_validos
    progresso = (visited_validos / total_urls_validas) if total_urls_validas > 0 else 0.0

    return {
        "cidade": cidade,
        "paginas_visitadas": visited_validos,
        "urls_na_fila": queue_validos,
        "arquivos": arquivos_validos,
        "erros": total_erros,
        "externos": total_ext,
        "maior_nivel": max_depth,
        "fora_dominios": visited_fora,
        "progresso": progresso,
        "total_urls_validas": total_urls_validas,
        "completa": completa,
    }


# =============================================================================
# SIDEBAR — MODO DE VISUALIZAÇÃO
# =============================================================================

st.set_page_config(
    page_title="Visualizador de Checkpoint — Crawler TCC",
    page_icon="🕷️",
    layout="wide",
)

# Auto-rerun a cada 10 segundos (pode ser desativado na sidebar)
auto_rerun = st.sidebar.checkbox("Atualizar a cada 1 min", value=True)
if auto_rerun:
    st_autorefresh(interval=60_000, key="autorefresh")

st.sidebar.title("Configuração")

modo = st.sidebar.radio(
    "Modo de visualização",
    options=["Dashboard", "Resultados", "Cidade individual"],
    index=0,
)

usar_oficial = st.sidebar.checkbox(
    f"Usar pasta '{SUFIXO_PASTA}' (dados oficiais)",
    value=False,
    help=f"Se marcado, lê de 'CIDADE{SUFIXO_PASTA}'. Caso contrário, lê de 'CIDADE'.",
)

# =============================================================================
# MODO DASHBOARD — VISÃO GERAL DE TODAS AS CIDADES
# =============================================================================

if modo == "Dashboard":
    st.title("🕷️ Dashboard — Progresso por Município")
    st.caption(f"Total de cidades configuradas: {len(CIDADES)}")

    with st.spinner("Carregando métricas de todas as cidades..."):
        metricas = []
        for cidade in CIDADES:
            m = carregar_metricas_cidade(cidade, usar_oficial)
            if m is not None:
                metricas.append(m)
            else:
                metricas.append({
                    "cidade": cidade,
                    "pasta": "",
                    "paginas_visitadas": 0,
                    "urls_na_fila": 0,
                    "arquivos": 0,
                    "erros": 0,
                    "externos": 0,
                    "ultimo_nivel_arquivos": 0,
                    "progresso": 0.0,
                    "total_urls": 0,
                    "completa": False,
                })

    df_dash = pd.DataFrame(metricas)
    cidades_com_dados = len(df_dash[df_dash["paginas_visitadas"] > 0])
    cidades_nao_processadas = len(df_dash) - cidades_com_dados

    # Métricas globais
    col_g1, col_g2, col_g3, col_g4, col_g5, col_g6 = st.columns(6)
    col_g1.metric("Total de Cidades", f"{len(df_dash)}")
    col_g2.metric("Com Dados", f"{cidades_com_dados}")
    col_g3.metric("Não Processadas", f"{cidades_nao_processadas}")
    col_g4.metric("Páginas Visitadas", f"{df_dash['paginas_visitadas'].sum():,}")
    col_g5.metric("Arquivos", f"{df_dash['arquivos'].sum():,}")
    col_g6.metric("Erros", f"{df_dash['erros'].sum():,}")

    st.divider()

    # Filtros
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        busca_dash = st.text_input("Buscar cidade", key="busca_dash")
    with col_f2:
        filtro_status = st.selectbox(
            "Filtrar por status",
            options=["Todas", "Com dados", "Não processadas"],
            key="filtro_status",
        )

    df_filtrado = df_dash.copy()
    if busca_dash:
        df_filtrado = df_filtrado[
            df_filtrado["cidade"].str.contains(busca_dash, case=False, na=False)
        ]
    if filtro_status == "Com dados":
        df_filtrado = df_filtrado[df_filtrado["paginas_visitadas"] > 0]
    elif filtro_status == "Não processadas":
        df_filtrado = df_filtrado[df_filtrado["paginas_visitadas"] == 0]

    st.subheader(f"Progresso por Cidade ({len(df_filtrado)} municípios)")

    # Tabela com progresso
    df_tabela = df_filtrado.copy()
    df_tabela["progresso_pct"] = df_tabela["progresso"].apply(
        lambda x: f"{x:.1%}" if x > 0 else "—"
    )
    df_tabela["status"] = df_tabela.apply(
        lambda row: "✅ Processada" if row["completa"] else "⚠️ Processando..." if row["paginas_visitadas"] > 0 else "⏳ Pendente",
        axis=1,
    )
    # df_tabela["status"] = df_tabela["paginas_visitadas"].apply(
    #    lambda x: "✅ Processada" if x > 0 else "⏳ Pendente"
    #)
    df_tabela = df_tabela.rename(columns={
        "cidade": "Cidade",
        "paginas_visitadas": "Páginas",
        "urls_na_fila": "Fila",
        "arquivos": "Arquivos",
        "erros": "Erros",
        "externos": "Externos",
        "ultimo_nivel_arquivos": "Últ. Nível",
        "progresso_pct": "Progresso",
    })
    df_tabela = df_tabela[[
        "Cidade", "status", "Páginas", "Fila", "Arquivos", "Erros", "Externos", "Últ. Nível", "Progresso"
    ]]

    st.dataframe(
        df_tabela,
        use_container_width=True,
        height=min(600, len(df_tabela) * 35 + 40),
        hide_index=True,
    )

    st.divider()

    # Gráficos
    col_graf1, col_graf2 = st.columns(2)

    with col_graf1:
        st.subheader("Top 15 Cidades por Páginas Visitadas")
        top_paginas = df_filtrado.nlargest(15, "paginas_visitadas")
        if len(top_paginas) > 0:
            chart_data = top_paginas.set_index("cidade")["paginas_visitadas"]
            st.bar_chart(chart_data, use_container_width=True)
        else:
            st.info("Sem dados para exibir.")

    with col_graf2:
        st.subheader("Top 15 Cidades por Arquivos Encontrados")
        top_arquivos = df_filtrado.nlargest(15, "arquivos")
        if len(top_arquivos) > 0:
            chart_data = top_arquivos.set_index("cidade")["arquivos"]
            st.bar_chart(chart_data, use_container_width=True)
        else:
            st.info("Sem dados para exibir.")

    st.divider()

    # Barras de progresso individuais
    st.subheader("Progresso Detalhado")
    for _, row in df_filtrado.iterrows():
        cidade_nome = row["cidade"].capitalize()
        prog = row["progresso"]
        vis = int(row["paginas_visitadas"])
        fila = int(row["urls_na_fila"])
        arq = int(row["arquivos"])
        err = int(row["erros"])
        st.write(
            f"**{cidade_nome}** — {vis:,} páginas | {arq:,} arquivos | {err} erros | {fila:,} na fila"
        )
        if row["total_urls"] > 0:
            st.progress(prog, text=f"{prog:.1%}")
        else:
            st.progress(0, text="Sem dados")

    st.stop()


# =============================================================================
# MODO RESULTADOS — MÉTRICAS FILTRADAS POR DOMÍNIO
# =============================================================================

if modo == "Resultados":
    st.title("📊 Resultados — Métricas por Domínios Permitidos")
    st.caption("Apenas URLs de domínios permitidos são contabilizadas em Páginas, Fila e Arquivos.")

    with st.spinner("Carregando métricas filtradas de todas as cidades..."):
        metricas = []
        for cidade in CIDADES:
            m = carregar_metricas_filtradas(cidade, usar_oficial)
            if m is not None:
                metricas.append(m)

    if not metricas:
        st.info("Nenhuma cidade com dados encontrada.")
        st.stop()

    df_res = pd.DataFrame(metricas)
    cidades_com_dados = len(df_res[df_res["paginas_visitadas"] > 0])

    # Métricas globais
    col_g1, col_g2, col_g3, col_g4, col_g5 = st.columns(5)
    col_g1.metric("Cidades com Dados", f"{cidades_com_dados}")
    col_g2.metric("Páginas Válidas", f"{df_res['paginas_visitadas'].sum():,}")
    col_g3.metric("Arquivos Válidos", f"{df_res['arquivos'].sum():,}")
    col_g4.metric("Fora dos Domínios", f"{df_res['fora_dominios'].sum():,}")
    col_g5.metric("Erros", f"{df_res['erros'].sum():,}")

    st.divider()

    # Filtros
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        busca_res = st.text_input("Buscar cidade", key="busca_res")
    with col_f2:
        filtro_status_res = st.selectbox(
            "Filtrar por status",
            options=["Todas", "Com dados", "Não processadas"],
            key="filtro_status_res",
        )

    df_res_f = df_res.copy()
    if busca_res:
        df_res_f = df_res_f[
            df_res_f["cidade"].str.contains(busca_res, case=False, na=False)
        ]
    if filtro_status_res == "Com dados":
        df_res_f = df_res_f[df_res_f["paginas_visitadas"] > 0]
    elif filtro_status_res == "Não processadas":
        df_res_f = df_res_f[df_res_f["paginas_visitadas"] == 0]

    st.subheader(f"Métricas por Cidade ({len(df_res_f)} municípios)")

    # Tabela
    df_tabela = df_res_f.copy()
    df_tabela["progresso_pct"] = df_tabela["progresso"].apply(
        lambda x: f"{x:.1%}" if x > 0 else "—"
    )
    df_tabela["status"] = df_tabela.apply(
        lambda row: "✅ Concluída" if row["completa"] else "⚠️ Processando" if row["paginas_visitadas"] > 0 else "⏳ Pendente",
        axis=1,
    )
    df_tabela = df_tabela.rename(columns={
        "cidade": "Cidade",
        "status": "Status",
        "paginas_visitadas": "Páginas",
        "urls_na_fila": "Fila",
        "arquivos": "Arquivos",
        "externos": "Externos",
        "erros": "Erros",
        "maior_nivel": "Maior Nível",
        "fora_dominios": "Fora Domínios",
        "progresso_pct": "Progresso",
    })
    df_tabela = df_tabela[[
        "Cidade", "Status", "Progresso", "Páginas", "Fila", "Arquivos",
        "Externos", "Erros", "Maior Nível", "Fora Domínios",
    ]]

    st.dataframe(
        df_tabela,
        use_container_width=True,
        height=min(600, len(df_tabela) * 35 + 40),
        hide_index=True,
    )

    st.divider()

    # Gráficos
    df_graf = df_res_f[df_res_f["paginas_visitadas"] > 0].copy()

    col_graf1, col_graf2 = st.columns(2)
    with col_graf1:
        st.subheader("Top 15 Cidades por Páginas Visitadas (domínios válidos)")
        top_pag = df_graf.nlargest(15, "paginas_visitadas")
        if len(top_pag) > 0:
            st.bar_chart(top_pag.set_index("cidade")["paginas_visitadas"], use_container_width=True)
        else:
            st.info("Sem dados para exibir.")

    with col_graf2:
        st.subheader("Top 15 Cidades por Arquivos (domínios válidos)")
        top_arq = df_graf.nlargest(15, "arquivos")
        if len(top_arq) > 0:
            st.bar_chart(top_arq.set_index("cidade")["arquivos"], use_container_width=True)
        else:
            st.info("Sem dados para exibir.")

    col_graf3, col_graf4 = st.columns(2)
    with col_graf3:
        st.subheader("Top 15 Cidades — Links Fora dos Domínios Permitidos")
        top_fora = df_graf.nlargest(15, "fora_dominios")
        if len(top_fora) > 0:
            st.bar_chart(top_fora.set_index("cidade")["fora_dominios"], use_container_width=True)
        else:
            st.info("Sem dados para exibir.")

    with col_graf4:
        st.subheader("Distribuição de Conclusão")
        df_concl = df_res_f[df_res_f["total_urls_validas"] > 0].copy()
        if len(df_concl) > 0:
            bins = [0, 0.25, 0.50, 0.75, 0.999, 1.0]
            labels = ["0–25%", "25–50%", "50–75%", "75–99%", "100%"]
            df_concl["faixa"] = pd.cut(df_concl["progresso"], bins=bins, labels=labels, include_lowest=True)
            dist = df_concl["faixa"].value_counts().reindex(labels, fill_value=0)
            st.bar_chart(dist, use_container_width=True)
        else:
            st.info("Sem dados para exibir.")

    st.stop()


# =============================================================================
# MODO CIDADE INDIVIDUAL — SELEÇÃO
# =============================================================================

cidade_sel = st.sidebar.selectbox(
    "Cidade",
    options=list(CIDADES.keys()),
    format_func=lambda c: c.capitalize(),
)

# Define a pasta de resultados
pasta_cidade = cidade_sel + (SUFIXO_PASTA if usar_oficial else "")
dir_cidade = DIR_RESULTADOS / pasta_cidade

# Caminhos dos arquivos
caminho_visited = dir_cidade / "checkpoint_visited.json"
caminho_queue = dir_cidade / "checkpoint_queue.json"
caminho_erros = dir_cidade / "erros_varredura.xlsx"
caminho_inventario = dir_cidade / "inventario_links.xlsx"
caminho_externos  = dir_cidade / "inventario_externos.xlsx"

st.sidebar.divider()
st.sidebar.caption(f"📁 Pasta: `{dir_cidade}`")

# Indica quais arquivos existem
arquivos_status = {
    "checkpoint_visited.json": caminho_visited.exists(),
    "checkpoint_queue.json": caminho_queue.exists(),
    "erros_varredura.xlsx": caminho_erros.exists(),
    "inventario_links.xlsx": caminho_inventario.exists(),
    "inventario_externos.xlsx": caminho_externos.exists(),
}
for nome, existe in arquivos_status.items():
    icone = "✅" if existe else "❌"
    st.sidebar.caption(f"{icone} {nome}")

# =============================================================================
# CARREGAR DADOS
# =============================================================================

if not dir_cidade.exists():
    st.error(f"Pasta de resultados não encontrada: `{dir_cidade}`")
    st.info("Execute o crawler antes de visualizar o checkpoint.")
    st.stop()

with st.spinner("Carregando dados do checkpoint..."):
    # Cidade completa → cache; em execução → sem cache (dados frescos)
    completa = _cidade_completa(dir_cidade)
    if completa:
        visited_list = carregar_visited(str(caminho_visited))
        queue_list = carregar_queue(str(caminho_queue))
        df_erros = carregar_excel(str(caminho_erros))
        df_inventario = carregar_excel(str(caminho_inventario))
        df_externos = carregar_excel(str(caminho_externos))
    else:
        visited_list = _carregar_visited_raw(str(caminho_visited))
        queue_list = _carregar_queue_raw(str(caminho_queue))
        df_erros = _carregar_excel_raw(str(caminho_erros))
        df_inventario = _carregar_excel_raw(str(caminho_inventario))
        df_externos = _carregar_excel_raw(str(caminho_externos))

total_visited = len(visited_list)
total_queue = len(queue_list)
total_erros = len(df_erros) if df_erros is not None else 0
total_inventario = len(df_inventario) if df_inventario is not None else 0
total_externos = len(df_externos) if df_externos is not None else 0

# =============================================================================
# TÍTULO
# =============================================================================

st.title(f"🕷️ Visualizador de Checkpoint — {cidade_sel.capitalize()}")
st.caption(f"Pasta: `{dir_cidade}`")

# =============================================================================
# ESTATÍSTICAS DO MUNICÍPIO
# =============================================================================

st.header("Estatísticas do Município")

# Profundidade configurada
profundidade_config = MAX_DEPTH

# Último nível com arquivos
if df_inventario is not None and total_inventario > 0 and "profundidade" in df_inventario.columns:
    ultimo_nivel_arquivos = int(df_inventario["profundidade"].max())
else:
    ultimo_nivel_arquivos = 0

col1, col2, col3, col4, col5, col6 = st.columns(6)
col1.metric("Páginas Visitadas", f"{total_visited:,}")
col2.metric("Profundidade Configurada", f"{profundidade_config}")
col3.metric("Último Nível com Arquivos", f"{ultimo_nivel_arquivos}")
col4.metric("Arquivos Encontrados", f"{total_inventario:,}")
col5.metric("Erros Registrados", f"{total_erros:,}")
col6.metric("Links Externos", f"{total_externos:,}")

total_urls = total_visited + total_queue
if total_urls > 0:
    progresso = total_visited / total_urls
    st.progress(progresso, text=f"Progresso estimado: {progresso:.1%} ({total_visited:,} de {total_urls:,} URLs)")

st.divider()

# =============================================================================
# DISTRIBUIÇÃO DE ARQUIVOS POR GRUPO
# =============================================================================

st.header("Distribuição de Arquivos por Grupo")

GRUPOS_ARQUIVO = {
    "Planilhas": [".xls", ".xlsx", ".xlsm", ".ods"],
    "Documentos": [".pdf", ".doc", ".docx", ".docm", ".odt", ".rtf", ".txt"],
    "Apresentações": [".ppt", ".pptx", ".ppsx"],
    "Geoespaciais": [".dwg", ".kmz"],
}

if df_inventario is not None and total_inventario > 0 and "tipo_arquivo" in df_inventario.columns:
    exts = df_inventario["tipo_arquivo"].str.lower().str.strip()
    contagem_grupos = {}
    for grupo, ext_lista in GRUPOS_ARQUIVO.items():
        contagem_grupos[grupo] = int(exts.isin(ext_lista).sum())
    contagem_grupos["Outros"] = int(total_inventario - sum(contagem_grupos.values()))

    df_grupos = pd.DataFrame(
        [{"Grupo": g, "Quantidade": q} for g, q in contagem_grupos.items() if q > 0]
    )

    col_grp_graf, col_grp_dados = st.columns([2, 1])

    with col_grp_graf:
        st.bar_chart(df_grupos.set_index("Grupo"), use_container_width=True)

    with col_grp_dados:
        st.subheader("Detalhamento")
        for grupo, qtd in contagem_grupos.items():
            if qtd > 0:
                pct = qtd / total_inventario * 100
                st.write(f"**{grupo}**: {qtd:,} ({pct:.1f}%)")
else:
    st.info("Nenhum arquivo inventariado para distribuir por grupo.")

st.divider()

# =============================================================================
# FILA DE PROCESSAMENTO
# =============================================================================

st.header("📥 Fila de Processamento")

if total_queue == 0:
    st.info("Nenhum URL na fila — varredura concluída ou ainda não iniciada.")
else:
    df_queue = pd.DataFrame(queue_list)

    # Filtro por profundidade
    prof_min, prof_max = int(df_queue["depth"].min()), int(df_queue["depth"].max())
    prof_range = st.slider(
        "Filtrar por profundidade",
        min_value=prof_min,
        max_value=prof_max,
        value=(prof_min, prof_max),
        key="filtro_prof_fila",
    )
    df_queue_filtrada = df_queue[
        (df_queue["depth"] >= prof_range[0]) & (df_queue["depth"] <= prof_range[1])
    ]

    # Busca por texto
    busca_fila = st.text_input("Buscar URL (contém)", key="busca_fila")
    if busca_fila:
        df_queue_filtrada = df_queue_filtrada[
            df_queue_filtrada["url"].str.contains(busca_fila, case=False, na=False)
        ]

    col_graf, col_tabela = st.columns([1, 2])

    with col_graf:
        st.subheader("Distribuição por Profundidade")
        dist_prof = df_queue["depth"].value_counts().sort_index()
        st.bar_chart(dist_prof, use_container_width=True)

    with col_tabela:
        st.subheader(f"URLs na Fila ({len(df_queue_filtrada):,})")
        st.dataframe(
            df_queue_filtrada,
            column_config={
                "url": "URL",
                "depth": st.column_config.NumberColumn("Profundidade", width="small"),
            },
            use_container_width=True,
            height=400,
        )

st.divider()

# =============================================================================
# URLS VISITADAS
# =============================================================================

st.header("✅ URLs Visitadas")

if total_visited == 0:
    st.info("Nenhuma URL visitada ainda.")
else:
    df_visited = pd.DataFrame({"url": visited_list})

    busca_vis = st.text_input("Buscar URL (contém)", key="busca_vis")
    df_vis_filtrada = df_visited
    if busca_vis:
        df_vis_filtrada = df_visited[
            df_visited["url"].str.contains(busca_vis, case=False, na=False)
        ]

    st.subheader(f"URLs Visitadas ({len(df_vis_filtrada):,} de {total_visited:,})")
    st.dataframe(
        df_vis_filtrada,
        column_config={"url": "URL"},
        use_container_width=True,
        height=400,
    )

st.divider()

# =============================================================================
# ERROS DE VARREDURA
# =============================================================================

st.header("❌ Erros de Varredura")

if df_erros is None or total_erros == 0:
    st.info("Nenhum erro registrado.")
else:
    col_err_graf, col_err_tabela = st.columns([1, 2])

    with col_err_graf:
        st.subheader("Erros por Tipo")
        dist_erros = df_erros["tipo_erro"].value_counts()
        st.bar_chart(dist_erros, use_container_width=True)

    with col_err_tabela:
        st.subheader("Detalhes dos Erros")

        # Filtro por tipo de erro
        tipos_disponiveis = sorted(df_erros["tipo_erro"].dropna().unique().tolist())
        tipos_sel = st.multiselect(
            "Filtrar por tipo de erro",
            options=tipos_disponiveis,
            default=tipos_disponiveis,
            key="filtro_tipo_erro",
        )

        df_erros_filtrado = df_erros[df_erros["tipo_erro"].isin(tipos_sel)]

        st.dataframe(
            df_erros_filtrado,
            column_config={
                "cidade": "Cidade",
                "url_bloqueada": "URL",
                "tipo_erro": "Tipo de Erro",
                "status_http": st.column_config.NumberColumn("Status HTTP", width="small"),
                "profundidade": st.column_config.NumberColumn("Profundidade", width="small"),
                "data_hora": "Data/Hora",
            },
            use_container_width=True,
            height=400,
        )

st.divider()

# =============================================================================
# INVENTÁRIO DE ARQUIVOS
# =============================================================================

st.header("📄 Inventário de Arquivos")

if df_inventario is None or total_inventario == 0:
    st.info("Nenhum arquivo inventariado.")
else:
    col_inv_graf, col_inv_tabela = st.columns([1, 2])

    with col_inv_graf:
        st.subheader("Top 10 Tipos de Arquivo")
        top_tipos = df_inventario["tipo_arquivo"].value_counts().head(10)
        st.bar_chart(top_tipos, use_container_width=True)

    with col_inv_tabela:
        st.subheader("Arquivos Inventariados")

        # Filtros
        col_f1, col_f2 = st.columns(2)

        with col_f1:
            tipos_arquivo = sorted(df_inventario["tipo_arquivo"].dropna().unique().tolist())
            tipos_arq_sel = st.multiselect(
                "Filtrar por tipo",
                options=tipos_arquivo,
                default=[],
                key="filtro_tipo_arq",
            )

        with col_f2:
            busca_inv = st.text_input("Buscar URL (contém)", key="busca_inv")

        df_inv_filtrado = df_inventario
        if tipos_arq_sel:
            df_inv_filtrado = df_inv_filtrado[df_inv_filtrado["tipo_arquivo"].isin(tipos_arq_sel)]
        if busca_inv:
            df_inv_filtrado = df_inv_filtrado[
                df_inv_filtrado["url_encontrada"].str.contains(busca_inv, case=False, na=False)
            ]

        st.caption(f"{len(df_inv_filtrado):,} de {total_inventario:,} arquivos")

        st.dataframe(
            df_inv_filtrado,
            column_config={
                "cidade": "Cidade",
                "url_encontrada": "URL",
                "dominio_encontrado": "Domínio",
                "texto_no_site": "Texto no Site",
                "pagina_de_origem": "Página de Origem",
                "tipo_arquivo": "Tipo",
                "profundidade": st.column_config.NumberColumn("Profundidade", width="small"),
                "status_http": st.column_config.NumberColumn("Status HTTP", width="small"),
                "data_varredura": "Data",
            },
            use_container_width=True,
            height=400,
        )

st.divider()

# =============================================================================
# LINKS EXTERNOS
# =============================================================================

st.header("🔗 Links Externos")

if df_externos is None or total_externos == 0:
    st.info("Nenhum link externo registrado.")
else:
    col_ext_graf, col_ext_tabela = st.columns([1, 2])

    with col_ext_graf:
        st.subheader("Top 10 Domínios Externos")
        if "dominio_encontrado" in df_externos.columns:
            top_dominios = df_externos["dominio_encontrado"].value_counts().head(10)
            st.bar_chart(top_dominios, use_container_width=True)

    with col_ext_tabela:
        st.subheader("Links Externos Registrados")

        busca_ext = st.text_input("Buscar URL (contém)", key="busca_ext")
        df_ext_filtrado = df_externos
        if busca_ext:
            df_ext_filtrado = df_externos[
                df_externos["url_encontrada"].str.contains(busca_ext, case=False, na=False)
            ]

        st.caption(f"{len(df_ext_filtrado):,} de {total_externos:,} links externos")

        st.dataframe(
            df_ext_filtrado,
            column_config={
                "cidade": "Cidade",
                "url_encontrada": "URL",
                "dominio_encontrado": "Domínio",
                "texto_no_site": "Texto no Site",
                "pagina_de_origem": "Página de Origem",
                "profundidade": st.column_config.NumberColumn("Profundidade", width="small"),
                "data_varredura": "Data",
            },
            use_container_width=True,
            height=400,
        )