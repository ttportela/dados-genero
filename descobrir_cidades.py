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
    sites_prefeituras: dict[str, str] | None = None,
) -> dict | None:
    """
    Para um município, descobre os portais disponíveis.

    Estratégia (em ordem de prioridade):
      1. URL de página oficial (se fornecida via --pagina-prefeituras)
      2. Padrão de slug + subdomínios alternativos — fallback
      3. Portais de transparência e dados abertos (sempre testados)

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


def salvar_cidades(cidades: dict, metadados: dict | None = None):
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

    total = len(municipios)
    for i, muni in enumerate(municipios, 1):
        nome = muni["nome"]
        slug = nome_para_slug(nome)

        chave_existente = nome.lower().replace(" ", "")
        chaves_existentes = {
            k.lower().replace(" ", "") for k in cidades_existentes
        }
        if chave_existente in chaves_existentes and not args.sobrescrever:
            cidades_puladas.append(nome)
            print(f"  [{i}/{total}] ⏭️  {nome} — já configurada, pulando")
            continue

        print(f"  [{i}/{total}] 🔍 {nome} (slug: {slug})...", end=" ", flush=True)

        config = descobrir_portais(
            nome,
            estado_sigla=estado_sigla,
            timeout=args.timeout,
            sites_prefeituras=sites_prefeituras if sites_prefeituras else None,
        )

        if config:
            novas_cidades[nome.lower().replace(" ", "")] = config
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
        print(f"\n  ✅ {len(novas_cidades)} novas cidades salvas em {ARQUIVO_CIDADES}")
        print(f"  Total de cidades no arquivo: {len(cidades_finais)}")
    else:
        print(f"\n  Nenhuma cidade nova para salvar.")

    print(f"\n{'='*60}\n")


if __name__ == "__main__":
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    main()
