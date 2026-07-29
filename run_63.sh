python -u main.py peabiru --sem-limite --etapa 1 --max-profundidade 10 2>&1 | tee -a resultados/_logs/peabiru.txt
python -u main.py perobal --sem-limite --etapa 1 --max-profundidade 10 2>&1 | tee -a resultados/_logs/perobal.txt
python -u main.py perola --sem-limite --etapa 1 --max-profundidade 10 2>&1 | tee -a resultados/_logs/perola.txt
python -u main.py peroladoeste --sem-limite --etapa 1 --max-profundidade 10 2>&1 | tee -a resultados/_logs/peroladoeste.txt
