python -u main.py ibaiti --sem-limite --etapa 1 --max-profundidade 10 2>&1 | tee -a resultados/_logs/ibaiti.txt
python -u main.py ibema --sem-limite --etapa 1 --max-profundidade 10 2>&1 | tee -a resultados/_logs/ibema.txt
python -u main.py ibipora --sem-limite --etapa 1 --max-profundidade 10 2>&1 | tee -a resultados/_logs/ibipora.txt
python -u main.py icaraima --sem-limite --etapa 1 --max-profundidade 10 2>&1 | tee -a resultados/_logs/icaraima.txt
