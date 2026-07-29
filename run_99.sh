python -u main.py pien --sem-limite --etapa 1 --max-profundidade 10 2>&1 | tee -a resultados/_logs/pien.txt
python -u main.py saojorgedoeste --sem-limite --etapa 1 --max-profundidade 10 2>&1 | tee -a resultados/_logs/saojorgedoeste.txt
python -u main.py saojosedospinhais --sem-limite --etapa 1 --max-profundidade 10 2>&1 | tee -a resultados/_logs/saojosedospinhais.txt
python -u main.py uniaodavitoria --sem-limite --etapa 1 --max-profundidade 10 2>&1 | tee -a resultados/_logs/uniaodavitoria.txt
