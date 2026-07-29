python -u main.py ventania --sem-limite --etapa 1 --max-profundidade 10 2>&1 | tee -a resultados/_logs/ventania.txt
python -u main.py veracruzdooeste --sem-limite --etapa 1 --max-profundidade 10 2>&1 | tee -a resultados/_logs/veracruzdooeste.txt
python -u main.py vere --sem-limite --etapa 1 --max-profundidade 10 2>&1 | tee -a resultados/_logs/vere.txt
python -u main.py altoparaiso --sem-limite --etapa 1 --max-profundidade 10 2>&1 | tee -a resultados/_logs/altoparaiso.txt
