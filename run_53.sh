python -u main.py matinhos --sem-limite --etapa 1 --max-profundidade 10 2>&1 | tee -a resultados/_logs/matinhos.txt
python -u main.py matorico --sem-limite --etapa 1 --max-profundidade 10 2>&1 | tee -a resultados/_logs/matorico.txt
python -u main.py mauadaserra --sem-limite --etapa 1 --max-profundidade 10 2>&1 | tee -a resultados/_logs/mauadaserra.txt
python -u main.py medianeira --sem-limite --etapa 1 --max-profundidade 10 2>&1 | tee -a resultados/_logs/medianeira.txt
