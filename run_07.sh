python -u main.py assischateaubriand --sem-limite --etapa 1 --max-profundidade 10 2>&1 | tee -a resultados/_logs/assischateaubriand.txt
python -u main.py astorga --sem-limite --etapa 1 --max-profundidade 10 2>&1 | tee -a resultados/_logs/astorga.txt
python -u main.py atalaia --sem-limite --etapa 1 --max-profundidade 10 2>&1 | tee -a resultados/_logs/atalaia.txt
python -u main.py balsanova --sem-limite --etapa 1 --max-profundidade 10 2>&1 | tee -a resultados/_logs/balsanova.txt
