#!/bin/bash

CIDADE="${1:?Uso: ./run_pipeline.sh <cidade> [estado]}"
ESTADO="${2:-pr}"
LOG_DIR="resultados/_logs"
mkdir -p "$LOG_DIR"
LOG="$LOG_DIR/${CIDADE}.txt"

echo "=== Pipeline iniciado: ${CIDADE} ==="
echo "=== Log: ${LOG} ==="

echo ""
echo "[3/5] Re-crawler com reprocessar erros e novas sementes..."
python -u main.py "$CIDADE" --sem-limite --etapa 1 --max-profundidade 10 --reprocessar-erros --pular-captcha 2>&1 | tee -a "$LOG"