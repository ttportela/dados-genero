python -u main.py ipora --sem-limite --etapa 1 --max-profundidade 10 2>&1 | tee -a resultados/_logs/ipora.txt
python -u main.py iracemadooeste --sem-limite --etapa 1 --max-profundidade 10 2>&1 | tee -a resultados/_logs/iracemadooeste.txt
python -u main.py irati --sem-limite --etapa 1 --max-profundidade 10 2>&1 | tee -a resultados/_logs/irati.txt
python -u main.py iretama --sem-limite --etapa 1 --max-profundidade 10 2>&1 | tee -a resultados/_logs/iretama.txt
