python -u main.py curiuva --sem-limite --etapa 1 --max-profundidade 10 2>&1 | tee -a resultados/_logs/curiuva.txt
python -u main.py diamantedonorte --sem-limite --etapa 1 --max-profundidade 10 2>&1 | tee -a resultados/_logs/diamantedonorte.txt
python -u main.py diamantedosul --sem-limite --etapa 1 --max-profundidade 10 2>&1 | tee -a resultados/_logs/diamantedosul.txt
python -u main.py diamantedoeste --sem-limite --etapa 1 --max-profundidade 10 2>&1 | tee -a resultados/_logs/diamantedoeste.txt
