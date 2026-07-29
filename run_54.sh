python -u main.py mercedes --sem-limite --etapa 1 --max-profundidade 10 2>&1 | tee -a resultados/_logs/mercedes.txt
python -u main.py mirador --sem-limite --etapa 1 --max-profundidade 10 2>&1 | tee -a resultados/_logs/mirador.txt
python -u main.py miraselva --sem-limite --etapa 1 --max-profundidade 10 2>&1 | tee -a resultados/_logs/miraselva.txt
python -u main.py missal --sem-limite --etapa 1 --max-profundidade 10 2>&1 | tee -a resultados/_logs/missal.txt
