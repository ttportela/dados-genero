python -u main.py cascavel --sem-limite --etapa 1 --max-profundidade 10 2>&1 | tee -a resultados/_logs/cascavel.txt
python -u main.py castro --sem-limite --etapa 1 --max-profundidade 10 2>&1 | tee -a resultados/_logs/castro.txt
python -u main.py catanduvas --sem-limite --etapa 1 --max-profundidade 10 2>&1 | tee -a resultados/_logs/catanduvas.txt
python -u main.py cerroazul --sem-limite --etapa 1 --max-profundidade 10 2>&1 | tee -a resultados/_logs/cerroazul.txt
