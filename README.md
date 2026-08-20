# Mapeamento de Dados Públicos no Paraná: Perspectivas de Gênero

Projeto de Trabalho de Conclusão de Curso em Engenharia de Software - UTFPR.

## 📌 Sobre o projeto

Este trabalho tem como objetivo analisar a disponibilidade de dados públicos em cidades do estado do Paraná, abrangendo tanto dados diretamente relacionados ao planejamento urbano quanto aqueles com potencial para subsidiá-lo, com foco na presença ou ausência de informações desagregadas por gênero.

## 🎯 Objetivos

- Mapear portais de dados públicos municipais do Paraná
- Identificar e baixar arquivos de dados disponíveis nos portais
- Verificar a presença de dados desagregados por gênero via mineração de dados
- Realizar curadoria qualitativa para classificar os arquivos detectados
- Documentar barreiras técnicas e lacunas na disponibilização de dados abertos

## 💻 Tecnologias

- `Python 3.14` — Linguagem principal
- `requests` — Requisições HTTP para acesso às páginas
- `beautifulsoup4` — Parsing de HTML e extração de links
- `selenium` — Fallback para evasão de bloqueios anti-bot
- `pandas` — Manipulação e exportação de dados tabulares
- `openpyxl` — Motor de leitura/escrita de arquivos `.xlsx`

## 🚀 Como executar

### 1. Pré-requisitos

- Python 3.14 instalado
- Google Chrome instalado (necessário para o Selenium)

### 2. Instalar dependências

```bash
# Criar ambiente virtual (recomendado)
python -m venv venv

# Ativar o ambiente virtual
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# Instalar dependências
pip install -r requirements.txt
```

### 3. Executar o pipeline

Para executar as etapas criamos um script da primeira fase:

```bash
# Se usar linux:
./run_pipeline.sh cidade
```

Outros exemplos:

```bash
# Rodar o pipeline completo para uma cidade (Etapas 1 → 2 → 3)
python main.py maringa
python main.py londrina
python main.py curitiba

# Rodar apenas uma etapa específica
python main.py maringa --etapa 1   # Crawler: navega e anota arquivos
python main.py maringa --etapa 2   # Downloader: baixa os arquivos
python main.py maringa --etapa 3   # Analisador: detecta recorte de gênero

# Varredura completa sem limite de páginas
python main.py maringa --sem-limite

# Exemplo completo de início:
python main.py maringa --sem-limite --etapa 1 --max-profundidade 10
# Ou para tentar com as urls que deram erro também:
python main.py maringa --sem-limite --etapa 1 --max-profundidade 10 --reprocessar-erros
```

### 4. Descobrir portais municipais (`descobrir_cidades.py`)

Script automatizado que consulta o IBGE, testa URLs candidatas e popula o `cidades.json`.
Possui três modos de operação:

**Modo 1 — Padrão (testa padrões de URL):**
Testa `https://www.{slug}.{uf}.gov.br/`, `https://{slug}.atende.net/`,
subdomínios alternativos (`portal`, `www2`, `www3`), portais de transparência
e dados abertos. Apenas verifica acessibilidade via HEAD request.

```bash
python descobrir_cidades.py --estado pr

# Com scraping de página oficial de prefeituras (mais preciso)
python descobrir_cidades.py --estado pr \
  --pagina-prefeituras "https://www.parana.pr.gov.br/Pagina/Sites-das-Prefeituras-e-Camaras-Municipais"

# Testar apenas as 10 primeiras cidades (dry-run, não salva)
python descobrir_cidades.py --estado pr --limite 10 --dry-run

# Sobrescrever cidades já existentes no cidades.json
python descobrir_cidades.py --estado pr --sobrescrever

# Definir timeout por URL (padrão: 10s)
python descobrir_cidades.py --estado pr --timeout 15
```

**Modo 2 — Busca na web (primeiro resultado):**
Busca "prefeitura {cidade}" e "portal da transparência {cidade}" na web e
adiciona o primeiro resultado válido de cada consulta como semente (se ainda
não estiver configurado).

```bash
python descobrir_cidades.py --estado pr --cidade "curitiba" --buscar-web
```

**Modo 3 — Busca na web + inventário (até 5 resultados filtrados):**
Busca até 5 resultados de cada consulta na web, mas adiciona como sementes
apenas URLs que também aparecem no `inventario_externos` da cidade (gerado
pelo crawler na Etapa 1).

```bash
python descobrir_cidades.py --estado pr --cidade "curitiba" --buscar-web --apenas-inventario
```

**Argumentos:**
- `--estado` (obrigatório): Sigla do estado (ex: `pr`, `sp`, `rj`)
- `--pagina-prefeituras`: URL opcional com links oficiais das prefeituras
- `--limite <N>`: Limita o número de cidades testadas
- `--dry-run`: Lista resultados sem salvar no `cidades.json`
- `--timeout <s>`: Timeout por requisição HEAD (padrão: 10)
- `--sobrescrever`: Sobrescreve cidades já configuradas
- `--buscar-web`: Ativa busca na web (Modo 2 ou 3)
- `--apenas-inventario`: Com `--buscar-web`, filtra resultados pelo inventário de externos (Modo 3)
- `--cidade <nome>`: Processa apenas uma cidade específica (ex: `curitiba`)

### 5. Visualizar progresso (`visualizar_checkpoint.py`)

Dashboard Streamlit para inspecionar o estado do crawler:

```bash
streamlit run visualizar_checkpoint.py
```

**Modo Dashboard:** Visão geral de todas as cidades com métricas globais,
tabela de progresso filtrável (por nome e status: todas / com dados / não processadas),
gráficos de top 15 páginas visitadas e arquivos encontrados, e barras de progresso individuais.

**Modo Cidade individual:** Estatísticas detalhadas de um município:
- Páginas visitadas, profundidade configurada, último nível com arquivos, arquivos encontrados, erros
- Distribuição de arquivos por grupo (planilhas, documentos, apresentações, geoespaciais, outros)
- Tabelas interativas de URLs visitadas, fila pendente, erros e inventário

### 6. Configuração de cidades (`cidades.json`)

O arquivo `cidades.json` na raiz do projeto define as cidades-alvo. Cada cidade possui:

```json
"curitiba": {
  "sementes": ["https://www.curitiba.pr.gov.br/"],
  "dominios": ["curitiba.pr.gov.br"],
  "dominios_excluidos": ["exemplo.pr.gov.br"],
  "pausa_entre_requests": true
}
```

**Campos:**
- `sementes`: URLs iniciais onde o crawler começa a navegar
- `dominios`: Domínios válidos — o crawler rejeita links fora destes
- `dominios_excluidos` (opcional): Subdomínios bloqueados
- `pausa_entre_requests` (opcional): Controla o intervalo entre requisições:
  - `true`: Randomiza entre 2 e 10 segundos (anti-bloqueio por IP)
  - número (ex: `5.0`): Pausa fixa em segundos
  - omitido ou `false`: Usa o valor global de `config.py`

Os resultados são gerados na pasta `resultados/<cidade>/`.

### 7. Metodologia passo a passo:

Exemplo completo por partes:

```bash
# 1. Rodar crawler com limite de profundidade 10:
python main.py maringa --sem-limite --etapa 1 --max-profundidade 10

# 2. Atualizar o arquivo cidades.json com outros portais descobertos
# (busca site da prefeitura e portal da transparência na web e se o link
# existir no inventário_externos, adiciona a configuração)
python descobrir_cidades.py --estado pr --cidade maringa --buscar-web --apenas-inventario

# 3. Re-crawler com as urls que deram erro também e novas sementes adicionadas:
python main.py maringa --sem-limite --etapa 1 --max-profundidade 10 --reprocessar-erros

# 4. Baixar os arquivos:
python main.py maringa --etapa 2   

# 5. Analisar os arquivos de forma automática, inicialmente:
python main.py maringa --etapa 3 

# Adicione ao final de cada comando acima para salvar um log da execução: 
# 2>&1 | tee -a resultados/_logs/maringa.txt
python main.py maringa --etapa 3 2>&1 | tee -a resultados/_logs/maringa.txt

```

OU

```bash
# Executar o pipeline completo para uma cidade:
./run_pipeline.sh maringa
```




## 📊 Resultados

Os resultados da análise estão organizados por município na pasta `resultados/`:

| Município | Diretório |
|-----------|-----------|
| Maringá | `resultados/maringa_oficial/` |
| Londrina | `resultados/londrina_oficial/` |
| Curitiba | `resultados/curitiba_oficial/` |

Cada diretório contém os inventários de arquivos coletados e os relatórios de classificação por recorte de gênero.

## 📄 Proposta

A proposta desenvolvida no TCC 01 pode ser acessada em:  
[Proposta do projeto](docs/TCC%2001_Proposta.pdf)

## 🗄️ Base de Dados Bruta

Os arquivos coletados durante a pesquisa (downloads e extraídos) estão disponíveis no Google Drive:  
[Acessar base de dados bruta](https://drive.google.com/drive/folders/1JzrvB0snuPFuVCkFLBCbddMnNyjN3JhL?usp=drive_link)

## 🎓 Instituição

UTFPR - Universidade Tecnológica Federal do Paraná

## 👩‍💻 Autores

**Adriana Sarturi**  
Graduanda em Engenharia de Software - UTFPR  

**Tarlis Tortelli Portela**  
Professor Orientador
