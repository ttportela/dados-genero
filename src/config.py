# =============================================================================
# config.py — Configurações Centralizadas do Crawler Oficial
# TCC: Mapeamento de Dados Públicos no Paraná — Perspectivas de Gênero
# UTFPR — Adriana Sarturi
# =============================================================================
#
# Por que este arquivo existe?
# Pra centralizar todos os parâmetros que podem mudar em um único lugar. 
# Qualquer ajuste (ex: mudar o MAX_PAGES) acontece aqui, e todos os módulos
# que importam este arquivo já recebem o valor atualizado automaticamente.
#
# =============================================================================

import json
from pathlib import Path

# Diretório raiz do projeto (pasta tcc-dados-publicos-genero-pr/)
# Path(__file__) aponta para este arquivo (config.py), .parent é src/,
# e .parent.parent sobe para a raiz do projeto.
DIR_RAIZ = Path(__file__).parent.parent

# Pasta onde os resultados de cada cidade serão salvos (criada em runtime)
DIR_RESULTADOS = DIR_RAIZ / "resultados"
# SUFIXO_PASTA   = "_oficial"  # pastas com dados finalizados do TCC
SUFIXO_PASTA   = ""


# =============================================================================
# CIDADES — Configuração das cidades-alvo (arquivo externo)
# =============================================================================
#
# A configuração das cidades (sementes, domínios, domínios excluídos) é lida
# do arquivo cidades.json na raiz do projeto. Isso permite adicionar ou ajustar
# cidades sem editar código Python — basta editar o JSON.
#
# "sementes": lista de URLs onde o crawler começa a navegar.
# "dominios": domínios válidos — o crawler rejeita links fora destes.
#             Usa endswith() — cobre subdomínios automaticamente.
# "dominios_excluidos" (opcional): subdomínios bloqueados explicitamente.
#
# Portais verificados em: 20/04/2025

_ARQUIVO_CIDADES = DIR_RAIZ / "cidades.json"


def _carregar_cidades() -> dict:
    """Lê a configuração de cidades do arquivo JSON externo."""
    if not _ARQUIVO_CIDADES.exists():
        raise FileNotFoundError(
            f"Arquivo de configuração não encontrado: {_ARQUIVO_CIDADES}\n"
            "Crie o arquivo cidades.json na raiz do projeto. Veja a documentação no README."
        )
    with open(_ARQUIVO_CIDADES, encoding="utf-8") as f:
        dados = json.load(f)
    # Remove chaves de metadados (começam com _)
    return {k: v for k, v in dados.items() if not k.startswith("_")}


CIDADES = _carregar_cidades()


# =============================================================================
# PARÂMETROS DE CRAWLING
# =============================================================================
#
# MAX_PAGES: limite de páginas processadas por sessão.
#   Papel: controle de sessão, não segurança contra loop.
#   O set `visited` já garante que nenhuma URL é processada duas vezes.
#   Com o checkpoint ativo, o crawler retoma de onde parou na próxima execução.
#
# MAX_DEPTH: profundidade máxima da navegação BFS.
#
# REQUEST_TIMEOUT: tempo máximo de espera por resposta do servidor (segundos).
#   Prefeituras podem ser lentas — 15s evita travar sem desistir rápido demais.
#
# MAX_RETRIES: tentativas antes de registrar falha permanente.
#
# PAUSA_ENTRE_REQUESTS: intervalo entre requisições (segundos).
#   Respeita o servidor da prefeitura e reduz risco de bloqueio por volume.
#
# USER_AGENT: como o crawler se identifica para o servidor.
#   Boa prática ética em pesquisa acadêmica — identifica a instituição
#   e o e-mail de contato, diferenciando de bots maliciosos.

MAX_PAGES            = 100000 
MAX_DEPTH            = 10
REQUEST_TIMEOUT      = 15    # segundos
MAX_RETRIES          = 3
PAUSA_ENTRE_REQUESTS = 0     # segundos

USER_AGENT = (
    "TCC-UTFPR/1.0 "
    "(Pesquisa academica - Mapeamento de Dados Publicos no Parana; "
    "Engenharia de Software UTFPR; "
    "contato: adrianasarturi@alunos.utfpr.edu.br)"
)


# =============================================================================
# UNRAR_TOOL — Caminho para o executável UnRAR (necessário para leitura de .rar)
# =============================================================================
#
# O módulo rarfile exige o binário UnRAR para descompactar arquivos .rar.
# Ajuste o caminho conforme o ambiente:
#   Windows (WinRAR padrão) : r"C:\Program Files\WinRAR\UnRAR.exe"
#   Linux/macOS             : "/usr/bin/unrar"  (após: sudo apt install unrar)
#
UNRAR_TOOL = r"C:\Program Files\WinRAR\UnRAR.exe"


# =============================================================================
# PALAVRAS_GENERO — Termos usados pelo Analisador (src/analisador.py)
# =============================================================================

PALAVRAS_GENERO = [
    # Termos diretos
    "genero", "gênero", "gender",
    "sexo", "sex",
    "identidade de gênero", "identidade de genero",

    # Valores que costumam preencher essa coluna (rede de segurança caso a coluna venha sem nome)
    "feminino", "masculino", "female", "male",
    "mulher", "mulheres", "woman", "women",
    "homem", "homens", "man", "men", 
]
