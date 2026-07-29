python -u main.py campobonito --sem-limite --etapa 1 --max-profundidade 10 2>&1 | tee -a resultados/_logs/campobonito.txt
python -u main.py campodotenente --sem-limite --etapa 1 --max-profundidade 10 2>&1 | tee -a resultados/_logs/campodotenente.txt
python -u main.py campolargo --sem-limite --etapa 1 --max-profundidade 10 2>&1 | tee -a resultados/_logs/campolargo.txt
python -u main.py campomagro --sem-limite --etapa 1 --max-profundidade 10 2>&1 | tee -a resultados/_logs/campomagro.txt
