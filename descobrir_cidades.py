# =============================================================================
# descobrir_cidades.py — Descoberta Automática de Portais Municipais
# TCC: Mapeamento de Dados Públicos no Paraná — Perspectivas de Gênero
# UTFPR — Adriana Sarturi
# =============================================================================
#
# Script genérico para descobrir portais de prefeituras municipais:
#   1. Consulta a API do IBGE para listar municípios de um estado
#   2. Opcionalmente raspa uma página com links oficiais das prefeituras
#   3. Usa padrão de slug (www.{cidade}.{uf}.gov.br) como fallback
#   4. Testa portais de transparência e dados abertos
#   5. Salva as URLs válidas em cidades.json
#
# Como usar:
#   python descobrir_cidades.py --estado pr
#   python descobrir_cidades.py --estado pr --pagina-prefeituras "https://www.parana.pr.gov.br/Pagina/Sites-das-Prefeituras-e-Camaras-Municipais"
#   python descobrir_cidades.py --estado pr --limite 50 --dry-run
#   python descobrir_cidades.py --estado sp --timeout 5
#
# =============================================================================

import argparse
import json
import re
import time
from pathlib import Path
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

try:
    from duckduckgo_search import DDGS
    _DDGS_DISPONIVEL = True
except ImportError:
    _DDGS_DISPONIVEL = False


# =============================================================================
# CONSTANTES
# =============================================================================

IBGE_API_BASE = "https://servicodados.ibge.gov.br/api/v1/localidades/estados"

DIR_RAIZ = Path(__file__).parent
ARQUIVO_CIDADES = DIR_RAIZ / "cidades.json"

# Padrões de URL para gerar candidatos (estado = sigla da UF, ex: pr, sp, rj)
PADRAO_PREFEITURA = "https://www.{slug}.{estado}.gov.br/"
PADRAO_TRANSPARENCIA = "https://www.transparencia.{slug}.{estado}.gov.br/"
PADRAO_DADOS_ABERTOS = "https://dadosabertos.{slug}.{estado}.gov.br/"

# Subdomínios alternativos comuns
SUBDOMINIOS_ALTERNATIVOS = ["portal", "www2", "www3"]

# Headers para identificação ética
HEADERS = {
    "User-Agent": (
        "CrawlerTCC-UTFPR/1.0 "
        "(Pesquisa academica - Descoberta de portais municipais; "
        "Engenharia de Software UTFPR; "
        "contato: adrianasarturi@alunos.utfpr.edu.br)"
    )
}

# Mapeamento sigla → código IBGE do estado
_SIGLAS_PARA_CODIGO = {
    "ac": 12, "al": 27, "ap": 16, "am": 13, "ba": 29,
    "ce": 23, "df": 53, "es": 32, "go": 52, "ma": 21,
    "mt": 51, "ms": 50, "mg": 31, "pa": 15, "pb": 25,
    "pr": 41, "pe": 26, "pi": 22, "rj": 33, "rn": 24,
    "rs": 43, "ro": 11, "rr": 14, "sc": 42, "sp": 35,
    "se": 28, "to": 17,
}


# =============================================================================
# NORMALIZAÇÃO DE NOME → SLUG DE URL
# =============================================================================

def nome_para_slug(nome: str) -> str:
    """
    Converte nome de município para slug de URL.

    Exemplos:
      "São José dos Pinhais" → "saojosedospinhais"
      "Pinhão"               → "pinhao"
    """
    nome = nome.lower()
    substituicoes = {
        "á": "a", "à": "a", "ã": "a", "â": "a",
        "é": "e", "ê": "e",
        "í": "i",
        "ó": "o", "ô": "o", "õ": "o",
        "ú": "u", "û": "u",
        "ç": "c",
        "ñ": "n",
    }
    for acentuado, simples in substituicoes.items():
        nome = nome.replace(acentuado, simples)

    nome = re.sub(r"[-\s'\".]", "", nome)
    return nome


# =============================================================================
# CONSULTA IBGE
# =============================================================================

def listar_municipios_ibge(estado_sigla: str) -> list[dict]:
    """
    Consulta a API do IBGE e retorna lista de municípios do estado.
    Cada item: {"nome": "Curitiba", "id": 4106902, ...}
    """
    sigla = estado_sigla.lower()
    if sigla not in _SIGLAS_PARA_CODIGO:
        print(f"  ERRO: sigla de estado inválida '{estado_sigla}'. Use: {', '.join(sorted(_SIGLAS_PARA_CODIGO))}")
        return []

    codigo = _SIGLAS_PARA_CODIGO[sigla]
    url = f"{IBGE_API_BASE}/{codigo}/municipios"
    print(f"Consultando IBGE — municípios de {sigla.upper()} (código {codigo})...")
    try:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        municipios = resp.json()
        print(f"  {len(municipios)} municípios encontrados.")
        return municipios
    except Exception as e:
        print(f"  ERRO ao consultar IBGE: {e}")
        return []


# =============================================================================
# RASPAGEM DE PÁGINA COM LINKS DAS PREFEITURAS
# =============================================================================

def raspar_sites_prefeituras(url_pagina: str, dominio_pagina: str) -> dict[str, str]:
    """
    Raspa uma página que lista links para sites das prefeituras.

    A página deve conter links <a> onde o texto é o nome da cidade
    e o href é a URL do site da prefeitura.

    Parâmetros:
      url_pagina: URL da página a ser raspada
      dominio_pagina: domínio da própria página (para filtrar links de navegação)

    Retorna um dict {nome_normalizado: url} onde nome_normalizado é o
    nome da cidade em minúsculo sem espaços/acentos — para match com IBGE.
    """
    print(f"Raspando página de prefeituras: {url_pagina}")

    # Alguns servidores governamentais rejeitam User-Agens de bots.
    # Tenta primeiro com headers de navegador; se falhar, tenta com
    # o User-Agent acadêmico do projeto.
    headers_browser = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/125.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
        "Connection": "keep-alive",
    }

    resp = None
    for label, hdrs in [("navegador", headers_browser), ("acadêmico", HEADERS)]:
        try:
            resp = requests.get(url_pagina, headers=hdrs, timeout=30, verify=False)
            resp.raise_for_status()
            print(f"  Página carregada com headers {label}.")
            break
        except Exception as e:
            print(f"  Tentativa com headers {label} falhou: {e}")
            resp = None

    if resp is None:
        print(f"  ERRO: não foi possível carregar a página após 2 tentativas.")
        return {}

    soup = BeautifulSoup(resp.text, "html.parser")
    mapping = {}

    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"].strip()
        texto = a_tag.get_text(strip=True)

        if not href or not texto:
            continue
        if href.startswith("#") or href.startswith("javascript"):
            continue
        # Filtra links internos da própria página (navegação, menu, etc.)
        if dominio_pagina in href:
            continue
        if not href.startswith("http"):
            continue

        nome_norm = nome_para_slug(texto)
        if nome_norm and href:
            mapping[nome_norm] = href

    print(f"  {len(mapping)} prefeituras encontradas na página.")
    return mapping


# =============================================================================
# BUSCA NO DUCKDUCKGO
# =============================================================================

def _scraping_ddg_html(query: str, max_resultados: int) -> list[str]:
    """Scraping direto do HTML do DuckDuckGo via POST (mais resistente a rate limit)."""
    urls = []
    resp = requests.post(
        "https://html.duckduckgo.com/html/",
        data={"q": query},
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/125.0.0.0 Safari/537.36"
            )
        },
        timeout=15,
        verify=False,
    )
    # Detecta CAPTCHA/bloqueio
    if "anomaly" in resp.text.lower() or resp.status_code == 202:
        return []
    soup = BeautifulSoup(resp.text, "html.parser")
    for a in soup.find_all("a", class_="result__a", href=True):
        href = a["href"]
        if "uddg=" in href:
            from urllib.parse import parse_qs, urlparse as _urlparse
            params = parse_qs(_urlparse(href).query)
            if "uddg" in params:
                urls.append(params["uddg"][0])
        elif href.startswith("http"):
            urls.append(href)
        if len(urls) >= max_resultados:
            break
    return urls


def _buscar_google(query: str, max_resultados: int) -> list[str]:
    """Fallback: usa biblioteca googlesearch-python."""
    try:
        from googlesearch import search as gsearch
        results = list(gsearch(query, num_results=max_resultados, lang="pt-br"))
        return [u for u in results if u.startswith("http")]
    except Exception:
        return []


def buscar_duckduckgo(query: str, max_resultados: int = 5) -> list[str]:
    """
    Faz uma busca web e retorna uma lista de URLs.

    Estratégia (em ordem):
    1. Scraping HTML do DuckDuckGo via POST (mais resistente a rate limit)
    2. Biblioteca duckduckgo_search (DDGS) como fallback
    3. Fallback: googlesearch-python
    4. Fallback: Google scraping direto
    """
    urls = []

    # Tentativa 1: scraping HTML via POST (mais confiável)
    try:
        urls = _scraping_ddg_html(query, max_resultados)
        if urls:
            return urls[:max_resultados]
    except Exception:
        pass

    # Tentativa 2: biblioteca duckduckgo_search
    if _DDGS_DISPONIVEL:
        try:
            with DDGS() as ddgs:
                for r in ddgs.text(query, max_results=max_resultados):
                    url = r.get("href") or r.get("link") or ""
                    if url and url.startswith("http"):
                        urls.append(url)
            if urls:
                return urls[:max_resultados]
        except Exception:
            pass

    # Tentativa 3: retry do scraping POST com espera
    for tentativa in range(2):
        if tentativa > 0:
            espera = 5 + tentativa * 5
            print(f"\n  (DuckDuckGo bloqueou — aguardando {espera}s...)", end="", flush=True)
            time.sleep(espera)
        try:
            urls = _scraping_ddg_html(query, max_resultados)
            if urls:
                return urls[:max_resultados]
        except Exception:
            pass

    # Tentativa 4: fallback Google (googlesearch-python)
    if not urls:
        print(f"\n  (tentando Google...)", end="", flush=True)
        urls = _buscar_google(query, max_resultados)
        if urls:
            return urls[:max_resultados]

    # Tentativa 5: fallback Google scraping direto
    if not urls:
        try:
            from urllib.parse import quote
            resp = requests.get(
                f"https://www.google.com/search?q={quote(query)}&hl=pt-BR&num=10",
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
                    "Accept": "text/html,application/xhtml+xml",
                    "Accept-Language": "pt-BR,pt;q=0.9",
                },
                timeout=15,
                verify=False,
                cookies={"CONSENT": "YES+"},
            )
            import re as _re
            found = _re.findall(r'/url\?q=(https?://[^&"]+)', resp.text)
            seen = set()
            for u in found:
                if u not in seen and "google" not in u:
                    seen.add(u)
                    urls.append(u)
                if len(urls) >= max_resultados:
                    break
        except Exception:
            pass

    return urls[:max_resultados]


def descobrir_portais_por_busca(
    nome: str,
    estado_sigla: str,
    timeout: int,
    apenas_inventario: bool = False,
    sementes_config=None,
    dominios_config=None,
) -> tuple:
    """
    Busca portais da prefeitura e da transparência via DuckDuckGo.

    Deduplica por domínio (mantém apenas a URL mais curta de cada domínio).
    Exibe todos os links encontrados com marcadores:
      * = presente no inventario_externos da cidade
      + = já configurado em cidades.json
      ✅ = online  ✗ = offline

    Se apenas_inventario=True, adiciona como sementes apenas URLs que
    estão no inventario_externos da cidade (mas ainda exibe todas).

    Retorna (sementes, dominios) encontrados.
    """
    uf = estado_sigla.lower()
    slug_cidade = nome_para_slug(nome)
    dominios = set()

    # Domínios descartáveis (redes sociais, enciclopédias, agregadores genéricos)
    dominios_descartaveis = {
        "www.wikipedia.org", "wikipedia.org", "pt.wikipedia.org",
        "www.facebook.com", "facebook.com",
        "www.instagram.com", "instagram.com",
        "www.youtube.com", "youtube.com",
        "www.linkedin.com", "linkedin.com",
        "www.twitter.com", "twitter.com", "x.com",
        "duckduckgo.com",
        "www.prefeituras.org", "prefeituras.org",
        "sitesmunicipais.com.br", "www.sitesmunicipais.com.br",
        "www.cidade-brasil.com.br", "cidade-brasil.com.br",
        "www.iptu.net.br", "iptu.net.br",
        "portaldatransparencia.gov.br", "www.portaldatransparencia.gov.br",
    }

    queries = [
        f"prefeitura {nome} {uf}",
        f"portal da transparência {nome} {uf}",
    ]

    # Coleta todos os candidatos brutos
    todos_candidatos: list[str] = []
    for query in queries:
        candidatos = buscar_duckduckgo(query, max_resultados=5)
        for url in candidatos:
            if url.startswith("http://"):
                url = "https://" + url[7:]
            dominio = urlparse(url).netloc
            if dominio in dominios_descartaveis:
                continue
            todos_candidatos.append(url)
        time.sleep(5)

    # Deduplica por domínio: mantém apenas a URL mais curta de cada domínio
    por_dominio: dict[str, str] = {}
    for url in todos_candidatos:
        dominio = urlparse(url).netloc
        if dominio not in por_dominio or len(url) < len(por_dominio[dominio]):
            por_dominio[dominio] = url

    # Carrega URLs do inventario_externos da cidade (se disponível)
    urls_inventario = set()
    caminho_externos = DIR_RAIZ / "resultados" / slug_cidade / "inventario_externos.xlsx"
    if caminho_externos.exists():
        try:
            import pandas as pd
            df_ext = pd.read_excel(caminho_externos)
            if "url_encontrada" in df_ext.columns:
                urls_inventario = set(
                    df_ext["url_encontrada"].dropna().str.rstrip("/").str.lower()
                )
        except Exception:
            pass

    # Testa cada URL candidata (já deduplicada por domínio)
    sementes = []
    sementes_config = sementes_config or set()
    dominios_config = dominios_config or set()

    for dominio in sorted(por_dominio):
        url = por_dominio[dominio]
        if not url.endswith("/"):
            url += "/"
        no_inventario = url.rstrip("/").lower() in urls_inventario
        ja_configurada = url in sementes_config or dominio in dominios_config

        # Marcadores: * inventário, + configurado, ✅/✗ online
        marc_inv = "*" if no_inventario else " "
        marc_cfg = "+" if ja_configurada else " "
        online = testar_url(url, timeout)
        marc_onl = "✅" if online else "✗"
        print(f"\n           {marc_inv}{marc_cfg} {marc_onl} {url}", end="", flush=True)

        # Se apenas_inventario=True, só adiciona como semente URLs do inventário
        if apenas_inventario and not no_inventario:
            continue
        # Não re-adiciona URLs já configuradas
        if ja_configurada:
            continue
        if online:
            sementes.append(url)
            dominios.add(dominio)

    return sementes, dominios


# =============================================================================
# GERAÇÃO E TESTE DE URLs CANDIDATAS
# =============================================================================

def gerar_urls_candidatas(slug: str, estado_sigla: str) -> list[tuple[str, str]]:
    """
    Gera URLs candidatas para uma cidade.
    Retorna lista de tuplas (url, tipo) onde tipo descreve o portal.
    """
    uf = estado_sigla.lower()
    candidatos = []

    candidatos.append((PADRAO_PREFEITURA.format(slug=slug, estado=uf), "prefeitura"))
    candidatos.append((PADRAO_TRANSPARENCIA.format(slug=slug, estado=uf), "transparencia"))
    candidatos.append((PADRAO_DADOS_ABERTOS.format(slug=slug, estado=uf), "dados_abertos"))

    for sub in SUBDOMINIOS_ALTERNATIVOS:
        url = f"https://{sub}.{slug}.{uf}.gov.br/"
        candidatos.append((url, "prefeitura"))

    return candidatos


def testar_url(url: str, timeout: int = 10) -> bool:
    """
    Faz um HEAD request para testar se a URL responde.
    Retorna True se o servidor respondeu (qualquer status HTTP).
    """
    try:
        resp = requests.head(
            url,
            headers=HEADERS,
            timeout=timeout,
            allow_redirects=True,
            verify=False,
        )
        return True
    except requests.exceptions.SSLError:
        try:
            resp = requests.head(
                url,
                headers=HEADERS,
                timeout=timeout,
                allow_redirects=True,
                verify=False,
            )
            return True
        except Exception:
            return False
    except Exception:
        return False


def descobrir_portais(
    nome: str,
    estado_sigla: str,
    timeout: int,
    sites_prefeituras=None,
    buscar_web: bool = False,
    apenas_inventario: bool = False,
):
    """
    Para um município, descobre os portais disponíveis.

    Estratégia (em ordem de prioridade):
      1. URL de página oficial (se fornecida via --pagina-prefeituras)
      2. Padrão de slug + subdomínios alternativos — fallback
      3. Portais de transparência e dados abertos (sempre testados)
      4. Busca no DuckDuckGo (se buscar_web=True, ou como fallback final)
         Se apenas_inventario=True, adiciona apenas URLs encontradas
         no DuckDuckGo que também aparecem no inventario_externos da cidade.

    Retorna dict no formato do cidades.json ou None se nenhum portal responde.
    """
    uf = estado_sigla.lower()
    slug = nome_para_slug(nome)
    sementes = []
    dominios = set()

    # --- 1. Fonte oficial: página fornecida ---
    if sites_prefeituras and slug in sites_prefeituras:
        url_oficial = sites_prefeituras[slug]
        if url_oficial.startswith("http://"):
            url_oficial = "https://" + url_oficial[7:]
        if not url_oficial.endswith("/"):
            url_oficial += "/"
        if testar_url(url_oficial, timeout):
            sementes.append(url_oficial)
            dominio = urlparse(url_oficial).netloc
            dominios.add(dominio)
            if dominio.endswith(f".{uf}.gov.br"):
                dominio_base = f"{slug}.{uf}.gov.br"
                dominios.add(dominio_base)

    # --- 2. Fallback: padrão de slug ---
    if not sementes:
        candidatos = gerar_urls_candidatas(slug, uf)
        for url, tipo in candidatos:
            if testar_url(url, timeout):
                dominio = urlparse(url).netloc
                dominios.add(dominio)
                if tipo in ("prefeitura", "dados_abertos"):
                    sementes.append(url)

        if not sementes:
            for url, tipo in candidatos:
                if testar_url(url, timeout) and tipo == "transparencia":
                    sementes.append(url)
                    dominios.add(urlparse(url).netloc)
                    break

    # --- 3. Testa portais de transparência e dados abertos (complementar) ---
    url_transp = PADRAO_TRANSPARENCIA.format(slug=slug, estado=uf)
    if testar_url(url_transp, timeout):
        sementes.append(url_transp)
        dominios.add(urlparse(url_transp).netloc)

    url_dados = PADRAO_DADOS_ABERTOS.format(slug=slug, estado=uf)
    if testar_url(url_dados, timeout):
        sementes.append(url_dados)
        dominios.add(urlparse(url_dados).netloc)

    # --- 4. Busca no DuckDuckGo ---
    # Sempre busca se buscar_web=True (complementar) ou se nada encontrado (fallback)
    if buscar_web or not sementes:
        if apenas_inventario:
            print("  → buscando no DuckDuckGo (apenas inventário)...", end=" ", flush=True)
        else:
            print("  → buscando no DuckDuckGo...", end=" ", flush=True)
        bus_sementes, bus_dominios = descobrir_portais_por_busca(
            nome, estado_sigla, timeout,
            apenas_inventario=apenas_inventario,
            sementes_config=set(sementes),
            dominios_config=dominios,
        )
        sementes.extend(bus_sementes)
        dominios.update(bus_dominios)
        if bus_sementes:
            print(f"\n{len(bus_sementes)} URL(s) encontrada(s)", end=" ", flush=True)
        else:
            print("\nnenhum portal encontrado", end=" ", flush=True)

    if not sementes:
        return None

    sementes = list(dict.fromkeys(sementes))

    dominio_base = f"{slug}.{uf}.gov.br"
    dominios.add(dominio_base)

    config = {
        "sementes": sementes,
        "dominios": sorted(dominios),
    }

    return config


# =============================================================================
# SALVAMENTO EM cidades.json
# =============================================================================

def carregar_cidades_existentes() -> dict:
    """Lê o cidades.json atual, se existir."""
    if not ARQUIVO_CIDADES.exists():
        return {}
    with open(ARQUIVO_CIDADES, encoding="utf-8") as f:
        dados = json.load(f)
    return {k: v for k, v in dados.items() if not k.startswith("_")}


def salvar_cidades(cidades: dict, metadados=None):
    """Salva o dict de cidades em cidades.json, preservando metadados."""
    dados = {}
    if metadados:
        dados.update(metadados)
    dados.update(cidades)

    with open(ARQUIVO_CIDADES, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=True, indent=2)
        f.write("\n")


# =============================================================================
# MAIN
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description=(
            "Descoberta automática de portais municipais.\n"
            "Consulta o IBGE, opcionalmente raspa uma página com links das prefeituras,\n"
            "testa URLs pelo padrão de slug, e salva em cidades.json."
        ),
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "--estado",
        type=str,
        required=True,
        help=(
            "Sigla do estado (ex: pr, sp, rj, mg, rs, sc).\n"
            "Usado para consultar o IBGE e gerar URLs candidatas."
        ),
    )
    parser.add_argument(
        "--pagina-prefeituras",
        type=str,
        default=None,
        help=(
            "URL opcional de uma página que lista links das prefeituras.\n"
            "Ex PR: https://www.parana.pr.gov.br/Pagina/Sites-das-Prefeituras-e-Camaras-Municipais\n"
            "Se omitido, usa apenas o padrão de slug."
        ),
    )
    parser.add_argument(
        "--limite",
        type=int,
        default=None,
        help="Limitar número de cidades a testar (para testes rápidos)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Apenas lista resultados, não salva em cidades.json",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=10,
        help="Timeout por URL em segundos (padrão: 10)",
    )
    parser.add_argument(
        "--sobrescrever",
        action="store_true",
        default=False,
        help="Sobrescreve cidades já existentes no cidades.json",
    )
    parser.add_argument(
        "--buscar-web",
        action="store_true",
        default=False,
        help="Usa DuckDuckGo para buscar portais quando o padrão de slug falha (requer duckduckgo_search)",
    )
    parser.add_argument(
        "--apenas-inventario",
        action="store_true",
        default=False,
        help="Com --buscar-web: adiciona apenas URLs que aparecem no inventario_externos da cidade",
    )
    parser.add_argument(
        "--cidade",
        type=str,
        default=None,
        help="Processa apenas uma cidade específica (ex: abatia, curitiba)",
    )
    args = parser.parse_args()

    estado_sigla = args.estado.lower().strip()

    print(f"\n{'='*60}")
    print(f"  Descoberta de Portais Municipais — {estado_sigla.upper()}")
    print(f"{'='*60}\n")

    # 1. Lista municípios do IBGE
    municipios = listar_municipios_ibge(estado_sigla)
    if not municipios:
        print("Não foi possível obter a lista de municípios. Encerrando.")
        return

    if args.limite:
        municipios = municipios[:args.limite]
        print(f"  (Limite de teste: {args.limite} cidades)")

    if args.cidade:
        cidade_alvo = args.cidade.lower().replace(" ", "")
        municipios = [m for m in municipios if nome_para_slug(m["nome"]) == cidade_alvo
                      or m["nome"].lower().replace(" ", "") == cidade_alvo]
        if not municipios:
            print(f"  Cidade '{args.cidade}' não encontrada no IBGE para {estado_sigla.upper()}.")
            return
        print(f"  (Filtro: apenas {municipios[0]['nome']})")

    # 2. Raspa página com links oficiais (se fornecida)
    sites_prefeituras = {}
    if args.pagina_prefeituras:
        dominio_pagina = urlparse(args.pagina_prefeituras).netloc
        sites_prefeituras = raspar_sites_prefeituras(
            args.pagina_prefeituras, dominio_pagina
        )

    # 3. Carrega cidades já configuradas
    cidades_existentes = carregar_cidades_existentes()
    print(f"  Cidades já configuradas: {len(cidades_existentes)}\n")

    # 4. Descobre portais para cada município
    novas_cidades = {}
    cidades_sem_portal = []
    cidades_puladas = []
    cidades_da_pagina = 0
    cidades_por_slug = 0
    cidades_atualizadas = 0

    total = len(municipios)
    for i, muni in enumerate(municipios, 1):
        nome = muni["nome"]
        slug = nome_para_slug(nome)

        chave_existente = slug
        # Normaliza chaves existentes por slug para detectar duplicatas
        # (ex: "abatiá" e "abatia" devem ser a mesma cidade)
        chaves_existentes = {}
        for k in cidades_existentes:
            slug_k = nome_para_slug(k)
            chaves_existentes[slug_k] = k
        ja_configurada = slug in chaves_existentes
        config_existente = cidades_existentes.get(
            chaves_existentes.get(slug, ""), {}
        ) if ja_configurada else {}

        print(f"  [{i}/{total}] 🔍 {nome} (slug: {slug})...", end=" ", flush=True)

        config = descobrir_portais(
            nome,
            estado_sigla=estado_sigla,
            timeout=args.timeout,
            sites_prefeituras=sites_prefeituras if sites_prefeituras else None,
            buscar_web=args.buscar_web,
            apenas_inventario=args.apenas_inventario,
        )

        if config:
            if ja_configurada and not args.sobrescrever:
                # Mescla sementes e domínios novos na configuração existente
                sementes_existentes = set(config_existente.get("sementes", []))
                dominios_existentes = set(config_existente.get("dominios", []))
                novas_sementes = [s for s in config["sementes"] if s not in sementes_existentes]
                novos_dominios = [d for d in config["dominios"] if d not in dominios_existentes]

                if novas_sementes or novos_dominios:
                    config_final = {
                        "sementes": list(config_existente.get("sementes", [])) + novas_sementes,
                        "dominios": sorted(set(config_existente.get("dominios", []) + config["dominios"])),
                    }
                    novas_cidades[chaves_existentes[slug]] = config_final
                    cidades_atualizadas += 1
                    print(f"✅ [+{len(novas_sementes)} semente(s), +{len(novos_dominios)} domínio(s)]")
                    for s in novas_sementes:
                        print(f"           → {s}")
                else:
                    cidades_puladas.append(nome)
                    print(f"⏭️  já configurada, sem novidades")
            else:
                novas_cidades[slug] = config
                if sites_prefeituras and slug in sites_prefeituras:
                    cidades_da_pagina += 1
                    fonte = "página oficial"
                else:
                    cidades_por_slug += 1
                    fonte = "padrão de slug"
                print(f"✅ [{fonte}] {len(config['sementes'])} semente(s), {len(config['dominios'])} domínio(s)")
                for s in config["sementes"]:
                    print(f"           → {s}")
        else:
            cidades_sem_portal.append(nome)
            print("❌ nenhum portal encontrado")

        time.sleep(0.5)

    # 5. Resumo
    print(f"\n{'='*60}")
    print(f"  RESUMO — {estado_sigla.upper()}")
    print(f"{'='*60}")
    print(f"  Total testado:       {total}")
    print(f"  Novas encontradas:   {len(novas_cidades)}")
    print(f"    via página oficial: {cidades_da_pagina}")
    print(f"    via padrão de slug: {cidades_por_slug}")
    print(f"  Sem portal:          {len(cidades_sem_portal)}")
    print(f"  Já configuradas:     {len(cidades_puladas)}")
    print(f"  Atualizadas (novas sementes): {cidades_atualizadas}")

    if cidades_sem_portal:
        print(f"\n  Cidades sem portal detectado:")
        for nome in cidades_sem_portal:
            print(f"    - {nome}")

    # 6. Salva
    if args.dry_run:
        print(f"\n  --dry-run: não salvando alterações.")
    elif novas_cidades:
        cidades_finais = dict(cidades_existentes)
        cidades_finais.update(novas_cidades)

        metadados = {
            "_comentario": "Configuração das cidades-alvo do crawler. Editar este arquivo para adicionar/remover cidades ou ajustar sementes/domínios.",
            "_portais_verificados": f"Descoberto automaticamente em {time.strftime('%d/%m/%Y')}",
        }

        salvar_cidades(cidades_finais, metadados)
        novas_count = len([k for k in novas_cidades if k not in cidades_existentes])
        atualizadas_count = len(novas_cidades) - novas_count
        print(f"\n  ✅ {novas_count} nova(s) cidade(s) + {atualizadas_count} atualizada(s) salvas em {ARQUIVO_CIDADES}")
        print(f"  Total de cidades no arquivo: {len(cidades_finais)}")
    else:
        print(f"\n  Nenhuma cidade nova para salvar.")

    print(f"\n{'='*60}\n")


if __name__ == "__main__":
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    main()
