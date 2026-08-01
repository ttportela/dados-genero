#!/bin/bash
# Pipeline completo para uma cidade: crawler → descobrir portais → re-crawler → download → análise
# Uso: ./run_pipeline.sh <cidade> [estado]
# Ex:  ./run_pipeline.sh maringa
#      ./run_pipeline.sh abatia pr

CIDADE="${1:?Uso: ./run_pipeline.sh <cidade> [estado]}"
ESTADO="${2:-pr}"
LOG_DIR="resultados/_logs"
mkdir -p "$LOG_DIR"
LOG="$LOG_DIR/${CIDADE}.txt"

echo "=== Pipeline iniciado: ${CIDADE} ==="
echo "=== Log: ${LOG} ==="

echo ""
echo "[1/5] Crawler (etapa 1, profundidade 10)..."
python -u main.py "$CIDADE" --sem-limite --etapa 1 --max-profundidade 10 --pular-captcha 2>&1 | tee -a "$LOG"

echo ""
echo "[2/5] Descobrir portais na web (apenas inventário)..."
python -u descobrir_cidades.py --estado "$ESTADO" --cidade "$CIDADE" --buscar-web --apenas-inventario 2>&1 | tee -a "$LOG"

echo ""
echo "[3/5] Re-crawler com reprocessar erros e novas sementes..."
python -u main.py "$CIDADE" --sem-limite --etapa 1 --max-profundidade 10 --reprocessar-erros --pular-captcha 2>&1 | tee -a "$LOG"

# echo ""
# echo "[4/5] Download dos arquivos (etapa 2)..."
# python -u main.py "$CIDADE" --etapa 2 2>&1 | tee -a "$LOG"

# echo ""
# echo "[5/5] Análise dos arquivos (etapa 3)..."
# python -u main.py "$CIDADE" --etapa 3 2>&1 | tee -a "$LOG"

echo ""
echo "=== Pipeline concluído: ${CIDADE} ==="
