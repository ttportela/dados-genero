python -u main.py pinhais --sem-limite --etapa 1 --max-profundidade 10 2>&1 | tee -a resultados/_logs/pinhais.txt
python -u main.py pinhalao --sem-limite --etapa 1 --max-profundidade 10 2>&1 | tee -a resultados/_logs/pinhalao.txt
python -u main.py pinhaldesaobento --sem-limite --etapa 1 --max-profundidade 10 2>&1 | tee -a resultados/_logs/pinhaldesaobento.txt
python -u main.py pinhao --sem-limite --etapa 1 --max-profundidade 10 2>&1 | tee -a resultados/_logs/pinhao.txt
