# =============================================================================
# crawler.py — Classe CrawlerUrbano (Módulo 1 do Pipeline)
# TCC: Mapeamento de Dados Públicos no Paraná — Perspectivas de Gênero
# UTFPR — Adriana Sarturi
# =============================================================================
#
# Responsabilidade: navegar o site de uma prefeitura usando BFS (Busca em
# Largura) e anotar na planilha todos os links de arquivos encontrados.
#
# O Crawler NÃO baixa nada. Ele apenas ANOTA.
#
# Por que uma Classe e não funções soltas?
# Nos experimentos piloto, `visited`, `queue` e `registros` eram variáveis
# globais. Se rodássemos duas cidades no mesmo script, os estados se
# misturariam. Com a classe CrawlerUrbano, cada instância tem seu próprio
# estado isolado — instanciar crawler_curitiba e crawler_maringa ao mesmo
# tempo é seguro. 
#
# =============================================================================

import json
import random
import time
import warnings
from collections import deque
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse, urljoin

import requests
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from bs4 import BeautifulSoup

from src.config import (
    CIDADES,
    DIR_RESULTADOS,
    MAX_DEPTH,
    MAX_PAGES,
    PAUSA_ENTRE_REQUESTS,
    REQUEST_TIMEOUT,
    USER_AGENT,
)
from src.utils import (
    fazer_request,
    get_extensao,
    is_arquivo,
    is_midia,
    is_valid_domain,
    normalizar_url,
    mime_para_extensao,
    url_chave_dedup,
)

# Suprime o aviso de SSL para não poluir o terminal durante a execução
warnings.filterwarnings("ignore", message="Unverified HTTPS request")


class CrawlerUrbano:
    """
    Crawler BFS para varredura de portais de prefeituras municipais.

    Uso:
        crawler = CrawlerUrbano("maringa")
        crawler.iniciar_varredura()

    Saídas geradas em resultados/{cidade}/:
        inventario_links.xlsx   — arquivos encontrados (xlsx, csv, pdf, etc.)
        erros_varredura.xlsx    — bloqueios e erros registrados (CAPTCHAs, 403, etc.)
        checkpoint_visited.json — URLs já visitadas (para retomada)
        checkpoint_queue.json   — URLs ainda na fila (para retomada)
    """

    def __init__(
        self,
        nome_cidade: str,
        reprocessar_erros: bool = False,
        max_paginas: int | None = None,
        max_profundidade: int | None = None,
    ):
        """
        Inicializa o crawler para uma cidade específica.

        Verifica se existe um checkpoint salvo e retoma de onde parou,
        ou começa uma varredura nova a partir das sementes do config.py.

        Parâmetros:
          reprocessar_erros: se True, lê o log de erros_varredura.xlsx e
            re-enfileira as URLs com erros transitórios (TIMEOUT, HTTP_403,
            HTTP_500, CAPTCHA, SELENIUM_ERRO) para nova tentativa. Erros
            permanentes (HTTP_404, CAPTCHA_NAO_RESOLVIDO) são ignorados.
        """
        if nome_cidade not in CIDADES:
            raise ValueError(
                f"Cidade '{nome_cidade}' não encontrada em config.CIDADES. "
            )

        self.nome_cidade = nome_cidade
        self.config_cidade = CIDADES[nome_cidade]
        self.dominios = self.config_cidade["dominios"]
        self.sementes = self.config_cidade["sementes"]
        # Subd. explicitamente bloqueados (ex: encurtadores mortos, sistemas desativados).
        # Definidos por cidade em config.py — vazio por padrão.
        self.dominios_excluidos = self.config_cidade.get("dominios_excluidos", [])
        # Pausa entre requisições — pode ser sobrescrita por cidade no cidades.json
        # para evitar bloqueio por IP em servidores mais restritivos.
        # Valores aceitos:
        #   false (padrão): usa PAUSA_ENTRE_REQUESTS do config.py
        #   true: randomiza entre 2 e 10 segundos (anti-bloqueio)
        #   número (float): pausa fixa em segundos
        cfg_pausa = self.config_cidade.get("pausa_entre_requests", False)
        if cfg_pausa is True:
            self.pausa_aleatoria = True
            self.pausa_entre_requests = None
        elif isinstance(cfg_pausa, (int, float)) and cfg_pausa > 0:
            self.pausa_aleatoria = False
            self.pausa_entre_requests = float(cfg_pausa)
        else:
            self.pausa_aleatoria = False
            self.pausa_entre_requests = PAUSA_ENTRE_REQUESTS
        # Flag: re-enfileirar URLs com erros transitórios para nova tentativa.
        self.reprocessar_erros = reprocessar_erros
        # Limites opcionais — sobrescrevem config.py quando informados via CLI.
        # None = usar valor de config.py (MAX_PAGES / MAX_DEPTH).
        self.max_paginas = max_paginas
        self.max_profundidade = max_profundidade
        # Profundidade da página sendo processada — usada por _registrar_erro
        # para anotar a profundidade do link no log de erros, permitindo
        # re-enfileirar com a profundidade correta ao reprocessar.
        self._depth_atual = 0

        # Pasta de resultados da cidade
        self.dir_cidade = DIR_RESULTADOS / nome_cidade
        self.dir_cidade.mkdir(parents=True, exist_ok=True)

        # Caminhos dos arquivos de saída
        self.arquivo_inventario   = self.dir_cidade / "inventario_links.xlsx"
        self.arquivo_externos     = self.dir_cidade / "inventario_externos.xlsx"
        self.arquivo_erros        = self.dir_cidade / "erros_varredura.xlsx"
        self.arquivo_ckpt_visited = self.dir_cidade / "checkpoint_visited.json"
        self.arquivo_ckpt_queue   = self.dir_cidade / "checkpoint_queue.json"

        # Listas de registros em memória (serão salvas em planilha ao final)
        self._registros_inventario: list[dict] = []
        self._registros_externos: list[dict] = []
        self._registros_erros: list[dict] = []
        # Set de URLs já inventariadas — garante que cada arquivo e anotado
        # apenas uma vez, mesmo que apareça em múltiplas páginas do site.
        self._urls_inventariadas: set[str] = set()
        # Set de URLs externas já registradas — deduplicação.
        self._urls_externas: set[str] = set()

        # Inicializa fila e visitados (carrega checkpoint se existir)
        self.visited: set[str] = set()
        self.queue: deque[tuple[str, int]] = deque()  # (url, profundidade)
        # Fix 2: set espelho da fila para deduplicação O(1) sem varrer a deque.
        # Evita que a mesma URL seja enfileirada múltiplas vezes em sites com
        # muitos links repetidos, impedindo crescimento excessivo da fila em RAM.
        self._urls_na_fila: set[str] = set()
        # Fix 3: URLs sem sessao= que redirecionaram para outro subdomínio.
        # Não são re-enfileiradas na versão sem sessao= (o servidor exige sessao=),
        # mas a versão COM sessao= pode ser processada normalmente.
        self._sem_sessao_falhos: set[str] = set()
        self._carregar_checkpoint()

        print(f"\n{'='*60}")
        print(f"  Crawler iniciado: {nome_cidade.upper()}")
        print(f"  Páginas já visitadas (checkpoint): {len(self.visited)}")
        print(f"  URLs na fila: {len(self.queue)}")
        if self.reprocessar_erros:
            print(f"  Reprocessar erros: ATIVADO")
        print(f"{'='*60}\n")

    # =========================================================================
    # CHECKPOINT — Persistência de Estado
    # =========================================================================

    def _carregar_checkpoint(self):
        """
        Carrega o estado salvo em disco (visited + queue + inventário parcial).
        Se não existir checkpoint, começa com as sementes do config.py.

        """
        if self.arquivo_ckpt_visited.exists() and self.arquivo_ckpt_queue.exists():
            with open(self.arquivo_ckpt_visited, "r", encoding="utf-8") as f:
                self.visited = set(json.load(f))
            with open(self.arquivo_ckpt_queue, "r", encoding="utf-8") as f:
                dados_queue = json.load(f)
                self.queue = deque((item["url"], item["depth"]) for item in dados_queue)
            # Popula o set espelho com as CHAVES normalizadas (sem sessao=)
            # para deduplicação correta ao retomar do checkpoint.
            self._urls_na_fila = {url_chave_dedup(item["url"]) for item in dados_queue}

            # Carrega o inventário parcial já salvo, se existir
            if self.arquivo_inventario.exists():
                try:
                    df_existente = pd.read_excel(self.arquivo_inventario)
                    self._registros_inventario = df_existente.to_dict("records")
                    # Popula o set de deduplicação com as URLs já conhecidas
                    self._urls_inventariadas = {
                        str(r.get("url_encontrada", ""))
                        for r in self._registros_inventario
                    }
                    print(f"Checkpoint carregado — retomando varredura.")
                    print(f"Inventário parcial carregado: {len(self._registros_inventario)} arquivos já registrados.")
                except Exception as e:
                    print(f"Aviso: não foi possível carregar o inventário existente ({e}). Começando o inventário do zero.")
            else:
                print(f"Checkpoint carregado — retomando varredura.")

            # Carrega o inventário de links externos parcial já salvo, se existir
            if self.arquivo_externos.exists():
                try:
                    df_ext = pd.read_excel(self.arquivo_externos)
                    self._registros_externos = df_ext.to_dict("records")
                    self._urls_externas = {
                        str(r.get("url_encontrada", ""))
                        for r in self._registros_externos
                    }
                    print(f"  Links externos parciais carregados: {len(self._registros_externos)} links já registrados.")
                except Exception as e:
                    print(f"Aviso: não foi possível carregar o inventário de externos ({e}).")

            # Carrega o log de erros parcial já salvo, se existir
            if self.arquivo_erros.exists():
                try:
                    df_erros = pd.read_excel(self.arquivo_erros)
                    self._registros_erros = df_erros.to_dict("records")
                    print(f"  Log de erros parcial carregado: {len(self._registros_erros)} erros já registrados.")
                except Exception as e:
                    print(f"Aviso: não foi possível carregar o log de erros existente ({e}). Começando log do zero.")

            # Adiciona sementes novas que ainda não foram visitadas nem estão na fila
            novas_sementes = 0
            for semente in self.sementes:
                url_norm = normalizar_url(semente)
                chave = url_chave_dedup(url_norm)
                if chave not in self.visited and chave not in self._urls_na_fila:
                    self.queue.append((url_norm, 0))
                    self._urls_na_fila.add(chave)
                    novas_sementes += 1
            if novas_sementes:
                print(f"  {novas_sementes} nova(s) semente(s) adicionada(s) à fila.")
        else:
            # Primeira execução: inicia com as sementes
            for semente in self.sementes:
                url_norm = normalizar_url(semente)
                self.queue.append((url_norm, 0))
                self._urls_na_fila.add(url_chave_dedup(url_norm))  # chave normalizada
            print(f"Nenhum checkpoint encontrado — iniciando do zero.")

        # Se solicitado, re-enfileira URLs com erros transitórios para nova tentativa
        if self.reprocessar_erros:
            self._recarregar_erros_para_fila()

    def _salvar_checkpoint(self):
        """Persiste o estado atual (visited + queue) em disco."""
        with open(self.arquivo_ckpt_visited, "w", encoding="utf-8") as f:
            json.dump(list(self.visited), f, ensure_ascii=False)
        with open(self.arquivo_ckpt_queue, "w", encoding="utf-8") as f:
            dados_queue = [{"url": url, "depth": depth} for url, depth in self.queue]
            json.dump(dados_queue, f, ensure_ascii=False)

    # =========================================================================
    # DETECÇÃO DE CAPTCHA
    # =========================================================================

    @staticmethod
    def _user_agent_str() -> str:
        """Retorna o User-Agent como string simples (para uso no Selenium)."""
        from src.config import USER_AGENT
        return USER_AGENT

    def _detectar_captcha(self, texto_html: str) -> bool:
        """
        Verifica se a resposta contém impressões digitais de sistemas de CAPTCHA.

        Não há um código HTTP específico para CAPTCHA — os sistemas de proteção
        retornam HTML com marcadores identificáveis. Esta função detecta os
        principais: Cloudflare, Google reCAPTCHA, hCaptcha e genéricos.

        Retorna True se CAPTCHA detectado, False caso contrário.
        """
        conteudo = texto_html.lower()

        # Sinais de BLOQUEIO REAL — página que impede a navegação
        sinais_bloqueio = [
            "just a moment",            # Cloudflare — página de espera
            "cf-challenge",             # Cloudflare — challenge JS
            "attention required",       # Cloudflare — bloqueio por IP
            "prove you are human",      # Cloudflare genérico
            "verificação de segurança",
            "hcaptcha.com/captcha",     # hCaptcha ativo (não só carregado)
        ]

        # Sinais de reCAPTCHA VISÍVEL — widget de desafio, não invisível (v3)
        # "recaptcha" sozinho é falso positivo: portais gov carregam o script
        # invisível (v3) que aparece no HTML mas não bloqueia a navegação.
        sinais_recaptcha_visivel = [
            "g-recaptcha-response",     # campo de formulário do desafio
            "recaptcha/api2/bframe",    # iframe do desafio visual
            '<div class="g-recaptcha"', # widget visível no DOM
        ]

        return (
            any(s in conteudo for s in sinais_bloqueio)
            or any(s in conteudo for s in sinais_recaptcha_visivel)
        )

    # =========================================================================
    # EXTRAÇÃO DE LINKS
    # =========================================================================

    @staticmethod
    def _alternar_protocolo(url: str) -> str:
        """Retorna a URL com o protocolo alternativo (http↔https). String vazia se não for http(s)."""
        if url.startswith("https://"):
            return "http://" + url[len("https://"):]
        if url.startswith("http://"):
            return "https://" + url[len("http://"):]
        return ""

    def _extrair_links(self, url: str) -> list[tuple[str, str]]:
        """
        Extrai todos os links de uma página usando requests + BeautifulSoup.
        Estratégia Nível 1 (rápida).

        Retorna lista de tuplas (url_absoluta, texto_do_link).
        Retorna None se a página precisar do fallback Selenium.
        """
        url_original = url
        response = fazer_request(url)

        # Se falhou (None ou não-200), tenta protocolo alternativo (http ↔ https)
        if response is None or response.status_code != 200:
            url_alt = self._alternar_protocolo(url)
            if url_alt and url_alt != url:
                response_alt = fazer_request(url_alt)
                if response_alt is not None and (
                    response is None
                    or (response.status_code != 200 and response_alt.status_code == 200)
                ):
                    response = response_alt
                    url = url_alt

        if response is None:
            self._registrar_erro(url_original, "TIMEOUT_OU_CONEXAO", 0)
            return None

        # Verifica redirecionamento externo (proteção dupla)
        if not is_valid_domain(response.url, self.dominios):
            print(f"Redirecionamento externo ignorado: {url} → {response.url}")
            return []

        # Redirecionamento para subdomínio diferente dentro do domínio válido.
        # Ex: www3.maringa.pr.gov.br (sem sessao=) → www.maringa.pr.gov.br (homepage).
        # Aplicamos isso APENAS para Maringá, pois Londrina/Curitiba podem ter
        # redirects legítimos para seus portais de transparência em outros subdomínios.
        if self.nome_cidade == "maringa" and urlparse(url).netloc != urlparse(response.url).netloc:
            self._redirect_subdominio = True
            return []

        if response.status_code == 403:
            # 403 pode ser bloqueio com CAPTCHA — tenta Selenium
            self._registrar_erro(url_original, "HTTP_403", response.status_code)
            return None

        if response.status_code == 404:
            self._registrar_erro(url_original, "HTTP_404", response.status_code)
            return []  # não tenta Selenium — página não existe

        if response.status_code != 200:
            # Outros erros (500, 503, etc.) — verifica se é CAPTCHA/bloqueio
            if self._detectar_captcha(response.text):
                self._registrar_erro(url_original, "CAPTCHA", response.status_code)
                return None
            self._registrar_erro(url_original, f"HTTP_{response.status_code}", response.status_code)
            return None

        # Status 200: resposta recebida com sucesso.
        # Verifica o Content-Type: se não for HTML, é um arquivo servido
        # por uma URL sem extensão (ex: /download?id=123). Registra no inventário.
        content_type = response.headers.get("Content-Type", "")
        tipo_arquivo = mime_para_extensao(content_type)
        if tipo_arquivo:
            self._arquivo_detectado = tipo_arquivo
            return []
        # octet-stream genérico: tenta pela extensão da URL como fallback
        if "application/octet-stream" in content_type and get_extensao(url):
            self._arquivo_detectado = get_extensao(url)
            return []

        # Só verifica CAPTCHA se o conteúdo for suspeitamente curto (< 500 chars)
        # — páginas reais têm muito mais conteúdo que uma página de bloqueio.
        # Portais com reCAPTCHA invisível (v3) retornam 200 com HTML completo,
        # não devem acionar o Selenium.
        if len(response.text) < 500 and self._detectar_captcha(response.text):
            self._registrar_erro(url_original, "CAPTCHA", response.status_code)
            return None

        # Parsing do HTML
        soup = BeautifulSoup(response.text, "html.parser")
        links = []
        for tag in soup.find_all("a", href=True):
            href = tag["href"].strip()
            texto = tag.get_text(strip=True)
            try:
                url_absoluta = normalizar_url(urljoin(url, href))
                if url_absoluta.startswith("http"):
                    links.append((url_absoluta, texto))
            except ValueError:
                continue

        return links

    def _extrair_links_selenium(self, url: str) -> list[tuple[str, str]]:
        """
        Fallback: extrai links usando Selenium com Chrome headless.
        Estratégia Nível 2 (lenta, usada quando requests é bloqueado).

        Ativado quando requests encontra 403 ou detecta CAPTCHA.
        """
        print(f"  🤖 Usando Selenium para: {url}")
        driver = None
        try:
            options = ChromeOptions()
            options.add_argument("--headless=new")  # sem abrir janela
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")

            driver = webdriver.Chrome(options=options)
            driver.get(url)
            time.sleep(3)  # aguarda carregamento dinâmico

            html = driver.page_source

            # Se a página veio vazia ou com erro, tenta protocolo alternativo
            if not html or len(html) < 500 or self._detectar_captcha(html):
                url_alt = self._alternar_protocolo(url)
                if url_alt and url_alt != url:
                    driver.get(url_alt)
                    time.sleep(3)
                    html_alt = driver.page_source
                    if html_alt and len(html_alt) > len(html) and not self._detectar_captcha(html_alt):
                        html = html_alt
                        url = url_alt

            # Verifica CAPTCHA mesmo com Selenium
            if self._detectar_captcha(html):
                # Nível 3: CAPTCHA duro — abre janela e aguarda intervenção humana
                print(f"\n CAPTCHA detectado em: {url}")
                print(f"  Você tem 60 segundos para resolver manualmente no navegador.")
                print(f"  (Se não resolver, o crawler pula esta URL e continua.)\n")

                # Reabre com janela visível para intervenção humana
                driver.quit()
                options_visivel = ChromeOptions()
                driver = webdriver.Chrome(options=options_visivel)
                driver.get(url)
                time.sleep(60)  # janela de 60s para resolução manual

                html = driver.page_source
                if self._detectar_captcha(html):
                    self._registrar_erro(url, "CAPTCHA_NAO_RESOLVIDO", 0)
                    return []

            soup = BeautifulSoup(html, "html.parser")
            links = []
            for tag in soup.find_all("a", href=True):
                href = tag["href"].strip()
                texto = tag.get_text(strip=True)
                try:
                    url_absoluta = normalizar_url(urljoin(url, href))
                    if url_absoluta.startswith("http"):
                        links.append((url_absoluta, texto))
                except ValueError:
                    continue

            return links

        except Exception as e:
            self._registrar_erro(url, f"SELENIUM_ERRO: {type(e).__name__}", 0)
            return []
        finally:
            if driver:
                driver.quit()

    # =========================================================================
    # PROCESSAMENTO DE PÁGINA
    # =========================================================================

    def _processar_pagina(self, url: str, depth: int) -> bool:
        """
        Processa uma página: extrai links e toma duas decisões para cada um:
          1. Se é arquivo → anota no inventário
          2. Se é página HTML e está no domínio → adiciona à fila BFS

        Retorna False se a página redirecionou para outro subdomínio (exige sessao=),
        sinalizando ao BFS para não marcar essa URL como visitada.
        Páginas HTML não são anotadas na planilha — são apenas meio de transporte.
        """
        self._redirect_subdominio = False   # reset a cada página
        self._depth_atual = depth            # profundidade para _registrar_erro
        self._arquivo_detectado = None       # MIME type se URL da fila for arquivo
        # Tenta Nível 1 (requests)
        links = self._extrair_links(url)

        # Redirect de subdomínio detectado (página precisa de sessao=)
        if self._redirect_subdominio:
            return False   # BFS não marcará como visitada

        # Se None → tenta Nível 2 (Selenium)
        if links is None:
            links = self._extrair_links_selenium(url)

        # Se a URL da fila foi detectada como arquivo via MIME type,
        # registra no inventário e não processa links.
        if self._arquivo_detectado:
            self._registrar_arquivo(
                url_encontrada=url,
                texto_no_site="",
                pagina_de_origem="",
                depth=depth,
                tipo_conhecido=self._arquivo_detectado,
            )
            return True

        for url_link, texto in links:
            url_link = normalizar_url(url_link)

            # Ignora links em subdomínios explicitamente bloqueados
            if self.dominios_excluidos and is_valid_domain(url_link, self.dominios_excluidos):
                continue

            # Links fora dos domínios válidos (mas não bloqueados) são registrados
            # no inventário de externos — não entram na fila, mas ficam visíveis.
            if not is_valid_domain(url_link, self.dominios):
                self._registrar_externo(
                    url_encontrada=url_link,
                    texto_no_site=texto,
                    pagina_de_origem=url,
                    depth=depth,
                )
                continue

            if is_arquivo(url_link):
                # É um arquivo de dados → anota no inventário
                self._registrar_arquivo(
                    url_encontrada=url_link,
                    texto_no_site=texto,
                    pagina_de_origem=url,
                    depth=depth,
                )
            elif is_midia(url_link):
                # É mídia → descarta completamente
                continue
            else:
                # É uma página HTML → usa chave sem sessao= para deduplicação.
                # O request HTTP usa a URL completa (servidor exige o token);
                # a chave normalizada evita visitas repetidas à mesma página
                # com session IDs diferentes (problema: 2.255x em id=60/Maringá).
                chave = url_chave_dedup(url_link)
                if chave in self.visited or chave in self._urls_na_fila:
                    continue
                # Não re-enfileira URL sem sessao= que já sabemos que redireciona
                if url_link in self._sem_sessao_falhos:
                    continue
                limite_depth = self.max_profundidade if self.max_profundidade is not None else MAX_DEPTH
                if depth < limite_depth:
                    self.queue.append((url_link, depth + 1))  # URL completa para o request
                    self._urls_na_fila.add(chave)             # chave normalizada para dedup

    # =========================================================================
    # REGISTRO DE DADOS
    # =========================================================================

    def _checar_status_arquivo(self, url: str) -> tuple[int, str]:
        """
        Faz um HEAD request para verificar o status HTTP e o tipo real do arquivo.

        Por que HEAD e não GET?
        O método HEAD retorna apenas os cabeçalhos da resposta (status, tipo,
        tamanho), sem transferir o corpo do arquivo. É ordens de grandeza mais
        rápido e consome muito menos banda do que um GET completo.

        Identificação do tipo (MIME type):
        O cabeçalho Content-Type retornado pelo servidor declara o tipo real
        do arquivo, independente do nome ou extensão na URL. Isso resolve
        casos de URLs malformadas (ex: .pdfaaaaaa) ou sem extensão
        (ex: /download?id=123).
        O get_extensao() da URL é usado como fallback caso o servidor não
        informe o Content-Type ou informe o genérico 'application/octet-stream'.

        Retorna tupla (status_http, tipo_arquivo).
        """
        from src.config import USER_AGENT
        headers = {"User-Agent": USER_AGENT}
        try:
            resp = requests.head(
                url,
                headers=headers,
                timeout=REQUEST_TIMEOUT,
                allow_redirects=True,
                verify=False,  # alguns servidores de arquivo têm SSL problemático
            )
            # Se falhou, tenta protocolo alternativo (http ↔ https)
            if resp.status_code != 200:
                url_alt = self._alternar_protocolo(url)
                if url_alt and url_alt != url:
                    resp_alt = requests.head(
                        url_alt,
                        headers=headers,
                        timeout=REQUEST_TIMEOUT,
                        allow_redirects=True,
                        verify=False,
                    )
                    if resp_alt.status_code == 200:
                        resp = resp_alt
            # Tenta identificar o tipo pelo MIME type do servidor
            content_type = resp.headers.get("Content-Type", "")
            tipo = mime_para_extensao(content_type)
            # Fallback: se MIME não identificou, usa extensão da URL
            if not tipo:
                tipo = get_extensao(url)
            return resp.status_code, tipo
        except Exception:
            return 0, get_extensao(url)  # fallback para a URL

    def _registrar_arquivo(
        self,
        url_encontrada: str,
        texto_no_site: str,
        pagina_de_origem: str,
        depth: int,
        tipo_conhecido: str = "",
    ):
        """
        Adiciona um arquivo ao inventário em memória.
        Faz um HEAD request para preencher o status_http.
        Ignora URLs já registradas (deduplicação por URL).

        Se tipo_conhecido for informado, pula o HEAD request (tipo já conhecido).
        """
        # Deduplicação: mesma URL pode aparecer em múltiplas páginas
        if url_encontrada in self._urls_inventariadas:
            return
        self._urls_inventariadas.add(url_encontrada)

        if tipo_conhecido:
            status, tipo = 200, tipo_conhecido
        else:
            status, tipo = self._checar_status_arquivo(url_encontrada)

        icone = "📄" if status == 200 else ("🔒" if status == 403 else "⚠️")
        print(f"  {icone} [{status}] {tipo or get_extensao(url_encontrada)} -> {url_encontrada[:70]}")

        self._registros_inventario.append({
            "cidade":             self.nome_cidade,
            "url_encontrada":     url_encontrada,
            "dominio_encontrado": urlparse(url_encontrada).netloc,
            "texto_no_site":      texto_no_site,
            "pagina_de_origem":   pagina_de_origem,
            "tipo_arquivo":       tipo or get_extensao(url_encontrada),
            "profundidade":       depth,
            "status_http":        status,
            "data_varredura":     datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        })

    def _registrar_externo(self, url_encontrada: str, texto_no_site: str, pagina_de_origem: str, depth: int):
        """Registra um link externo (fora dos domínios válidos) no inventário de externos."""
        if url_encontrada in self._urls_externas:
            return
        self._urls_externas.add(url_encontrada)

        self._registros_externos.append({
            "cidade":             self.nome_cidade,
            "url_encontrada":     url_encontrada,
            "dominio_encontrado": urlparse(url_encontrada).netloc,
            "texto_no_site":      texto_no_site,
            "pagina_de_origem":   pagina_de_origem,
            "profundidade":       depth,
            "data_varredura":     datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        })

    def _registrar_erro(self, url: str, tipo_erro: str, status_code: int):
        """Adiciona um erro/bloqueio ao log de erros em memória."""
        print(f" ❌ {tipo_erro}: {url}")
        self._registros_erros.append({
            "cidade":        self.nome_cidade,
            "url_bloqueada": url,
            "tipo_erro":     tipo_erro,
            "status_http":   status_code,
            "profundidade":  self._depth_atual,
            "data_hora":     datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        })

    # =========================================================================
    # REPROCESSAMENTO DE ERROS
    # =========================================================================

    # Erros permanentes: não vale a pena tentar novamente.
    # HTTP_404 — página não existe; CAPTCHA_NAO_RESOLVIDO — intervenção humana já falhou.
    _ERROS_PERMANENTES = {"HTTP_404", "CAPTCHA_NAO_RESOLVIDO"}

    def _recarregar_erros_para_fila(self):
        """
        Lê o log de erros em memória e re-enfileira as URLs com erros
        transitórios (TIMEOUT, HTTP_403, HTTP_500, CAPTCHA, SELENIUM_ERRO) para
        nova tentativa. Erros permanentes (HTTP_404, CAPTCHA_NAO_RESOLVIDO) são
        mantidos no log e não são re-enfileirados.

        Para cada URL re-enfileirada:
          1. Remove do set `visited` (para que o BFS a processe novamente)
          2. Adiciona à fila com a profundidade original (coluna `profundidade`)
          3. Remove do log de erros em memória (ganha nova entrada se falhar de novo)
        """
        if not self._registros_erros:
            print(f"  Reprocessar erros: nenhum erro no log — nada a re-enfileirar.")
            return

        # URLs já na fila não precisam ser re-enfileiradas
        urls_ja_na_fila = {url_chave_dedup(url) for url, _ in self.queue}
        urls_ja_na_fila |= self._urls_na_fila

        re_enfileirar = []   # (url, depth)
        manter_erros = []    # registros de erro permanentes

        for registro in self._registros_erros:
            tipo_erro = registro.get("tipo_erro", "")
            url = registro.get("url_bloqueada", "")
            depth = registro.get("profundidade", 0)

            # Erro permanente → mantém no log
            if tipo_erro in self._ERROS_PERMANENTES:
                manter_erros.append(registro)
                continue

            # URL já na fila → não duplica
            chave = url_chave_dedup(url)
            if chave in urls_ja_na_fila:
                manter_erros.append(registro)
                continue

            # Remove de visited para permitir reprocessamento
            self.visited.discard(chave)
            # Adiciona à fila e ao espelho
            self.queue.append((url, depth))
            self._urls_na_fila.add(chave)
            urls_ja_na_fila.add(chave)
            re_enfileirar.append((url, depth))

        # Atualiza o log de erros: mantém apenas os permanentes + os que já estavam na fila
        self._registros_erros = manter_erros

        print(f"  Reprocessar erros: {len(re_enfileirar)} URLs re-enfileiradas para nova tentativa.")
        print(f"  Reprocessar erros: {len(manter_erros)} erros permanentes mantidos no log.")

    # =========================================================================
    # SALVAMENTO DAS PLANILHAS
    # =========================================================================

    @staticmethod
    def _sanitizar_df(df: pd.DataFrame) -> pd.DataFrame:
        """
        Remove caracteres ilegais para o Excel de todas as colunas de texto.

        O openpyxl rejeita caracteres de controle (ASCII 0-8, 11-12, 14-31)
        com IllegalCharacterError. Esses chars aparecem em textos coletados de
        CMSs de prefeituras que geram conteudo mal-formatado.
        """
        import re
        # Padrao que cobre todos os chars ilegais para Excel
        CHARS_ILEGAIS = re.compile(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]")

        for col in df.select_dtypes(include="object").columns:
            df[col] = df[col].apply(
                lambda v: CHARS_ILEGAIS.sub("", str(v)) if pd.notna(v) else v
            )
        return df

    @staticmethod
    def _salvar_excel_atomico(df: pd.DataFrame, caminho_final: Path):
        """
        Fix 3: Escrita atômica de planilha Excel.

        Salva primeiro em um arquivo temporário (.tmp) no mesmo diretório e
        só então renomeia para o destino final. Isso garante que, se o processo
        for interrompido durante a escrita (queda de luz, SIGKILL), o arquivo
        anterior permanece íntegro — nunca ficamos com um Excel corrompido pela
        metade. O rename é uma operação atômica no sistema de arquivos.
        """
        caminho_tmp = caminho_final.with_suffix(".tmp.xlsx")
        df.to_excel(caminho_tmp, index=False)
        caminho_tmp.replace(caminho_final)  # rename atômico

    def _salvar_planilhas(self):
        """Salva os registros em memória nas planilhas Excel finais (escrita atômica)."""
        if self._registros_inventario:
            df_inv = pd.DataFrame(self._registros_inventario)
            df_inv = self._sanitizar_df(df_inv)
            self._salvar_excel_atomico(df_inv, self.arquivo_inventario)
            print(f"\n  Inventário salvo: {self.arquivo_inventario}")
            print(f"  {len(df_inv)} arquivos registrados.")
        else:
            print(f"\n  Nenhum arquivo encontrado para {self.nome_cidade}.")

        if self._registros_erros:
            df_err = pd.DataFrame(self._registros_erros)
            df_err = self._sanitizar_df(df_err)
            self._salvar_excel_atomico(df_err, self.arquivo_erros)
            print(f"  Log de erros salvo: {self.arquivo_erros}")
            print(f"  {len(df_err)} erros/bloqueios registrados.")

        if self._registros_externos:
            df_ext = pd.DataFrame(self._registros_externos)
            df_ext = self._sanitizar_df(df_ext)
            self._salvar_excel_atomico(df_ext, self.arquivo_externos)
            print(f"  Links externos salvos: {self.arquivo_externos}")
            print(f"  {len(df_ext)} links externos registrados.")

    # =========================================================================
    # MOTOR PRINCIPAL — BFS
    # =========================================================================

    def iniciar_varredura(self, sem_limite: bool = False):
        """
        Motor BFS público. Consome a fila e produz as planilhas finais.

        BFS (Breadth-First Search / Busca em Largura):
        Visita primeiro todas as páginas do nível 1, depois as do nível 2, etc.
        Isso garante que os links mais próximos da homepage sejam encontrados primeiro.

        Guardas contra loop infinito:
          1. set `visited` — nenhuma URL é processada duas vezes
          2. MAX_PAGES    — limite de sessão (desativado se sem_limite=True)
          3. MAX_DEPTH    — limite de profundidade

        Parâmetros:
          sem_limite: se True, ignora MAX_PAGES e varre até esgotar a fila.
        """
        # Resolve o limite de páginas: prioriza o valor passado via CLI
        # (self.max_paginas), depois config.py (MAX_PAGES), a menos que
        # sem_limite=True (varredura oficial sem teto).
        limite_cfg = self.max_paginas if self.max_paginas is not None else MAX_PAGES
        # Fix 1: dois contadores separados.
        # `paginas_lidas` é CUMULATIVO (inclui checkpoint) — controla o limite MAX_PAGES
        # entre sessões. Se o checkpoint tem 4.930 visitadas e MAX_PAGES=5.000,
        # esta sessão processará apenas 70 páginas novas antes de parar.
        # `paginas_nesta_sessao` conta só o que foi feito AGORA — usado nos prints
        # finais para não confundir o usuário com o total acumulado do checkpoint.
        paginas_lidas = len(self.visited)        # cumulativo (para o limite)
        paginas_nesta_sessao = 0                 # só desta execução (para os prints)
        limite = None if sem_limite else limite_cfg
        limite_str = "sem limite" if limite is None else str(limite)

        ja_visitadas = paginas_lidas
        print(f"  Modo: {'SEM LIMITE de páginas' if limite is None else f'limite de {limite} páginas (já visitadas: {ja_visitadas})'}")

        try:
            while self.queue and (limite is None or paginas_lidas < limite):
                url, depth = self.queue.popleft()

                # Guarda 1: já visitado? (compara pela chave normalizada — sem sessao=)
                chave = url_chave_dedup(url)
                if chave in self.visited:
                    continue

                self.visited.add(chave)             # armazena chave normalizada
                self._urls_na_fila.discard(chave)   # remove do espelho
                paginas_lidas += 1
                paginas_nesta_sessao += 1

                prefixo = f"{paginas_nesta_sessao} (+{ja_visitadas})" if ja_visitadas > 0 else str(paginas_nesta_sessao)
                print(f"  [{prefixo}/{limite_str}] fila={len(self.queue)} | depth={depth} | {url[:80]}")

                visitado_ok = self._processar_pagina(url, depth)
                if visitado_ok is False:
                    # Página exige sessao= — remove dos visitados para que
                    # a versão com sessao= (encontrada na navegação) possa ser processada
                    self.visited.discard(chave)
                    self._sem_sessao_falhos.add(url)  # evita re-enfileirar sem sessao=
                    paginas_lidas -= 1
                    paginas_nesta_sessao -= 1
                    continue

                # Salva checkpoint E planilhas a cada 200 paginas (~5 min de intervalo)
                # Ambos precisam ser salvos juntos: se o sistema desligar abruptamente,
                # o finally nao executa e os dados em memória sao perdidos.
                if paginas_nesta_sessao % 200 == 0:
                    self._salvar_checkpoint()
                    self._salvar_planilhas()
                    print(f"  Checkpoint salvo ({paginas_lidas} páginas totais | {paginas_nesta_sessao} nesta sessão).")

                # Pausa ética entre requisições (configurável por cidade)
                if self.pausa_aleatoria:
                    pausa = random.uniform(2, 10)
                else:
                    pausa = self.pausa_entre_requests
                time.sleep(pausa)

        except KeyboardInterrupt:
            # Usuário interrompeu com Ctrl+C - salva estado antes de sair
            print(f"\n\n  Interrompido pelo usuário. Salvando estado...")

        finally:
            # Sempre salva checkpoint e planilhas ao encerrar
            self._salvar_checkpoint()
            self._salvar_planilhas()

            print(f"\n  Varredura encerrada: {self.nome_cidade.upper()}")
            print(f"  Páginas nesta sessão: {paginas_nesta_sessao}")
            print(f"  Páginas totais (acumulado): {paginas_lidas}")
            print(f"  Arquivos no inventário: {len(self._registros_inventario)}")
            print(f"  Erros registrados: {len(self._registros_erros)}\n")
