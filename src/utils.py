# =============================================================================
# utils.py — Funções Utilitárias Compartilhadas
# TCC: Mapeamento de Dados Públicos no Paraná — Perspectivas de Gênero
# UTFPR — Adriana Sarturi
# =============================================================================
#
# Por que este arquivo existe?
# Este módulo funciona como uma "caixa de ferramentas" para o pipeline.
# Funções de validação, tratamento de URLs e requisições HTTP seguras 
# ficam centralizadas aqui para serem importadas sob demanda pelo Crawler,
# pelo Downloader ou pelo Analisador, evitando duplicação de código.
# =============================================================================

import time
import re
import mimetypes
from urllib.parse import urlparse, urldefrag, unquote, parse_qs, urlencode

import requests

from src.config import REQUEST_TIMEOUT, MAX_RETRIES, PAUSA_ENTRE_REQUESTS, USER_AGENT


# =============================================================================
# NORMALIZAÇÃO DE URL
# =============================================================================

def normalizar_url(url: str) -> str:
    """
    Padroniza uma URL removendo fragmentos (#ancora) e garantindo que
    não haja barras duplas acidentais no caminho.

    Por que remover fragmentos?
    http://site.com/pagina e http://site.com/pagina#secao são a MESMA página
    no servidor — só diferem na navegação do browser. Sem essa normalização,
    o crawler visitaria a mesma página duas vezes.

    """
    url, _ = urldefrag(url)  # remove tudo após o '#'
    return url.strip()


# =============================================================================
# CHAVE DE DEDUPLICAÇÃO — Remove parâmetros de sessão/rastreamento
# =============================================================================
#
# Por que isso existe?
# CMSs antigos (ex: Joomla no www3.maringa.pr.gov.br) embutem tokens de sessão
# em alguns links. O mesmo conteúdo (ex: id=60) pode aparecer com centenas de
# valores de sessao= diferentes. Sem normalização, o crawler visita a mesma
# página milhares de vezes — confirmado empiricamente: 2.255 visitas a id=60.
#
# Importante: a URL COMPLETA (com sessao=) ainda é usada para o request HTTP
# — o servidor exige o token. Esta chave é usada APENAS para os sets
# visited e _urls_na_fila, garantindo deduplicação correta.
# =============================================================================

# Parâmetros que identificam sessões ou rastreamento, nunca conteúdo.
# Descobertos empiricamente nas varreduras-piloto de mai/2026.
PARAMS_IGNORADOS = {
    "sessao",        # Joomla antigo — www3.maringa.pr.gov.br
    "phpsessid",     # PHP padrão (case-insensitive)
    "jsessionid",    # Java / Tomcat
    "sid",           # genérico
    "session_id",    # genérico
    "aspsessionid",  # ASP clássico
    "utm_source",    # Google Analytics
    "utm_medium",    # Google Analytics
    "utm_campaign",  # Google Analytics
    "utm_term",      # Google Analytics
    "utm_content",   # Google Analytics
}

def url_chave_dedup(url: str) -> str:
    """
    Gera a chave de deduplicação da URL, removendo parâmetros de sessão
    e rastreamento que não identificam conteúdo.

    Exemplo:
        ?sessao=AAA&id=60  →  ?id=60   (chave)
        ?sessao=BBB&id=60  →  ?id=60   (mesma chave → deduplicado!)
        ?sessao=CCC&id=44  →  ?id=44   (chave diferente → página diferente)

    Retorna a URL sem os parâmetros ignorados. Se nenhum parâmetro relevante
    restar, retorna a URL base sem query string.
    """
    try:
        parsed = urlparse(url)
        if not parsed.query:
            return url  # sem query params — retorna como está
        params = parse_qs(parsed.query, keep_blank_values=True)
        # Filtra parâmetros ignorados (case-insensitive)
        params_limpos = {
            k: v for k, v in params.items()
            if k.lower() not in PARAMS_IGNORADOS
        }
        query_limpa = urlencode(params_limpos, doseq=True)
        return parsed._replace(query=query_limpa).geturl()
    except Exception:
        return url  # fallback: retorna URL original sem modificação


# =============================================================================
# VALIDAÇÃO DE DOMÍNIO
# =============================================================================

def is_valid_domain(url: str, dominios: list[str]) -> bool:
    """
    Verifica se a URL pertence a um dos domínios válidos da cidade.

    Usa .endswith() para cobrir subdomínios automaticamente, exemplo:
      "curitiba.pr.gov.br" cobre:

        www.curitiba.pr.gov.br           ✅
        dados.curitiba.pr.gov.br         ✅
        transparencia.curitiba.pr.gov.br ✅
        google.com                       ❌

    Recebe uma lista de domínios (e não apenas um string) para suportar
    cidades que usam sistemas terceirizados (Londrina/Equiplano, Maringá/Elotech).

    """
    try:
        netloc = urlparse(url).netloc.lower()
        return any(
            netloc == dominio.lower() or netloc.endswith("." + dominio.lower())
            for dominio in dominios
        )
    except Exception:
        return False


# =============================================================================
# IDENTIFICAÇÃO DE ARQUIVOS
# =============================================================================

# Extensões de PÁGINAS WEB — o Crawler usa estas apenas para NAVEGAR, não anota.
EXTENSOES_PAGINA_WEB = {
    ".html", ".htm", ".xhtml",
    ".php", ".asp", ".aspx", ".jsp", ".cfm",
    ".cgi", ".pl",
    ".css", ".js",
}

# TLDs (Top-Level Domains) que podem ser confundidos com extensões de arquivo.
# Ex: URL '/secretaria/conselho.gov.br' → último segmento 'conselho.gov.br'
# → rsplit dá '.br', que não está em PAGINA_WEB nem MIDIA → falso positivo.
# Inclui os TLDs mais comuns no contexto de portais governamentais brasileiros.
TLDS_FALSOS_POSITIVOS = {
    ".br", ".gov", ".com", ".org", ".net", ".edu",
    ".int", ".mil", ".inf", ".leg", ".jus",
}

# Extensões de MÍDIA — ignoradas pelo inventário.
# Imagens de notícias, ícones e logos não têm valor para pesquisa de dados.
# Vídeos e áudios também estão fora do escopo do TCC.
EXTENSOES_MIDIA = {
    # Imagens
    ".jpg", ".jpeg", ".png", ".gif", ".bmp",
    ".svg", ".webp", ".ico", ".tiff", ".tif",
    # Video
    ".mp4", ".avi", ".mov", ".wmv", ".flv", ".webm", ".mkv",
    # Audio
    ".mp3", ".wav", ".ogg", ".aac", ".flac", ".wma",
    # Fontes e assets web
    ".woff", ".woff2", ".ttf", ".eot",
}

def is_arquivo(url: str) -> bool:
    """
    Retorna True se a URL aponta para um arquivo de dados (não página web, não midia).
    """
    try:
        caminho = urlparse(url).path.lower()
        ultimo_segmento = caminho.split("/")[-1]

        # Sem extensao = pagina de navegacao (ex: /secretarias, /sobre)
        if "." not in ultimo_segmento:
            return False

        extensao = "." + ultimo_segmento.rsplit(".", 1)[-1]

        # Exclui páginas web, mídia e TLDs (falsos positivos)
        if extensao in EXTENSOES_PAGINA_WEB or extensao in EXTENSOES_MIDIA:
            return False
        if extensao in TLDS_FALSOS_POSITIVOS:
            return False

        return True

    except Exception:
        return False

def is_midia(url: str) -> bool:
    """
    Retorna True se a URL aponta para um arquivo de mídia (imagem, video, audio).

    Usado para descartar URLs que não devem ser inventariadas nem navegadas.
    Sem este check, URLs como /sistema/imagens/foto.jpg são enfileiradas
    pelo BFS como páginas a visitar, poluindo a fila e o terminal.
    """
    try:
        caminho = urlparse(url).path.lower()
        ultimo_segmento = caminho.split("/")[-1]
        if "." not in ultimo_segmento:
            return False
        extensao = "." + ultimo_segmento.rsplit(".", 1)[-1]
        return extensao in EXTENSOES_MIDIA
    except Exception:
        return False

def get_extensao(url: str) -> str:
    """
    Retorna a extensão do arquivo da URL (ex: '.xlsx', '.pdf').
    Retorna string vazia se não for um arquivo ou se a extensão tiver
    mais de 10 caracteres (indício de ID grudado na URL, ex: .pdfaaaaaa).
    """
    try:
        caminho = urlparse(url).path.lower()
        # URL-decode antes de extrair a extensão: converte %20→espaço, %C3%A7→ç, etc.
        # Sem isso, URLs malformadas como 'arquivo.pdf%20' geram extensão '.pdf%20'
        # em vez de '.pdf' (o %20 é espaço — removido automaticamente pela strip abaixo).
        ultimo_segmento = unquote(caminho.split("/")[-1]).strip()
        if "." in ultimo_segmento:
            ext = "." + ultimo_segmento.rsplit(".", 1)[-1]
            # Extensões reais têm no máximo 10 caracteres.
            # Valores maiores indicam ID de sessão grudado na URL.
            if len(ext) <= 10:
                return ext
        return ""
    except Exception:
        return ""


# =============================================================================
# MIME TYPE — Identificação pelo Content-Type do servidor
# =============================================================================
#
# Por que MIME type é superior à extensão da URL?
# A extensão da URL pode ser malformada (ex: .pdfaaaaaaa) ou ausente
# (ex: /download?id=123). O MIME type é declarado pelo próprio servidor
# no cabeçalho HTTP Content-Type, refletindo o tipo real do arquivo.
#
# Referência: https://developer.mozilla.org/en-US/docs/Web/HTTP/MIME_types
# =============================================================================

# Mapeamento dos principais MIME types para extensões legíveis.
# A chave é o início do Content-Type (antes do ";"), em minúsculas.
MIME_PARA_EXTENSAO: dict[str, str] = {
    # Documentos de texto e planilhas
    "application/pdf":                                                              ".pdf",
    "application/msword":                                                           ".doc",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document":      ".docx",
    "application/vnd.ms-excel":                                                     ".xls",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet":            ".xlsx",
    "application/vnd.ms-excel.sheet.macroenabled.12":                               ".xlsm",
    "application/vnd.oasis.opendocument.spreadsheet":                               ".ods",
    "application/vnd.oasis.opendocument.text":                                      ".odt",
    "application/vnd.ms-powerpoint":                                                ".ppt",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation":    ".pptx",
    "application/vnd.ms-powerpoint.presentation.macroenabled.12":                   ".pps",
    # Dados estruturados
    "text/csv":                                                                     ".csv",
    "text/plain":                                                                   ".txt",
    "application/json":                                                             ".json",
    "application/xml":                                                              ".xml",
    "text/xml":                                                                     ".xml",
    # Compactados
    "application/zip":                                                              ".zip",
    "application/x-rar-compressed":                                                ".rar",
    "application/vnd.rar":                                                         ".rar",
    "application/x-7z-compressed":                                                 ".7z",
    "application/gzip":                                                            ".gz",
    # Outros
    "application/rtf":                                                             ".rtf",
    "text/rtf":                                                                    ".rtf",
    # Executável Windows
    "application/x-msdownload":                                                    ".exe",
    "application/exe":                                                             ".exe",
    # AutoCAD — muito usado por secretarias de obras e planejamento urbano
    "image/vnd.dwg":                                                               ".dwg",
    "application/acad":                                                            ".dwg",
    "application/x-autocad":                                                      ".dwg",
    "application/dwg":                                                             ".dwg",
    # Assinatura digital ICP-Brasil — padrão do governo federal brasileiro
    "application/pkcs7-signature":                                                 ".p7s",
    "application/x-pkcs7-signature":                                               ".p7s",
    "application/octet-stream":                                                    "",   # genérico — usa fallback
}

def mime_para_extensao(content_type: str) -> str:
    """
    Converte o valor do cabeçalho HTTP Content-Type para uma extensão de arquivo.

    O Content-Type pode vir com parâmetros extras separados por ';', por exemplo:
        'application/pdf; charset=utf-8'
    Por isso extraímos apenas o tipo principal (antes do ';') antes de consultar
    o dicionário MIME_PARA_EXTENSAO.

    Estratégia em cascata de 3 níveis:
      1. Nosso dicionário curado (MIME_PARA_EXTENSAO) — máxima precisão e controle.
         Construído com base nos 19 tipos de arquivo encontrados na varredura de
         mais de 90.000 páginas do portal de Maringá (primeira cidade do estudo),
         cobrindo 100% dos tipos reais observados nessa amostra.
      2. Biblioteca padrão do Python (mimetypes) — cobertura ampla para tipos não
         mapeados no dicionário. Funciona como rede de segurança para tipos inesperados
         encontrados em Londrina ou Curitiba.
      3. String vazia — sinaliza ao chamador para acionar o fallback pela extensão da URL.

    Retorna a extensão (ex: '.pdf') ou string vazia se não reconhecido.
    """
    if not content_type:
        return ""
    # Pega apenas o tipo principal, sem parâmetros (charset, boundary, etc.)
    tipo_principal = content_type.split(";")[0].strip().lower()

    # Nível 1: nosso dicionário curado
    # Usa sentinela "NAOACHADO" para distinguir entre:
    #   - tipo não mapeado (não está no dict) → tenta nível 2
    #   - octet-stream mapeado como "" → retorna "" imediatamente para o fallback da URL
    resultado = MIME_PARA_EXTENSAO.get(tipo_principal, "NAOACHADO")
    if resultado != "NAOACHADO":
        return resultado

    # Nível 2: biblioteca padrão do Python
    # mimetypes.guess_extension() retorna a extensão com ponto (ex: ".pdf")
    # ou None se não reconhecer o tipo.
    ext = mimetypes.guess_extension(tipo_principal)
    if ext:
        # Validação: descarta extensões de página web retornadas pelo mimetypes.
        # Servidores mal configurados podem declarar Content-Type: text/html para
        # arquivos reais (ex: PDFs do imap.curitiba.pr.gov.br). Nesse caso, a
        # extensão da URL é mais confiável que o MIME do servidor, problema real encontrado em curitiba.
        if ext in EXTENSOES_PAGINA_WEB:
            return ""  # descarta → fallback para URL no chamador
        return ext

    # Nível 3: não reconhecido — o chamador usará get_extensao(url) como fallback
    return ""


# =============================================================================
# SANITIZAÇÃO DE NOMES DE ARQUIVO
# =============================================================================

def sanitizar_nome_arquivo(nome: str) -> str:
    """
    Remove caracteres inválidos de um nome de arquivo para salvar em disco.

    # Caracteres inválidos no Windows: \\ / : * ? " < > |
    Substitui por underscore. Limita o comprimento para evitar erros
    de path muito longo.

    """
    nome_limpo = re.sub(r'[\\/:*?"<>|]', "_", nome)
    return nome_limpo[:200]  # limite seguro para Windows


# =============================================================================
# REQUISIÇÃO COM RETENTATIVAS
# =============================================================================

def fazer_request(url: str, stream: bool = False):
    """
    Realiza uma requisição HTTP com retentativas automáticas e backoff exponencial.

    Por que isso existe?
    Prefeituras apresentam instabilidades constantes (erros 403, 500, timeouts).
    Sem retentativas, o crawler simplesmente pularia essas páginas/arquivos.
    Com backoff exponencial, cada tentativa espera o dobro da anterior:
      Tentativa 1: falhou → aguarda 2s
      Tentativa 2: falhou → aguarda 4s
      Tentativa 3: falhou → registra falha permanente

    Parâmetros:
      url    : URL a ser acessada
      stream : True para downloads de arquivo (não carrega tudo na memória)

    Retorna:
      Response do requests se bem-sucedido, None se todas as tentativas falharem.
    """
    headers = {"User-Agent": USER_AGENT}

    for tentativa in range(1, MAX_RETRIES + 1):
        try:
            response = requests.get(
                url,
                headers=headers,
                timeout=REQUEST_TIMEOUT,
                stream=stream,
                verify=True,   # valida certificado SSL
            )
            # Consideramos sucesso qualquer resposta do servidor,
            # mesmo 403 ou 404 — o chamador decide o que fazer com o status.
            return response

        except requests.exceptions.SSLError:
            # Alguns sites governamentais têm certificados SSL desatualizados.
            # Tenta novamente sem validação SSL.
            try:
                response = requests.get(
                    url,
                    headers=headers,
                    timeout=REQUEST_TIMEOUT,
                    stream=stream,
                    verify=False,  # ignora SSL inválido
                )
                return response
            except Exception:
                pass

        except (requests.exceptions.RequestException, UnicodeDecodeError):
            # Timeout, erro de conexão, etc.
            # UnicodeDecodeError ocorre quando o servidor retorna um header
            # Location com encoding inválido (ex: Latin-1 em vez de UTF-8).
            pass

        # Backoff exponencial: 2s, 4s, 8s...
        if tentativa < MAX_RETRIES:
            espera = 2 ** tentativa
            time.sleep(espera)

    # Todas as tentativas falharam
    return None
