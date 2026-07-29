python -u main.py guapirama --sem-limite --etapa 1 --max-profundidade 10 2>&1 | tee -a resultados/_logs/guapirama.txt
python -u main.py guaporema --sem-limite --etapa 1 --max-profundidade 10 2>&1 | tee -a resultados/_logs/guaporema.txt
python -u main.py guaraci --sem-limite --etapa 1 --max-profundidade 10 2>&1 | tee -a resultados/_logs/guaraci.txt
python -u main.py guaraniacu --sem-limite --etapa 1 --max-profundidade 10 2>&1 | tee -a resultados/_logs/guaraniacu.txt
