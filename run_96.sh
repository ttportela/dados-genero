python -u main.py doutorulysses --sem-limite --etapa 1 --max-profundidade 10 2>&1 | tee -a resultados/_logs/doutorulysses.txt
python -u main.py virmond --sem-limite --etapa 1 --max-profundidade 10 2>&1 | tee -a resultados/_logs/virmond.txt
python -u main.py vitorino --sem-limite --etapa 1 --max-profundidade 10 2>&1 | tee -a resultados/_logs/vitorino.txt
python -u main.py xambre --sem-limite --etapa 1 --max-profundidade 10 2>&1 | tee -a resultados/_logs/xambre.txt
